"""ForLoopsMixin — boucles For génériques (avatar, material, model, granulo)."""
import math
from typing import Optional, List

from ..core.models import (
    Avatar, AvatarOrigin, AvatarType,
    ForLoop, GranuloGeneration,
)
from ..core.generators import GranuloGenerator
from ..utils.safe_eval import SafeEvaluator


_BASE_CONTEXT = {
    'math':  math,
    'sqrt':  math.sqrt,
    'pi':    math.pi,
    'e':     math.e,
    'abs':   abs,
    'min':   min,
    'max':   max,
    'sum':   sum,
    'len':   len,
    'str':   str,
    'int':   int,
    'float': float,
}


class ForLoopsMixin:

    # ── Génération ────────────────────────────────────────────────────────────

    def generate_for_loop(self, for_loop: ForLoop) -> List[int]:
        """
        Génère des éléments selon une boucle For.
        Les avatars produits sont référencés par avatar_id dans generated_refs.
        """
        evaluator = SafeEvaluator()

        # ── Cas granulo ───────────────────────────────────────────────────────
        if for_loop.target_type == 'granulo':
            return self._generate_for_granulo(for_loop, evaluator)

        # ── Boucle For classique ──────────────────────────────────────────────
        evaluator.allowed_names = _BASE_CONTEXT
        start = evaluator.eval_expression(for_loop.start_expr)
        end   = evaluator.eval_expression(for_loop.end_expr)
        step  = evaluator.eval_expression(for_loop.step_expr)

        generated_indices = []
        current           = start
        loop_var          = for_loop.loop_var

        while (step > 0 and current < end) or (step < 0 and current > end):
            ctx = {**_BASE_CONTEXT, loop_var: current}
            evaluator.allowed_names = ctx

            evaluated = {}
            for key, value in for_loop.template_config.items():
                if isinstance(value, str):
                    try:
                        evaluated[key] = evaluator.eval_expression(value)
                    except (ValueError, NameError, SyntaxError):
                        if any(op in value for op in [
                            '+', '-', '*', '/', '(', '[',
                            'str(', 'int(', 'float(', 'math.',
                        ]):
                            raise
                        else:
                            evaluated[key] = value
                else:
                    evaluated[key] = value

            if for_loop.target_type == 'avatar':
                avatar = Avatar(
                    avatar_type     = AvatarType(evaluated['avatar_type']),
                    center          = evaluated['center'],
                    material_name   = evaluated.get('material_name', 'TDURx'),
                    model_name      = evaluated.get('model_name', 'rigid'),
                    color           = evaluated.get('color', 'BLUEx'),
                    origin          = AvatarOrigin.LOOP,
                    radius          = evaluated.get('radius'),
                    axis            = evaluated.get('axis'),
                    vertices        = evaluated.get('vertices'),
                    nb_vertices     = evaluated.get('nb_vertices'),
                    generation_type = evaluated.get('generation_type'),
                    is_hollow       = evaluated.get('is_hollow', False),
                    wall_params     = evaluated.get('wall_params'),
                    contactors      = evaluated.get('contactors'),
                )
                idx = self.add_avatar(avatar)
                generated_indices.append(idx)

            elif for_loop.target_type == 'material':
                from ...core.models import Material, MaterialType
                mat = Material(
                    name          = evaluated['name'],
                    material_type = MaterialType(evaluated.get('material_type', 'RIGID')),
                    density       = evaluated.get('density', 2800),
                    properties    = evaluated.get('properties', {}),
                )
                self.add_material(mat)
                generated_indices.append(len(self.state.materials) - 1)

            elif for_loop.target_type == 'model':
                from ...core.models import Model
                mod = Model(
                    name      = evaluated['name'],
                    physics   = evaluated.get('physics', 'MECAx'),
                    element   = evaluated.get('element', 'Rxx2D'),
                    dimension = evaluated.get('dimension', 2),
                    options   = evaluated.get('options', {}),
                )
                self.add_model(mod)
                generated_indices.append(len(self.state.models) - 1)

            current += step

        # Stocker les refs stables
        if for_loop.target_type == 'avatar':
            for_loop.generated_refs = [
                self.state.avatars[idx].avatar_id for idx in generated_indices
            ]
        else:
            for_loop.generated_refs = generated_indices

        if not self._is_loading:
            self.state.for_loops.append(for_loop)

        if for_loop.group_name and for_loop.target_type in ('avatar', 'granulo'):
            self.state.avatar_groups.setdefault(
                for_loop.group_name, []
            ).extend(for_loop.generated_refs)

        return generated_indices

    def _generate_for_granulo(
        self, for_loop: ForLoop, evaluator: SafeEvaluator
    ) -> List[int]:
        """Génère un dépôt granulométrique par itération de boucle For."""
        tc = for_loop.template_config

        def _ev(val, ctx):
            if not isinstance(val, str):
                return val
            evaluator.allowed_names = ctx
            try:
                return evaluator.eval_expression(val)
            except Exception:
                return val

        evaluator.allowed_names = _BASE_CONTEXT
        start = evaluator.eval_expression(for_loop.start_expr)
        end   = evaluator.eval_expression(for_loop.end_expr)
        step  = evaluator.eval_expression(for_loop.step_expr)

        try:
            base_config = GranuloGeneration(
                nb_particles     = int(tc.get('nb_particles', 50)),
                radius_min       = float(tc.get('radius_min', 0.01)),
                radius_max       = float(tc.get('radius_max', 0.05)),
                container_type   = str(tc.get('container_type', 'Box2D')),
                container_params = {k: float(v) for k, v in tc.get('container_params', {}).items()},
                material_name    = str(tc.get('material_name', '')),
                model_name       = str(tc.get('model_name', '')),
                avatar_type      = str(tc.get('avatar_type', 'rigidDisk')),
                color            = str(tc.get('color', 'BLUEx')),
                seed             = tc.get('seed'),
                group_name       = for_loop.group_name,
            )
        except Exception as exc:
            raise ValueError(f"Erreur dans le template granulo : {exc}")

        nb_p, coords_ref, radii_ref = GranuloGenerator.generate(base_config)
        av_type_obj = AvatarType(base_config.avatar_type)

        generated_indices = []
        prev_batch        = self._batch_mode
        self._batch_mode  = True
        loop_var          = for_loop.loop_var
        try:
            current = start
            while (step > 0 and current < end) or (step < 0 and current > end):
                ctx    = {**_BASE_CONTEXT, loop_var: current, 'i': current}
                origin = list(_ev(tc.get('origin', '[0.0, 0.0]'), ctx))
                for k in range(nb_p):
                    coord  = coords_ref[k].tolist()
                    center = [
                        coord[j] + (origin[j] if j < len(origin) else 0.0)
                        for j in range(len(coord))
                    ]
                    avatar = Avatar(
                        avatar_type   = av_type_obj,
                        center        = center,
                        material_name = base_config.material_name,
                        model_name    = base_config.model_name,
                        color         = base_config.color,
                        origin        = AvatarOrigin.GRANULO,
                        radius        = float(radii_ref[k]),
                    )
                    idx = self.add_avatar(avatar)
                    generated_indices.append(idx)
                current += step
        finally:
            self._batch_mode = prev_batch

        for_loop.generated_refs = [
            self.state.avatars[idx].avatar_id for idx in generated_indices
        ]
        if not self._is_loading:
            self.state.for_loops.append(for_loop)
        if for_loop.group_name:
            self.state.avatar_groups.setdefault(
                for_loop.group_name, []
            ).extend(for_loop.generated_refs)
        self.state_changed.emit()
        return generated_indices

    # ── Mise à jour ───────────────────────────────────────────────────────────

    def update_for_loop(self, index: int, for_loop: ForLoop) -> None:
        if not (0 <= index < len(self.state.for_loops)):
            raise ValueError(f"Index {index} invalide")

        old = self.state.for_loops[index]

        # Supprimer les anciens éléments
        if old.target_type == 'avatar':
            for aid in old.generated_refs:
                res = self._find_avatar_by_id(aid)
                if res:
                    self.remove_avatar(res[0])
        elif old.target_type == 'material':
            for elem_idx in sorted(old.generated_refs, reverse=True):
                if elem_idx < len(self.state.materials):
                    self.remove_material(self.state.materials[elem_idx].name)
        elif old.target_type == 'model':
            for elem_idx in sorted(old.generated_refs, reverse=True):
                if elem_idx < len(self.state.models):
                    self.remove_model(self.state.models[elem_idx].name)

        self.state.for_loops[index] = for_loop

        # Régénérer (sans append dans state.for_loops)
        was_loading       = self._is_loading
        self._is_loading  = True   # empêche le double-append
        try:
            generated_indices = self.generate_for_loop(for_loop)
        finally:
            self._is_loading = was_loading

        # Mettre à jour les groupes
        if old.group_name and old.group_name in self.state.avatar_groups:
            if old.target_type == 'avatar':
                old_ids = set(old.generated_refs)
                self.state.avatar_groups[old.group_name] = [
                    aid for aid in self.state.avatar_groups[old.group_name]
                    if aid not in old_ids
                ]

        if for_loop.group_name and for_loop.target_type == 'avatar':
            self.state.avatar_groups.setdefault(for_loop.group_name, []).extend(
                for_loop.generated_refs
            )

    # ── Suppression ───────────────────────────────────────────────────────────

    def remove_for_loop(self, index: int) -> bool:
        if not (0 <= index < len(self.state.for_loops)):
            return False
        for_loop = self.state.for_loops[index]

        if for_loop.target_type == 'avatar':
            for aid in for_loop.generated_refs:
                res = self._find_avatar_by_id(aid)
                if res:
                    self.remove_avatar(res[0])
        elif for_loop.target_type == 'material':
            for elem_idx in sorted(for_loop.generated_refs, reverse=True):
                if elem_idx < len(self.state.materials):
                    self.remove_material(self.state.materials[elem_idx].name)
        elif for_loop.target_type == 'model':
            for elem_idx in sorted(for_loop.generated_refs, reverse=True):
                if elem_idx < len(self.state.models):
                    self.remove_model(self.state.models[elem_idx].name)

        self.state.for_loops.pop(index)
        return True

    def get_for_loop(self, index: int) -> Optional[ForLoop]:
        if 0 <= index < len(self.state.for_loops):
            return self.state.for_loops[index]
        return None
