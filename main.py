# ============================================================================
# Point d'entrée de l'application
# ============================================================================
"""
Point d'entrée de l'application LMGC90_GUI.
Lance la fenêtre principale.
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from src.views.main_window import MainWindow

# ── Mode worker (calcul en subprocess frozen)
_worker_script = os.environ.get("LMGC90_WORKER", "")
if _worker_script:
    import runpy
    # exécuter command.py dans le répertoire où il se trouve
    os.chdir(os.path.dirname(_worker_script) or os.getcwd())
    runpy.run_path(_worker_script, run_name="__main__")
    sys.exit(0)

# ── Logger global
from src.core.app_logger import init_logger
_log = init_logger()
_log.info("main.py démarré")

def main():
    """Fonction principale"""
    init_logger()
    app = QApplication(sys.argv)
    
    # Configuration de la police
    font = app.font()
    font.setPointSize(10)
    font.setFamily("Segoe UI")
    app.setFont(font)
    
    # Créer et afficher la fenêtre
    window = MainWindow()
    window.showMaximized()
    
    # Lancer l'application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()