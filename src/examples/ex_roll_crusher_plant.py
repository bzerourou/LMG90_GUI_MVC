"""
Exemple « de ouf » — Usine de broyage à cylindres (double-roll crusher).

Scène industrielle 2D complète qui enchaîne plusieurs mécanismes avancés
de LMGC90_GUI dans un seul projet :

  1. Variables dynamiques  — toute la géométrie pilotée par dynamic_vars
  2. Trémie d'alimentation — 2 roughWall inclinés + DOF groupe (fixe)
  3. Deux cylindres acier  — rigidDisk entraînés en rotation opposée
  4. Guides latéraux + sol — smoothWall / roughWall immobilisés
  5. Charge granulaire     — granulo_Random + depositInBox2D (200 grains)
  6. 3 matériaux           — rock / steel / concrete (densités distinctes)
  7. 3 lois de contact     — grain↔grain, grain↔acier (broyage), grain↔béton
  8. Visibilité croisée    — par paires de couleurs
  9. Post-pro              — énergie cinétique, dissipée, couple sur les rouleaux

Physique illustrée :
  Les grains tombent de la trémie dans l'entrefer des deux cylindres
  contrarotatifs. Le frottement élevé grain/acier (μ ≈ 0.55) les entraîne
  et les « broie » (fortes forces de contact). Le débit sort en bas.

C'est l'exemple vitrine pour démontrer la puissance de l'API publique
du contrôleur (matériaux, avatars, granulo, DOF, lois, post-pro, variables).
"""
from __future__ import annotations

import math

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, GranuloGeneration,
    DOFOperation, PostProCommand,
)
from ..utils.safe_eval import SafeEvaluator, build_eval_context


def _eval(controller, expr: str):
    """Évalue une expression dans le contexte des dynamic_vars du projet."""
    ev = SafeEvaluator(allowed_names=build_eval_context(controller))
    return float(ev.eval_expression(expr))


def _add_inclined_wall(controller, bottom, top, thickness, mat_name, mod_name, color):
    """roughWall horizontal + rotation DOF (pattern validé hopper / composite)."""
    dx, dy = top[0] - bottom[0], top[1] - bottom[1]
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    cx, cy = (bottom[0] + top[0]) / 2.0, (bottom[1] + top[1]) / 2.0

    wall = Avatar(
        avatar_type=AvatarType.ROUGH_WALL,
        center=[cx, cy],
        material_name=mat_name,
        model_name=mod_name,
        color=color,
        origin=AvatarOrigin.MANUAL,
        wall_params={"l": length, "r": thickness, "nb_vertex": 12},
    )
    idx = controller.add_avatar(wall)
    wid = controller.state.avatars[idx].avatar_id
    controller.add_dof_operation(DOFOperation(
        operation_type="rotate",
        target_type="avatar",
        target_value=wid,
        parameters={
            "description": "axis",
            "center": [cx, cy],
            "axis": [0.0, 0.0, 1.0],
            "alpha": angle,
        },
    ))
    return idx, wid


