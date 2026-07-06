# ============================================================================
# Sérialisation/Désérialisation
# ============================================================================
"""
Gestionnaire de sauvegarde/chargement de projets.

=== VERSIONS DE SCHÉMA ===
  v1  — champs basés sur des positions entières (avatar_groups: List[int],
         Loop.model_avatar_index, generated_indices, etc.)
  v2  — champs basés sur avatar_id stable (str uuid / déterministe)

  La migration v1→v2 est appliquée automatiquement au chargement des anciens
  fichiers .lmgc90 pour garantir la compatibilité ascendante.

=== CHAMPS GÉRÉS ICI (hors ProjectState.to_dict) ===
  schema_version   : version du schéma JSON
  masonry_patterns : patterns de maçonnerie (wizard)
  factory_avatars  : avatars factory (non régénérés par _rebuild)
  load_warnings    : avertissements (transient, non sauvegardé)
"""

import json
from pathlib import Path
from typing import Dict, Any, List

from .models import ProjectState, Avatar, AvatarOrigin

# Version courante du schéma
_SCHEMA_VERSION = 2


class ProjectSerializer:
    """Sérialisation/désérialisation de l'état du projet."""

    # ── Sauvegarde ────────────────────────────────────────────────────────────

    @staticmethod
    def save(state: ProjectState, filepath: Path) -> None:
        """
        Sauvegarde l'état du projet dans un fichier JSON (schéma v2).
        """
        data = state.to_dict()

        # Version du schéma — permet la migration automatique au rechargement
        data['schema_version'] = _SCHEMA_VERSION

        # masonry_patterns (non couvert par to_dict)
        data['masonry_patterns'] = getattr(state, 'masonry_patterns', {}) or {}

        # Factory avatars — identifiés par avatar_id déterministe "factory_…"
        data['factory_avatars'] = [
            av.to_dict()
            for av in state.avatars
            if av.avatar_id.startswith('factory_')
        ]

        # ── Nettoyage des groupes vides ───────────────────────────────────
        # Après suppressions d'avatars, certains groupes deviennent [].
        # On ne les sauvegarde pas pour garder le JSON propre.
        data['avatar_groups'] = {
            grp: aids
            for grp, aids in data.get('avatar_groups', {}).items()
            if aids
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── Chargement ───────────────────────────────────────────────────────────

    @staticmethod
    def load(filepath: Path) -> ProjectState:
        """
        Charge un projet depuis un fichier JSON.
        Applique automatiquement la migration v1→v2 si nécessaire.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # ── Validation basique du schéma ──────────────────────────────────
        _validate_schema(data, filepath)

        # ── Migration automatique des anciens fichiers ────────────────────
        version = data.get('schema_version', 1)
        if version < 2:
            data = _migrate_v1_to_v2(data)

        state = ProjectState.from_dict(data)

        # Restaurer masonry_patterns
        state.masonry_patterns = data.get('masonry_patterns', {}) or {}

        # Mettre en attente les factory avatars (ajoutés APRÈS _rebuild
        # pour maintenir l'alignement _pylmgc_bodies / state.avatars)
        state._factory_avatars_staged = [
            Avatar.from_dict(av_data)
            for av_data in data.get('factory_avatars', [])
        ]

        # load_warnings est transient
        state.load_warnings = []

        return state


# ============================================================================
# Validation du schéma
# ============================================================================

def _validate_schema(data: dict, filepath: Path) -> None:
    """
    Vérifie que le fichier chargé est bien un projet LMGC90_GUI valide.

    Lève ValueError avec un message clair si :
      - Le JSON n'est pas un dict (fichier vide, corrompu, mauvais format)
      - Les clés obligatoires sont absentes (pas un fichier .lmgc90)
      - La version de schéma est trop récente (app trop ancienne)
    """
    if not isinstance(data, dict):
        raise ValueError(
            f"Format invalide : '{filepath.name}' n'est pas un projet LMGC90_GUI "
            f"(JSON attendu : dict, reçu : {type(data).__name__})"
        )

    # Clés minimales obligatoires
    required = {'project_name', 'dimension', 'materials', 'models', 'avatars'}
    missing  = required - data.keys()
    if missing:
        raise ValueError(
            f"'{filepath.name}' n'est pas un projet LMGC90_GUI valide.\n"
            f"Clés manquantes : {', '.join(sorted(missing))}"
        )

    # Compatibilité version
    version = data.get('schema_version', 1)
    if version > _SCHEMA_VERSION:
        raise ValueError(
            f"'{filepath.name}' a été créé avec une version plus récente "
            f"de LMGC90_GUI (schéma v{version}, version courante v{_SCHEMA_VERSION}).\n"
            f"Mettez à jour l'application pour ouvrir ce fichier."
        )

    # Vérifications de type basiques
    if not isinstance(data.get('dimension'), int):
        raise ValueError(
            f"Champ 'dimension' invalide dans '{filepath.name}' "
            f"(entier attendu, reçu : {type(data.get('dimension')).__name__})"
        )

    if data['dimension'] not in (2, 3):
        raise ValueError(
            f"Dimension invalide dans '{filepath.name}' : "
            f"{data['dimension']} (2 ou 3 attendu)"
        )


# ============================================================================
# Migration v1 → v2
# ============================================================================

def _migrate_v1_to_v2(data: dict) -> dict:
    """
    Convertit un fichier de projet v1 (références entières) en v2
    (références par avatar_id stable).

    Transformations appliquées
    ──────────────────────────
    1. Avatars      : ajout de avatar_id (uuid) à chaque avatar sauvegardé
    2. Loops        : model_avatar_index (int) → model_avatar_id (str)
                      generated_indices → generated_ids = [] (régénéré)
    3. GranuloGen   : generated_indices → generated_ids = []
    4. ForLoops     : generated_indices → generated_refs = []
    5. avatar_groups: [0, 1, …] → [avatar_id, …] pour les avatars MANUAL
                      Les avatars générés (loops/granulo) seront re-ajoutés
                      automatiquement pendant _rebuild_pylmgc_objects.
    6. DOF ops      : target_value int → avatar_id pour type 'avatar'
    7. PostPro      : target_value int → avatar_id pour type 'avatar'

    Les indices pointant vers des avatars GÉNÉRÉS (hors JSON) sont supprimés
    des groupes — ils seront recréés proprement lors du rebuild.
    """
    from .models import new_avatar_id   # générateur d'uuid

    # ── 1. Assigner des avatar_ids aux avatars MANUAL sauvegardés ─────────
    avatars_data = data.get('avatars', [])
    idx_to_id: Dict[int, str] = {}

    for i, av_data in enumerate(avatars_data):
        if 'avatar_id' not in av_data:
            av_data['avatar_id'] = new_avatar_id()
        idx_to_id[i] = av_data['avatar_id']

    # ── 2. Loops ──────────────────────────────────────────────────────────
    for loop_data in data.get('loops', []):
        # model_avatar_index → model_avatar_id
        if 'model_avatar_index' in loop_data:
            old_idx = loop_data.pop('model_avatar_index')
            loop_data['model_avatar_id'] = idx_to_id.get(old_idx, '')

        # generated_indices → generated_ids (vide, sera régénéré)
        loop_data.pop('generated_indices', None)
        loop_data.setdefault('generated_ids', [])

    # ── 3. GranuloGeneration ──────────────────────────────────────────────
    for gen_data in data.get('granulo_generations', []):
        gen_data.pop('generated_indices', None)
        gen_data.setdefault('generated_ids', [])

    # ── 4. ForLoops ───────────────────────────────────────────────────────
    for fl_data in data.get('for_loops', []):
        fl_data.pop('generated_indices', None)
        fl_data.setdefault('generated_refs', [])

    # ── 5. avatar_groups ──────────────────────────────────────────────────
    # Seuls les avatars MANUAL (présents dans le JSON) peuvent être mappés.
    # Les indices vers des avatars générés (>= len(avatars_data)) sont
    # ignorés — ils seront recrées correctement lors du rebuild.
    groups = data.get('avatar_groups', {})
    new_groups: Dict[str, List[str]] = {}
    for grp_name, refs in groups.items():
        new_refs = []
        for ref in refs:
            if isinstance(ref, int):
                mapped = idx_to_id.get(ref)
                if mapped:
                    new_refs.append(mapped)
                # Sinon : avatar généré — sera re-ajouté lors du rebuild
            elif isinstance(ref, str):
                new_refs.append(ref)   # déjà migré ou déterministe
        new_groups[grp_name] = new_refs
    data['avatar_groups'] = new_groups

    # ── 6. Opérations DOF ────────────────────────────────────────────────
    for op_data in data.get('operations', []):
        if op_data.get('target') == 'avatar':
            tv = op_data.get('target_value')
            if isinstance(tv, int):
                op_data['target_value'] = idx_to_id.get(tv, f'_v1_unmapped_{tv}')

    # ── 7. Commandes PostPro ─────────────────────────────────────────────
    for pp_data in data.get('postpro_creations', []):
        target_info = pp_data.get('target_info')
        if target_info and target_info.get('type') == 'avatar':
            tv = target_info.get('value')
            if isinstance(tv, int):
                target_info['value'] = idx_to_id.get(tv, f'_v1_unmapped_{tv}')

    # ── Marquer comme migré ───────────────────────────────────────────────
    data['schema_version'] = 2
    data['_migrated_from'] = 'v1'   # trace pour debug

    return data