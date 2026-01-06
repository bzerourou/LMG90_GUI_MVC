# ============================================================================
# Point d'entrée de l'application
# ============================================================================
"""
Point d'entrée de l'application LMGC90_GUI.
Lance la fenêtre principale.
"""
import sys
from PyQt6.QtWidgets import QApplication
from src.views.main_window import MainWindow


def main():
    """Fonction principale"""
    app = QApplication(sys.argv)
    
    # Configuration de la police
    font = app.font()
    font.setPointSize(10)
    font.setFamily("Segoe UI")
    app.setFont(font)
    
    # Créer et afficher la fenêtre
    window = MainWindow()
    window.show()
    
    # Lancer l'application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()