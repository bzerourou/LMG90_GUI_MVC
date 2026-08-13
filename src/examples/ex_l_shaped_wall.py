"""Exemple avancé : structure en L (deux murs de briques) recevant un dépôt granulométrique."""
from pylmgc90 import pre

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, GranuloGeneration,
    DOFOperation,
)


def _place_bricks(controller, mat_name, mod_name, mat_obj, mod_obj,
                   nb_rows, nb_cols, lx, ly, offset_x, offset_y, color):
    """Place une grille de briques (Stack Bond) et retourne les indices créés."""
    indices = []
    for row in range(nb_rows):
        for col in range(nb_cols):
            cx = offset_x + col * lx + lx / 2.0
            cy = offset_y + row * ly + ly / 2.0
            brick = pre.brick2D("std", lx, ly)
            body = brick.rigidBrick(
                center=[cx, cy], model=mod_obj, material=mat_obj, color=color
            )
            controller._bodies_container.addAvatar(body)
            controller._pylmgc_bodies.append(body)

            av = Avatar(
                avatar_type=AvatarType.EMPTY_AVATAR,
                center=[cx, cy],
                material_name=mat_name, model_name=mod_name, color=color,
                origin=AvatarOrigin.MANUAL,
                wall_params={'l': lx, 'h': ly, 'brick_name': 'std'},
                contactors=[ {'shape': 'POLYG', 'color': color} ],  # il faut un contacteur pour chaque brique, mais on ne le définit pas ici
            )
            controller.state.avatars.append(av)
            indices.append(len(controller.state.avatars) - 1)
    return indices


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="brick", material_type=MaterialType.RIGID, density=1800.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))
    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2600.0
    ))

    mat_obj = controller._pylmgc_materials["brick"]
    mod_obj = controller._pylmgc_models["rigid"]

    lx, ly = 0.25, 0.10

    # ── Mur horizontal (base) — 6 colonnes x 2 rangs ────────────────────────
    idx_h = _place_bricks(
        controller, "brick", "rigid", mat_obj, mod_obj,
        nb_rows=2, nb_cols=6, lx=lx, ly=ly, offset_x=0.0, offset_y=0.0,
        color="ORANx",
    )
    # ── Mur vertical (côté) — 2 colonnes x 6 rangs ──────────────────────────
    # Léger recouvrement au coin (2x2 briques communes) : simplification
    # volontaire pour un angle solide sans gérer la découpe/rotation des
    # briques d'angle (hors scope pédagogique de cet exemple).
    idx_v = _place_bricks(
        controller, "brick", "rigid", mat_obj, mod_obj,
        nb_rows=6, nb_cols=2, lx=lx, ly=ly, offset_x=0.0, offset_y=0.0,
        color="ORANx",
    )

    all_ids = [controller.state.avatars[i].avatar_id for i in (idx_h + idx_v)]
    controller.state.avatar_groups["mur_L"] = all_ids

    # ── Immobiliser toute la structure en L ─────────────────────────────────
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="group", target_value="mur_L",
        parameters={"component": [1, 2, 3], "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Dépôt granulométrique tombant dans le coin du L ─────────────────────
    config = GranuloGeneration(
        nb_particles=120,
        radius_min=0.03, radius_max=0.05,
        container_type="Box2D",
        container_params={'lx': 1.2, 'ly': 0.8},
        model_name="rigid", material_name="TDURx",
        avatar_type="rigidDisk", color="BLUEx", seed=5,
        group_name="grains_coin",
    )
    controller.generate_granulo(config)

    # ── Lois de contact ────────────────────────────────────────────────────
    controller.add_contact_law(ContactLaw(
        name="law01", law_type=ContactLawType.IQS_DS_CLB,
        friction = 0.4,
        properties={"stfr": 1e8, "dyfr": 1e8},
    ))
    controller.add_contact_law(ContactLaw(
        name="law02", law_type=ContactLawType.IQS_CLB, friction=0.4
    ))

    # Bricks are rigid bodies in this example: use RBDY2 + CLxxx contactor
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="POLYG", candidate_color="ORANx",
        antagonist_body="RBDY2", antagonist_contactor="POLYG", antagonist_color="ORANx",
        behavior_name="law01", alert=0.02,
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="BLUEx",
        behavior_name="law02", alert=0.05,
    ))
    # Interaction bricks <-> disks: bricks are RBDY2 with CLxxx contactor
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="POLYG", candidate_color="ORANx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="BLUEx",
        behavior_name="law02", alert=0.05,
    ))

    controller.state.name = "Exemple - Structure en L + dépôt granulométrique"