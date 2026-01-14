"""
Modèles de données pour LMGC90_GUI.
Représentation pure des objets sans logique UI (Model dans MVC).
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from pathlib import Path



# ============================================================================
# EXCEPTIONS - Erreurs personnalisées
# ============================================================================

class ValidationError(Exception):
    """
    Exception levée lors d'une erreur de validation de données.
    Utilisée par les validateurs pour signaler des données invalides.
    """
    pass


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
    # 3D
    RIGID_SPHERE = "rigidSphere"
    RIGID_PLAN = "rigidPlan"
    RIGID_CYLINDER = "rigidCylinder"
    RIGID_POLYHEDRON = "rigidPolyhedron"
    ROUGH_WALL_3D = "roughWall3D"
    GRANULO_ROUGH_WALL_3D = "granuloRoughWall3D"
    
class ContactLawType(Enum):
    """Types de lois de contact"""
    IQS_CLB = "IQS_CLB"
    IQS_CLB_G0 = "IQS_CLB_g0"
    COUPLED_DOF = "COUPLED_DOF"


class AvatarOrigin(Enum):
    """Origine de création d'un avatar"""
    MANUAL = "manual"      # Créé manuellement
    LOOP = "loop"          # Généré par une boucle
    GRANULO = "granulo"    # Généré par granulométrie


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
    """
    avatar_type: AvatarType
    center: List[float]
    material_name: str
    model_name: str
    color: str = "BLUEx"
    origin: AvatarOrigin = AvatarOrigin.MANUAL
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
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour sérialisation"""
        data = {
            'type': self.avatar_type.value,
            'center': self.center,
            'material': self.material_name,
            'model': self.model_name,
            'color': self.color,
            '__origin': self.origin.value
        }
        
        # Ajouter les champs non-None
        if self.radius is not None:
            data['r'] = self.radius
        
        if self.axis:
            data['axe1'] = self.axis['axe1']
            data['axe2'] = self.axis['axe2']
            if self.controller.state.dimension == 3 and 'axe3' in self.axis:
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
            data.update(self.wall_params)
        
        if self.contactors:
            data['contactors'] = self.contactors
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Avatar':
        """Crée un Avatar depuis un dictionnaire"""
        # Reconstruire axis si présent
        axis = None
        if 'axe1' in data and 'axe2' in data:
            axis = {'axe1': data['axe1'], 'axe2': data['axe2']}
        
        # Reconstruire wall_params
        wall_keys = ['l', 'h', 'r', 'rmin', 'rmax', 'nb_vertex', 'nb_polyg']
        wall_params = {k: data[k] for k in wall_keys if k in data}
        
        return cls(
            avatar_type=AvatarType(data['type']),
            center=data['center'],
            material_name=data['material'],
            model_name=data['model'],
            color=data.get('color', 'BLUEx'),
            origin=AvatarOrigin(data.get('__origin', 'manual')),
            radius=data.get('r'),
            axis=axis,
            vertices=data.get('vertices'),
            nb_vertices=data.get('nb_vertices'),
            generation_type=data.get('gen_type'),
            is_hollow=data.get('is_Hollow', False),
            wall_params=wall_params if wall_params else None,
            contactors=data.get('contactors', [])
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
    """Opération sur les degrés de liberté (conditions aux limites)"""
    operation_type: str  # translate, rotate, imposeDrivenDof, imposeInitValue
    target_type: str  # 'avatar' ou 'group'
    target_value: Any  # index d'avatar ou nom de groupe
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            'type': self.operation_type,
            'target': self.target_type,
            'target_value': self.target_value,
            'params': self.parameters
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
    """Configuration d'une boucle de génération d'avatars"""
    loop_type: str  # Cercle, Grille, Ligne, Spirale, Manuel
    model_avatar_index: int
    count: int
    radius: float = 0.0
    step: float = 0.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    spiral_factor: float = 0.0
    invert_axis: bool = False
    group_name: Optional[str] = None
    generated_indices: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            'type': self.loop_type,
            'model_avatar_index': self.model_avatar_index,
            'count': self.count,
            'radius': self.radius,
            'step': self.step,
            'offset_x': self.offset_x,
            'offset_y': self.offset_y,
            'spiral_factor': self.spiral_factor,
            'invert_axis': self.invert_axis,
            'stored_in_group': self.group_name,
            'generated_avatar_indices': self.generated_indices
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Loop':
        """Crée depuis un dictionnaire"""
        return cls(
            loop_type=data['type'],
            model_avatar_index=data['model_avatar_index'],
            count=data['count'],
            radius=data.get('radius', 0.0),
            step=data.get('step', 0.0),
            offset_x=data.get('offset_x', 0.0),
            offset_y=data.get('offset_y', 0.0),
            spiral_factor=data.get('spiral_factor', 0.0),
            invert_axis=data.get('invert_axis', False),
            group_name=data.get('stored_in_group'),
            generated_indices=data.get('generated_avatar_indices', [])
        )


@dataclass
class GranuloGeneration:
    """Configuration d'une génération granulométrique"""
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
    generated_indices: List[int] = field(default_factory=list)
    
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
            'avatar_indices': self.generated_indices
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GranuloGeneration':
        """Crée depuis un dictionnaire"""
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
            generated_indices=data.get('avatar_indices', [])
        )


