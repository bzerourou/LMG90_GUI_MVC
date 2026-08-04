"""Exemple avancé : Particle Factory avec conteneur silo + lois de contact complètes."""
from ..core.models import Material, MaterialType, Model, ContactLaw, ContactLawType
from ..core.models import VisibilityRule, PostProCommand
from ..core.particle_factory import (
    FactoryConfig, FactoryType, ZoneShape, ContainerShape, ParticleFactory,
)


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2500.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Factory avec conteneur silo (parois générées automatiquement dans
    # le script pre.py exporté — voir PreCodeGenerator._write_container_2d) ─
    config = FactoryConfig(
        name="silo1",
        factory_type=FactoryType.PERIODIC.value,
        dimension=2,
        particle_type="rigidDisk",
        radius_min=0.04, radius_max=0.06,
        nb_particles=300,
        model_name="rigid", material_name="TDURx", color="BLUEx",
        seed=3,
        zone_shape=ZoneShape.BOX.value,
        zone_center=[0.0, 0.0, 4.0],
        zone_lx=1.2, zone_ly=1.0, zone_lz=0.5,
        batch_size=15,
        start_step=1,
        interval_steps=30,
        container_shape=ContainerShape.SILO_BOX.value,
        container_lx=1.5, container_ly=1.5, container_lz=5.0,
        container_wall_r=0.02,
        container_center=[0.0, 0.0, 0.0],
    )

    engine = ParticleFactory()
    nb_existing = len(controller.state.avatars)
    engine.reset_body_counter(nb_existing + 1)
    engine.add(config)
    controller.state.factories = engine.to_list_of_dicts()

    # ── Lois de contact — appliquées aux particules une fois le script
    # pre.py exécuté et les avatars factory chargés (Charger Factory) ──────
    controller.add_contact_law(ContactLaw(
        name="silo_law", law_type=ContactLawType.IQS_CLB, friction=0.35
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="BLUEx",
        behavior_name="silo_law", alert=0.05,
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="GRAYx",
        behavior_name="silo_law", alert=0.05,
    ))

    controller.add_postpro_command(PostProCommand(name="KINETIC ENERGY", step=10))
    controller.add_postpro_command(PostProCommand(name="COORDINATION NUMBER", step=50))

    controller.state.name = "Exemple - Factory en silo (injection périodique)"