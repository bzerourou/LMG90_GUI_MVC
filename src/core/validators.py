# ============================================================================
# Validation des données
# ============================================================================
"""
Validateurs pour les modèles de données.
"""
from typing import Tuple
from .models import Material, Model, Avatar, ContactLaw, AvatarType


class ValidationError(Exception):
    """Exception levée lors d'une erreur de validation"""
    pass


class MaterialValidator:
    """Valide les données de matériau"""
    
    @staticmethod
    def validate(material: Material) -> Tuple[bool, str]:
        """
        Valide un matériau.
        
        Returns:
            (is_valid, error_message)
        """
        if not material.name or not material.name.strip():
            return False, "Le nom du matériau ne peut pas être vide"
        
        if len(material.name) > 5:
            return False, "Le nom du matériau doit faire maximum 5 caractères"
        
        if material.density <= 0:
            return False, "La densité doit être strictement positive"
        
        return True, ""
    
    @staticmethod
    def validate_or_raise(material: Material) -> None:
        """Valide ou lève une exception"""
        is_valid, error = MaterialValidator.validate(material)
        if not is_valid:
            raise ValidationError(error)


class ModelValidator:
    """Valide les données de modèle"""
    
    VALID_ELEMENTS_2D = ["Rxx2D", "T3xxx", "Q4xxx", "T6xxx", "Q8xxx", "Q9xxx", "BARxx"]
    VALID_ELEMENTS_3D = ["Rxx3D", "H8xxx", "SHB8x", "H20xx", "SHB6x", "TE10x", "DKTxx", "BARxx"]
    
    @staticmethod
    def validate(model: Model) -> Tuple[bool, str]:
        """
        Valide un modèle.
        
        Returns:
            (is_valid, error_message)
        """
        if not model.name or not model.name.strip():
            return False, "Le nom du modèle ne peut pas être vide"
        
        if len(model.name) > 5:
            return False, "Le nom du modèle doit faire maximum 5 caractères"
        
        if model.dimension not in [2, 3]:
            return False, "La dimension doit être 2 ou 3"
        
        valid_elements = (ModelValidator.VALID_ELEMENTS_2D if model.dimension == 2 
                         else ModelValidator.VALID_ELEMENTS_3D)
        
        if model.element not in valid_elements:
            return False, f"Élément '{model.element}' invalide pour dimension {model.dimension}"
        
        return True, ""
    
    @staticmethod
    def validate_or_raise(model: Model) -> None:
        """Valide ou lève une exception"""
        is_valid, error = ModelValidator.validate(model)
        if not is_valid:
            raise ValidationError(error)


