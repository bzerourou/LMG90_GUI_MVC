# ============================================================================
# convert.py  —  Convertisseur script pylmgc90 → projet .lmgc90 (GUI)
# ============================================================================
"""
Convertit un script Python de pre-traitement pylmgc90 en fichier .lmgc90
lisible par LMGC90_GUI.

Strategie : execution du script dans un environnement controle ou pylmgc90.pre
est remplace par un module fantome (_MockPre) qui intercepte tous les appels
et construit la representation du projet.

Usage :
    python convert.py mon_script.py               → mon_script.lmgc90
    python convert.py mon_script.py -o sortie.lmgc90
    python convert.py mon_script.py --check        # verif sans ecrire

Elements convertis
──────────────────
Corps rigides 2D
  ✓ pre.rigidDisk(r, center, ...)
  ✓ pre.rigidJonc(axe1, axe2, center, ...)
  ✓ pre.rigidPolygon(center, ..., generation_type, nb_vertices/vertices)
  ✓ pre.rigidOvoidPolygon(ra, rb, nb_vertices, center, ...)
  ✓ pre.rigidDiscreteDisk(r, center, ...)
  ✓ pre.rigidCluster(nb_disk, r, center, ...)
  ✓ pre.roughWall(l, r, center, ...)
  ✓ pre.fineWall(l, r, center, ...)
  ✓ pre.smoothWall(l, h, center, ...)
  ✓ pre.granuloRoughWall(l, rmin, rmax, center, ...)

Corps rigides 3D
  ✓ pre.rigidSphere(r, center, ...)
  ✓ pre.rigidPlan(axe1, axe2, axe3, center, ...)
  ✓ pre.rigidCylinder(r, h, center, ...)
  ✓ pre.rigidPolyhedron(center, ..., vertices, faces)
  ✓ pre.roughWall3D(lx, ly, r, center, ...)
  ✓ pre.granuloRoughWall3D(lx, ly, rmin, rmax, center, ...)

Avatar vide (contacteurs manuels)
  ✓ pre.avatar(dimension=2/3)
  ✓ .addBulk(pre.rigid2d()/pre.rigid3d())
  ✓ .addNode(pre.node(coor, number))
  ✓ .defineGroups() / .defineModel() / .defineMaterial()
  ✓ .addContactors(shape, color, ...)
  ✓ .computeRigidProperties()

Corps deformables / rigides issus de maillage
  ✓ pre.buildMesh2D(mesh_type, x0, y0, lx, ly, nx, ny)
  ✓ pre.buildMeshH8(x0, y0, z0, lx, ly, lz, nx, ny, nz)
  ✓ pre.buildMeshT3(...)  pre.buildMeshQ4(...)
  ✓ pre.buildMeshT6(...)  pre.buildMeshQ8(...)
  ✓ pre.readMesh(filename, dim)
  ✓ pre.readMeshGMSH(filename, dim)
  ✓ pre.readMeshVTK(filename, dim)
  ✓ pre.buildMeshedAvatar(mesh, model, material)
  ✓ pre.surfacicMeshToRigid3D(mesh, model, material, color)
  ✓ pre.volumicMeshToRigid3D(mesh, model, material, color)
  ✓ .defineModel() / .defineMaterial() / .addContactors()
  ✓ .imposeDrivenDof() / .imposeInitValue() / .translate() / .rotate()

Maconnerie
  ✓ pre.brick2D(name, lx, ly)
  ✓ pre.brick3D(name, lx, ly, lz)
  ✓ pre.paneresse_simple / paneresse_double
  ✓ .buildRigidWall() / .buildRigidWallWithoutHalfBricks()

Contact / Visibilite / PostPro
  ✓ pre.tact_behav(...)
  ✓ pre.see_table(...)
  ✓ pre.postpro_command(...)

Granulometrie
  ✓ pre.granulo_Random(nb, rmin, rmax)
  ✓ pre.depositInBox2D/Disk2D/Couette2D/Drum2D/Box3D/Sphere3D/Cylinder3D

Divers
  ✓ Variables dynamiques scalaires  → dynamic_vars
  ✓ Boucles for range() / np.linspace()
  ✓ dim = 2 / dim = 3
"""

import ast
import sys
import os
import json
import math
import copy
import argparse
import traceback
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Objets proxy
# ============================================================================

class _NodeObj:
    """Proxy d'un noeud pylmgc90."""
    __slots__ = ('coor', 'number')

    def __init__(self, coor=None, number=1):
        self.coor   = list(coor) if coor is not None else [0., 0.]
        self.number = int(number)

    def __repr__(self):
        return f"Node(number={self.number}, coor={self.coor})"


class _BulkObj:
    """Proxy de rigid2d() / rigid3d() — aucune donnee utile pour la conversion."""
    def __init__(self, kind='rigid2d'):
        self._kind = kind

    def __repr__(self):
        return f"Bulk({self._kind})"


class _AvatarObj:
    """Proxy d'un avatar rigide cree directement (pre.rigidDisk, etc.)."""

    def __init__(self, avatar_type: str, kwargs: dict):
        self._type      = avatar_type
        self._kwargs    = kwargs
        self._dof_ops   = []
        self._loop_idx: Optional[int] = None
        self._masonry_idx: Optional[int] = None

    # ── Transformations ──────────────────────────────────────────────────────

    def translate(self, dx=0., dy=0., dz=0., **kw):
        self._dof_ops.append({'op': 'translate',
                              'params': {'dx': float(dx), 'dy': float(dy), 'dz': float(dz)}})
        c = self._kwargs.get('center', [0., 0.])
        if len(c) == 2:
            self._kwargs['center'] = [c[0]+float(dx), c[1]+float(dy)]
        else:
            self._kwargs['center'] = [c[0]+float(dx), c[1]+float(dy), c[2]+float(dz)]

    def rotate(self, description='Euler', phi=0., theta=0., psi=0.,
               alpha=0., axis=None, center=None, **kw):
        params = {'description': description}
        if description == 'Euler':
            params.update({'phi': float(phi), 'theta': float(theta), 'psi': float(psi)})
        else:
            params.update({'alpha': float(alpha),
                           'axis': list(axis) if axis is not None else [0., 0., 1.]})
        if center is not None:
            params['center'] = list(center)
        self._dof_ops.append({'op': 'rotate', 'params': params})

    # ── Conditions aux limites ────────────────────────────────────────────────

    def imposeDrivenDof(self, group='all', component=1, description='predefined',
                        dofty='vlocy', ct=0., amp=0., omega=0., phi=0.,
                        rampi=1., ramp=0., evolutionFile='', **kw):
        params = {'group': group, 'component': _to_serial(component),
                  'dofty': dofty, 'ct': float(ct)}
        if amp:         params['amp']           = float(amp)
        if omega:       params['omega']         = float(omega)
        if phi:         params['phi']           = float(phi)
        if rampi != 1.: params['rampi']         = float(rampi)
        if ramp:        params['ramp']          = float(ramp)
        if evolutionFile: params['evolutionFile'] = evolutionFile
        if description != 'predefined': params['description'] = description
        self._dof_ops.append({'op': 'imposeDrivenDof', 'params': params})

    def imposeInitValue(self, group='all', component=1, value=0., **kw):
        self._dof_ops.append({'op': 'imposeInitValue',
                              'params': {'group': group,
                                         'component': _to_serial(component),
                                         'value': float(value)}})

    @property
    def nodes(self):
        return _NodesMock(self._kwargs.get('center', [0., 0.]))

    def __repr__(self):
        return f"Avatar({self._type}, center={self._kwargs.get('center')})"


# ============================================================================
# Avatar vide (pre.avatar() + methodes)
# ============================================================================

