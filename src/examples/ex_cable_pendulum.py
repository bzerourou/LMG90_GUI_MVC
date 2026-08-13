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

    # ── Point d'ancrage : petit disque rigide, quasi ponctuel ──────────────
    # Note : PT2Dx (contacteur point pur) n'est PAS utilisable ici — c'est
    # un contacteur pour corps FEM (cf. chipy_routines_dialog.py, catégorie
    # "Noeuds ponctuels 2D (cables, barres elastiques)"), pas pour un
    # emptyAvatar rigide : computeRigidProperties() échoue faute de
    # géométrie surfacique pour en déduire une masse/inertie. Un petit
    # rigidDisk (rayon négligeable) donne le même comportement visuel et
    # physique attendu, avec une masse/inertie bien définies.
    anchor_radius = 0.02
    anchor = Avatar(
        avatar_type=AvatarType.RIGID_DISK,
        center=[0.0, 3.0],
        material_name="TDURx",
        model_name="rigid",
        color="DISxx",
        origin=AvatarOrigin.MANUAL,
        radius=anchor_radius,
        contactors=[
            {
                'shape': 'PT2Dx',
                'color': 'REDxx',
                'params': {"shift" : [0.0, 3.0]},
            },
        ],
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

    # ── Masse suspendue : second disque, relié à l'ancrage par câble ───────
    bob_radius = 0.08
    bob = Avatar(
        avatar_type=AvatarType.RIGID_DISK,
        center=[1.2, 1.5],
        material_name="TDURx",
        model_name="rigid",
        color="DIS1x",
        origin=AvatarOrigin.MANUAL,
        radius=bob_radius,
        contactors=[
            {
                'shape': 'PT2Dx',
                'color': 'BLUEx',
                'params': {"shift" : [1.2, 1.5]},
            },
        ],
    )
    controller.add_avatar(bob)


    # ── Loi ELASTIC_WIRE — propriétés obligatoires : stiffness, prestrain ──
    controller.add_contact_law(ContactLaw(
        name="law01",
        law_type=ContactLawType.ELASTIC_WIRE,
        properties={"stiffness": 5e5, "prestrain": 0.0},
    ))

    controller.add_contact_law(ContactLaw(
        name="law02",
        law_type=ContactLawType.IQS_CLB,
        friction=0.35,
    ))



    # ── Visibilité entre ancrage et masse (contacteurs DISKx désormais) ────
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="PT2Dx", candidate_color="REDxx",
        antagonist_body="RBDY2", antagonist_contactor="PT2Dx", antagonist_color="BLUEx",
        behavior_name="law01", alert=2.5,  # alerte large : distance initiale ~1.94m
    ))

    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="DISxx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="DIS1x",
        behavior_name="law02", alert=0.02,  
    ))

    controller.state.name = "Exemple - Pendule à câble (ELASTIC_WIRE)"