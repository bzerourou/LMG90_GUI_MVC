"""Exemple : boucle géométrique Cercle — 12 disques autour d'un centre."""
from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin, Loop,
)


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2500.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    model_disk = Avatar(
        avatar_type=AvatarType.RIGID_DISK,
        center=[0.0, 0.0],
        material_name="TDURx",
        model_name="rigid",
        color="ORANx",
        origin=AvatarOrigin.MANUAL,
        radius=0.15,
    )
    model_idx = controller.add_avatar(model_disk)
    model_id = controller.state.avatars[model_idx].avatar_id

    loop = Loop(
        loop_type="Cercle",
        model_avatar_id=model_id,
        count=12,
        radius=2.0,
        offset_x=0.0,
        offset_y=0.0,
        group_name="couronne",
    )
    controller.generate_loop(loop)

    controller.state.name = "Exemple - Boucle Cercle"