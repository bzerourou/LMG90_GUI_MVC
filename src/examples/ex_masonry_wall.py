"""Exemple : mur de maçonnerie en appareil Standard (via l'API pylmgc90 directe)."""
from pylmgc90 import pre

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType,
)


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="brick", material_type=MaterialType.RIGID, density=1800.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    mat_obj = controller._pylmgc_materials["brick"]
    mod_obj = controller._pylmgc_models["rigid"]

    lx, ly, joint = 0.20, 0.065, 0.01
    nb_rows, nb_cols = 5, 8
    group_name = "mur_briques"
    generated_indices = []

    for row in range(nb_rows):
        row_offset = (lx / 2.0) if (row % 2 == 1) else 0.0
        for col in range(nb_cols):
            cx = col * (lx + joint) + row_offset + lx / 2.0
            cy = row * (ly + joint) + ly / 2.0
            brick = pre.brick2D("std", lx, ly)
            body = brick.rigidBrick(
                center=[cx, cy], model=mod_obj, material=mat_obj, color="BLUEx"
            )
            controller._bodies_container.addAvatar(body)
            controller._pylmgc_bodies.append(body)

            av = Avatar(
                avatar_type=AvatarType.EMPTY_AVATAR,
                center=[cx, cy],
                material_name="brick",
                model_name="rigid",
                color="BLUEx",
                origin=AvatarOrigin.MANUAL,
                wall_params={'l': lx, 'h': ly, 'brick_name': 'std'},
                contactors=[],
            )
            controller.state.avatars.append(av)
            generated_indices.append(len(controller.state.avatars) - 1)

    avatar_ids = [controller.state.avatars[i].avatar_id for i in generated_indices]
    controller.state.avatar_groups[group_name] = avatar_ids
    controller.state.masonry_patterns[group_name] = {
        'pattern': 'Standard', 'lx': lx, 'ly': ly, 'lz': None,
        'nb_rows': nb_rows, 'nb_cols': nb_cols,
        'offset_x': 0.0, 'offset_y': 0.0, 'offset_z': 0.0,
        'joint': joint, 'brick_name': 'std',
        'mat': 'brick', 'mod': 'rigid', 'color': 'BLUEx', 'dim': 2,
    }

    controller.add_contact_law(ContactLaw(
        name="law01", law_type=ContactLawType.IQS_CLB, friction=0.6
    ))

    controller.state_changed.emit()
    controller.state.name = "Exemple - Mur de maçonnerie"