"""Exemple avancé : pendule suspendu par câble (loi ELASTIC_WIRE, contact point/point)."""
from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, DOFOperation,
)


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2500.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Point d'ancrage : emptyAvatar avec un unique contacteur PT2Dx ──────
    # PT2Dx ne prend aucun paramètre géométrique (juste un point matériel).
    anchor = Avatar(
        avatar_type=AvatarType.EMPTY_AVATAR,
        center=[0.0, 3.0],
        material_name="TDURx",
        model_name="rigid",
        color="REDxx",
        origin=AvatarOrigin.MANUAL,
        contactors=[{'shape': 'PT2Dx', 'color': 'REDxx', 'params': {}}],
    )
    anchor_idx = controller.add_avatar(anchor)
    anchor_id  = controller.state.avatars[anchor_idx].avatar_id

    # ── Bloquer complètement le point d'ancrage (translation + rotation) ───
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar",
        target_value=anchor_id,
        parameters={"component": [1, 2, 3], "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Masse suspendue : second point PT2Dx, relié à l'ancrage par câble ──
    bob = Avatar(
        avatar_type=AvatarType.EMPTY_AVATAR,
        center=[1.2, 1.5],
        material_name="TDURx",
        model_name="rigid",
        color="BLUEx",
        origin=AvatarOrigin.MANUAL,
        contactors=[{'shape': 'PT2Dx', 'color': 'BLUEx', 'params': {}}],
    )
    controller.add_avatar(bob)

    # ── Loi ELASTIC_WIRE — propriétés obligatoires : stiffness, prestrain ──
    controller.add_contact_law(ContactLaw(
        name="cable01",
        law_type=ContactLawType.ELASTIC_WIRE,
        properties={"stiffness": 5e5, "prestrain": 0.0},
    ))

    # ── Visibilité point/point entre ancrage et masse ───────────────────────
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="PT2Dx", candidate_color="REDxx",
        antagonist_body="RBDY2", antagonist_contactor="PT2Dx", antagonist_color="BLUEx",
        behavior_name="cable01", alert=2.5,  # alerte large : distance initiale ~1.94m
    ))

    controller.state.name = "Exemple - Pendule à câble (ELASTIC_WIRE)"