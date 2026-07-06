"""GranuloMixin — génération granulométrique."""
from typing import Optional, List

from ..core.models import Avatar, AvatarOrigin, AvatarType, GranuloGeneration
from ..core.generators import GranuloGenerator


class GranuloMixin:

    def generate_granulo(self, config: GranuloGeneration) -> List[int]:
        nb_particles, coordinates, radii = GranuloGenerator.generate(config)

        generated_indices = []
        prev_batch        = self._batch_mode
        self._batch_mode  = True
        try:
            for i in range(nb_particles):
                center = coordinates[i].tolist()
                radius = float(radii[i])
                avatar = Avatar(
                    avatar_type   = AvatarType(config.avatar_type),
                    center        = center,
                    material_name = config.material_name,
                    model_name    = config.model_name,
                    color         = config.color,
                    origin        = AvatarOrigin.GRANULO,
                    radius        = radius,
                )
                idx = self.add_avatar(avatar)
                generated_indices.append(idx)
        finally:
            self._batch_mode = prev_batch

        config.generated_ids = [
            self.state.avatars[idx].avatar_id for idx in generated_indices
        ]

        if not self._is_loading:
            self.state.granulo_generations.append(config)

        if config.group_name:
            self.state.avatar_groups.setdefault(config.group_name, []).extend(
                config.generated_ids
            )

        return generated_indices

    def remove_granulo(self, index: int) -> bool:
        if not (0 <= index < len(self.state.granulo_generations)):
            return False
        granulo = self.state.granulo_generations[index]
        for aid in granulo.generated_ids:
            res = self._find_avatar_by_id(aid)
            if res:
                self.remove_avatar(res[0])
        self.state.granulo_generations.pop(index)
        return True

    def get_granulo(self, index: int) -> Optional[GranuloGeneration]:
        if 0 <= index < len(self.state.granulo_generations):
            return self.state.granulo_generations[index]
        return None

    def create_granulo_avatar(
        self, center: list, radius: float, config: GranuloGeneration
    ) -> int:
        """Crée un seul avatar granulo (appelé depuis un worker thread)."""
        avatar = Avatar(
            avatar_type   = AvatarType(config.avatar_type),
            center        = center,
            material_name = config.material_name,
            model_name    = config.model_name,
            color         = config.color,
            origin        = AvatarOrigin.GRANULO,
            radius        = radius,
        )
        return self.add_avatar(avatar)

    def finalize_granulo(self, config: GranuloGeneration, indices: List[int]) -> None:
        """Finalise la génération granulo (appelé depuis le thread UI)."""
        config.generated_ids = [
            self.state.avatars[i].avatar_id for i in indices
        ]
        if not self._is_loading:
            self.state.granulo_generations.append(config)
        if config.group_name:
            self.state.avatar_groups.setdefault(config.group_name, []).extend(
                config.generated_ids
            )
