"""Exemple : grille 3x3 de sphères rigides empilées sur un plan 3D."""
from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule,
)


def build(controller) -> None:
    controller.state.dimension = 3

    # ── Matériau et modèle ───────────────────────────────────────────────
    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2500.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx3D", dimension=3
    ))

    # ── Sol : plan rigide fixe ────────────────────────────────────────────
    floor = Avatar(
        avatar_type=AvatarType.RIGID_PLAN,
        center=[0.0, 0.0, -0.1],
        material_name="TDURx",
        model_name="rigid",
        color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        axis={'axe1': 2.0, 'axe2': 2.0, 'axe3': 0.05},
    )
    controller.add_avatar(floor)

    # ── Grille 3x3 de sphères ─────────────────────────────────────────────
    # Placées directement (et non via une boucle "Loop"/LoopGenerator,
    # dont le générateur "Grille" ne produit que des centres 2D — voir
    # core/generators.py::LoopGenerator.generate_grid). Une vraie boucle
    # 3D nécessiterait d'étendre LoopGenerator, hors scope de cet exemple.
    step   = 0.6
    z0     = 1.5
    side   = 3
    origin_x = -step * (side - 1) / 2.0
    origin_y = -step * (side - 1) / 2.0

    generated_indices = []
    for i in range(side * side):
        x = origin_x + (i % side) * step
        y = origin_y + (i // side) * step
        sphere = Avatar(
            avatar_type=AvatarType.RIGID_SPHERE,
            center=[x, y, z0],
            material_name="TDURx",
            model_name="rigid",
            color="CYANx",
            origin=AvatarOrigin.MANUAL,
            radius=0.15,
        )
        idx = controller.add_avatar(sphere)
        generated_indices.append(idx)

    avatar_ids = [controller.state.avatars[i].avatar_id for i in generated_indices]
    controller.state.avatar_groups["pile_spheres"] = avatar_ids

    # ── Loi de contact + visibilité (sphère/sphère, sphère/sol) ────────────
    law = ContactLaw(
        name="iqsc0", law_type=ContactLawType.IQS_CLB, friction=0.3
    )
    controller.add_contact_law(law)

    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY3", candidate_contactor="SPHER", candidate_color="CYANx",
        antagonist_body="RBDY3", antagonist_contactor="SPHER", antagonist_color="CYANx",
        behavior_name="iqsc0", alert=0.05,
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY3", candidate_contactor="SPHER", candidate_color="CYANx",
        antagonist_body="RBDY3", antagonist_contactor="PLANx", antagonist_color="GRAYx",
        behavior_name="iqsc0", alert=0.05,
    ))

    controller.state.name = "Exemple - Empilement de sphères 3D"