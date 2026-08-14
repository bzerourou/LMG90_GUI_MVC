"""
Exemple avancé : tambour rotatif (drum) contenant un dépôt granulométrique.

Le tambour est un rigidDisk creux (is_hollow=True) — LMGC90 le représente
via un contacteur xKSID (paroi cylindrique intérieure), pas DISKx. C'est
le même mécanisme que le conteneur "Drum2D" utilisé par la génération
granulométrique standard (cf. generators.py::GranuloGenerator, container
"Drum2D" -> pre.depositInDrum2D).
"""
from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, GranuloGeneration,
    DOFOperation, PostProCommand,
)


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2600.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Tambour : disque creux fixe en translation, entraîné en rotation ──
    drum = Avatar(
        avatar_type=AvatarType.RIGID_DISK,
        center=[0.0, 0.0],
        material_name="TDURx",
        model_name="rigid",
        color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        radius=2.2,
        is_hollow=True,
    )
    drum_idx = controller.add_avatar(drum)
    drum_id  = controller.state.avatars[drum_idx].avatar_id

    # Translation bloquée (le tambour reste centré) ; rotation entraînée
    # à vitesse angulaire constante (0.5 rad/s).
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=drum_id,
        parameters={"component": [1, 2], "dofty": "vlocy", "ct": 0.0},
    ))
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=drum_id,
        parameters={"component": 3, "dofty": "vlocy", "ct": 0.5},
    ))

    # ── Dépôt granulométrique à l'intérieur du tambour ──────────────────────
    config = GranuloGeneration(
        nb_particles=200,
        radius_min=0.05, radius_max=0.09,
        container_type="Drum2D",
        container_params={'r': 2.0},   # < rayon du tambour (2.2) pour rester contenu
        model_name="rigid", material_name="TDURx",
        avatar_type="rigidDisk", color="BLUEx", seed=21,
        group_name="grains_tambour",
    )
    controller.generate_granulo(config)

    # ── Lois de contact ────────────────────────────────────────────────────
    controller.add_contact_law(ContactLaw(
        name="law01", law_type=ContactLawType.IQS_CLB, friction=0.45
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="BLUEx",
        behavior_name="law01", alert=0.05,
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="xKSID", antagonist_color="GRAYx",
        behavior_name="law01", alert=0.05,
    ))

    controller.add_postpro_command(PostProCommand(name="COORDINATION NUMBER", step=50))

    controller.state.name = "Exemple - Tambour rotatif"