class AvatarValidator:
    """Valide les données d'avatar"""
    
    RIGID_AVATARS_2D = {
        AvatarType.RIGID_DISK,
        AvatarType.RIGID_JONC,
        AvatarType.RIGID_POLYGON,
        AvatarType.RIGID_OVOID,
        AvatarType.RIGID_DISCRETE,
        AvatarType.RIGID_CLUSTER,
        AvatarType.ROUGH_WALL,
        AvatarType.FINE_WALL,
        AvatarType.SMOOTH_WALL,
        AvatarType.GRANULO_WALL
    }
    
    RIGID_AVATARS_3D = {
        AvatarType.RIGID_SPHERE,
        AvatarType.RIGID_PLAN,
        AvatarType.RIGID_CYLINDER,
        AvatarType.RIGID_POLYHEDRON,
        AvatarType.ROUGH_WALL_3D,
        AvatarType.GRANULO_ROUGH_WALL_3D
    }
    
    RIGID_ELEMENTS_2D = ["Rxx2D"]
    RIGID_ELEMENTS_3D = ["Rxx3D"]
    
    DEFORMABLE_ELEMENTS_2D = ["T3xxx", "Q4xxx", "T6xxx", "Q8xxx", "Q9xxx", "BARxx"]
    DEFORMABLE_ELEMENTS_3D = ["H8xxx", "SHB8x", "H20xx", "SHB6x", "TE10x", "DKTxx", "BARxx"]
    

    @staticmethod
    def validate(avatar: Avatar, model: Model) -> Tuple[bool, str]:
        """
        Valide un avatar avec son modèle.
        
        Args:
            avatar: Avatar à valider
            model: Modèle associé à l'avatar
            
        Returns:
            (is_valid, error_message)
        """
        dimension = model.dimension
        element = model.element
        
        if len(avatar.center) != dimension:
            return False, f"Le centre doit avoir {dimension} coordonnées (actuellement {len(avatar.center)})"
        
        if not avatar.material_name or not avatar.model_name:
            return False, "Matériau et modèle requis"
        
        atype = avatar.avatar_type
        
        if atype in AvatarValidator.RIGID_AVATARS_2D:
            if dimension != 2:
                return False, f"{atype.value} nécessite un modèle 2D"
            if element not in AvatarValidator.RIGID_ELEMENTS_2D:
                return False, f"{atype.value} nécessite un élément rigide 2D (Rxx2D), pas {element}"
        
        if atype in AvatarValidator.RIGID_AVATARS_3D:
            if dimension != 3:
                return False, f"{atype.value} nécessite un modèle 3D"
            if element not in AvatarValidator.RIGID_ELEMENTS_3D:
                return False, f"{atype.value} nécessite un élément rigide 3D (Rxx3D), pas {element}"
        
        if atype == AvatarType.MESH_DEFORMABLE:
            valid_elements = (AvatarValidator.DEFORMABLE_ELEMENTS_2D if dimension == 2 
                            else AvatarValidator.DEFORMABLE_ELEMENTS_3D)
            if element not in valid_elements:
                return False, f"Élément {element} invalide pour mesh déformable en {dimension}D"
        
        if atype == AvatarType.EMPTY_AVATAR:
            pass
        
        if atype == AvatarType.RIGID_DISK:
            if dimension != 2:
                return False, "rigidDisk est uniquement 2D"
            if avatar.radius is None or avatar.radius <= 0:
                return False, "Rayon positif requis pour rigidDisk"
        
        elif atype == AvatarType.RIGID_JONC:
            if dimension != 2:
                return False, "rigidJonc est uniquement 2D"
            if not avatar.axis or 'axe1' not in avatar.axis or 'axe2' not in avatar.axis:
                return False, "Axes axe1 et axe2 requis pour rigidJonc"
        
        elif atype == AvatarType.RIGID_POLYGON:
            if dimension != 2:
                return False, "rigidPolygon est uniquement 2D"
            if avatar.generation_type == "regular":
                if not avatar.nb_vertices or avatar.nb_vertices < 3:
                    return False, "nb_vertices >= 3 requis pour polygone régulier"
                if avatar.radius is None or avatar.radius <= 0:
                    return False, "Rayon positif requis pour polygone régulier"
            else:
                if not avatar.vertices or len(avatar.vertices) < 3:
                    return False, "Au moins 3 vertices requis pour polygone personnalisé"
        
        elif atype == AvatarType.RIGID_OVOID:
            if dimension != 2:
                return False, "rigidOvoidPolygon est uniquement 2D"
            if not avatar.wall_params:
                return False, "wall_params requis pour rigidOvoidPolygon"
            if 'ra' not in avatar.wall_params or 'rb' not in avatar.wall_params:
                return False, "ra et rb requis dans wall_params pour rigidOvoidPolygon"
            if avatar.wall_params['ra'] <= 0 or avatar.wall_params['rb'] <= 0:
                return False, "ra et rb doivent être positifs"
            if not avatar.nb_vertices or avatar.nb_vertices < 3:
                return False, "nb_vertices >= 3 requis pour rigidOvoidPolygon"
        
        elif atype == AvatarType.RIGID_DISCRETE:
            if dimension != 2:
                return False, "rigidDiscreteDisk est uniquement 2D"
            if avatar.radius is None or avatar.radius <= 0:
                return False, "Rayon positif requis pour rigidDiscreteDisk"
        
        elif atype == AvatarType.RIGID_CLUSTER:
            if dimension != 2:
                return False, "rigidCluster est uniquement 2D"
            if avatar.radius is None or avatar.radius <= 0:
                return False, "Rayon positif requis pour rigidCluster"
            if not avatar.nb_vertices or avatar.nb_vertices < 2:
                return False, "nb_disk >= 2 requis pour rigidCluster"
        
        elif atype == AvatarType.ROUGH_WALL:
            if dimension != 2:
                return False, "roughWall est uniquement 2D"
            if not avatar.wall_params:
                return False, "wall_params requis pour roughWall"
            if 'l' not in avatar.wall_params or 'r' not in avatar.wall_params:
                return False, "l et r requis dans wall_params pour roughWall"
            if avatar.wall_params['l'] <= 0 or avatar.wall_params['r'] <= 0:
                return False, "l et r doivent être positifs"
        
        elif atype == AvatarType.FINE_WALL:
            if dimension != 2:
                return False, "fineWall est uniquement 2D"
            if not avatar.wall_params:
                return False, "wall_params requis pour fineWall"
            if 'l' not in avatar.wall_params or 'r' not in avatar.wall_params:
                return False, "l et r requis dans wall_params pour fineWall"
            if avatar.wall_params['l'] <= 0 or avatar.wall_params['r'] <= 0:
                return False, "l et r doivent être positifs"
        
        elif atype == AvatarType.SMOOTH_WALL:
            if dimension != 2:
                return False, "smoothWall est uniquement 2D"
            if not avatar.wall_params:
                return False, "wall_params requis pour smoothWall"
            if 'l' not in avatar.wall_params or 'h' not in avatar.wall_params:
                return False, "l et h requis dans wall_params pour smoothWall"
            if avatar.wall_params['l'] <= 0 or avatar.wall_params['h'] <= 0:
                return False, "l et h doivent être positifs"
        
        elif atype == AvatarType.GRANULO_WALL:
            if dimension != 2:
                return False, "granuloRoughWall est uniquement 2D"
            if not avatar.wall_params:
                return False, "wall_params requis pour granuloRoughWall"
            required = ['l', 'rmin', 'rmax']
            missing = [k for k in required if k not in avatar.wall_params]
            if missing:
                return False, f"Paramètres manquants pour granuloRoughWall: {', '.join(missing)}"
            if avatar.wall_params['l'] <= 0:
                return False, "l doit être positif"
            if avatar.wall_params['rmin'] <= 0 or avatar.wall_params['rmax'] <= 0:
                return False, "rmin et rmax doivent être positifs"
            if avatar.wall_params['rmin'] > avatar.wall_params['rmax']:
                return False, "rmin doit être <= rmax"
        
        elif atype == AvatarType.RIGID_SPHERE:
            if dimension != 3:
                return False, "rigidSphere est uniquement 3D"
            if avatar.radius is None or avatar.radius <= 0:
                return False, "Rayon positif requis pour rigidSphere"
        
        elif atype == AvatarType.RIGID_PLAN:
            if dimension != 3:
                return False, "rigidPlan est uniquement 3D"
            if not avatar.axis:
                return False, "Axes requis pour rigidPlan"
            required_axes = ['axe1', 'axe2', 'axe3']
            missing = [k for k in required_axes if k not in avatar.axis]
            if missing:
                return False, f"Axes manquants pour rigidPlan: {', '.join(missing)}"
        
        elif atype == AvatarType.RIGID_CYLINDER:
            if dimension != 3:
                return False, "rigidCylinder est uniquement 3D"
            if avatar.radius is None or avatar.radius <= 0:
                return False, "Rayon positif requis pour rigidCylinder"
            if not avatar.wall_params or 'h' not in avatar.wall_params:
                return False, "Hauteur h requise dans wall_params pour rigidCylinder"
            if avatar.wall_params['h'] <= 0:
                return False, "Hauteur h doit être positive"
        
        elif atype == AvatarType.RIGID_POLYHEDRON:
            if dimension != 3:
                return False, "rigidPolyhedron est uniquement 3D"
            if avatar.generation_type == "regular":
                if not avatar.nb_vertices or avatar.nb_vertices < 4:
                    return False, "nb_vertices >= 4 requis pour polyèdre régulier"
                if avatar.radius is None or avatar.radius <= 0:
                    return False, "Rayon positif requis pour polyèdre régulier"
            else:
                if not avatar.vertices or len(avatar.vertices) < 4:
                    return False, "Au moins 4 vertices requis pour polyèdre personnalisé"
                if not avatar.wall_params or 'faces' not in avatar.wall_params:
                    return False, "faces requis dans wall_params pour polyèdre personnalisé"
        
        elif atype == AvatarType.ROUGH_WALL_3D:
            if dimension != 3:
                return False, "roughWall3D est uniquement 3D"
            if not avatar.wall_params:
                return False, "wall_params requis pour roughWall3D"
            required = ['lx', 'ly']
            missing = [k for k in required if k not in avatar.wall_params]
            if missing:
                return False, f"Paramètres manquants pour roughWall3D: {', '.join(missing)}"
            if avatar.wall_params['lx'] <= 0 or avatar.wall_params['ly'] <= 0:
                return False, "lx et ly doivent être positifs"
            if avatar.radius is None or avatar.radius <= 0:
                return False, "Rayon r positif requis pour roughWall3D"
        
        elif atype == AvatarType.GRANULO_ROUGH_WALL_3D:
            if dimension != 3:
                return False, "granuloRoughWall3D est uniquement 3D"
            if not avatar.wall_params:
                return False, "wall_params requis pour granuloRoughWall3D"
            required = ['lx', 'ly', 'rmin', 'rmax']
            missing = [k for k in required if k not in avatar.wall_params]
            if missing:
                return False, f"Paramètres manquants pour granuloRoughWall3D: {', '.join(missing)}"
            if avatar.wall_params['lx'] <= 0 or avatar.wall_params['ly'] <= 0:
                return False, "lx et ly doivent être positifs"
            if avatar.wall_params['rmin'] <= 0 or avatar.wall_params['rmax'] <= 0:
                return False, "rmin et rmax doivent être positifs"
            if avatar.wall_params['rmin'] > avatar.wall_params['rmax']:
                return False, "rmin doit être <= rmax"
        
        elif atype == AvatarType.EMPTY_AVATAR:
            if not avatar.contactors or len(avatar.contactors) == 0:
                return False, "Au moins un contacteur requis pour emptyAvatar"
            for i, cont in enumerate(avatar.contactors):
                if 'shape' not in cont:
                    return False, f"Contacteur {i+1}: 'shape' requis"
        
        elif atype == AvatarType.MESH_DEFORMABLE:
            pass
        
        return True, ""
    
    @staticmethod
    def validate_or_raise(avatar: Avatar, model: Model) -> None:
        """Valide ou lève une exception"""
        is_valid, error = AvatarValidator.validate(avatar, model)
        if not is_valid:
            raise ValidationError(error)


