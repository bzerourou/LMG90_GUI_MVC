"""Exemple : dépôt granulométrique dans une cellule de Couette (anneau)."""
from ..core.models import Material, MaterialType, Model, GranuloGeneration


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2600.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Dépôt dans un anneau (Couette2D : rint < r < rext) ──────────────────
    config = GranuloGeneration(
        nb_particles=250,
        radius_min=0.03,
        radius_max=0.05,
        container_type="Couette2D",
        container_params={'rint': 1.0, 'rext': 2.0},
        model_name="rigid",
        material_name="TDURx",
        avatar_type="rigidDisk",
        color="TURQx",
        seed=11,
        group_name="depot_couette",
    )
    controller.generate_granulo(config)

    controller.state.name = "Exemple - Cisaillement en cellule de Couette"