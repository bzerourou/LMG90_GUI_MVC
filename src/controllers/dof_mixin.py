"""DOFMixin — opérations sur les degrés de liberté."""
from typing import List

from ..core.models import DOFOperation
from ..core.pylmgc_bridge import LMGC90Bridge


class DOFMixin:

    def apply_dof_operation(self, operation: DOFOperation) -> None:
        """Applique une opération DOF sans la sauvegarder."""
        if operation.target_type == 'avatar':
            res = self._find_avatar_by_id(operation.target_value)
            if res:
                idx, _ = res
                if 0 <= idx < len(self._pylmgc_bodies):
                    body = self._pylmgc_bodies[idx]
                    if body is not None:
                        LMGC90Bridge.apply_dof_operation(operation, body)
                        self._sync_avatar_position(idx, body)

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
                            self._sync_avatar_position(idx, body)

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
        self.apply_dof_operation(operation)

    def remove_dof_operation(self, index: int) -> None:
        del self.state.operations[index]
