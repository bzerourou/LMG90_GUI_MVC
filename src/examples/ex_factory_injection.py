"""Exemple : Particle Factory — injection périodique de 200 particules par vagues."""
from ..core.models import Material, MaterialType, Model
from ..core.particle_factory import (
    FactoryConfig, FactoryType, ZoneShape, ContainerShape, ParticleFactory,
)


def build(controller) -> None:
    controller.state.dimension = 2

    # ── Matériau et modèle ───────────────────────────────────────────────
    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2500.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Configuration de la factory ──────────────────────────────────────
    config = FactoryConfig(
        name="injection1",
        factory_type=FactoryType.PERIODIC.value,
        dimension=2,
        particle_type="rigidDisk",
        radius_min=0.04,
        radius_max=0.06,
        nb_particles=200,
        model_name="rigid",
        material_name="TDURx",
        color="BLUEx",
        seed=7,
        zone_shape=ZoneShape.BOX.value,
        zone_center=[0.0, 0.0, 2.0],
        zone_lx=1.5,
        zone_ly=1.0,
        zone_lz=0.4,
        batch_size=20,
        start_step=1,
        interval_steps=50,
        container_shape=ContainerShape.BOX_OPEN.value,
        container_lx=2.0,
        container_ly=2.0,
        container_lz=3.0,
        container_wall_r=0.01,
        container_center=[0.0, 0.0, 0.0],
    )

    engine = ParticleFactory()
    nb_existing = len(controller.state.avatars)
    engine.reset_body_counter(nb_existing + 1)
    engine.add(config)

    controller.state.factories = engine.to_list_of_dicts()
    controller.state_changed.emit()

    controller.state.name = "Exemple - Particle Factory (injection périodique)"