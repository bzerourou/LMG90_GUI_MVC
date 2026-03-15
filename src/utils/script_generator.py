"""
Générateur de scripts Python pour LMGC90.
Permet de créer des scripts reproductibles depuis l'état du projet.
"""

from pathlib import Path
from typing import TextIO

from ..controllers.project_controller import ProjectController
from ..core.models import (
    MaterialType, AvatarType, AvatarOrigin, ContactLawType
)


# Correspondance conteneur → fonction de dépôt pylmgc90
_DEPOSIT_FUNC = {
    "Box2D":      "depositInBox2D",
    "Disk2D":     "depositInDisk2D",
    "Couette2D":  "depositInCouette2D",
    "Drum2D":     "depositInDrum2D",
    "Box3D":      "depositInBox3D",
    "Sphere3D":   "depositInSphere3D",
    "Cylinder3D": "depositInCylinder3D",
}

# Correspondance conteneur → clés de paramètres attendus par la fonction de dépôt
_DEPOSIT_PARAMS = {
    "Box2D":      ["lx", "ly"],
    "Disk2D":     ["r"],
    "Couette2D":  ["rint", "rext"],
    "Drum2D":     ["r"],
    "Box3D":      ["lx", "ly", "lz"],
    "Sphere3D":   ["r"],
    "Cylinder3D": ["r"],
}

_MASONRY_WALL_KEYS = {'l', 'h', 'lz', 'brick_name'}