@dataclass
class PostProCommand:
    """Commande de post-traitement"""
    name: str
    step: int
    target_type: Optional[str] = None  # None, 'avatar', 'group'
    target_value: Optional[Any] = None  # index ou nom
    
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
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            'default_project_path': str(self.default_project_path) if self.default_project_path else None,
            'unit_system': self.unit_system.value,
            'auto_save': self.auto_save,
            'auto_save_interval': self.auto_save_interval,
            'backup_enabled': self.backup_enabled,
            'recent_projects': [str(p) for p in self.recent_projects],
            'max_recent_projects': self.max_recent_projects
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
            max_recent_projects=data.get('max_recent_projects', 10)
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
    """
    name: str
    dimension: int = 2
    units: Dict[str, str] = field(default_factory=dict)
    preferences: ProjectPreferences = field(default_factory= ProjectPreferences)   
    materials: List[Material] = field(default_factory=list)
    models: List[Model] = field(default_factory=list)
    avatars: List[Avatar] = field(default_factory=list)
    custom_templates: Dict[int, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
    contact_laws: List[ContactLaw] = field(default_factory=list)
    visibility_rules: List[VisibilityRule] = field(default_factory=list)
    operations: List[DOFOperation] = field(default_factory=list)
    loops: List[Loop] = field(default_factory=list)
    granulo_generations: List[GranuloGeneration] = field(default_factory=list)
    postpro_commands: List[PostProCommand] = field(default_factory=list)
    avatar_groups: Dict[str, List[int]] = field(default_factory=dict)
    dynamic_vars: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convertit l'état complet en dictionnaire pour sauvegarde JSON"""
        # Ne sauvegarder que les avatars manuels (pas ceux générés)
        manual_avatars = [a for a in self.avatars if a.origin == AvatarOrigin.MANUAL]
        
        return {
            'project_name': self.name,
            'dimension': self.dimension,
            'units': self.units,
            'preferences': self.preferences.to_dict(),
            'materials': [m.to_dict() for m in self.materials],
            'models': [m.to_dict() for m in self.models],
            'avatars': [a.to_dict() for a in manual_avatars],
            'contact_laws': [c.to_dict() for c in self.contact_laws],
            'visibility_rules': [v.to_dict() for v in self.visibility_rules],
            'operations': [o.to_dict() for o in self.operations],
            'loops': [l.to_dict() for l in self.loops],
            'granulo_generations': [g.to_dict() for g in self.granulo_generations],
            'postpro_creations': [p.to_dict() for p in self.postpro_commands],
            'avatar_groups': self.avatar_groups,
            'dynamic_vars': self.dynamic_vars
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectState':
        """Crée un état complet depuis un dictionnaire"""
        prefs_data = data.get('preferences', {})
        preferences = ProjectPreferences.from_dict(prefs_data) if prefs_data else ProjectPreferences()
        return cls(
            name=data.get('project_name', 'Projet'),
            dimension=data.get('dimension', 2),
            units=data.get('units', {}),
            preferences=preferences,
            materials=[Material.from_dict(m) for m in data.get('materials', [])],
            models=[Model.from_dict(m) for m in data.get('models', [])],
            avatars=[Avatar.from_dict(a) for a in data.get('avatars', [])],
            contact_laws=[ContactLaw.from_dict(c) for c in data.get('contact_laws', [])],
            visibility_rules=[VisibilityRule.from_dict(v) for v in data.get('visibility_rules', [])],
            operations=[DOFOperation.from_dict(o) for o in data.get('operations', [])],
            loops=[Loop.from_dict(l) for l in data.get('loops', [])],
            granulo_generations=[GranuloGeneration.from_dict(g) for g in data.get('granulo_generations', [])],
            postpro_commands=[PostProCommand.from_dict(p) for p in data.get('postpro_creations', [])],
            avatar_groups=data.get('avatar_groups', {}),
            dynamic_vars=data.get('dynamic_vars', {})
        )
    
