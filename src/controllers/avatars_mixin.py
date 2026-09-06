"""AvatarsMixin — CRUD avatars + duplication."""
import copy as _copy
from typing import Optional, List, Dict

from ..core.models import Avatar, AvatarOrigin, new_avatar_id
from ..core.validators import AvatarValidator
from ..core.pylmgc_bridge import LMGC90Bridge


class AvatarsMixin:

    def add_avatar(self, avatar: Avatar, create_pylmgc: bool = True) -> int:
        model = next((m for m in self.state.models if m.name == avatar.model_name), None)
        if not model:
            raise ValueError(f"Modèle '{avatar.model_name}' introuvable")
        AvatarValidator.validate_or_raise(avatar, model)
        if create_pylmgc:
            mat_obj = self._pylmgc_materials.get(avatar.material_name)
            mod_obj = self._pylmgc_models.get(avatar.model_name)
            if not mat_obj:
                raise ValueError(f"Matériau '{avatar.material_name}' introuvable")
            if not mod_obj:
                raise ValueError(f"Modèle '{avatar.model_name}' introuvable")
            from ..core.app_logger import get_logger
            logger = get_logger('controller')
            logger.debug(
                "add_avatar avant native: type=%s center=%s radius=%s",
                avatar.avatar_type.value, avatar.center, avatar.radius,
            )
            body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
            logger.debug("add_avatar après create_avatar")
            # None pour MESH_DEFORMABLE sans mesh_params — placeholder alignement
            if body_obj is not None:
                self._bodies_container.addAvatar(body_obj)
            logger.debug("add_avatar après containers.addAvatar")
            self._pylmgc_bodies.append(body_obj)
        else:
            self._pylmgc_bodies.append(None)
        self.state.avatars.append(avatar)
        if not self._batch_mode:
            self.state_changed.emit()
        return len(self.state.avatars) - 1

    def update_avatar(self, index: int, avatar: Avatar) -> None:
        if not (0 <= index < len(self.state.avatars)):
            raise ValueError(f"Index {index} invalide")
        model = next((m for m in self.state.models if m.name == avatar.model_name), None)
        if not model:
            raise ValueError(f"Modèle '{avatar.model_name}' introuvable")
        AvatarValidator.validate_or_raise(avatar, model)
        mat_obj = self._pylmgc_materials.get(avatar.material_name)
        mod_obj = self._pylmgc_models.get(avatar.model_name)
        if not mat_obj:
            raise ValueError(f"Matériau '{avatar.material_name}' introuvable")
        if not mod_obj:
            raise ValueError(f"Modèle '{avatar.model_name}' introuvable")
        old_body = self._pylmgc_bodies[index]
        if old_body is not None:
            self._bodies_container.remove(old_body)
        body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
        if body_obj is not None:
            self._bodies_container.addAvatar(body_obj)
        self._pylmgc_bodies[index] = body_obj
        self.state.avatars[index] = avatar

    def get_avatar(self, index: int) -> Optional[Avatar]:
        if 0 <= index < len(self.state.avatars):
            return self.state.avatars[index]
        return None

    def is_avatar_used(self, index: int) -> tuple[bool, list[str]]:
        refs = []
        if not (0 <= index < len(self.state.avatars)):
            return False, []
        aid = self.state.avatars[index].avatar_id

        for i, loop in enumerate(self.state.loops):
            if loop.model_avatar_id == aid:
                refs.append(f"Boucle #{i + 1} ({loop.loop_type})")

        for grp_name, avatar_ids in self.state.avatar_groups.items():
            if aid in avatar_ids:
                refs.append(f"Groupe '{grp_name}'")

        for i, op in enumerate(self.state.operations):          # ✅ corrigé
            if op.target_type == 'avatar' and op.target_value == aid:
                refs.append(f"Opération DOF #{i + 1} (avatar)")
            elif op.target_type == 'group':
                group_ids = self.state.avatar_groups.get(op.target_value, [])
                if aid in group_ids:
                    refs.append(f"Opération DOF #{i + 1} (groupe '{op.target_value}')")

        for i, cmd in enumerate(self.state.postpro_commands):   # ✅ corrigé
            if cmd.target_type == 'avatar' and cmd.target_value == aid:
                refs.append(f"Commande post #{i + 1} (avatar)")
            elif cmd.target_type == 'group':
                group_ids = self.state.avatar_groups.get(cmd.target_value, [])
                if aid in group_ids:
                    refs.append(f"Commande post #{i + 1} (groupe '{cmd.target_value}')")
        return len(refs) > 0, refs

    def remove_avatar(self, index: int) -> bool:
        if not (0 <= index < len(self.state.avatars)):
            return False

        avatar_id = self.state.avatars[index].avatar_id

        # Retirer l'avatar de state
        self.state.avatars.pop(index)

        # Retirer l'objet pylmgc correspondant
        body = None
        if index < len(self._pylmgc_bodies):
            body = self._pylmgc_bodies.pop(index)
        if body is not None:
            try:
                self._bodies_container.remove(body)
            except Exception as e:
                from ..core.app_logger import get_logger
                get_logger('controller').warning(
                    f"Erreur suppression avatar #{index}: {e}"
                )

        # ── Nettoyage des groupes orphelins ──────────────────────────────
        # Sans ce nettoyage, avatar_id reste dans avatar_groups indéfiniment
        # et est sauvegardé dans le JSON, créant des références fantômes.
        for grp_name in list(self.state.avatar_groups.keys()):
            group = self.state.avatar_groups[grp_name]
            if avatar_id in group:
                self.state.avatar_groups[grp_name] = [
                    aid for aid in group if aid != avatar_id
                ]

        return True

    def get_avatars(self, include_generated: bool = True) -> List[Avatar]:
        if include_generated:
            return self.state.avatars.copy()
        return [a for a in self.state.avatars if a.origin == AvatarOrigin.MANUAL]

    def duplicate_avatar(
        self, index: int, n_copies: int, offset: list, group_name: str = None
    ) -> list:
        if not (0 <= index < len(self.state.avatars)):
            raise IndexError(f"Index avatar {index} hors bornes.")
        if n_copies < 1:
            raise ValueError("n_copies doit être ≥ 1.")
        if not offset:
            raise ValueError("offset ne peut pas être vide.")

        source     = self.state.avatars[index]
        dim        = len(source.center)
        new_indices = []

        self._batch_mode = True
        try:
            for k in range(1, n_copies + 1):
                clone = _copy.deepcopy(source)
                clone.avatar_id = new_avatar_id()
                clone.center = [
                    source.center[i] + k * (offset[i] if i < len(offset) else 0.0)
                    for i in range(dim)
                ]
                idx = self._add_avatar_no_validate(clone)
                new_indices.append(idx)
        finally:
            self._batch_mode = False

        if group_name:
            new_ids = [self.state.avatars[i].avatar_id for i in new_indices]
            self.state.avatar_groups.setdefault(group_name, []).extend(new_ids)

        self.state_changed.emit()
        return new_indices

    def duplicate_group(
        self,
        group_name: str,
        n_copies: int,
        offset: list,
        new_group_prefix: str = None,
    ) -> Dict[str, list]:
        if group_name not in self.state.avatar_groups:
            raise KeyError(f"Groupe '{group_name}' introuvable.")
        if n_copies < 1:
            raise ValueError("n_copies doit être ≥ 1.")
        if not offset:
            raise ValueError("offset ne peut pas être vide.")

        source_avatar_ids = self.state.avatar_groups[group_name]
        prefix  = new_group_prefix or group_name
        result: Dict[str, list] = {}

        self._batch_mode = True
        try:
            for k in range(1, n_copies + 1):
                serie_indices = []
                for aid in source_avatar_ids:
                    res = self._find_avatar_by_id(aid)
                    if res is None:
                        continue
                    src_idx, source = res
                    dim   = len(source.center)
                    clone = _copy.deepcopy(source)
                    clone.avatar_id = new_avatar_id()
                    clone.center = [
                        source.center[i] + k * (offset[i] if i < len(offset) else 0.0)
                        for i in range(dim)
                    ]
                    idx = self._add_avatar_no_validate(clone)
                    serie_indices.append(idx)

                serie_ids = [self.state.avatars[i].avatar_id for i in serie_indices]
                grp = f"{prefix}_copie_{k}"
                self.state.avatar_groups.setdefault(grp, []).extend(serie_ids)
                result[grp] = serie_ids
        finally:
            self._batch_mode = False

        self.state_changed.emit()
        return result