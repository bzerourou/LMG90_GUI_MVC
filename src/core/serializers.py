# ============================================================================
# Sérialisation/Désérialisation
# ============================================================================
"""
Gestionnaire de sauvegarde/chargement de projets.

=== CHAMPS GÉRÉS ICI (non couverts par ProjectState.to_dict) ===
- masonry_patterns  : patterns de maçonnerie (wizard), perdus sans ce patch
- load_warnings     : avertissements de chargement (transient, non sauvegardé)

Ces champs sont injectés/extraits directement dans le dict JSON autour de
l'appel à state.to_dict() / ProjectState.from_dict(), ce qui évite de
modifier models.py.
"""

import json
from pathlib import Path
from typing import Dict, Any

from .models import ProjectState

# Clés supplémentaires gérées par le serializer (hors ProjectState.to_dict)
_EXTRA_KEYS = ['masonry_patterns']


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

        # ── Champs supplémentaires non couverts par to_dict ───────────────
        # masonry_patterns : dict {group_name: mp_dict} généré par
        #   masonry_wizard._generate_masonry() et utilisé par
        #   script_generator._write_masonry_pattern_loop().
        #   Sans sauvegarde, toutes les boucles de maçonnerie tombent en
        #   fallback « liste de centers » après un reload.
        data['masonry_patterns'] = getattr(state, 'masonry_patterns', {}) or {}

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

        # ── Restaurer les champs supplémentaires ──────────────────────────
        state.masonry_patterns = data.get('masonry_patterns', {}) or {}

        # load_warnings est transient (non sauvegardé) ; on repart propre
        state.load_warnings = []

        return state