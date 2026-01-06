# ============================================================================
# FICHIER 13: tests/integration/test_project_lifecycle.py
# Tests d'intégration
# ============================================================================
"""
Tests d'intégration du cycle de vie complet d'un projet.
"""
import pytest
from pathlib import Path

from src.controllers.project_controller import ProjectController
from src.core.models import Material, Model, Avatar, MaterialType, AvatarType, AvatarOrigin


class TestProjectLifecycle:
    
    def test_complete_workflow(self, temp_dir):
        """
        Test workflow complet :
        1. Créer projet
        2. Ajouter matériau, modèle, avatar
        3. Sauvegarder
        4. Recharger
        5. Vérifier intégrité
        """
        # 1. Créer projet
        controller = ProjectController()
        controller.new_project("TestProjet")
        
        # 2. Ajouter matériau
        mat = Material(
            name="STEEL",
            material_type=MaterialType.RIGID,
            density=7800.0
        )
        controller.add_material(mat)
        
        # 3. Ajouter modèle
        mod = Model(
            name="rigid",
            physics="MECAx",
            element="Rxx2D",
            dimension=2
        )
        controller.add_model(mod)
        
        # 4. Ajouter avatar
        avatar = Avatar(
            avatar_type=AvatarType.RIGID_DISK,
            center=[1.0, 2.0],