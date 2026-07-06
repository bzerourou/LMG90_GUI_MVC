"""LoopsMixin — boucles géométriques (Cercle, Grille, Ligne, Spirale)."""
from typing import Optional, List

from ..core.models import Avatar, AvatarOrigin, Loop
from ..core.generators import LoopGenerator


class LoopsMixin:

    def generate_loop(self, loop: Loop) -> List[int]:
        """Génère des avatars selon une boucle (référence par avatar_id)."""
        res = self._find_avatar_by_id(loop.model_avatar_id)
        if res is None:
            raise ValueError(f"Avatar modèle '{loop.model_avatar_id}' introuvable")
        _, model_avatar = res

        centers          = LoopGenerator.generate_positions(loop)
        generated_indices = []

        for center in centers:
            new_avatar = Avatar(
                avatar_type     = model_avatar.avatar_type,
                center          = center,
                material_name   = model_avatar.material_name,
                model_name      = model_avatar.model_name,
                color           = model_avatar.color,
                origin          = AvatarOrigin.LOOP,
                radius          = model_avatar.radius,
                axis            = model_avatar.axis,
                vertices        = model_avatar.vertices,
                nb_vertices     = model_avatar.nb_vertices,
                generation_type = model_avatar.generation_type,
                is_hollow       = model_avatar.is_hollow,
                wall_params     = model_avatar.wall_params,
                contactors      = model_avatar.contactors,
            )
            idx = self.add_avatar(new_avatar)
            generated_indices.append(idx)

        loop.generated_ids = [
            self.state.avatars[idx].avatar_id for idx in generated_indices
        ]

        if not self._is_loading:
            self.state.loops.append(loop)

        if loop.group_name:
            self.state.avatar_groups.setdefault(loop.group_name, []).extend(
                loop.generated_ids
            )

        return generated_indices

    def remove_loop(self, index: int) -> bool:
        if not (0 <= index < len(self.state.loops)):
            return False
        loop = self.state.loops[index]
        for aid in loop.generated_ids:
            res = self._find_avatar_by_id(aid)
            if res:
                self.remove_avatar(res[0])
        self.state.loops.pop(index)
        return True

    def get_loop(self, index: int) -> Optional[Loop]:
        if 0 <= index < len(self.state.loops):
            return self.state.loops[index]
        return None

    def update_loop(self, index: int, loop: Loop) -> None:
        if not (0 <= index < len(self.state.loops)):
            raise ValueError(f"Index {index} invalide")

        old_loop        = self.state.loops[index]
        old_generated   = list(old_loop.generated_ids)

        # Supprimer les anciens avatars
        for aid in old_generated:
            res = self._find_avatar_by_id(aid)
            if res:
                self.remove_avatar(res[0])

        self.state.loops[index] = loop

        # Trouver l'avatar modèle
        res = self._find_avatar_by_id(loop.model_avatar_id)
        if res is None:
            raise ValueError(f"Avatar modèle '{loop.model_avatar_id}' introuvable")
        _, model_avatar = res

        centers          = LoopGenerator.generate_positions(loop)
        generated_indices = []

        for center in centers:
            new_avatar = Avatar(
                avatar_type     = model_avatar.avatar_type,
                center          = center,
                material_name   = model_avatar.material_name,
                model_name      = model_avatar.model_name,
                color           = model_avatar.color,
                origin          = AvatarOrigin.LOOP,
                radius          = model_avatar.radius,
                axis            = model_avatar.axis,
                vertices        = model_avatar.vertices,
                nb_vertices     = model_avatar.nb_vertices,
                generation_type = model_avatar.generation_type,
                is_hollow       = model_avatar.is_hollow,
                wall_params     = model_avatar.wall_params,
                contactors      = model_avatar.contactors,
            )
            idx = self.add_avatar(new_avatar)
            generated_indices.append(idx)

        loop.generated_ids = [
            self.state.avatars[idx].avatar_id for idx in generated_indices
        ]

        # Mettre à jour les groupes
        if old_loop.group_name and old_loop.group_name in self.state.avatar_groups:
            old_ids = set(old_generated)
            self.state.avatar_groups[old_loop.group_name] = [
                aid for aid in self.state.avatar_groups[old_loop.group_name]
                if aid not in old_ids
            ]

        if loop.group_name:
            self.state.avatar_groups.setdefault(loop.group_name, []).extend(
                loop.generated_ids
            )
