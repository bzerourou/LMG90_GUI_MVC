
# ============================================================================
# Onglet Modèle
# ============================================================================
"""
Onglet de création/édition de modèles.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QPushButton, QMessageBox, QGroupBox, QHBoxLayout
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import Model
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController


class ModelTab(QWidget):
    """Onglet de gestion des modèles"""
    
    model_created = pyqtSignal()
    
    # Éléments par dimension
    ELEMENTS_2D = ["Rxx2D", "T3xxx", "Q4xxx", "T6xxx", "Q8xxx", "Q9xxx", "BARxx"]
    ELEMENTS_3D = ["Rxx3D", "H8xxx", "SHB8x", "H20xx", "SHB6x", "TE10x", "DKTxx", "BARxx"]
    
    # Options pour éléments finis
    ELEMENT_OPTIONS = {
        "T3xxx": ["kinematic", "formulation", "mass_storage"],
        "Q4xxx": ["kinematic", "formulation", "mass_storage"],
        "T6xxx": ["kinematic", "formulation", "mass_storage"],
        "Q8xxx": ["kinematic", "formulation", "mass_storage"],
        "Q9xxx": ["kinematic", "formulation"],
        "BARxx": ["kinematic", "formulation", "mass_storage"],
    }
    
    OPTION_VALUES = {
        "kinematic": ["small", "large"],
        "formulation": ["UpdtL", "TotaL"],
        "mass_storage": ["lump_", "coher"],
        "material": ["elas_", "elasd", "J2iso", "J2mix", "kvisc"],
        "anisotropy": ["iso__", "ortho"],
        "external_model": ["MatL_", "Demfi", "Umat_", "no___"],
    }
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.option_combos = {}
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        # Formulaire de base
        form = QFormLayout()
        
        self.name_input = QLineEdit("rigid")
        self.name_input.setMaxLength(5)
        form.addRow("Nom (max 5 car.) :", self.name_input)
        
        self.physics_combo = QComboBox()
        self.physics_combo.addItems(["MECAx", "THERx", "HYDRx"])
        form.addRow("Physique :", self.physics_combo)
        
        self.dimension_combo = QComboBox()
        self.dimension_combo.addItems(["2", "3"])
        form.addRow("Dimension :", self.dimension_combo)
        
        self.element_combo = QComboBox()
        form.addRow("Élément :", self.element_combo)
        
        layout.addLayout(form)
        
        # Groupe options (masqué par défaut)
        self.options_group = QGroupBox("Options du modèle")
        self.options_layout = QFormLayout()
        self.options_group.setLayout(self.options_layout)
        self.options_group.setVisible(False)
        layout.addWidget(self.options_group)
        
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
        
        # Initialiser les éléments
        self._update_elements()
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.dimension_combo.currentTextChanged.connect(self._on_dimension_changed)
        self.element_combo.currentTextChanged.connect(self._on_element_changed)
    
    def _on_dimension_changed(self, dim_text):
        """Quand la dimension change"""
        self._update_elements()
        self.controller.state.dimension = int(dim_text)
    
    def _update_elements(self):
        """Met à jour la liste des éléments selon dimension"""
        dim = int(self.dimension_combo.currentText())
        elements = self.ELEMENTS_2D if dim == 2 else self.ELEMENTS_3D
        
        current = self.element_combo.currentText()
        self.element_combo.blockSignals(True)
        self.element_combo.clear()
        self.element_combo.addItems(elements)
        
        # Restaurer sélection si possible
        if current in elements:
            self.element_combo.setCurrentText(current)
        
        self.element_combo.blockSignals(False)
        self._on_element_changed(self.element_combo.currentText())
    
    def _on_element_changed(self, element):
        """Quand l'élément change, afficher les options"""
        # Nettoyer les anciennes options
        for i in reversed(range(self.options_layout.count())):
            item = self.options_layout.takeAt(i)
            if item.widget():
                item.widget().deleteLater()
        self.option_combos.clear()
        
        # Éléments rigides → pas d'options
        if element in ["Rxx2D", "Rxx3D"]:
            self.options_group.setVisible(False)
            return
        
        # Afficher les options
        self.options_group.setVisible(True)
        
        # Options spécifiques à l'élément
        specific_options = self.ELEMENT_OPTIONS.get(element, [])
        for opt_name in specific_options:
            combo = QComboBox()
            combo.addItems(self.OPTION_VALUES.get(opt_name, []))
            self.options_layout.addRow(f"{opt_name} :", combo)
            self.option_combos[opt_name] = combo
        
        # Options globales (toujours disponibles pour éléments finis)
        for opt_name in ["material", "anisotropy", "external_model"]:
            combo = QComboBox()
            combo.addItems(self.OPTION_VALUES[opt_name])
            self.options_layout.addRow(f"{opt_name} :", combo)
            self.option_combos[opt_name] = combo
    
    def _on_create(self):
        """Crée le modèle"""
        try:
            # Récupérer les options
            options = {}
            for opt_name, combo in self.option_combos.items():
                selected = combo.currentText()
                if selected:
                    options[opt_name] = selected
            
            # Créer le modèle
            model = Model(
                name=self.name_input.text().strip(),
                physics=self.physics_combo.currentText(),
                element=self.element_combo.currentText(),
                dimension=int(self.dimension_combo.currentText()),
                options=options
            )
            
            # Ajouter via le contrôleur
            self.controller.add_model(model)
            
            # Succès
            self.model_created.emit()
            QMessageBox.information(self, "Succès", f"Modèle '{model.name}' créé")
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def _on_edit(self):
        pass

    def _on_delete(self):
        pass
    
    def refresh(self):
        """Rafraîchit l'onglet"""
        pass