"""
contactor_compat.py — Compatibilité contacteur / type d'avatar.

Centralise la liste des contacteurs LMGC90 valides pour chaque catégorie
de corps, en un seul endroit, pour que l'UI (empty_avatar_tab.py) et le
contrôleur (avatars_mixin.py::add_contactor_to_avatar) appliquent
exactement la même règle — pas de duplication, pas de divergence.

Règle de catégorisation
────────────────────────
Le type de corps pylmgc90 sous-jacent détermine les contacteurs valides,
pas le type d'Avatar GUI au sens large :
  - AvatarType.MESH_DEFORMABLE → corps MAILx        → contacteurs de maillage
  - tout le reste (y compris EMPTY_AVATAR, construit sur
    pre.rigid2d()/pre.rigid3d()) → corps RBDY2/RBDY3 → contacteurs rigides

Tous les contacteurs LMGC90 suivent la convention à 5 caractères
(ex: DISKx, CLxxx, PT2Dx). Toute variante à 4 caractères ou non
référencée ailleurs dans le code (ex: anciennes listes "CLxx", "DISKL",
"PT2TL", "DNLYC") est une erreur, pas une forme alternative — elle a été
retirée volontairement de ce module.
"""
from typing import List

from .models import AvatarType


# ── Corps rigides (RBDY2 / RBDY3) ────────────────────────────────────────
CONTACTORS_RIGID_2D: List[str] = ["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"]
CONTACTORS_RIGID_3D: List[str] = ["SPHER", "PLANx", "CYLND", "POLYR", "PT3Dx"]

# ── Corps déformables (MAILx) ─────────────────────────────────────────────
CONTACTORS_MESH_2D: List[str] = ["CLxxx", "ALpxx", "PT2Dx"]
CONTACTORS_MESH_3D: List[str] = ["CSpxx", "ASpxx", "PT3Dx"]


def get_compatible_contactor_shapes(avatar_type: AvatarType, dimension: int) -> List[str]:
    """
    Retourne la liste des formes de contacteur compatibles avec un type
    d'avatar et une dimension donnés.

    Lève ValueError si dimension n'est ni 2 ni 3 — signal d'un bug appelant
    plutôt qu'un cas à tolérer silencieusement.
    """
    if dimension not in (2, 3):
        raise ValueError(f"Dimension invalide : {dimension!r} (2 ou 3 attendu)")

    if avatar_type == AvatarType.MESH_DEFORMABLE:
        return list(CONTACTORS_MESH_2D if dimension == 2 else CONTACTORS_MESH_3D)
    return list(CONTACTORS_RIGID_2D if dimension == 2 else CONTACTORS_RIGID_3D)


def is_shape_compatible(shape: str, avatar_type: AvatarType, dimension: int) -> bool:
    """True si `shape` est un contacteur valide pour ce type d'avatar/dimension."""
    return shape in get_compatible_contactor_shapes(avatar_type, dimension)