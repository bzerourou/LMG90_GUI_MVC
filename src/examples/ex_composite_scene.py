"""
Exemple de synthèse — scène composite mélangeant tous les mécanismes.

Objectif pédagogique : montrer dans UN seul projet la diversité complète
du système, plutôt que des exemples isolés par mécanisme :

  Avatars       : rigidDisk, rigidJonc, rigidPolygon (full), rigidCluster,
                  smoothWall/roughWall (inclinés), emptyAvatar (briques
                  via brick2D), rigidSphere (extension future 3D — non
                  utilisée ici car dimension=2 pour rester cohérent)
  Matériaux     : 3 matériaux RIGID de densités différentes
  Lois          : IQS_CLB (frottement pur), RST_CLB (restitution),
                  IQS_MOHR_DS_CLB (cohésion + frottement, pour le mur)
  Visibilité    : tables croisées par PAIRE DE COULEURS (pas juste
                  même-couleur/même-couleur), pour illustrer un vrai
                  système multi-matériaux où chaque paire a sa propre loi
  Variables     : state.dynamic_vars — dimensions du site, épaisseur des
                  joints, hauteur de chute, facteur d'espacement — TOUTES
                  réutilisées dans la construction de la scène ci-dessous,
                  et laissées dans le projet pour que l'utilisateur les
                  retrouve dans Outils > Variables dynamiques après
                  chargement de l'exemple.

Comme pour les exemples précédents : parois horizontales/inclinées créées
via roughWall + rotation DOF (pattern déjà validé, évite le bug connu de
AvatarFactory.create_hopper_2d).
"""
import math

from pylmgc90 import pre

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, DOFOperation,
    PostProCommand,
)
from ..utils.safe_eval import SafeEvaluator, build_eval_context


def _eval_var(controller, expr: str):
    """Évalue une expression dans le contexte projet courant (variables déjà définies incluses)."""
    ev = SafeEvaluator(allowed_names=build_eval_context(controller))
    return ev.eval_expression(expr)


def _add_inclined_wall(controller, bottom, top, thickness, mat_name, mod_name, color):
    """Mur incliné via roughWall + rotation DOF (pattern validé, cf. ex_hopper_discharge.py)."""
    dx, dy = top[0] - bottom[0], top[1] - bottom[1]
    length = math.hypot(dx, dy)
    angle  = math.atan2(dy, dx)
    cx, cy = (bottom[0] + top[0]) / 2.0, (bottom[1] + top[1]) / 2.0

    wall = Avatar(
        avatar_type=AvatarType.ROUGH_WALL,
        center=[cx, cy],
        material_name=mat_name, model_name=mod_name, color=color,
        origin=AvatarOrigin.MANUAL,
        wall_params={'l': length, 'r': thickness, 'nb_vertex': 10},
    )
    idx = controller.add_avatar(wall)
    wid = controller.state.avatars[idx].avatar_id
    controller.add_dof_operation(DOFOperation(
        operation_type="rotate", target_type="avatar", target_value=wid,
        parameters={"description": "axis", "center": [cx, cy],
                    "axis": [0.0, 0.0, 1.0], "alpha": angle},
    ))
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof", target_type="avatar", target_value=wid,
        parameters={"component": [1, 2, 3], "dofty": "vlocy", "ct": 0.0},
    ))
    return idx, wid


