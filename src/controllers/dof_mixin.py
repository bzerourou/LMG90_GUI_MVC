"""DOFMixin — opérations sur les degrés de liberté."""
from typing import List

from ..core.models import DOFOperation
from ..core.pylmgc_bridge import LMGC90Bridge


class DOFMixin:

    def apply_dof_operation(self, operation: DOFOperation) -> None:
        """
        Applique une opération DOF sans la sauvegarder.

        Important : on ne synchronise PAS avatar.center après la transformation.
        avatar.center représente toujours la position ORIGINALE définie par
        l'utilisateur. Les DOF sont des contraintes appliquées par-dessus.
        Sans ça, remove_dof_operation ne peut pas retrouver le centre d'origine
        pour recréer l'objet proprement.
        """
        if operation.target_type == 'avatar':
            res = self._find_avatar_by_id(operation.target_value)
            if res:
                idx, _ = res
                if 0 <= idx < len(self._pylmgc_bodies):
                    body = self._pylmgc_bodies[idx]
                    if body is not None:
                        LMGC90Bridge.apply_dof_operation(operation, body)
                        # ← pas de _sync_avatar_position ici

        elif operation.target_type == 'group':
            avatar_ids = self.state.avatar_groups.get(operation.target_value, [])
            for aid in avatar_ids:
                res = self._find_avatar_by_id(aid)
                if res:
                    idx, _ = res
                    if 0 <= idx < len(self._pylmgc_bodies):
                        body = self._pylmgc_bodies[idx]
                        if body is not None:
                            LMGC90Bridge.apply_dof_operation(operation, body)

    def add_dof_operation(self, operation: DOFOperation) -> None:
        """Applique ET sauvegarde une opération DOF."""
        self.apply_dof_operation(operation)
        self.state.operations.append(operation)

    def get_dof_operations(self) -> List[DOFOperation]:
        return self.state.operations.copy()

    def get_dof_operation(self, index: int) -> DOFOperation:
        if index < 0 or index >= len(self.state.operations):
            raise IndexError(f"Index DOF invalide: {index}")
        return self.state.operations[index]

    def update_dof_operation(self, index: int, operation: DOFOperation) -> None:
        self.state.operations[index] = operation
        self._rebuild_avatar_dof_for_op(operation)

    def remove_dof_operation(self, index: int) -> None:
        """
        Supprime une opération DOF et remet l'avatar à son état original.

        Stratégie :
          1. Supprimer l'op de la liste
          2. Recréer le body pylmgc depuis avatar.center (position originale)
          3. Rejouer les opérations RESTANTES dans l'ordre

        Fonctionne car avatar.center n'est jamais modifié par les DOF
        (contrairement à l'ancien comportement avec _sync_avatar_position).
        """
        if not (0 <= index < len(self.state.operations)):
            return

        op = self.state.operations.pop(index)

        if op.target_type == 'avatar':
            self._rebuild_avatar_dof(op.target_value)
        elif op.target_type == 'group':
            for aid in self.state.avatar_groups.get(op.target_value, []):
                self._rebuild_avatar_dof(aid)

    # ── Utilitaires internes ──────────────────────────────────────────────────

    def _rebuild_avatar_dof_for_op(self, operation: DOFOperation) -> None:
        if operation.target_type == 'avatar':
            self._rebuild_avatar_dof(operation.target_value)
        elif operation.target_type == 'group':
            for aid in self.state.avatar_groups.get(operation.target_value, []):
                self._rebuild_avatar_dof(aid)

    def _rebuild_avatar_dof(self, avatar_id: str) -> None:
        """
        Recrée l'objet pylmgc à partir de avatar.center (position originale)
        puis ré-applique toutes les opérations DOF restantes dans l'ordre.
        """
        res = self._find_avatar_by_id(avatar_id)
        if res is None:
            return
        idx, avatar = res

        mat_obj = self._pylmgc_materials.get(avatar.material_name)
        mod_obj = self._pylmgc_models.get(avatar.model_name)
        if not mat_obj or not mod_obj:
            return

        # Retirer l'ancien objet
        old_body = self._pylmgc_bodies[idx]
        if old_body is not None:
            try:
                self._bodies_container.remove(old_body)
            except Exception:
                pass

        # Recréer depuis avatar.center — toujours la position originale
        new_body = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
        if new_body is not None:
            self._bodies_container.addAvatar(new_body)
        self._pylmgc_bodies[idx] = new_body

        # Rejouer les opérations restantes dans l'ordre
        for op in self.state.operations:
            if new_body is None:
                break
            applies = False
            if op.target_type == 'avatar' and op.target_value == avatar_id:
                applies = True
            elif op.target_type == 'group':
                applies = avatar_id in self.state.avatar_groups.get(
                    op.target_value, []
                )
            if applies:
                try:
                    LMGC90Bridge.apply_dof_operation(op, new_body)
                except Exception as e:
                    from ..core.app_logger import get_logger
                    get_logger('controller').warning(
                        f"Replay DOF sur avatar '{avatar_id}' échoué : {e}"
                    )