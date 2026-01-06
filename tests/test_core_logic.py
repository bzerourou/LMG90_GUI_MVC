import pytest
from core_logic import MaterialData, ModelValidator, GranuloGenerator

class TestMaterialValidator:
    
    def test_valid_material(self):
        mat = MaterialData(
            name="TDUR", type="RIGID", density=1000., props={}
        )
        valid, msg = ModelValidator.validate_material(mat)
        assert valid is True
        assert msg == ""
    
    def test_name_too_long(self):
        mat = MaterialData(
            name="TOOLONG", type="RIGID", density=1000., props={}
        )
        valid, msg = ModelValidator.validate_material(mat)
        assert valid is False
        assert "max 5" in msg.lower()
    
    def test_negative_density(self):
        mat = MaterialData(
            name="TEST", type="RIGID", density=-10., props={}
        )
        valid, msg = ModelValidator.validate_material(mat)
        assert valid is False
        assert "positive" in msg.lower()

class TestGranuloGenerator:
    
    def test_box2d_deposition(self):
        nb, coor, radii = GranuloGenerator.generate_positions(
            nb=50, rmin=0.1, rmax=0.2,
            container_type='Box2D',
            lx=5.0, ly=5.0
        )
        
        assert nb > 0
        assert len(radii) == 50
        assert coor.shape == (nb, 2)
        assert all(0.1 <= r <= 0.2 for r in radii)
    
    def test_invalid_container(self):
        with pytest.raises(ValueError):
            GranuloGenerator.generate_positions(
                nb=10, rmin=0.1, rmax=0.2,
                container_type='INVALID'
            )