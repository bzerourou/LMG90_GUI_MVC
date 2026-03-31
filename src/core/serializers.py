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
    """Sérialisation/désérialisation de l'état du projet"""
    
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
        data = state.to_dict()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
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
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        state = ProjectState.from_dict(data)
        
        #if 'custom_templates' in data:
        #    state.custom_templates = data['custom_templates']
        
        return state