class ScriptGenerator:
    """Génère un script Python reproductible du projet"""
    
    def __init__(self, controller: ProjectController):
        self.controller = controller
        self.state = controller.state
        
    @property
    def _use_loop(self) -> bool :
        """True -> boucles compactes (script court) ; False -> element par element."""
        return bool(getattr(
            getattr(self.state, 'preferences', None),
            'script_use_loop', True
        ))
    def generate(self, output_path: Path) -> None:
        """Génère le script complet"""
        with open(output_path, 'w', encoding='utf-8') as f:
            self._write_header(f)
            self._write_imports(f)
            self._write_dynamic_vars(f)
            self._write_containers(f)
            self._write_materials(f)
            self._write_models(f)
            self._write_avatars_manual(f)
            self._write_for_loops(f)
            self._write_loops(f)
            self._write_granulo(f)
            self._write_contact_laws(f)
            self._write_visibility(f)
            self._write_dof_operations(f)
            self._write_postpro(f)
            self._write_datbox(f)
    # ── En-tête ───────────────────────────────────────────────────────────────
    def _write_header(self, f: TextIO):
        f.write(f'"""\n')
        f.write(f'Script généré automatiquement par LMGC90_GUI\n')
        f.write(f'Projet: {self.state.name}\n')
        f.write(f'Dimension: {self.state.dimension}D\n')
        f.write(f'"""\n\n')
    
    def _write_imports(self, f: TextIO):
        f.write('from pylmgc90 import pre\n')
        f.write('import numpy as np\n')
        f.write('import math\n\n')
        # ── Variables dynamiques ──────────────────────────────────────────────────
    def _write_dynamic_vars(self, f: TextIO):
        """
        Injecte les variables dynamiques du projet dans le script genere.

        Chaque variable est evaluee dans l'ordre de definition pour resoudre
        les dependances entre variables (ex: radius = thickness * 2).
        Les expressions referençant avatar[], group[], material[] ou model[]
        sont converties en valeur concrete au moment de la generation.

        Les objets proxy non serialisables (listes d'avatars, etc.) sont
        ecrits en commentaire avec la valeur litterale de l'expression.
        """
        dyn_vars = getattr(self.state, 'dynamic_vars', {}) or {}
        if not dyn_vars:
            return

        f.write('# ── Variables dynamiques ─────────────────────────────────────\n')

        # Contexte complet avec proxies (avatar, group, material, model, ...)
        from ..utils.safe_eval import build_eval_context
        full_ctx  = build_eval_context(self.controller)
        evaluated: dict = {}
        written   = 0

        for var_name, var_expr in dyn_vars.items():
            if not var_name.isidentifier():
                f.write(f'# Variable ignoree (nom invalide) : {var_name!r}\n')
                continue

            # Evaluer avec le contexte complet + variables deja evaluees
            raw_value = var_expr
            if isinstance(var_expr, str):
                try:
                    ctx = {**full_ctx, **evaluated}
                    raw_value = eval(var_expr, {"__builtins__": {}}, ctx)
                except Exception:
                    raw_value = var_expr  # garder brut si echec

            evaluated[var_name] = raw_value

            # Serialiser en representation Python litterale
            script_value = self._format_dynamic_var_value(raw_value)
            if script_value is not None:
                f.write(f'{var_name} = {script_value}\n')
                written += 1
            else:
                # Objet proxy ou type non serialisable
                f.write(
                    f'# {var_name} = {var_expr!r}'
                    f'  # valeur non serialisable — a recalculer\n'
                )

        if written > 0:
            f.write('\n')

    def _format_dynamic_var_value(self, value) -> 'str | None':
        """
        Convertit une valeur evaluee en representation Python litterale.
        Retourne None si la valeur n'est pas serialisable (proxy, objet...).
        """
        if isinstance(value, bool):
            return repr(value)
        if isinstance(value, int):
            return repr(value)
        if isinstance(value, float):
            return repr(value)
        if isinstance(value, str):
            return repr(value)
        if isinstance(value, (list, tuple)):
            parts = []
            for item in value:
                part = self._format_dynamic_var_value(item)
                if part is None:
                    return None
                parts.append(part)
            if isinstance(value, tuple):
                return f'({", ".join(parts)})'
            return f'[{", ".join(parts)}]'
        # Tout autre type (proxy, ndarray, objet) : non serialisable
        return None

    def _write_containers(self, f: TextIO):
        f.write('# Conteneurs\n')
        f.write('mats = pre.materials()\n')
        f.write('mods = pre.models()\n')
        f.write('bodies = pre.avatars()\n')
        f.write('tacts = pre.tact_behavs()\n')
        f.write('sees = pre.see_tables()\n')
        f.write('posts = pre.postpro_commands()\n\n')
        f.write('bodies_list = []\n\n')

    # ── Matériaux ─────────────────────────────────────────────────────────────
    def _write_materials(self, f: TextIO):
        if not self.state.materials:
            return
        
        f.write('# Matériaux\n')
        for mat in self.state.materials:
            f.write(f"mat_{mat.name} = pre.material(\n")
            f.write(f"    name='{mat.name}',\n")
            f.write(f"    materialType='{mat.material_type.value}',\n")
            f.write(f"    density={mat.density}")
            
            if mat.properties:
                for key, value in (mat.properties).items():
                    f.write(',\n    ')
                    f.write(f"{key}='{value}'" if isinstance(value, str) else f"{key}={value}")
            f.write('\n)\n')
            f.write(f"mats.addMaterial(mat_{mat.name})\n\n")
    
    # ── Modèles ───────────────────────────────────────────────────────────────
    def _write_models(self, f: TextIO):
        if not self.state.models:
            return
        
        f.write('# Modèles\n')
        for mod in self.state.models:
            f.write(f"mod_{mod.name} = pre.model(\n")
            f.write(f"    name='{mod.name}',\n")
            f.write(f"    physics='{mod.physics}',\n")
            f.write(f"    element='{mod.element}',\n")
            f.write(f"    dimension={mod.dimension}")
            
            if mod.options:
                for key, value in (mod.options).items():
                    f.write(',\n    ')
                    f.write(f"{key}='{value}'" if isinstance(value, str) else f"{key}={value}")
            f.write('\n)\n')
            f.write(f"mods.addModel(mod_{mod.name})\n\n")

    # ── Avatars manuels ───────────────────────────────────────────────────────
    def _write_avatars_manual(self, f: TextIO):
        manual_avatars = [a for a in self.state.avatars if a.origin == AvatarOrigin.MANUAL]
        if not manual_avatars:
            return
        
        f.write('# Avatars manuels\n')

        if self._use_loop : 
                self._write_avatars_manual_loop(f)
        else:
            for av in manual_avatars:
                self._write_single_avatar(f, av, "bodies")

        f.write('\n')

    
    # ---- Mode boucle --------------------------------------------------------
    def _write_avatars_manual_loop(self, f: TextIO):
        """
        Regroupe les avatars par groupe (avatar_groups).
        Chaque groupe homogene -> boucle compacte.
        Avatars sans groupe ou groupes heterogenes -> ecriture individuelle.
        """
        avatar_groups   = getattr(self.state, 'avatar_groups', {}) or {}
        written_indices: set = set()

        for group_name, indices in avatar_groups.items():
            group_avs = []
            for idx in indices:
                if idx < len(self.state.avatars):
                    av = self.state.avatars[idx]
                    if av.origin == AvatarOrigin.MANUAL:
                        group_avs.append((idx, av))
            if not group_avs:
                continue
            ok = self._try_write_group_as_loop(f, group_name, group_avs)
            if ok:
                written_indices.update(idx for idx, _ in group_avs)

        # Avatars restants (hors groupe ou groupe heterogene)
        for i, av in enumerate(self.state.avatars):
            if av.origin != AvatarOrigin.MANUAL:
                continue
            if i in written_indices:
                continue
            self._write_single_avatar(f, av, "bodies")

    def _try_write_group_as_loop(
        self, f: TextIO, group_name: str, group_avs: list
    ) -> bool:
        """
        Tente d'ecrire le groupe comme boucle compacte.
        Retourne True si reussi (groupe homogene), False sinon.
        """
        if not group_avs:
            return False

        _, ref = group_avs[0]
        atype  = ref.avatar_type.value

        # --- Briques de maconnerie -------------------------------------------
        if (atype == "emptyAvatar"
                and ref.wall_params
                and 'l' in ref.wall_params
                and 'h' in ref.wall_params):
            wp0 = ref.wall_params
            for _, av in group_avs[1:]:
                wp = av.wall_params or {}
                if (av.material_name       != ref.material_name
                        or av.model_name   != ref.model_name
                        or av.color        != ref.color
                        or wp.get('brick_name') != wp0.get('brick_name')
                        or wp.get('l')     != wp0.get('l')
                        or wp.get('h')     != wp0.get('h')
                        or wp.get('lz')    != wp0.get('lz')):
                    return False
            self._write_masonry_group_loop(f, group_name, group_avs)
            return True

        # --- Avatars standards homogenes -------------------------------------
        if atype not in ("emptyAvatar", "mesh"):
            for _, av in group_avs[1:]:
                if (av.avatar_type.value  != atype
                        or av.material_name   != ref.material_name
                        or av.model_name      != ref.model_name
                        or av.color           != ref.color
                        or av.radius          != ref.radius
                        or av.generation_type != ref.generation_type):
                    return False
            self._write_standard_group_loop(f, group_name, group_avs)
            return True

        return False  # mesh ou emptyAvatar classique -> individuel

    def _write_masonry_group_loop(
        self, f: TextIO, group_name: str, group_avs: list
    ):
        """
        Genere la boucle de creation des briques du groupe en reconstituant
        exactement les memes boucles for row/col que le masonry_wizard.

        Si les parametres du pattern sont disponibles dans state.masonry_patterns,
        on genere la boucle structuree (double for row/col ou paneresse_simple)
        identique au wizard  ->  script ultra-compact.

        Sinon (ancien projet sans masonry_patterns), fallback sur une liste
        de centers + for _c in _centers.
        """
        _, ref     = group_avs[0]
        wp         = ref.wall_params
        safe       = group_name.replace(' ', '_').replace('-', '_')
        masonry_patterns = getattr(self.state, 'masonry_patterns', {}) or {}
        mp = masonry_patterns.get(group_name)

        if mp:
            self._write_masonry_pattern_loop(f, group_name, safe, mp)
        else:
            self._write_masonry_centers_loop(f, group_name, safe, group_avs, wp, ref)

    def _write_masonry_pattern_loop(
        self, f: TextIO, group_name: str, safe: str, mp: dict
    ):
        """
        Genere la double boucle for row/col en reconstituant les formules
        de position exactement comme dans masonry_wizard._generate_masonry().

        Patterns supportes :
          Standard         : decalage lx/2 sur rangs impairs
          Running Bond     : decalage (row%3)*(lx/3) par rang
          Stack Bond       : grille reguliere sans decalage
          Flemish Bond     : alternance panneresse (lx) / boutisse (lx/2)
          Paneresse simple : via pre.paneresse_simple
        """
        pattern   = mp['pattern']
        lx        = mp['lx']
        ly        = mp['ly']
        lz        = mp.get('lz')
        nb_rows   = mp['nb_rows']
        nb_cols   = mp['nb_cols']
        offset_x  = mp['offset_x']
        offset_y  = mp['offset_y']
        offset_z  = mp.get('offset_z', 0.0)
        joint     = mp['joint']
        bname     = mp['brick_name']
        mat       = mp['mat']
        mod       = mp['mod']
        color     = mp['color']
        dim       = mp['dim']
        _lz       = lz if lz is not None else ly

        f.write(f"# Mur de maconnerie : {group_name}"
                f" — pattern '{pattern}' ({nb_rows} rangs x {nb_cols} cols)\n")

        # ---- lignes de creation du body (appelees dans chaque boucle) ------
        def body_block(indent, ce, br=None):
            br = br or f"_brick_{safe}"
            i  = indent
            return (
                f"{i}body = {br}.rigidBrick(\n"
                f"{i}    center={ce},\n"
                f"{i}    model=mods['{mod}'],\n"
                f"{i}    material=mats['{mat}'],\n"
                f"{i}    color='{color}'\n"
                f"{i})\n"
                f"{i}bodies.addAvatar(body)\n"
                f"{i}bodies_list.append(body)\n"
            )

        # ---- Standard -------------------------------------------------------
        if pattern == 'Standard':
            f.write(f"_brick_{safe} = pre.brick2D('{bname}', {lx}, {ly})\n"
                    if dim == 2 else
                    f"_brick_{safe} = pre.brick3D('{bname}', {lx}, {ly}, {_lz})\n")
            f.write(f"for _row in range({nb_rows}):\n")
            f.write(f"    _row_off = ({lx} / 2.0) if (_row % 2 == 1) else 0.0\n")
            f.write(f"    for _col in range({nb_cols}):\n")
            f.write(f"        _cx = {offset_x} + _col * ({lx} + {joint}) + _row_off + {lx} / 2.0\n")
            f.write(f"        _cy = {offset_y} + _row * ({ly} + {joint}) + {ly} / 2.0\n")
            ce = "[_cx, _cy]" if dim == 2 else f"[_cx, _cy, {offset_z}]"
            f.write(body_block("        ", ce))

        # ---- Running Bond ---------------------------------------------------
        elif pattern == 'Running Bond':
            f.write(f"_brick_{safe} = pre.brick2D('{bname}', {lx}, {ly})\n"
                    if dim == 2 else
                    f"_brick_{safe} = pre.brick3D('{bname}', {lx}, {ly}, {_lz})\n")
            f.write(f"for _row in range({nb_rows}):\n")
            f.write(f"    _row_off = (_row % 3) * ({lx} / 3.0)\n")
            f.write(f"    for _col in range({nb_cols}):\n")
            f.write(f"        _cx = {offset_x} + _col * ({lx} + {joint}) + _row_off + {lx} / 2.0\n")
            f.write(f"        _cy = {offset_y} + _row * ({ly} + {joint}) + {ly} / 2.0\n")
            ce = "[_cx, _cy]" if dim == 2 else f"[_cx, _cy, {offset_z}]"
            f.write(body_block("        ", ce))

        # ---- Stack Bond -----------------------------------------------------
        elif pattern == 'Stack Bond':
            f.write(f"_brick_{safe} = pre.brick2D('{bname}', {lx}, {ly})\n"
                    if dim == 2 else
                    f"_brick_{safe} = pre.brick3D('{bname}', {lx}, {ly}, {_lz})\n")
            f.write(f"for _row in range({nb_rows}):\n")
            f.write(f"    for _col in range({nb_cols}):\n")
            f.write(f"        _cx = {offset_x} + _col * ({lx} + {joint}) + {lx} / 2.0\n")
            f.write(f"        _cy = {offset_y} + _row * ({ly} + {joint}) + {ly} / 2.0\n")
            ce = "[_cx, _cy]" if dim == 2 else f"[_cx, _cy, {offset_z}]"
            f.write(body_block("        ", ce))

        # ---- Flemish Bond ---------------------------------------------------
        # Panneresse (lx) si (row+col)%2==0, boutisse (lx/2) sinon.
        # Deux briques de reference car brick_lx est variable.
        elif pattern == 'Flemish Bond':
            lx_bou = lx / 2.0
            if dim == 2:
                f.write(f"_brick_{safe}_pan = pre.brick2D('{bname}', {lx}, {ly})\n")
                f.write(f"_brick_{safe}_bou = pre.brick2D('{bname}', {lx_bou}, {ly})\n")
            else:
                f.write(f"_brick_{safe}_pan = pre.brick3D('{bname}', {lx}, {ly}, {_lz})\n")
                f.write(f"_brick_{safe}_bou = pre.brick3D('{bname}', {lx_bou}, {ly}, {_lz})\n")
            f.write(f"for _row in range({nb_rows}):\n")
            f.write(f"    _x_cur = {offset_x}\n")
            f.write(f"    for _col in range({nb_cols}):\n")
            f.write(f"        _is_pan = (_row + _col) % 2 == 0\n")
            f.write(f"        _blx = {lx} if _is_pan else {lx_bou}\n")
            f.write(f"        _br  = _brick_{safe}_pan if _is_pan else _brick_{safe}_bou\n")
            f.write(f"        _cx  = _x_cur + _blx / 2.0\n")
            f.write(f"        _cy  = {offset_y} + _row * ({ly} + {joint}) + {ly} / 2.0\n")
            ce = "[_cx, _cy]" if dim == 2 else f"[_cx, _cy, {offset_z}]"
            f.write(body_block("        ", ce, "_br"))
            f.write(f"        _x_cur += _blx + {joint}\n")

        # ---- Paneresse simple / double (pylmgc90) ------------------------------------
        elif pattern in ('Paneresse simple (pylmgc90)', 'Paneresse double (pylmgc90)'):
            disposition  = mp.get('disposition',    'paneresse')
            first_type   = mp.get('first_type',     '1')
            use_length   = mp.get('pan_use_length', False)
            pan_length   = mp.get('pan_length',     1.0)
            no_half      = mp.get('pan_no_half',    False)
            wall_fn      = ('paneresse_double' if 'double' in pattern
                            else 'paneresse_simple')
            # brick3D requis même en 2D (ly=1.0 pour mur plan)
        
            if dim == 3:
                f.write(f"_bref_{safe} = pre.brick3D('{bname}', {lx}, {ly}, {_lz})\n")
            origin = (f"[{offset_x}, {offset_y}, {offset_z}]")
            f.write(f"_wall_{safe} = pre.{wall_fn}("
                    f"brick_ref=_bref_{safe}, disposition='{disposition}')\n")
            f.write(f"_wall_{safe}.setNumberOfRows({nb_rows})\n")
            f.write(f"_wall_{safe}.setJointThicknessBetweenRows({joint})\n")
            f.write(f"_wall_{safe}.computeHeight()\n")
            if use_length:
                f.write(f"_wall_{safe}.setFirstRowByLength(\n")
                f.write(f"    first_brick_type='{first_type}',\n")
                f.write(f"    length={pan_length},\n")
                f.write(f"    joint_thickness={joint}\n")
                f.write(f")\n")
            else:
                f.write(f"_wall_{safe}.setFirstRowByNumberOfBricks(\n")
                f.write(f"    first_brick_type='{first_type}',\n")
                f.write(f"    nb_bricks={nb_cols},\n")
                f.write(f"    joint_thickness={joint}\n")
                f.write(f")\n")
            build_fn = ('buildRigidWallWithoutHalfBricks' if no_half
                        else 'buildRigidWall')
            f.write(f"_bodies_{safe} = _wall_{safe}.{build_fn}(\n")
            f.write(f"    origin={origin},\n")
            f.write(f"    model=mods['{mod}'],\n")
            f.write(f"    material=mats['{mat}'],\n")
            f.write(f"    colors=['{color}', '{color}']\n")
            f.write(f")\n")
            f.write(f"for _body in _bodies_{safe}:\n")
            f.write(f"    bodies.addAvatar(_body)\n")
            f.write(f"    bodies_list.append(_body)\n")
 
            # ── Transformations (translate / rotate / deepcopy) ────────────
            tf_translate = mp.get("tf_translate", False)
            tf_rotate    = mp.get("tf_rotate",    False)
            tf_copy      = mp.get("tf_copy",      False)
 
            if tf_translate:
                tx = mp.get("tf_tx", 0.0)
                ty = mp.get("tf_ty", 0.0)
                tz = mp.get("tf_tz", 0.0)
                if dim == 3:
                    f.write(f"_bodies_{safe}.translate(dx={tx}, dy={ty}, dz={tz})\n")
                else:
                    f.write(f"_bodies_{safe}.translate(dx={tx}, dy={ty})\n")
 
            if tf_rotate:
                cx      = mp.get("tf_cx",        0.0)
                cy      = mp.get("tf_cy",        0.0)
                cz      = mp.get("tf_cz",        0.0)
                axis    = mp.get("tf_axis",      "Z")
                alpha_d = mp.get("tf_alpha_deg", 0.0)
                ax_map  = {"X": "[1.,0.,0.]", "Y": "[0.,1.,0.]", "Z": "[0.,0.,1.]"}
                ax_str  = ax_map.get(axis, "[0.,0.,1.]")
                f.write(f"_bodies_{safe}.rotate(\n")
                f.write(f"    description='axis',\n")
                f.write(f"    center=np.array([{cx}, {cy}, {cz}]),\n")
                f.write(f"    axis={ax_str},\n")
                f.write(f"    alpha=math.radians({alpha_d})\n")
                f.write(f")\n")
 
            if tf_copy:
                cdx = mp.get("tf_copy_dx", 0.0)
                cdy = mp.get("tf_copy_dy", 0.0)
                cdz = mp.get("tf_copy_dz", 0.0)
                f.write(f"_bodies_{safe}_copy = copy.deepcopy(_bodies_{safe})\n")
                if dim == 3:
                    f.write(f"_bodies_{safe}_copy.translate(dx={cdx}, dy={cdy}, dz={cdz})\n")
                else:
                    f.write(f"_bodies_{safe}_copy.translate(dx={cdx}, dy={cdy})\n")
                f.write(f"for _body in _bodies_{safe}_copy:\n")
                f.write(f"    bodies.addAvatar(_body)\n")
                f.write(f"    bodies_list.append(_body)\n")
 
        else:
            f.write(f"# Pattern inconnu '{pattern}' -> fallback liste de centers\n")
            for _, av in getattr(self, '_last_group_avs', []):
                f.write(f"# center={list(av.center)}\n")
 
        f.write('\n')

    def _write_masonry_centers_loop(
        self, f: TextIO, group_name: str, safe: str,
        group_avs: list, wp: dict, ref
    ):
        """
        Fallback : liste de centers + boucle for _c.
        Utilise quand masonry_patterns n'est pas disponible (ancien projet).
        """
        brick_name = wp.get('brick_name', 'std')
        bx  = wp['l']
        by  = wp['h']
        bz  = wp.get('lz')
        mat   = ref.material_name
        mod   = ref.model_name
        color = ref.color
        dim   = len(ref.center)

        f.write(f"# Groupe maconnerie (fallback) : {group_name} ({len(group_avs)} briques)\n")
        if dim == 2:
            f.write(f"_brick_{safe} = pre.brick2D('{brick_name}', {bx}, {by})\n")
        else:
            if bz is None:
                bz = by
            f.write(f"_brick_{safe} = pre.brick3D('{brick_name}', {bx}, {by}, {bz})\n")
        lines = ['[']
        for _, av in group_avs:
            lines.append(f'    {list(av.center)},')
        lines.append(']')
        f.write(f"_centers_{safe} = " + '\n'.join(lines) + "\n\n")
        f.write(f"for _c in _centers_{safe}:\n")
        f.write(f"    body = _brick_{safe}.rigidBrick(\n")
        f.write(f"        center=_c,\n")
        f.write(f"        model=mods['{mod}'],\n")
        f.write(f"        material=mats['{mat}'],\n")
        f.write(f"        color='{color}'\n")
        f.write(f"    )\n")
        f.write(f"    bodies.addAvatar(body)\n")
        f.write(f"    bodies_list.append(body)\n")
        f.write('\n')

    def _write_standard_group_loop(
        self, f: TextIO, group_name: str, group_avs: list
    ):
        """
        Genere :
            _centers_<group> = [[x,y], ...]
            for _c in _centers_<group>:
                body = pre.<type>(center=_c, model=..., ...)
                bodies.addAvatar(body)
                bodies_list.append(body)
        """
        _, ref  = group_avs[0]
        atype   = ref.avatar_type.value
        mat     = ref.material_name
        mod     = ref.model_name
        color   = ref.color
        safe    = group_name.replace(' ', '_').replace('-', '_')

        lines = ['[']
        for _, av in group_avs:
            lines.append(f'    {list(av.center)},')
        lines.append(']')
        centers_repr = '\n'.join(lines)

        f.write(f'# Groupe : {group_name} ({len(group_avs)} avatars)\n')
        f.write(f'_centers_{safe} = {centers_repr}\n\n')
        f.write(f'for _c in _centers_{safe}:\n')
        f.write(f"    body = pre.{atype}(\n")
        f.write(f"        center=_c,\n")
        f.write(f"        model=mods['{mod}'],\n")
        f.write(f"        material=mats['{mat}'],\n")
        f.write(f"        color='{color}'")
        if ref.radius is not None:
            f.write(f",\n        r={ref.radius}")
        if ref.generation_type:
            f.write(f",\n        generation_type='{ref.generation_type}'")
        if ref.nb_vertices:
            key = 'nb_disk' if ref.avatar_type == AvatarType.RIGID_CLUSTER \
                  else 'nb_vertices'
            f.write(f",\n        {key}={ref.nb_vertices}")
        if ref.is_hollow:
            f.write(",\n        is_Hollow=True")
        if ref.wall_params:
            for k, v in ref.wall_params.items():
                if k not in _MASONRY_WALL_KEYS:
                    f.write(f",\n        {k}={v}")
        f.write("\n    )\n")
        f.write("    bodies.addAvatar(body)\n")
        f.write("    bodies_list.append(body)\n")
        f.write('\n')

    def _write_single_avatar(self, f, avatar, container="bodies"):
        """Écrit un avatar individuel"""
        atype = avatar.avatar_type.value
        center = self._format_value( avatar.center)
        mat = avatar.material_name
        mod = avatar.model_name
        color = avatar.color
        
        # ── Corps déformable (MESH_DEFORMABLE) ───────────────────────────────
        if atype == "mesh":
            mp = avatar.mesh_params
            if not mp:
                f.write(f"# ⚠️  Corps déformable sans mesh_params — à recréer via le wizard\n\n")
                return

            geom = mp['geom']
            dim  = mp['dim']
            cx   = mp.get('cx', 0.0)
            cy   = mp.get('cy', 0.0)
            cz   = mp.get('cz', 0.0)

            f.write(f"# Corps déformable — {geom}\n")

            if geom == "Rectangle":
                x0 = cx - mp['lx'] / 2.0
                y0 = cy - mp['ly'] / 2.0
                f.write(f"_surf = pre.buildMesh2D(\n")
                f.write(f"    '{mp['mesh_type']}',\n")
                f.write(f"    {x0}, {y0},\n")
                f.write(f"    {mp['lx']}, {mp['ly']},\n")
                f.write(f"    {mp['nx']}, {mp['ny']}\n")
                f.write(f")\n")

            elif geom == "Boîte (H8)":
                x0 = cx - mp['lx'] / 2.0
                y0 = cy - mp['ly'] / 2.0
                z0 = cz - mp['lz'] / 2.0
                f.write(f"_vol = pre.buildMeshH8(\n")
                f.write(f"    {x0}, {y0}, {z0},\n")
                f.write(f"    {mp['lx']}, {mp['ly']}, {mp['lz']},\n")
                f.write(f"    {mp['nx']}, {mp['ny']}, {mp['nz']}\n")
                f.write(f")\n")

            elif geom == "Disque":
                lc = round(2 * 3.14159 * mp['r'] / mp['ntheta'], 6)
                f.write(f"import gmsh, tempfile, os\n")
                f.write(f"gmsh.initialize(); gmsh.option.setNumber('General.Terminal', 0)\n")
                f.write(f"gmsh.model.add('disk'); gmsh.model.occ.addDisk({cx}, {cy}, 0., {mp['r']}, {mp['r']})\n")
                f.write(f"gmsh.model.occ.synchronize()\n")
                f.write(f"gmsh.option.setNumber('Mesh.CharacteristicLengthMin', {lc})\n")
                f.write(f"gmsh.option.setNumber('Mesh.CharacteristicLengthMax', {lc})\n")
                f.write(f"gmsh.option.setNumber('Mesh.MshFileVersion', 2.2)\n")
                f.write(f"gmsh.model.mesh.generate(2)\n")
                f.write(f"_tmp = tempfile.mktemp(suffix='.msh'); gmsh.write(_tmp); gmsh.finalize()\n")
                f.write(f"_surf = pre.readMesh(_tmp, 2); os.unlink(_tmp)\n")

            elif geom == "Sphère":
                lc = round(2 * 3.14159 * mp['r'] / mp['ntheta'], 6)
                f.write(f"import gmsh, tempfile, os\n")
                f.write(f"gmsh.initialize(); gmsh.option.setNumber('General.Terminal', 0)\n")
                f.write(f"gmsh.model.add('sphere'); gmsh.model.occ.addSphere({cx}, {cy}, {cz}, {mp['r']})\n")
                f.write(f"gmsh.model.occ.synchronize()\n")
                f.write(f"gmsh.option.setNumber('Mesh.CharacteristicLengthMin', {lc})\n")
                f.write(f"gmsh.option.setNumber('Mesh.CharacteristicLengthMax', {lc})\n")
                f.write(f"gmsh.option.setNumber('Mesh.MshFileVersion', 2.2)\n")
                f.write(f"gmsh.model.mesh.generate(3)\n")
                f.write(f"_tmp = tempfile.mktemp(suffix='.msh'); gmsh.write(_tmp); gmsh.finalize()\n")
                f.write(f"_vol = pre.readMesh(_tmp, 3); os.unlink(_tmp)\n")

            elif geom == "Cylindre":
                lc = round(2 * 3.14159 * mp['r'] / mp['ntheta'], 6)
                z0 = cz - mp['h'] / 2.0
                f.write(f"import gmsh, tempfile, os\n")
                f.write(f"gmsh.initialize(); gmsh.option.setNumber('General.Terminal', 0)\n")
                f.write(f"gmsh.model.add('cylinder')\n")
                f.write(f"gmsh.model.occ.addCylinder({cx}, {cy}, {z0}, 0., 0., {mp['h']}, {mp['r']})\n")
                f.write(f"gmsh.model.occ.synchronize()\n")
                f.write(f"gmsh.option.setNumber('Mesh.CharacteristicLengthMin', {lc})\n")
                f.write(f"gmsh.option.setNumber('Mesh.CharacteristicLengthMax', {lc})\n")
                f.write(f"gmsh.option.setNumber('Mesh.MshFileVersion', 2.2)\n")
                f.write(f"gmsh.model.mesh.generate(3)\n")
                f.write(f"_tmp = tempfile.mktemp(suffix='.msh'); gmsh.write(_tmp); gmsh.finalize()\n")
                f.write(f"_vol = pre.readMesh(_tmp, 3); os.unlink(_tmp)\n")

            elif geom == "Fichier externe":
                filepath = mp.get('filepath', '').replace('\\', '/')
                f.write(f"_mesh = pre.readMesh('{filepath}', {dim})\n")

            # buildMeshedAvatar commun à tous les cas
            mesh_var = "_surf" if dim == 2 else "_vol"
            if geom == "Fichier externe":
                mesh_var = "_mesh"
            f.write(f"body = pre.buildMeshedAvatar(\n")
            f.write(f"    mesh={mesh_var},\n")
            f.write(f"    model=mods['{mod}'],\n")
            f.write(f"    material=mats['{mat}']\n")
            f.write(f")\n")
            f.write(f"{container}.addAvatar(body)\n")
            f.write(f"bodies_list.append(body)\n")
            # Contacteurs éventuellement ajoutés via l'onglet empty_avatar
            if avatar.contactors:
                for cont in avatar.contactors:
                    shape = cont['shape']
                    color = cont.get('color', 'BLEUx')
                    group = cont.get('group')
                    params = cont.get('params', {})
                    kwargs = f"shape='{shape}', color='{color}'"
                    if group:
                        kwargs += f", group='{group}'"
                    for k, v in params.items():
                        kwargs += f", {k}={repr(v)}"
                    f.write(f"body.addContactors({kwargs})\n")
            f.write("\n")
            return

        # ── Brique de maçonnerie (EMPTY_AVATAR issu du masonry_wizard) ────────
        #  emptyAvatar dont wall_params contient 'l' et 'h'
        if atype == "emptyAvatar" and avatar.wall_params and \
                'l' in avatar.wall_params and 'h' in avatar.wall_params:
            wp         = avatar.wall_params
            brick_name = wp.get('brick_name', 'std')
            bx         = wp['l']        # longueur
            by         = wp['h']        # hauteur (2D) ou profondeur (3D)
            bz         = wp.get('lz')   # hauteur 3D, None en 2D
            dim        = len(avatar.center)

            f.write(f"# Brique de maçonnerie — {brick_name}\n")
            if dim == 2:
                f.write(f"_brick = pre.brick2D('{brick_name}', {bx}, {by})\n")
                f.write(f"body = _brick.rigidBrick(\n")
                f.write(f"    center={center},\n")
                f.write(f"    model=mods['{mod}'],\n")
                f.write(f"    material=mats['{mat}'],\n")
                f.write(f"    color='{color}'\n")
                f.write(f")\n")
            else:
                if bz is None:
                    bz = by
                f.write(f"_brick = pre.brick3D('{brick_name}', {bx}, {by}, {bz})\n")
                f.write(f"body = _brick.rigidBrick(\n")
                f.write(f"    center={center},\n")
                f.write(f"    model=mods['{mod}'],\n")
                f.write(f"    material=mats['{mat}'],\n")
                f.write(f"    color='{color}'\n")
                f.write(f")\n")
            f.write(f"{container}.addAvatar(body)\n")
            f.write(f"bodies_list.append(body)\n\n")
            return

        # emptyAvatar
        if atype == "emptyAvatar" :
            f.write(f"# Avatar vide avec contacteurs personnalisés\n")
            f.write(f"body = pre.avatar(dimension={self.state.dimension})\n")
            
            # Bulk
            if len(center) == 2:
                f.write(f"body.addBulk(pre.rigid2d())\n")
            else:
                f.write(f"body.addBulk(pre.rigid3d())\n")
            
            # Node principal
            f.write(f"body.addNode(pre.node(coor=np.array({center}), number=1))\n")
            
            # Configuration
            f.write(f"body.defineGroups()\n")
            f.write(f"body.defineModel(model=mods['{mod}'])\n")
            f.write(f"body.defineMaterial(material=mats['{mat}'])\n")
            
            # Contacteurs
            for cont in avatar.contactors:
                shape = cont['shape']
                color_c = cont.get('color', color)
                params = cont.get('params', {})
                
                # Construire les paramètres
                params_str = ", ".join(f"{k}={repr(v)}" for k, v in params.items())
                
                f.write(f"body.addContactors(shape='{shape}', color='{color_c}'")
                if params_str:
                    f.write(f", {params_str}")
                f.write(f")\n")
            
            # Calcul des propriétés rigides
            f.write(f"body.computeRigidProperties()\n")
            f.write(f"{container}.addAvatar(body)\n")
            f.write("bodies_list.append(body)\n\n")
            return
        
        # avatars standards
        # construire les arguments
        args = [
            f"center={center}",
            f"model=mods['{mod}']",
            f"material=mats['{mat}']",
            f"color='{color}'"
        ]
        
        # 1. Traiter wall_params d'abord (ex: r, thick, etc.)
        has_r_in_wall_params = False
        if avatar.wall_params:
            for k, v in avatar.wall_params.items():
                if k in _MASONRY_WALL_KEYS:
                    continue
                args.append(f"{k}={v}")
                if k == 'r':
                    has_r_in_wall_params = True
        
        # 2. Déterminer si on doit EXCLURE r (cas spécial polygone full/bevel)
        exclude_r = False
        if avatar.avatar_type in [AvatarType.RIGID_POLYGON, AvatarType.RIGID_POLYHEDRON]:
            if avatar.generation_type in ["full", "bevel"]:
                exclude_r = True

        # 3. Ajouter r seulement si :
        #    - il existe,
        #    - il n'est pas déjà dans wall_params,
        #    - ET ce n'est PAS un polygone full/bevel
        if avatar.radius and not has_r_in_wall_params and not exclude_r:

            args.append(f"radius={avatar.radius}")
        
        if avatar.axis:
            args.append(f"axe1={avatar.axis['axe1']}")
            args.append(f"axe2={avatar.axis['axe2']}")
            if 'axe3' in avatar.axis:
                args.append(f"axe3={avatar.axis['axe3']}")
        
        if avatar.generation_type:
            args.append(f"generation_type='{avatar.generation_type}'")
        
        if avatar.nb_vertices:
            if avatar.avatar_type == AvatarType.RIGID_CLUSTER:
                args.append(f"nb_disk = {avatar.nb_vertices}")
            else : 
                args.append(f"nb_vertices={avatar.nb_vertices}")
        
        if avatar.vertices:
            args.append(f"vertices=np.array({avatar.vertices})")
        
        if avatar.is_hollow:
            args.append("is_Hollow=True")
        
        # Écrire
        f.write(f"body = pre.{atype}(\n")
        for i, arg in enumerate(args):
            if "None" not in arg : 
                f.write(f"    {arg}")
                if i < len(args) - 1:
                    f.write(",\n")
                else:
                    f.write("\n")
        f.write(")\n")
        f.write(f"{container}.addAvatar(body)\n")
        f.write("bodies_list.append(body)\n\n")
    
    # ── Boucles géométriques (Cercle, Grille, Ligne, Spirale) ────────────────
    def _write_loops(self, f: TextIO):
        if not self.state.loops:
            return
        
        f.write('# Boucles\n')
        for i, loop in enumerate(self.state.loops):
            f.write(f"# Boucle {i+1}: {loop.loop_type}\n")
            
            model_avatar = self.state.avatars[loop.model_avatar_index]
            
            if loop.loop_type == "Cercle":
                f.write(f"for angle_idx in range({loop.count}):\n")
                f.write(f"    angle = 2 * math.pi * angle_idx / {loop.count}\n")
                f.write(f"    x = {model_avatar.center[0]} + {loop.offset_x} + {loop.radius} * math.cos(angle)\n")
                f.write(f"    y = {model_avatar.center[1]} + {loop.offset_y} + {loop.radius} * math.sin(angle)\n")
                center_calc = "[x, y]" if self.state.dimension == 2 else "[x, y, 0]"
            
            elif loop.loop_type == "Grille":
                n_side = int(loop.count ** 0.5)
                f.write(f"n_side = {n_side}\n")
                f.write(f"for i in range(n_side):\n")
                f.write(f"    for j in range(n_side):\n")
                f.write(f"        x = {model_avatar.center[0]} + {loop.offset_x} + i * {loop.step}\n")
                f.write(f"        y = {model_avatar.center[1]} + {loop.offset_y} + j * {loop.step}\n")
                center_calc = "[x, y]" if self.state.dimension == 2 else "[x, y, 0]"
            
            elif loop.loop_type == "Ligne":
                axis = 1 if loop.invert_axis else 0
                f.write(f"for idx in range({loop.count}):\n")
                if axis == 0:
                    f.write(f"    x = {model_avatar.center[0]} + {loop.offset_x} + idx * {loop.step}\n")
                    f.write(f"    y = {model_avatar.center[1]} + {loop.offset_y}\n")
                else:
                    f.write(f"    x = {model_avatar.center[0]} + {loop.offset_x}\n")
                    f.write(f"    y = {model_avatar.center[1]} + {loop.offset_y} + idx * {loop.step}\n")
                center_calc = "[x, y]" if self.state.dimension == 2 else "[x, y, 0]"
            
            elif loop.loop_type == "Spirale":
                f.write(f"for idx in range({loop.count}):\n")
                f.write(f"    angle = 2 * math.pi * idx / 10\n")
                f.write(f"    r = {loop.radius} + idx * {loop.spiral_factor}\n")
                f.write(f"    x = {model_avatar.center[0]} + {loop.offset_x} + r * math.cos(angle)\n")
                f.write(f"    y = {model_avatar.center[1]} + {loop.offset_y} + r * math.sin(angle)\n")
                center_calc = "[x, y]" if self.state.dimension == 2 else "[x, y, 0]"
            else:
                continue
            
            indent = "    " if loop.loop_type == "Grille" else "    "
            if loop.loop_type == "Grille":
                indent = "        "
            
            f.write(f"{indent}center = {center_calc}\n")
            f.write(f"{indent}av = pre.{model_avatar.avatar_type.value}(\n")
            f.write(f"{indent}    center=center,\n")
            f.write(f"{indent}    material=mat_{model_avatar.material_name},\n")
            f.write(f"{indent}    model=mod_{model_avatar.model_name},\n")
            f.write(f"{indent}    color='{model_avatar.color}'")
            
            if model_avatar.radius is not None:
                f.write(f",\n{indent}    r={model_avatar.radius}")
            
            f.write(f"\n{indent})\n")
            f.write(f"{indent}bodies.addAvatar(av)\n\n")
    
    # ── Boucles for génériques ────────────────────────────────────────────────
    def _write_for_loops(self, f):
        """Boucles For génériques"""
        if not hasattr(self.state, 'for_loops') or not self.state.for_loops:
            return
        f.write("#Boucles for génériques\n")
        for idx, for_loop in enumerate(self.state.for_loops):
            f.write(f"# Boucle For {idx + 1} : {for_loop.target_type}\n")
            
            # Évaluer les expressions de début/fin/step
            f.write(f"for {for_loop.loop_var} in range({for_loop.start_expr}, {for_loop.end_expr}, {for_loop.step_expr}):\n")
            
            # Générer l'élément selon le type
            template = for_loop.template_config
            
            if for_loop.target_type == "avatar":
                self._write_for_avatar(f, template, for_loop.loop_var)
            elif for_loop.target_type == "material":
                self._write_for_material(f, template, for_loop.loop_var)
            elif for_loop.target_type == "model":
                self._write_for_model(f, template, for_loop.loop_var)
            elif for_loop.target_type == "contact_law":
                self._write_for_contact_law(f, template, for_loop.loop_var)
            elif for_loop.target_type == "visibility":
                self._write_for_visibility(f, template, for_loop.loop_var)
            elif for_loop.target_type == "dof":
                self._write_for_dof(f, template, for_loop.loop_var)
            
            f.write("\n")
    
    
    def _write_for_avatar(self, f, template: dict, loop_var: str):
        """Génère un avatar dans une boucle for"""
        atype = template['avatar_type']
        
        # Extraire les expressions avec variable de boucle
        center_expr = template.get('center', '[0, 0]')
        radius_expr = template.get('radius', '0.1')
        
        f.write(f"    # Évaluer les paramètres avec {loop_var}\n")
        f.write(f"    center = {center_expr}\n")
        
        if atype == "emptyAvatar":
            # Avatar vide
            f.write(f"    body = pre.avatar(dimension=len(center))\n")
            f.write(f"    body.addBulk(pre.rigid2d() if len(center) == 2 else pre.rigid3d())\n")
            f.write(f"    body.addNode(pre.node(coor=np.array(center), number=1))\n")
            f.write(f"    body.defineGroups()\n")
            f.write(f"    body.defineModel(model=mods['{template['model_name']}'])\n")
            f.write(f"    body.defineMaterial(material=mats['{template['material_name']}'])\n")
            
            # Contacteurs
            if 'contactors' in template:
                for cont in template['contactors']:
                    shape = cont['shape']
                    color = cont.get('color', template.get('color', 'BLUEx'))
                    params = cont.get('params', {})
                    params_str = ", ".join(f"{k}={repr(v)}" for k, v in params.items())
                    
                    f.write(f"    body.addContactors(shape='{shape}', color='{color}'")
                    if params_str:
                        f.write(f", {params_str}")
                    f.write(f")\n")
            
            f.write(f"    body.computeRigidProperties()\n")
            f.write(f"    bodies.addAvatar(body)\n")
            f.write(f"    bodies_list.append(body)\n")
        
        else:
            # Avatar standard
            f.write(f"    body = pre.{atype}(\n")
            f.write(f"        center=center,\n")
            f.write(f"        model=mods['{template['model_name']}'],\n")
            f.write(f"        material=mats['{template['material_name']}'],\n")
            f.write(f"        color='{template.get('color', 'BLUEx')}'")
            
            if 'radius' in template:
                f.write(f",\n        r={radius_expr}")
            
            if 'axis' in template:
                for k, v in template['axis'].items():
                    f.write(f",\n        {k}={v}")
            
            f.write(f"\n    )\n")
            f.write(f"    bodies.addAvatar(body)\n")
            f.write(f"    bodies_list.append(body)\n")

    def _write_for_material(self, f, template: dict, loop_var: str):
        """Génère un matériau dans une boucle for"""
        name_expr = template['name']
        density_expr = template.get('density', '2800')
        
        f.write(f"    mat_name = {name_expr}\n")
        f.write(f"    density_val = {density_expr}\n")
        f.write(f"    mats[mat_name] = pre.material(\n")
        f.write(f"        name=mat_name,\n")
        f.write(f"        materialType='{template['material_type']}',\n")
        f.write(f"        density=density_val\n")
        f.write(f"    )\n")
        f.write(f"    materials.addMaterial(mats[mat_name])\n")

    def _write_for_model(self, f, template: dict, loop_var: str):
        """Génère un modèle dans une boucle for"""
        name_expr = template['name']
        
        f.write(f"    mod_name = {name_expr}\n")
        f.write(f"    mods[mod_name] = pre.model(\n")
        f.write(f"        name=mod_name,\n")
        f.write(f"        physics='{template['physics']}',\n")
        f.write(f"        element='{template['element']}',\n")
        f.write(f"        dimension={template['dimension']}\n")
        f.write(f"    )\n")
        f.write(f"    models.addModel(mods[mod_name])\n")

    def _write_for_contact_law(self, f, template: dict, loop_var: str):
        """Génère une loi de contact dans une boucle for"""
        name_expr = template['name']
        friction_expr = template.get('friction', '0.3')
        
        f.write(f"    law_name = {name_expr}\n")
        f.write(f"    laws[law_name] = pre.tact_behav(\n")
        f.write(f"        name=law_name,\n")
        f.write(f"        law='{template['law_type']}',\n")
        f.write(f"        fric={friction_expr}\n")
        f.write(f"    )\n")
        f.write(f"    tacts.addBehav(laws[law_name])\n")

    def _write_for_visibility(self, f, template: dict, loop_var: str):
        """Génère une règle de visibilité dans une boucle for"""
        f.write(f"    see_table = pre.see_table(\n")
        f.write(f"        CorpsCandidat='{template['candidate_body']}',\n")
        f.write(f"        candidat='{template['candidate_contactor']}',\n")
        f.write(f"        colorCandidat={template['candidate_color']},\n")
        f.write(f"        CorpsAntagoniste='{template['antagonist_body']}',\n")
        f.write(f"        antagoniste='{template['antagonist_contactor']}',\n")
        f.write(f"        colorAntagoniste={template['antagonist_color']},\n")
        f.write(f"        behav=laws['{template['behavior_name']}'],\n")
        f.write(f"        alert={template.get('alert', 0.1)}\n")
        f.write(f"    )\n")
        f.write(f"    see_tables.addSeeTable(see_table)\n")

    def _write_for_dof(self, f, template: dict, loop_var: str):
        """Génère une opération DOF dans une boucle for"""
        params = template.get('parameters', {})
        params_str = ", ".join(f"{k}={v}" for k, v in params.items())
        
        if template['target_type'] == 'avatar':
            target_expr = template['target_value']
            f.write(f"    bodies_list[{target_expr}].{template['operation_type']}({params_str})\n")
    
    # =======Fin loops génériques
    # ── Granulométrie ─────────────────────────────────────────────────────────
    def _write_granulo(self, f: TextIO):
        if not self.state.granulo_generations:
            return
        
        # Préférence : affichage individuel ou groupes seulement
        show_individually = getattr(
            getattr(self.state, 'preferences', None),
            'show_granulo_individually', True
        )

        f.write('# Génération granulométrique\n')
        for i, gen in enumerate(self.state.granulo_generations):
            f.write(f"# Dépôt granulo {i+1}  : {gen.color}----\n")
            
            container_params_str = ', '.join(f"{k}={v}" for k, v in gen.container_params.items())
            
            f.write(f"radii_{i} = pre.granulo_Random(\n")
            f.write(f"    nb={gen.nb_particles},\n")
            f.write(f"    r_min={gen.radius_min},\n")
            f.write(f"    r_max={gen.radius_max}")
            if gen.seed:
                f.write(f",\n    seed={gen.seed}")
   
            f.write(f"\n)\n\n")
            # 2. Dépôt dans le conteneur
            deposit_func = _DEPOSIT_FUNC.get(gen.container_type, "depositInBox2D")
            deposit_keys = _DEPOSIT_PARAMS.get(gen.container_type, ["lx", "ly"])

            f.write(f"_nb_remaining, _coords_{i} = pre.{deposit_func}(\n")
            f.write(f"    radii=radii_{i},\n")
            for key in deposit_keys:
                val = gen.container_params.get(key, 1.0)
                f.write(f"    {key}={val},\n")
            f.write(f")\n\n")
            f.write(f"# Reshape coordinates\n")
            f.write(f"_coords_{i}.shape = [_coords_{i}.size//2,2]\n")
            f.write(f"radii_{i} = radii_{i}[:_nb_remaining]\n\n")

            # 3. Boucle for de création des avatars
            f.write(f"# Création des avatars — dépôt {i+1}\n")

            if not show_individually:
                # Pas de stockage individuel : avatars non indexés
                f.write(f"# (avatars non indexés — préférence 'affichage groupes uniquement')\n")
                f.write(f"for j in range(len(radii_{i})):\n")
                f.write(f"    av = pre.{gen.avatar_type}(\n")
                f.write(f"        center=_coords_{i}[j],\n")
                f.write(f"        model=mod_{gen.model_name},\n")
                f.write(f"        material=mat_{gen.material_name},\n")
                f.write(f"        color='{gen.color}',\n")
                f.write(f"        r=float(radii_{i}[j])\n")
                f.write(f"    )\n")
                f.write(f"    bodies.addAvatar(av)\n\n")
            else:
                # Stockage individuel + groupe optionnel
                if gen.group_name:
                    f.write(f"group_{gen.group_name} = []\n")
                f.write(f"for j in range(len(radii_{i})):\n")
                f.write(f"    av = pre.{gen.avatar_type}(\n")
                f.write(f"        center=_coords_{i}[j],\n")
                f.write(f"        model=mod_{gen.model_name},\n")
                f.write(f"        material=mat_{gen.material_name},\n")
                f.write(f"        color='{gen.color}',\n")
                f.write(f"        r=float(radii_{i}[j])\n")
                f.write(f"    )\n")
                f.write(f"    bodies.addAvatar(av)\n")
                f.write(f"    bodies_list.append(av)\n")
                if gen.group_name:
                    f.write(f"    group_{gen.group_name}.append(av)\n")
                f.write(f"\n")

    # ── Lois de contact ───────────────────────────────────────────────────────
    def _write_contact_laws(self, f: TextIO):
        if not self.state.contact_laws:
            return
        
        f.write('# Lois de contact\n')
        for law in self.state.contact_laws:
            f.write(f"law_{law.name} = pre.tact_behav(\n")
            f.write(f"    name='{law.name}',\n")
            f.write(f"    law='{law.law_type.value}'")
            
            if law.friction is not None:
                f.write(f",\n    fric={law.friction}")
            
            if law.properties:
                for key, value in law.properties.items():
                    f.write(',\n    ')
                    if isinstance(value, str):
                        f.write(f"{key}='{value}'")
                    else:
                        f.write(f"{key}={value}")
            
            f.write('\n)\n')
            f.write(f"tacts.addBehav(law_{law.name})\n\n")
    # ── Tables de visibilité ──────────────────────────────────────────────────
    def _write_visibility(self, f: TextIO):
        if not self.state.visibility_rules:
            return
        
        f.write('# Tables de visibilité\n')
        for i, rule in enumerate(self.state.visibility_rules):
            f.write(f"see_{i} = pre.see_table(\n")
            f.write(f"    CorpsCandidat='{rule.candidate_body}',\n")
            f.write(f"    candidat='{rule.candidate_contactor}',\n")
            f.write(f"    colorCandidat='{rule.candidate_color}',\n")
            f.write(f"    CorpsAntagoniste='{rule.antagonist_body}',\n")
            f.write(f"    antagoniste='{rule.antagonist_contactor}',\n")
            f.write(f"    colorAntagoniste='{rule.antagonist_color}',\n")
            f.write(f"    behav=law_{rule.behavior_name},\n")
            f.write(f"    alert={rule.alert}\n")
            f.write(f")\n")
            f.write(f"sees.addSeeTable(see_{i})\n\n")
    # ── Opérations DOF ────────────────────────────────────────────────────────
    def _write_dof_operations(self, f: TextIO):
        if not self.state.operations:
            return
        
        f.write('# Opérations DOF\n')
        for i, op in enumerate(self.state.operations):
            params_str = ', '.join(f"{k}={repr(v)}" for k, v in op.parameters.items())
            
            if op.target_type == 'avatar':
                f.write(f"# DOF sur avatar #{op.target_value}\n")
                f.write(f"bodies[{op.target_value}].{op.operation_type}({params_str})\n\n")
            elif op.target_type == 'group':
                f.write(f"DOF sur groupe '{op.target_value}'\n")
                f.write(f"for av in group_{op.target_value}:\n")
                f.write(f"    av.{op.operation_type}({params_str})\n\n")
    # ── Post-traitement ───────────────────────────────────────────────────────
    def _write_postpro(self, f: TextIO):
        if not self.state.postpro_commands:
            return
        
        f.write('# Post-traitement\n')
        for i, cmd in enumerate(self.state.postpro_commands):
            if cmd.target_type and cmd.target_value is not None:
                f.write(f"# Commande avec cible: {cmd.target_type} = {cmd.target_value}\n")
                f.write(f"# rigid_set = [...]  # À définir selon la cible\n")
                f.write(f"post_cmd_{i} = pre.postpro_command(\n")
                f.write(f"     name='{cmd.name}',\n")
                f.write(f"     step={cmd.step},\n")
                if cmd.target_type == 'avatar':
                    f.write(f"     rigid_set=[bodies[{cmd.target_value}]]\n")
                elif cmd.target_type == 'group':
                    #récupérer les indices des avatars du groupe
                    f.write(f"     rigid_set = [bodies[i] for i in group_{cmd.target_value}]\n")
                
                f.write(f" )\n")
                f.write(f"posts.addCommand(post_cmd_{i})\n")
            else:
                f.write(f"post_cmd_{i} = pre.postpro_command(\n")
                f.write(f"    name='{cmd.name}',\n")
                f.write(f"    step={cmd.step}\n")
                f.write(f")\n")
                f.write(f"posts.addCommand(post_cmd_{i})\n")
            f.write('\n')
    # ── DATBOX ────────────────────────────────────────────────────────────────
    def _write_datbox(self, f: TextIO):
        f.write('# Génération DATBOX\n')
        f.write(f"pre.writeDatbox(\n")
        f.write(f"    dim={self.state.dimension},\n")
        f.write(f"    mats=mats,\n")
        f.write(f"    mods=mods,\n")
        f.write(f"    bodies=bodies,\n")
        f.write(f"    tacts=tacts,\n")
        f.write(f"    sees=sees,\n")
        f.write(f"    post=posts,\n")
        f.write(f"    datbox_path='DATBOX'\n")
        f.write(f")\n\n")
        f.write(f"print('DATBOX généré avec succès!')\n")
   
    #── Utilitaire ────────────────────────────────────────────────────────────
    def _format_value(self, value):
        """Formate une valeur pour Python"""
        import numpy as np
        if isinstance(value, str):
            return f"{value}"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, bool):
            return "True" if value else "False"
        elif isinstance(value, np.ndarray):
            return value.tolist()
        else :      
            return value