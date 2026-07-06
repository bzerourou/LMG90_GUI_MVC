"""
BaseMixin — utilitaires partagés + reconstruction pylmgc90.

Contient :
  - _find_avatar_by_id / _build_id_to_idx
  - _add_avatar_no_validate
  - _sync_avatar_position
  - _reset_containers
  - _rebuild_pylmgc_objects
  - _restore_factory_avatars
"""
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path

from ..core.models import Avatar, AvatarOrigin
from ..core.pylmgc_bridge import LMGC90Bridge
from pylmgc90 import pre


class BaseMixin:
    """Utilitaires internes partagés par tous les mixins."""

    # ── Résolution avatar_id ──────────────────────────────────────────────────

    def _find_avatar_by_id(self, avatar_id: str) -> Optional[Tuple[int, Avatar]]:
        """Retourne (index, avatar) pour l'avatar_id donné, ou None."""
        for i, av in enumerate(self.state.avatars):
            if av.avatar_id == avatar_id:
                return i, av
        return None

    def _build_id_to_idx(self) -> Dict[str, int]:
        """Construit avatar_id → index (accès O(1) en lot)."""
        return {av.avatar_id: i for i, av in enumerate(self.state.avatars)}

    # ── Ajout sans validation ─────────────────────────────────────────────────

    def _add_avatar_no_validate(self, avatar: Avatar, create_pylmgc: bool = True) -> int:
        """
        Ajoute un avatar SANS validation.
        Réservé à la duplication d'avatars déjà valides.
        """
        if create_pylmgc:
            mat_obj = self._pylmgc_materials.get(avatar.material_name)
            mod_obj = self._pylmgc_models.get(avatar.model_name)
            if mat_obj and mod_obj:
                body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
                if body_obj is not None:
                    self._bodies_container.addAvatar(body_obj)
                self._pylmgc_bodies.append(body_obj)
            else:
                self._pylmgc_bodies.append(None)
        else:
            self._pylmgc_bodies.append(None)
        self.state.avatars.append(avatar)
        if not self._batch_mode:
            self.state_changed.emit()
        return len(self.state.avatars) - 1

    # ── Synchronisation position ──────────────────────────────────────────────

    def _sync_avatar_position(self, index: int, body) -> None:
        if index >= len(self.state.avatars):
            return
        try:
            if hasattr(body, 'nodes') and len(body.nodes) > 0:
                self.state.avatars[index].center = body.nodes[1].coor
        except Exception as e:
            from ...core.app_logger import get_logger
            get_logger('controller').warning(
                f"Erreur synchronisation position avatar {index}: {e}"
            )

    # ── Conteneurs pylmgc90 ───────────────────────────────────────────────────

    def _reset_containers(self) -> None:
        self._materials_container    = pre.materials()
        self._models_container       = pre.models()
        self._bodies_container       = pre.avatars()
        self._contact_laws_container = pre.tact_behavs()
        self._visibility_container   = pre.see_tables()
        self._postpro_container      = pre.postpro_commands()
        self._pylmgc_materials.clear()
        self._pylmgc_models.clear()
        self._pylmgc_bodies.clear()
        self._pylmgc_laws.clear()

    # ── Reconstruction complète depuis l'état chargé ──────────────────────────

    def _rebuild_pylmgc_objects(self) -> None:
        """
        Reconstruit tous les objets pylmgc90 depuis l'état chargé (après load).

        Ordre impératif :
          1. Matériaux + modèles
          2. Avatars MANUAL → _pylmgc_bodies[0..M-1]
          3. Nettoyage des groupes (préserve factory avatar_ids en attente)
          4. Régénération boucles / granulos / for_loops → _pylmgc_bodies[M..]
          5. Lois de contact + visibilité
          6. Réapplication des opérations DOF
          (_restore_factory_avatars est appelé séparément, APRÈS cette méthode)
        """
        self._reset_containers()

        # 1. Matériaux
        for mat in self.state.materials:
            mat_obj = LMGC90Bridge.create_material(mat)
            self._materials_container.addMaterial(mat_obj)
            self._pylmgc_materials[mat.name] = mat_obj

        # 2. Modèles
        for mod in self.state.models:
            mod_obj = LMGC90Bridge.create_model(mod)
            self._models_container.addModel(mod_obj)
            self._pylmgc_models[mod.name] = mod_obj

        # 3. Avatars MANUAL
        regeneration_errors = []
        manual_avatars = [av for av in self.state.avatars if av.origin == AvatarOrigin.MANUAL]
        for avatar in manual_avatars:
            mat_obj = self._pylmgc_materials.get(avatar.material_name)
            mod_obj = self._pylmgc_models.get(avatar.model_name)
            if not mat_obj:
                raise ValueError(
                    f"Matériau '{avatar.material_name}' introuvable lors de la reconstruction"
                )
            if not mod_obj:
                raise ValueError(
                    f"Modèle '{avatar.model_name}' introuvable lors de la reconstruction"
                )
            body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
            if body_obj is None:
                self._pylmgc_bodies.append(None)
                regeneration_errors.append(
                    f"Corps déformable '{avatar.material_name}/{avatar.model_name}' : "
                    f"mesh_params absent — recréez-le via le wizard."
                )
                continue
            self._bodies_container.addAvatar(body_obj)
            self._pylmgc_bodies.append(body_obj)

        # 4. Nettoyage des groupes
        # On preserve les factory avatar_ids (staged) et les avatars manuels.
        existing_ids   = {av.avatar_id for av in self.state.avatars}
        staged_fac_ids = {av.avatar_id
                          for av in getattr(self.state, '_factory_avatars_staged', [])}
        valid_ids = existing_ids | staged_fac_ids
        for grp_name in list(self.state.avatar_groups.keys()):
            self.state.avatar_groups[grp_name] = [
                aid for aid in self.state.avatar_groups[grp_name]
                if aid in valid_ids
            ]

        # 5. Régénération boucles
        for i, loop in enumerate(self.state.loops):
            try:
                if not loop.model_avatar_id:
                    raise ValueError("model_avatar_id vide")
                self.generate_loop(loop)
            except Exception as e:
                regeneration_errors.append(f"Boucle {i + 1}: {e}")

        # 6. Régénération granulo
        for i, granulo in enumerate(self.state.granulo_generations):
            try:
                self.generate_granulo(granulo)
            except Exception as e:
                regeneration_errors.append(f"Granulo {i + 1}: {e}")

        # 7. Régénération boucles For
        for i, for_loop in enumerate(self.state.for_loops):
            try:
                self.generate_for_loop(for_loop)
            except Exception as e:
                regeneration_errors.append(f"Boucle For {i + 1}: {e}")

        if regeneration_errors:
            existing = getattr(self.state, 'load_warnings', [])
            self.state.load_warnings = existing + regeneration_errors

        # 8. Lois de contact
        for law in self.state.contact_laws:
            law_obj = LMGC90Bridge.create_contact_law(law)
            self._contact_laws_container.addBehav(law_obj)
            self._pylmgc_laws[law.name] = law_obj

        # 9. Visibilité
        for rule in self.state.visibility_rules:
            behavior_obj = self._pylmgc_laws.get(rule.behavior_name)
            if not behavior_obj:
                raise ValueError(
                    f"Loi '{rule.behavior_name}' introuvable lors de la reconstruction"
                )
            rule_obj = LMGC90Bridge.create_visibility_rule(rule, behavior_obj)
            self._visibility_container.addSeeTable(rule_obj)

        # 10. Opérations DOF
        for op in self.state.operations:
            self.apply_dof_operation(op)

    # ── Restauration factory avatars (appelée APRÈS _rebuild) ─────────────────

    def _restore_factory_avatars(self) -> None:
        """
        Ajoute les factory avatars après _rebuild_pylmgc_objects.

        Pourquoi après ? _rebuild construit state.avatars + _pylmgc_bodies en
        parallèle. Ajouter les factory avatars avant décalerait les indices des
        avatars régénérés (loops/granulos) et casserait l'alignement.

        Résultat :
          state.avatars   = [manuels | loops | granulos | factory]
          _pylmgc_bodies  = [manuels | loops | granulos | None…  ]
        """
        factory_avs = getattr(self.state, '_factory_avatars_staged', [])
        if not factory_avs:
            return
        for av in factory_avs:
            self.state.avatars.append(av)
            self._pylmgc_bodies.append(None)  # pas d'objet pylmgc pour la factory
        self.state._factory_avatars_staged = []