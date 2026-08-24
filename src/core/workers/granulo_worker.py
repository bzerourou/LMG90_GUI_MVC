# ============================================================================
# granulo_worker.py  —  Préparation des données particules (thread-safe)
# ============================================================================
"""
Ne contient PLUS d'appel pylmgc90.
Le dépôt (depositInXxx) est fait sur le thread principal.
Ce worker transforme seulement des arrays déjà calculés
en liste de dicts pour la création progressive d'avatars.
"""
from typing import List, Dict, Any

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal


class GranuloWorker(QThread):
    """
    Thread secondaire : conversion arrays → liste de dicts uniquement.
    Aucun appel natif pylmgc90 ici.
    """

    progress_updated = pyqtSignal(int, int, str)
    data_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, coordinates, radii, parent=None):
        # parent DOIT être un QObject ou None — jamais un ndarray
        super().__init__(parent)
        self.coordinates = np.asarray(coordinates, dtype=np.float64)
        self.radii = np.asarray(radii, dtype=np.float64)
        self._canceled = False

    def run(self) -> None:
        try:
            nb = int(len(self.radii))
            self.progress_updated.emit(0, nb, "Préparation des particules…")

            particles_data: List[Dict[str, Any]] = []
            report_step = max(1, nb // 20)

            for i in range(nb):
                if self._canceled:
                    return
                particles_data.append({
                    "center": self.coordinates[i].tolist(),
                    "radius": float(self.radii[i]),
                })
                if i % report_step == 0:
                    self.progress_updated.emit(
                        i, nb, f"Traitement {i + 1}/{nb} particules"
                    )

            self.progress_updated.emit(nb, nb, "Préparation terminée")
            self.data_ready.emit(particles_data)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def cancel(self) -> None:
        self._canceled = True