"""
Exemple avancé : contact roue/rail (modèle 3D, dimensions ferroviaires réalistes).

Illustre :
  - rigidCylinder (roue) sur rigidPlan (rail) — corps rigides 3D
  - Dimensions normalisées UIC : roue Ø920mm, largeur bandage 135mm,
    champignon de rail 70mm
  - Deux lois de contact distinctes sur le même couple roue/rail :
      * IQS_CLB   — roulement continu (adhérence sèche acier/acier, μ≈0.3)
      * RST_CLB   — impact au passage d'un joint de rail (restitution +
                    frottement dégradé, simule un défaut de voie)
  - DOFOperation : rail et joint totalement immobilisés (6 DDL RBDY3),
    roue guidée latéralement et entraînée en translation longitudinale
    (le roulement proprement dit résulte du contact, pas d'une rotation
    imposée — cohérent avec le comportement physique attendu)
  - Post-traitement : énergie cinétique globale + suivi du couple sur la roue
"""
from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, DOFOperation, PostProCommand,
)
import math


def build(controller) -> None:
    controller.state.dimension = 3

    # ── Matériaux ────────────────────────────────────────────────────────
    # Acier de roue forgée (roue + rail)
    controller.add_material(Material(
        name="acier", material_type=MaterialType.RIGID, density=7850.0
    ))
    # Traverse / ballast (support du rail, densité équivalente béton armé)
    controller.add_material(Material(
        name="balst", material_type=MaterialType.RIGID, density=2400.0
    ))

    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx3D", dimension=3
    ))

    # ── Dimensions ferroviaires réalistes (norme UIC 920) ──────────────────
    wheel_radius   = 0.460   # rayon de roue standard (Ø 920 mm)
    wheel_width    = 0.135   # largeur du bandage de roulement
    rail_length    = 3.0     # longueur de rail modélisée
    rail_head_w    = 0.070   # largeur du champignon de rail (zone de contact)
    rail_thickness = 0.030   # épaisseur équivalente du rail (demi-dim. axe3)

    joint_length   = 0.20    # longueur du tronçon "joint de rail" (défaut)
    joint_drop     = 0.004   # décalage vertical du joint (4 mm, défaut de voie)

    # ── Rail principal : plan rigide fixe (champignon de roulement) ────────
    rail = Avatar(
        avatar_type=AvatarType.RIGID_PLAN,
        center=[0.0, 0.0, 0.0],
        material_name="balst",
        model_name="rigid",
        color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        axis={
            'axe1': rail_length / 2.0,   # demi-longueur (direction de roulement, X)
            'axe2': rail_head_w / 2.0,   # demi-largeur du champignon (Y)
            'axe3': rail_thickness / 2.0,  # demi-épaisseur (Z)
        },
    )
    rail_idx = controller.add_avatar(rail)
    rail_id  = controller.state.avatars[rail_idx].avatar_id

    # Rail totalement immobilisé (3 translations + 3 rotations, RBDY3)
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=rail_id,
        parameters={"component": [1, 2, 3, 4, 5, 6], "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Joint de rail : tronçon avec léger défaut d'alignement ─────────────
    # Positionné plus loin sur la voie ; couleur distincte pour recevoir une
    # loi de contact différente (impact/restitution) au passage de la roue.
    joint_x = rail_length / 2.0 - joint_length  # proche de l'extrémité du rail
    rail_joint = Avatar(
        avatar_type=AvatarType.RIGID_PLAN,
        center=[joint_x, 0.0, -joint_drop],
        material_name="balst",
        model_name="rigid",
        color="ORANx",
        origin=AvatarOrigin.MANUAL,
        axis={
            'axe1': joint_length / 2.0,
            'axe2': rail_head_w / 2.0,
            'axe3': rail_thickness / 2.0,
        },
    )
    joint_idx = controller.add_avatar(rail_joint)
    joint_id  = controller.state.avatars[joint_idx].avatar_id

    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=joint_id,
        parameters={"component": [1, 2, 3, 4, 5, 6], "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Roue : cylindre rigide posé sur le champignon de rail ──────────────
    # Axe du cylindre par défaut selon Z côté LMGC90. La rotation autour de X
    # place donc l'axe de la roue transversalement au rail.
    wheel = Avatar(
        avatar_type=AvatarType.RIGID_CYLINDER,
        center=[-rail_length / 2.0 + 0.3, 0.0, wheel_radius + rail_thickness / 2.0],
        material_name="acier",
        model_name="rigid",
        color="BLUEx",
        origin=AvatarOrigin.MANUAL,
        radius=wheel_radius,
        wall_params={'h': wheel_width},
    )
    wheel_idx = controller.add_avatar(wheel)
    wheel_id  = controller.state.avatars[wheel_idx].avatar_id

    controller.add_dof_operation(DOFOperation(
        operation_type="rotate",
        target_type="avatar", target_value=wheel_id,
        parameters={
            "description": "axis",
            "center": controller.state.avatars[wheel_idx].center,
            "axis": [1.0, 0.0, 0.0],
            "alpha": math.pi / 2.0,
        },
    ))

    # Guidage latéral : bloque tout déplacement transversal (boudin de roue)
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=wheel_id,
        parameters={"component": 2, "dofty": "vlocy", "ct": 0.0},
    ))
    # Entraînement longitudinal à vitesse constante (essai à faible vitesse) ;
    # le roulement lui-même résulte du contact + friction, pas d'une rotation
    # imposée artificiellement.
    rolling_speed = 1.5  # m/s
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=wheel_id,
        parameters={"component": 1, "dofty": "vlocy", "ct": rolling_speed},
    ))

    # ── Lois de contact ──────────────────────────────────────────────────
    # 1) Roulement continu roue/rail — adhérence sèche acier/acier (μ ≈ 0.3,
    #    valeur usuelle pour contact roue/rail non lubrifié).
    controller.add_contact_law(ContactLaw(
        name="law01", law_type=ContactLawType.IQS_CLB, friction=0.3
    ))

    # 2) Passage du joint de rail — frottement dégradé + restitution pour
    #    représenter l'impact au niveau du défaut de voie (rstn/rstt faibles :
    #    choc majoritairement dissipatif).
    controller.add_contact_law(ContactLaw(
        name="law02",
        law_type=ContactLawType.RST_CLB,
        friction=0.2,
        properties={"rstn": 0.3, "rstt": 0.15},
    ))

    # ── Tables de visibilité ────────────────────────────────────────────────
    # Contacteurs 3D : CYLND (roue), PLANx (rail/joint) — cf. visibility_tab.py
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY3", candidate_contactor="CYLND", candidate_color="BLUEx",
        antagonist_body="RBDY3", antagonist_contactor="PLANx", antagonist_color="GRAYx",
        behavior_name="law01", alert=0.005,   # 5 mm — alerte de contact serrée
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY3", candidate_contactor="CYLND", candidate_color="BLUEx",
        antagonist_body="RBDY3", antagonist_contactor="PLANx", antagonist_color="ORANx",
        behavior_name="law02", alert=0.01,    # alerte plus large : défaut de voie
    ))

    # ── Post-traitement ──────────────────────────────────────────────────────
    controller.add_postpro_command(PostProCommand(name="KINETIC ENERGY", step=10))
    controller.add_postpro_command(PostProCommand(
        name="TORQUE EVOLUTION", step=10,
        target_type="avatar", target_value=wheel_id,
    ))
    controller.add_postpro_command(PostProCommand(name="SOLVER INFORMATIONS", step=20))

    controller.state.name = "Exemple - Contact roue/rail (ferroviaire)"