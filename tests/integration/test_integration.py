import pytest
import tempfile
import json
from pathlib import Path

class TestProjectSaveLoad:
    
    @pytest.fixture
    def temp_project_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_save_and_reload(self, temp_project_dir, qtbot):
        """Teste qu'un projet sauvegardé se recharge correctement"""
        from main import LMGC90GUI
        
        # Crée une fenêtre
        window = LMGC90GUI()
        qtbot.addWidget(window)
        
        # Crée un matériau
        window.mat_name.setText("TEST")
        window.mat_type.setCurrentText("RIGID")
        window.mat_density.setText("2000")
        window.create_material()
        
        # Sauvegarde
        window.project_dir = str(temp_project_dir)
        window.project_name = "test_project"
        window.do_save()
        
        # Vérifie le fichier
        save_file = temp_project_dir / "test_project.lmgc90"
        assert save_file.exists()
        
        # Recharge dans une nouvelle fenêtre
        window2 = LMGC90GUI()
        qtbot.addWidget(window2)
        
        with open(save_file) as f:
            state = json.load(f)
        
        window2._deserialize_state(state)
        
        # Vérifie que le matériau est bien là
        assert len(window2.material_objects) == 1
        assert window2.material_objects[0].nom == "TEST"
        assert window2.material_objects[0].density == 2000.

class TestUIWorkflow:
    
    def test_create_avatar_full_workflow(self, qtbot):
        """Teste la création d'un avatar complet"""
        from main import LMGC90GUI
        
        window = LMGC90GUI()
        qtbot.addWidget(window)
        
        # 1. Créer matériau
        window.mat_name.setText("MAT1")
        window.create_material()
        
        # 2. Créer modèle
        window.model_name.setText("MOD1")
        window.create_model()
        
        # 3. Créer avatar
        window.avatar_center.setText("1.0, 2.0")
        window.avatar_radius.setText("0.5")
        window.create_avatar()
        
        # Vérifications
        assert len(window.bodies_objects) == 1
        assert len(window.avatar_creations) == 1
        
        avatar = window.avatar_creations[0]
        assert avatar['center'] == [1.0, 2.0]
        assert avatar['type'] == 'rigidDisk'