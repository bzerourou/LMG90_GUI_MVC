"""MaterialsMixin — CRUD matériaux."""
from typing import Optional, List

from ..core.models import Material
from ..core.validators import MaterialValidator, ValidationError
from ..core.pylmgc_bridge import LMGC90Bridge


class MaterialsMixin:

    def add_material(self, material: Material) -> None:
        if any(m.name == material.name for m in self.state.materials):
            raise ValidationError(
                f"Nom de matériau '{material.name}' déjà utilisé."
            )
        MaterialValidator.validate_or_raise(material)
        mat_obj = LMGC90Bridge.create_material(material)
        self._materials_container.addMaterial(mat_obj)
        self._pylmgc_materials[material.name] = mat_obj
        self.state.materials.append(material)
        self.state_changed.emit()

    def update_material(self, old_name: str, material: Material) -> None:
        MaterialValidator.validate_or_raise(material)
        old_mat = self._find_material(old_name)
        if not old_mat:
            raise ValueError(f"Matériau '{old_name}' introuvable")
        if old_name != material.name:
            if self._find_material(material.name):
                raise ValueError(f"Un matériau nommé '{material.name}' existe déjà")
            for avatar in self.state.avatars:
                if avatar.material_name == old_name:
                    avatar.material_name = material.name
        self._materials_container.pop(old_name)
        self._pylmgc_materials.pop(old_name, None)
        mat_obj = LMGC90Bridge.create_material(material)
        self._materials_container.addMaterial(mat_obj)
        self._pylmgc_materials[material.name] = mat_obj
        idx = self.state.materials.index(old_mat)
        self.state.materials[idx] = material

    def remove_material(self, name: str) -> bool:
        material = self._find_material(name)
        if not material:
            return False
        self.state.materials.remove(material)
        self._materials_container.pop(name)
        self._pylmgc_materials.pop(name, None)
        return True

    def get_materials(self) -> List[Material]:
        return self.state.materials.copy()

    def get_material(self, name: str) -> Optional[Material]:
        return self._find_material(name)

    def is_material_used(self, name: str) -> tuple[bool, list[str]]:
        refs = [
            f"Avatar #{i} ({av.avatar_type.value})"
            for i, av in enumerate(self.state.avatars)
            if av.material_name == name
        ]
        return len(refs) > 0, refs

    def _find_material(self, name: str) -> Optional[Material]:
        for mat in self.state.materials:
            if mat.name == name:
                return mat
        return None
