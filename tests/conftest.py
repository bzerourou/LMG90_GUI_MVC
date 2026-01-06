# ============================================================================
# FICHIER 10: tests/conftest.py
# Configuration pytest
# ============================================================================
"""
Configuration et fixtures partagées pour les tests.
"""
import pytest
import tempfile
from pathlib import Path

from src.controllers.project_controller import ProjectController
from src.core.models import Material, Model, MaterialType


@pytest.fixture
def controller():
    """Crée un contrôleur vide"""
    return ProjectController()


@pytest.fixture
def temp_dir():
    """Crée un dossier temporaire"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_material():
    """Matériau de test"""
    return Material(
        name="TEST",
        material_type=MaterialType.RIGID,
        density=2000.0
    )


@pytest.fixture
def sample_model():
    """Modèle de test"""
    return Model(
        name="rigid",
        physics="MECAx",
        element="Rxx2D",
        dimension=2
    )

