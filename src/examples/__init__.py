"""
Registre central des exemples du menu "📚 Exemples".
"""
from .base import ExampleSpec

from .ex_falling_disks import build as _build_falling_disks
from .ex_sphere_stack import build as _build_sphere_stack
from .ex_masonry_wall import build as _build_masonry_wall
from .ex_granulo_deposit import build as _build_granulo_deposit
from .ex_circle_loop import build as _build_circle_loop
from .ex_deformable_drop import build as _build_deformable_drop
from .ex_factory_injection import build as _build_factory_injection
from .ex_cohesive_wall import build as _build_cohesive_wall
from .ex_dumbbell_avatar import build as _build_dumbbell_avatar
from .ex_for_loop_ramp import build as _build_for_loop_ramp
from .ex_dof_conditions import build as _build_dof_conditions
from .ex_couette_shear import build as _build_couette_shear
from .ex_hopper_discharge import build as _build_hopper_discharge
from .ex_cable_pendulum import build as _build_cable_pendulum
from .ex_deformable_impact import build as _build_deformable_impact
from .ex_l_shaped_wall import build as _build_l_shaped_wall
from .ex_silo_factory import build as _build_silo_factory


EXAMPLES: list[ExampleSpec] = [
    ExampleSpec(
        id="falling_disks",
        title="🎱 Chute de disques 2D",
        category="Bases",
        description=(
            "<b>Le point de départ classique.</b><br>"
            "Une rangée de disques rigides tombe sous gravité dans une "
            "boîte ouverte. Illustre : matériau RIGID, modèle Rxx2D, "
            "avatars rigidDisk, loi IQS_CLB, table de visibilité, "
            "boucle Ligne pour aligner les disques."
        ),
        dimension=2,
        difficulty="Débutant",
        builder=_build_falling_disks,
        tags=["avatar", "contact", "boucle"],
    ),
    ExampleSpec(
        id="sphere_stack",
        title="🔵 Empilement de sphères 3D",
        category="Bases",
        description=(
            "Grille 3×3 de sphères rigides empilées sur un plan. "
            "Illustre : modèle Rxx3D, rigidSphere, rigidPlan comme sol. "
            "Placement direct (pas de boucle Loop — ce système est 2D "
            "uniquement, voir le tag correspondant sur cet exemple)."
        ),
        dimension=3,
        difficulty="Débutant",
        builder=_build_sphere_stack,
        tags=["avatar", "3d"],
    ),
    ExampleSpec(
        id="masonry_wall",
        title="🧱 Mur de maçonnerie",
        category="Structures",
        description=(
            "Mur de 8×5 briques en appareil Standard (décalage demi-brique). "
            "Illustre : pre.brick2D, groupe d'avatars, loi CLALp pour "
            "l'interface entre briques."
        ),
        dimension=2,
        difficulty="Intermédiaire",
        builder=_build_masonry_wall,
        tags=["maconnerie", "groupe"],
    ),
    ExampleSpec(
        id="cohesive_wall",
        title="🩹 Mur avec liaisons cohésives (CZM)",
        category="Structures",
        description=(
            "Deux rangées de blocs collées avec une loi de zone cohésive "
            "MAC_CZM (résistance normale/tangentielle avant rupture). "
            "Illustre : IQS_MAC_CZM, propriétés stfr/dyfr/cn/ct/b/w."
        ),
        dimension=2,
        difficulty="Avancé",
        builder=_build_cohesive_wall,
        tags=["contact", "czm"],
    ),
    ExampleSpec(
        id="dumbbell_avatar",
        title="🏋️ Avatar composite — haltère",
        category="Contacteurs manuels",
        description=(
            "Un avatar unique composé de 2 disques + 1 jonc reliant "
            "les deux, via emptyAvatar et addContactors. Illustre le "
            "système de contacteurs manuels pour des formes composites."
        ),
        dimension=2,
        difficulty="Intermédiaire",
        builder=_build_dumbbell_avatar,
        tags=["avatar_vide", "contacteurs"],
    ),
    ExampleSpec(
        id="for_loop_ramp",
        title="📐 Boucle For — rampe de disques à rayon croissant",
        category="Génération de masse",
        description=(
            "12 disques alignés dont le rayon augmente à chaque itération "
            "(expression Python liée à la variable de boucle i). Illustre "
            "le système ForLoop générique avec template JSON évalué."
        ),
        dimension=2,
        difficulty="Intermédiaire",
        builder=_build_for_loop_ramp,
        tags=["boucle", "for"],
    ),
    ExampleSpec(
        id="dof_conditions",
        title="🔒 Conditions aux limites DOF",
        category="Contrôle",
        description=(
            "Un disque avec une vitesse initiale imposée (imposeInitValue) "
            "et un second bloqué en rotation (imposeDrivenDof). Illustre "
            "le système DOFOperation appliqué directement via l'API."
        ),
        dimension=2,
        difficulty="Intermédiaire",
        builder=_build_dof_conditions,
        tags=["dof", "conditions_limites"],
    ),
    ExampleSpec(
        id="couette_shear",
        title="🌀 Cisaillement en cellule de Couette",
        category="Avancé",
        description=(
            "Dépôt granulométrique dans un anneau (conteneur Couette2D) — "
            "配置 typique pour l'étude de cisaillement annulaire en "
            "mécanique des milieux granulaires. Illustre GranuloGeneration "
            "avec container_type='Couette2D'."
        ),
        dimension=2,
        difficulty="Avancé",
        builder=_build_couette_shear,
        tags=["granulo", "couette"],
    ),
    ExampleSpec(
        id="hopper_discharge",
        title="⏳ Décharge en trémie",
        category="Avancé",
        description=(
            "Trémie en V (géométrie réelle via AvatarFactory) recevant un "
            "dépôt granulométrique de 180 disques. Illustre : "
            "AvatarFactory.create_hopper_2d, DOF par groupe, post-pro."
        ),
        dimension=2,
        difficulty="Avancé",
        builder=_build_hopper_discharge,
        tags=["factory", "granulo", "dof"],
    ),
    ExampleSpec(
        id="cable_pendulum",
        title="🪢 Pendule à câble",
        category="Avancé",
        description=(
            "Deux points matériels (PT2Dx) reliés par une loi ELASTIC_WIRE, "
            "l'un fixé, l'autre libre sous gravité. Illustre le contact "
            "point/point et l'immobilisation complète d'un avatar via DOF."
        ),
        dimension=2,
        difficulty="Avancé",
        builder=_build_cable_pendulum,
        tags=["contact", "dof", "point_point"],
    ),
    ExampleSpec(
        id="deformable_impact",
        title="💥 Impact déformable (contacteur complet)",
        category="Avancé",
        description=(
            "Corps déformable avec contacteur CLxxx correctement câblé "
            "(live + script + viewer) chutant sur un sol immobilisé. "
            "Corrige une simplification des exemples déformables précédents."
        ),
        dimension=2,
        difficulty="Avancé",
        builder=_build_deformable_impact,
        tags=["deformable", "contact"],
    ),
    ExampleSpec(
        id="l_shaped_wall",
        title="📐 Structure en L + dépôt granulométrique",
        category="Avancé",
        description=(
            "Deux murs de briques formant un angle, immobilisés en un "
            "seul DOFOperation de groupe, recevant un dépôt de 120 grains "
            "dans le coin. Illustre DOFOperation(target_type='group')."
        ),
        dimension=2,
        difficulty="Avancé",
        builder=_build_l_shaped_wall,
        tags=["maconnerie", "granulo", "dof", "groupe"],
    ),
    ExampleSpec(
        id="silo_factory",
        title="🏭 Factory en silo",
        category="Avancé",
        description=(
            "Particle Factory avec conteneur silo complet (parois "
            "générées automatiquement) + lois de contact et post-pro "
            "préconfigurées, prêtes à l'emploi après génération du script."
        ),
        dimension=2,
        difficulty="Avancé",
        builder=_build_silo_factory,
        tags=["factory", "contact", "postpro"],
    ),
]


def get_example(example_id: str) -> ExampleSpec | None:
    return next((e for e in EXAMPLES if e.id == example_id), None)


def get_categories() -> list[str]:
    seen = []
    for e in EXAMPLES:
        if e.category not in seen:
            seen.append(e.category)
    return seen