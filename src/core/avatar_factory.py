
"""
Factory pour créer des avatars prédéfinis .
"""
from typing import List, Dict, Any, Optional
from .models import Avatar, AvatarType, AvatarOrigin
import math


class AvatarTemplate:
    """Template d'avatar avec paramètres"""
    
    def __init__(self, name: str, description: str, avatar_type: AvatarType,
                 default_params: Dict[str, Any], param_schema: Dict[str, Dict]):
        self.name = name
        self.description = description
        self.avatar_type = avatar_type
        self.default_params = default_params
        self.param_schema = param_schema  # {'param_name': {'type': float, 'min': 0, 'max': 10}}
    
    def create(self, center: List[float], material: str, model: str,
               color: str = "BLUEx", **custom_params) -> Avatar:
        """Crée un avatar depuis le template"""
        params = self.default_params.copy()
        params.update(custom_params)
        
        return Avatar(
            avatar_type=self.avatar_type,
            center=center,
            material_name=material,
            model_name=model,
            color=color,
            origin=AvatarOrigin.MANUAL,
            **params
        )


class AvatarFactory:
    """Factory pour créer des avatars complexes"""
    
    # ========== TEMPLATES 2D ==========
    
    TEMPLATES_2D = {
        # Particules simples
        "disk_small": AvatarTemplate(
            name="Petit Disque",
            description="Disque de rayon 0.05m",
            avatar_type=AvatarType.RIGID_DISK,
            default_params={'radius': 0.05},
            param_schema={'radius': {'type': float, 'min': 0.001, 'max': 10.0}}
        ),
        
        "disk_medium": AvatarTemplate(
            name="Disque Moyen",
            description="Disque de rayon 0.1m",
            avatar_type=AvatarType.RIGID_DISK,
            default_params={'radius': 0.1},
            param_schema={'radius': {'type': float, 'min': 0.001, 'max': 10.0}}
        ),
        
        "disk_large": AvatarTemplate(
            name="Grand Disque",
            description="Disque de rayon 0.2m",
            avatar_type=AvatarType.RIGID_DISK,
            default_params={'radius': 0.2},
            param_schema={'radius': {'type': float, 'min': 0.001, 'max': 10.0}}
        ),
        
        # Formes allongées
        "cylinder_horizontal": AvatarTemplate(
            name="Cylindre Horizontal",
            description="Jonc allongé horizontalement (2:1)",
            avatar_type=AvatarType.RIGID_JONC,
            default_params={'axis': {'axe1': 0.2, 'axe2': 0.1}},
            param_schema={
                'axe1': {'type': float, 'min': 0.001, 'max': 10.0},
                'axe2': {'type': float, 'min': 0.001, 'max': 10.0}
            }
        ),
        
        "cylinder_vertical": AvatarTemplate(
            name="Cylindre Vertical",
            description="Jonc allongé verticalement (1:2)",
            avatar_type=AvatarType.RIGID_JONC,
            default_params={'axis': {'axe1': 0.1, 'axe2': 0.2}},
            param_schema={
                'axe1': {'type': float, 'min': 0.001, 'max': 10.0},
                'axe2': {'type': float, 'min': 0.001, 'max': 10.0}
            }
        ),
        
        # Polygones réguliers
        "triangle": AvatarTemplate(
            name="Triangle",
            description="Triangle équilatéral",
            avatar_type=AvatarType.RIGID_POLYGON,
            default_params={
                'generation_type': 'regular',
                'nb_vertices': 3,
                'radius': 0.1
            },
            param_schema={
                'radius': {'type': float, 'min': 0.001, 'max': 10.0}
            }
        ),
        
        "square": AvatarTemplate(
            name="Carré",
            description="Carré régulier",
            avatar_type=AvatarType.RIGID_POLYGON,
            default_params={
                'generation_type': 'regular',
                'nb_vertices': 4,
                'radius': 0.1
            },
            param_schema={
                'radius': {'type': float, 'min': 0.001, 'max': 10.0}
            }
        ),
        
        "pentagon": AvatarTemplate(
            name="Pentagone",
            description="Pentagone régulier",
            avatar_type=AvatarType.RIGID_POLYGON,
            default_params={
                'generation_type': 'regular',
                'nb_vertices': 5,
                'radius': 0.1
            },
            param_schema={
                'radius': {'type': float, 'min': 0.001, 'max': 10.0}
            }
        ),
        
        "hexagon": AvatarTemplate(
            name="Hexagone",
            description="Hexagone régulier",
            avatar_type=AvatarType.RIGID_POLYGON,
            default_params={
                'generation_type': 'regular',
                'nb_vertices': 6,
                'radius': 0.1
            },
            param_schema={
                'radius': {'type': float, 'min': 0.001, 'max': 10.0}
            }
        ),
        
        # Formes spéciales
        "rectangle": AvatarTemplate(
            name="Rectangle",
            description="Rectangle personnalisé",
            avatar_type=AvatarType.RIGID_POLYGON,
            default_params={
                'generation_type': 'full',
                'vertices': [[-0.15, -0.05], [0.15, -0.05], [0.15, 0.05], [-0.15, 0.05]],
                'radius': 0.15
            },
            param_schema={}
        ),
        
        # Murs
        "wall_horizontal": AvatarTemplate(
            name="Mur Horizontal",
            description="Mur horizontal lisse",
            avatar_type=AvatarType.SMOOTH_WALL,
            default_params={
                'wall_params': {'l': 2.0, 'h': 0.1, 'nb_polyg': 20}
            },
            param_schema={
                'l': {'type': float, 'min': 0.1, 'max': 100.0},
                'h': {'type': float, 'min': 0.01, 'max': 10.0}
            }
        ),
    }
    
    # ========== TEMPLATES 3D ==========
    
    TEMPLATES_3D = {
        "sphere_small": AvatarTemplate(
            name="Petite Sphère",
            description="Sphère de rayon 0.05m",
            avatar_type=AvatarType.RIGID_SPHERE,
            default_params={'radius': 0.05},
            param_schema={'radius': {'type': float, 'min': 0.001, 'max': 10.0}}
        ),
        
        "sphere_medium": AvatarTemplate(
            name="Sphère Moyenne",
            description="Sphère de rayon 0.1m",
            avatar_type=AvatarType.RIGID_SPHERE,
            default_params={'radius': 0.1},
            param_schema={'radius': {'type': float, 'min': 0.001, 'max': 10.0}}
        ),
        
        "sphere_large": AvatarTemplate(
            name="Grande Sphère",
            description="Sphère de rayon 0.2m",
            avatar_type=AvatarType.RIGID_SPHERE,
            default_params={'radius': 0.2},
            param_schema={'radius': {'type': float, 'min': 0.001, 'max': 10.0}}
        ),
        
        "cylinder_3d": AvatarTemplate(
            name="Cylindre 3D",
            description="Cylindre droit",
            avatar_type=AvatarType.RIGID_CYLINDER,
            default_params={
                'radius': 0.05,
                'wall_params': {'h': 0.2}
            },
            param_schema={
                'radius': {'type': float, 'min': 0.001, 'max': 10.0},
                'h': {'type': float, 'min': 0.001, 'max': 10.0}
            }
        ),
        
        "plan_floor": AvatarTemplate(
            name="Plan Sol",
            description="Plan horizontal (sol)",
            avatar_type=AvatarType.RIGID_PLAN,
            default_params={},
            param_schema={}
        ),
    }
    
    # ========== ASSEMBLAGES COMPLEXES ==========
    
    @staticmethod
    def create_cluster_2d(center: List[float], material: str, model: str,
                         nb_disks: int = 5, main_radius: float = 0.1,
                         color: str = "BLUEx") -> Avatar:
        """Crée un cluster de disques"""
        return Avatar(
            avatar_type=AvatarType.RIGID_CLUSTER,
            center=center,
            material_name=material,
            model_name=model,
            color=color,
            origin=AvatarOrigin.MANUAL,
            radius=main_radius,
            nb_vertices=nb_disks
        )
    
    @staticmethod
    def create_dumbbell_2d(center: List[float], material: str, model: str,
                          length: float = 0.3, disk_radius: float = 0.05,
                          color: str = "BLUEx") -> List[Avatar]:
        """Crée un haltère (2 disques reliés)"""
        # Note: Nécessite emptyAvatar avec contacteurs personnalisés
        half_length = length / 2
        
        contactors = [
            {
                'shape': 'DISKx',
                'color': color,
                'params': {'byrd': disk_radius, 'coor': [-half_length, 0.0]}
            },
            {
                'shape': 'DISKx',
                'color': color,
                'params': {'byrd': disk_radius, 'coor': [half_length, 0.0]}
            },
            {
                'shape': 'JONCx',
                'color': color,
                'params': {'axe1': length, 'axe2': disk_radius * 0.3}
            }
        ]
        
        return Avatar(
            avatar_type=AvatarType.EMPTY_AVATAR,
            center=center,
            material_name=material,
            model_name=model,
            color=color,
            origin=AvatarOrigin.MANUAL,
            contactors=contactors
        )
    
    @staticmethod
    def create_box_container_2d(width: float, height: float, wall_thickness: float,
                               center: List[float], material: str, model: str,
                               color: str = "GRAYx") -> List[Avatar]:
        """Crée une boîte rectangulaire (3 murs)"""
        walls = []
        
        # Mur bas
        walls.append(Avatar(
            avatar_type=AvatarType.SMOOTH_WALL,
            center=[center[0], center[1] - height/2],
            material_name=material,
            model_name=model,
            color=color,
            origin=AvatarOrigin.MANUAL,
            wall_params={'l': width, 'h': wall_thickness, 'nb_polyg': 20}
        ))
        
        # Mur gauche
        walls.append(Avatar(
            avatar_type=AvatarType.SMOOTH_WALL,
            center=[center[0] - width/2, center[1]],
            material_name=material,
            model_name=model,
            color=color,
            origin=AvatarOrigin.MANUAL,
            wall_params={'l': wall_thickness, 'h': height, 'nb_polyg': 20}
        ))
        
        # Mur droit
        walls.append(Avatar(
            avatar_type=AvatarType.SMOOTH_WALL,
            center=[center[0] + width/2, center[1]],
            material_name=material,
            model_name=model,
            color=color,
            origin=AvatarOrigin.MANUAL,
            wall_params={'l': wall_thickness, 'h': height, 'nb_polyg': 20}
        ))
        
        return walls
    
    @staticmethod
    def create_hopper_2d(top_width: float, bottom_width: float, height: float,
                        center: List[float], material: str, model: str,
                        color: str = "GRAYx") -> List[Avatar]:
        """Crée une trémie en V"""
        # Calcul des vertices pour les parois inclinées
        half_top = top_width / 2
        half_bot = bottom_width / 2
        
        # Paroi gauche
        left_wall = Avatar(
            avatar_type=AvatarType.RIGID_POLYGON,
            center=[center[0] - (half_top + half_bot) / 2, center[1]],
            material_name=material,
            model_name=model,
            color=color,
            origin=AvatarOrigin.MANUAL,
            generation_type='full',
            vertices=[
                [-half_top, height/2],
                [-half_bot, -height/2],
                [-half_bot + 0.1, -height/2],
                [-half_top + 0.1, height/2]
            ],
            radius=(half_top - half_bot) / 2
        )
        
        # Paroi droite (symétrique)
        right_wall = Avatar(
            avatar_type=AvatarType.RIGID_POLYGON,
            center=[center[0] + (half_top + half_bot) / 2, center[1]],
            material_name=material,
            model_name=model,
            color=color,
            origin=AvatarOrigin.MANUAL,
            generation_type='full',
            vertices=[
                [half_bot - 0.1, -height/2],
                [half_bot, -height/2],
                [half_top, height/2],
                [half_top - 0.1, height/2]
            ],
            radius=(half_top - half_bot) / 2
        )
        
        return [left_wall, right_wall]
    
    # ========== MÉTHODES UTILITAIRES ==========
    
    @staticmethod
    def get_template(template_name: str, dimension: int) -> Optional[AvatarTemplate]:
        """Récupère un template par nom"""
        templates = AvatarFactory.TEMPLATES_2D if dimension == 2 else AvatarFactory.TEMPLATES_3D
        return templates.get(template_name)
    
    @staticmethod
    def list_templates(dimension: int) -> Dict[str, AvatarTemplate]:
        """Liste tous les templates disponibles"""
        return AvatarFactory.TEMPLATES_2D if dimension == 2 else AvatarFactory.TEMPLATES_3D
    
    @staticmethod
    def get_categories(dimension: int) -> Dict[str, List[str]]:
        """Retourne les templates organisés par catégorie"""
        templates = AvatarFactory.list_templates(dimension)
        
        if dimension == 2:
            return {
                "Particules Simples": ["disk_small", "disk_medium", "disk_large"],
                "Formes Allongées": ["cylinder_horizontal", "cylinder_vertical"],
                "Polygones": ["triangle", "square", "pentagon", "hexagon", "rectangle"],
                "Murs": ["wall_horizontal"],
            }
        else:  # 3D
            return {
                "Particules Simples": ["sphere_small", "sphere_medium", "sphere_large"],
                "Formes 3D": ["cylinder_3d", "plan_floor"],
            }