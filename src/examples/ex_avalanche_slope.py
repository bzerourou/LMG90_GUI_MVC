"""
Exemple avancé : avalanche granulaire sur pente inclinée.

Combine : mur incliné via rotation DOF (même pattern que la trémie et la
compression biaxiale), dépôt granulométrique au sommet, loi de friction
modérée pour observer l'écoulement le long de la pente.
"""
import math

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, GranuloGeneration,
    DOFOperation,
)


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2600.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Pente : smoothWall inclinée à 25° via rotation autour de son centre ─
    slope_length = 4.0
    slope_angle  = math.radians(25.0)
    slope = Avatar(
        avatar_type=AvatarType.SMOOTH_WALL,
        center=[0.0, 0.0],
        material_name="TDURx", model_name="rigid", color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        wall_params={'l': slope_length, 'h': 0.1, 'nb_polyg': 30},
    )
    slope_idx = controller.add_avatar(slope)
    slope_id  = controller.state.avatars[slope_idx].avatar_id

    controller.add_dof_operation(DOFOperation(
        operation_type="rotate",
        target_type="avatar", target_value=slope_id,
        parameters={
            "description": "axis",
            "center": [0.0, 0.0],
            "axis": [0.0, 0.0, 1.0],
            "alpha": slope_angle,
        },
    ))
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=slope_id,
        parameters={"component": [1, 2, 3], "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Dépôt granulométrique au sommet de la pente ──────────────────────
    # Le dépôt Box2D est centré sur l'origine indépendamment de la pente ;
    # on le décale artificiellement vers le haut de la pente en ajustant
    # la position via le centre de la boîte (offset non supporté nativement
    # par depositInBox2D — limitation du générateur existant), donc le tas
    # tombera d'abord verticalement avant de heurter la pente inclinée.
    config = GranuloGeneration(
        nb_particles=200,
        radius_min=0.03, radius_max=0.05,
        container_type="Box2D",
        container_params={'lx': 1.5, 'ly': 1.0},
        model_name="rigid", material_name="TDURx",
        avatar_type="rigidDisk", color="BLUEx", seed=9,
        group_name="grains_avalanche",
    )
    controller.generate_granulo(config)

    # Élever le tas au-dessus de la pente après génération (translation
    # verticale du groupe, via une opération DOF appliquée à chaque grain).
    for aid in controller.state.avatar_groups["grains_avalanche"]:
        controller.add_dof_operation(DOFOperation(
            operation_type="translate",
            target_type="avatar", target_value=aid,
            parameters={"dx": 0.0, "dy": 1.5},
        ))

    # ── Lois de contact — friction modérée pour un écoulement réaliste ─────
    controller.add_contact_law(ContactLaw(
        name="law01", law_type=ContactLawType.IQS_CLB, friction=0.35
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="BLUEx",
        behavior_name="law01", alert=0.05,
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="GRAYx",
        behavior_name="law01", alert=0.05,
    ))

    controller.state.name = "Exemple - Avalanche sur pente inclinée"