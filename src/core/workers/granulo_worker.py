# ============================================================================
#Thread pour Génération Granulométrique
# ============================================================================
"""
Worker thread pour générer des distributions granulométriques sans bloquer l'UI.
"""
from PyQt6.QtCore import QThread, pyqtSignal, QMutex
import numpy as np
from typing import List, Dict, Any


class GranuloWorker(QThread):
    """Worker pour générer les particules en arrière-plan"""
    
    # Signaux
    data_ready = pyqtSignal(list)  # Liste de {center, radius}
    progress_updated = pyqtSignal(int, int, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, config):
        """
        Args:
            config: GranuloGeneration - configuration complète
        """
        super().__init__()
        self.config = config
        self._is_running = True
    
    def run(self):
        """Génère un VRAI dépôt avec GranuloGenerator"""
        try:
            # Importer GranuloGenerator (dans le thread worker)
            from src.core.generators import GranuloGenerator
       
            nb = self.config.nb_particles
            
            self.progress_updated.emit(0, nb, "Calcul du dépôt granulométrique...")
            
            # ===== GÉNÉRATEUR =====
            nb_generated, coordinates, radii = GranuloGenerator.generate(self.config)
            
            self.progress_updated.emit(nb_generated, nb, "Dépôt calculé avec succès")
            
            # Convertir en format dict pour le thread principal
            particles_data = []
            for i in range(nb_generated):
                particles_data.append({
                    'center': coordinates[i].tolist(),  # numpy array -> list
                    'radius': float(radii[i])
                })
            
            # Envoyer les données
            self.data_ready.emit(particles_data)
            
        except Exception as e:
            import traceback
            error_msg = f"Erreur génération dépôt:\n{str(e)}\n\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)
    
    def stop(self):
        """Arrête le worker"""
        self._is_running = False
