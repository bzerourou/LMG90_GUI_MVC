"""
Générateur de scripts Python pour LMGC90.
Permet de créer des scripts reproductibles depuis l'état du projet.

=== REFACTOR "avatar_id stable" ===
- avatar_groups contient des avatar_ids (str), plus des positions (int)
- Loop.model_avatar_id remplace Loop.model_avatar_index
- DOFOperation.target_value et PostProCommand.target_value pour 'avatar'
  contiennent des avatar_id (str) ; on les résout en index via _id_to_idx()
"""

from pathlib import Path
from typing import TextIO, Dict

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

# Correspondance conteneur → clés de paramètres attendus
_DEPOSIT_PARAMS = {
    "Box2D":      ["lx", "ly"],
    "Disk2D":     ["r"],
    "Couette2D":  ["rint", "rext"],
    "Drum2D":     ["r"],
    "Box3D":      ["lx", "ly", "lz"],
    "Sphere3D":   ["r"],
    "Cylinder3D": ["r"],
}

_MASONRY_WALL_KEYS = {'lz', 'brick_name'}


class ScriptGenerator:
    """Génère un script Python reproductible du projet."""

    def __init__(self, controller: ProjectController):
        self.controller = controller
        self.state = controller.state
        self._written_group_vars: set[str] = set()

    @property
    def _use_loop(self) -> bool:
        """True → boucles compactes ; False → élément par élément."""
        return bool(getattr(
            getattr(self.state, 'preferences', None),
            'script_use_loop', True
        ))

    # ── Utilitaire central : avatar_id → index ────────────────────────────────

    def _id_to_idx(self) -> Dict[str, int]:
        """
        Construit et retourne un dict avatar_id → position dans state.avatars.
        À appeler au début de chaque méthode qui résout des références avatar.
        """
        return {av.avatar_id: i for i, av in enumerate(self.state.avatars)}

    def generate(self, output_path: Path) -> None:
        """Génère le script complet."""
        with open(output_path, 'w', encoding='utf-8') as f:
            self._write_header(f)
            self._write_imports(f)
            self._write_numpy_compatibility_shim(f)
            self._write_dynamic_vars(f)
            self._write_containers(f)
            self._write_materials(f)
            self._write_models(f)
            self._write_avatars_manual(f)
            self._write_for_loops(f)
            self._write_loops(f)
            self._write_granulo(f)
            self._write_avatar_groups(f)
            self._write_contact_laws(f)
            self._write_visibility(f)
            self._write_dof_operations(f)
            self._write_postpro(f)
            self._write_factories(f)
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
        f.write('import copy\n\n')

    def _write_numpy_compatibility_shim(self, f: TextIO):
        """Compatibilité NumPy 2.x / pylmgc90 2D pour les axes rigides.

        Pour les vecteurs plans (2D), l’API LMGC90 utilise le signe du
        produit vectoriel 2D, c’est-à-dire un scalaire :
            a.x * b.y - a.y * b.x
        Le code de pylmgc90 compare ensuite ce résultat à 0.0.
        """
        f.write('# Compatibilité NumPy 2.x + pylmgc90 2D\n')
        f.write('_np_cross = np.cross\n')
        f.write('def _lmgc90_safe_cross(a, b, *args, **kwargs):\n')
        f.write('    a = np.asarray(a, dtype=float)\n')
        f.write('    b = np.asarray(b, dtype=float)\n')
        f.write('    if a.shape[-1] == 2 and b.shape[-1] == 2:\n')
        f.write('        return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]\n')
        f.write('    return _np_cross(a, b, *args, **kwargs)\n')
        f.write('np.cross = _lmgc90_safe_cross\n\n')

    # ── Variables dynamiques ──────────────────────────────────────────────────

    def _write_dynamic_vars(self, f: TextIO):
        dyn_vars = getattr(self.state, 'dynamic_vars', {}) or {}
        if not dyn_vars:
            return

        f.write('# ── Variables dynamiques ─────────────────────────────────────\n')

        from ..utils.safe_eval import build_eval_context
        full_ctx   = build_eval_context(self.controller)
        evaluated: dict = {}
        written    = 0

        for var_name, var_expr in dyn_vars.items():
            if not var_name.isidentifier():
                f.write(f'# Variable ignorée (nom invalide) : {var_name!r}\n')
                continue

            raw_value = var_expr
            if isinstance(var_expr, str):
                try:
                    ctx = {**full_ctx, **evaluated}
                    raw_value = eval(var_expr, {"__builtins__": {}}, ctx)
                except Exception:
                    raw_value = var_expr

            evaluated[var_name] = raw_value

            script_value = self._format_dynamic_var_value(raw_value)
            if script_value is not None:
                f.write(f'{var_name} = {script_value}\n')
                written += 1
            else:
                f.write(
                    f'# {var_name} = {var_expr!r}'
                    f'  # valeur non sérialisable — à recalculer\n'
                )

        if written > 0:
            f.write('\n')

    def _format_dynamic_var_value(self, value) -> 'str | None':
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
        return None

    # ── Conteneurs ────────────────────────────────────────────────────────────

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
                for key, value in mat.properties.items():
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
                for key, value in mod.options.items():
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
        if self._use_loop:
            self._write_avatars_manual_loop(f)
        else:
            for av in manual_avatars:
                self._write_single_avatar(f, av, "bodies")
        f.write('\n')

    def _write_avatars_manual_loop(self, f: TextIO):
        """
        Regroupe les avatars manuels par groupe (avatar_groups).
        Les groupes contiennent désormais des avatar_ids (str).
        """
        # Résolution avatar_id → index
        id_to_idx       = self._id_to_idx()
        avatar_groups   = getattr(self.state, 'avatar_groups', {}) or {}
        written_indices: set = set()

        for group_name, avatar_ids in avatar_groups.items():
            group_avs = []
            for aid in avatar_ids:
                idx = id_to_idx.get(aid)
                if idx is not None and idx < len(self.state.avatars):
                    av = self.state.avatars[idx]
                    if av.origin == AvatarOrigin.MANUAL:
                        group_avs.append((idx, av))
            if not group_avs:
                continue
            ok = self._try_write_group_as_loop(f, group_name, group_avs)
            if ok:
                written_indices.update(idx for idx, _ in group_avs)

        # Avatars manuels restants (hors groupe ou groupe hétérogène)
        for i, av in enumerate(self.state.avatars):
            if av.origin != AvatarOrigin.MANUAL:
                continue
            if i in written_indices:
                continue
            self._write_single_avatar(f, av, "bodies")

    def _try_write_group_as_loop(
        self, f: TextIO, group_name: str, group_avs: list
    ) -> bool:
        if not group_avs:
            return False
        _, ref  = group_avs[0]
        atype   = ref.avatar_type.value

        # Briques de maçonnerie
        if (atype == "emptyAvatar"
                and ref.wall_params
                and 'l' in ref.wall_params
                and 'h' in ref.wall_params):
            wp0 = ref.wall_params
            for _, av in group_avs[1:]:
                wp = av.wall_params or {}
                if (av.material_name     != ref.material_name
                        or av.model_name != ref.model_name
                        or av.color      != ref.color
                        or wp.get('brick_name') != wp0.get('brick_name')
                        or wp.get('l')   != wp0.get('l')
                        or wp.get('h')   != wp0.get('h')
                        or wp.get('lz')  != wp0.get('lz')):
                    return False
            self._write_masonry_group_loop(f, group_name, group_avs)
            return True

        # Avatars standards homogènes
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

        return False

    def _write_masonry_group_loop(
        self, f: TextIO, group_name: str, group_avs: list
    ):
        _, ref = group_avs[0]
        safe   = group_name.replace(' ', '_').replace('-', '_')
        masonry_patterns = getattr(self.state, 'masonry_patterns', {}) or {}
        mp = masonry_patterns.get(group_name)

        if mp:
            self._write_masonry_pattern_loop(f, group_name, safe, mp)
        else:
            self._write_masonry_centers_loop(f, group_name, safe, group_avs,
                                              ref.wall_params, ref)

    def _write_masonry_pattern_loop(
        self, f: TextIO, group_name: str, safe: str, mp: dict
    ):
        pattern  = mp['pattern']
        lx       = mp['lx']
        ly       = mp['ly']
        lz       = mp.get('lz')
        nb_rows  = mp['nb_rows']
        nb_cols  = mp['nb_cols']
        offset_x = mp['offset_x']
        offset_y = mp['offset_y']
        offset_z = mp.get('offset_z', 0.0)
        joint    = mp['joint']
        bname    = mp['brick_name']
        mat      = mp['mat']
        mod      = mp['mod']
        color    = mp['color']
        dim      = mp['dim']
        _lz      = lz if lz is not None else ly

        f.write(f"# Mur de maçonnerie : {group_name}"
                f" — pattern '{pattern}' ({nb_rows} rangs x {nb_cols} cols)\n")

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

        elif pattern in ('Paneresse simple (pylmgc90)', 'Paneresse double (pylmgc90)'):
            disposition = mp.get('disposition',    'paneresse')
            first_type  = mp.get('first_type',     '1')
            use_length  = mp.get('pan_use_length', False)
            pan_length  = mp.get('pan_length',     1.0)
            no_half     = mp.get('pan_no_half',    False)
            wall_fn     = ('paneresse_double' if 'double' in pattern
                           else 'paneresse_simple')
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

        f.write('\n')

    def _write_masonry_centers_loop(
        self, f: TextIO, group_name: str, safe: str,
        group_avs: list, wp: dict, ref
    ):
        brick_name = wp.get('brick_name', 'std')
        bx  = wp['l']
        by  = wp['h']
        bz  = wp.get('lz')
        mat   = ref.material_name
        mod   = ref.model_name
        color = ref.color
        dim   = len(ref.center)

        f.write(f"# Groupe maçonnerie (fallback) : {group_name} ({len(group_avs)} briques)\n")
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
        _, ref = group_avs[0]
        safe = group_name.replace(' ', '_').replace('-', '_')

        lines = ['[']
        for _, av in group_avs:
            lines.append(f'    {list(av.center)},')
        lines.append(']')
        centers_repr = '\n'.join(lines)

        f.write(f'# Groupe : {group_name} ({len(group_avs)} avatars)\n')
        f.write(f'_centers_{safe} = {centers_repr}\n\n')
        f.write(f'for _c in _centers_{safe}:\n')
        args = self._build_avatar_args(ref, center_expr='_c')
        f.write(f"    body = pre.{ref.avatar_type.value}(\n")
        for i, arg in enumerate(args):
            f.write(f"        {arg}")
            if i < len(args) - 1:
                f.write(",\n")
            else:
                f.write("\n")
        f.write("    )\n")
        f.write("    bodies.addAvatar(body)\n")
        f.write("    bodies_list.append(body)\n")
        f.write('\n')

    def _build_avatar_args(self, avatar, center_expr: str | None = None) -> list[str]:
        """Construit la liste des arguments d’appel pylmgc90 pour un avatar."""
        center_value = center_expr if center_expr is not None else self._format_value(avatar.center)
        args = [
            f"center={center_value}",
            f"model=mods['{avatar.model_name}']",
            f"material=mats['{avatar.material_name}']",
            f"color='{avatar.color}'"
        ]

        has_r_in_wall_params = False
        if avatar.wall_params:
            for k, v in avatar.wall_params.items():
                if k in _MASONRY_WALL_KEYS:
                    continue
                args.append(f"{k}={v}")
                if k == 'r':
                    has_r_in_wall_params = True

        exclude_r = False
        if avatar.avatar_type in [AvatarType.RIGID_POLYGON, AvatarType.RIGID_POLYHEDRON]:
            if avatar.generation_type in ["full", "bevel"]:
                exclude_r = True

        if avatar.radius and not has_r_in_wall_params and not exclude_r:
            if avatar.avatar_type in [AvatarType.RIGID_POLYGON, AvatarType.RIGID_POLYHEDRON]:
                args.append(f"radius={avatar.radius}")
            else:
                args.append(f"r={avatar.radius}")

        if avatar.axis:
            args.append(f"axe1={avatar.axis['axe1']}")
            args.append(f"axe2={avatar.axis['axe2']}")
            if 'axe3' in avatar.axis:
                args.append(f"axe3={avatar.axis['axe3']}")

        if avatar.generation_type:
            args.append(f"generation_type='{avatar.generation_type}'")

        if avatar.nb_vertices:
            if avatar.avatar_type == AvatarType.RIGID_CLUSTER:
                args.append(f"nb_disk={avatar.nb_vertices}")
            else:
                args.append(f"nb_vertices={avatar.nb_vertices}")

        if avatar.vertices:
            args.append(f"vertices=np.array({avatar.vertices})")

        if avatar.is_hollow:
            args.append("is_Hollow=True")

        return args

    def _write_single_avatar(self, f, avatar, container="bodies"):
        """Écrit un avatar individuel."""
        atype  = avatar.avatar_type.value
        center = self._format_value(avatar.center)
        mat    = avatar.material_name
        mod    = avatar.model_name
        color  = avatar.color

        # Corps déformable (MESH_DEFORMABLE)
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
            if avatar.contactors:
                for cont in avatar.contactors:
                    shape  = cont['shape']
                    color  = cont.get('color', 'BLEUx')
                    group  = cont.get('group')
                    params = cont.get('params', {})
                    kwargs = f"shape='{shape}', color='{color}'"
                    if group:
                        kwargs += f", group='{group}'"
                    for k, v in params.items():
                        kwargs += f", {k}={repr(v)}"
                    f.write(f"body.addContactors({kwargs})\n")
            f.write("\n")
            return

        # Brique de maçonnerie
        if atype == "emptyAvatar" and avatar.wall_params and \
                'l' in avatar.wall_params and 'h' in avatar.wall_params:
            wp         = avatar.wall_params
            brick_name = wp.get('brick_name', 'std')
            bx         = wp['l']
            by         = wp['h']
            bz         = wp.get('lz')
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

        # emptyAvatar avec contacteurs personnalisés
        if atype == "emptyAvatar":
            f.write(f"# Avatar vide avec contacteurs personnalisés\n")
            f.write(f"body = pre.avatar(dimension={self.state.dimension})\n")
            if len(center) == 2:
                f.write(f"body.addBulk(pre.rigid2d())\n")
            else:
                f.write(f"body.addBulk(pre.rigid3d())\n")
            f.write(f"body.addNode(pre.node(coor=np.array({center}), number=1))\n")
            f.write(f"body.defineGroups()\n")
            f.write(f"body.defineModel(model=mods['{mod}'])\n")
            f.write(f"body.defineMaterial(material=mats['{mat}'])\n")
            for cont in avatar.contactors:
                shape   = cont['shape']
                color_c = cont.get('color', color)
                params  = cont.get('params', {})
                params_str = ", ".join(f"{k}={repr(v)}" for k, v in params.items())
                f.write(f"body.addContactors(shape='{shape}', color='{color_c}'")
                if params_str:
                    f.write(f", {params_str}")
                f.write(f")\n")
            f.write(f"body.computeRigidProperties()\n")
            f.write(f"{container}.addAvatar(body)\n")
            f.write("bodies_list.append(body)\n\n")
            return

        # Avatars standards
        args = self._build_avatar_args(avatar)

        f.write(f"body = pre.{atype}(\n")
        for i, arg in enumerate(args):
            if "None" not in arg:
                f.write(f"    {arg}")
                if i < len(args) - 1:
                    f.write(",\n")
                else:
                    f.write("\n")
        f.write(")\n")
        f.write(f"{container}.addAvatar(body)\n")
        f.write("bodies_list.append(body)\n\n")

    # ── Boucles géométriques ──────────────────────────────────────────────────

    def _write_loops(self, f: TextIO):
        if not self.state.loops:
            return

        # Résolution avatar_id → index (model_avatar_id remplace model_avatar_index)
        id_to_idx = self._id_to_idx()

        f.write('# Boucles\n')
        for i, loop in enumerate(self.state.loops):
            f.write(f"# Boucle {i + 1}: {loop.loop_type}\n")

            # Résoudre l'avatar modèle par son id stable
            _idx = id_to_idx.get(loop.model_avatar_id)
            if _idx is None:
                f.write(
                    f"# ⚠️  Boucle {i + 1} ignorée : avatar modèle "
                    f"'{loop.model_avatar_id[:8]}…' introuvable\n\n"
                )
                continue
            model_avatar = self.state.avatars[_idx]

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

            indent = "        " if loop.loop_type == "Grille" else "    "

            f.write(f"{indent}center = {center_calc}\n")
            args = self._build_avatar_args(model_avatar, center_expr="center")
            f.write(f"{indent}av = pre.{model_avatar.avatar_type.value}(\n")
            for i, arg in enumerate(args):
                f.write(f"{indent}    {arg}")
                if i < len(args) - 1:
                    f.write(",\n")
                else:
                    f.write("\n")
            f.write(f"{indent})\n")
            f.write(f"{indent}bodies.addAvatar(av)\n\n")

    # ── Boucles For génériques ────────────────────────────────────────────────

    def _write_for_loops(self, f):
        if not hasattr(self.state, 'for_loops') or not self.state.for_loops:
            return
        f.write("# Boucles for génériques\n")
        for idx, for_loop in enumerate(self.state.for_loops):
            f.write(f"# Boucle For {idx + 1} : {for_loop.target_type}\n")
            f.write(f"for {for_loop.loop_var} in range({for_loop.start_expr}, {for_loop.end_expr}, {for_loop.step_expr}):\n")
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
            elif for_loop.target_type == "granulo":
                self._write_for_granulo(f, template, for_loop.loop_var)
            else:
                f.write(f"    # ⚠️ Type cible non supporté : {for_loop.target_type}\n")
            f.write("\n")

    def _write_for_avatar(self, f, template: dict, loop_var: str):
        atype      = template['avatar_type']
        center_expr = template.get('center', '[0, 0]')
        radius_expr = template.get('radius', '0.1')
        f.write(f"    # Évaluer les paramètres avec {loop_var}\n")
        f.write(f"    center = {center_expr}\n")
        if atype == "emptyAvatar":
            f.write(f"    body = pre.avatar(dimension=len(center))\n")
            f.write(f"    body.addBulk(pre.rigid2d() if len(center) == 2 else pre.rigid3d())\n")
            f.write(f"    body.addNode(pre.node(coor=np.array(center), number=1))\n")
            f.write(f"    body.defineGroups()\n")
            f.write(f"    body.defineModel(model=mods['{template['model_name']}'])\n")
            f.write(f"    body.defineMaterial(material=mats['{template['material_name']}'])\n")
            if 'contactors' in template:
                for cont in template['contactors']:
                    shape      = cont['shape']
                    color      = cont.get('color', template.get('color', 'BLUEx'))
                    params     = cont.get('params', {})
                    params_str = ", ".join(f"{k}={repr(v)}" for k, v in params.items())
                    f.write(f"    body.addContactors(shape='{shape}', color='{color}'")
                    if params_str:
                        f.write(f", {params_str}")
                    f.write(f")\n")
            f.write(f"    body.computeRigidProperties()\n")
            f.write(f"    bodies.addAvatar(body)\n")
            f.write(f"    bodies_list.append(body)\n")
        else:
            f.write(f"    body = pre.{atype}(\n")
            f.write(f"        center=center,\n")
            f.write(f"        model=mods['{template['model_name']}'],\n")
            f.write(f"        material=mats['{template['material_name']}'],\n")
            f.write(f"        color='{template.get('color', 'BLUEx')}'")
            if 'radius' in template:
                f.write(f",\n        r={radius_expr}")
            if 'wall_params' in template and 'h' in template['wall_params']:
                f.write(f",\n        h={template['wall_params']['h']}")
            if template.get('is_hollow'):
                f.write(",\n        is_Hollow=True")
            if 'axis' in template:
                for k, v in template['axis'].items():
                    f.write(f",\n        {k}={v}")
            f.write(f"\n    )\n")
            f.write(f"    bodies.addAvatar(body)\n")
            f.write(f"    bodies_list.append(body)\n")

    def _write_for_material(self, f, template: dict, loop_var: str):
        f.write(f"    mat_name = {template['name']}\n")
        f.write(f"    density_val = {template.get('density', '2800')}\n")
        f.write(f"    mats[mat_name] = pre.material(\n")
        f.write(f"        name=mat_name,\n")
        f.write(f"        materialType='{template['material_type']}',\n")
        f.write(f"        density=density_val\n")
        f.write(f"    )\n")
        f.write(f"    materials.addMaterial(mats[mat_name])\n")

    def _write_for_model(self, f, template: dict, loop_var: str):
        f.write(f"    mod_name = {template['name']}\n")
        f.write(f"    mods[mod_name] = pre.model(\n")
        f.write(f"        name=mod_name,\n")
        f.write(f"        physics='{template['physics']}',\n")
        f.write(f"        element='{template['element']}',\n")
        f.write(f"        dimension={template['dimension']}\n")
        f.write(f"    )\n")
        f.write(f"    models.addModel(mods[mod_name])\n")

    def _write_for_contact_law(self, f, template: dict, loop_var: str):
        law_name = template.get('name', "'LAW'+str(%s)" % loop_var)
        law_type = template.get('law_type', template.get('law', 'IQS_CLB'))
        friction = template.get('friction', template.get('fric', '0.3'))
        f.write(f"    law_name = {law_name}\n")
        f.write(f"    laws[law_name] = pre.tact_behav(\n")
        f.write(f"        name=law_name,\n")
        f.write(f"        law='{law_type}',\n")
        f.write(f"        fric={friction}\n")
        f.write(f"    )\n")
        f.write(f"    tacts.addBehav(laws[law_name])\n")

    def _write_for_visibility(self, f, template: dict, loop_var: str):
        candidate_body = template.get('candidate_body', template.get('CorpsCandidat', "'RBDY2'"))
        candidate_contactor = template.get('candidate_contactor', template.get('candidat', "'DISKx'"))
        candidate_color = template.get('candidate_color', template.get('colorCandidat', "'BLUEx'"))
        antagonist_body = template.get('antagonist_body', template.get('CorpsAntagoniste', "'RBDY2'"))
        antagonist_contactor = template.get('antagonist_contactor', template.get('antagoniste', "'DISKx'"))
        antagonist_color = template.get('antagonist_color', template.get('colorAntagoniste', "'REDxx'"))
        behavior_name = template.get('behavior_name', template.get('behav', "'LAW01'"))
        alert = template.get('alert', 0.1)
        f.write(f"    see_table = pre.see_table(\n")
        f.write(f"        CorpsCandidat={candidate_body},\n")
        f.write(f"        candidat={candidate_contactor},\n")
        f.write(f"        colorCandidat={candidate_color},\n")
        f.write(f"        CorpsAntagoniste={antagonist_body},\n")
        f.write(f"        antagoniste={antagonist_contactor},\n")
        f.write(f"        colorAntagoniste={antagonist_color},\n")
        f.write(f"        behav=laws[{behavior_name}],\n")
        f.write(f"        alert={alert}\n")
        f.write(f"    )\n")
        f.write(f"    sees.addSeeTable(see_table)\n")

    def _write_for_dof(self, f, template: dict, loop_var: str):
        operation_type = template.get('operation_type', template.get('dof', template.get('type', 'translate')))
        target_type = template.get('target_type', template.get('target', 'group'))
        target_value = template.get('target_value', template.get('target_id', 'all'))
        params = template.get('parameters', template.get('params', {}))
        if not params:
            params = {
                key: template[key]
                for key in ('component', 'dofty', 'ct', 'amp', 'omega', 'phi', 'dx', 'dy', 'dz')
                if key in template
            }
        params_str = ', '.join(f"{k}={v}" for k, v in params.items())
        if target_type == 'avatar':
            f.write(f"    bodies[{target_value}].{operation_type}({params_str})\n")
        else:
            f.write(f"    for av in group_{str(target_value).replace(' ', '_').replace('-', '_')}:\n")
            f.write(f"        av.{operation_type}({params_str})\n")

    def _write_for_granulo(self, f, template: dict, loop_var: str):
        nb_particles = template.get('nb_particles', 1)
        radius_min = template.get('radius_min', 0.04)
        radius_max = template.get('radius_max', 0.05)
        container_type = template.get('container_type', 'Box2D')
        container_params = template.get('container_params', {})
        material_name = template.get('material_name', 'TDURx')
        model_name = template.get('model_name', 'rigid')
        avatar_type = template.get('avatar_type', 'rigidDisk')
        color = template.get('color', 'BLUEx')
        seed = template.get('seed')

        params_list = []
        for key, value in container_params.items():
            params_list.append(f"    {key}={value},")
        params_block = "\n".join(params_list)

        f.write(f"    radii = pre.granulo_Random(\n")
        f.write(f"        nb={nb_particles},\n")
        f.write(f"        r_min={radius_min},\n")
        f.write(f"        r_max={radius_max}\n")
        if seed is not None:
            f.write(f"        , seed={seed}\n")
        f.write(f"    )\n\n")
        f.write(f"    _nb_remaining, _coords, _radii = pre.{_DEPOSIT_FUNC.get(container_type, 'depositInBox2D')}(\n")
        f.write(f"        radii=radii,\n")
        if params_block:
            f.write(f"{params_block}\n")
        f.write(f"    )\n")
        f.write(f"    _coords = np.asarray(_coords, dtype=float).reshape(-1, {self.state.dimension})\n")
        f.write(f"    radii = np.asarray(_radii, dtype=float).reshape(-1)\n")
        f.write(f"    for j in range(len(radii)):\n")
        f.write(f"        av = pre.{avatar_type}(\n")
        f.write(f"            center=_coords[j],\n")
        f.write(f"            model=mods['{model_name}'],\n")
        f.write(f"            material=mats['{material_name}'],\n")
        f.write(f"            color='{color}',\n")
        f.write(f"            r=float(radii[j])\n")
        f.write(f"        )\n")
        f.write(f"        bodies.addAvatar(av)\n")
        f.write(f"        bodies_list.append(av)\n")


    # ── Granulométrie ─────────────────────────────────────────────────────────

    def _write_granulo(self, f: TextIO):
        if not self.state.granulo_generations:
            return
        show_individually = getattr(
            getattr(self.state, 'preferences', None),
            'show_granulo_individually', True
        )
        f.write('# Génération granulométrique\n')
        for i, gen in enumerate(self.state.granulo_generations):
            if gen.container_type == "Distribution" or gen.container_params.get("distribution_only"):
                f.write(
                    f"# Distribution {i + 1} (rayons seuls, sans dépôt) — "
                    f"non reproduite dans le script\n\n"
                )
                continue
            f.write(f"# Dépôt granulo {i + 1}  : {gen.color}----\n")
            f.write(f"radii_{i} = pre.granulo_Random(\n")
            f.write(f"    nb={gen.nb_particles},\n")
            f.write(f"    r_min={gen.radius_min},\n")
            f.write(f"    r_max={gen.radius_max}")
            if gen.seed:
                f.write(f",\n    seed={gen.seed}")
            f.write(f"\n)\n\n")

            deposit_func = _DEPOSIT_FUNC.get(gen.container_type, "depositInBox2D")
            deposit_keys = _DEPOSIT_PARAMS.get(gen.container_type, ["lx", "ly"])
            f.write(f"_nb_remaining, _coords_{i}, _radii_{i} = pre.{deposit_func}(\n")
            f.write(f"    radii=radii_{i},\n")
            for key in deposit_keys:
                val = gen.container_params.get(key, 1.0)
                f.write(f"    {key}={val},\n")
            f.write(f")\n\n")
            f.write(f"# Reshape coordinates\n")
            f.write(f"_coords_{i} = np.asarray(_coords_{i}, dtype=float).reshape(-1, {self.state.dimension})\n")
            f.write(f"radii_{i} = np.asarray(_radii_{i}, dtype=float).reshape(-1)\n")

            f.write(f"# Création des avatars — dépôt {i + 1}\n")
            if not show_individually:
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
                if gen.group_name:
                    safe_group = gen.group_name.replace(' ', '_').replace('-', '_')
                    self._written_group_vars.add(safe_group)
                    f.write(f"if 'group_{safe_group}' not in globals():\n")
                    f.write(f"    group_{safe_group} = []\n")
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
                    safe_group = gen.group_name.replace(' ', '_').replace('-', '_')
                    f.write(f"    group_{safe_group}.append(av)\n")
                f.write(f"\n")


    # ── Groupes d'avatars (résolution unique, source unique de vérité) ───────

    def _write_avatar_groups(self, f: TextIO):
        """
        Résout chaque groupe de state.avatar_groups en une liste d'objets
        pylmgc90 dans ``group_<nom_safe>``.

        Les références peuvent être soit des avatar_id (nouveau format), soit
        des indices historiques (compatibilité legacy). On les normalise vers
        des indices de ``state.avatars`` avant d’écrire le script final.
        """
        groups = getattr(self.state, 'avatar_groups', {}) or {}
        if not groups:
            return

        id_to_idx = self._id_to_idx()

        f.write('# ── Groupes d\'avatars ───────────────────────────────────\n')
        for group_name, refs in groups.items():
            safe = group_name.replace(' ', '_').replace('-', '_')
            indices = []
            missing = 0

            for ref in refs:
                if isinstance(ref, int):
                    idx = ref
                elif isinstance(ref, str):
                    idx = id_to_idx.get(ref)
                else:
                    idx = None

                if idx is not None and 0 <= idx < len(self.state.avatars):
                    indices.append(idx)
                else:
                    missing += 1

            if missing:
                f.write(
                    f"# ⚠️  Groupe '{group_name}' : {missing} avatar(s) "
                    f"introuvable(s) — ignoré(s)\n"
                )

            if safe in self._written_group_vars:
                f.write(f"group_{safe}.extend([bodies[i] for i in {indices}])\n")
                self._written_group_vars.add(safe)
                continue

            f.write(f"group_{safe} = [bodies[i] for i in {indices}]\n")
            self._written_group_vars.add(safe)
        f.write('\n')


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

        # Résolution avatar_id → index pour toutes les opérations en une passe
        id_to_idx = self._id_to_idx()

        f.write('# Opérations DOF\n')
        for i, op in enumerate(self.state.operations):
            params_str = ', '.join(f"{k}={repr(v)}" for k, v in op.parameters.items())

            if op.target_type == 'avatar':
                # target_value est désormais un avatar_id (str)
                idx = id_to_idx.get(op.target_value)
                if idx is not None:
                    f.write(f"# DOF sur avatar #{idx}\n")
                    f.write(f"bodies[{idx}].{op.operation_type}({params_str})\n\n")
                else:
                    f.write(
                        f"# ⚠️  DOF ignoré : avatar '{op.target_value[:8]}…' introuvable\n\n"
                    )

            elif op.target_type == 'group':
                safe = op.target_value.replace(' ', '_').replace('-', '_')
                f.write(f"# DOF sur groupe '{op.target_value}'\n")
                f.write(f"for av in group_{safe}:\n")
                f.write(f"    av.{op.operation_type}({params_str})\n\n")

    # ── Post-traitement ───────────────────────────────────────────────────────

    def _write_postpro(self, f: TextIO):
        if not self.state.postpro_commands:
            return

        # Résolution avatar_id → index
        id_to_idx = self._id_to_idx()

        f.write('# Post-traitement\n')
        for i, cmd in enumerate(self.state.postpro_commands):
            if cmd.target_type and cmd.target_value is not None:
                f.write(f"post_cmd_{i} = pre.postpro_command(\n")
                f.write(f"     name='{cmd.name}',\n")
                f.write(f"     step={cmd.step},\n")

                if cmd.target_type == 'avatar':
                    idx = id_to_idx.get(cmd.target_value)
                    if idx is not None:
                        f.write(f"     rigid_set=[bodies[{idx}]]\n")
                    else:
                        f.write(
                            f"     # ⚠️  avatar '{cmd.target_value[:8]}…' introuvable\n"
                        )
                elif cmd.target_type == 'group':
                    safe = cmd.target_value.replace(' ', '_').replace('-', '_')
                    f.write(f"     rigid_set=[bodies[i] for i in group_{safe}]\n")

                f.write(f")\n")
                f.write(f"posts.addCommand(post_cmd_{i})\n")
            else:
                f.write(f"post_cmd_{i} = pre.postpro_command(\n")
                f.write(f"    name='{cmd.name}',\n")
                f.write(f"    step={cmd.step}\n")
                f.write(f")\n")
                f.write(f"posts.addCommand(post_cmd_{i})\n")
            f.write('\n')

    # ── Particle Factories ────────────────────────────────────────────────────

    def _write_factories(self, f: TextIO) -> None:
        factories = getattr(self.state, 'factories', None) or []
        if not factories:
            return
        try:
            from ..core.particle_factory import ParticleFactory
        except ImportError:
            f.write('# particle_factory.py introuvable\n')
            return

        engine      = ParticleFactory.from_list_of_dicts(factories)
        nb_existing = len(self.state.avatars)
        engine.freeze_body_indices(body_counter_start=nb_existing + 1)

        if self.controller is not None:
            self.controller.state.factories = engine.to_list_of_dicts()

        pre_code = engine.generate_pre_code(body_counter_start=nb_existing + 1)
        f.write('\n')
        f.write('# ============================================================\n')
        f.write('# Avatars (Particles Factories) créés invisibles\n')
        f.write('# ============================================================\n')
        f.write(pre_code)
        pickle_code = engine.generate_pickle_code(dimension=self.state.dimension)
        if pickle_code:
            f.write(pickle_code)

            meta_code = engine.generate_bodies_list_code()
            if meta_code:
                f.write(meta_code)
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

    # ── Utilitaire ────────────────────────────────────────────────────────────

    def _format_value(self, value):
        import numpy as np
        if isinstance(value, str):
            return f"{value}"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, bool):
            return "True" if value else "False"
        elif isinstance(value, np.ndarray):
            return value.tolist()
        else:
            return value