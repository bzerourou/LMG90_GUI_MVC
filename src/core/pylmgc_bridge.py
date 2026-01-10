# ============================================================================
# Pont vers pylmgc90
# ============================================================================
"""
Pont entre nos modèles et les objets pylmgc90.
Gère la conversion et la création d'objets LMGC90.
"""
import numpy as np
from typing import Dict, List, Any
from pylmgc90 import pre

from .models import (
    Material, Model, Avatar, ContactLaw, VisibilityRule, 
    DOFOperation, AvatarType, MaterialType, ContactLawType
)


class LMGC90Bridge:
    """Convertit entre nos modèles et pylmgc90"""
    
    @staticmethod
    def create_material(material: Material) -> Any:
        """Crée un objet material pylmgc90"""
        mat_type = material.material_type.value
        
        if mat_type in ["RIGID", "ELAS", "ELAS_DILA", "VISCO_ELAS", 
                        "ELAS_PLAS", "THERMO_ELAS", "PORO_ELAS"]:
            return pre.material(
                name=material.name,
                materialType=mat_type,
                density=material.density,
                **material.properties
            )
        else:
            raise ValueError(f"Type de matériau non supporté: {mat_type}")
    
    @staticmethod
    def create_model(model: Model) -> Any:
        """Crée un objet model pylmgc90"""
        if model.element in ["Rxx2D", "Rxx3D"]:
            return pre.model(
                name=model.name,
                physics=model.physics,
                element=model.element,
                dimension=model.dimension
            )
        else:
            return pre.model(
                name=model.name,
                physics=model.physics,
                element=model.element,
                dimension=model.dimension,
                **model.options
            )
    
    @staticmethod
    def create_avatar(avatar: Avatar, model_obj: Any, material_obj: Any) -> Any:
        """
        Crée un objet avatar pylmgc90.
        
        Args:
            avatar: Modèle d'avatar
            model_obj: Objet model pylmgc90
            material_obj: Objet material pylmgc90
            
        Returns:
            Objet avatar pylmgc90
        """
        atype = avatar.avatar_type
        center = avatar.center
        color = avatar.color
        
        # Création selon le type
        # 2D avatars
        if atype == AvatarType.RIGID_DISK:
            kwargs = {
                'r': avatar.radius,
                'center': center,
                'model': model_obj,
                'material': material_obj,
                'color': color
            }
            if avatar.is_hollow:
                kwargs['is_Hollow'] = True
            return pre.rigidDisk(**kwargs)
        
        elif atype == AvatarType.RIGID_JONC:
            return pre.rigidJonc(
                axe1=avatar.axis['axe1'],
                axe2=avatar.axis['axe2'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        
        elif atype == AvatarType.RIGID_POLYGON:
            if avatar.generation_type == "regular":
                return pre.rigidPolygon(
                    model=model_obj,
                    material=material_obj,
                    center=center,
                    color=color,
                    generation_type=avatar.generation_type,
                    nb_vertices=avatar.nb_vertices,
                    radius=avatar.radius
                )
            else:
                return pre.rigidPolygon(
                    model=model_obj,
                    material=material_obj,
                    center=center,
                    color=color,
                    generation_type=avatar.generation_type,
                    vertices=np.array(avatar.vertices, dtype=float),
                    radius=avatar.radius
                )
        
        elif atype == AvatarType.RIGID_OVOID:
            return pre.rigidOvoidPolygon(
                ra=avatar.wall_params['ra'],
                rb=avatar.wall_params['rb'],
                nb_vertices=avatar.nb_vertices,
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        
        elif atype == AvatarType.RIGID_DISCRETE:
            return pre.rigidDiscreteDisk(
                r=avatar.radius,
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        
        elif atype == AvatarType.RIGID_CLUSTER:
            return pre.rigidCluster(
                r=avatar.radius,
                center=center,
                model=model_obj,
                material=material_obj,
                color=color,
                nb_disk=avatar.nb_vertices
            )
        
        elif atype == AvatarType.ROUGH_WALL:
            return pre.roughWall(
                l=avatar.wall_params['l'],
                r=avatar.wall_params['r'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color,
                nb_vertex=avatar.wall_params.get('nb_vertex', 10)
            )
        
        elif atype == AvatarType.FINE_WALL:
            return pre.fineWall(
                l=avatar.wall_params['l'],
                r=avatar.wall_params['r'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color,
                nb_vertex=avatar.wall_params.get('nb_vertex', 10)
            )
        
        elif atype == AvatarType.SMOOTH_WALL:
            return pre.smoothWall(
                l=avatar.wall_params['l'],
                h=avatar.wall_params['h'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color,
                nb_polyg=avatar.wall_params.get('nb_polyg', 10)
            )
        
        elif atype == AvatarType.GRANULO_WALL:
            return pre.granuloRoughWall(
                l=avatar.wall_params['l'],
                rmin=avatar.wall_params['rmin'],
                rmax=avatar.wall_params['rmax'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color,
                nb_vertex=avatar.wall_params.get('nb_vertex', 10)
            )
        
        elif atype == AvatarType.EMPTY_AVATAR:
            # Avatar vide avec contacteurs personnalisés
            body = pre.avatar(dimension=len(center))
            
            # Bulk
            if len(center) == 2:
                body.addBulk(pre.rigid2d())
            else:
                body.addBulk(pre.rigid3d())
            
            # Node principal
            body.addNode(pre.node(coor=np.array(center), number=1))
            
            # Configuration
            body.defineGroups()
            body.defineModel(model=model_obj)
            body.defineMaterial(material=material_obj)
            
            # Contacteurs
            for cont in avatar.contactors:
                shape = cont['shape']
                color_c = cont.get('color', color)
                params = cont.get('params', {})
                
                body.addContactors(
                    shape=shape,
                    color=color_c,
                    **params
                )
            
            # Calcul des propriétés rigides
            body.computeRigidProperties()
            
            return body
        
        # Avatars 3D
        elif atype == AvatarType.RIGID_SPHERE:
            return pre.rigidSphere(
                r=avatar.radius,
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
    
        elif atype == AvatarType.RIGID_PLAN:
            return pre.rigidPlan(
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        
        elif atype == AvatarType.RIGID_CYLINDER:
            return pre.rigidCylinder(
                r=avatar.radius,
                h=avatar.wall_params.get('h', 1.0) if avatar.wall_params else 1.0,
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        
        elif atype == AvatarType.RIGID_POLYHEDRON:
            return pre.rigidPolyhedron(
                vertices=np.array(avatar.vertices) if avatar.vertices else np.array([]),
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        
        elif atype == AvatarType.ROUGH_WALL_3D:
            return pre.roughWall3D(
                l=avatar.wall_params['l'],
                r=avatar.wall_params['r'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )
        
        elif atype == AvatarType.GRANULO_ROUGH_WALL_3D:
            return pre.granuloRoughWall3D(
                l=avatar.wall_params['l'],
                rmin=avatar.wall_params['rmin'],
                rmax=avatar.wall_params['rmax'],
                center=center,
                model=model_obj,
                material=material_obj,
                color=color
            )

        
        else:
            raise ValueError(f"Type d'avatar non supporté: {atype}")
    
    @staticmethod
    def create_contact_law(law: ContactLaw) -> Any:
        """Crée une loi de contact pylmgc90"""
        if law.law_type in [ContactLawType.IQS_CLB, ContactLawType.IQS_CLB_G0]:
            return pre.tact_behav(
                name=law.name,
                law=law.law_type.value,
                fric=law.friction
            )
        else:
            return pre.tact_behav(
                name=law.name,
                law=law.law_type.value
            )
    
    @staticmethod
    def create_visibility_rule(rule: VisibilityRule, behavior_obj: Any) -> Any:
        """Crée une table de visibilité pylmgc90"""
        return pre.see_table(
            CorpsCandidat=rule.candidate_body,
            candidat=rule.candidate_contactor,
            colorCandidat=rule.candidate_color,
            CorpsAntagoniste=rule.antagonist_body,
            antagoniste=rule.antagonist_contactor,
            colorAntagoniste=rule.antagonist_color,
            behav=behavior_obj,
            alert=rule.alert
        )
    
    @staticmethod
    def apply_dof_operation(operation: DOFOperation, avatar_obj: Any) -> None:
        """
        Applique une opération DOF sur un avatar pylmgc90.
        
        Args:
            operation: Opération à appliquer
            avatar_obj: Objet avatar pylmgc90
        """
        getattr(avatar_obj, operation.operation_type)(**operation.parameters)

