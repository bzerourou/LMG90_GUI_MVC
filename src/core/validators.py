# ============================================================================
# Validation des données
# ============================================================================
"""
Validateurs pour les modèles de données.
Séparation de la logique de validation.
"""
from typing import Tuple
from .models import Material, Model, Avatar, ContactLaw


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
    
    @staticmethod
    def validate(avatar: Avatar, dimension: int) -> Tuple[bool, str]:
        """
        Valide un avatar.
        
        Args:
            avatar: Avatar à valider
            dimension: Dimension du modèle (2 ou 3)
            
        Returns:
            (is_valid, error_message)
        """
        if len(avatar.center) != dimension:
            return False, f"Le centre doit avoir {dimension} coordonnées (actuellement {len(avatar.center)})"
        
        if not avatar.material_name or not avatar.model_name:
            return False, "Matériau et modèle requis"
        
        # Validation spécifique selon le type
        from .models import AvatarType
        
        if avatar.avatar_type in [AvatarType.RIGID_DISK, AvatarType.RIGID_DISCRETE, 
                                  AvatarType.RIGID_CLUSTER]:
            if avatar.radius is None or avatar.radius <= 0:
                return False, f"Rayon positif requis pour {avatar.avatar_type.value}"
        
        if avatar.avatar_type == AvatarType.RIGID_JONC:
            if not avatar.axis or 'axe1' not in avatar.axis or 'axe2' not in avatar.axis:
                return False, "Axes axe1 et axe2 requis pour rigidJonc"
        
        if avatar.avatar_type == AvatarType.RIGID_POLYGON:
            if avatar.generation_type == "regular":
                if not avatar.nb_vertices or avatar.nb_vertices < 3:
                    return False, "nb_vertices >= 3 requis pour polygone régulier"
            else:
                if not avatar.vertices or len(avatar.vertices) < 3:
                    return False, "Au moins 3 vertices requis"
        
        return True, ""
    
    @staticmethod
    def validate_or_raise(avatar: Avatar, dimension: int) -> None:
        """Valide ou lève une exception"""
        is_valid, error = AvatarValidator.validate(avatar, dimension)
        if not is_valid:
            raise ValidationError(error)


class ContactLawValidator:
    """Valide les lois de contact"""
    
    @staticmethod
    def validate(law: ContactLaw) -> Tuple[bool, str]:
        """Valide une loi de contact"""
        if not law.name or not law.name.strip():
            return False, "Le nom de la loi ne peut pas être vide"
        
        from .models import ContactLawType
        if law.law_type in [ContactLawType.IQS_CLB, ContactLawType.IQS_CLB_G0]:
            if law.friction is None:
                return False, f"Friction requise pour {law.law_type.value}"
            if law.friction < 0:
                return False, "Le coefficient de friction doit être positif"
        
        return True, ""
    
    @staticmethod
    def validate_or_raise(law: ContactLaw) -> None:
        """Valide ou lève une exception"""
        is_valid, error = ContactLawValidator.validate(law)
        if not is_valid:
            raise ValidationError(error)

