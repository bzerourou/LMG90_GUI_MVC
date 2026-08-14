"""
Exemple avancé : pavage hexagonal (nid d'abeille) via rigidPolygon en mode
'full' (sommets explicites), placement direct par grille décalée.
"""
import math

from ..core.models import (
    Material, MaterialType, Model, Avatar, AvatarType, AvatarOrigin,
)


def _hexagon_vertices(circumradius: float) -> list:
    """6 sommets d'un hexagone régulier (pointy-top), relatifs au centre local."""
    return [
        [circumradius * math.cos(math.pi / 2 + k * math.pi / 3),
         circumradius * math.sin(math.pi / 2 + k * math.pi / 3)]
        for k in range(6)
    ]


def build(controller) -> None:
    controller.state.dimension = 2

    controller.add_material(Material(
        name="TDURx", material_type=MaterialType.RIGID, density=2400.0
    ))
    controller.add_model(Model(
        name="rigid", physics="MECAx", element="Rxx2D", dimension=2
    ))

    R = 0.12   # circumradius
    vertices = _hexagon_vertices(R)

    # ── Grille hexagonale décalée (4 colonnes x 4 rangs) ────────────────────
    dx = R * math.sqrt(3)      # espacement horizontal entre centres
    dy = R * 1.5               # espacement vertical entre rangs
    nb_cols, nb_rows = 4, 4

    generated_indices = []
    for row in range(nb_rows):
        row_offset = (dx / 2.0) if (row % 2 == 1) else 0.0
        for col in range(nb_cols):
            cx = col * dx + row_offset
            cy = row * dy + 3.0   # +3.0 pour laisser tomber sous gravité
            hexagon = Avatar(
                avatar_type=AvatarType.RIGID_POLYGON,
                center=[cx, cy],
                material_name="TDURx",
                model_name="rigid",
                color="GOLDx",
                origin=AvatarOrigin.MANUAL,
                generation_type="full",
                vertices=vertices,
                radius=R,   # taille caractéristique (cf. avatar_factory.py rectangle template)
            )
            idx = controller.add_avatar(hexagon)
            generated_indices.append(idx)

    avatar_ids = [controller.state.avatars[i].avatar_id for i in generated_indices]
    controller.state.avatar_groups["nid_abeille"] = avatar_ids

    controller.state.name = "Exemple - Pavage hexagonal"