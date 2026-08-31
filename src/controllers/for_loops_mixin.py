"""ForLoopsMixin — boucles For génériques (avatar, material, model, contact_law, visibility, dof, granulo)."""
import math
from typing import Optional, List

import numpy as np

from ..core.models import (
    Avatar, AvatarOrigin, AvatarType,
    ForLoop, GranuloGeneration,
    ContactLaw, ContactLawType,
    VisibilityRule,
    DOFOperation,
)
from ..core.generators import GranuloGenerator
from ..core.particle_population import ParticlePopulation
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

# Types d'avatars supportés par le chemin rapide SoA — mêmes types que
# LMGC90Bridge.create_avatars_from_population (rigidDisk/rigidSphere).
_POPULATION_ELIGIBLE_TYPES = {'rigidDisk', 'rigidSphere'}

# Clé interne du template_config portant le choix explicite de
# l'utilisateur (case à cocher dans loop_tab.py). Absente ou False ->
# chemin Avatar classique (AoS) ; True -> chemin ParticlePopulation (SoA)
# si les autres conditions d'éligibilité sont remplies.
_SOA_FLAG_KEY = '_use_soa'


class ForLoopsMixin:

    # ── Génération ────────────────────────────────────────────────────────────

    def generate_for_loop(self, for_loop: ForLoop) -> List[int]:
        """
        Génère des éléments selon une boucle For.
        
        Types de cibles supportés:
          - avatar       : crée des Avatar individuels avec positions/paramètres variables
          - material     : crée des Material avec densité/propriétés variables
          - model        : crée des Model avec physique/éléments variables
          - contact_law  : crée des ContactLaw avec loi/friction variables
          - visibility   : crée des VisibilityRule avec paramètres de détection variables
          - dof          : crée des DOFOperation avec conditions limites variables
          - granulo      : crée une population de particules granulométriques
        
        Les avatars produits sont référencés par avatar_id dans generated_refs ;
        les autres types sont référencés par leur index dans la liste respective.
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

        # ── Chemin rapide SoA — activé explicitement par l'utilisateur ────────
        if for_loop.target_type == 'avatar' and self._for_loop_eligible_for_population(
            for_loop
        ):
            return self._generate_for_loop_avatar_population(
                for_loop, evaluator, start, end, step
            )

        generated_indices = []
        current           = start
        loop_var          = for_loop.loop_var

        while (step > 0 and current < end) or (step < 0 and current > end):
            ctx = {**_BASE_CONTEXT, loop_var: current}
            evaluator.allowed_names = ctx

            evaluated = {}
            for key, value in for_loop.template_config.items():
                if key == _SOA_FLAG_KEY:
                    continue  # meta-champ, pas un paramètre d'avatar
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
                try:
                    from ..core.models import Material, MaterialType
                except ImportError:  # exécution directe / package non standard
                    from src.core.models import Material, MaterialType
                mat = Material(
                    name          = evaluated['name'],
                    material_type = MaterialType(evaluated.get('material_type', 'RIGID')),
                    density       = evaluated.get('density', 2800),
                    properties    = evaluated.get('properties', {}),
                )
                self.add_material(mat)
                generated_indices.append(len(self.state.materials) - 1)

            elif for_loop.target_type == 'model':
                try:
                    from ..core.models import Model
                except ImportError:  # exécution directe / package non standard
                    from src.core.models import Model
                mod = Model(
                    name      = evaluated['name'],
                    physics   = evaluated.get('physics', 'MECAx'),
                    element   = evaluated.get('element', 'Rxx2D'),
                    dimension = evaluated.get('dimension', 2),
                    options   = evaluated.get('options', {}),
                )
                self.add_model(mod)
                generated_indices.append(len(self.state.models) - 1)

            elif for_loop.target_type == 'contact_law':
                law = ContactLaw(
                    name      = evaluated.get('name', 'LAW'),
                    law_type  = ContactLawType(evaluated.get('law_type', evaluated.get('law', 'IQS_CLB'))),
                    friction  = evaluated.get('friction', evaluated.get('fric')),
                    properties= evaluated.get('properties', {}),
                )
                self.add_contact_law(law)
                generated_indices.append(len(self.state.contact_laws) - 1)

            elif for_loop.target_type == 'visibility':
                visibility = VisibilityRule(
                    candidate_body       = evaluated.get('candidate_body', 'RBDY2'),
                    candidate_contactor = evaluated.get('candidate_contactor', 'DISKx'),
                    candidate_color     = evaluated.get('candidate_color', 'BLUEx'),
                    antagonist_body     = evaluated.get('antagonist_body', 'RBDY2'),
                    antagonist_contactor= evaluated.get('antagonist_contactor', 'DISKx'),
                    antagonist_color    = evaluated.get('antagonist_color', 'REDxx'),
                    behavior_name       = evaluated.get('behavior_name', 'LAW01'),
                    alert               = evaluated.get('alert', 0.1),
                )
                self.add_visibility_rule(visibility)
                generated_indices.append(len(self.state.visibility_rules) - 1)

            elif for_loop.target_type == 'dof':
                dof_op = DOFOperation(
                    operation_type = evaluated.get('operation_type', evaluated.get('dof', 'translate')),
                    target_type    = evaluated.get('target_type', evaluated.get('target', 'avatar')),
                    target_value   = evaluated.get('target_value', ''),
                    parameters     = evaluated.get('parameters', {}),
                )
                self.add_dof_operation(dof_op)
                generated_indices.append(len(self.state.operations) - 1)

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

    def _generate_for_granulo(self, for_loop: ForLoop, evaluator: SafeEvaluator) -> List[int]:
        """
        Génère N dépôts granulométriques via une boucle For (target_type='granulo').
        Chaque itération i évalue le template (nb_particles, container_params, ...)
        avec la variable de boucle disponible, puis délègue à generate_granulo().
        """
        evaluator.allowed_names = _BASE_CONTEXT
        start = evaluator.eval_expression(for_loop.start_expr)
        end   = evaluator.eval_expression(for_loop.end_expr)
        step  = evaluator.eval_expression(for_loop.step_expr)

        tc       = for_loop.template_config
        loop_var = for_loop.loop_var
        all_generated_indices: List[int] = []
        all_ids: List[str] = []

        current = start
        while (step > 0 and current < end) or (step < 0 and current > end):
            ctx = {**_BASE_CONTEXT, loop_var: current}
            evaluator.allowed_names = ctx

            def _ev(value):
                if isinstance(value, str):
                    try:
                        return evaluator.eval_expression(value)
                    except Exception:
                        return value
                return value

            container_params = {
                k: _ev(v) for k, v in tc.get('container_params', {}).items()
            }

            config = GranuloGeneration(
                nb_particles     = int(_ev(tc.get('nb_particles', 50))),
                radius_min       = float(_ev(tc.get('radius_min', 0.04))),
                radius_max       = float(_ev(tc.get('radius_max', 0.05))),
                container_type   = str(_ev(tc.get('container_type', 'Box2D'))),
                container_params = container_params,
                model_name       = str(_ev(tc.get('model_name', 'rigid'))),
                material_name    = str(_ev(tc.get('material_name', 'TDURx'))),
                avatar_type      = str(_ev(tc.get('avatar_type', 'rigidDisk'))),
                color            = str(_ev(tc.get('color', 'BLUEx'))),
                seed             = tc.get('seed'),
            )

            indices = self.generate_granulo(config)   # délègue à GranuloMixin
            all_generated_indices.extend(indices)
            all_ids.extend(
                self.state.avatars[i].avatar_id for i in indices
            )

            current += step

        for_loop.generated_refs = all_ids
        if not self._is_loading:
            self.state.for_loops.append(for_loop)
        if for_loop.group_name:
            self.state.avatar_groups.setdefault(
                for_loop.group_name, []
            ).extend(for_loop.generated_refs)

        return all_generated_indices

    # ── Chemin rapide SoA (ParticlePopulation) ────────────────────────────────

    def _for_loop_eligible_for_population(self, for_loop: ForLoop) -> bool:
        """
        Détermine si une boucle For d'avatars peut être générée via
        ParticlePopulation plutôt qu'un Avatar individuel par itération.

        Le choix est désormais explicitement piloté par l'utilisateur via
        la case à cocher "SoA" de loop_tab.py (stockée dans
        template_config['_use_soa']) — plus de seuil automatique implicite.
        Conditions supplémentaires vérifiées ici, indépendamment du choix
        utilisateur, car le chemin SoA ne sait tout simplement pas produire
        ces cas :
          - avatar_type ∈ {rigidDisk, rigidSphere} (seuls types supportés
            par LMGC90Bridge.create_avatars_from_population)
          - le template ne contient PAS de clés incompatibles avec le SoA
            (contactors, vertices, wall_params, is_hollow, generation_type,
            axis, nb_vertices) — ces avatars restent individuellement
            construits même si l'utilisateur a coché la case
        """
        tc = for_loop.template_config
        if not tc.get(_SOA_FLAG_KEY):
            return False

        avatar_type = tc.get('avatar_type', {}).get('value') if isinstance(
            tc.get('avatar_type'), dict
        ) else tc.get('avatar_type')
        if avatar_type not in _POPULATION_ELIGIBLE_TYPES:
            return False

        incompatible_keys = {
            'contactors', 'vertices', 'wall_params', 'is_hollow',
            'generation_type', 'axis', 'nb_vertices',
        }
        if incompatible_keys & set(tc.keys()):
            return False

        return True

    def _generate_for_loop_avatar_population(
        self, for_loop: ForLoop, evaluator: SafeEvaluator, start, end, step
    ) -> List[int]:
        """
        Chemin rapide : construit une ParticlePopulation en une passe numpy
        plutôt que N objets Avatar individuels. Suit le même schéma que
        GranuloMixin.create_granulo_population_from_arrays().

        Activé uniquement si l'utilisateur l'a explicitement demandé (case
        à cocher SoA dans loop_tab.py) — voir _for_loop_eligible_for_population.

        Limitation assumée : les avatars produits ne sont plus
        individuellement modifiables via l'onglet Avatar (comme pour les
        populations granulo) — cohérent avec le compromis déjà accepté
        pour la granulométrie massive, et explicité à l'utilisateur dans
        le tooltip de la case à cocher.
        """
        tc       = for_loop.template_config
        loop_var = for_loop.loop_var

        avatar_type_str = (
            tc['avatar_type']['value'] if isinstance(tc['avatar_type'], dict)
            else tc['avatar_type']
        )
        material_name = str(tc.get('material_name', 'TDURx'))
        model_name    = str(tc.get('model_name', 'rigid'))
        color         = str(tc.get('color', 'BLUEx'))
        radius_expr   = tc.get('radius', 0.1)
        center_expr   = tc.get('center', '[0, 0]')

        centers: List[List[float]] = []
        radii:   List[float]       = []
        current = start
        while (step > 0 and current < end) or (step < 0 and current > end):
            ctx = {**_BASE_CONTEXT, loop_var: current}
            evaluator.allowed_names = ctx

            c = evaluator.eval_expression(center_expr) if isinstance(center_expr, str) else center_expr
            if isinstance(c, str):
                c = evaluator.eval_expression(c)
            r = (
                evaluator.eval_expression(radius_expr)
                if isinstance(radius_expr, str) else radius_expr
            )

            centers.append([float(x) for x in c])
            radii.append(float(r))
            current += step

        if not centers:
            # Boucle vide : rien à générer, pas de population à créer
            for_loop.generated_refs = []
            if not self._is_loading:
                self.state.for_loops.append(for_loop)
            return []

        centers_arr = np.array(centers, dtype=np.float64)
        radii_arr   = np.array(radii, dtype=np.float64)

        mat_obj = self._pylmgc_materials.get(material_name)
        mod_obj = self._pylmgc_models.get(model_name)
        if not mat_obj:
            raise ValueError(f"Matériau '{material_name}' introuvable")
        if not mod_obj:
            raise ValueError(f"Modèle '{model_name}' introuvable")

        population = ParticlePopulation.create(
            avatar_type=AvatarType(avatar_type_str),
            material_name=material_name,
            model_name=model_name,
            color=color,
            origin=AvatarOrigin.LOOP,
            centers=centers_arr,
            radii=radii_arr,
            group_name=for_loop.group_name,
        )
        for_loop.template_config['_population_id'] = population.population_id

        from ..core.pylmgc_bridge import LMGC90Bridge
        bodies = LMGC90Bridge.create_avatars_from_population(population, mod_obj, mat_obj)
        for body in bodies:
            self._bodies_container.addAvatar(body)
            self._pylmgc_bodies.append(body)
        self._pylmgc_population_bodies[population.population_id] = bodies

        if not self._is_loading:
            self.state.particle_populations.append(population)
            self.state.for_loops.append(for_loop)

        if for_loop.group_name:
            self.state.populations_groups.setdefault(
                for_loop.group_name, []
            ).append(population.population_id)

        # generated_refs reste vide pour ce chemin (pas d'Avatar AoS
        # individuel produit) — ces particules vivent dans
        # state.particle_populations, pas state.avatars.
        for_loop.generated_refs = []

        self.state_changed.emit()
        return []

    def remove_for_loop(self, index: int) -> bool:
        if not (0 <= index < len(self.state.for_loops)):
            return False
        for_loop = self.state.for_loops[index]

        if for_loop.target_type == 'avatar':
            for aid in for_loop.generated_refs:
                res = self._find_avatar_by_id(aid)
                if res:
                    self.remove_avatar(res[0])
            # Chemin SoA (generated_refs vide) : nettoyer la population associée
            self._remove_for_loop_population(for_loop)
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

    def _remove_for_loop_population(self, for_loop: ForLoop) -> None:
        """Supprime la ParticlePopulation associée à une boucle For SoA, si présente."""
        pop_id = for_loop.template_config.get('_population_id')
        if pop_id :
            self.remove_particle_population(pop_id)
            return

        if not for_loop.group_name:
            return
        pop_ids = self.state.populations_groups.get(for_loop.group_name, [])
        for pid in list(pop_ids):
            self.remove_particle_population(pid)