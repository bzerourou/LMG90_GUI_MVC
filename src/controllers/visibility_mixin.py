"""VisibilityMixin — tables de visibilité."""
from typing import Optional, List

from ..core.models import VisibilityRule
from ..core.pylmgc_bridge import LMGC90Bridge
from pylmgc90 import pre


class VisibilityMixin:

    def add_visibility_rule(self, rule: VisibilityRule) -> None:
        behavior_obj = self._pylmgc_laws.get(rule.behavior_name)
        if not behavior_obj:
            raise ValueError(f"Loi '{rule.behavior_name}' introuvable")
        rule_obj = LMGC90Bridge.create_visibility_rule(rule, behavior_obj)
        self._visibility_container.addSeeTable(rule_obj)
        self.state.visibility_rules.append(rule)

    def update_visibility_rule(self, index: int, rule: VisibilityRule) -> None:
        if not (0 <= index < len(self.state.visibility_rules)):
            raise ValueError(f"Index {index} invalide")
        behavior_obj = self._pylmgc_laws.get(rule.behavior_name)
        if not behavior_obj:
            raise ValueError(f"Loi '{rule.behavior_name}' introuvable")
        # Reconstruire toute la table (pylmgc90 ne permet pas la modification)
        self._visibility_container = pre.see_tables()
        self.state.visibility_rules[index] = rule
        for r in self.state.visibility_rules:
            behav    = self._pylmgc_laws[r.behavior_name]
            rule_obj = LMGC90Bridge.create_visibility_rule(r, behav)
            self._visibility_container.addSeeTable(rule_obj)

    def get_visibility_rule(self, index: int) -> Optional[VisibilityRule]:
        if 0 <= index < len(self.state.visibility_rules):
            return self.state.visibility_rules[index]
        return None

    def remove_visibility_rule(self, index: int) -> bool:
        if 0 <= index < len(self.state.visibility_rules):
            self.state.visibility_rules.pop(index)
            return True
        return False

    def get_visibility_rules(self) -> List[VisibilityRule]:
        return self.state.visibility_rules.copy()
