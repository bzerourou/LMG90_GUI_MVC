"""Exemple : dépôt granulométrique de 500 disques via granulo_Random + depositInBox2D."""
from ..core.models import (
    Material, MaterialType, Model, GranuloGeneration,
)


def build(controller) -> None:
    controller.state.dimension = 2

    # ── Matériau et modèle ───────────────────────────────────────────────
    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2600.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Configuration du dépôt ────────────────────────────────────────────
    config = GranuloGeneration(
        nb_particles=500,
        radius_min=0.03,
        radius_max=0.08,
        container_type="Box2D",
        container_params={'lx': 4.0, 'ly': 4.0},
        model_name="rigid",
        material_name="TDURx",
        avatar_type="rigidDisk",
        color="BLUEx",
        seed=42,
        group_name="depot_box",
    )

    # ── Génération via l'API contrôleur (identique au chemin GranuloTab) ──
    controller.generate_granulo(config)

    controller.state.name = "Exemple - Dépôt granulométrique"