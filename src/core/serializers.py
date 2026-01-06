# ============================================================================
# Sérialisation/Désérialisation
# ============================================================================
"""
Gestionnaire de sauvegarde/chargement de projets.
"""
import json
from pathlib import Path
from typing import Dict, Any
from .models import ProjectState


class ProjectSerializer:
    """Gère la sérialisation des projets"""
    
    @staticmethod
    def save(state: ProjectState, filepath: Path) -> None:
        """
        Sauvegarde l'état du projet dans un fichier JSON.
        
        Args:
            state: État du projet à sauvegarder
            filepath: Chemin du fichier de sortie
            
        Raises:
            IOError: En cas d'erreur d'écriture
        """
        try:
            data = state.to_dict()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Erreur lors de la sauvegarde: {e}")
    
    @staticmethod
    def load(filepath: Path) -> ProjectState:
        """
        Charge un projet depuis un fichier JSON.
        
        Args:
            filepath: Chemin du fichier à charger
            
        Returns:
            État du projet reconstruit
            
        Raises:
            IOError: En cas d'erreur de lecture
            ValueError: Si le format est invalide
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ProjectState.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Fichier JSON invalide: {e}")
        except Exception as e:
            raise IOError(f"Erreur lors du chargement: {e}")

