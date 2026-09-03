"""
Exemple avancé : frein à disque de vélo (modèle 3D fidèle à la réalité).

Illustre :
  - rigidCylinder très plat (disque de frein, Ø160 mm x 1.8 mm — standard
    Shimano/SRAM route) monté sur un axe de moyeu fixe
  - Deux plaquettes (rigidPlan) de l'étrier, positionnées de part et
    d'autre du disque au rayon effectif de freinage, fermées par une
    vitesse de piston réaliste (~5 mm/s) jusqu'au contact
  - Rotation du disque définie par une CONDITION INITIALE
    (imposeInitValue) et non une vitesse imposée en continu : c'est bien
    le frottement plaquette/disque qui freine la roue, pas une contrainte
    artificielle — condition indispensable pour que le freinage soit
    physiquement représenté
  - Loi de contact IQS_CLB (μ ≈ 0.40, plaquette semi-métallique / disque
    acier inoxydable, valeur usuelle à sec)
  - Suivi de l'énergie dissipée par frottement (freinage) et du couple
    résistant sur le disque
"""
import math

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, DOFOperation, PostProCommand,
)


def build(controller) -> None:
    controller.state.dimension = 3

    # ── Matériaux ────────────────────────────────────────────────────────
    # Disque en acier inoxydable (rotor de frein vélo)
    controller.add_material(Material(
        name="rotor", material_type=MaterialType.RIGID, density=7700.0
    ))
    # Plaquette semi-métallique (matrice résine + charges métalliques)
    controller.add_material(Material(
        name="padxx", material_type=MaterialType.RIGID, density=2600.0
    ))

    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx3D", dimension=3
    ))

    # ── Dimensions réelles (standard vélo route/VTT, ex. Shimano RT-CL800) ─
    disc_radius     = 0.080   # rayon du disque (Ø 160 mm)
    disc_thickness  = 0.0018  # épaisseur du disque (1.8 mm, acier fin)

    pad_length      = 0.034   # longueur de plaquette (dans le sens tangentiel)
    pad_width       = 0.020   # largeur radiale de la plaquette
    pad_thickness   = 0.008   # épaisseur de la garniture

    effective_radius = 0.060  # rayon effectif de freinage (~75% du rayon disque)

    disc_center = [0.0, 0.0, 0.0]

    # ── Disque de frein : cylindre très plat (axe du cylindre selon Z) ──────
    rotor = Avatar(
        avatar_type=AvatarType.RIGID_CYLINDER,
        center=list(disc_center),
        material_name="rotor",
        model_name="rigid",
        color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        radius=disc_radius,
        wall_params={'h': disc_thickness},
    )
    rotor_idx = controller.add_avatar(rotor)
    rotor_id  = controller.state.avatars[rotor_idx].avatar_id

    # ── Moyeu / axe : bearing fixe ──────────────────────────────────────────
    # Le roulement de moyeu bloque toute translation et toute rotation
    # transversale (tangage/lacet), mais LAISSE LIBRE la rotation propre du
    # disque autour de son axe (Z) — c'est cette liberté qui permet au
    # frottement des plaquettes de réellement décélérer la roue.
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=rotor_id,
        parameters={"component": [1, 2, 3], "dofty": "vlocy", "ct": 0.0},
    ))
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=rotor_id,
        parameters={"component": [4, 5], "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Condition initiale de roulage : roue à ~25 km/h (700x25c, R=0.335 m) ─
    wheel_travel_radius = 0.335
    initial_speed_kmh   = 25.0
    v0 = initial_speed_kmh / 3.6
    omega0 = v0 / wheel_travel_radius   # vitesse angulaire initiale (rad/s)

    controller.add_dof_operation(DOFOperation(
        operation_type="imposeInitValue",
        target_type="avatar", target_value=rotor_id,
        parameters={"component": 6, "value": omega0},
    ))

    # ── Plaquettes de frein (étrier) — de part et d'autre du disque ─────────
    # axe1 = demi-longueur tangentielle, axe2 = demi-largeur radiale,
    # axe3 = demi-épaisseur garniture (axe1, axe2 > axe3 requis par le
    # validateur pour rigidPlan).
    pad_axis = {
        'axe1': pad_length / 2.0,
        'axe2': pad_width / 2.0,
        'axe3': pad_thickness / 2.0,
    }

    closing_speed = 0.005  # vitesse de fermeture du piston (~5 mm/s)
    pad_gap       = 0.0005 # jeu initial plaquette/disque au repos (0.5 mm)

    pad_indices = []
    pad_ids     = []

    for side, sign, color in (("haut", +1.0, "REDxx"), ("bas", -1.0, "REDxx")):
        z_pos = sign * (disc_thickness / 2.0 + pad_thickness / 2.0 + pad_gap)
        pad = Avatar(
            avatar_type=AvatarType.RIGID_PLAN,
            center=[effective_radius, 0.0, z_pos],
            material_name="padxx",
            model_name="rigid",
            color=color,
            origin=AvatarOrigin.MANUAL,
            axis=dict(pad_axis),
        )
        idx = controller.add_avatar(pad)
        pad_id = controller.state.avatars[idx].avatar_id
        pad_indices.append(idx)
        pad_ids.append(pad_id)

        # Bloquer tout sauf la fermeture selon Z (translation normale au disque)
        controller.add_dof_operation(DOFOperation(
            operation_type="imposeDrivenDof",
            target_type="avatar", target_value=pad_id,
            parameters={"component": [1, 2], "dofty": "vlocy", "ct": 0.0},
        ))
        controller.add_dof_operation(DOFOperation(
            operation_type="imposeDrivenDof",
            target_type="avatar", target_value=pad_id,
            parameters={"component": [4, 5, 6], "dofty": "vlocy", "ct": 0.0},
        ))
        # Fermeture du piston vers le disque (signe opposé selon le côté)
        controller.add_dof_operation(DOFOperation(
            operation_type="imposeDrivenDof",
            target_type="avatar", target_value=pad_id,
            parameters={"component": 3, "dofty": "vlocy", "ct": -sign * closing_speed},
        ))

    controller.state.avatar_groups["plaquettes"] = list(pad_ids)

    # ── Loi de contact plaquette/disque ─────────────────────────────────────
    # μ ≈ 0.40 : valeur usuelle pour une garniture semi-métallique sur disque
    # acier inoxydable à sec (plage typique constructeur : 0.35 – 0.45).
    controller.add_contact_law(ContactLaw(
        name="brake", law_type=ContactLawType.IQS_CLB, friction=0.40
    ))

    # ── Tables de visibilité (une par plaquette, même loi) ──────────────────
    for pad_color in ("REDxx",):
        controller.add_visibility_rule(VisibilityRule(
            candidate_body="RBDY3", candidate_contactor="CYLND", candidate_color="GRAYx",
            antagonist_body="RBDY3", antagonist_contactor="PLANx", antagonist_color=pad_color,
            behavior_name="brake", alert=0.002,   # 2 mm — alerte serrée (jeu 0.5 mm)
        ))

    # ── Post-traitement ──────────────────────────────────────────────────────
    controller.add_postpro_command(PostProCommand(name="KINETIC ENERGY", step=5))
    controller.add_postpro_command(PostProCommand(name="DISSIPATED ENERGY", step=5))
    controller.add_postpro_command(PostProCommand(
        name="TORQUE EVOLUTION", step=5,
        target_type="avatar", target_value=rotor_id,
    ))

    controller.state.name = "Exemple - Frein à disque de vélo"