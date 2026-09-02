"""
Exemple avancé : trémie (hopper) construite à partir de roughWall inclinés,
recevant un dépôt granulométrique.

Note : la première version de cet exemple utilisait
AvatarFactory.create_hopper_2d() (core/avatar_factory.py), qui génère un
rigidPolygon dont pylmgc90 rejette les propriétés rigides au calcul
(Exception dans computeRigidProperties — probable incohérence entre le
paramètre radius et les vertices réels de cette méthode). Plutôt que de
patcher une méthode existante que je ne peux pas déboguer facilement sans
pylmgc90 en local, la trémie est reconstruite ici avec deux roughWall
inclinés via une rotation DOF — pattern déjà validé et utilisé dans
particle_factory.py::PreCodeGenerator._write_container_2d pour les parois
de conteneur.
"""
import math

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, GranuloGeneration,
    PostProCommand, DOFOperation,
)


def _add_inclined_wall(controller, bottom, top, thickness, mat_name, mod_name, color):
    """
    Crée un roughWall reliant les points bottom -> top, via un roughWall
    horizontal (longueur = distance bottom-top) centré au milieu, puis
    tourné de l'angle nécessaire autour de son propre centre.
    """
    dx = top[0] - bottom[0]
    dy = top[1] - bottom[1]
    length = math.hypot(dx, dy)
    angle  = math.atan2(dy, dx)   # angle par rapport à l'axe X (orientation par défaut du mur)
    cx = (bottom[0] + top[0]) / 2.0
    cy = (bottom[1] + top[1]) / 2.0

    wall = Avatar(
        avatar_type=AvatarType.ROUGH_WALL,
        center=[cx, cy],
        material_name=mat_name,
        model_name=mod_name,
        color=color,
        origin=AvatarOrigin.MANUAL,
        wall_params={'l': length, 'r': thickness, 'nb_vertex': 10},
    )
    idx = controller.add_avatar(wall)
    wall_id = controller.state.avatars[idx].avatar_id

    # Rotation autour du CENTRE PROPRE du mur (pattern identique à
    # masonery_wizard.py et particle_factory.py pour les parois inclinées)
    controller.add_dof_operation(DOFOperation(
        operation_type="rotate",
        target_type="avatar",
        target_value=wall_id,
        parameters={
            "description": "axis",
            "center": [cx, cy],
            "alpha": angle,
        },
    ))
    return idx


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2600.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Géométrie de la trémie en V ──────────────────────────────────────
    # IMPORTANT : pylmgc90.depositInBox2D place le dépôt dans le repère
    # [0, lx] x [0, ly], donc la trémie doit être construite dans ce système,
    # et non centrée sur x=0 comme si la zone de dépôt était libre.
    box_lx, box_ly = 2.0, 1.6
    top_width, bottom_width, height = 1.6, 0.45, 1.2
    half_top, half_bot = top_width / 2.0, bottom_width / 2.0
    thickness = 0.03
    # Petit décalage des deux pieds de paroi pour éviter que les JONCx
    # du bas soient exactement alignés sur la même ligne centrale.
    bottom_offset = thickness * 0.75
    x_center = box_lx / 2.0
    left_bottom = [x_center - (half_bot + bottom_offset), 0.0]
    left_top = [x_center - half_top, height]
    right_bottom = [x_center + (half_bot + bottom_offset), 0.0]
    right_top = [x_center + half_top, height]

    hopper_indices = []
    # Paroi gauche : de la base au niveau du sol vers le haut, dans le cadre [0, box_lx]
    hopper_indices.append(_add_inclined_wall(
        controller,
        bottom=left_bottom, top=left_top,
        thickness=thickness, mat_name="TDURx", mod_name="rigid", color="GRAYx",
    ))
    # Paroi droite : symétrique
    hopper_indices.append(_add_inclined_wall(
        controller,
        bottom=right_bottom, top=right_top,
        thickness=thickness, mat_name="TDURx", mod_name="rigid", color="GRAYx",
    ))

    hopper_ids = [controller.state.avatars[i].avatar_id for i in hopper_indices]
    controller.state.avatar_groups["hopper_walls"] = hopper_ids

    # ── Immobiliser complètement les deux parois (translation + rotation) ──
    # Nécessaire car la rotation ci-dessus est une transformation ponctuelle
    # (pas un blocage) — sans ce blocage, les parois retomberaient sous
    # gravité au calcul, comme n'importe quel autre corps rigide.
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="group",
        target_value="hopper_walls",
        parameters={"component": [1, 2, 3], "dofty": "vlocy"},
    ))

    # les décalés en bas 
    controller.add_dof_operation(DOFOperation(
        operation_type="translate",
        target_type="group",
        target_value="hopper_walls",
        parameters={"dx":0.0, "dy": -box_lx}

    ))

    # ── Dépôt granulométrique au-dessus de la trémie ────────────────────────
    config = GranuloGeneration(
        nb_particles=180,
        radius_min=0.04,
        radius_max=0.07,
        container_type="Box2D",
        container_params={'lx': box_lx, 'ly': box_ly},
        model_name="rigid",
        material_name="TDURx",
        avatar_type="rigidDisk",
        color="BLUEx",
        seed=17,
        group_name="grains_tremie",
    )
    controller.generate_granulo(config)

    # ── Lois de contact ────────────────────────────────────────────────────
    controller.add_contact_law(ContactLaw(
        name="grain", law_type=ContactLawType.IQS_CLB, friction=0.4
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="BLUEx",
        behavior_name="grain", alert=0.05,
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="GRAYx",
        behavior_name="grain", alert=0.05,
    ))

    # ── Post-traitement : suivi de l'énergie cinétique globale ─────────────
    controller.add_postpro_command(PostProCommand(name="KINETIC ENERGY", step=20))

    controller.state.name = "Exemple - Décharge en trémie"