class _EmptyAvatarObj:
    """
    Proxy d'un avatar vide cree par pre.avatar(dimension=2/3) suivi de
    addBulk / addNode / defineModel / defineMaterial / addContactors /
    computeRigidProperties.
    """

    def __init__(self, dimension: int = 2):
        self._type        = 'emptyAvatar'
        self.dimension    = int(dimension)
        self._model       = ''
        self._material    = ''
        self._color       = 'BLUEx'
        self._contactors: List[dict] = []
        self._dof_ops:    List[dict] = []
        self._loop_idx:   Optional[int] = None
        self._masonry_idx: Optional[int] = None
        self._center: List[float] = [0.] * self.dimension
        # Compatibilite _TrackedContainer / _avatar_to_dict
        self._kwargs: dict = {'center': self._center}

    # ── Configuration ────────────────────────────────────────────────────────

    def addBulk(self, bulk=None): pass  # rigid2d/rigid3d — pas de donnees utiles

    def addNode(self, node=None):
        if isinstance(node, _NodeObj) and node.coor:
            self._center = list(node.coor)
            self._kwargs['center'] = self._center

    def defineGroups(self, *a, **kw): pass

    def defineModel(self, model=None, **kw):
        if model is not None:
            self._model = _name(model)
            self._kwargs['model'] = self._model

    def defineMaterial(self, material=None, **kw):
        if material is not None:
            self._material = _name(material)
            self._kwargs['material'] = self._material

    def addContactors(self, shape='DISKx', color='BLUEx', group='all', **params):
        self._color = color
        self._kwargs['color'] = color
        self._contactors.append({
            'shape': shape,
            'color': color,
            'group': group,
            'params': {k: _to_serial(v) for k, v in params.items()},
        })

    def computeRigidProperties(self, *a, **kw): pass

    # ── DOF / transformations ─────────────────────────────────────────────────

    def translate(self, dx=0., dy=0., dz=0., **kw):
        self._dof_ops.append({'op': 'translate',
                              'params': {'dx': float(dx), 'dy': float(dy), 'dz': float(dz)}})
        c = self._center
        if len(c) == 2:
            self._center = [c[0]+float(dx), c[1]+float(dy)]
        else:
            self._center = [c[0]+float(dx), c[1]+float(dy), c[2]+float(dz)]
        self._kwargs['center'] = self._center

    def rotate(self, description='Euler', phi=0., theta=0., psi=0.,
               alpha=0., axis=None, center=None, **kw):
        params = {'description': description}
        if description == 'Euler':
            params.update({'phi': float(phi), 'theta': float(theta), 'psi': float(psi)})
        else:
            params.update({'alpha': float(alpha),
                           'axis': list(axis) if axis is not None else [0., 0., 1.]})
        if center is not None:
            params['center'] = list(center)
        self._dof_ops.append({'op': 'rotate', 'params': params})

    def imposeDrivenDof(self, group='all', component=1, description='predefined',
                        dofty='vlocy', ct=0., amp=0., omega=0., phi=0.,
                        rampi=1., ramp=0., evolutionFile='', **kw):
        params = {'group': group, 'component': _to_serial(component),
                  'dofty': dofty, 'ct': float(ct)}
        if amp:         params['amp']   = float(amp)
        if omega:       params['omega'] = float(omega)
        if phi:         params['phi']   = float(phi)
        if rampi != 1.: params['rampi'] = float(rampi)
        if ramp:        params['ramp']  = float(ramp)
        if evolutionFile: params['evolutionFile'] = evolutionFile
        if description != 'predefined': params['description'] = description
        self._dof_ops.append({'op': 'imposeDrivenDof', 'params': params})

    def imposeInitValue(self, group='all', component=1, value=0., **kw):
        self._dof_ops.append({'op': 'imposeInitValue',
                              'params': {'group': group,
                                         'component': _to_serial(component),
                                         'value': float(value)}})

    @property
    def nodes(self):
        return _NodesMock(self._center)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return lambda *a, **kw: None

    def __repr__(self):
        return f"EmptyAvatar(dim={self.dimension}, center={self._center}, contactors={len(self._contactors)})"


# ============================================================================
# Corps deformable / rigide issu de maillage
# ============================================================================

class _MeshAvatarObj:
    """
    Proxy d'un corps deformable ou rigide issu de maillage.

    Sources supportees :
      buildMesh2D, buildMeshH8, buildMeshT3, buildMeshQ4,
      buildMeshT6, buildMeshQ8,
      readMesh, readMeshGMSH, readMeshVTK,
      buildMeshedAvatar,
      surfacicMeshToRigid3D, volumicMeshToRigid3D
    """

    def __init__(self, source: str, params: dict, converter: 'Converter'):
        self._type          = 'mesh'
        self._source        = source
        self._mesh_params   = dict(params)
        self._cv            = converter
        self._model         = params.get('model', '')
        self._material      = params.get('material', '')
        self._color         = params.get('color', 'BLUEx')
        self._groups:      List[str]  = []
        self._contactors:  List[dict] = []
        self._dof_ops:     List[dict] = []
        self._loop_idx:    Optional[int] = None
        self._masonry_idx: Optional[int] = None
        dim = 3 if source in ('buildMeshH8', 'surfacicMeshToRigid3D',
                               'volumicMeshToRigid3D', 'readMesh3D',
                               'readMeshGMSH', 'readMeshVTK') else 2
        self._center: List[float] = _center(params.get('center'), dim=dim)
        self._kwargs = {
            'center':   self._center,
            'model':    self._model,
            'material': self._material,
            'color':    self._color,
        }

    # ── Configuration ────────────────────────────────────────────────────────

    def defineGroups(self, *groups, **kw):
        for g in groups:
            if isinstance(g, str):
                self._groups.append(g)

    def defineModel(self, model=None, **kw):
        if model is not None:
            self._model = _name(model)
            self._kwargs['model'] = self._model
            self._mesh_params['model'] = self._model

    def defineMaterial(self, material=None, **kw):
        if material is not None:
            self._material = _name(material)
            self._kwargs['material'] = self._material
            self._mesh_params['material'] = self._material

    def addContactors(self, group='all', contactor='ALpxx',
                      shape=None, color='BLUEx', **kw):
        self._color = color
        self._kwargs['color'] = color
        self._contactors.append({
            'group':      group,
            'contactor':  contactor or shape or 'ALpxx',
            'color':      color,
            'extra':      {k: _to_serial(v) for k, v in kw.items()},
        })

    def computeRigidProperties(self, *a, **kw): pass
    def setModel(self, *a, **kw):                pass
    def setMaterial(self, *a, **kw):             pass

    # ── DOF / transformations ─────────────────────────────────────────────────

    def translate(self, dx=0., dy=0., dz=0., **kw):
        self._dof_ops.append({'op': 'translate',
                              'params': {'dx': float(dx), 'dy': float(dy), 'dz': float(dz)}})
        c = self._center
        if len(c) == 2:
            self._center = [c[0]+float(dx), c[1]+float(dy)]
        else:
            self._center = [c[0]+float(dx), c[1]+float(dy), c[2]+float(dz)]
        self._kwargs['center'] = self._center

    def rotate(self, description='Euler', phi=0., theta=0., psi=0.,
               alpha=0., axis=None, center=None, **kw):
        params = {'description': description}
        if description == 'Euler':
            params.update({'phi': float(phi), 'theta': float(theta), 'psi': float(psi)})
        else:
            params.update({'alpha': float(alpha),
                           'axis': list(axis) if axis is not None else [0., 0., 1.]})
        if center is not None:
            params['center'] = list(center)
        self._dof_ops.append({'op': 'rotate', 'params': params})

    def imposeDrivenDof(self, group='all', component=1, description='predefined',
                        dofty='vlocy', ct=0., amp=0., omega=0., phi=0.,
                        rampi=1., ramp=0., evolutionFile='', **kw):
        params = {'group': group, 'component': _to_serial(component),
                  'dofty': dofty, 'ct': float(ct)}
        if amp:         params['amp']   = float(amp)
        if omega:       params['omega'] = float(omega)
        if phi:         params['phi']   = float(phi)
        if rampi != 1.: params['rampi'] = float(rampi)
        if ramp:        params['ramp']  = float(ramp)
        if evolutionFile: params['evolutionFile'] = evolutionFile
        if description != 'predefined': params['description'] = description
        self._dof_ops.append({'op': 'imposeDrivenDof', 'params': params})

    def imposeInitValue(self, group='all', component=1, value=0., **kw):
        self._dof_ops.append({'op': 'imposeInitValue',
                              'params': {'group': group,
                                         'component': _to_serial(component),
                                         'value': float(value)}})

    @property
    def nodes(self):
        return _NodesMock(self._center)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return lambda *a, **kw: None

    def __repr__(self):
        return f"MeshAvatar({self._source}, center={self._center})"


# ============================================================================
# Autres proxies de donnees
# ============================================================================

class _NodesMock:
    """Simule body.nodes[1].coor."""
    def __init__(self, center):
        self._c = list(center)

    def __getitem__(self, idx): return self

    @property
    def coor(self): return self._c


class _MaterialObj:
    def __init__(self, name, materialType='RIGID', density=1000., **props):
        self.name          = name
        self.material_type = materialType
        self.density       = float(density)
        self.props         = dict(props)

    def __repr__(self): return f"Material({self.name})"


class _ModelObj:
    def __init__(self, name, physics='MECAx', element='Rxx2D', dimension=2, **opts):
        self.name      = name
        self.physics   = physics
        self.element   = element
        self.dimension = int(dimension)
        self.opts      = dict(opts)

    def __repr__(self): return f"Model({self.name})"


