"""Exemple : deux rangées de blocs avec liaison cohésive MAC_CZM."""
from pylmgc90 import pre

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule,
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

    # ── Deux rangées de 6 blocs collées (2 assises) ────────────────────────
    lx, ly = 0.25, 0.10
    nb_cols = 6
    generated_indices = []

    for row in range(2):
        for col in range(nb_cols):
            cx = col * lx + lx / 2.0
            cy = row * ly + ly / 2.0
            brick = pre.brick2D("std", lx, ly)
            body = brick.rigidBrick(
                center=[cx, cy], model=mod_obj, material=mat_obj, color="ORANx"
            )
            controller._bodies_container.addAvatar(body)
            controller._pylmgc_bodies.append(body)

            av = Avatar(
                avatar_type=AvatarType.EMPTY_AVATAR,
                center=[cx, cy],
                material_name="brick",
                model_name="rigid",
                color="ORANx",
                origin=AvatarOrigin.MANUAL,
                wall_params={'l': lx, 'h': ly, 'brick_name': 'std'},
                contactors=[],
            )
            controller.state.avatars.append(av)
            generated_indices.append(len(controller.state.avatars) - 1)

    avatar_ids = [controller.state.avatars[i].avatar_id for i in generated_indices]
    controller.state.avatar_groups["assises_collees"] = avatar_ids

    # ── Loi de zone cohésive MAC_CZM ────────────────────────────────────────
    # Propriétés obligatoires selon ContactLawValidator._REQUIRED_PROPS :
    # ["stfr", "dyfr", "cn", "ct", "b", "w"] — toutes passées via
    # properties={...}, PAS en paramètres directs du constructeur (voir
    # correctif précédent sur ex_deformable_drop.py pour le même piège).
    controller.add_contact_law(ContactLaw(
        name="czm01",
        law_type=ContactLawType.IQS_MAC_CZM,
        properties={
            "stfr": 1e10,   # rigidité de contact statique
            "dyfr": 1e10,   # rigidité de contact dynamique
            "cn":   5e6,    # résistance normale à rupture
            "ct":   3e6,    # résistance tangentielle à rupture
            "b":    1.0,    # paramètre de mélange mode I/II
            "w":    0.02,   # énergie de rupture
        },
    ))

    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="POLYG", candidate_color="ORANx",
        antagonist_body="RBDY2", antagonist_contactor="POLYG", antagonist_color="ORANx",
        behavior_name="czm01", alert=0.02,
    ))

    controller.state.name = "Exemple - Mur avec liaisons cohésives (CZM)"