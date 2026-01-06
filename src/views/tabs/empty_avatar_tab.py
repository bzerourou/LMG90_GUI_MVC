# ============================================================================
# Onglet Avatar Vide
# ============================================================================
"""
Onglet pour créer des avatars vides avec contacteurs personnalisés.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QPushButton, QMessageBox, QScrollArea, QLabel, QHBoxLayout
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import Avatar, AvatarType, AvatarOrigin
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController


class EmptyAvatarTab(QWidget):
    """Onglet création d'avatars vides"""
    
    avatar_created = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._setup_ui()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Dimension
        self.dim_combo = QComboBox()
        self.dim_combo.addItems(["2", "3"])
        self.dim_combo.currentTextChanged.connect(self._on_dim_changed)
        form.addRow("Dimension :", self.dim_combo)
        
        # Centre
        self.center_label = QLabel("Centre (x,y) :")
        self.center_input = QLineEdit("0.0, 0.0")
        form.addRow(self.center_label, self.center_input)
        
        # Matériau et modèle
        self.material_combo = QComboBox()
        form.addRow("Matériau :", self.material_combo)
        
        self.model_combo = QComboBox()
        form.addRow("Modèle :", self.model_combo)
        
        # Couleur
        self.color_input = QLineEdit("BLUEx")
        form.addRow("Couleur :", self.color_input)
        
        layout.addLayout(form)
        
        # --- Contacteurs ---
        layout.addWidget(QLabel("<b>Contacteurs à ajouter :</b>"))
        
        # Liste scrollable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        contactors_widget = QWidget()
        self.contactors_layout = QVBoxLayout()
        contactors_widget.setLayout(self.contactors_layout)
        scroll.setWidget(contactors_widget)
        
        layout.addWidget(scroll)
        
        # Bouton ajouter contacteur
        add_btn = QPushButton("Ajouter un contacteur")
        add_btn.clicked.connect(self._add_contactor_row)
        layout.addWidget(add_btn)
        
        # Bouton créer
        create_btn = QPushButton("Créer Avatar Vide")
        create_btn.clicked.connect(self._on_create)
        layout.addWidget(create_btn)
        
        self.setLayout(layout)
        
        # Ajouter un contacteur par défaut
        self._add_contactor_row()
    
    def _on_dim_changed(self, dim_text):
        """Quand dimension change"""
        dim = int(dim_text)
        center_default = "0.0, 0.0" if dim == 2 else "0.0, 0.0, 0.0"
        self.center_input.setText(center_default)
        self.center_label.setText(f"Centre ({'x,y' if dim == 2 else 'x,y,z'}) :")
    
    def _add_contactor_row(self):
        """Ajoute une ligne de contacteur"""
        row = QHBoxLayout()
        
        row.addWidget(QLabel("Forme :"))
        
        shape_combo = QComboBox()
        shape_combo.addItems(["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"])
        shape_combo.currentTextChanged.connect(
            lambda: self._on_contactor_type_changed(row)
        )
        row.addWidget(shape_combo)
        
        row.addWidget(QLabel("Couleur :"))
        
        color_input = QLineEdit("BLUEx")
        row.addWidget(color_input)
        
        params_label = QLabel("Params :")
        row.addWidget(params_label)
        
        params_input = QLineEdit("byrd=0.3")
        row.addWidget(params_input)
        
        remove_btn = QPushButton("×")
        remove_btn.setFixedWidth(30)
        remove_btn.clicked.connect(lambda: self._remove_contactor_row(row))
        row.addWidget(remove_btn)
        
        # Stocker les widgets pour accès ultérieur
        row.shape_combo = shape_combo
        row.color_input = color_input
        row.params_label = params_label
        row.params_input = params_input
        
        widget = QWidget()
        widget.setLayout(row)
        self.contactors_layout.addWidget(widget)
    
    def _on_contactor_type_changed(self, row):
        """Quand le type de contacteur change"""
        shape = row.shape_combo.currentText()
        
        if shape in ["DISKx", "xKSID"]:
            row.params_input.setText("byrd=0.3")
            row.params_label.setText("Params (byrd) :")
        elif shape == "JONCx":
            row.params_input.setText("axe1=1.0, axe2=0.1")
            row.params_label.setText("Params (axes) :")
        elif shape == "POLYG":
            row.params_input.setText("nb_vertices=4, vertices=[[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]]")
            row.params_label.setText("Params (vertices) :")
        elif shape == "PT2Dx":
            row.params_input.setText("")
            row.params_label.setText("Params :")
    
    def _remove_contactor_row(self, row):
        """Supprime une ligne de contacteur"""
        for i in range(self.contactors_layout.count()):
            widget = self.contactors_layout.itemAt(i).widget()
            if widget and widget.layout() == row:
                widget.deleteLater()
                return
    
    def _on_create(self):
        """Crée l'avatar vide"""
        try:
            # Parser données de base
            dim = int(self.dim_combo.currentText())
            center = [float(x.strip()) for x in self.center_input.text().split(',')]
            
            if len(center) != dim:
                raise ValueError(f"Centre doit avoir {dim} coordonnées")
            
            # Parser les contacteurs
            contactors = []
            for i in range(self.contactors_layout.count()):
                widget = self.contactors_layout.itemAt(i).widget()
                if not widget:
                    continue
                
                row = widget.layout()
                shape = row.shape_combo.currentText()
                color = row.color_input.text().strip()
                params_text = row.params_input.text().strip()
                
                # Parser les paramètres
                from ...utils.safe_eval import SafeEvaluator
                evaluator = SafeEvaluator()
                params = evaluator.eval_dict(params_text) if params_text else {}
                
                contactors.append({
                    'shape': shape,
                    'color': color or self.color_input.text(),
                    'params': params
                })
            
            # Créer l'avatar
            avatar = Avatar(
                avatar_type=AvatarType.EMPTY_AVATAR,
                center=center,
                material_name=self.material_combo.currentText(),
                model_name=self.model_combo.currentText(),
                color=self.color_input.text().strip(),
                origin=AvatarOrigin.MANUAL,
                contactors=contactors
            )
            
            # Ajouter via le contrôleur
            idx = self.controller.add_avatar(avatar)
            
            # Succès
            self.avatar_created.emit()
            QMessageBox.information(self, "Succès", f"Avatar vide #{idx} créé")
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def refresh(self):
        """Rafraîchit les combos"""
        self.material_combo.clear()
        materials = self.controller.get_materials()
        self.material_combo.addItems([m.name for m in materials])
        
        self.model_combo.clear()
        models = self.controller.get_models()
        self.model_combo.addItems([m.name for m in models])

