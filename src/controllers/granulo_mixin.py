"""GranuloMixin — génération granulométrique."""
from typing import Optional, List

import numpy as np

from ..core.models import Avatar, AvatarOrigin, AvatarType, GranuloGeneration
from ..core.generators import GranuloGenerator
from ..core.particle_population import ParticlePopulation


class GranuloMixin:

    def generate_granulo(self, config: GranuloGeneration) -> List[int]:
        if config.use_particle_population:
            nb_particles, coordinates, radii = GranuloGenerator.generate(config)
            self.create_granulo_population_from_arrays(config, coordinates, radii)
            return []

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
        if granulo.use_particle_population and granulo.population_id:
            self.remove_particle_population(granulo.population_id)
            self.state.granulo_generations.pop(index)
            return True
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
    def create_granulo_population_from_arrays(
        self,
        config: GranuloGeneration,
        centers: np.ndarray,
        radii: np.ndarray,
    ) -> "ParticlePopulation":
        """Crée une ParticlePopulation à partir de centres et rayons déjà calculés."""
        population = ParticlePopulation.create(
            avatar_type=AvatarType(config.avatar_type),
            material_name=config.material_name,
            model_name=config.model_name,
            color=config.color,
            origin=AvatarOrigin.GRANULO,
            centers=centers,
            radii=radii,
            group_name=config.group_name,
            population_id=config.population_id,
        )
        config.population_id = population.population_id

        mat_obj = self._pylmgc_materials.get(config.material_name)
        mod_obj = self._pylmgc_models.get(config.model_name)
        if not mat_obj:
            raise ValueError(f"Matériau '{config.material_name}' introuvable")
        if not mod_obj:
            raise ValueError(f"Modèle '{config.model_name}' introuvable")
        from ..core.pylmgc_bridge import LMGC90Bridge
        bodies = LMGC90Bridge.create_avatars_from_population(population, mod_obj, mat_obj)
        for body in bodies:
            self._bodies_container.addAvatar(body)
            self._pylmgc_bodies.append(body)
        self._pylmgc_population_bodies[population.population_id] = bodies

        if not self._is_loading:
            if config not in self.state.granulo_generations:
                self.state.granulo_generations.append(config)
            if population not in self.state.particle_populations:
                self.state.particle_populations.append(population)

        if config.group_name:
            self.state.populations_groups.setdefault(config.group_name, []).append(
                population.population_id
            )

        self.state_changed.emit()
        return population

    def generate_granulo_population(self, config: GranuloGeneration) -> "ParticlePopulation":
        """
        Variante SoA de generate_granulo() : produit un ParticlePopulation
        unique au lieu de N Avatar individuels dans state.avatars.
        """
        nb_particles, coordinates, radii = GranuloGenerator.generate(config)
        return self.create_granulo_population_from_arrays(config, coordinates, radii)

    def remove_particle_population(self, population_id: str) -> bool:
        """Supprime une population entière (tous les bodies pylmgc90 associés)."""
        pop = next(
            (p for p in self.state.particle_populations if p.population_id == population_id),
            None,
        )
        if pop is None:
            return False

        bodies = self._pylmgc_population_bodies.pop(population_id, [])
        for body in bodies:
            try:
                self._bodies_container.remove(body)
            except Exception as e:
                from ..core.app_logger import get_logger
                get_logger('controller').warning(
                    f"Erreur suppression body population '{population_id}': {e}"
                )

        self.state.particle_populations.remove(pop)

        for grp_name in list(self.state.populations_groups.keys()):
            self.state.populations_groups[grp_name] = [
                pid for pid in self.state.populations_groups[grp_name]
                if pid != population_id
            ]
            if not self.state.populations_groups[grp_name]:
                del self.state.populations_groups[grp_name]

        self.state_changed.emit()
        return True