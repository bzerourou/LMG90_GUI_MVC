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
from .ex_rotating_drum import build as _build_rotating_drum
from .ex_biaxial_compression import build as _build_biaxial_compression
from .ex_hexagon_packing import build as _build_hexagon_packing
from .ex_cluster_pile import build as _build_cluster_pile
from .ex_avalanche_slope import build as _build_avalanche_slope
from .ex_composite_scene import build as _build_composite_scene


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
        id="granulo_deposit",
        title="🎲 Dépôt granulométrique",
        category="Génération de masse",
        description=(
            "500 disques de rayons aléatoires [0.03, 0.08] déposés par "
            "gravité dans une boîte via granulo_Random + depositInBox2D. "
            "Illustre : GranuloGeneration, génération vectorisée numpy."
        ),
        dimension=2,
        difficulty="Intermédiaire",
        builder=_build_granulo_deposit,
        tags=["granulo", "masse"],
    ),
    ExampleSpec(
        id="circle_loop",
        title="⭕ Boucle géométrique — Cercle",
        category="Génération de masse",
        description=(
            "12 disques disposés en cercle autour d'un centre, générés "
            "depuis un avatar modèle via une boucle Cercle. Illustre le "
            "système de boucles géométriques (Loop) et les groupes."
        ),
        dimension=2,
        difficulty="Débutant",
        builder=_build_circle_loop,
        tags=["boucle", "groupe"],
    ),
    ExampleSpec(
        id="deformable_drop",
        title="🔷 Corps déformable sur sol rigide",
        category="Avancé",
        description=(
            "Un rectangle déformable (maillage T3, matériau ELAS) tombe "
            "sur un mur rigide. Illustre : buildMesh2D, matériau élastique, "
            "loi GAP_SGR_CLB (rigide/déformable)."
        ),
        dimension=2,
        difficulty="Avancé",
        builder=_build_deformable_drop,
        tags=["deformable", "fem"],
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
    ExampleSpec(
        id="rotating_drum",
        title="🌀 Tambour rotatif",
        category="Avancé",
        description=(
            "Disque creux (is_hollow, contacteur xKSID) entraîné en "
            "rotation constante, contenant un dépôt granulométrique "
            "Drum2D. Illustre le conteneur xKSID et la rotation entraînée."
        ),
        dimension=2, difficulty="Avancé",
        builder=_build_rotating_drum,
        tags=["dof", "granulo", "rotation"],
    ),
    ExampleSpec(
        id="biaxial_compression",
        title="🗜️ Compression biaxiale",
        category="Avancé",
        description=(
            "Deux parois verticales mobiles compriment un lit de grains "
            "à vitesse constante. Illustre imposeDrivenDof en translation "
            "continue, combiné à une rotation ponctuelle de mise en place."
        ),
        dimension=2, difficulty="Avancé",
        builder=_build_biaxial_compression,
        tags=["dof", "granulo", "essai_mecanique"],
    ),
    ExampleSpec(
        id="hexagon_packing",
        title="⬡ Pavage hexagonal",
        category="Structures",
        description=(
            "Grille de 16 hexagones (rigidPolygon, sommets explicites) "
            "en pavage décalé de type nid d'abeille. Illustre les "
            "polygones personnalisés (generation_type='full')."
        ),
        dimension=2, difficulty="Intermédiaire",
        builder=_build_hexagon_packing,
        tags=["avatar", "polygone"],
    ),
    ExampleSpec(
        id="cluster_pile",
        title="🔺 Empilement de clusters",
        category="Structures",
        description=(
            "Grille de 12 clusters triangulaires (rigidCluster, 3 disques "
            "chacun) tombant sur un socle fixe. Illustre rigidCluster, "
            "non compatible avec la génération granulométrique standard."
        ),
        dimension=2, difficulty="Intermédiaire",
        builder=_build_cluster_pile,
        tags=["avatar", "cluster"],
    ),
    ExampleSpec(
        id="avalanche_slope",
        title="⛰️ Avalanche sur pente inclinée",
        category="Avancé",
        description=(
            "Pente inclinée à 25° (rotation DOF) recevant un dépôt "
            "granulométrique qui s'écoule sous gravité et friction. "
            "Illustre la combinaison rotation statique + granulo + DOF."
        ),
        dimension=2, difficulty="Avancé",
        builder=_build_avalanche_slope,
        tags=["dof", "granulo", "pente"],
    ),    
    ExampleSpec(
        id="composite_scene",
        title="🎨 Scène composite — synthèse complète",
        category="Avancé",
        description=(
            "L'exemple le plus complet : mur de briques cohésif, rampe "
            "inclinée, disques/jonc/polygone/cluster mobiles, 3 lois de "
            "contact distinctes, tables de visibilité croisées par paire "
            "de couleurs, et variables dynamiques (dynamic_vars) pilotant "
            "toute la géométrie — visibles dans Outils > Variables "
            "dynamiques après chargement."
        ),
        dimension=2, difficulty="Avancé",
        builder=_build_composite_scene,
        tags=["synthese", "variables", "contact", "avatar"],
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