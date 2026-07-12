# ============================================================================
# granulo_worker.py  —  Worker thread pour le dépôt granulométrique
# ============================================================================
"""
Worker QThread pour le calcul du dépôt granulométrique.

Architecture thread-safe
─────────────────────────
  GranuloWorker (QThread secondaire)
    └─ Calcule positions + rayons via GranuloGenerator.generate()
    └─ Émet data_ready(particles_data) → main thread

  GranuloTab (main thread)
    └─ Reçoit data_ready via signal Qt (QueuedConnection automatique)
    └─ Crée les avatars par batches via QTimer (intervalle=0)
    └─ Appelle controller.add_avatar() — toujours sur main thread

Principe : le worker NE TOUCHE PAS au contrôleur ni à state.avatars.
Il ne fait que du calcul numérique (pylmgc90 deposit functions).
Toutes les modifications d'état se font sur le main thread.
"""
from PyQt6.QtCore import QThread, pyqtSignal

from ..generators import GranuloGenerator
from ..models import GranuloGeneration


class GranuloWorker(QThread):
    """
    Thread secondaire pour le calcul du dépôt granulométrique.

    Signaux
    ───────
    progress_updated(current, total, message)
        Progression du calcul (0 ≤ current ≤ total).

    data_ready(particles_data)
        Calcul terminé. particles_data est une liste de dict :
            [{'center': [x, y], 'radius': float}, ...]
        Ce signal est reçu sur le main thread (QueuedConnection).

    error_occurred(message)
        Erreur pendant le calcul.
    """

    progress_updated = pyqtSignal(int, int, str)
    data_ready       = pyqtSignal(list)
    error_occurred   = pyqtSignal(str)

    def __init__(self, config: GranuloGeneration, parent=None):
        super().__init__(parent)
        self.config     = config
        self._canceled  = False

    # ── Thread principal ──────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Point d'entrée du thread secondaire.
        UNIQUEMENT du calcul numérique — aucun accès au contrôleur.
        """
        try:
            self.progress_updated.emit(0, 100, "Calcul du dépôt granulométrique…")

            # Appel pylmgc90 — peut prendre plusieurs secondes pour >1000 part.
            nb_particles, coordinates, radii = GranuloGenerator.generate(self.config)

            if self._canceled:
                return

            # Convertir les tableaux numpy en liste de dicts Python
            # (plus sûr pour la transmission inter-thread via signal Qt)
            particles_data = []
            report_step    = max(1, nb_particles // 20)   # rapport tous les 5%

            for i in range(nb_particles):
                if self._canceled:
                    return

                particles_data.append({
                    'center': coordinates[i].tolist(),
                    'radius': float(radii[i]),
                })

                if i % report_step == 0:
                    self.progress_updated.emit(
                        i, nb_particles,
                        f"Traitement {i + 1}/{nb_particles} particules"
                    )

            self.progress_updated.emit(nb_particles, nb_particles, "Calcul terminé")

            # Transmission au main thread — Qt garantit QueuedConnection
            self.data_ready.emit(particles_data)

        except Exception as e:
            self.error_occurred.emit(str(e))

    # ── Annulation ────────────────────────────────────────────────────────────

    def cancel(self) -> None:
        """
        Demande l'arrêt propre du worker.
        Le thread s'arrête au prochain point de vérification (tous les 5%).
        Thread-safe : _canceled est un bool Python (GIL protège l'accès).
        """
        self._canceled = True