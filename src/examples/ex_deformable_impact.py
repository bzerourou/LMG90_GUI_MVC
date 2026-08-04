"""
Exemple avancé : corps déformable avec contacteur CLxxx correctement câblé.

Corrige une simplification des exemples déformables précédents : sans
addContactors() sur le corps maillé, le contact rigide/déformable ne
fonctionne PAS lors du calcul, même si tout le reste (loi, visibilité)
est configuré. Cet exemple montre le câblage complet nécessaire :
  1. body.addContactors(...) sur l'objet pylmgc90 vivant
  2. avatar.contactors  -> utilisé par script_generator pour régénérer
     le body.addContactors(...) dans le script pre.py exporté
  3. avatar.mesh_params['contactors'] -> utilisé par viewer_3d pour
     dessiner les contacteurs en 3D (chemin de lecture différent de (2))
Les trois doivent être renseignés pour une cohérence totale entre calcul
live, script exporté, et visualisation.
"""
from pylmgc90 import pre

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule, DOFOperation, PostProCommand,
)


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="ELAS1", material_type=MaterialType.ELAS, density=2700.0,
        properties={"elas": "standard", "anisotropy": "isotropic",
                    "young": 70e9, "nu": 0.3},
    ))
    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2500.0
    ))
    controller.add_model(Model(
        name="femxx", physics="MECAx", element="T3xxx", dimension=2,
        options={"anisotropy": "iso__", "kinematic": "small",
                 "formulation": "UpdtL", "mass_storage": "lump_",
                 "material": "elas_", "external_model": "no___"},
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    mat_elas_obj = controller._pylmgc_materials["ELAS1"]
    mod_fem_obj  = controller._pylmgc_models["femxx"]

    lx, ly = 1.0, 0.4
    nx, ny = 8, 4
    x0, y0 = -lx / 2.0, 2.0

    surf_mesh = pre.buildMesh2D("2T3", x0, y0, lx, ly, nx, ny)
    body = pre.buildMeshedAvatar(mesh=surf_mesh, model=mod_fem_obj, material=mat_elas_obj)

    # ── Contacteur CLxxx sur le groupe "down" (créé automatiquement par
    # buildMesh2D — cf. mesh_wiz_def.py::MeshBoundaryPage._GROUPS_2D) ──────
    contactor_spec = {'shape': 'CLxxx', 'color': 'CYANx', 'group': 'down', 'params': {}}
    body.addContactors(shape='CLxxx', color='CYANx', group='down')

    controller._bodies_container.addAvatar(body)
    controller._pylmgc_bodies.append(body)

    mesh_params = {
        'geom': 'Rectangle', 'dim': 2,
        'lx': lx, 'ly': ly, 'nx': nx, 'ny': ny, 'mesh_type': '2T3',
        'cx': x0 + lx / 2.0, 'cy': y0 + ly / 2.0,
        'contactors': [contactor_spec],   # lu par viewer_3d
    }
    deformable_avatar = Avatar(
        avatar_type=AvatarType.MESH_DEFORMABLE,
        center=[x0 + lx / 2.0, y0 + ly / 2.0],
        material_name="ELAS1",
        model_name="femxx",
        color="CYANx",
        origin=AvatarOrigin.MANUAL,
        contactors=[contactor_spec],       # lu par script_generator
        mesh_params=mesh_params,
    )
    controller.state.avatars.append(deformable_avatar)
    controller.state_changed.emit()

    # ── Sol rigide, immobilisé ──────────────────────────────────────────────
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

    # ── Loi rigide/déformable + visibilité + postpro ───────────────────────
    controller.add_contact_law(ContactLaw(
        name="gapc0", law_type=ContactLawType.GAP_SGR_CLB, friction=0.3
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="MAILx", candidate_contactor="CLxxx", candidate_color="CYANx",
        antagonist_body="RBDY2", antagonist_contactor="ALpxx", antagonist_color="GRAYx",
        behavior_name="gapc0", alert=0.05,
    ))
    controller.add_postpro_command(PostProCommand(name="Fint EVOLUTION", step=10))

    controller.state.name = "Exemple - Impact déformable (contacteur complet)"