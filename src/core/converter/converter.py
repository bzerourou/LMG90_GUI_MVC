"""Converter — orchestrateur principal : exécute le script mocké et produit le JSON projet."""
import ast
import copy
import os
import sys
import traceback
import types as _types
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .ast_analyzer import _AstAnalyzer
from .containers import _Container, _TrackedContainer, _AVATAR_TYPES
from .mock_pre import _MockPre
from .proxies_avatar import _AvatarObj, _EmptyAvatarObj, _MeshAvatarObj
from .proxies_data import _MaterialObj, _ModelObj, _TactBehavObj, _SeeTableObj, _PostproCommandObj
from .proxies_runtime import _NpProxy, _RangeProxy
from .utils import _center, _name, _to_serial, _rotate_vertices_2d, _default_preferences


class Converter:
    def __init__(self, script_path: Path):
        self.script_path  = script_path
        self.project_name = script_path.stem

        self._dimension    = 2
        self._materials    : Dict[str, _MaterialObj]  = {}
        self._models       : Dict[str, _ModelObj]     = {}
        self._avatar_pool  : List[Any]                = []
        self._bodies       : List[Any]                = []
        self._tact_behavs  : Dict[str, _TactBehavObj] = {}
        self._see_tables   : List[_SeeTableObj]       = []
        self._postpro_cmds : List[_PostproCommandObj] = []
        self._granulo_pairs: List[dict]               = []
        self._masonry_patterns: List[dict]            = []
        self._warnings:     List[str]                 = []

        self._dynamic_vars:  Dict[str, Any] = {}
        self._ast_for_loops: List[dict]     = []

        self._loop_captures: List[dict] = []
        self._loop_stack_rt: List[int]  = []

    @property
    def _active_loop_idx(self) -> Optional[int]:
        return self._loop_stack_rt[-1] if self._loop_stack_rt else None

    def _push_loop(self, count: int) -> int:
        idx = len(self._loop_captures)
        self._loop_captures.append({'count': count, 'avatar_indices': []})
        self._loop_stack_rt.append(idx)
        return idx

    def _pop_loop(self, loop_idx: int) -> None:
        if self._loop_stack_rt and self._loop_stack_rt[-1] == loop_idx:
            self._loop_stack_rt.pop()

    def run(self):
        script_src = self.script_path.read_text(encoding='utf-8', errors='replace')

        analyzer = _AstAnalyzer(script_src)
        analyzer.analyze()
        self._dynamic_vars  = analyzer.dynamic_vars
        self._ast_for_loops = analyzer.for_loops
        self._warnings.extend(analyzer.warnings)

        pre               = _MockPre(self)
        mock_pylmgc90     = type(sys)('pylmgc90')
        mock_pylmgc90.pre = pre

        bodies_container = _TrackedContainer(self)
        tacts_container  = _Container('tacts')
        sees_container   = _Container('sees')
        posts_container  = _Container('posts')
        mats_container   = _Container('mats')
        mods_container   = _Container('mods')

        import types as _types
        fake_os = _types.SimpleNamespace(
            path=_types.SimpleNamespace(
                isdir=lambda p: True, exists=lambda p: True,
                join=os.path.join, dirname=os.path.dirname,
                basename=os.path.basename,
            ),
            mkdir=lambda *a, **kw: None,
            getcwd=os.getcwd,
        )

        np_proxy = _NpProxy(self)
        glob = {
            '__name__': '__main__', '__file__': str(self.script_path),
            'os': fake_os, 'sys': sys, 'math': math,
            'numpy': np_proxy, 'np': np_proxy,
            'matplotlib': _SilentModule('matplotlib'), 'plt': _SilentModule('plt'),
            'bodies': bodies_container, 'mats': mats_container,
            'mods': mods_container, 'tacts': tacts_container,
            'svs': sees_container, 'sees': sees_container,
            'post': posts_container, 'posts': posts_container,
            'pre': pre, 'range': _RangeProxy(self),
        }

        sys.modules['pylmgc90']     = mock_pylmgc90
        sys.modules['pylmgc90.pre'] = pre

        try:
            exec(compile(script_src, str(self.script_path), 'exec'), glob)
        except Exception as exc:
            tb = traceback.format_exc()
            self._warnings.append(f"Execution partielle : {exc}\n{tb}")
        finally:
            sys.modules.pop('pylmgc90',     None)
            sys.modules.pop('pylmgc90.pre', None)

        bc = glob.get('bodies')
        if isinstance(bc, (_TrackedContainer, _Container)):
            self._bodies = [x for x in bc._items
                            if isinstance(x, _AVATAR_TYPES)]

        for t in tacts_container._items:
            if isinstance(t, _TactBehavObj):
                self._tact_behavs[t.name] = t
        for s in sees_container._items:
            if isinstance(s, _SeeTableObj):
                self._see_tables.append(s)
        for p in posts_container._items:
            if isinstance(p, _PostproCommandObj):
                self._postpro_cmds.append(p)

    # ── Heuristiques granulometrie ────────────────────────────────────────────

    def _guess_granulo_material(self) -> str:
        for name, m in reversed(list(self._materials.items())):
            if m.material_type == 'RIGID': return name
        return list(self._materials.keys())[-1] if self._materials else 'TDURx'

    def _guess_granulo_model(self) -> str:
        for name, m in reversed(list(self._models.items())):
            if 'Rxx' in m.element: return name
        return list(self._models.keys())[-1] if self._models else 'rigid'

    # ── Construction des Loop dicts ───────────────────────────────────────────

    def _build_loop_dicts(self) -> Tuple[List[dict], List[dict]]:
        loops:     List[dict] = []
        for_loops: List[dict] = []
        analyzer = _AstAnalyzer('')
        analyzer.dynamic_vars = self._dynamic_vars

        for ast_idx, desc in enumerate(self._ast_for_loops):
            loop_type  = desc.get('loop_type', 'Générique')
            geom       = desc.get('geometry', {})
            count      = desc.get('count')
            group_name = desc.get('group_name')

            avatar_indices: List[int] = []
            if ast_idx < len(self._loop_captures):
                avatar_indices = self._loop_captures[ast_idx].get('avatar_indices', [])
                if count is None and avatar_indices:
                    count = len(avatar_indices)

            model_av_idx = avatar_indices[0] if avatar_indices else 0

            for_loops.append({
                'loop_var':          desc['loop_var'],
                'start_expr':        desc['start_expr'],
                'end_expr':          desc['end_expr'],
                'step_expr':         desc['step_expr'],
                'target_type':       'avatar',
                'template_config':   desc.get('template_config', {}),
                'group_name':        group_name,
                'generated_indices': avatar_indices,
            })

            if count is None or loop_type == 'Générique':
                continue

            base = {
                'model_avatar_index':       model_av_idx,
                'count':                    count,
                'radius':                   0.0,
                'step':                     0.0,
                'offset_x':                0.0,
                'offset_y':                0.0,
                'spiral_factor':           0.0,
                'invert_axis':             False,
                'stored_in_group':         group_name,
                'generated_avatar_indices': avatar_indices,
            }

            if loop_type == 'Cercle':
                R   = analyzer._resolve_float(geom.get('R_expr', '')) or 1.0
                cx0 = analyzer._resolve_float(geom.get('offset_x', '')) or 0.0
                cy0 = analyzer._resolve_float(geom.get('offset_y', '')) or 0.0
                loops.append({**base, 'type': 'Cercle',
                               'radius': R, 'offset_x': cx0, 'offset_y': cy0})
            elif loop_type == 'Spirale':
                R = analyzer._resolve_float(geom.get('R_expr', '')) or 1.0
                loops.append({**base, 'type': 'Spirale',
                               'radius': R, 'spiral_factor': R / max(count, 1)})
            elif loop_type == 'Ligne':
                dx   = analyzer._resolve_float(geom.get('dx_expr', '')) or 0.0
                dy   = analyzer._resolve_float(geom.get('dy_expr', '')) or 0.0
                step = abs(dx) if dx else abs(dy)
                ox   = self._extract_constant_offset(
                    geom.get('cx_src', ''), desc['loop_var'], analyzer)
                oy   = self._extract_constant_offset(
                    geom.get('cy_src', ''), desc['loop_var'], analyzer)
                loops.append({**base, 'type': 'Ligne',
                               'step': step,
                               'offset_x': dx if dx else ox,
                               'offset_y': dy if dy else oy,
                               'invert_axis': (dy < 0) or (dx < 0)})
            elif loop_type == 'Grille':
                nx = analyzer._resolve_int(geom.get('nx_expr', '')) or count
                ny = analyzer._resolve_int(geom.get('ny_expr', '')) or 1
                dx = analyzer._resolve_float(geom.get('dx_expr', '')) or 0.0
                dy = analyzer._resolve_float(geom.get('dy_expr', '')) or 0.0
                loops.append({**base, 'type': 'Grille',
                               'count': nx * ny, 'step': abs(dx) if dx else abs(dy),
                               'offset_x': dx, 'offset_y': dy})

        return loops, for_loops

    @staticmethod
    def _extract_constant_offset(center_expr: str, loop_var: str,
                                  analyzer: '_AstAnalyzer') -> float:
        if not center_expr: return 0.0
        try:
            tree = ast.parse(center_expr, mode='eval')
            for node in ast.walk(tree):
                if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
                    for side in (node.left, node.right):
                        s = ast.unparse(side)
                        if loop_var not in s:
                            val = analyzer._resolve_float(s)
                            if val is not None: return val
        except Exception:
            pass
        return 0.0

    # ── Construction du JSON projet ───────────────────────────────────────────

    def to_lmgc90_dict(self) -> dict:
        avatar_index = {id(av): i for i, av in enumerate(self._bodies)}

        materials = [
            {'name': name, 'type': m.material_type,
             'density': m.density, 'props': m.props}
            for name, m in self._materials.items()
        ]

        models = []
        for name, m in self._models.items():
            d = {'name': name, 'physics': m.physics,
                 'element': m.element, 'dimension': m.dimension}
            d.update(m.opts)
            models.append(d)

        avatars = []
        for av in self._bodies:
            av_dict = self._avatar_to_dict(av)
            if av_dict:
                avatars.append(av_dict)

        contact_laws = []
        for name, t in self._tact_behavs.items():
            d = {'name': name, 'law': t.law}
            if t.fric is not None: d['fric'] = float(t.fric)
            d.update(t.props)
            contact_laws.append(d)

        visibility_rules = [{
            'CorpsCandidat':    s.candidate_body,
            'candidat':        s.candidate_contactor,
            'colorCandidat':   s.candidate_color,
            'CorpsAntagoniste': s.antagonist_body,
            'antagoniste':     s.antagonist_contactor,
            'colorAntagoniste': s.antagonist_color,
            'behav':           s.behav_name,
            'alert':           s.alert,
        } for s in self._see_tables]

        operations = []
        for av in self._bodies:
            idx = avatar_index.get(id(av))
            if idx is None: continue
            for dof in av._dof_ops:
                op     = dof['op']
                params = copy.deepcopy(dof['params'])
                if op == 'translate' and self._dimension == 2:
                    params.pop('dz', None)
                operations.append({
                    'type': op, 'target': 'avatar',
                    'target_value': idx, 'params': params,
                })

        postpro_creations = []
        for p in self._postpro_cmds:
            d: dict = {'name': p.name, 'step': p.step}
            if p.rigid_set:
                indices = [avatar_index[id(b)] for b in p.rigid_set
                           if isinstance(b, _AVATAR_TYPES) and id(b) in avatar_index]
                if indices:
                    d['target_info'] = {'type': 'avatar', 'value': indices[0]}
            postpro_creations.append(d)

        granulo_generations = []
        for g in self._granulo_pairs:
            if g.get('container_type') is None: continue
            granulo_generations.append({
                'nb':    g.get('nb_particles', g['nb']),
                'rmin':  g['rmin'], 'rmax': g['rmax'],
                'container_params': {'type': g['container_type'], **g['container_params']},
                'model':       self._guess_granulo_model(),
                'material':    self._guess_granulo_material(),
                'avatar_type': 'rigidSphere' if self._dimension == 3 else 'rigidDisk',
                'color':       'BLUEx', 'seed': g.get('seed'),
                'stored_in_group': f"granulo_{g['container_type'].lower()}",
                'avatar_indices':  [],
            })

        loops, for_loops = self._build_loop_dicts()

        masonry_patterns = {
            str(p['pattern_idx']): {k: v for k, v in p.items() if k != 'pattern_idx'}
            for p in self._masonry_patterns
        }

        return {
            'project_name':        self.project_name,
            'dimension':           self._dimension,
            'units':               'SI',
            'preferences':         _default_preferences(),
            'materials':           materials,
            'models':              models,
            'avatars':             avatars,
            'custom_templates':    {},
            'contact_laws':        contact_laws,
            'visibility_rules':    visibility_rules,
            'operations':          operations,
            'loops':               loops,
            'for_loops':           for_loops,
            'granulo_generations': granulo_generations,
            'postpro_creations':   postpro_creations,
            'avatar_groups':       {},
            'dynamic_vars':        self._dynamic_vars,
            'masonry_patterns':    masonry_patterns,
        }

    # ── Serialisation d'un avatar ─────────────────────────────────────────────

    def _avatar_to_dict(self, av) -> Optional[dict]:
        """Convertit un avatar en dict .lmgc90."""

        # ── Avatar vide (contacteurs manuels) ─────────────────────────────────
        if isinstance(av, _EmptyAvatarObj):
            return self._empty_avatar_to_dict(av)

        # ── Corps deformable / rigide issu de maillage ────────────────────────
        if isinstance(av, _MeshAvatarObj):
            return self._mesh_avatar_to_dict(av)

        # ── Corps rigide standard ─────────────────────────────────────────────
        return self._rigid_avatar_to_dict(av)

    def _empty_avatar_to_dict(self, av: _EmptyAvatarObj) -> dict:
        """Serialise un avatar vide avec contacteurs manuels."""
        origin = 'loop' if av._loop_idx is not None else 'manual'
        d: dict = {
            'type':       'emptyAvatar',
            'center':     _to_serial(av._center),
            'material':   av._material,
            'model':      av._model,
            'color':      av._color,
            '__origin':   origin,
            'contactors': av._contactors,
        }
        return d

    def _mesh_avatar_to_dict(self, av: _MeshAvatarObj) -> dict:
        """
        Serialise un corps deformable ou rigide issu de maillage.

        Geometries reconnues (stockees dans mesh_params['geom']) :
          buildMesh2D / buildMeshT3/T6/Q4/Q8  → 'Rectangle'
          buildMeshH8                          → 'Boite (H8)'
          readMesh / readMeshGMSH / readMeshVTK → 'Fichier externe'
          buildMeshedAvatar (depuis buildMesh)  → geom herite du maillage source
          surfacicMeshToRigid3D                → 'SurfacicRigid3D'
          volumicMeshToRigid3D                 → 'VolumetricRigid3D'
        """
        model    = av._model    or av._mesh_params.get('model', '')
        material = av._material or av._mesh_params.get('material', '')
        color    = av._color    or av._mesh_params.get('color', 'BLUEx')

        if model    and model    not in self._models:
            self._warnings.append(f"Mesh {av._source}: modele '{model}' inconnu.")
        if material and material not in self._materials:
            self._warnings.append(f"Mesh {av._source}: materiau '{material}' inconnu.")

        origin = 'loop' if av._loop_idx is not None else 'manual'

        # ── Determiner la geometrie et les params pour mesh_params ────────────
        mp   = av._mesh_params
        src  = av._source
        geom: dict = {}

        if src in ('surfacicMeshToRigid3D',):
            geom = {'geom': 'SurfacicRigid3D', 'dim': 3,
                    'rigid_from_mesh': True, 'deformable': False}
            sub = mp.get('mesh_params', {})
            if sub.get('mesh_file'): geom['filepath'] = sub['mesh_file']
            elif mp.get('mesh_file'): geom['filepath'] = mp['mesh_file']

        elif src in ('volumicMeshToRigid3D',):
            geom = {'geom': 'VolumetricRigid3D', 'dim': 3,
                    'rigid_from_mesh': True, 'deformable': False}
            sub = mp.get('mesh_params', {})
            if sub.get('mesh_file'): geom['filepath'] = sub['mesh_file']
            elif mp.get('mesh_file'): geom['filepath'] = mp['mesh_file']

        elif src in ('readMesh', 'readMeshGMSH', 'readMeshVTK'):
            fname = mp.get('mesh_file', '')
            dim   = int(mp.get('dim', 2))
            fmt   = mp.get('format', 'lmgc90')
            geom  = {'geom': 'Fichier externe', 'filepath': fname, 'dim': dim,
                     'format': fmt, 'deformable': mp.get('deformable', True)}

        elif src == 'buildMeshH8':
            geom = {
                'geom': 'Boite (H8)', 'dim': 3, 'deformable': True,
                'x0': mp.get('x0', 0.), 'y0': mp.get('y0', 0.), 'z0': mp.get('z0', 0.),
                'lx': mp.get('lx', 1.), 'ly': mp.get('ly', 1.), 'lz': mp.get('lz', 1.),
                'nx': mp.get('nx', 2),  'ny': mp.get('ny', 2),  'nz': mp.get('nz', 2),
                'cx': av._center[0] if len(av._center) > 0 else 0.,
                'cy': av._center[1] if len(av._center) > 1 else 0.,
                'cz': av._center[2] if len(av._center) > 2 else 0.,
            }

        elif src in ('buildMesh2D', 'buildMeshT3', 'buildMeshQ4',
                     'buildMeshT6', 'buildMeshQ8'):
            geom = {
                'geom': 'Rectangle', 'dim': 2, 'deformable': True,
                'mesh_type': mp.get('mesh_type', 'T3xxx'),
                'x0': mp.get('x0', 0.), 'y0': mp.get('y0', 0.),
                'lx': mp.get('lx', 1.), 'ly': mp.get('ly', 1.),
                'nx': mp.get('nx', 4),  'ny': mp.get('ny', 4),
                'cx': av._center[0] if len(av._center) > 0 else 0.,
                'cy': av._center[1] if len(av._center) > 1 else 0.,
            }

        elif src == 'buildMeshedAvatar':
            # Heriter la geometrie du maillage source
            sub_mp  = mp.get('mesh_params', {})
            sub_src = mp.get('mesh_source', '')
            if sub_src == 'buildMeshH8':
                geom = {
                    'geom': 'Boite (H8)', 'dim': 3, 'deformable': True,
                    'x0': sub_mp.get('x0', 0.), 'y0': sub_mp.get('y0', 0.),
                    'z0': sub_mp.get('z0', 0.),
                    'lx': sub_mp.get('lx', 1.), 'ly': sub_mp.get('ly', 1.),
                    'lz': sub_mp.get('lz', 1.),
                    'nx': sub_mp.get('nx', 2), 'ny': sub_mp.get('ny', 2),
                    'nz': sub_mp.get('nz', 2),
                    'cx': av._center[0] if len(av._center) > 0 else 0.,
                    'cy': av._center[1] if len(av._center) > 1 else 0.,
                    'cz': av._center[2] if len(av._center) > 2 else 0.,
                }
            elif sub_src in ('buildMesh2D', 'buildMeshT3', 'buildMeshQ4',
                              'buildMeshT6', 'buildMeshQ8'):
                geom = {
                    'geom': 'Rectangle', 'dim': 2, 'deformable': True,
                    'mesh_type': sub_mp.get('mesh_type', 'T3xxx'),
                    'x0': sub_mp.get('x0', 0.), 'y0': sub_mp.get('y0', 0.),
                    'lx': sub_mp.get('lx', 1.), 'ly': sub_mp.get('ly', 1.),
                    'nx': sub_mp.get('nx', 4), 'ny': sub_mp.get('ny', 4),
                    'cx': av._center[0] if len(av._center) > 0 else 0.,
                    'cy': av._center[1] if len(av._center) > 1 else 0.,
                }
            elif sub_src in ('readMesh', 'readMeshGMSH', 'readMeshVTK'):
                fname = sub_mp.get('mesh_file', mp.get('mesh_file', ''))
                dim   = int(sub_mp.get('dim', mp.get('dim', 2)))
                fmt   = sub_mp.get('format', 'lmgc90')
                geom  = {'geom': 'Fichier externe', 'filepath': fname,
                         'dim': dim, 'format': fmt, 'deformable': True}
            else:
                # Source inconnue ou intermediaire
                fname = sub_mp.get('mesh_file', mp.get('mesh_file', ''))
                dim   = int(sub_mp.get('dim', mp.get('dim', len(av._center))))
                geom  = {'geom': 'Fichier externe', 'filepath': fname,
                         'dim': dim, 'deformable': True,
                         'note': f'source={sub_src or src}'}
        else:
            # Source inconnue : on capture ce qu'on peut
            fname = mp.get('mesh_file', '')
            dim   = int(mp.get('dim', len(av._center)))
            geom  = {'geom': 'Fichier externe', 'filepath': fname,
                     'dim': dim, 'deformable': True, 'note': f'source={src}'}

        # Ajouter les groupes et contacteurs si presents
        if av._groups:
            geom['groups']     = av._groups
        if av._contactors:
            geom['contactors'] = av._contactors

        return {
            'type':       'mesh',
            'center':     _to_serial(av._center),
            'material':   material,
            'model':      model,
            'color':      color,
            '__origin':   origin,
            'mesh_params': geom,
        }

    def _rigid_avatar_to_dict(self, av: _AvatarObj) -> Optional[dict]:
        """Serialise un avatar rigide standard."""
        kw       = av._kwargs
        t        = av._type
        center   = kw.get('center',   [0., 0.])
        material = kw.get('material') or ''
        model    = kw.get('model')    or ''
        color    = kw.get('color',    'BLUEx')

        if material and material not in self._materials:
            self._warnings.append(f"Avatar {t}: materiau '{material}' inconnu.")
        if model and model not in self._models:
            self._warnings.append(f"Avatar {t}: modele '{model}' inconnu.")

        origin = ('masonry' if av._masonry_idx is not None
                  else 'loop' if av._loop_idx is not None
                  else 'manual')

        d: dict = {
            'type':     t,
            'center':   _to_serial(center),
            'material': material,
            'model':    model,
            'color':    color,
            '__origin': origin,
        }

        # ── Rigides 2D ───────────────────────────────────────────────────────

        if t == 'rigidDisk':
            d['r'] = float(kw.get('r', 0.1))
            if kw.get('is_Hollow') or kw.get('is_hollow'):
                d['is_Hollow'] = True

        elif t == 'rigidJonc':
            d['axe1'] = float(kw.get('axe1', 1.))
            d['axe2'] = float(kw.get('axe2', 0.1))

        elif t == 'rigidPolygon':
            gen = kw.get('generation_type', 'regular')
            if gen: d['gen_type'] = gen
            if kw.get('radius')      is not None: d['radius']      = float(kw['radius'])
            if kw.get('nb_vertices') is not None: d['nb_vertices'] = int(kw['nb_vertices'])
            if kw.get('vertices'):
                verts = _to_serial(kw['vertices'])
                theta = kw.get('theta', 0.)
                if theta and isinstance(verts, list):
                    verts = _rotate_vertices_2d(verts, float(theta))
                d['vertices'] = verts
            # Dimensions brique (genere par _BrickObj.rigidBrick)
            if 'lx' in kw: d['lx'] = float(kw['lx'])
            if 'ly' in kw: d['ly'] = float(kw['ly'])
            if 'brick_name' in kw: d['brick_name'] = str(kw['brick_name'])

        elif t == 'rigidOvoidPolygon':
            d['ra']          = float(kw.get('ra', 1.))
            d['rb']          = float(kw.get('rb', 1.))
            d['nb_vertices'] = int(kw.get('nb_vertices', 8))

        elif t == 'rigidDiscreteDisk':
            d['r'] = float(kw.get('r', 0.1))

        elif t == 'rigidCluster':
            d['nb_vertices'] = int(kw.get('nb_disk', kw.get('nb_vertices', 3)))
            d['r']           = float(kw.get('r', 0.1))

        elif t in ('roughWall', 'fineWall'):
            # l = longueur, r = rayon des disques de contacteurs
            d['l']         = float(kw.get('l', 1.))
            d['r']         = float(kw.get('r', 0.1))
            d['nb_vertex'] = int(kw.get('nb_vertex', 10))

        elif t == 'smoothWall':
            # l = longueur, h = hauteur du mur
            d['l']        = float(kw.get('l', 1.))
            d['h']        = float(kw.get('h', 0.1))
            d['nb_polyg'] = int(kw.get('nb_polyg', 10))

        elif t == 'granuloRoughWall':
            d['l']         = float(kw.get('l', 1.))
            d['rmin']      = float(kw.get('rmin', 0.05))
            d['rmax']      = float(kw.get('rmax', 0.1))
            d['nb_vertex'] = int(kw.get('nb_vertex', 10))

        # ── Rigides 3D ───────────────────────────────────────────────────────

        elif t == 'rigidSphere':
            d['r'] = float(kw.get('r', 0.1))

        elif t == 'rigidPlan':
            # axe1/axe2/axe3 = demi-dimensions du plan rectangulaire
            d['axe1'] = float(kw.get('axe1', 1.))
            d['axe2'] = float(kw.get('axe2', 1.))
            d['axe3'] = float(kw.get('axe3', 0.05))

        elif t == 'rigidCylinder':
            d['r']  = float(kw.get('r',  0.5))
            d['lz'] = float(kw.get('h', kw.get('lz', 1.)))

        elif t == 'rigidPolyhedron':
            gen = kw.get('generation_type', 'regular')
            if gen: d['gen_type'] = gen
            if kw.get('vertices'):   d['vertices']    = _to_serial(kw['vertices'])
            if kw.get('faces'):      d['faces']        = _to_serial(kw['faces'])
            if kw.get('nb_vertices') is not None: d['nb_vertices'] = int(kw['nb_vertices'])
            if kw.get('radius')      is not None: d['radius']      = float(kw['radius'])
            if 'lx' in kw: d['lx'] = float(kw['lx'])
            if 'ly' in kw: d['ly'] = float(kw['ly'])
            if 'lz' in kw: d['lz'] = float(kw['lz'])
            if 'brick_name' in kw: d['brick_name'] = str(kw['brick_name'])

        elif t == 'roughWall3D':
            # lx/ly = dimensions du plan, r = rayon des disques
            d['lx'] = float(kw.get('lx', 1.))
            d['ly'] = float(kw.get('ly', 1.))
            d['r']  = float(kw.get('r',  0.05))

        elif t == 'granuloRoughWall3D':
            d['lx']  = float(kw.get('lx',   1.))
            d['ly']  = float(kw.get('ly',   1.))
            d['rmin'] = float(kw.get('rmin', 0.02))
            d['rmax'] = float(kw.get('rmax', 0.05))

        # Maonnerie index
        if av._masonry_idx is not None:
            d['masonry_pattern_idx'] = av._masonry_idx

        return d
