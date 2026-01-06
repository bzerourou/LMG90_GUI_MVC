# ============================================================================
# Onglet Boucles
# ============================================================================
"""
Onglet pour générer des avatars en boucle.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QCheckBox, QLabel
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import Loop
from ...controllers.project_controller import ProjectController


class LoopTab(QWidget):
    """Onglet génération de boucles"""
    
    loop_generated = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Type de boucle
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Cercle", "Grille", "Ligne", "Spirale", "Manuel"])
        form.addRow("Type de boucle :", self.type_combo)
        
        # Avatar modèle
        self.avatar_combo = QComboBox()
        form.addRow("Avatar à répéter :", self.avatar_combo)
        
        # Nombre
        self.count_input = QLineEdit("10")
        form.addRow("Nombre d'avatars :", self.count_input)
        
        # Paramètres géométriques
        self.radius_label = QLabel("Rayon :")
        self.radius_input = QLineEdit("2.0")
        form.addRow(self.radius_label, self.radius_input)
        
        self.step_label = QLabel("Pas :")
        self.step_input = QLineEdit("1.0")
        form.addRow(self.step_label, self.step_input)
        
        self.invert_check = QCheckBox("Inverser l'axe")
        form.addRow("", self.invert_check)
        
        self.offset_x_label = QLabel("Offset X :")
        self.offset_x_input = QLineEdit("0.0")
        form.addRow(self.offset_x_label, self.offset_x_input)
        
        self.offset_y_label = QLabel("Offset Y :")
        self.offset_y_input = QLineEdit("0.0")
        form.addRow(self.offset_y_label, self.offset_y_input)
        
        self.spiral_label = QLabel("Facteur spirale :")
        self.spiral_input = QLineEdit("0.1")
        form.addRow(self.spiral_label, self.spiral_input)
        
        layout.addLayout(form)
        
        # Stockage dans groupe
        self.store_check = QCheckBox("Stocker dans un groupe nommé")
        self.store_check.setChecked(True)
        layout.addWidget(self.store_check)
        
        group_layout = QFormLayout()
        self.group_name_input = QLineEdit("groupe_boucle")
        group_layout.addRow("Nom du groupe :", self.group_name_input)
        layout.addLayout(group_layout)
        
        # Bouton générer
        gen_btn = QPushButton("Générer la Boucle")
        gen_btn.clicked.connect(self._on_generate)
        layout.addWidget(gen_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Stocker les widgets pour masquer/afficher
        self.geom_widgets = [
            self.radius_label, self.radius_input,
            self.step_label, self.step_input,
            self.invert_check,
            self.offset_x_label, self.offset_x_input,
            self.offset_y_label, self.offset_y_input,
            self.spiral_label, self.spiral_input
        ]
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
    
    def _on_type_changed(self, loop_type):
        """Affiche/masque les champs selon le type"""
        # Masquer tout
        for w in self.geom_widgets:
            w.setVisible(False)
        
        # Afficher selon le type
        if loop_type == "Cercle":
            self.radius_label.setVisible(True)
            self.radius_input.setVisible(True)
            self.offset_x_label.setVisible(True)
            self.offset_x_input.setVisible(True)
            self.offset_y_label.setVisible(True)
            self.offset_y_input.setVisible(True)
        
        elif loop_type == "Grille":
            self.step_label.setVisible(True)
            self.step_input.setVisible(True)
            self.offset_x_label.setVisible(True)
            self.offset_x_input.setVisible(True)
            self.offset_y_label.setVisible(True)
            self.offset_y_input.setVisible(True)
        
        elif loop_type == "Ligne":
            self.step_label.setVisible(True)
            self.step_input.setVisible(True)
            self.invert_check.setVisible(True)
            self.offset_x_label.setVisible(True)
            self.offset_x_input.setVisible(True)
            self.offset_y_label.setVisible(True)
            self.offset_y_input.setVisible(True)
        
        elif loop_type == "Spirale":
            self.radius_label.setVisible(True)
            self.radius_input.setVisible(True)
            self.spiral_label.setVisible(True)
            self.spiral_input.setVisible(True)
            self.offset_x_label.setVisible(True)
            self.offset_x_input.setVisible(True)
            self.offset_y_label.setVisible(True)
            self.offset_y_input.setVisible(True)
        
        elif loop_type == "Manuel":
            # Mode manuel : on force le stockage
            self.store_check.setChecked(True)
            self.store_check.setEnabled(False)
        else:
            self.store_check.setEnabled(True)
    
    def _on_generate(self):
        """Génère la boucle"""
        try:
            # Créer la configuration
            loop = Loop(
                loop_type=self.type_combo.currentText(),
                model_avatar_index=self.avatar_combo.currentData(),
                count=int(self.count_input.text()),
                radius=float(self.radius_input.text()),
                step=float(self.step_input.text()),
                offset_x=float(self.offset_x_input.text()),
                offset_y=float(self.offset_y_input.text()),
                spiral_factor=float(self.spiral_input.text()),
                invert_axis=self.invert_check.isChecked(),
                group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
            )
            
            # Générer via le contrôleur
            indices = self.controller.generate_loop(loop)
            
            # Succès
            self.loop_generated.emit()
            msg = f"{len(indices)} avatars générés"
            if loop.group_name:
                msg += f"\nGroupe : {loop.group_name}"
            QMessageBox.information(self, "Succès", msg)
            
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération échouée :\n{e}")
    
    def refresh(self):
        """Rafraîchit le combo des avatars"""
        self.avatar_combo.clear()
        avatars = self.controller.get_avatars(include_generated=False)
        
        for i, avatar in enumerate(avatars):
            label = f"{avatar.avatar_type.value} - {avatar.color}"
            self.avatar_combo.addItem(label, i)