class _TactBehavObj:
    def __init__(self, name, law, fric=None, **props):
        self.name  = name
        self.law   = law
        self.fric  = fric
        self.props = dict(props)


class _SeeTableObj:
    def __init__(self, CorpsCandidat, candidat, colorCandidat,
                 CorpsAntagoniste, antagoniste, colorAntagoniste,
                 behav, alert=0.1, **kw):
        self.candidate_body       = CorpsCandidat
        self.candidate_contactor  = candidat
        self.candidate_color      = colorCandidat
        self.antagonist_body      = CorpsAntagoniste
        self.antagonist_contactor = antagoniste
        self.antagonist_color     = colorAntagoniste
        self.behav_name = (behav.name if isinstance(behav, _TactBehavObj) else str(behav))
        self.alert      = float(alert)


class _PostproCommandObj:
    def __init__(self, name, step=1, rigid_set=None, **kw):
        self.name      = name
        self.step      = int(step)
        self.rigid_set = rigid_set


class _GranuloRadii:
    """Tableau de rayons retourne par granulo_Random."""
    def __init__(self, nb, rmin, rmax, seed=None):
        self.nb   = nb
        self.rmin = rmin
        self.rmax = rmax
        self.seed = seed
        rng        = np.random.default_rng(seed)
        self._arr  = rng.uniform(rmin, rmax, nb)
        self._granulo_idx: Optional[int] = None

    def __len__(self):              return len(self._arr)
    def __getitem__(self, idx):     return self._arr[idx]
    def __setitem__(self, idx, v):  self._arr[idx] = v

    @property
    def size(self): return self._arr.size


# ============================================================================
# Maconnerie
# ============================================================================

class _BrickObj:
    def __init__(self, kind: str, name: str = 'brick',
                 lx: float = 0.2, ly: float = 0.1, lz: float = 0.05, **kw):
        self._kind = kind
        self._name = str(name or 'brick')
        self._lx   = float(lx) if lx is not None else 0.2
        self._ly   = float(ly) if ly is not None else 0.1
        self._lz   = float(lz) if lz is not None else 0.05

    def rigidBrick(self, center=None, model=None, material=None,
                   color='BLUEx', theta=0., **kw) -> _AvatarObj:
        if self._kind == 'brick2D':
            av = _AvatarObj('rigidPolygon', dict(
                center          = _center(center),
                model           = _name(model),
                material        = _name(material),
                color           = color,
                generation_type = 'regular',
                nb_vertices     = 4,
                lx              = self._lx,
                ly              = self._ly,
                brick_name      = self._name,
            ))
            if theta:
                av._dof_ops.append({'op': 'rotate',
                                    'params': {'description': 'Euler',
                                               'phi': 0., 'theta': float(theta), 'psi': 0.}})
        else:
            av = _AvatarObj('rigidPolyhedron', dict(
                center     = _center(center, dim=3),
                model      = _name(model),
                material   = _name(material),
                color      = color,
                lx         = self._lx,
                ly         = self._ly,
                lz         = self._lz,
                brick_name = self._name,
            ))
        return av

    def rigidBrick3D(self, *a, **kw):
        return self.rigidBrick(*a, **kw)


class _WallObj:
    def __init__(self, kind: str, brick: Optional['_BrickObj'] = None,
                 converter: Optional['Converter'] = None):
        self._kind    = kind
        self._brick   = brick
        self._cv      = converter
        self._nb_rows = 1
        self._joint_h = 0.01
        self._joint_v = 0.01
        self._nb_bricks: Optional[int]   = None
        self._row_length: Optional[float] = None

    def setNumberOfRows(self, n: int):           self._nb_rows   = int(n)
    def setJointThicknessBetweenRows(self, e: float): self._joint_h = float(e)
    def setJointThicknessInRows(self, e: float = None, **kw):
        if e is not None: self._joint_v = float(e)

    def computeHeight(self) -> float:
        by = self._brick._ly if self._brick else 0.1
        return self._nb_rows * (by + self._joint_h)

    def getHeight(self) -> float:    return self.computeHeight()

    def getWidth(self) -> float:
        nb = self._nb_bricks or 5
        bx = self._brick._lx if self._brick else 0.2
        return nb * bx + (nb - 1) * self._joint_v

    def setFirstRowByNumberOfBricks(self, nb: int = 5, **kw):
        self._nb_bricks = int(nb)

    def setFirstRowByLength(self, L: float = 1.0, **kw):
        self._row_length = float(L)
        if self._brick:
            self._nb_bricks = max(1, int(round(float(L) / (self._brick._lx + self._joint_v))))

    def _brick_centers(self, wall_center, offset_rows: bool) -> List[List[float]]:
        nb  = self._nb_bricks or 5
        bx  = self._brick._lx if self._brick else 0.2
        by  = self._brick._ly if self._brick else 0.1
        jv  = self._joint_v
        jh  = self._joint_h
        cx0 = float(wall_center[0])
        cy0 = float(wall_center[1])
        total_w = nb * bx + (nb - 1) * jv
        x0 = cx0 - total_w / 2. + bx / 2.
        y0 = cy0 + by / 2.
        centers = []
        for row in range(self._nb_rows):
            ry     = y0 + row * (by + jh)
            offset = ((bx + jv) / 2.) if (offset_rows and row % 2 == 1) else 0.
            for col in range(nb):
                rx = x0 + col * (bx + jv) + offset
                centers.append([rx, ry])
        return centers

    def _build(self, center, model, material, color: str,
               offset_rows: bool) -> List[_AvatarObj]:
        c       = list(center) if center is not None else [0., 0.]
        centers = self._brick_centers(c, offset_rows)
        avatars = []
        for pos in centers:
            if self._brick:
                av = self._brick.rigidBrick(center=pos, model=model,
                                            material=material, color=color)
            else:
                av = _AvatarObj('rigidPolygon', dict(
                    center=pos, model=_name(model),
                    material=_name(material), color=color,
                    generation_type='regular', nb_vertices=4,
                ))
            avatars.append(av)
        if self._cv is not None:
            pattern_idx = len(self._cv._masonry_patterns)
            self._cv._masonry_patterns.append({
                'pattern_idx':        pattern_idx,
                'kind':               self._kind,
                'brick_name':         self._brick._name if self._brick else '',
                'lx':                 self._brick._lx   if self._brick else 0.2,
                'ly':                 self._brick._ly   if self._brick else 0.1,
                'lz':                 self._brick._lz   if self._brick else 0.05,
                'nb_rows':            self._nb_rows,
                'nb_bricks_per_row':  self._nb_bricks or 5,
                'joint_h':            self._joint_h,
                'joint_v':            self._joint_v,
                'center':             c,
                'model':              _name(model),
                'material':           _name(material),
                'color':              color,
                'avatar_indices':     [],
            })
            for av in avatars:
                av._masonry_idx = pattern_idx
        return avatars

    def buildRigidWall(self, center=None, model=None, material=None,
                       color='BLUEx', **kw) -> List[_AvatarObj]:
        return self._build(center, model, material, color,
                           offset_rows=(self._kind == 'paneresse_double'))

    def buildRigidWallWithoutHalfBricks(self, center=None, model=None,
                                         material=None, color='BLUEx',
                                         **kw) -> List[_AvatarObj]:
        return self._build(center, model, material, color, offset_rows=False)


# ============================================================================
# Analyse statique AST
# ============================================================================

