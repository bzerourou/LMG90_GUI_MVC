# ============================================================================
# FICHIER 11: tests/unit/test_validators.py
# Tests unitaires des validateurs
# ============================================================================
"""
Tests unitaires pour les validateurs.
"""
import pytest
from src.core.models import Material, Model, Avatar, MaterialType, AvatarType
from src.core.validators import (
    MaterialValidator, ModelValidator, AvatarValidator, ValidationError
)


class TestMaterialValidator:
    
    def test_valid_material(self, sample_material):
        """Test d'un matériau valide"""
        is_valid, msg = MaterialValidator.validate(sample_material)
        assert is_valid is True
        assert msg == ""
    
    def test_empty_name(self):
        """Test nom vide"""
        mat = Material(
            name="",
            material_type=MaterialType.RIGID,
            density=1000.0
        )
        is_valid, msg = MaterialValidator.validate(mat)
        assert is_valid is False
        assert "vide" in msg.lower()
    
    def test_name_too_long(self):
        """Test nom trop long"""
        mat = Material(
            name="TOOLONG",
            material_type=MaterialType.RIGID,
            density=1000.0
        )
        is_valid, msg = MaterialValidator.validate(mat)
        assert is_valid is False
        assert "5 caractères" in msg.lower() or "maximum" in msg.lower()
    
    def test_negative_density(self):
        """Test densité négative"""
        mat = Material(
            name="TEST",
            material_type=MaterialType.RIGID,
            density=-100.0
        )
        is_valid, msg = MaterialValidator.validate(mat)
        assert is_valid is False
        assert "positive" in msg.lower()
    
    def test_validate_or_raise_success(self, sample_material):
        """Test validate_or_raise sans erreur"""
        MaterialValidator.validate_or_raise(sample_material)
    
    def test_validate_or_raise_error(self):
        """Test validate_or_raise avec erreur"""
        mat = Material(name="", material_type=MaterialType.RIGID, density=1000.0)
        with pytest.raises(ValidationError):
            MaterialValidator.validate_or_raise(mat)


class TestModelValidator:
    
    def test_valid_model_2d(self, sample_model):
        """Test modèle 2D valide"""
        is_valid, msg = ModelValidator.validate(sample_model)
        assert is_valid is True
    
    def test_invalid_dimension(self):
        """Test dimension invalide"""
        mod = Model(name="test", physics="MECAx", element="Rxx2D", dimension=5)
        is_valid, msg = ModelValidator.validate(mod)
        assert is_valid is False
        assert "dimension" in msg.lower()
    
    def test_invalid_element_for_dimension(self):
        """Test élément invalide pour la dimension"""
        mod = Model(name="test", physics="MECAx", element="Rxx3D", dimension=2)
        is_valid, msg = ModelValidator.validate(mod)
        assert is_valid is False


class TestAvatarValidator:
    
    def test_valid_rigid_disk(self):
        """Test rigidDisk valide"""
        avatar = Avatar(
            avatar_type=AvatarType.RIGID_DISK,
            center=[0.0, 0.0],
            material_name="MAT",
            model_name="MOD",
            radius=0.5
        )
        is_valid, msg = AvatarValidator.validate(avatar, dimension=2)
        assert is_valid is True
    
    def test_wrong_center_dimension(self):
        """Test centre avec mauvaise dimension"""
        avatar = Avatar(
            avatar_type=AvatarType.RIGID_DISK,
            center=[0.0, 0.0, 0.0],  # 3D pour un modèle 2D
            material_name="MAT",
            model_name="MOD",
            radius=0.5
        )
        is_valid, msg = AvatarValidator.validate(avatar, dimension=2)
        assert is_valid is False
        assert "coordonnées" in msg.lower()
    
    def test_missing_radius_for_disk(self):
        """Test rayon manquant pour disque"""
        avatar = Avatar(
            avatar_type=AvatarType.RIGID_DISK,
            center=[0.0, 0.0],
            material_name="MAT",
            model_name="MOD"
            # pas de radius !
        )
        is_valid, msg = AvatarValidator.validate(avatar, dimension=2)
        assert is_valid is False
        assert "rayon" in msg.lower()

