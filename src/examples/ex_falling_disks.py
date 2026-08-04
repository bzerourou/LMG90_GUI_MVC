"""Exemple : chute de disques 2D sous gravité dans une boîte ouverte."""
from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, Loop,
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

    # ── Sol : mur lisse fixe ─────────────────────────────────────────────
    floor = Avatar(
        avatar_type=AvatarType.SMOOTH_WALL,
        center=[0.0, -0.5],
        material_name="TDURx",
        model_name="rigid",
        color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        wall_params={'l': 4.0, 'h': 0.1, 'nb_polyg': 20},
    )
    floor_idx = controller.add_avatar(floor)
    controller.state.avatars[floor_idx]  # référence, pas de translation ici

    # ── Avatar modèle pour la boucle ──────────────────────────────────────
    model_disk = Avatar(
        avatar_type=AvatarType.RIGID_DISK,
        center=[-1.5, 1.0],
        material_name="TDURx",
        model_name="rigid",
        color="BLUEx",
        origin=AvatarOrigin.MANUAL,
        radius=0.1,
    )
    model_idx = controller.add_avatar(model_disk)
    model_id = controller.state.avatars[model_idx].avatar_id

    # ── Loi de contact + visibilité ────────────────────────────────────────
    law = ContactLaw(
        name="iqsc0", law_type=ContactLawType.IQS_CLB, friction=0.3
    )
    controller.add_contact_law(law)

    rule = VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="BLUEx",
        behavior_name="iqsc0", alert=0.05,

    )
    controller.add_visibility_rule(rule)

    rule_floor = VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="GRAYx",
        behavior_name="iqsc0", alert=0.05,
    )
    controller.add_visibility_rule(rule_floor)

    controller.state.name = "Exemple - Chute de disques 2D"