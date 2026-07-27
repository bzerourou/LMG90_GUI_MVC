"""
particle_population_io.py — Lecture/écriture du sidecar binaire (.npz)
regroupant les arrays numpy de toutes les ParticlePopulation d'un projet.

Format du fichier .npz : deux arrays par population, préfixés par son
population_id, pour tout stocker dans un seul fichier compagnon :
    "<population_id>__centers" -> (N, dim) float64
    "<population_id>__radii"   -> (N,)     float64

Étape 3/7 du refactor ParticlePopulation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from .particle_population import ParticlePopulation


def sidecar_path_for(project_filepath: Path) -> Path:
    """<projet>.lmgc90 → <projet>.populations.npz, dans le même dossier."""
    return project_filepath.with_suffix('').with_suffix('.populations.npz')
    # .with_suffix('') retire '.lmgc90', le 2e .with_suffix ajoute le nouveau
    # suffixe complet — évite un double-suffixe si le nom contient un '.'


def save_populations_sidecar(
    populations: List[ParticlePopulation], npz_path: Path
) -> None:
    """
    Écrit toutes les populations dans un seul fichier .npz compressé.
    Si `populations` est vide, aucun fichier n'est écrit (et un ancien
    sidecar orphelin est supprimé pour éviter une désynchronisation).
    """
    if not populations:
        if npz_path.exists():
            npz_path.unlink()
        return

    arrays: Dict[str, np.ndarray] = {}
    for pop in populations:
        arrays[f"{pop.population_id}__centers"] = pop.centers
        arrays[f"{pop.population_id}__radii"] = pop.radii

    npz_path.parent.mkdir(parents=True, exist_ok=True)
    # compressed : bon compromis taille/vitesse pour des positions/rayons
    # (données peu compressibles mais le gain reste net sur de gros volumes)
    np.savez_compressed(npz_path, **arrays)


def load_populations_sidecar(
    npz_path: Path,
) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """
    Charge le sidecar et retourne {population_id: (centers, radii)}.
    Retourne un dict vide si le fichier n'existe pas (projet sans
    population, ou sidecar supprimé par erreur — traité comme "aucune
    population chargeable", pas comme une erreur fatale : voir l'appelant
    dans serializers.py qui journalise un load_warning par population
    manquante plutôt que de faire échouer tout le chargement).
    """
    if not npz_path.exists():
        return {}

    result: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
    with np.load(npz_path) as data:
        # Regrouper les clés "<id>__centers" / "<id>__radii" par population_id
        population_ids = {
            key.rsplit('__', 1)[0]
            for key in data.files
            if key.endswith('__centers') or key.endswith('__radii')
        }
        for pop_id in population_ids:
            centers_key = f"{pop_id}__centers"
            radii_key = f"{pop_id}__radii"
            if centers_key in data.files and radii_key in data.files:
                result[pop_id] = (data[centers_key], data[radii_key])

    return result