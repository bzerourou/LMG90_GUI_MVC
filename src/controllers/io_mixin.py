"""IOMixin — nouveau projet, save/load, DATBOX."""
from pathlib import Path
from typing import Optional

from ..core.models import ProjectState
from ..core.serializers import ProjectSerializer
from pylmgc90 import pre


class IOMixin:

    def new_project(self, name: str) -> None:
        """Crée un nouveau projet vide."""
        self.state = ProjectState(name=name)
        self.project_path = None
        self._reset_containers()

    def save_project(self, filepath: Optional[Path] = None) -> Path:
        if filepath:
            self.project_path = filepath
        elif not self.project_path:
            raise ValueError("Aucun chemin de sauvegarde défini")
        ProjectSerializer.save(self.state, self.project_path)
        return self.project_path

    def load_project(self, filepath: Path) -> None:
        try:
            self._is_loading = True
            self.state = ProjectSerializer.load(filepath)
            self.project_path = filepath
            self._rebuild_pylmgc_objects()
            self._restore_factory_avatars()
        finally:
            self._is_loading = False

    def generate_datbox(self, output_path: Path) -> None:
        pre.writeDatbox(
            dim=self.state.dimension,
            mats=self._materials_container,
            mods=self._models_container,
            bodies=self._bodies_container,
            tacts=self._contact_laws_container,
            sees=self._visibility_container,
            post=self._postpro_container,
            datbox_path=str(output_path),
        )
