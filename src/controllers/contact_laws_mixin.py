"""ContactLawsMixin — CRUD lois de contact."""
from typing import Optional, List

from ..core.models import ContactLaw
from ..core.validators import ContactLawValidator, ValidationError
from ..core.pylmgc_bridge import LMGC90Bridge


class ContactLawsMixin:

    def add_contact_law(self, law: ContactLaw) -> None:
        if self._find_contact_law(law.name):
            raise ValidationError(f"Une loi nommée '{law.name}' existe déjà")
        ContactLawValidator.validate_or_raise(law)
        law_obj = LMGC90Bridge.create_contact_law(law)
        self._contact_laws_container.addBehav(law_obj)
        self._pylmgc_laws[law.name] = law_obj
        self.state.contact_laws.append(law)
        self.state_changed.emit()

    def update_contact_law(self, old_name: str, law: ContactLaw) -> None:
        ContactLawValidator.validate_or_raise(law)
        old_law = self._find_contact_law(old_name)
        if not old_law:
            raise ValueError(f"Loi '{old_name}' introuvable")
        if old_name != law.name:
            if self._find_contact_law(law.name):
                raise ValueError(f"Une loi nommée '{law.name}' existe déjà")
            for rule in self.state.visibility_rules:
                if rule.behavior_name == old_name:
                    rule.behavior_name = law.name
        self._contact_laws_container.pop(old_name)
        self._pylmgc_laws.pop(old_name, None)
        law_obj = LMGC90Bridge.create_contact_law(law)
        self._contact_laws_container.addBehav(law_obj)
        self._pylmgc_laws[law.name] = law_obj
        idx = self.state.contact_laws.index(old_law)
        self.state.contact_laws[idx] = law

    def remove_contact_law(self, name: str) -> bool:
        law = self._find_contact_law(name)
        if not law:
            return False
        self.state.contact_laws.remove(law)
        self._contact_laws_container.pop(name)
        self._pylmgc_laws.pop(name, None)
        return True

    def get_contact_laws(self) -> List[ContactLaw]:
        return self.state.contact_laws.copy()

    def get_contact_law(self, name: str) -> Optional[ContactLaw]:
        return self._find_contact_law(name)

    def is_contact_law_used(self, name: str) -> tuple[bool, list[str]]:
        refs = [
            f"Règle de visibilité #{i + 1}"
            for i, rule in enumerate(self.state.visibility_rules)
            if rule.behavior_name == name
        ]
        return len(refs) > 0, refs

    def _find_contact_law(self, name: str) -> Optional[ContactLaw]:
        for law in self.state.contact_laws:
            if law.name == name:
                return law
        return None
