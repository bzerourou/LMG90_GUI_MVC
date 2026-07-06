"""ModelsMixin — CRUD modèles."""
from typing import Optional, List

from ..core.models import Model
from ..core.validators import ModelValidator, ValidationError
from ..core.pylmgc_bridge import LMGC90Bridge


class ModelsMixin:

    def add_model(self, model: Model) -> None:
        if any(m.name == model.name for m in self.state.models):
            raise ValidationError(
                f"Nom de modèle '{model.name}' déjà utilisé."
            )
        ModelValidator.validate_or_raise(model)
        mod_obj = LMGC90Bridge.create_model(model)
        self._models_container.addModel(mod_obj)
        self._pylmgc_models[model.name] = mod_obj
        self.state.models.append(model)
        self.state_changed.emit()

    def update_model(self, old_name: str, model: Model) -> None:
        ModelValidator.validate_or_raise(model)
        old_mod = self._find_model(old_name)
        if not old_mod:
            raise ValueError(f"Modèle '{old_name}' introuvable")
        if old_name != model.name:
            if self._find_model(model.name):
                raise ValueError(f"Un modèle nommé '{model.name}' existe déjà")
            for avatar in self.state.avatars:
                if avatar.model_name == old_name:
                    avatar.model_name = model.name
        self._models_container.pop(old_name)
        self._pylmgc_models.pop(old_name, None)
        mod_obj = LMGC90Bridge.create_model(model)
        self._models_container.addModel(mod_obj)
        self._pylmgc_models[model.name] = mod_obj
        idx = self.state.models.index(old_mod)
        self.state.models[idx] = model

    def remove_model(self, name: str) -> bool:
        model = self._find_model(name)
        if not model:
            return False
        self.state.models.remove(model)
        self._models_container.pop(name)
        self._pylmgc_models.pop(name, None)
        return True

    def get_models(self) -> List[Model]:
        return self.state.models.copy()

    def get_model(self, name: str) -> Optional[Model]:
        return self._find_model(name)

    def is_model_used(self, name: str) -> tuple[bool, list[str]]:
        refs = [
            f"Avatar #{i} ({av.avatar_type.value})"
            for i, av in enumerate(self.state.avatars)
            if av.model_name == name
        ]
        return len(refs) > 0, refs

    def _find_model(self, name: str) -> Optional[Model]:
        for mod in self.state.models:
            if mod.name == name:
                return mod
        return None
