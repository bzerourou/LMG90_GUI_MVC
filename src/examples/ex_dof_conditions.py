"""Exemple : conditions aux limites DOF — vitesse initiale et blocage de rotation."""
from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    DOFOperation,
)


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2500.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Disque A : vitesse initiale horizontale imposée ─────────────────────
    disk_a = Avatar(
        avatar_type=AvatarType.RIGID_DISK,
        center=[-1.0, 1.0],
        material_name="TDURx",
        model_name="rigid",
        color="REDxx",
        origin=AvatarOrigin.MANUAL,
        radius=0.12,
    )
    idx_a = controller.add_avatar(disk_a)
    id_a  = controller.state.avatars[idx_a].avatar_id

    # imposeInitValue(component=1, value=...) => vitesse initiale en X
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeInitValue",
        target_type="avatar",
        target_value=id_a,
        parameters={"component": 1, "value": 2.0},
    ))

    # ── Disque B : rotation bloquée (vitesse angulaire imposée à 0) ────────
    disk_b = Avatar(
        avatar_type=AvatarType.RIGID_DISK,
        center=[1.0, 1.0],
        material_name="TDURx",
        model_name="rigid",
        color="VERTx",
        origin=AvatarOrigin.MANUAL,
        radius=0.12,
    )
    idx_b = controller.add_avatar(disk_b)
    id_b  = controller.state.avatars[idx_b].avatar_id

    # imposeDrivenDof sur la composante de rotation (3 = angle en 2D)
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar",
        target_value=id_b,
        parameters={"component": 3, "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Sol pour visualiser l'effet des conditions imposées ─────────────────
    floor = Avatar(
        avatar_type=AvatarType.SMOOTH_WALL,
        center=[0.0, -0.05],
        material_name="TDURx",
        model_name="rigid",
        color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        wall_params={'l': 4.0, 'h': 0.1, 'nb_polyg': 20},
    )
    controller.add_avatar(floor)

    controller.state.name = "Exemple - Conditions aux limites DOF"