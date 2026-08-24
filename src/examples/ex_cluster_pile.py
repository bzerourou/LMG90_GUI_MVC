"""
Exemple avancé : empilement de clusters triangulaires (rigidCluster)
tombant dans une boîte à parois fixes.

rigidCluster n'est pas généré par generate_granulo() (le générateur
granulométrique standard ne renseigne pas nb_vertices/nb_disk, requis par
AvatarValidator pour ce type — cf. validators.py::RIGID_CLUSTER). Les
clusters sont donc placés directement, un par un.
"""
from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, DOFOperation,
)


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2400.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Socle fixe ────────────────────────────────────────────────────────
    floor = Avatar(
        avatar_type=AvatarType.SMOOTH_WALL,
        center=[0.0, -0.05],
        material_name="TDURx", model_name="rigid", color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        wall_params={'l': 3.0, 'h': 0.1, 'nb_polyg': 20},
    )
    floor_idx = controller.add_avatar(floor)
    floor_id  = controller.state.avatars[floor_idx].avatar_id
    controller.add_dof_operation(DOFOperation(
        operation_type="imposeDrivenDof",
        target_type="avatar", target_value=floor_id,
        parameters={"component": [1, 2, 3], "dofty": "vlocy", "ct": 0.0},
    ))

    # ── Grille de clusters (chacun = 3 disques élémentaires) ────────────────
    nb_cols, nb_rows = 4, 3
    spacing = 0.4
    generated_indices = []

    for row in range(nb_rows):
        for col in range(nb_cols):
            cx = (col - (nb_cols - 1) / 2.0) * spacing
            cy = row * spacing + 1.5
            cluster = Avatar(
                avatar_type=AvatarType.RIGID_CLUSTER,
                center=[cx, cy],
                material_name="TDURx",
                model_name="rigid",
                color="MAGEx",
                origin=AvatarOrigin.MANUAL,
                radius=0.08,
                nb_vertices=3,   # nb_disk : 3 disques élémentaires par cluster

            )
            idx = controller.add_avatar(cluster)
            generated_indices.append(idx)

    avatar_ids = [controller.state.avatars[i].avatar_id for i in generated_indices]
    controller.state.avatar_groups["pile_clusters"] = avatar_ids

    # ── Lois de contact ────────────────────────────────────────────────────
    controller.add_contact_law(ContactLaw(
        name="isqc0", law_type=ContactLawType.IQS_CLB, friction=0.5
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="MAGEx",
        antagonist_body="RBDY2", antagonist_contactor="DISKx", antagonist_color="MAGEx",
        behavior_name="isqc0", alert=0.05,
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="RBDY2", candidate_contactor="DISKx", candidate_color="MAGEx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="GRAYx",
        behavior_name="isqc0", alert=0.05,
    ))

    controller.state.name = "Exemple - Empilement de clusters"