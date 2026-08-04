"""Exemple : corps déformable (maillage T3, matériau ELAS) chutant sur un mur rigide."""
from pylmgc90 import pre

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
    ContactLaw, ContactLawType, VisibilityRule,
)


def build(controller) -> None:
    controller.state.dimension = 2

    # ── Matériau élastique pour le corps déformable ────────────────────────
    controller.add_material(Material(
        name="ELAS1",
        material_type=MaterialType.ELAS,
        density=2700.0,
        properties={
            "elas": "standard",
            "anisotropy": "isotropic",
            "young": 70e9,
            "nu": 0.3,
        },
    ))

    # ── Matériau rigide pour le sol ─────────────────────────────────────────
    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2500.0
    ))

    # ── Modèle EF (triangle linéaire) ────────────────────────────────────
    controller.add_model(Model(
        name="femxx",
        physics="MECAx",
        element="T3xxx",
        dimension=2,
        options={
            "anisotropy": "iso__",
            "kinematic": "small",
            "formulation": "UpdtL",
            "mass_storage": "lump_",
            "material": "elas_",
            "external_model": "no___",
        },
    ))

    # ── Modèle rigide pour le sol ────────────────────────────────────────
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    mat_elas_obj = controller._pylmgc_materials["ELAS1"]
    mod_fem_obj  = controller._pylmgc_models["femxx"]

    # ── Corps déformable : rectangle maillé (1.0 x 0.4, 6x3 éléments) ─────
    lx, ly = 1.0, 0.4
    nx, ny = 6, 3
    x0, y0 = -lx / 2.0, 2.0

    # "2T3" est le mesh_type attendu par pre.buildMesh2D (découpage du
    # quadrangle en 2 triangles) — distinct du nom d'élément fini "T3xxx"
    # utilisé côté Model plus haut.
    surf_mesh = pre.buildMesh2D("2T3", x0, y0, lx, ly, nx, ny)
    body = pre.buildMeshedAvatar(mesh=surf_mesh, model=mod_fem_obj, material=mat_elas_obj)

    controller._bodies_container.addAvatar(body)
    controller._pylmgc_bodies.append(body)

    mesh_params = {
        'geom': 'Rectangle', 'dim': 2,
        'lx': lx, 'ly': ly, 'nx': nx, 'ny': ny,
        'mesh_type': '2T3',
        'cx': x0 + lx / 2.0, 'cy': y0 + ly / 2.0,
    }
    deformable_avatar = Avatar(
        avatar_type=AvatarType.MESH_DEFORMABLE,
        center=[x0 + lx / 2.0, y0 + ly / 2.0],
        material_name="ELAS1",
        model_name="femxx",
        color="CYANx",
        origin=AvatarOrigin.MANUAL,
        contactors=[],
        mesh_params=mesh_params,
    )
    controller.state.avatars.append(deformable_avatar)
    controller.state_changed.emit()

    # ── Sol rigide (mur lisse fixe) ───────────────────────────────────────
    floor = Avatar(
        avatar_type=AvatarType.SMOOTH_WALL,
        center=[0.0, -0.05],
        material_name="TDURx",
        model_name="rigid",
        color="GRAYx",
        origin=AvatarOrigin.MANUAL,
        wall_params={'l': 3.0, 'h': 0.1, 'nb_polyg': 20},
    )
    controller.add_avatar(floor)

    # ── Loi de contact rigide/déformable + visibilité ──────────────────────
    # GAP_SGR_CLB ne requiert QUE 'fric' (ContactLawValidator._FRICTION_REQUIRED) —
    # pas de 'stiffness' ni autre propriété. ContactLaw n'accepte 'stiffness'
    # que via le dict properties={...}, jamais comme paramètre direct du
    # constructeur (cf. models.py::ContactLaw — seuls name/law_type/friction/
    # properties sont des champs valides).
    controller.add_contact_law(ContactLaw(
        name="gapc0",
        law_type=ContactLawType.GAP_SGR_CLB,
        friction=0.3,
    ))
    controller.add_visibility_rule(VisibilityRule(
        candidate_body="MAILx", candidate_contactor="CLxxx", candidate_color="CYANx",
        antagonist_body="RBDY2", antagonist_contactor="JONCx", antagonist_color="GRAYx",
        behavior_name="gapc0", alert=0.05,
    ))

    controller.state.name = "Exemple - Corps déformable sur sol rigide"