def build(controller) -> None:
    controller.state.dimension = 2

    # =========================================================================
    # 1. VARIABLES DYNAMIQUES — géométrie pilotée
    # =========================================================================
    controller.state.dynamic_vars = {
        # Zone de dépôt granulométrique (repère depositInBox2D : [0,lx]×[0,ly])
        "box_lx": "3.2",
        "box_ly": "2.4",
        # Trémie
        "hopper_top_w": "2.4",
        "hopper_bot_w": "0.55",
        "hopper_h": "1.4",
        "wall_t": "0.04",
        # Cylindres de broyage
        "roll_r": "0.35",
        "roll_gap": "0.12",          # entrefer (doit rester > 2*radius_max grains)
        "roll_omega": "2.5",         # rad/s (≈ 24 tr/min)
        "roll_y": "0.55",            # hauteur des axes au-dessus du sol
        # Charge
        "n_grains": "220",
        "r_min": "0.035",
        "r_max": "0.055",
        # Dérivées
        "x_center": "box_lx / 2.0",
        "half_top": "hopper_top_w / 2.0",
        "half_bot": "hopper_bot_w / 2.0",
        "roll_dx": "roll_r + roll_gap / 2.0",
    }

    box_lx = _eval(controller, "box_lx")
    box_ly = _eval(controller, "box_ly")
    hopper_h = _eval(controller, "hopper_h")
    wall_t = _eval(controller, "wall_t")
    roll_r = _eval(controller, "roll_r")
    roll_omega = _eval(controller, "roll_omega")
    roll_y = _eval(controller, "roll_y")
    n_grains = int(_eval(controller, "n_grains"))
    r_min = _eval(controller, "r_min")
    r_max = _eval(controller, "r_max")
    x_center = _eval(controller, "x_center")
    half_top = _eval(controller, "half_top")
    half_bot = _eval(controller, "half_bot")
    roll_dx = _eval(controller, "roll_dx")

    # =========================================================================
    # 2. MATÉRIAUX & MODÈLE
    # =========================================================================
    controller.add_material(Material(
        name="rockx", material_type=MaterialType.RIGID, density=2700.0,
    ))
    controller.add_material(Material(
        name="steel", material_type=MaterialType.RIGID, density=7800.0,
    ))
    controller.add_material(Material(
        name="conct", material_type=MaterialType.RIGID, density=2400.0,
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2,
    ))

    # =========================================================================
    # 3. STRUCTURE FIXE — sol, guides, trémie
    # =========================================================================
    fixed_ids: list[str] = []

    # Sol collecteur (sous les cylindres)
    floor = Avatar(
        avatar_type=AvatarType.SMOOTH_WALL,
        center=[x_center, -0.08],
        material_name="conct",
        model_name="rigid",
        color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        wall_params={"l": box_lx + 0.6, "h": 0.12, "nb_polyg": 40},
    )
    fi = controller.add_avatar(floor)
    fixed_ids.append(controller.state.avatars[fi].avatar_id)

    # Guides latéraux (évite que les grains s'échappent sur les côtés)
    for sign, color in ((-1, "GRAYx"), (1, "GRAYx")):
        gx = x_center + sign * (box_lx / 2.0 + 0.05)
        guide = Avatar(
            avatar_type=AvatarType.ROUGH_WALL,
            center=[gx, hopper_h / 2.0],
            material_name="conct",
            model_name="rigid",
            color=color,
            origin=AvatarOrigin.MANUAL,
            wall_params={"l": hopper_h + 0.4, "r": wall_t, "nb_vertex": 10},
        )
        gi = controller.add_avatar(guide)
        gid = controller.state.avatars[gi].avatar_id
        fixed_ids.append(gid)
        # Orientation verticale (π/2)
        controller.add_dof_operation(DOFOperation(
            operation_type="rotate",
            target_type="avatar",
            target_value=gid,
            parameters={
                "description": "axis",
                "center": [gx, hopper_h / 2.0],
                "axis": [0.0, 0.0, 1.0],
                "alpha": math.pi / 2.0,
            },
        ))

    # Trémie en V (parois inclinées)
    bottom_offset = wall_t * 0.8
    left_bottom = [x_center - (half_bot + bottom_offset), roll_y + roll_r + 0.15]
    left_top = [x_center - half_top, left_bottom[1] + hopper_h]
    right_bottom = [x_center + (half_bot + bottom_offset), roll_y + roll_r + 0.15]
    right_top = [x_center + half_top, right_bottom[1] + hopper_h]

    hopper_ids: list[str] = []
    for bottom, top in ((left_bottom, left_top), (right_bottom, right_top)):
        _, wid = _add_inclined_wall(
            controller, bottom, top, wall_t, "conct", "rigid", "ORANx",
        )
        hopper_ids.append(wid)
        fixed_ids.append(wid)

    controller.state.avatar_groups["hopper_walls"] = list(hopper_ids)
    controller.state.avatar_groups["structure_fixe"] = list(fixed_ids)

    # Immobiliser toute la structure (translation + rotation)
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="group",
        target_value="structure_fixe",
        parameters={"component": [1, 2, 3], "dofty": "vlocy", "ct": 0.0},
    ))

    # =========================================================================
    # 4.a CYLINDRES DE BROYAGE — contrarotatifs
    # =========================================================================
    roll_ids: list[str] = []
    # Gauche : rotation horaire (−ω) ; droite : anti-horaire (+ω)
    # → les faces internes entraînent les grains vers le bas
    for sign, omega, color in (
        (-1.0, -roll_omega, "REEDx"),
        (+1.0, +roll_omega, "REEDx"),
    ):
        rx = x_center + sign * roll_dx
        roll = Avatar(
            avatar_type=AvatarType.RIGID_DISK,
            center=[rx, roll_y],
            material_name="steel",
            model_name="rigid",
            color=color,
            origin=AvatarOrigin.MANUAL,
            radius=roll_r,
            is_hollow=False,
        )
        ri = controller.add_avatar(roll)
        rid = controller.state.avatars[ri].avatar_id
        roll_ids.append(rid)

        # Centre fixe
        controller.add_dof_operation(DOFOperation(
            operation_type="imposeDrivenDof",
            target_type="avatar",
            target_value=rid,
            parameters={"component": [1, 2], "dofty": "vlocy", "ct": 0.0},
        ))
        # Rotation entraînée
        controller.add_dof_operation(DOFOperation(
            operation_type="imposeDrivenDof",
            target_type="avatar",
            target_value=rid,
            parameters={"component": 3, "dofty": "vlocy", "ct": omega},
        ))

    controller.state.avatar_groups["broyeurs"] = list(roll_ids)

    # =========================================================================
    # 4b. DÉCALAGE GLOBAL — depositInBox2D est ancré en (0,0)
    # =========================================================================
    # La génération granulométrique remplit toujours [0, lx] × [0, ly].
    # On abaisse donc toute la structure (trémie, guides, sol, cylindres)
    # sous cette zone, comme dans ex_hopper_discharge (translate dy négatif).
    # Les grains tombent ensuite de la boîte dans la trémie / l'entrefer.
    plant_dy = -1.1*box_ly
    for group_name in ("structure_fixe", "broyeurs"):
        controller.add_dof_operation(DOFOperation(
            operation_type="translate",
            target_type="group",
            target_value=group_name,
            parameters={"dx": 0.0, "dy": plant_dy},
        ))

    # =========================================================================
    # 5. CHARGE GRANULAIRE — dépôt dans la zone haute (Box2D)
    # =========================================================================
    # depositInBox2D place dans [0, lx] × [0, ly]. La trémie est construite
    # dans ce repère : les grains se forment au-dessus des cylindres.
    config = GranuloGeneration(
        nb_particles=n_grains,
        radius_min=r_min,
        radius_max=r_max,
        container_type="Box2D",
        container_params={"lx": box_lx, "ly": box_ly},
        model_name="rigid",
        material_name="rockx",
        avatar_type="rigidDisk",
        color="BLUEx",
        seed=42,
        group_name="charge_rocher",
    )
    controller.generate_granulo(config)

    # =========================================================================
    # 6. LOIS DE CONTACT
    # =========================================================================
    # a) Grain ↔ grain (rocher)
    controller.add_contact_law(ContactLaw(
        name="law01",
        law_type=ContactLawType.IQS_CLB,
        friction=0.40,
    ))
    # b) Grain ↔ acier (broyage — fort frottement pour entraîner)
    controller.add_contact_law(ContactLaw(
        name="law02",
        law_type=ContactLawType.IQS_CLB,
        friction=0.55,
    ))
    # c) Grain ↔ béton (trémie / sol — frottement modéré)
    controller.add_contact_law(ContactLaw(
        name="law03",
        law_type=ContactLawType.IQS_CLB,
        friction=0.35,
    ))

    # =========================================================================
    # 7. TABLES DE VISIBILITÉ (par paires de couleurs)
    # =========================================================================
    # Grains entre eux
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="BLUEx",
        behavior_name="law01", alert=0.04,
    ))
    # Grains / cylindres acier
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="REEDx",
        behavior_name="law02", alert=0.04,
    ))
    # Grains / structure béton (sol GRAYx + trémie ORANx)
    for ant_color in ("GRAYx", "ORANx"):
        controller.add_visibility_rule(VisibilityRule(
            candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
            antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color=ant_color,
            behavior_name="law03", alert=0.04,
        ))

    # =========================================================================
    # 8. POST-TRAITEMENT
    # =========================================================================
    controller.add_postpro_command(PostProCommand(name="KINETIC ENERGY", step=25))
    controller.add_postpro_command(PostProCommand(name="DISSIPATED ENERGY", step=25))
    controller.add_postpro_command(PostProCommand(name="COORDINATION NUMBER", step=25))
    # Couple résistant sur chaque cylindre (utile pour estimer la puissance)
    for rid in roll_ids:
        controller.add_postpro_command(PostProCommand(
            name="TORQUE EVOLUTION",
            step=10,
            target_type="avatar",
            target_value=rid,
        ))

    controller.state.name = (
        "Exemple - Usine de broyage à cylindres "
        "(trémie + double-roll + granulo + multi-lois)"
    )
