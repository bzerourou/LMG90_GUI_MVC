"""
Modèles de données pour LMGC90_GUI.
Représentation pure des objets sans logique UI (Model dans MVC).

=== REFACTOR "avatar_id stable" ===
Chaque Avatar possède désormais un identifiant `avatar_id` (uuid hex),
généré une seule fois à la création et JAMAIS modifié, y compris quand
sa position dans `state.avatars` change (suppression d'un autre avatar,
réordonnancement, etc.).

"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from pathlib import Path
import uuid


def convert_to_serializable(obj):
    """
    Convertit récursivement les objets non-sérialisables en types JSON.
    Gère numpy.ndarray, numpy.integer, numpy.floating, etc.
    """
    import numpy as np

    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    else:
        return obj


def new_avatar_id() -> str:
    """Génère un nouvel identifiant stable d'avatar (uuid4 hex, 32 car.)."""
    return uuid.uuid4().hex


# ============================================================================
# ENUMS - Types énumérés
# ============================================================================

class MaterialType(Enum):
    """Types de matériaux supportés par LMGC90"""
    RIGID = "RIGID"
    ELAS = "ELAS"
    ELAS_DILA = "ELAS_DILA"
    VISCO_ELAS = "VISCO_ELAS"
    ELAS_PLAS = "ELAS_PLAS"
    THERMO_ELAS = "THERMO_ELAS"
    PORO_ELAS = "PORO_ELAS"
    DISCRETE = "DISCRETE"
    USER_MAT = "USER_MAT"
    EXTERNAL = "EXTERNAL"


class AvatarType(Enum):
    """Types d'avatars (corps rigides) supportés"""
    RIGID_DISK = "rigidDisk"
    RIGID_JONC = "rigidJonc"
    RIGID_POLYGON = "rigidPolygon"
    RIGID_OVOID = "rigidOvoidPolygon"
    RIGID_DISCRETE = "rigidDiscreteDisk"
    RIGID_CLUSTER = "rigidCluster"
    ROUGH_WALL = "roughWall"
    FINE_WALL = "fineWall"
    SMOOTH_WALL = "smoothWall"
    GRANULO_WALL = "granuloRoughWall"
    EMPTY_AVATAR = "emptyAvatar"
    MESH_DEFORMABLE = "mesh"
    # 3D
    RIGID_SPHERE = "rigidSphere"
    RIGID_PLAN = "rigidPlan"
    RIGID_CYLINDER = "rigidCylinder"
    RIGID_POLYHEDRON = "rigidPolyhedron"
    ROUGH_WALL_3D = "roughWall3D"
    GRANULO_ROUGH_WALL_3D = "granuloRoughWall3D"

class ContactLawType(Enum):
    """Types de lois de contact pylmgc90"""
    # Rigide / Rigide
    IQS_CLB          = "IQS_CLB"
    IQS_CLB_G0       = "IQS_CLB_g0"
    IQS_DS_CLB       = "IQS_DS_CLB"
    IQS_MOHR_DS_CLB  = "IQS_MOHR_DS_CLB"
    IQS_MAC_CZM      = "IQS_MAC_CZM"
    RST_CLB          = "RST_CLB"
    # Rigide / Déformable  ou  Déformable / Déformable
    GAP_SGR_CLB      = "GAP_SGR_CLB"
    GAP_SGR_CLB_G0   = "GAP_SGR_CLB_g0"
    GAP_MOHR_DS_CLB  = "GAP_MOHR_DS_CLB"
    MAC_CZM          = "MAC_CZM"
    MAL_CZM          = "MAL_CZM"
    # Point / Point
    ELASTIC_WIRE     = "ELASTIC_WIRE"
    BRITTLE_ELASTIC_WIRE = "BRITTLE_ELASTIC_WIRE"
    ELASTIC_ROD      = "ELASTIC_ROD"
    VOIGT_ROD        = "VOIGT_ROD"
    # Any / Any
    COUPLED_DOF        = "COUPLED_DOF"
    NORMAL_COUPLED_DOF = "NORMAL_COUPLED_DOF"
    ELASTIC_REPELL_CLB = "ELASTIC_REPELL_CLB"



# ---------------------------------------------------------------------------
# Classification des lois par catégorie de paires de contacteurs
# Utilisé dans contact_tab pour filtrer le combo "Type" et dans les validators
# ---------------------------------------------------------------------------

#: Lois applicables entre deux corps rigides
LAWS_RIGID_RIGID: list[str] = [
    "IQS_CLB",
    "IQS_CLB_g0",
    "IQS_DS_CLB",
    # lois cohésive
    "IQS_MOHR_DS_CLB",
    #modèle cohésif
    "IQS_MAC_CZM",
    #fr avec restitution
    "RST_CLB",


]

#: Lois applicables entre rigide/déformable ou déformable/déformable
LAWS_RIGID_DEFORMABLE: list[str] = [

    "GAP_SGR_CLB",
    "GAP_SGR_CLB_g0",
    #loi cohésive
    "GAP_MOHR_DS_CLB",
    #modèle cohésif
    "MAC_CZM",
    "MAL_CZM"
]

