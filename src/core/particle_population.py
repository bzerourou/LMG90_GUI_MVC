"""
particle_population.py — Modèle SoA (Structure of Arrays) pour les populations
de particules générées en masse (granulo, factory, boucles massives).

Complémentaire à Avatar (modèle AoS), pas un remplacement : Avatar reste la
bonne structure pour les objets peu nombreux et individuellement édités
(murs, avatars manuels, corps déformables). ParticlePopulation vise les
volumes qui feraient s'effondrer une List[Avatar] (dizaines de milliers de
particules et plus).

Étapes du refactor couvertes par ce fichier :
  1. Structure isolée (create, validation, as_avatar_view, stats)
  3. Sérialisation à deux niveaux :
       - to_dict()/from_dict()            : forme autonome (arrays inclus),
         utilisée en mémoire (tests, duplication) et rétrocompatible avec
         les projets sauvegardés avant l'introduction du sidecar binaire.
       - to_meta_dict()/from_meta_and_arrays() : forme "sidecar", utilisée
         par ProjectSerializer (métadonnées en JSON, arrays dans un .npz
         séparé — voir particle_population_io.py).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .models import Avatar, AvatarType, AvatarOrigin


def new_population_id() -> str:
    """Identifiant stable de la population (jamais par particule)."""
    return "pop_" + uuid.uuid4().hex


@dataclass
class ParticlePopulation:
    """
    Population homogène de particules — un seul avatar_type, un seul
    matériau, un seul modèle pour toute la population (cohérent avec
    la façon dont granulo/factory génèrent aujourd'hui via GranuloTab).

    Champs SoA :
        centers : np.ndarray, shape (N, dim), dtype float64
        radii   : np.ndarray, shape (N,),      dtype float64
    """

    population_id: str
    avatar_type: AvatarType
    material_name: str
    model_name: str
    color: str
    origin: AvatarOrigin
    dimension: int

    centers: np.ndarray = field(repr=False)
    radii: np.ndarray = field(repr=False)

    group_name: Optional[str] = None

    # ── Construction ──────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        avatar_type: AvatarType,
        material_name: str,
        model_name: str,
        color: str,
        origin: AvatarOrigin,
        centers: np.ndarray,
        radii: np.ndarray,
        group_name: Optional[str] = None,
        population_id: Optional[str] = None,
    ) -> "ParticlePopulation":
        """Point d'entrée validé — préférer à l'appel direct du constructeur."""
        centers = np.asarray(centers, dtype=np.float64)
        radii = np.asarray(radii, dtype=np.float64)

        if centers.ndim != 2:
            raise ValueError(
                f"centers doit être 2D (N, dim), reçu shape={centers.shape}"
            )
        if centers.shape[1] not in (2, 3):
            raise ValueError(
                f"dimension invalide : centers.shape[1]={centers.shape[1]} "
                f"(attendu 2 ou 3)"
            )
        if radii.ndim != 1:
            raise ValueError(f"radii doit être 1D (N,), reçu shape={radii.shape}")
        if radii.shape[0] != centers.shape[0]:
            raise ValueError(
                f"centers ({centers.shape[0]} particules) et radii "
                f"({radii.shape[0]} valeurs) incohérents"
            )
        if radii.shape[0] > 0 and np.any(radii <= 0):
            raise ValueError("tous les rayons doivent être strictement positifs")

        return cls(
            population_id=population_id or new_population_id(),
            avatar_type=avatar_type,
            material_name=material_name,
            model_name=model_name,
            color=color,
            origin=origin,
            dimension=centers.shape[1],
            centers=centers,
            radii=radii,
            group_name=group_name,
        )

    # ── Métadonnées ───────────────────────────────────────────────────────

    def __len__(self) -> int:
        return self.centers.shape[0]

    def particle_avatar_id(self, i: int) -> str:
        """
        avatar_id dérivé et déterministe (jamais stocké par particule).
        Compatible avec le refactor 'avatar_id stable' existant : cet id
        reste valide tant que la population n'est pas régénérée.
        """
        if not (0 <= i < len(self)):
            raise IndexError(f"Index particule {i} hors bornes (0..{len(self) - 1})")
        return f"{self.population_id}:{i}"

    def index_from_particle_avatar_id(self, avatar_id: str) -> Optional[int]:
        """Inverse de particle_avatar_id — utile pour la sélection/DOF ciblé."""
        prefix = f"{self.population_id}:"
        if not avatar_id.startswith(prefix):
            return None
        try:
            idx = int(avatar_id[len(prefix):])
        except ValueError:
            return None
        return idx if 0 <= idx < len(self) else None

    # ── Vue individuelle (matérialisation à la demande) ─────────────────

    def as_avatar_view(self, i: int) -> Avatar:
        """
        Matérialise UN Avatar à la volée pour un cas d'usage ponctuel
        (édition individuelle, DOF ciblé, affichage d'info dans l'UI).
        Ne PAS appeler ceci en boucle sur toute la population — c'est
        justement ce que ParticlePopulation évite.
        """
        return Avatar(
            avatar_id=self.particle_avatar_id(i),
            avatar_type=self.avatar_type,
            center=self.centers[i].tolist(),
            radius=float(self.radii[i]),
            material_name=self.material_name,
            model_name=self.model_name,
            color=self.color,
            origin=self.origin,
        )

    # ── Statistiques utiles (aperçu UI, validation) ─────────────────────

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Retourne (min, max) par axe — utile pour cadrer la caméra du viewer."""
        if len(self) == 0:
            zeros = np.zeros(self.dimension)
            return zeros, zeros
        return self.centers.min(axis=0), self.centers.max(axis=0)

    def radius_stats(self) -> dict:
        if len(self) == 0:
            return {"min": 0.0, "max": 0.0, "mean": 0.0}
        return {
            "min": float(self.radii.min()),
            "max": float(self.radii.max()),
            "mean": float(self.radii.mean()),
        }

    # ── Sérialisation ────────────────────────────────────────────────────
    # to_dict()/from_dict() : forme "autonome" (arrays inclus en JSON) —
    #   utile en mémoire (tests, duplication) et pour la rétrocompatibilité
    #   avec les projets sauvegardés avant l'introduction du sidecar binaire.
    # to_meta_dict()/from_meta_and_arrays() : forme "sidecar" utilisée par
    #   ProjectSerializer — métadonnées en JSON, arrays dans un .npz séparé.

    def to_dict(self) -> dict:
        """Forme autonome (arrays inclus) — usage mémoire / tests uniquement."""
        d = self.to_meta_dict()
        d['centers'] = self.centers.tolist()
        d['radii'] = self.radii.tolist()
        return d

    def to_meta_dict(self) -> dict:
        """Métadonnées seules, sans les arrays — utilisé par le sidecar binaire."""
        return {
            'population_id': self.population_id,
            'avatar_type': self.avatar_type.value,
            'material_name': self.material_name,
            'model_name': self.model_name,
            'color': self.color,
            'origin': self.origin.value,
            'dimension': self.dimension,
            'group_name': self.group_name,
            'n_particles': len(self),  # redondant avec les arrays, utile pour
                                        # validation/affichage sans charger le npz
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ParticlePopulation":
        """Forme autonome — attend centers/radii inline dans data."""
        centers = np.array(data['centers'], dtype=np.float64)
        radii = np.array(data['radii'], dtype=np.float64)
        if centers.size == 0:
            centers = centers.reshape(0, data.get('dimension', 2))
        return cls._from_meta(data, centers, radii)

    @classmethod
    def from_meta_and_arrays(
        cls, meta: dict, centers: np.ndarray, radii: np.ndarray
    ) -> "ParticlePopulation":
        """Forme sidecar — meta vient du JSON, centers/radii viennent du .npz."""
        return cls._from_meta(meta, centers, radii)

    @classmethod
    def _from_meta(cls, meta: dict, centers: np.ndarray, radii: np.ndarray) -> "ParticlePopulation":
        centers = np.asarray(centers, dtype=np.float64)
        radii = np.asarray(radii, dtype=np.float64)
        return cls(
            population_id=meta['population_id'],
            avatar_type=AvatarType(meta['avatar_type']),
            material_name=meta['material_name'],
            model_name=meta['model_name'],
            color=meta['color'],
            origin=AvatarOrigin(meta['origin']),
            dimension=meta['dimension'],
            centers=centers,
            radii=radii,
            group_name=meta.get('group_name'),
        )

    def __repr__(self) -> str:
        return (
            f"ParticlePopulation(id={self.population_id!r}, "
            f"n={len(self)}, type={self.avatar_type.value}, "
            f"dim={self.dimension}, group={self.group_name!r})"
        )