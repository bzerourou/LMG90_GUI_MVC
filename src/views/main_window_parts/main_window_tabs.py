"""Gestion du cycle de vie des onglets de la fenetre principale."""
from PyQt6.QtWidgets import QMessageBox


class MainWindowTabsMixin:
    """Operations d'ouverture et de fermeture des onglets."""

    def _add_tab(self, tab_id: str):
        """Ajoute un onglet s'il n'est pas deja ouvert."""
        if tab_id not in self.all_tabs:
            return

        title, widget, icon = self.all_tabs[tab_id]
        for index in range(self.tabs.count()):
            if self.tabs.widget(index) is widget:
                self.tabs.setCurrentIndex(index)
                return

        index = self.tabs.addTab(widget, f"{icon} {title}")
        self.tabs.setCurrentIndex(index)

    def _on_tab_close_requested(self, index: int):
        """Gere la fermeture d'un onglet."""
        widget = self.tabs.widget(index)
        tab_name = self.tabs.tabText(index)
        essential_tabs = [self.material_tab, self.model_tab]

        if widget in essential_tabs:
            QMessageBox.warning(
                self,
                "Onglet essentiel",
                f"L'onglet '{tab_name}' ne peut pas etre ferme car il est essentiel.",
            )
            return

        self.tabs.removeTab(index)

    def _close_other_tabs(self):
        """Ferme tous les onglets sauf celui actif et les essentiels."""
        current_index = self.tabs.currentIndex()
        essential_tabs = [self.material_tab, self.model_tab, self.compute_tab]

        for index in range(self.tabs.count() - 1, -1, -1):
            if index != current_index and self.tabs.widget(index) not in essential_tabs:
                self.tabs.removeTab(index)

    def _close_all_tabs(self):
        """Ferme tous les onglets non essentiels."""
        essential_tabs = [self.material_tab, self.model_tab, self.compute_tab]

        for index in range(self.tabs.count() - 1, -1, -1):
            if self.tabs.widget(index) not in essential_tabs:
                self.tabs.removeTab(index)

    def _reopen_default_tabs(self):
        """Rouvre les onglets de travail courants."""
        default_tabs = [
            "material", "model", "avatar", "dof", "contact",
            "visibility", "postpro", "viewer",
        ]
        for tab_id in default_tabs:
            self._add_tab(tab_id)
