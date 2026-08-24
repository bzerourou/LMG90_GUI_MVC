"""
Exemple avancé : essai de compression biaxiale sur un massif granulaire.

Deux parois verticales (roughWall inclinés à 90° via rotation DOF, même
pattern que le correctif de la trémie — voir ex_hopper_discharge.py)
se rapprochent à vitesse constante pour comprimer un lit de grains,
sur un socle fixe.
"""
import math

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, GranuloGeneration,
    DOFOperation, PostProCommand,
)


def _add_vertical_wall(controller, x, height, thickness, mat_name, mod_name, color):
    """Crée un roughWall vertical (segment de longueur `height`) centré en x."""
    wall = Avatar(
        avatar_type=AvatarType.ROUGH_WALL,
        center=[x, height / 2.0],
        material_name=mat_name, model_name=mod_name, color=color,
        origin=AvatarOrigin.MANUAL,
        wall_params={'l': height, 'r': thickness, 'nb_vertex': 10},
    )
    idx = controller.add_avatar(wall)
    wall_id = controller.state.avatars[idx].avatar_id

    # Rotation ponctuelle de 90° autour du centre propre du mur (horizontal -> vertical)
    controller.add_dof_operation(DOFOperation(
        operation_type="rotate",
        target_type="avatar", target_value=wall_id,
        parameters={
            "description": "axis",
            "center": [x, height / 2.0],
            "axis": [0.0, 0.0, 1.0],
            "alpha": math.pi / 2.0,
        },
    ))
    return idx, wall_id


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2600.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    box_width, box_height, thickness = 2.0, 1.5, 0.03
    half_w = box_width / 2.0

    # ── Socle fixe ────────────────────────────────────────────────────────
    floor = Avatar(
        avatar_type=AvatarType.SMOOTH_WALL,
        center=[0.0, -0.05],
        material_name="TDURx", model_name="rigid", color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        wall_params={'l': box_width + 0.4, 'h': 0.1, 'nb_polyg': 20},
    )
    floor_idx = controller.add_avatar(floor)
    floor_id  = controller.state.avatars[floor_idx].avatar_id
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=floor_id,
        parameters={"component": [1, 2, 3], "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Parois latérales mobiles ─────────────────────────────────────────
    compression_velocity = 0.05   # m/s, vers l'intérieur
    left_idx, left_id = _add_vertical_wall(
        controller, x=-half_w, height=box_height, thickness=thickness,
        mat_name="TDURx", mod_name="rigid", color="ORANx",
    )
    right_idx, right_id = _add_vertical_wall(
        controller, x=half_w, height=box_height, thickness=thickness,
        mat_name="TDURx", mod_name="rigid", color="ORANx",
    )
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=left_id,
        parameters={"component": 1, "dofty": "vlocy", "ct": compression_velocity},
    ))
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=right_id,
        parameters={"component": 1, "dofty": "vlocy", "ct": -compression_velocity},
    ))

    controller.state.avatar_groups["biaxial_frame"] = [
        controller.state.avatars[i].avatar_id for i in (floor_idx, left_idx, right_idx)
    ]

    # ── Lit de grains entre les parois ──────────────────────────────────────
    config = GranuloGeneration(
        nb_particles=150,
        radius_min=0.04, radius_max=0.06,
        container_type="Box2D",
        container_params={'lx': box_width - 0.2, 'ly': box_height - 0.3},
        model_name="rigid", material_name="TDURx",
        avatar_type="rigidDisk", color="BLUEx", seed=8,
        group_name="grains_biaxial",
    )
    controller.generate_granulo(config)

    # ── Lois de contact ────────────────────────────────────────────────────
    controller.add_contact_law(ContactLaw(
        name="law01", law_type=ContactLawType.IQS_CLB, friction=0.4
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="BLUEx",
        behavior_name="law01", alert=0.05,
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="ORANx",
        behavior_name="law01", alert=0.05,
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="GRAYx",
        behavior_name="law01", alert=0.05,
    ))

    controller.add_postpro_command(PostProCommand(name="SOLVER INFORMATIONS", step=10))

    controller.state.name = "Exemple - Compression biaxiale"