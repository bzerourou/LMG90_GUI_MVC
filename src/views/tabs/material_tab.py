# ============================================================================
# Onglet Matériau (exemple complet)
# ============================================================================
"""
Onglet de création/édition de matériaux.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QPushButton, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import Material, MaterialType
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController


class MaterialTab(QWidget):
    """Onglet de gestion des matériaux"""
    
    material_created = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        # Formulaire
        form = QFormLayout()
        
        self.name_input = QLineEdit("TDURx")
        self.name_input.setMaxLength(5)
        form.addRow("Nom (max 5 car.) :", self.name_input)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([mt.value for mt in MaterialType])
        form.addRow("Type :", self.type_combo)
        
        self.density_input = QLineEdit("1000.0")
        form.addRow("Densité (kg/m³) :", self.density_input)
        
        self.props_input = QLineEdit()
        self.props_input.setPlaceholderText("ex: young=1e9, nu=0.3")
        form.addRow("Propriétés :", self.props_input)
        
        layout.addLayout(form)
        
        # Boutons
        create_btn = QPushButton("Créer")
        edit_btn = QPushButton("Modifier")
        delete_btn = QPushButton("Supprimer")
        create_btn.clicked.connect(self._on_create)
        edit_btn.clicked.connect(self._on_edit)
        delete_btn.clicked.connect(self._on_delete)
        button_layout = QHBoxLayout()
        button_layout.addWidget(create_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
    
    def _on_type_changed(self, mat_type: str):
        """Quand le type change, suggère des propriétés"""
        suggestions = {
            "RIGID": "",
            "ELAS": "young=1e11, nu=0.3",
            "ELAS_DILA": "young=1e11, nu=0.3, dilatation=1e-5",
            "VISCO_ELAS": "young=1e11, nu=0.3, viscous_young=1e9",
        }
        self.props_input.setPlaceholderText(suggestions.get(mat_type, ""))
    
    def _on_create(self):
        """Crée le matériau"""
        try:
            # Parser les propriétés
            props = self._parse_properties(self.props_input.text())
            
            # Créer le matériau
            material = Material(
                name=self.name_input.text().strip(),
                material_type=MaterialType(self.type_combo.currentText()),
                density=float(self.density_input.text()),
                properties=props
            )
            
            # Ajouter via le contrôleur
            self.controller.add_material(material)
            
            # Succès
            self.material_created.emit()
            QMessageBox.information(self, "Succès", f"Matériau '{material.name}' créé")
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def _on_edit(self):
        pass
    def _on_delete(self):
        pass
    def _parse_properties(self, text: str) -> dict:
        """Parse la chaîne de propriétés"""
        if not text.strip():
            return {}
        
        props = {}
        for pair in text.split(','):
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Essayer de convertir en nombre
                try:
                    if '.' in value or 'e' in value.lower():
                        props[key] = float(value)
                    else:
                        props[key] = int(value)
                except ValueError:
                    props[key] = value
        
        return props
    
    def refresh(self):
        """Rafraîchit l'onglet (si nécessaire)"""
        pass

