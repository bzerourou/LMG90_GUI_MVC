"""FactoryMixin — chargement des avatars factory depuis le JSON metadata."""
from typing import List

from ..core.app_logger import get_logger

_log = get_logger('factory_mixin')


class FactoryMixin:

    def load_factory_avatars_from_json(
        self, json_path: str = 'factory_avatars_metadata.json'
    ) -> List[int]:
        """
        Charge les métadonnées des avatars factory et les ajoute au projet.
        Les avatar_ids sont déterministes (schéma "factory_{name}_{type}_{i}"),
        ce qui garantit leur stabilité entre sessions.
        """
        from ..core.particle_factory import (
            load_factory_avatars_from_json,
            create_avatars_from_factory_metadata,
        )
        try:
            metadata = load_factory_avatars_from_json(json_path)
        except FileNotFoundError as e:
            _log.warning(f"Impossible de charger factory avatars: {e}")
            return []

        avatars_to_add = create_avatars_from_factory_metadata(metadata)
        if not avatars_to_add:
            _log.warning("Aucun avatar à créer depuis le JSON de factory")
            return []

        was_batch        = self._batch_mode
        self._batch_mode = True
        try:
            indices = []
            for avatar in avatars_to_add:
                idx = self.add_avatar(avatar, create_pylmgc=False)
                indices.append(idx)
            self.state_changed.emit()
            _log.info(f"{len(indices)} factory avatar(s) chargé(s)")
            return indices
        finally:
            self._batch_mode = was_batch