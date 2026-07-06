"""PostProMixin — commandes de post-traitement."""
from typing import Optional

from ..core.models import PostProCommand
from pylmgc90 import pre


class PostProMixin:

    def add_postpro_command(self, command: PostProCommand) -> None:
        rigid_set = self._resolve_postpro_target(command)
        if rigid_set:
            cmd = pre.postpro_command(
                name=command.name, step=command.step, rigid_set=rigid_set
            )
        else:
            cmd = pre.postpro_command(name=command.name, step=command.step)
        self._postpro_container.addCommand(cmd)
        self.state.postpro_commands.append(command)

    def remove_postpro_command(self, index: int) -> bool:
        if 0 <= index < len(self.state.postpro_commands):
            self.state.postpro_commands.pop(index)
            return True
        return False

    def update_postpro_command(self, index: int, command: PostProCommand) -> None:
        if not (0 <= index < len(self.state.postpro_commands)):
            raise ValueError(f"Index {index} invalide")
        self._postpro_container = pre.postpro_commands()
        self.state.postpro_commands[index] = command
        for cmd in self.state.postpro_commands:
            rigid_set = self._resolve_postpro_target(cmd)
            cmd_obj = (
                pre.postpro_command(name=cmd.name, step=cmd.step, rigid_set=rigid_set)
                if rigid_set
                else pre.postpro_command(name=cmd.name, step=cmd.step)
            )
            self._postpro_container.addCommand(cmd_obj)

    def get_postpro_command(self, index: int) -> Optional[PostProCommand]:
        if 0 <= index < len(self.state.postpro_commands):
            return self.state.postpro_commands[index]
        return None

    # ── Utilitaire interne ────────────────────────────────────────────────────

    def _resolve_postpro_target(self, command: PostProCommand):
        """Résout la cible d'une commande postpro en liste d'objets pylmgc."""
        if command.target_type == 'avatar':
            res = self._find_avatar_by_id(command.target_value)
            if res:
                idx, _ = res
                if 0 <= idx < len(self._pylmgc_bodies):
                    body = self._pylmgc_bodies[idx]
                    if body is not None:
                        return [body]
        elif command.target_type == 'group':
            avatar_ids = self.state.avatar_groups.get(command.target_value, [])
            bodies = []
            for aid in avatar_ids:
                res = self._find_avatar_by_id(aid)
                if res:
                    idx, _ = res
                    if (0 <= idx < len(self._pylmgc_bodies)
                            and self._pylmgc_bodies[idx] is not None):
                        bodies.append(self._pylmgc_bodies[idx])
            return bodies if bodies else None
        return None