class _AstAnalyzer:
    AVATAR_FUNCS: frozenset = frozenset({
        # Rigides 2D
        'rigidDisk', 'rigidJonc', 'rigidPolygon', 'rigidOvoidPolygon',
        'rigidDiscreteDisk', 'rigidCluster',
        'roughWall', 'fineWall', 'smoothWall', 'granuloRoughWall',
        # Rigides 3D
        'rigidSphere', 'rigidPlan', 'rigidCylinder', 'rigidPolyhedron',
        'roughWall3D', 'granuloRoughWall3D',
        # Maillages / deformables
        'buildMesh2D', 'buildMeshH8', 'buildMeshT3', 'buildMeshQ4',
        'buildMeshT6', 'buildMeshQ8',
        'readMesh', 'readMeshGMSH', 'readMeshVTK',
        'buildMeshedAvatar',
        'surfacicMeshToRigid3D', 'volumicMeshToRigid3D',
        # Avatar vide
        'avatar',
    })

    MASONRY_FUNCS: frozenset = frozenset({'buildRigidWall',
                                          'buildRigidWallWithoutHalfBricks'})

    STD_CONTAINERS: frozenset = frozenset({
        'bodies', 'avatars', 'avs', 'body_list', 'mats', 'mods',
        'tacts', 'svs', 'sees', 'post', 'posts',
    })

    def __init__(self, source: str):
        self._source = source
        self._tree:  Optional[ast.Module] = None
        self.dynamic_vars: Dict[str, Any] = {}
        self.for_loops:    List[dict]     = []
        self.warnings:     List[str]      = []

    def analyze(self) -> None:
        try:
            self._tree = ast.parse(self._source)
        except SyntaxError as exc:
            self.warnings.append(f"Erreur de syntaxe AST : {exc}")
            return
        self._extract_dynamic_vars()
        self._detect_for_loops()

    def _extract_dynamic_vars(self) -> None:
        env: Dict[str, Any] = {}
        for node in ast.iter_child_nodes(self._tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    val = self._safe_eval(node.value, env)
                    if val is not None:
                        env[target.id] = val
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.value is not None:
                    val = self._safe_eval(node.value, env)
                    if val is not None:
                        env[node.target.id] = val
        self.dynamic_vars = {
            k: v for k, v in env.items()
            if isinstance(v, (int, float, str, bool)) and not k.startswith('_')
        }

    def _safe_eval(self, node, env: Dict[str, Any]) -> Any:
        try:
            val = ast.literal_eval(node)
            if isinstance(val, (int, float, str, bool)):
                return val
        except (ValueError, TypeError):
            pass
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                v = self._safe_eval(node.operand, env)
                return -v if isinstance(v, (int, float)) else None
            if isinstance(node.op, ast.UAdd):
                return self._safe_eval(node.operand, env)
        if isinstance(node, ast.BinOp):
            left  = self._safe_eval(node.left,  env)
            right = self._safe_eval(node.right, env)
            if left is not None and right is not None:
                try:
                    op = node.op
                    if isinstance(op, ast.Add):       return left + right
                    if isinstance(op, ast.Sub):       return left - right
                    if isinstance(op, ast.Mult):      return left * right
                    if isinstance(op, ast.Div):       return left / right
                    if isinstance(op, ast.FloorDiv):  return int(left // right)
                    if isinstance(op, ast.Mod):       return left % right
                    if isinstance(op, ast.Pow):       return left ** right
                except (ZeroDivisionError, OverflowError, TypeError):
                    pass
        return None

    def _detect_for_loops(self) -> None:
        for node in ast.iter_child_nodes(self._tree):
            if isinstance(node, ast.For):
                desc = self._analyze_for(node, depth=0)
                if desc is not None:
                    self.for_loops.append(desc)

    def _analyze_for(self, node: ast.For, depth: int) -> Optional[dict]:
        if not isinstance(node.target, ast.Name):
            return None
        loop_var = node.target.id
        range_info    = self._parse_range(node.iter)
        linspace_info = self._parse_linspace(node.iter) if range_info is None else None
        if range_info is None and linspace_info is None:
            return None
        avatar_calls  = list(self._iter_avatar_calls(node.body))
        masonry_calls = list(self._iter_masonry_calls(node.body))
        if not avatar_calls and not masonry_calls:
            return None
        if linspace_info is not None:
            a_expr, b_expr, n_expr = linspace_info
            count    = self._resolve_int(n_expr)
            all_calls = avatar_calls or masonry_calls
            template  = self._build_template(all_calls[0], loop_var)
            return {
                'loop_var': loop_var, 'start_expr': a_expr, 'end_expr': b_expr,
                'step_expr': 'linspace', 'count': count, 'loop_type': 'Générique',
                'geometry': {'linspace': True, 'n_expr': n_expr,
                             'a_expr': a_expr, 'b_expr': b_expr},
                'template_config': template,
                'group_name': self._detect_group(node.body),
            }
        start_expr, end_expr, step_expr = range_info
        inner_for_nodes = [
            n for n in ast.walk(ast.Module(body=node.body, type_ignores=[]))
            if isinstance(n, ast.For) and n is not node
        ]
        inner_desc: Optional[dict] = None
        if inner_for_nodes and depth == 0:
            inner_desc = self._analyze_for(inner_for_nodes[0], depth=1)
        all_calls  = avatar_calls or masonry_calls
        loop_type, geometry = self._classify_geometry(
            loop_var, node.body, all_calls, range_info, inner_desc)
        template   = self._build_template(all_calls[0], loop_var)
        group_name = self._detect_group(node.body)
        count      = self._resolve_int(end_expr)
        return {
            'loop_var': loop_var, 'start_expr': start_expr,
            'end_expr': end_expr, 'step_expr': step_expr,
            'count': count, 'loop_type': loop_type,
            'geometry': geometry, 'template_config': template,
            'group_name': group_name,
        }

    def _parse_range(self, node) -> Optional[Tuple[str, str, str]]:
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == 'range'):
            return None
        args = node.args
        if len(args) == 1: return ('0', self._unparse(args[0]), '1')
        if len(args) == 2: return (self._unparse(args[0]), self._unparse(args[1]), '1')
        if len(args) == 3: return (self._unparse(args[0]), self._unparse(args[1]),
                                   self._unparse(args[2]))
        return None

    def _parse_linspace(self, node) -> Optional[Tuple[str, str, str]]:
        if not isinstance(node, ast.Call):
            return None
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == 'linspace'
                and isinstance(func.value, ast.Name)
                and func.value.id in ('np', 'numpy')):
            return None
        args = node.args
        kws  = {kw.arg: kw.value for kw in node.keywords}
        if len(args) >= 2:
            a_expr = self._unparse(args[0])
            b_expr = self._unparse(args[1])
            n_node = args[2] if len(args) >= 3 else kws.get('num')
            n_expr = self._unparse(n_node) if n_node is not None else '50'
            return (a_expr, b_expr, n_expr)
        if 'start' in kws and 'stop' in kws:
            n_node = kws.get('num')
            n_expr = self._unparse(n_node) if n_node is not None else '50'
            return (self._unparse(kws['start']), self._unparse(kws['stop']), n_expr)
        return None

    def _iter_avatar_calls(self, body: list):
        module_stub = ast.Module(body=body, type_ignores=[])
        for node in ast.walk(module_stub):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in self.AVATAR_FUNCS):
                yield node

    def _iter_masonry_calls(self, body: list):
        module_stub = ast.Module(body=body, type_ignores=[])
        for node in ast.walk(module_stub):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in self.MASONRY_FUNCS):
                yield node

    def _loop_dependent_vars(self, body: list, loop_var: str) -> frozenset:
        depends: set = {loop_var}
        changed = True
        module_stub = ast.Module(body=body, type_ignores=[])
        while changed:
            changed = False
            for node in ast.iter_child_nodes(module_stub):
                if not isinstance(node, ast.Assign):
                    continue
                rhs = self._unparse(node.value)
                if not any(dep in rhs for dep in depends):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id not in depends:
                        depends.add(target.id)
                        changed = True
        return frozenset(depends)

    def _classify_geometry(self, loop_var, body, avatar_calls,
                           range_info, inner_desc) -> Tuple[str, dict]:
        if inner_desc is not None and inner_desc.get('loop_type') in ('Ligne', 'Grille', 'Générique'):
            inner_geom = inner_desc.get('geometry', {})
            return ('Grille', {
                'nx_expr': range_info[1], 'ny_expr': inner_desc['end_expr'],
                'dx_expr': self._extract_step_in_body(loop_var, body, axis=0),
                'dy_expr': inner_geom.get('dy_expr', ''),
                'inner_loop_var': inner_desc['loop_var'],
            })
        cx_src, cy_src = None, None
        for call in avatar_calls:
            ce = self._extract_center_exprs(call)
            if ce is not None:
                cx_src, cy_src = ce
                break
        if cx_src is None:
            return ('Générique', {})
        dep_vars = self._loop_dependent_vars(body, loop_var)
        trig_x = self._expr_uses_trig_of(cx_src, dep_vars)
        trig_y = self._expr_uses_trig_of(cy_src, dep_vars)
        if trig_x or trig_y:
            R_expr  = self._extract_trig_amplitude(cx_src, cy_src)
            offsets = self._extract_trig_offsets(cx_src, cy_src, dep_vars)
            r_grows = (any(v in cx_src for v in dep_vars) and not trig_x) or \
                      (any(v in cy_src for v in dep_vars) and not trig_y)
            lt = 'Spirale' if r_grows else 'Cercle'
            return (lt, {'R_expr': R_expr or '', 'N_expr': range_info[1],
                         'cx_src': cx_src, 'cy_src': cy_src, **offsets})
        var_in_x = loop_var in cx_src
        var_in_y = loop_var in cy_src
        if var_in_x or var_in_y:
            dx_expr = self._extract_linear_step(cx_src, loop_var) if var_in_x else '0'
            dy_expr = self._extract_linear_step(cy_src, loop_var) if var_in_y else '0'
            direction = ('x' if var_in_x and not var_in_y else
                         'y' if var_in_y and not var_in_x else 'diag')
            return ('Ligne', {'direction': direction, 'dx_expr': dx_expr,
                              'dy_expr': dy_expr, 'cx_src': cx_src, 'cy_src': cy_src})
        return ('Générique', {'cx_src': cx_src, 'cy_src': cy_src})

    def _extract_center_exprs(self, call_node) -> Optional[Tuple[str, str]]:
        for kw in call_node.keywords:
            if kw.arg == 'center':
                v = kw.value
                if isinstance(v, ast.List) and len(v.elts) >= 2:
                    return (self._unparse(v.elts[0]), self._unparse(v.elts[1]))
        return None

    def _expr_uses_trig_of(self, expr: str, dep_vars) -> bool:
        if 'cos' not in expr and 'sin' not in expr:
            return False
        return any(v in expr for v in dep_vars)

    def _extract_trig_amplitude(self, cx_src: str, cy_src: str) -> Optional[str]:
        for expr in (cx_src, cy_src):
            if 'cos' not in expr and 'sin' not in expr:
                continue
            try:
                tree = ast.parse(expr, mode='eval')
                for node in ast.walk(tree):
                    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                        for a_side, b_side in ((node.left, node.right),
                                               (node.right, node.left)):
                            if not isinstance(b_side, ast.Call):
                                continue
                            func = b_side.func
                            fname = (func.attr if isinstance(func, ast.Attribute)
                                     else func.id if isinstance(func, ast.Name) else None)
                            if fname in ('cos', 'sin'):
                                return self._unparse(a_side)
            except Exception:
                pass
        return None

    def _extract_trig_offsets(self, cx_src: str, cy_src: str, dep_vars) -> dict:
        if isinstance(dep_vars, str):
            dep_vars = {dep_vars}
        result: dict = {}
        for key, expr in (('offset_x', cx_src), ('offset_y', cy_src)):
            if 'cos' not in expr and 'sin' not in expr:
                continue
            try:
                tree = ast.parse(expr, mode='eval')
                for node in ast.walk(tree):
                    if isinstance(node, ast.BinOp) and isinstance(
                        node.op, (ast.Add, ast.Sub)
                    ):
                        for side in (node.left, node.right):
                            s = self._unparse(side)
                            if ('cos' not in s and 'sin' not in s
                                    and not any(v in s for v in dep_vars)):
                                result[key] = s
                                break
            except Exception:
                pass
        return result

    def _extract_linear_step(self, expr: str, loop_var: str) -> str:
        try:
            tree = ast.parse(expr, mode='eval')
            for node in ast.walk(tree):
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                    ls, rs = self._unparse(node.left), self._unparse(node.right)
                    if ls == loop_var: return rs
                    if rs == loop_var: return ls
        except Exception:
            pass
        return ''

    def _extract_step_in_body(self, loop_var: str, body: list, axis: int = 0) -> str:
        for call in self._iter_avatar_calls(body):
            ce = self._extract_center_exprs(call)
            if ce is not None:
                step = self._extract_linear_step(ce[axis], loop_var)
                if step:
                    return step
        return ''

    def _build_template(self, call_node, loop_var: str) -> dict:
        cfg: dict = {}
        if isinstance(call_node.func, ast.Attribute):
            cfg['avatar_type'] = call_node.func.attr
        params: dict = {}
        for kw in call_node.keywords:
            if kw.arg is None:
                continue
            literal = self._try_literal(kw.value)
            if literal is not None:
                params[kw.arg] = {'value': literal, 'is_expr': False}
            else:
                expr = self._unparse(kw.value)
                params[kw.arg] = {'expr': expr, 'uses_loop_var': loop_var in expr, 'is_expr': True}
        cfg['params'] = params
        return cfg

    def _detect_group(self, body: list) -> Optional[str]:
        module_stub = ast.Module(body=body, type_ignores=[])
        for node in ast.walk(module_stub):
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                if name not in self.STD_CONTAINERS:
                    return name
            elif (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
                c = node.value
                if (isinstance(c.func, ast.Attribute)
                        and c.func.attr in ('addAvatar', 'append', 'extend')
                        and isinstance(c.func.value, ast.Name)):
                    name = c.func.value.id
                    if name not in self.STD_CONTAINERS:
                        return name
        return None

    def _resolve_int(self, expr: str) -> Optional[int]:
        try:
            val = ast.literal_eval(expr)
            if isinstance(val, (int, float)): return int(val)
        except (ValueError, TypeError): pass
        try:
            val = eval(expr, {'__builtins__': {}}, dict(self.dynamic_vars))
            if isinstance(val, (int, float)): return int(val)
        except Exception: pass
        return None

    def _resolve_float(self, expr: str) -> Optional[float]:
        if not expr: return None
        try:
            val = ast.literal_eval(expr)
            if isinstance(val, (int, float)): return float(val)
        except (ValueError, TypeError): pass
        try:
            val = eval(expr, {'__builtins__': {}}, dict(self.dynamic_vars))
            if isinstance(val, (int, float)): return float(val)
        except Exception: pass
        return None

    def _try_literal(self, node) -> Any:
        try: return ast.literal_eval(node)
        except (ValueError, TypeError): return None

    @staticmethod
    def _unparse(node) -> str:
        try:
            return ast.unparse(node)
        except AttributeError:
            pass
        try:
            import astunparse  # type: ignore[import]
            return astunparse.unparse(node).strip()
        except Exception:
            return '<expr>'


# ============================================================================
# Proxies range / numpy pour suivi runtime des boucles
# ============================================================================

class _TrackedRange:
    def __init__(self, converter: 'Converter', r: range):
        self._cv = converter
        self._r  = r

    def __iter__(self):
        loop_idx = self._cv._push_loop(len(self._r))
        try:
            for val in self._r:
                yield val
        finally:
            self._cv._pop_loop(loop_idx)

    def __len__(self):              return len(self._r)
    def __getitem__(self, idx):     return self._r[idx]
    def __bool__(self):             return bool(self._r)
    def __contains__(self, item):   return item in self._r


class _RangeProxy:
    def __init__(self, converter: 'Converter'):
        self._cv = converter

    def __call__(self, *args):
        return _TrackedRange(self._cv, range(*args))

    def __getattr__(self, name):
        return getattr(range, name)


class _TrackedLinspace:
    def __init__(self, converter: 'Converter', arr):
        self._cv  = converter
        self._arr = arr

    def __iter__(self):
        loop_idx = self._cv._push_loop(len(self._arr))
        try:
            for val in self._arr:
                yield val
        finally:
            self._cv._pop_loop(loop_idx)

    def __len__(self):              return len(self._arr)
    def __getitem__(self, idx):     return self._arr[idx]
    def __array__(self, *a, **kw):  return np.asarray(self._arr)

    def __getattr__(self, name):
        return getattr(self._arr, name)


class _NpProxy:
    def __init__(self, converter: 'Converter'):
        self._cv = converter

    def linspace(self, start, stop, num=50, *args, **kw):
        arr = np.linspace(start, stop, int(num), *args, **kw)
        return _TrackedLinspace(self._cv, arr)

    def __getattr__(self, name):
        return getattr(np, name)


# ============================================================================
# Conteneurs generiques
# ============================================================================

class _Container:
    def __init__(self, kind=''):
        self._items: List[Any] = []
        self._kind = kind

    def _add(self, item): self._items.append(item)

    def addAvatar(self, item):    self._add(item)
    def addMaterial(self, *args):
        for a in args: self._add(a)
    def addModel(self, item):     self._add(item)
    def addBehav(self, item):     self._add(item)
    def addSeeTable(self, item):  self._add(item)
    def addCommand(self, item):   self._add(item)

    def __iadd__(self, item):
        self._add(item)
        return self

    def __iter__(self):   return iter(self._items)
    def __len__(self):    return len(self._items)
    def __repr__(self):   return f"Container({self._kind}, {len(self._items)} items)"


class _SilentModule:
    def __init__(self, name):     self._name = name
    def __getattr__(self, k):     return _SilentModule(f"{self._name}.{k}")
    def __call__(self, *a, **kw): return _SilentModule(f"{self._name}()")
    def __iadd__(self, o):        return self
    def show(self, *a, **kw):     pass
    def savefig(self, *a, **kw):  pass


# Alias pour eviter toute confusion avec les vraies listes retournees
_AVATAR_TYPES = (_AvatarObj, _MeshAvatarObj, _EmptyAvatarObj)


class _TrackedContainer(_Container):
    """
    Conteneur bodies enrichi : tague chaque avatar avec son indice de boucle
    et met a jour les masonry_patterns.
    Accepte : _AvatarObj, _MeshAvatarObj, _EmptyAvatarObj, et listes de briques.
    """

    def __init__(self, converter: 'Converter'):
        super().__init__('bodies')
        self._cv = converter

    def _register(self, item) -> None:
        if not isinstance(item, _AVATAR_TYPES):
            return
        body_idx = len(self._items)
        self._items.append(item)

        active = self._cv._active_loop_idx
        if active is not None:
            item._loop_idx = active
            self._cv._loop_captures[active]['avatar_indices'].append(body_idx)

        masonry_idx = getattr(item, '_masonry_idx', None)
        if (masonry_idx is not None
                and masonry_idx < len(self._cv._masonry_patterns)):
            self._cv._masonry_patterns[masonry_idx]['avatar_indices'].append(body_idx)

    def addAvatar(self, item):
        if isinstance(item, list):
            for av in item:
                self._register(av)
        elif isinstance(item, _AVATAR_TYPES):
            self._register(item)

    def __iadd__(self, item):
        self.addAvatar(item)
        return self


# ============================================================================
# Module mock pylmgc90.pre  — version amelioree
# ============================================================================

class _MockPre:
    """
    Remplace pylmgc90.pre pendant l'execution du script.
    """

    def __init__(self, converter: 'Converter'):
        self._cv = converter

    # ── Conteneurs vides ─────────────────────────────────────────────────────

    def avatars(self):          return _Container('avatars')
    def materials(self):        return _Container('materials')
    def models(self):           return _Container('models')
    def tact_behavs(self):      return _Container('tact_behavs')
    def see_tables(self):       return _Container('see_tables')
    def postpro_commands(self): return _Container('postpro_commands')

    # ── Materiaux ─────────────────────────────────────────────────────────────

    def material(self, name, materialType='RIGID', density=1000., **kw):
        obj = _MaterialObj(name, materialType, density, **kw)
        self._cv._materials[name] = obj
        return obj

    # ── Modeles ───────────────────────────────────────────────────────────────

    def model(self, name, physics='MECAx', element='Rxx2D', dimension=2, **kw):
        obj = _ModelObj(name, physics, element, dimension, **kw)
        self._cv._models[name] = obj
        return obj

    # ── Utilitaire interne ────────────────────────────────────────────────────

    def _make_avatar(self, avatar_type: str, **kw) -> _AvatarObj:
        kw  = _normalize_kwargs(kw)
        obj = _AvatarObj(avatar_type, kw)
        self._cv._avatar_pool.append(obj)
        return obj

    # ── Corps rigides 2D ─────────────────────────────────────────────────────

    def rigidDisk(self, r=0.1, center=None, model=None, material=None,
                  color='BLUEx', is_Hollow=False, **kw):
        av = self._make_avatar('rigidDisk', r=float(r),
                               center=_center(center), model=_name(model),
                               material=_name(material), color=color)
        if is_Hollow:
            av._kwargs['is_Hollow'] = True
        return av

    def rigidJonc(self, axe1=1., axe2=0.1, center=None, model=None,
                  material=None, color='BLUEx', **kw):
        return self._make_avatar('rigidJonc',
                                 axe1=float(axe1), axe2=float(axe2),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def rigidPolygon(self, model=None, material=None, center=None, color='BLUEx',
                     theta=0., radius=None, generation_type='regular',
                     nb_vertices=None, vertices=None, **kw):
        kw_av = dict(center=_center(center), model=_name(model),
                     material=_name(material), color=color,
                     generation_type=generation_type)
        if radius is not None:       kw_av['radius']      = float(radius)
        if theta:                    kw_av['theta']        = float(theta)
        if nb_vertices is not None:  kw_av['nb_vertices']  = int(nb_vertices)
        if vertices is not None:     kw_av['vertices']     = _to_serial(vertices)
        return self._make_avatar('rigidPolygon', **kw_av)

    def rigidOvoidPolygon(self, ra=1., rb=1., nb_vertices=8, center=None,
                          model=None, material=None, color='BLUEx', **kw):
        return self._make_avatar('rigidOvoidPolygon',
                                 ra=float(ra), rb=float(rb),
                                 nb_vertices=int(nb_vertices),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def rigidDiscreteDisk(self, r=0.1, center=None, model=None, material=None,
                          color='BLUEx', **kw):
        return self._make_avatar('rigidDiscreteDisk', r=float(r),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def rigidCluster(self, nb_disk=3, r=0.1, center=None, model=None,
                     material=None, color='BLUEx', **kw):
        return self._make_avatar('rigidCluster',
                                 nb_disk=int(nb_disk), r=float(r),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    # ── Murs 2D — signatures corrigees (l=longueur, r=rayon disques, h=hauteur) ──

    def roughWall(self, l=1., r=0.1, center=None, model=None,
                  material=None, color='BLUEx', nb_vertex=10, **kw):
        return self._make_avatar('roughWall',
                                 l=float(l), r=float(r), nb_vertex=int(nb_vertex),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def fineWall(self, l=1., r=0.1, center=None, model=None,
                 material=None, color='BLUEx', nb_vertex=10, **kw):
        return self._make_avatar('fineWall',
                                 l=float(l), r=float(r), nb_vertex=int(nb_vertex),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def smoothWall(self, l=1., h=0.1, center=None, model=None,
                   material=None, color='BLUEx', nb_polyg=10, **kw):
        return self._make_avatar('smoothWall',
                                 l=float(l), h=float(h), nb_polyg=int(nb_polyg),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def granuloRoughWall(self, l=1., rmin=0.05, rmax=0.1, center=None,
                         model=None, material=None, color='BLUEx',
                         nb_vertex=10, **kw):
        return self._make_avatar('granuloRoughWall',
                                 l=float(l), rmin=float(rmin), rmax=float(rmax),
                                 nb_vertex=int(nb_vertex),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    # ── Corps rigides 3D ─────────────────────────────────────────────────────

    def rigidSphere(self, r=0.1, center=None, model=None, material=None,
                    color='BLUEx', **kw):
        return self._make_avatar('rigidSphere', r=float(r),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color)

    def rigidPlan(self, center=None, axe1=1., axe2=1., axe3=0.05,
                  model=None, material=None, color='BLUEx', **kw):
        """Plan rigide 3D. axe1/axe2/axe3 = demi-dimensions du plan rectangulaire."""
        return self._make_avatar('rigidPlan',
                                 axe1=float(axe1), axe2=float(axe2), axe3=float(axe3),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color)

    def rigidCylinder(self, r=0.5, h=1., center=None, model=None,
                      material=None, color='BLUEx', **kw):
        return self._make_avatar('rigidCylinder',
                                 r=float(r), h=float(h),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color)

    def rigidPolyhedron(self, model=None, material=None, center=None,
                        color='BLUEx', vertices=None, faces=None,
                        nb_vertices=None, radius=None,
                        generation_type='regular', **kw):
        kw_av = dict(center=_center(center, dim=3), model=_name(model),
                     material=_name(material), color=color,
                     generation_type=generation_type)
        if vertices    is not None: kw_av['vertices']    = _to_serial(vertices)
        if faces       is not None: kw_av['faces']       = _to_serial(faces)
        if nb_vertices is not None: kw_av['nb_vertices'] = int(nb_vertices)
        if radius      is not None: kw_av['radius']      = float(radius)
        return self._make_avatar('rigidPolyhedron', **kw_av)

    def roughWall3D(self, lx=1., ly=1., r=0.05, center=None, model=None,
                    material=None, color='BLUEx', **kw):
        return self._make_avatar('roughWall3D',
                                 lx=float(lx), ly=float(ly), r=float(r),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color)

    def granuloRoughWall3D(self, lx=1., ly=1., rmin=0.02, rmax=0.05,
                           center=None, model=None, material=None,
                           color='BLUEx', **kw):
        return self._make_avatar('granuloRoughWall3D',
                                 lx=float(lx), ly=float(ly),
                                 rmin=float(rmin), rmax=float(rmax),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color)

    # ── Avatar vide (contacteurs manuels) ─────────────────────────────────────

    def avatar(self, dimension=2) -> _EmptyAvatarObj:
        obj = _EmptyAvatarObj(dimension=int(dimension))
        self._cv._avatar_pool.append(obj)
        return obj

    def node(self, coor=None, number=1) -> _NodeObj:
        return _NodeObj(coor=coor, number=number)

    def rigid2d(self) -> _BulkObj: return _BulkObj('rigid2d')
    def rigid3d(self) -> _BulkObj: return _BulkObj('rigid3d')

    # ── Maillages 2D ─────────────────────────────────────────────────────────

    def _make_mesh(self, source: str, params: dict) -> _MeshAvatarObj:
        obj = _MeshAvatarObj(source, params, self._cv)
        self._cv._avatar_pool.append(obj)
        return obj

    def buildMesh2D(self, mesh_type='T3xxx', x0=0., y0=0.,
                    lx=1., ly=1., nx=4, ny=4, **kw):
        """Maillage 2D structure (triangles ou quads)."""
        return self._make_mesh('buildMesh2D', {
            'source_type': 'built2D', 'mesh_type': mesh_type,
            'x0': float(x0), 'y0': float(y0),
            'lx': float(lx), 'ly': float(ly),
            'nx': int(nx),   'ny': int(ny),
            'center': [float(x0) + float(lx)/2., float(y0) + float(ly)/2.],
        })

    def buildMeshT3(self, x0=0., y0=0., lx=1., ly=1., nx=4, ny=4, **kw):
        return self.buildMesh2D('T3xxx', x0, y0, lx, ly, nx, ny)

    def buildMeshQ4(self, x0=0., y0=0., lx=1., ly=1., nx=4, ny=4, **kw):
        return self.buildMesh2D('Q4xxx', x0, y0, lx, ly, nx, ny)

    def buildMeshT6(self, x0=0., y0=0., lx=1., ly=1., nx=4, ny=4, **kw):
        return self.buildMesh2D('T6xxx', x0, y0, lx, ly, nx, ny)

    def buildMeshQ8(self, x0=0., y0=0., lx=1., ly=1., nx=4, ny=4, **kw):
        return self.buildMesh2D('Q8xxx', x0, y0, lx, ly, nx, ny)

    # ── Maillages 3D ─────────────────────────────────────────────────────────

    def buildMeshH8(self, x0=0., y0=0., z0=0.,
                    lx=1., ly=1., lz=1., nx=2, ny=2, nz=2, **kw):
        """Volume 3D en hexaedres H8."""
        return self._make_mesh('buildMeshH8', {
            'source_type': 'builtH8',
            'x0': float(x0), 'y0': float(y0), 'z0': float(z0),
            'lx': float(lx), 'ly': float(ly), 'lz': float(lz),
            'nx': int(nx),   'ny': int(ny),   'nz': int(nz),
            'center': [float(x0)+float(lx)/2.,
                       float(y0)+float(ly)/2.,
                       float(z0)+float(lz)/2.],
            'dim': 3,
        })

    # ── Lecture de maillages exterieurs ──────────────────────────────────────

    def readMesh(self, filename=None, dim=2, **kw):
        """Lit un maillage depuis un fichier (format LMGC90 natif)."""
        fname = str(filename) if filename is not None else ''
        return self._make_mesh('readMesh', {
            'source_type': 'file', 'mesh_file': fname,
            'dim': int(dim), 'format': 'lmgc90',
        })

    def readMeshGMSH(self, filename=None, dim=2, **kw):
        """Lit un maillage au format GMSH (.msh)."""
        fname = str(filename) if filename is not None else ''
        return self._make_mesh('readMeshGMSH', {
            'source_type': 'file', 'mesh_file': fname,
            'dim': int(dim), 'format': 'gmsh',
        })

    def readMeshVTK(self, filename=None, dim=2, **kw):
        """Lit un maillage au format VTK."""
        fname = str(filename) if filename is not None else ''
        return self._make_mesh('readMeshVTK', {
            'source_type': 'file', 'mesh_file': fname,
            'dim': int(dim), 'format': 'vtk',
        })

    # ── Construction de corps deformable ou rigide issu de maillage ───────────

    def buildMeshedAvatar(self, mesh=None, model=None, material=None,
                          color='BLUEx', **kw):
        """Corps deformable (FEM) construit depuis un objet maillage."""
        params: dict = {'source_type': 'meshed_avatar', 'deformable': True,
                        'color': color}
        if isinstance(mesh, _MeshAvatarObj):
            params['mesh_source']  = mesh._source
            params['mesh_params']  = dict(mesh._mesh_params)
            params['center']       = mesh._center
            params['dim']          = len(mesh._center)
        params['model']    = _name(model)
        params['material'] = _name(material)
        obj = _MeshAvatarObj('buildMeshedAvatar', params, self._cv)
        obj._model    = _name(model)
        obj._material = _name(material)
        obj._color    = color
        obj._kwargs.update({'model': obj._model, 'material': obj._material, 'color': color})
        if isinstance(mesh, _MeshAvatarObj):
            obj._center = mesh._center
            obj._kwargs['center'] = obj._center
        self._cv._avatar_pool.append(obj)
        return obj

    def surfacicMeshToRigid3D(self, mesh=None, model=None, material=None,
                               color='BLUEx', **kw):
        """Convertit un maillage surfacique en corps rigide 3D."""
        params: dict = {'source_type': 'surfacicToRigid3D', 'deformable': False,
                        'dim': 3, 'color': color}
        if isinstance(mesh, _MeshAvatarObj):
            params['mesh_source'] = mesh._source
            params['mesh_params'] = dict(mesh._mesh_params)
            params['center']      = mesh._center
        params['model']    = _name(model)
        params['material'] = _name(material)
        obj = _MeshAvatarObj('surfacicMeshToRigid3D', params, self._cv)
        obj._model    = _name(model)
        obj._material = _name(material)
        obj._color    = color
        obj._kwargs.update({'model': obj._model, 'material': obj._material, 'color': color})
        if isinstance(mesh, _MeshAvatarObj):
            obj._center = mesh._center
            obj._kwargs['center'] = obj._center
        self._cv._avatar_pool.append(obj)
        return obj

    def volumicMeshToRigid3D(self, mesh=None, model=None, material=None,
                              color='BLUEx', **kw):
        """Convertit un maillage volumique en corps rigide 3D."""
        params: dict = {'source_type': 'volumicToRigid3D', 'deformable': False,
                        'dim': 3, 'color': color}
        if isinstance(mesh, _MeshAvatarObj):
            params['mesh_source'] = mesh._source
            params['mesh_params'] = dict(mesh._mesh_params)
            params['center']      = mesh._center
        params['model']    = _name(model)
        params['material'] = _name(material)
        obj = _MeshAvatarObj('volumicMeshToRigid3D', params, self._cv)
        obj._model    = _name(model)
        obj._material = _name(material)
        obj._color    = color
        obj._kwargs.update({'model': obj._model, 'material': obj._material, 'color': color})
        if isinstance(mesh, _MeshAvatarObj):
            obj._center = mesh._center
            obj._kwargs['center'] = obj._center
        self._cv._avatar_pool.append(obj)
        return obj

    # ── Maconnerie ────────────────────────────────────────────────────────────

    def brick2D(self, name='brick', lx=0.2, ly=0.1, **kw):
        return _BrickObj('brick2D', name=name, lx=lx, ly=ly)

    def brick3D(self, name='brick', lx=0.2, ly=0.1, lz=0.05, **kw):
        return _BrickObj('brick3D', name=name, lx=lx, ly=ly, lz=lz)

    def paneresse_simple(self, brick=None, *a, **kw):
        return _WallObj('paneresse_simple', brick=brick, converter=self._cv)

    def paneresse_double(self, brick=None, *a, **kw):
        return _WallObj('paneresse_double', brick=brick, converter=self._cv)

    # ── Contact / Visibilite / Postpro ────────────────────────────────────────

    def tact_behav(self, name, law, fric=None, **kw):
        obj = _TactBehavObj(name, law, fric, **kw)
        self._cv._tact_behavs[name] = obj
        return obj

    def see_table(self, CorpsCandidat, candidat, colorCandidat,
                  CorpsAntagoniste, antagoniste, colorAntagoniste,
                  behav, alert=0.1, **kw):
        obj = _SeeTableObj(CorpsCandidat, candidat, colorCandidat,
                           CorpsAntagoniste, antagoniste, colorAntagoniste,
                           behav, alert)
        self._cv._see_tables.append(obj)
        return obj

    def postpro_command(self, name, step=1, rigid_set=None, **kw):
        obj = _PostproCommandObj(name, step, rigid_set)
        self._cv._postpro_cmds.append(obj)
        return obj

    # ── Granulometrie ─────────────────────────────────────────────────────────

    def granulo_Random(self, nb, rmin=None, rmax=None,
                       r_min=None, r_max=None, seed=None, **kw):
        rmin = rmin if rmin is not None else r_min
        rmax = rmax if rmax is not None else r_max
        obj  = _GranuloRadii(int(nb), float(rmin), float(rmax), seed)
        idx  = len(self._cv._granulo_pairs)
        obj._granulo_idx = idx
        self._cv._granulo_pairs.append({
            'nb': int(nb), 'rmin': float(rmin), 'rmax': float(rmax),
            'seed': seed, 'nb_particles': None,
            'container_type': None, 'container_params': {},
        })
        return obj

    def _deposit(self, container_type: str, radii, params: dict):
        nb  = len(radii) if hasattr(radii, '__len__') else int(radii.nb)
        rng = np.random.default_rng(None)
        coords = rng.uniform(0, 1, (nb, 2))
        idx = getattr(radii, '_granulo_idx', None)
        if idx is not None and idx < len(self._cv._granulo_pairs):
            self._cv._granulo_pairs[idx].update({
                'nb_particles': nb, 'container_type': container_type,
                'container_params': params,
            })
        else:
            self._cv._granulo_pairs.append({
                'nb': nb, 'rmin': 0., 'rmax': 0., 'seed': None,
                'nb_particles': nb, 'container_type': container_type,
                'container_params': params,
            })
        return nb, coords

    def depositInBox2D(self, radii=None, lx=4., ly=4., **kw):
        return self._deposit('Box2D', radii, {'lx': float(lx), 'ly': float(ly)})

    def depositInDisk2D(self, radii=None, r=2., **kw):
        return self._deposit('Disk2D', radii, {'r': float(r)})

    def depositInCouette2D(self, radii=None, rint=1., rext=3., **kw):
        return self._deposit('Couette2D', radii, {'rint': float(rint), 'rext': float(rext)})

    def depositInDrum2D(self, radii=None, r=2., **kw):
        return self._deposit('Drum2D', radii, {'r': float(r)})

    def depositInBox3D(self, radii=None, lx=4., ly=4., lz=4., **kw):
        return self._deposit('Box3D', radii,
                             {'lx': float(lx), 'ly': float(ly), 'lz': float(lz)})

    def depositInSphere3D(self, radii=None, r=2., **kw):
        return self._deposit('Sphere3D', radii, {'r': float(r)})

    def depositInCylinder3D(self, radii=None, r=2., **kw):
        return self._deposit('Cylinder3D', radii, {'r': float(r)})

    # ── writeDatbox — capture de la dimension ─────────────────────────────────

    def writeDatbox(self, dim=2, mats=None, mods=None, bodies=None,
                    tacts=None, sees=None, post=None, datbox_path='DATBOX', **kw):
        if isinstance(dim, int):
            self._cv._dimension = int(dim)

    # ── Divers ────────────────────────────────────────────────────────────────

    def visuAvatars(self, *a, **kw):      pass
    def saveAvatarSet(self, *a, **kw):    pass
    def loadAvatarSet(self, *a, **kw):    return _Container('avatars')
    def mzToolBox(self, *a, **kw):        return _SilentModule('mzToolBox')

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        def _stub(*a, **kw): return _SilentModule(name)
        return _stub


# ============================================================================
# Utilitaires
# ============================================================================

def _center(c, dim=None):
    if c is None:
        return [0., 0.] if (dim or 2) == 2 else [0., 0., 0.]
    if hasattr(c, 'tolist'):
        return c.tolist()
    return [float(x) for x in c]


def _name(obj) -> str:
    if obj is None:
        return ''
    if isinstance(obj, (_MaterialObj, _ModelObj)):
        return obj.name
    return str(obj)


def _to_serial(obj):
    if obj is None:                                 return None
    if hasattr(obj, 'tolist'):                      return obj.tolist()
    if isinstance(obj, (list, tuple)):              return [_to_serial(x) for x in obj]
    if isinstance(obj, dict):                       return {k: _to_serial(v) for k, v in obj.items()}
    if isinstance(obj, (int, float, str, bool)):    return obj
    return str(obj)


def _normalize_kwargs(kw: dict) -> dict:
    return {k: _to_serial(v) for k, v in kw.items()}


def _rotate_vertices_2d(vertices, theta_deg: float):
    th = math.radians(theta_deg)
    ct, st = math.cos(th), math.sin(th)
    return [[ct*float(v[0]) - st*float(v[1]),
             st*float(v[0]) + ct*float(v[1])] for v in vertices]


def _default_preferences() -> dict:
    return {
        'default_project_path': None, 'unit_system': 'SI',
        'auto_save': True, 'auto_save_interval': 300,
        'backup_enabled': True, 'recent_projects': [],
        'max_recent_projects': 10, 'show_granulo_individually': True,
        'create_pylmgc_on_generate': True, 'script_use_loop': True,
    }


# ============================================================================
# Convertisseur principal
# ============================================================================

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


# ============================================================================
# Interface en ligne de commande
# ============================================================================

def convert(script_path: Path, output_path: Path, verbose: bool = True) -> bool:
    if not script_path.exists():
        print(f"Fichier introuvable : {script_path}", file=sys.stderr)
        return False
    if verbose:
        print(f"Conversion de : {script_path}")
        print(f"Destination   : {output_path}")
    cv      = Converter(script_path)
    cv.run()
    project = cv.to_lmgc90_dict()
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(project, f, indent=2, ensure_ascii=False)
    if verbose:
        _print_report(cv, project)
    return True


def _print_report(cv: Converter, project: dict) -> None:
    def _count_origin(avatars, origin):
        return sum(1 for a in avatars if a.get('__origin') == origin)

    avs  = project['avatars']
    n_m  = _count_origin(avs, 'manual')
    n_l  = _count_origin(avs, 'loop')
    n_ms = sum(1 for a in avs if a.get('type') == 'mesh')
    n_ea = sum(1 for a in avs if a.get('type') == 'emptyAvatar')
    n_ma = _count_origin(avs, 'masonry')

    print(f"\nResume :")
    print(f"  Dimension      : {project['dimension']}D")
    print(f"  Materiaux      : {len(project['materials'])}")
    print(f"  Modeles        : {len(project['models'])}")
    print(f"  Avatars        : {len(avs)}"
          f"  (manuel={n_m}, boucle={n_l}, maille={n_ms}, "
          f"emptyAvatar={n_ea}, maconnerie={n_ma})")
    print(f"  Lois contact   : {len(project['contact_laws'])}")
    print(f"  Visibilites    : {len(project['visibility_rules'])}")
    print(f"  Operations DOF : {len(project['operations'])}")
    print(f"  Granulo        : {len(project['granulo_generations'])}")
    print(f"  PostPro        : {len(project['postpro_creations'])}")
    print(f"  Maconnerie     : {len(project['masonry_patterns'])} pattern(s)")

    forl  = project['for_loops']
    if forl:
        print(f"\nBoucles ({len(forl)}) :")
        for i, fl in enumerate(forl):
            n = fl.get('generated_indices', [])
            print(f"  [{i}] for {fl['loop_var']} in "
                  f"range({fl['start_expr']},{fl['end_expr']}) "
                  f"— {len(n)} avatars")

    dv = project['dynamic_vars']
    if dv:
        print(f"\nVariables dynamiques ({len(dv)}) :")
        for k, v in list(dv.items())[:15]:
            print(f"  {k} = {v!r}")
        if len(dv) > 15:
            print(f"  ... ({len(dv)-15} de plus)")

    if cv._warnings:
        print(f"\nAvertissements ({len(cv._warnings)}) :")
        for w in cv._warnings[:10]:
            print(f"  • {w.split(chr(10))[0]}")

    print(f"\nFichier ecrit.")


def main():
    parser = argparse.ArgumentParser(
        description='Convertit un script pylmgc90 en projet .lmgc90 pour LMGC90_GUI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('script', type=Path, help='Fichier Python source (.py)')
    parser.add_argument('-o', '--output', type=Path, default=None,
                        help='Fichier de sortie (.lmgc90).')
    parser.add_argument('--check', action='store_true',
                        help='Verifie sans ecrire le fichier.')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Sortie minimale.')

    args   = parser.parse_args()
    script = args.script.resolve()
    output = args.output or script.with_suffix('.lmgc90')

    if args.check:
        cv = Converter(script)
        cv.run()
        project = cv.to_lmgc90_dict()
        print(json.dumps(project, indent=2, ensure_ascii=False))
        return

    ok = convert(script, output, verbose=not args.quiet)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()