def build(controller) -> None:
    controller.state.dimension = 2

    # =========================================================================
    # 1. VARIABLES DYNAMIQUES — définies AVANT tout le reste
    # =========================================================================
    # Chaque valeur est une expression Python (str), évaluée via
    # SafeEvaluator — exactement le mécanisme utilisé par
    # DynamicVarsDialog et les champs eval_float()/eval_list() des onglets.
    controller.state.dynamic_vars = {
        "site_width":        "6.0",
        "site_height":       "5.0",
        "joint_thickness":   "0.012",
        "brick_lx":          "0.22",
        "brick_ly":          "0.07",
        "drop_height":       "site_height * 0.7",          # dépend d'une autre variable
        "spacing_factor":    "2.4",
        "disk_radius":       "0.11",
        "disk_spacing":      "disk_radius * spacing_factor",  # dépend de 2 variables
        "cluster_radius":    "0.09",
        "wall_thickness":    "0.03",
    }

    # Récupération des valeurs évaluées — comme le ferait un formulaire UI
    # via self.eval_float(field.text(), ...) en tapant le nom de variable.
    site_width      = _eval_var(controller, "site_width")
    joint_thickness = _eval_var(controller, "joint_thickness")
    brick_lx        = _eval_var(controller, "brick_lx")
    brick_ly        = _eval_var(controller, "brick_ly")
    drop_height     = _eval_var(controller, "drop_height")
    disk_radius     = _eval_var(controller, "disk_radius")
    disk_spacing    = _eval_var(controller, "disk_spacing")
    cluster_radius  = _eval_var(controller, "cluster_radius")
    wall_thickness  = _eval_var(controller, "wall_thickness")

    # =========================================================================
    # 2. MATÉRIAUX (3 densités différentes)
    # =========================================================================
    controller.add_material(Material(
        name="brick", material_type=MaterialType.RIGID, density=1800.0
    ))
    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2500.0
    ))
    controller.add_material(Material(
        name="steel", material_type=MaterialType.RIGID, density=7800.0
    ))

    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    mat_brick_obj = controller._pylmgc_materials["brick"]
    mod_rigid_obj = controller._pylmgc_models["rigid"]

    # =========================================================================
    # 3. STRUCTURE FIXE — socle + mur de briques (cohésif) + rampe inclinée
    # =========================================================================
    floor = Avatar(
        avatar_type=AvatarType.SMOOTH_WALL,
        center=[site_width / 2.0, -0.05],
        material_name="TDURx", model_name="rigid", color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        wall_params={'l': site_width + 1.0, 'h': 0.1, 'nb_polyg': 30},
    )
    floor_idx = controller.add_avatar(floor)
    floor_id  = controller.state.avatars[floor_idx].avatar_id
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof", target_type="avatar", target_value=floor_id,
        parameters={"component": [1, 2, 3], "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Mur de briques (Stack Bond) contre le bord gauche, avatars via
    # emptyAvatar + brick2D — utilise brick_lx/brick_ly/joint_thickness ────
    nb_rows, nb_cols = 4, 3
    brick_indices = []
    for row in range(nb_rows):
        for col in range(nb_cols):
            cx = 0.3 + col * (brick_lx + joint_thickness) + brick_lx / 2.0
            cy = row * (brick_ly + joint_thickness) + brick_ly / 2.0
            brick = pre.brick2D("std", brick_lx, brick_ly)
            body = brick.rigidBrick(
                center=[cx, cy], model=mod_rigid_obj, material=mat_brick_obj, color="ORANx"
            )
            controller._bodies_container.addAvatar(body)
            controller._pylmgc_bodies.append(body)
            av = Avatar(
                avatar_type=AvatarType.EMPTY_AVATAR,
                center=[cx, cy],
                material_name="brick", model_name="rigid", color="ORANx",
                origin=AvatarOrigin.MANUAL,
                wall_params={'l': brick_lx, 'h': brick_ly, 'brick_name': 'std'},
                contactors=[],
            )
            controller.state.avatars.append(av)
            brick_indices.append(len(controller.state.avatars) - 1)

    brick_ids = [controller.state.avatars[i].avatar_id for i in brick_indices]
    controller.state.avatar_groups["mur_briques"] = brick_ids
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof", target_type="group", target_value="mur_briques",
        parameters={"component": [1, 2, 3], "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Rampe inclinée contre le bord droit (roughWall + rotation) ─────────
    ramp_idx, ramp_id = _add_inclined_wall(
        controller,
        bottom=[site_width - 1.0, 0.0], top=[site_width, 2.0],
        thickness=wall_thickness, mat_name="TDURx", mod_name="rigid", color="GRAYx",
    )

    # =========================================================================
    # 4. AVATARS MOBILES — disques, joncs, polygone, cluster
    # =========================================================================
    mobile_groups = {}

    # ── Ligne de disques (rigidDisk), espacement dérivé de disk_spacing ────
    disk_indices = []
    nb_disks = 6
    for i in range(nb_disks):
        d = Avatar(
            avatar_type=AvatarType.RIGID_DISK,
            center=[1.0 + i * disk_spacing, drop_height],
            material_name="TDURx", model_name="rigid", color="BLUEx",
            origin=AvatarOrigin.MANUAL,
            radius=disk_radius,
        )
        idx = controller.add_avatar(d)
        disk_indices.append(idx)
    disk_ids = [controller.state.avatars[i].avatar_id for i in disk_indices]
    controller.state.avatar_groups["disques"] = disk_ids
    mobile_groups["disques"] = disk_ids

    # ── Jonc (barre allongée) tombant en diagonale ──────────────────────────
    jonc = Avatar(
        avatar_type=AvatarType.RIGID_JONC,
        center=[site_width / 2.0, drop_height + 0.8],
        material_name="TDURx", model_name="rigid", color="VERTx",
        origin=AvatarOrigin.MANUAL,
        axis={'axe1': 0.5, 'axe2': 0.06},
    )
    jonc_idx = controller.add_avatar(jonc)
    jonc_id  = controller.state.avatars[jonc_idx].avatar_id
    controller.state.avatar_groups["joncs"] = [jonc_id]

    # ── Polygone personnalisé (losange, sommets explicites) ────────────────
    # Ensure vertices are counter-clockwise (pylmgc90 requires CCW orientation)
    diamond_vertices = [[-0.1, 0.0], [0.0, -0.15], [0.1, 0.0], [0.0, 0.15]]
    diamond = Avatar(
        avatar_type=AvatarType.RIGID_POLYGON,
        center=[site_width / 2.0 - 0.6, drop_height + 0.5],
        material_name="steel", model_name="rigid", color="MAGEx",
        origin=AvatarOrigin.MANUAL,
        generation_type="full",
        vertices=diamond_vertices,
        radius=0.15,
    )
    diamond_idx = controller.add_avatar(diamond)
    diamond_id  = controller.state.avatars[diamond_idx].avatar_id
    controller.state.avatar_groups["polygones"] = [diamond_id]

    # ── Cluster (3 disques élémentaires) ────────────────────────────────────
    cluster = Avatar(
        avatar_type=AvatarType.RIGID_CLUSTER,
        center=[site_width / 2.0 + 0.6, drop_height + 0.5],
        material_name="steel", model_name="rigid", color="CYANx",
        origin=AvatarOrigin.MANUAL,
        radius=cluster_radius,
        nb_vertices=3,
    )
    cluster_idx = controller.add_avatar(cluster)
    cluster_id  = controller.state.avatars[cluster_idx].avatar_id
    controller.state.avatar_groups["clusters"] = [cluster_id]

    # =========================================================================
    # 5. LOIS DE CONTACT — 3 lois distinctes selon la nature du contact
    # =========================================================================
    # a) Frottement pur, pour tous les mobiles entre eux
    controller.add_contact_law(ContactLaw(
        name="law01", law_type=ContactLawType.IQS_CLB, friction=0.4
    ))
    # b) Restitution (rebond), pour l'acier (polygone/cluster) contre le sol
    controller.add_contact_law(ContactLaw(
        name="law02", law_type=ContactLawType.RST_CLB, friction=0.25,
        properties={"rstn": 0.5, "rstt": 0.2},
    ))
    # c) Cohésion + frottement, pour l'interface entre briques du mur
    controller.add_contact_law(ContactLaw(
        name="law03", law_type=ContactLawType.IQS_MOHR_DS_CLB,
        friction=0.6, properties={"stfr": 1e8, "dyfr": 1e8, "cohn": 5e4, "coht": 3e4},
    ))

    # =========================================================================
    # 6. TABLES DE VISIBILITÉ — croisées par PAIRE DE COULEURS
    # =========================================================================
    # a) Interface briques (mur cohésif) — bricks are rigid: use CLxxx contactor
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="POLYG", candidate_color="ORANx",
        antagonist_body="RBDY2", antagonist_contactor="POLYG", antagonist_color="ORANx",
        behavior_name="law03", alert=0.02,
    ))

    # b) Disques entre eux
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="BLUEx",
        behavior_name="law01", alert=0.05,
    ))
    # c) Disques / sol
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="GRAYx",
        behavior_name="law01", alert=0.05,
    ))
    # d) Disques / mur de briques
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="POLYG", antagonist_color="ORANx",
        behavior_name="law01", alert=0.05,
    ))
    # e) Jonc / sol et jonc / disques
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="VERTx",
        behavior_name="law01", alert=0.05,
    ))
    # f) Polygone (acier) / sol — loi de restitution
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="POLYG", candidate_color="MAGEx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="GRAYx",
        behavior_name="law02", alert=0.05,
    ))
    # g) Cluster (acier) / sol — loi de restitution
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="CYANx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="GRAYx",
        behavior_name="law02", alert=0.05,
    ))
    # h) Polygone / cluster (acier / acier — frottement pur, pas de rebond)
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="POLYG", candidate_color="MAGEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="CYANx",
        behavior_name="law01", alert=0.05,
    ))
    # i) Rampe inclinée / disques et / polygone
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="GRAYx",
        behavior_name="law01", alert=0.05,
    ))

    # =========================================================================
    # 7. POST-TRAITEMENT
    # =========================================================================
    controller.add_postpro_command(PostProCommand(name="KINETIC ENERGY", step=20))
    controller.add_postpro_command(PostProCommand(name="COORDINATION NUMBER", step=20))
    controller.add_postpro_command(PostProCommand(name="DISSIPATED ENERGY", step=20))

    controller.state.name = "Exemple - Scène composite (tous mécanismes + variables)"