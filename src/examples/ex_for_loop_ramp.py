"""Exemple : boucle For générique — rampe de disques à rayon croissant."""
from ..core.models import Material, MaterialType, Model, ForLoop


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2500.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    # ── Boucle For : 12 disques dont le rayon croît linéairement avec i ────
    # template_config évalue les expressions Python via SafeEvaluator, avec
    # la variable de boucle 'i' disponible dans le contexte (cf.
    # for_loops_mixin.py::generate_for_loop).
    for_loop = ForLoop(
        loop_var="i",
        start_expr="0",
        end_expr="12",
        step_expr="1",
        target_type="avatar",
        template_config={
            "avatar_type": "rigidDisk",
            "center": "[i * 0.35, 0.0]",
            "material_name": "TDURx",
            "model_name": "rigid",
            "color": "JAUNx",
            "radius": "0.05 + i * 0.01",
        },
        group_name="rampe_croissante",
    )
    controller.generate_for_loop(for_loop)

    controller.state.name = "Exemple - Boucle For (rampe de rayons)"