#: Lois applicables entre contacteurs ponctuels (PT2Dx / PT3Dx / NODES)
LAWS_POINT_POINT: list[str] = [
    #cables
    "ELASTIC_WIRE",
    "BRITTLE_ELASTIC_WIRE",
    #barre élastique
    "ELASTIC_ROD",
    "VOIGT_ROD" ,
]

#: Toutes les lois disponibles (any / any)
LAWS_ANY_ANY: list[str] = [
       "COUPLED_DOF",
       "NORMAL_COUPLED_DOF",
       "ELASTIC_REPELL_CLB",
]

#: Dictionnaire catégorie → liste de lois (utilisé dans contact_tab)
CONTACT_LAW_CATEGORIES: dict[str, list[str]] = {
    "Rigide / Rigide":               LAWS_RIGID_RIGID,
    "Rigide / Déformable (ou Déf/Déf)": LAWS_RIGID_DEFORMABLE,
    "Point / Point":                 LAWS_POINT_POINT,
    "Toutes (any / any)":            LAWS_ANY_ANY,
}  



class AvatarOrigin(Enum):
    """Origine de création d'un avatar"""
    MANUAL  = "manual"   # Créé manuellement
    LOOP    = "loop"     # Généré par une boucle géométrique ou For
    GRANULO = "granulo"  # Généré par granulométrie
    FACTORY = "factory"  # Généré par une Particle Factory (pre.py)


class UnitSystem(Enum):
    """Système d'unités"""
    SI = "SI"      # International System (m, kg, s, N, Pa, J)
    CGS = "CGS"    # Centimeter-Gram-Second (cm, g, s, dyn, Ba, erg)

# ============================================================================
# DATACLASSES - Modèles de données
# ============================================================================

