"""
base.py — Contrat commun pour tous les exemples du menu "📚 Exemples".

Un exemple est une fonction qui reçoit un ProjectController FRAÎCHEMENT
créé (déjà appelé new_project()) et le peuple entièrement via l'API
publique du contrôleur (add_material, add_avatar, generate_loop, ...).

Ce choix (code plutôt que fichier .lmgc90 statique) garantit que chaque
exemple reste valide indéfiniment : il utilise la même API que les
wizards, donc suit automatiquement toute évolution du schéma de données.
"""
from dataclasses import dataclass, field
from typing import Callable, List

from ..controllers.project_controller import ProjectController


@dataclass
class ExampleSpec:
    """Description d'un exemple affiché dans ExamplesDialog."""
    id: str                          # identifiant stable, ex: "falling_disks"
    title: str                       # titre affiché, ex: "🎱 Chute de disques 2D"
    category: str                    # regroupement dans la liste, ex: "Bases"
    description: str                 # texte explicatif (HTML autorisé)
    dimension: int                   # 2 ou 3, pour affichage informatif
    difficulty: str                  # "Débutant" | "Intermédiaire" | "Avancé"
    builder: Callable[[ProjectController], None]  # fonction de construction
    tags: List[str] = field(default_factory=list)  # ex: ["granulo", "contact"]