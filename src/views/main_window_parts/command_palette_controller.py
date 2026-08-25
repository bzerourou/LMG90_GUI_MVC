"""Coordination de la palette de commandes de la fenetre principale."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence

from ..command_palette import CommandPalette


class CommandPaletteController:
    """Gere l'ouverture et le contenu de la palette Ctrl+K."""

    def __init__(self, window):
        self.window = window
        self.palette = None

    def setup_shortcut(self):
        """Installe le raccourci sur la fenetre pour conserver sa portee."""
        action = QAction("Palette de commandes", self.window)
        action.setShortcut(QKeySequence("Ctrl+K"))
        action.triggered.connect(self.open)
        self.window.addAction(action)

    def open(self):
        """Ouvre la palette et transmet la commande a MainWindow."""
        entries = self.build_entries()
        self.palette = CommandPalette(entries, parent=self.window)
        self.palette.command_selected.connect(self.window._on_command_entered)

        geometry = self.window.geometry()
        self.palette.move(
            geometry.center().x() - self.palette.width() // 2,
            geometry.top() + 80,
        )
        self.palette.show()

    def build_entries(self) -> list[tuple[str, str]]:
        """Construit les commandes affichees dans la palette."""
        entries = [
            ("help", "Afficher l'aide des commandes"),
            ("dim 2", "Passer le projet en 2D"),
            ("dim 3", "Passer le projet en 3D"),
            ("viewer refresh", "Rafraichir la scene 3D"),
            ("viewer color lmgc90", "Couleur du viewer : palette LMGC90"),
            ("viewer color type", "Couleur du viewer : par type d'avatar"),
            ("viewer color material", "Couleur du viewer : par materiau"),
            ("viewer color origin", "Couleur du viewer : par origine"),
            ("viewer edges on", "Afficher les aretes dans le viewer"),
            ("viewer edges off", "Masquer les aretes dans le viewer"),
            ("units si", "Systeme d'unites : International (SI)"),
            ("units cgs", "Systeme d'unites : CGS"),
            ("new", "Creer un nouveau projet"),
            ("save", "Sauvegarder le projet"),
            ("wizard project", "Ouvrir l'assistant de projet"),
            ("wizard granulo", "Ouvrir l'assistant de granulometrie"),
            ("wizard fast-granulo", "Ouvrir le generateur granulometrique rapide"),
            ("datbox", "Generer le dossier DATBOX"),
            ("script", "Generer le script Python"),
            ("compute setup", "Ouvrir les parametres de calcul"),
            ("logs app", "Afficher le journal de l'application"),
            ("logs lmgc90", "Afficher les logs LMGC90"),
            ("tabs default", "Rouvrir les onglets par defaut"),
            ("menu fichier", "Ouvrir le menu Fichier"),
            ("menu assistants", "Ouvrir le menu Assistants"),
            ("menu outils", "Ouvrir le menu Outils"),
            ("menu calcul", "Ouvrir le menu Calcul"),
            ("menu onglets", "Ouvrir le menu Onglets"),
            ("menu aide", "Ouvrir le menu Aide"),
            ("menu exemples", "Ouvrir le menu Exemples"),
        ]
        for tab_id, (title, _widget, icon) in self.window.all_tabs.items():
            entries.append((f"tab {tab_id}", f"Ouvrir l'onglet {icon} {title}"))
            entries.append((f"close {tab_id}", f"Fermer l'onglet {icon} {title}"))
        return entries