@dataclass
class Material:
    """Représente un matériau LMGC90"""
    name: str
    material_type: MaterialType
    density: float
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour sérialisation JSON"""
        return {
            'name': self.name,
            'type': self.material_type.value,
            'density': self.density,
            'props': self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Material':
        """Crée un Material depuis un dictionnaire"""
        return cls(
            name=data['name'],
            material_type=MaterialType(data['type']),
            density=data['density'],
            properties=data.get('props', {})
        )


@dataclass
class Model:
    """Représente un modèle physique (éléments finis ou corps rigides)"""
    name: str
    physics: str  # MECAx, THERx, HYDRx
    element: str  # Rxx2D, T3xxx, Q4xxx, etc.
    dimension: int  # 2 ou 3
    options: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        result = {
            'name': self.name,
            'physics': self.physics,
            'element': self.element,
            'dimension': self.dimension
        }
        # Ajouter les options au même niveau
        result.update(self.options)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Model':
        """Crée un Model depuis un dictionnaire"""
        # Extraire les champs principaux
        base_keys = ['name', 'physics', 'element', 'dimension']
        options = {k: v for k, v in data.items() if k not in base_keys}
        
        return cls(
            name=data['name'],
            physics=data['physics'],
            element=data['element'],
            dimension=data['dimension'],
            options=options
        )


@dataclass
class Avatar:
    """
    Représente un avatar (corps rigide).
    Contient tous les champs possibles pour tous les types.

    `avatar_id` est l'identité STABLE de l'avatar : générée une seule fois
    à la création, elle ne change jamais, même si la position de l'avatar
    dans `state.avatars` change (suppression d'un autre avatar, etc.).
    C'est cet id qui doit être utilisé pour toute référence persistée
    (groupes, opérations DOF, post-pro, boucles, granulo...).
    """
    avatar_type: AvatarType
    center: List[float]
    material_name: str
    model_name: str
    color: str = "BLUEx"
    origin: AvatarOrigin = AvatarOrigin.MANUAL
    avatar_id: str = field(default_factory=new_avatar_id)
    controller: Any = field(repr=False, default=None)  # Référence au contrôleur (non sérialisé)
    
    # Champs spécifiques selon le type
    radius: Optional[float] = None
    axis: Optional[Dict[str, float]] = None  # {'axe1': float, 'axe2': float}
    vertices: Optional[List[List[float]]] = None
    nb_vertices: Optional[int] = None
    generation_type: Optional[str] = None  # regular, full, bevel
    is_hollow: bool = False
    wall_params: Optional[Dict[str, Any]] = None  # l, h, r, rmin, rmax, nb_vertex, nb_polyg
    contactors: List[Dict[str, Any]] = field(default_factory=list)
    # Paramètres de maillage déformable (MESH_DEFORMABLE uniquement)
    mesh_params: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour sérialisation"""
        data = {
            'type': self.avatar_type.value,
            'avatar_id': self.avatar_id,
            'center': convert_to_serializable(self.center),
            'material': self.material_name,
            'model': self.model_name,
            'color': self.color,
            '__origin': self.origin.value
        }
        
        # Ajouter les champs non-None
        if self.radius is not None:
            if self.avatar_type not in [AvatarType.RIGID_POLYGON, AvatarType.RIGID_POLYHEDRON] :
                data['r'] = self.radius
            else : 
                data['radius'] = self.radius
        
        if self.axis:
            data['axe1'] = self.axis['axe1']
            data['axe2'] = self.axis['axe2']
            if 'axe3' in self.axis:
                data['axe3'] = self.axis['axe3']
        
        if self.vertices:
            data['vertices'] = self.vertices
        
        if self.nb_vertices is not None:
            data['nb_vertices'] = self.nb_vertices
        
        if self.generation_type:
            data['gen_type'] = self.generation_type
        
        if self.is_hollow:
            data['is_Hollow'] = True
        
        if self.wall_params:
            data.update(convert_to_serializable(self.wall_params))
        
        if self.contactors:
            data['contactors'] = convert_to_serializable(self.contactors)
        
        if self.mesh_params is not None:
            data['mesh_params'] = convert_to_serializable(self.mesh_params)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Avatar':
        """
        Crée un Avatar depuis un dictionnaire.

        Si 'avatar_id' est absent (anciens fichiers .lmgc90), un nouvel id
        est généré. C'est sans risque pour CET avatar individuellement :
        la résolution des anciennes références positionnelles qui le
        visaient éventuellement est gérée à un niveau supérieur, dans
        ProjectState.from_dict() / _migrate_legacy_avatar_refs(), qui a
        accès à l'ORDRE des avatars (donc à la correspondance
        position -> avatar_id) au moment du chargement.
        """
        # Reconstruire axis si présent
        axis = None
        if 'axe1' in data and 'axe2' in data:
            axis = {'axe1': data['axe1'], 'axe2': data['axe2']}
            if 'axe3' in data : 
                axis['axe3'] = data['axe3']
        if isinstance(data['center'], list):
            center = data['center']
        # Reconstruire wall_params
        wall_keys = ['l', 'h', 'r', 'rmin', 'rmax', 'nb_vertex', 'nb_polyg','lx', 'ly', 'lz','ra', 'rb', 'faces', 'brick_name']
        wall_params = {k: data[k] for k in wall_keys if k in data}
        
        return cls(
            avatar_type=AvatarType(data['type']),
            center=center,
            material_name=data['material'],
            model_name=data['model'],
            color=data.get('color', 'BLUEx'),
            origin=AvatarOrigin(data.get('__origin', 'manual')),
            avatar_id=data.get('avatar_id') or new_avatar_id(),
            radius=data.get('r') or data.get('radius'),
            axis=axis,
            vertices=data.get('vertices'),
            nb_vertices=data.get('nb_vertices'),
            generation_type=data.get('gen_type'),
            is_hollow=data.get('is_Hollow', False),
            wall_params=wall_params if wall_params else None,
            contactors=data.get('contactors', []),
            mesh_params=data.get('mesh_params'),
        )


@dataclass
class ContactLaw:
    """Représente une loi de contact entre corps"""
    name: str
    law_type: ContactLawType
    friction: Optional[float] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        data = {
            'name': self.name,
            'law': self.law_type.value
        }
        if self.friction is not None:
            data['fric'] = self.friction
        data.update(self.properties)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ContactLaw':
        """Crée un ContactLaw depuis un dictionnaire"""
        props = {k: v for k, v in data.items() if k not in ['name', 'law', 'fric']}
        return cls(
            name=data['name'],
            law_type=ContactLawType(data['law']),
            friction=data.get('fric'),
            properties=props
        )


@dataclass
class VisibilityRule:
    """Règle de visibilité pour la détection de contacts"""
    candidate_body: str
    candidate_contactor: str
    candidate_color: str
    antagonist_body: str
    antagonist_contactor: str
    antagonist_color: str
    behavior_name: str
    alert: float = 0.1
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            'CorpsCandidat': self.candidate_body,
            'candidat': self.candidate_contactor,
            'colorCandidat': self.candidate_color,
            'CorpsAntagoniste': self.antagonist_body,
            'antagoniste': self.antagonist_contactor,
            'colorAntagoniste': self.antagonist_color,
            'behav': self.behavior_name,
            'alert': self.alert
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VisibilityRule':
        """Crée depuis un dictionnaire"""
        return cls(
            candidate_body=data['CorpsCandidat'],
            candidate_contactor=data['candidat'],
            candidate_color=data['colorCandidat'],
            antagonist_body=data['CorpsAntagoniste'],
            antagonist_contactor=data['antagoniste'],
            antagonist_color=data['colorAntagoniste'],
            behavior_name=data['behav'],
            alert=data['alert']
        )


@dataclass
class DOFOperation:
    """
    Opération sur les degrés de liberté (conditions aux limites).

    `target_value` :
        - si target_type == 'avatar' : contient désormais l'avatar_id
          (str) de l'avatar visé (et non plus sa position).
        - si target_type == 'group'  : contient le nom du groupe (str),
          inchangé.
    Aucun changement de signature n'était nécessaire ici : `target_value`
    était déjà typé `Any` et contenait déjà un `str` dans le cas 'group' ;
    seul le contenu sémantique du cas 'avatar' change (int -> str).
    """
    operation_type: str  # translate, rotate, imposeDrivenDof, imposeInitValue
    target_type: str  # 'avatar' ou 'group'
    target_value: Any  # avatar_id (str) ou nom de groupe (str)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            'type': self.operation_type,
            'target': self.target_type,
            'target_value': self.target_value,
            'params': convert_to_serializable(self.parameters)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DOFOperation':
        """Crée depuis un dictionnaire (compatible ancien format)"""
        # Compatibilité ancien format
        if 'body_index' in data:
            return cls(
                operation_type=data['type'],
                target_type='avatar',
                target_value=data['body_index'],
                parameters=data.get('params', {})
            )
        elif 'group_name' in data:
            return cls(
                operation_type=data['type'],
                target_type='group',
                target_value=data['group_name'],
                parameters=data.get('params', {})
            )
        else:
            return cls(
                operation_type=data['type'],
                target_type=data.get('target', 'avatar'),
                target_value=data.get('target_value', 0),
                parameters=data.get('params', {})
            )


@dataclass
class Loop:
    """
    Configuration d'une boucle de génération d'avatars.

    `model_avatar_id` (avant : `model_avatar_index`) référence l'avatar
    modèle par son id stable plutôt que par sa position.
    `generated_ids` (avant : `generated_indices`) référence de la même
    façon les avatars produits par cette boucle.
    """
    loop_type: str  # Cercle, Grille, Ligne, Spirale, Manuel
    model_avatar_id: str
    count: int
    radius: float = 0.0
    step: float = 0.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    spiral_factor: float = 0.0
    invert_axis: bool = False
    group_name: Optional[str] = None
    generated_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            'type': self.loop_type,
            'model_avatar_id': self.model_avatar_id,
            'count': self.count,
            'radius': self.radius,
            'step': self.step,
            'offset_x': self.offset_x,
            'offset_y': self.offset_y,
            'spiral_factor': self.spiral_factor,
            'invert_axis': self.invert_axis,
            'stored_in_group': self.group_name,
            'generated_avatar_ids': self.generated_ids,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Loop':
        """
        Crée depuis un dictionnaire.

        Attend le NOUVEAU format ('model_avatar_id' / 'generated_avatar_ids').
        La traduction depuis l'ancien format positionnel
        ('model_avatar_index' / 'generated_avatar_indices') est effectuée
        EN AMONT par `ProjectState._migrate_legacy_avatar_refs()`, qui a
        accès à la liste des avatars pour résoudre position -> id avant
        d'appeler cette méthode.
        """
        return cls(
            loop_type=data['type'],
            model_avatar_id=data['model_avatar_id'],
            count=data['count'],
            radius=data.get('radius', 0.0),
            step=data.get('step', 0.0),
            offset_x=data.get('offset_x', 0.0),
            offset_y=data.get('offset_y', 0.0),
            spiral_factor=data.get('spiral_factor', 0.0),
            invert_axis=data.get('invert_axis', False),
            group_name=data.get('stored_in_group'),
            generated_ids=data.get('generated_avatar_ids', [])
        )

@dataclass
class ForLoop:
    """
    Configuration d'une boucle for générique.

    `generated_refs` (avant : `generated_indices`) contient :
        - des avatar_id (str)   si target_type == 'avatar'
        - des positions (int)   si target_type in ('material', 'model')
          (ces deux derniers cas restent positionnels : le refactor
          "id stable" ne concerne que les avatars).
    """
    loop_var: str
    start_expr: str
    end_expr: str
    step_expr: str = "1"
    target_type: str = "avatar"
    template_config: dict = field(default_factory=dict)
    group_name: str = None
    generated_refs: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'loop_var': self.loop_var,
            'start_expr': self.start_expr,
            'end_expr': self.end_expr,
            'step_expr': self.step_expr,
            'target_type': self.target_type,
            'template_config': self.template_config,
            'group_name': self.group_name,
            'generated_refs': self.generated_refs,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ForLoop':
        # 'generated_refs' = nouveau format. 'generated_indices' = alias
        # legacy accepté en lecture directe UNIQUEMENT pour les ForLoop
        # dont target_type n'est pas 'avatar' (material/model restent
        # positionnels, donc aucune migration n'est nécessaire pour eux).
        # Pour target_type == 'avatar', la migration positions -> ids est
        # effectuée en amont par ProjectState._migrate_legacy_avatar_refs().
        refs = data.get('generated_refs')
        if refs is None:
            refs = data.get('generated_indices', [])
        return cls(
            loop_var=data['loop_var'],
            start_expr=data['start_expr'],
            end_expr=data['end_expr'],
            step_expr=data.get('step_expr', '1'),
            target_type=data['target_type'],
            template_config=data.get('template_config', {}),
            group_name=data.get('group_name'),
            generated_refs=refs,
        )

@dataclass
class GranuloGeneration:
    """
    Configuration d'une génération granulométrique.

    `generated_ids` (avant : `generated_indices`) référence les avatars
    produits par leur id stable plutôt que leur position.
    """
    nb_particles: int
    radius_min: float
    radius_max: float
    container_type: str  # Box2D, Disk2D, Couette2D, Drum2D
    container_params: Dict[str, float]
    model_name: str
    material_name: str
    avatar_type: str
    color: str = "BLUEx"
    seed: Optional[int] = None
    group_name: Optional[str] = None
    generated_ids: List[str] = field(default_factory=list)
    use_particle_population: bool = False
    population_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            'nb': self.nb_particles,
            'rmin': self.radius_min,
            'rmax': self.radius_max,
            'container_params': {
                'type': self.container_type,
                **self.container_params
            },
            'model': self.model_name,
            'material': self.material_name,
            'avatar_type': self.avatar_type,
            'color': self.color,
            'seed': self.seed,
            'stored_in_group': self.group_name,
            'avatar_ids': self.generated_ids,
            'use_particle_population': self.use_particle_population,
            'population_id': self.population_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GranuloGeneration':
        """
        Crée depuis un dictionnaire.
        Attend le nouveau format ('avatar_ids'). La traduction depuis
        l'ancien format positionnel ('avatar_indices') est effectuée en
        amont par ProjectState._migrate_legacy_avatar_refs().
        """
        container = data.get('container_params', {})
        return cls(
            nb_particles=data['nb'],
            radius_min=data['rmin'],
            radius_max=data['rmax'],
            container_type=container.get('type', 'Box2D'),
            container_params={k: v for k, v in container.items() if k != 'type'},
            model_name=data.get('model', data.get('mod_name', 'rigid')),
            material_name=data.get('material', data.get('mat_name', 'TDURx')),
            avatar_type=data.get('avatar_type', 'rigidDisk'),
            color=data.get('color', 'BLUEx'),
            seed=data.get('seed'),
            group_name=data.get('stored_in_group'),
            generated_ids=data.get('avatar_ids', []),
            use_particle_population=data.get('use_particle_population', False),
            population_id=data.get('population_id'),
        )


@dataclass
class PostProCommand:
    """
    Commande de post-traitement.

    `target_value` : contient désormais l'avatar_id (str) quand
    target_type == 'avatar' (au lieu de la position). Pas de changement
    de signature (déjà typé Any), contenu de groupe (str) inchangé.
    """
    name: str
    step: int
    target_type: Optional[str] = None  # None, 'avatar', 'group'
    target_value: Optional[Any] = None  # avatar_id (str) ou nom de groupe (str)
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        data = {
            'name': self.name,
            'step': self.step
        }
        if self.target_type and self.target_value is not None:
            data['target_info'] = {
                'type': self.target_type,
                'value': self.target_value
            }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PostProCommand':
        """Crée depuis un dictionnaire"""
        target_info = data.get('target_info')
        return cls(
            name=data['name'],
            step=data['step'],
            target_type=target_info['type'] if target_info else None,
            target_value=target_info['value'] if target_info else None
        )

@dataclass
class ProjectPreferences:
    """Préférences du projet"""
    default_project_path: Optional[Path] = None
    unit_system: UnitSystem = UnitSystem.SI
    auto_save: bool = True
    auto_save_interval: int = 300  # secondes
    backup_enabled: bool = True
    recent_projects: List[Path] = field(default_factory=list)
    max_recent_projects: int = 10
    show_granulo_individually: bool = True
    create_pylmgc_on_generate: bool = True

    script_use_loop:bool = True

    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            'default_project_path': str(self.default_project_path) if self.default_project_path else None,
            'unit_system': self.unit_system.value,
            'auto_save': self.auto_save,
            'auto_save_interval': self.auto_save_interval,
            'backup_enabled': self.backup_enabled,
            'recent_projects': [str(p) for p in self.recent_projects],
            'max_recent_projects': self.max_recent_projects,
            'show_granulo_individually': self.show_granulo_individually,
            'create_pylmgc_on_generate': self.create_pylmgc_on_generate,
            'script_use_loop': self.script_use_loop,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectPreferences':
        """Crée depuis un dictionnaire"""
        return cls(
            default_project_path=Path(data['default_project_path']) if data.get('default_project_path') else None,
            unit_system=UnitSystem(data.get('unit_system', 'SI')),
            auto_save=data.get('auto_save', True),
            auto_save_interval=data.get('auto_save_interval', 300),
            backup_enabled=data.get('backup_enabled', True),
            recent_projects=[Path(p) for p in data.get('recent_projects', [])],
            max_recent_projects=data.get('max_recent_projects', 10),
            show_granulo_individually=data.get('show_granulo_individually', True),
            create_pylmgc_on_generate=data.get('create_pylmgc_on_generate', True),
            script_use_loop=data.get('script_use_loop', True),
        )
    
    def get_unit_labels(self) -> Dict[str, str]:
        """Retourne les labels d'unités selon le système"""
        if self.unit_system == UnitSystem.SI:
            return {
                'length': 'm',
                'mass': 'kg',
                'time': 's',
                'force': 'N',
                'pressure': 'Pa',
                'energy': 'J',
                'density': 'kg/m³',
                'velocity': 'm/s',
                'acceleration': 'm/s²',
            }
        else:  # CGS
            return {
                'length': 'cm',
                'mass': 'g',
                'time': 's',
                'force': 'dyn',
                'pressure': 'Ba',
                'energy': 'erg',
                'density': 'g/cm³',
                'velocity': 'cm/s',
                'acceleration': 'cm/s²',
            }

@dataclass
class ProjectState:
    """
    État complet du projet.
    Contient toutes les données du modèle LMGC90.

    `avatar_groups` : Dict[str, List[str]] — les listes contiennent
    désormais des avatar_id (str) et non plus des positions (int).
        `particle_populations` : populations de particules générées en masse
    (SoA — granulo, factory, boucles massives), en complément de `avatars`
    (AoS) qui reste réservé aux éléments peu nombreux et édités
    individuellement. Introduit à l'étape 2 du refactor ParticlePopulation
    — pas encore utilisé par les mixins existants (granulo_mixin.py continue
    de peupler `avatars` pour l'instant, migration prévue à l'étape 4).
    """
    name: str
    dimension: int = 2
    units: Dict[str, str] = field(default_factory=dict)
    preferences: ProjectPreferences = field(default_factory= ProjectPreferences)   
    materials: List[Material] = field(default_factory=list)
    models: List[Model] = field(default_factory=list)
    avatars: List[Avatar] = field(default_factory=list)
    particle_populations: List[Any] = field(default_factory=list)  # List[ParticlePopulation]
    populations_groups: Dict[str, List[str]] = field(default_factory=dict)  # group_name -> list of population_ids
    custom_templates: Dict[int, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
    contact_laws: List[ContactLaw] = field(default_factory=list)
    visibility_rules: List[VisibilityRule] = field(default_factory=list)
    operations: List[DOFOperation] = field(default_factory=list)
    loops: List[Loop] = field(default_factory=list)
    for_loops: List[ForLoop] = field(default_factory=list)
    granulo_generations: List[GranuloGeneration] = field(default_factory=list)
    postpro_commands: List[PostProCommand] = field(default_factory=list)
    factories: List[dict] = field(default_factory=list)  # FactoryConfig sérialisés
    avatar_groups: Dict[str, List[str]] = field(default_factory=dict)
    dynamic_vars: Dict[str, Any] = field(default_factory=dict)
    # Patterns de maçonnerie générés par masonry_wizard — persistés pour que
    # script_generator._write_masonry_pattern_loop() puisse reconstruire les
    # boucles structurées (Standard, Running Bond, etc.) sans tomber en
    # fallback "liste de centers".
    masonry_patterns: Dict[str, Any] = field(default_factory=dict)
    # Avertissements non bloquants accumulés au chargement (régénération,
    # migration d'anciennes références positionnelles, etc.)
    load_warnings: List[str] = field(default_factory=list)

    # Version du format de fichier .lmgc90. Incrémentée à 2 avec
    # l'introduction des avatar_id stables. Les fichiers sans ce champ
    # (ou avec une valeur < 2) sont considérés "legacy" et passent par
    # _migrate_legacy_avatar_refs() à la lecture.
    FILE_FORMAT_VERSION = 2

    def to_dict(self) -> Dict:
        """Convertit l'état complet en dictionnaire pour sauvegarde JSON"""
        manual_avatars = [a for a in self.avatars if a.origin == AvatarOrigin.MANUAL]
        
        return {
            'file_format_version': self.FILE_FORMAT_VERSION,
            'project_name': self.name,
            'dimension': self.dimension,
            'units': self.units,
            'preferences': self.preferences.to_dict(),
            'materials': [m.to_dict() for m in self.materials],
            'models': [m.to_dict() for m in self.models],
            'avatars': [a.to_dict() for a in manual_avatars],
            'particle_populations': [p.to_dict() for p in self.particle_populations],
            'populations_groups': self.populations_groups,
            'custom_templates': self.custom_templates,
            'contact_laws': [c.to_dict() for c in self.contact_laws],
            'visibility_rules': [v.to_dict() for v in self.visibility_rules],
            'operations': [o.to_dict() for o in self.operations],
            'loops': [l.to_dict() for l in self.loops],
            'for_loops': [fl.to_dict() for fl in self.for_loops],
            'granulo_generations': [g.to_dict() for g in self.granulo_generations],
            'postpro_creations': [p.to_dict() for p in self.postpro_commands],
            'factories': self.factories,
            'avatar_groups': self.avatar_groups,
            'dynamic_vars': self.dynamic_vars,
            'masonry_patterns': self.masonry_patterns,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectState':
        """Crée un état complet depuis un dictionnaire."""

        from .particle_population import ParticlePopulation  # Importer ici pour éviter les dépendances circulaires
        prefs_data = data.get('preferences', {})
        preferences = ProjectPreferences.from_dict(prefs_data) if prefs_data else ProjectPreferences()

        # 1. Construire les avatars MANUAL d'abord : à ce stade, leur ORDRE
        #    dans `data['avatars']` correspond exactement à leur position
        #    d'origine au moment de la sauvegarde (cf. to_dict()).
        avatars = [Avatar.from_dict(a) for a in data.get('avatars', [])]

        # 1bis. Réparer d'éventuels avatar_id dupliqués hérités d'anciennes
        #       versions (bug duplicate_avatar/duplicate_group corrigé —
        #       voir _repair_duplicate_avatar_ids). Doit tourner AVANT toute
        #       résolution de référence (migration legacy ou non), sinon les
        #       références utilisant l'ancien id dupliqué pointeraient de
        #       façon ambiguë vers plusieurs avatars.
        avatars, dup_warnings = cls._repair_duplicate_avatar_ids(avatars, data)

        file_version = data.get('file_format_version', 1)
        load_warnings: List[str] = list(dup_warnings)

        if file_version < cls.FILE_FORMAT_VERSION:
            # Fichier "legacy" : les références (avatar_groups, loops,
            # operations, postpro, granulo, for_loops) utilisent encore des
            # positions entières. On les traduit en avatar_id quand c'est
            # possible (cf. docstring de _migrate_legacy_avatar_refs).
            data, extra_warnings = cls._migrate_legacy_avatar_refs(data, avatars)
            load_warnings.extend(extra_warnings)

        # Chargement défensif des populations : un fichier corrompu sur UNE
        # population ne doit pas empêcher le chargement du reste du projet
        # (cohérent avec la philosophie load_warnings déjà en place).
        particle_populations = []
        for i, pop_data in enumerate(data.get('particle_populations', [])):
            try:
                particle_populations.append(ParticlePopulation.from_dict(pop_data))
            except Exception as e:
                load_warnings.append(
                    f"Population de particules #{i + 1} : chargement échoué "
                    f"({e}) — population ignorée."
                )

        state = cls(
            name=data.get('project_name', 'Projet'),
            dimension=data.get('dimension', 2),
            units=data.get('units', {}),
            preferences=preferences,
            materials=[Material.from_dict(m) for m in data.get('materials', [])],
            models=[Model.from_dict(m) for m in data.get('models', [])],
            avatars=avatars,
            particle_populations=particle_populations,
            populations_groups=data.get('populations_groups', data.get('population_groups', {})),
            contact_laws=[ContactLaw.from_dict(c) for c in data.get('contact_laws', [])],
            visibility_rules=[VisibilityRule.from_dict(v) for v in data.get('visibility_rules', [])],
            operations=[DOFOperation.from_dict(o) for o in data.get('operations', [])],
            loops=[Loop.from_dict(l) for l in data.get('loops', [])],
            for_loops=[ForLoop.from_dict(fl) for fl in data.get('for_loops', [])],
            granulo_generations=[GranuloGeneration.from_dict(g) for g in data.get('granulo_generations', [])],
            postpro_commands=[PostProCommand.from_dict(p) for p in data.get('postpro_creations', [])],
            factories=data.get('factories', []),
            avatar_groups=data.get('avatar_groups', {}),
            custom_templates=data.get('custom_templates', {}),
            dynamic_vars=data.get('dynamic_vars', {}),
            masonry_patterns=data.get('masonry_patterns', {}),
        )
        state.load_warnings = load_warnings
        return state

    # =========================================================================
    # Migration des anciens fichiers (positions -> avatar_id)
    # =========================================================================

    @staticmethod
    def _migrate_legacy_avatar_refs(data: Dict, manual_avatars: List['Avatar']
                                     ) -> tuple[Dict, List[str]]:
        """
        Traduit les références positionnelles d'un ancien fichier .lmgc90
        en avatar_id, partout où c'est possible.

        Pourquoi "partout où c'est possible" et pas "partout" :
        au moment où cette fonction tourne, on dispose UNIQUEMENT des
        avatars d'origine MANUAL (`manual_avatars`, dans leur ordre de
        création original). Les avatars générés par les boucles / la
        granulométrie / les boucles for n'existent pas encore : ils sont
        recréés plus tard par
        `ProjectController._rebuild_pylmgc_objects()`, dans cet ordre
        précis : matériaux, modèles, avatars manuels, PUIS boucles, PUIS
        granulométrie, PUIS boucles for.

        Cet ordre garantit qu'au moment de la sauvegarde ET au moment du
        rechargement, les avatars manuels occupent toujours les positions
        [0 .. len(manual_avatars)-1]. Toute référence ancienne dont la
        valeur entière est < len(manual_avatars) désigne donc forcément un
        avatar manuel et peut être traduite en avatar_id de façon fiable.

        En revanche, une référence ancienne >= len(manual_avatars) désigne
        un avatar généré (boucle/granulo/for_loop) qui n'existe pas encore
        à cet instant : elle est IRRÉCUPÉRABLE ici. Dans ce cas, on
        supprime la référence orpheline et on ajoute un avertissement
        explicite dans `load_warnings`, plutôt que de produire une donnée
        fausse silencieusement.

        Retourne (data_migré, liste_d_avertissements).
        """
        warnings: List[str] = []
        n_manual = len(manual_avatars)

        def pos_to_id(pos: int) -> Optional[str]:
            if isinstance(pos, str):
                # Déjà un id (fichier partiellement migré à la main) : on
                # le laisse passer tel quel.
                return pos
            if isinstance(pos, int) and 0 <= pos < n_manual:
                return manual_avatars[pos].avatar_id
            return None

        # ── avatar_groups : Dict[str, List[int|str]] ────────────────────────
        old_groups = data.get('avatar_groups', {}) or {}
        new_groups: Dict[str, List[str]] = {}
        for grp_name, refs in old_groups.items():
            kept: List[str] = []
            for ref in refs:
                aid = pos_to_id(ref)
                if aid is not None:
                    kept.append(aid)
                else:
                    warnings.append(
                        f"Groupe '{grp_name}' : référence à l'avatar généré "
                        f"#{ref} introuvable lors de la migration (sera "
                        f"reconstituée si la boucle/granulo source est "
                        f"toujours présente dans le projet, sinon perdue)."
                    )
            new_groups[grp_name] = kept
        data['avatar_groups'] = new_groups

        # ── loops : 'model_avatar_index' -> 'model_avatar_id' ───────────────
        for i, loop_d in enumerate(data.get('loops', [])):
            if 'model_avatar_id' not in loop_d and 'model_avatar_index' in loop_d:
                aid = pos_to_id(loop_d['model_avatar_index'])
                if aid is None:
                    warnings.append(
                        f"Boucle #{i + 1} : avatar modèle #"
                        f"{loop_d['model_avatar_index']} introuvable "
                        f"(devait être un avatar manuel) — boucle ignorée "
                        f"au rechargement."
                    )
                    aid = ''  # Loop.from_dict() exige une str ; sera invalide
                loop_d['model_avatar_id'] = aid
            if 'generated_avatar_ids' not in loop_d:
                # Les anciens indices générés seront re-générés de toute
                # façon par generate_loop() ; on ne tente pas de les migrer.
                loop_d['generated_avatar_ids'] = []

        # ── granulo_generations : 'avatar_indices' -> 'avatar_ids' ──────────
        for gran_d in data.get('granulo_generations', []):
            if 'avatar_ids' not in gran_d:
                # Régénérés par generate_granulo() au chargement -> liste
                # vide acceptable, aucune perte d'information utile.
                gran_d['avatar_ids'] = []

        # ── for_loops : 'generated_indices' -> 'generated_refs' ─────────────
        for fl_d in data.get('for_loops', []):
            if 'generated_refs' not in fl_d and 'generated_indices' in fl_d:
                if fl_d.get('target_type') == 'avatar':
                    # Régénérés par generate_for_loop() au chargement.
                    fl_d['generated_refs'] = []
                else:
                    # material/model : restent positionnels, aucune
                    # traduction nécessaire.
                    fl_d['generated_refs'] = fl_d['generated_indices']

        # ── operations (DOF) : target_value avatar -> avatar_id ─────────────
        for i, op_d in enumerate(data.get('operations', [])):
            if op_d.get('target') == 'avatar':
                old_val = op_d.get('target_value')
                aid = pos_to_id(old_val)
                if aid is None:
                    warnings.append(
                        f"Opération DOF #{i + 1} ({op_d.get('type')}) : "
                        f"avatar cible #{old_val} introuvable (généré par "
                        f"boucle/granulo, non résolvable à la migration) — "
                        f"opération ignorée."
                    )
                    aid = '__unresolved__'
                op_d['target_value'] = aid

        # ── postpro_creations : target_value avatar -> avatar_id ────────────
        for i, pp_d in enumerate(data.get('postpro_creations', [])):
            target_info = pp_d.get('target_info')
            if target_info and target_info.get('type') == 'avatar':
                old_val = target_info.get('value')
                aid = pos_to_id(old_val)
                if aid is None:
                    warnings.append(
                        f"Commande post-pro '{pp_d.get('name')}' : avatar "
                        f"cible #{old_val} introuvable à la migration — "
                        f"cible retirée (commande conservée en mode global)."
                    )
                    pp_d['target_info'] = None
                else:
                    target_info['value'] = aid

        return data, warnings

    # =========================================================================
    # Réparation des avatar_id dupliqués (héritage duplicate_avatar/duplicate_group)
    # =========================================================================

    @staticmethod
    def _repair_duplicate_avatar_ids(
        avatars: List['Avatar'], data: Dict
    ) -> tuple[List['Avatar'], List[str]]:
        """
        Détecte et répare les avatar_id dupliqués parmi les avatars MANUAL
        chargés depuis un fichier .lmgc90.

        Contexte : avant correctif, AvatarsMixin.duplicate_avatar() et
        duplicate_group() faisaient un copy.deepcopy(source) sans réassigner
        avatar_id — chaque clone héritait donc du MÊME id que son original
        (default_factory=new_avatar_id ne s'exécute qu'à la construction
        initiale, pas lors d'un deepcopy). Les fichiers .lmgc90 sauvegardés
        avant ce correctif peuvent donc contenir des avatars MANUAL distincts
        partageant le même avatar_id.

        Pour chaque id dupliqué : on conserve l'avatar rencontré en premier
        tel quel, et on assigne un NOUVEL id stable aux occurrences
        suivantes. Toute référence à l'ancien id dupliqué DANS CE MÊME
        FICHIER (avatar_groups, loops, operations, postpro_creations,
        granulo_generations, for_loops) reste donc valide pour la première
        occurrence, mais peut désigner un avatar différent de celui visé à
        l'origine par les copies suivantes — c'est un compromis inévitable :
        le fichier source ne permet pas de distinguer laquelle des
        occurrences dupliquées était réellement visée par chaque référence
        historique. Un avertissement explicite est ajouté par id réparé
        pour que l'utilisateur puisse vérifier les groupes concernés.

        Retourne (avatars_corrigés, avertissements).
        """
        seen: Dict[str, int] = {}   # avatar_id -> index de la première occurrence
        warnings: List[str] = []

        for i, av in enumerate(avatars):
            if av.avatar_id not in seen:
                seen[av.avatar_id] = i
                continue

            # Doublon détecté : réassigner un nouvel id stable
            old_id = av.avatar_id
            new_id = new_avatar_id()
            av.avatar_id = new_id

            warnings.append(
                f"Avatar #{i} ({av.avatar_type.value}) partageait le même "
                f"identifiant que l'avatar #{seen[old_id]} — corrigé "
                f"automatiquement (nouvel id assigné). Si cet avatar avait "
                f"été dupliqué via 'Dupliquer avatar/groupe' avant une "
                f"mise à jour de l'application, vérifiez que les groupes et "
                f"conditions aux limites qui le concernent sont toujours "
                f"corrects."
            )

        return avatars, warnings