class ContactLawValidator:
    """Valide les lois de contact"""

    # Lois qui nécessitent un coefficient de friction
    _FRICTION_REQUIRED = {
        "IQS_CLB",
        "IQS_CLB_g0",
        "IQS_DS_CLB",
        "IQS_MOHR_DS_CLB",
        "RST_CLB",
        "GAP_SGR_CLB",
        "GAP_SGR_CLB_g0",
        "GAP_MOHR_DS_CLB",
        "ELASTIC_REPELL_CLB",
    }

    # Lois sans friction ni propriétés obligatoires (validation triviale = nom seul)
    _NO_PARAMS = {
        "COUPLED_DOF",
        "NORMAL_COUPLED_DOF",
    }

    # Propriétés obligatoires par type de loi
    _REQUIRED_PROPS = {
        "IQS_DS_CLB":       ["stfr", "dyfr"],
        "IQS_MOHR_DS_CLB":  ["stfr", "dyfr", "cohn", "coht"],
        "IQS_MAC_CZM":      ["stfr", "dyfr", "cn", "ct", "b", "w"],
        "GAP_MOHR_DS_CLB":  ["stfr", "dyfr", "cohn", "coht"],
        "MAC_CZM":          ["stfr", "dyfr", "cn", "ct", "b", "w"],
        "MAL_CZM":          ["stfr", "dyfr", "cn", "ct", "s1", "s2", "G1", "G2"],
        "ELASTIC_WIRE":     ["stiffness", "prestrain"],
        "BRITTLE_ELASTIC_WIRE": ["stiffness", "prestrain", "Fmax"],
        "ELASTIC_ROD":      ["stiffness", "prestrain"],
        "VOIGT_ROD":        ["stiffness", "viscosity", "prestrain"],
        "ELASTIC_REPELL_CLB": ["stiffness"],
        "RST_CLB":          ["rstn", "rstt"],
    }

    @staticmethod
    def validate(law: ContactLaw) -> Tuple[bool, str]:
        """Valide une loi de contact"""
        if not law.name or not law.name.strip():
            return False, "Le nom de la loi ne peut pas être vide"

        law_value = law.law_type.value.strip()

        # Vérification friction
        if law_value in ContactLawValidator._FRICTION_REQUIRED:
            if law.friction is None:
                return False, f"Friction requise pour {law_value}"
            if law.friction < 0:
                return False, f"Le coefficient de friction doit être positif ou nul ({law_value})"

        # Vérification propriétés obligatoires
        required = ContactLawValidator._REQUIRED_PROPS.get(law_value, [])
        missing = [p for p in required if p not in law.properties]
        if missing:
            return False, f"{law_value} nécessite : {', '.join(missing)}"

        return True, ""

    @staticmethod
    def validate_or_raise(law: ContactLaw) -> None:
        """Valide ou lève une exception"""
        is_valid, error = ContactLawValidator.validate(law)
        if not is_valid:
            raise ValidationError(error)