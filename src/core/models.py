"""
Modèles de données pour LMGC90_GUI.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from pathlib import Path


def convert_to_serializable(obj):
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


class ValidationError(Exception):
    pass


class MaterialType(Enum):
    RIGID = "RIGID"
    ELAS = "ELAS"
    ELAS_DILA = "ELAS_DILA"
    VISCO_ELAS = "VISCO_ELAS"
    ELAS_PLAS = "ELAS_PLAS"
    THERMO_ELAS = "THERMO_ELAS"
    PORO_ELAS = "PORO_ELAS"


class AvatarType(Enum):
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
    RIGID_SPHERE = "rigidSphere"
    RIGID_PLAN = "rigidPlan"
    RIGID_CYLINDER = "rigidCylinder"
    RIGID_POLYHEDRON = "rigidPolyhedron"
    ROUGH_WALL_3D = "roughWall3D"
    GRANULO_ROUGH_WALL_3D = "granuloRoughWall3D"


class ContactLawType(Enum):
    IQS_CLB = "IQS_CLB"
    IQS_CLB_G0 = "IQS_CLB_g0"
    COUPLED_DOF = "COUPLED_DOF"
    IQS_DS_CLB = "IQS_DS_CLB"
    IQS_MOHR_DS_CLB = "IQS_MOHR_DS_CLB"
    IQS_MAC_CZM = "IQS_MAC_CZM"
    ELASTIC_WIRE = "ELASTIC_WIRE"
    ELASTIC_REPELL_CLB = "ELASTIC_REPELL_CLB"


class AvatarOrigin(Enum):
    MANUAL = "manual"
    LOOP = "loop"
    GRANULO = "granulo"


class UnitSystem(Enum):
    SI = "SI"
    CGS = "CGS"


@dataclass
class Material:
    name: str
    material_type: MaterialType
    density: float
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'type': self.material_type.value,
            'density': self.density,
            'props': self.properties
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Material':
        return cls(
            name=data['name'],
            material_type=MaterialType(data['type']),
            density=data['density'],
            properties=data.get('props', {})
        )


@dataclass
class Model:
    name: str
    physics: str
    element: str
    dimension: int
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        result = {
            'name': self.name,
            'physics': self.physics,
            'element': self.element,
            'dimension': self.dimension
        }
        result.update(self.options)
        return result

    @classmethod
    def from_dict(cls, data: Dict) -> 'Model':
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
    avatar_type: AvatarType
    center: List[float]
    material_name: str
    model_name: str
    color: str = "BLUEx"
    origin: AvatarOrigin = AvatarOrigin.MANUAL
    controller: Any = field(repr=False, default=None)

    radius: Optional[float] = None
    axis: Optional[Dict[str, float]] = None
    vertices: Optional[List[List[float]]] = None
    nb_vertices: Optional[int] = None
    generation_type: Optional[str] = None
    is_hollow: bool = False
    wall_params: Optional[Dict[str, Any]] = None
    contactors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        data = {
            'type': self.avatar_type.value,
            'center': convert_to_serializable(self.center),
            'material': self.material_name,
            'model': self.model_name,
            'color': self.color,
            '__origin': self.origin.value
        }
        if self.radius is not None:
            if self.avatar_type not in [AvatarType.RIGID_POLYGON, AvatarType.RIGID_POLYHEDRON]:
                data['r'] = self.radius
            else:
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
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'Avatar':
        axis = None
        if 'axe1' in data and 'axe2' in data:
            axis = {'axe1': data['axe1'], 'axe2': data['axe2']}
            if 'axe3' in data:
                axis['axe3'] = data['axe3']

        # FIX: center peut ne pas être une liste
        center = data['center']
        if not isinstance(center, list):
            center = list(center)

        wall_keys = ['l', 'h', 'r', 'rmin', 'rmax', 'nb_vertex', 'nb_polyg', 'lx', 'ly', 'lz', 'ra', 'rb', 'faces']
        wall_params = {k: data[k] for k in wall_keys if k in data}

        return cls(
            avatar_type=AvatarType(data['type']),
            center=center,
            material_name=data['material'],
            model_name=data['model'],
            color=data.get('color', 'BLUEx'),
            origin=AvatarOrigin(data.get('__origin', 'manual')),
            radius=data.get('r') or data.get('radius'),
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
    name: str
    law_type: ContactLawType
    friction: Optional[float] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        data = {'name': self.name, 'law': self.law_type.value}
        if self.friction is not None:
            data['fric'] = self.friction
        data.update(self.properties)
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'ContactLaw':
        props = {k: v for k, v in data.items() if k not in ['name', 'law', 'fric']}
        return cls(
            name=data['name'],
            law_type=ContactLawType(data['law']),
            friction=data.get('fric'),
            properties=props
        )


@dataclass
class VisibilityRule:
    candidate_body: str
    candidate_contactor: str
    candidate_color: str
    antagonist_body: str
    antagonist_contactor: str
    antagonist_color: str
    behavior_name: str
    alert: float = 0.1

    def to_dict(self) -> Dict:
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
    operation_type: str
    target_type: str
    target_value: Any
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'type': self.operation_type,
            'target': self.target_type,
            'target_value': self.target_value,
            'params': convert_to_serializable(self.parameters)
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DOFOperation':
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
    loop_type: str
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
class ForLoop:
    loop_var: str
    start_expr: str
    end_expr: str
    step_expr: str = "1"
    target_type: str = "avatar"
    template_config: dict = field(default_factory=dict)
    group_name: str = None
    generated_indices: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'loop_var': self.loop_var,
            'start_expr': self.start_expr,
            'end_expr': self.end_expr,
            'step_expr': self.step_expr,
            'target_type': self.target_type,
            'template_config': self.template_config,
            'group_name': self.group_name,
            'generated_indices': self.generated_indices
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ForLoop':
        return cls(
            loop_var=data['loop_var'],
            start_expr=data['start_expr'],
            end_expr=data['end_expr'],
            step_expr=data.get('step_expr', '1'),
            target_type=data['target_type'],
            template_config=data.get('template_config', {}),
            group_name=data.get('group_name'),
            generated_indices=data.get('generated_indices', [])
        )


@dataclass
class GranuloGeneration:
    nb_particles: int
    radius_min: float
    radius_max: float
    container_type: str
    container_params: Dict[str, float]
    model_name: str
    material_name: str
    avatar_type: str
    color: str = "BLUEx"
    seed: Optional[int] = None
    group_name: Optional[str] = None
    generated_indices: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict:
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
    name: str
    step: int
    target_type: Optional[str] = None
    target_value: Optional[Any] = None

    def to_dict(self) -> Dict:
        data = {'name': self.name, 'step': self.step}
        if self.target_type and self.target_value is not None:
            data['target_info'] = {
                'type': self.target_type,
                'value': self.target_value
            }
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'PostProCommand':
        target_info = data.get('target_info')
        return cls(
            name=data['name'],
            step=data['step'],
            target_type=target_info['type'] if target_info else None,
            target_value=target_info['value'] if target_info else None
        )


@dataclass
class ProjectPreferences:
    default_project_path: Optional[Path] = None
    unit_system: UnitSystem = UnitSystem.SI
    auto_save: bool = True
    auto_save_interval: int = 300
    backup_enabled: bool = True
    recent_projects: List[Path] = field(default_factory=list)
    max_recent_projects: int = 10
    show_granulo_individually: bool = True
    create_pylmgc_on_generate: bool = True

    def to_dict(self) -> Dict:
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
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectPreferences':
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
        )

    def get_unit_labels(self) -> Dict[str, str]:
        if self.unit_system == UnitSystem.SI:
            return {
                'length': 'm', 'mass': 'kg', 'time': 's',
                'force': 'N', 'pressure': 'Pa', 'energy': 'J',
                'density': 'kg/m³', 'velocity': 'm/s', 'acceleration': 'm/s²',
            }
        else:
            return {
                'length': 'cm', 'mass': 'g', 'time': 's',
                'force': 'dyn', 'pressure': 'Ba', 'energy': 'erg',
                'density': 'g/cm³', 'velocity': 'cm/s', 'acceleration': 'cm/s²',
            }


@dataclass
class ProjectState:
    name: str
    dimension: int = 2
    units: Dict[str, str] = field(default_factory=dict)
    preferences: ProjectPreferences = field(default_factory=ProjectPreferences)
    materials: List[Material] = field(default_factory=list)
    models: List[Model] = field(default_factory=list)
    avatars: List[Avatar] = field(default_factory=list)
    custom_templates: Dict[int, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
    contact_laws: List[ContactLaw] = field(default_factory=list)
    visibility_rules: List[VisibilityRule] = field(default_factory=list)
    operations: List[DOFOperation] = field(default_factory=list)
    loops: List[Loop] = field(default_factory=list)
    for_loops: List[ForLoop] = field(default_factory=list)  # FIX: champ manquant
    granulo_generations: List[GranuloGeneration] = field(default_factory=list)
    postpro_commands: List[PostProCommand] = field(default_factory=list)
    avatar_groups: Dict[str, List[int]] = field(default_factory=dict)
    dynamic_vars: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        manual_avatars = [a for a in self.avatars if a.origin == AvatarOrigin.MANUAL]
        return {
            'project_name': self.name,
            'dimension': self.dimension,
            'units': self.units,
            'preferences': self.preferences.to_dict(),
            'materials': [m.to_dict() for m in self.materials],
            'models': [m.to_dict() for m in self.models],
            'avatars': [a.to_dict() for a in manual_avatars],
            'custom_templates': self.custom_templates,
            'contact_laws': [c.to_dict() for c in self.contact_laws],
            'visibility_rules': [v.to_dict() for v in self.visibility_rules],
            'operations': [o.to_dict() for o in self.operations],
            'loops': [l.to_dict() for l in self.loops],
            'for_loops': [fl.to_dict() for fl in self.for_loops],  # FIX: persisté
            'granulo_generations': [g.to_dict() for g in self.granulo_generations],
            'postpro_creations': [p.to_dict() for p in self.postpro_commands],
            'avatar_groups': self.avatar_groups,
            'dynamic_vars': self.dynamic_vars
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProjectState':
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
            for_loops=[ForLoop.from_dict(fl) for fl in data.get('for_loops', [])],  # FIX
            granulo_generations=[GranuloGeneration.from_dict(g) for g in data.get('granulo_generations', [])],
            postpro_commands=[PostProCommand.from_dict(p) for p in data.get('postpro_creations', [])],
            avatar_groups=data.get('avatar_groups', {}),
            dynamic_vars=data.get('dynamic_vars', {})
        )