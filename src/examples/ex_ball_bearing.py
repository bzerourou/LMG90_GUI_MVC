"""
Exemple avancé : roulement à billes (coupe transversale 2D, type 608).

Modèle simplifié en coupe (les vraies billes sont sphériques et réparties
sur une piste torique 3D — ici on représente une coupe 2D du roulement,
cohérente avec le fait que LMGC90_GUI ne supporte que des disques creux
2D via is_hollow=True, cf. ex_rotating_drum.py pour le même mécanisme).

Illustre :
  - Bague extérieure : rigidDisk creux (is_hollow=True, contacteur xKSID)
    totalement immobilisée — piste de roulement extérieure fixe
  - Bague intérieure : rigidDisk plein, entraînée en rotation pure
    (translation bloquée, seule la rotation est pilotée) — représente
    l'arbre / axe du roulement
  - Billes : disques rigides libres (aucun DOF imposé), placées en
    couronne exactement dans l'entrefer bague int./bague ext. ; leur
    mouvement résulte uniquement du contact et du frottement, pas d'une
    contrainte artificielle — c'est le frottement de roulement qui les
    entraîne, comme dans la réalité
  - Deux lois de contact distinctes : bille/bague (roulement lubrifié,
    frottement très faible) — la cage de maintien n'est pas modélisée
  - Dimensions approximatives d'un roulement rainuré à billes 608
    (Ø extérieur 22 mm, alésage 8 mm, 7 billes) — modèle pédagogique,
    non dimensionné pour un calcul d'ingénierie réel
"""
import math

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, DOFOperation, PostProCommand,
)


def build(controller) -> None:
    controller.state.dimension = 2

    # ── Matériau : acier à roulement (100Cr6 / 52100), même pour bagues et billes ─
    controller.add_material(Material(
        name="acier", material_type=MaterialType.RIGID, density=7850.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Dimensions approximatives (roulement 608 : Ø ext. 22 mm, alésage 8 mm) ──
    outer_race_inner_radius = 0.0095   # piste de roulement extérieure (~9.5 mm)
    inner_race_outer_radius = 0.0050   # piste de roulement intérieure (~5.0 mm)
    # Rayon de bille calé exactement dans l'entrefer, pour un contact initial net
    ball_radius   = (outer_race_inner_radius - inner_race_outer_radius) / 2.0
    pitch_radius  = inner_race_outer_radius + ball_radius   # cercle primitif
    nb_balls      = 7   # nombre de billes typique d'un roulement 608

    center = [0.0, 0.0]

    # ── Bague extérieure : disque creux fixe (piste de roulement) ────────────
    outer_race = Avatar(
        avatar_type=AvatarType.RIGID_DISK,
        center=list(center),
        material_name="acier",
        model_name="rigid",
        color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        radius=outer_race_inner_radius,
        is_hollow=True,
    )
    outer_idx = controller.add_avatar(outer_race)
    outer_id  = controller.state.avatars[outer_idx].avatar_id

    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=outer_id,
        parameters={"component": [1, 2, 3], "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Bague intérieure : disque plein, entraîné en rotation pure ──────────
    inner_race = Avatar(
        avatar_type=AvatarType.RIGID_DISK,
        center=list(center),
        material_name="acier",
        model_name="rigid",
        color="ORANx",
        origin=AvatarOrigin.MANUAL,
        radius=inner_race_outer_radius,
    )
    inner_idx = controller.add_avatar(inner_race)
    inner_id  = controller.state.avatars[inner_idx].avatar_id

    # Translation bloquée (l'arbre reste centré) ; rotation entraînée à
    # vitesse constante — ~300 tr/min, régime de croisière typique d'une
    # roue de skateboard/patin équipée de ce type de roulement.
    inner_rpm   = 300.0
    inner_omega = inner_rpm * 2.0 * math.pi / 60.0
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=inner_id,
        parameters={"component": [1, 2], "dofty": "vlocy", "ct": 0.0},
    ))
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=inner_id,
        parameters={"component": 3, "dofty": "vlocy", "ct": inner_omega},
    ))

    # ── Billes : couronne libre dans l'entrefer, aucun DOF imposé ────────────
    ball_indices = []
    for k in range(nb_balls):
        angle = 2.0 * math.pi * k / nb_balls
        bx = center[0] + pitch_radius * math.cos(angle)
        by = center[1] + pitch_radius * math.sin(angle)
        ball = Avatar(
            avatar_type=AvatarType.RIGID_DISK,
            center=[bx, by],
            material_name="acier",
            model_name="rigid",
            color="BLUEx",
            origin=AvatarOrigin.MANUAL,
            radius=ball_radius,
        )
        idx = controller.add_avatar(ball)
        ball_indices.append(idx)

    ball_ids = [controller.state.avatars[i].avatar_id for i in ball_indices]
    controller.state.avatar_groups["billes"] = ball_ids

    # ── Loi de contact bille/bague — roulement lubrifié, frottement faible ──
    # μ ≈ 0.05 : valeur simplifiée pour un contact rigide/rigide représentant
    # un roulement gras standard (le frottement de roulement réel est bien
    # plus faible et physiquement différent d'un frottement de glissement —
    # cette loi reste une approximation pédagogique du contact bille/piste).
    controller.add_contact_law(ContactLaw(
        name="law01", law_type=ContactLawType.IQS_CLB, friction=0.05
    ))

    # Bague intérieure (DISKx) / billes (DISKx)
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="ORANx",
        behavior_name="law01", alert=0.0005,
    ))
    # Bague extérieure (xKSID, disque creux) / billes (DISKx)
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="BLUEx",
        antagonist_body="RBDY2", antagonist_contactor="xKSID", antagonist_color="GRAYx",
        behavior_name="law01", alert=0.0005,
    ))

    # ── Post-traitement ──────────────────────────────────────────────────────
    controller.add_postpro_command(PostProCommand(name="KINETIC ENERGY", step=5))
    controller.add_postpro_command(PostProCommand(name="COORDINATION NUMBER", step=10))
    controller.add_postpro_command(PostProCommand(name="VIOLATION EVOLUTION", step=10))

    controller.state.name = "Exemple - Roulement à billes (coupe 2D)"