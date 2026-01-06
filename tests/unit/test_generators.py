# ============================================================================
# FICHIER 12: tests/unit/test_generators.py
# Tests des générateurs
# ============================================================================
"""
Tests des générateurs de boucles et granulo.
"""
import pytest
import math
from src.core.models import Loop
from src.core.generators import LoopGenerator


class TestLoopGenerator:
    
    def test_generate_circle(self):
        """Test génération en cercle"""
        centers = LoopGenerator.generate_circle(
            count=8,
            radius=2.0,
            offset_x=1.0,
            offset_y=0.5
        )
        
        assert len(centers) == 8
        assert all(len(c) == 2 for c in centers)
        
        # Vérifier qu'ils sont bien sur un cercle
        for center in centers:
            dist = math.sqrt((center[0] - 1.0)**2 + (center[1] - 0.5)**2)
            assert abs(dist - 2.0) < 1e-10
    
    def test_generate_grid(self):
        """Test génération en grille"""
        centers = LoopGenerator.generate_grid(
            count=9,
            step=1.0
        )
        
        assert len(centers) == 9
        # Grille 3x3
        expected = [
            [0, 0], [1, 0], [2, 0],
            [0, 1], [1, 1], [2, 1],
            [0, 2], [1, 2], [2, 2]
        ]
        assert centers == expected
    
    def test_generate_line_horizontal(self):
        """Test ligne horizontale"""
        centers = LoopGenerator.generate_line(
            count=5,
            step=2.0,
            invert_axis=False
        )
        
        assert len(centers) == 5
        # Tous sur même Y
        assert all(c[1] == 0 for c in centers)
        # X espacés de 2
        for i, center in enumerate(centers):
            assert center[0] == i * 2.0
    
    def test_generate_line_vertical(self):
        """Test ligne verticale"""
        centers = LoopGenerator.generate_line(
            count=3,
            step=1.5,
            invert_axis=True
        )
        
        assert len(centers) == 3
        # Tous sur même X
        assert all(c[0] == 0 for c in centers)
        # Y espacés de 1.5
        for i, center in enumerate(centers):
            assert center[1] == i * 1.5
