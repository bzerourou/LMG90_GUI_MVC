"""Exemple : avatar composite haltère — 2 disques + 1 jonc via emptyAvatar."""
from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
)


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2500.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Avatar composite : haltère (2 disques + jonc de liaison) ──────────
    # Utilise le mécanisme de contacteurs manuels (emptyAvatar), identique
    # à celui exposé par AvatarFactory.create_dumbbell_2d (core/avatar_factory.py)
    # mais construit ici explicitement pour la pédagogie.
    length      = 0.4
    disk_radius = 0.06
    half_length = length / 2.0

    dumbbell = Avatar(
        avatar_type=AvatarType.EMPTY_AVATAR,
        center=[0.0, 2.0],
        material_name="TDURx",
        model_name="rigid",
        color="VIOLx",
        origin=AvatarOrigin.MANUAL,
        contactors=[
            {
                'shape': 'DISKx',
                'color': 'VIOLx',
                'params': {'byrd': disk_radius, 'coor': [-half_length, 0.0]},
            },
            {
                'shape': 'DISKx',
                'color': 'VIOLx',
                'params': {'byrd': disk_radius, 'coor': [half_length, 0.0]},
            },
            {
                'shape': 'JONCx',
                'color': 'VIOLx',
                'params': {'axe1': length, 'axe2': disk_radius * 0.3},
            },
        ],
    )
    controller.add_avatar(dumbbell)

    # ── Sol : mur lisse fixe pour voir l'haltère tomber et rebondir ────────
    floor = Avatar(
        avatar_type=AvatarType.SMOOTH_WALL,
        center=[0.0, -0.05],
        material_name="TDURx",
        model_name="rigid",
        color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        wall_params={'l': 2.0, 'h': 0.1, 'nb_polyg': 20},
    )
    controller.add_avatar(floor)

    controller.state.name = "Exemple - Avatar composite (haltère)"