# ============================================================================
# Onglet Granulométrie
# ============================================================================
"""
Onglet pour générer des distributions granulométriques.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QCheckBox, QLabel, QGroupBox, QHBoxLayout
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import GranuloGeneration
from ...controllers.project_controller import ProjectController


class GranuloTab(QWidget):
    """Onglet granulométrie"""
    
    granulo_generated = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        # === Groupe 1 : Distribution ===
        dist_group = QGroupBox("1. Distribution des Particules")
        dist_form = QFormLayout()
        
        self.nb_input = QLineEdit("200")
        dist_form.addRow("Nombre de particules :", self.nb_input)
        
        self.rmin_input = QLineEdit("0.05")
        dist_form.addRow("Rayon min :", self.rmin_input)
        
        self.rmax_input = QLineEdit("0.15")
        dist_form.addRow("Rayon max :", self.rmax_input)
        
        self.seed_input = QLineEdit()
        self.seed_input.setPlaceholderText("Graine aléatoire (optionnel)")
        dist_form.addRow("Seed :", self.seed_input)
        
        dist_group.setLayout(dist_form)
        layout.addWidget(dist_group)
        
        # === Groupe 2 : Conteneur ===
        container_group = QGroupBox("2. Géométrie du Dépôt")
        container_layout = QVBoxLayout()
        
        container_form = QFormLayout()
        
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["Box2D", "Disk2D", "Couette2D", "Drum2D"])
        container_form.addRow("Type de conteneur :", self.shape_combo)
        
        container_layout.addLayout(container_form)
        
        # Paramètres dynamiques du conteneur
        self.params_widget = QWidget()
        self.params_layout = QFormLayout()
        self.params_widget.setLayout(self.params_layout)
        container_layout.addWidget(self.params_widget)
        
        # Champs stockés
        self.lx_input = QLineEdit("4.0")
        self.ly_input = QLineEdit("4.0")
        self.r_input = QLineEdit("2.0")
        self.rint_input = QLineEdit("2.0")
        self.rext_input = QLineEdit("4.0")
        
        container_group.setLayout(container_layout)
        layout.addWidget(container_group)
        
        # === Groupe 3 : Propriétés physiques ===
        phys_group = QGroupBox("3. Propriétés Physiques")
        phys_form = QFormLayout()
        
        self.material_combo = QComboBox()
        phys_form.addRow("Matériau :", self.material_combo)
        
        self.model_combo = QComboBox()
        phys_form.addRow("Modèle :", self.model_combo)
        
        self.avatar_combo = QComboBox()
        phys_form.addRow("Type d'avatar :", self.avatar_combo)
        
        self.color_input = QLineEdit("BLUEx")
        phys_form.addRow("Couleur :", self.color_input)
        
        phys_group.setLayout(phys_form)
        layout.addWidget(phys_group)
        
        # Stockage dans groupe
        self.store_check = QCheckBox("Stocker le dépôt dans un groupe nommé")
        self.store_check.setChecked(True)
        layout.addWidget(self.store_check)
        
        group_form = QFormLayout()
        self.group_name_input = QLineEdit("depot_granulo")
        group_form.addRow("Nom du groupe :", self.group_name_input)
        layout.addLayout(group_form)
        
        # Bouton générer
        gen_btn = QPushButton("Générer le Dépôt")
        edit_btn = QPushButton("Modifier")
        delete_btn = QPushButton("Supprimer")
        gen_btn.clicked.connect(self._on_generate)
        edit_btn.clicked.connect(self._on_edit)
        delete_btn.clicked.connect(self._on_delete)
        button_layout = QHBoxLayout()
        button_layout.addWidget(gen_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Initialiser les paramètres du conteneur
        self._update_container_params("Box2D")
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.shape_combo.currentTextChanged.connect(self._update_container_params)
    
    def _update_container_params(self, shape):
        """Met à jour les paramètres selon le conteneur"""
        # Nettoyer
        while self.params_layout.count() > 0:
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        
        # Ajouter selon le type
        if shape == "Box2D":
            self.params_layout.addRow("Largeur (lx) :", self.lx_input)
            self.params_layout.addRow("Hauteur (ly) :", self.ly_input)
            self.lx_input.show()
            self.ly_input.show()
        
        elif shape in ["Disk2D", "Drum2D"]:
            self.params_layout.addRow("Rayon (r) :", self.r_input)
            self.r_input.show()
        
        elif shape == "Couette2D":
            self.params_layout.addRow("Rayon int (rint) :", self.rint_input)
            self.params_layout.addRow("Rayon ext (rext) :", self.rext_input)
            self.rint_input.show()
            self.rext_input.show()
    
    def _on_generate(self):
        """Génère la granulométrie"""
        try:
            # Paramètres du conteneur
            container_params = {}
            shape = self.shape_combo.currentText()
            
            if shape == "Box2D":
                container_params = {
                    'lx': float(self.lx_input.text()),
                    'ly': float(self.ly_input.text())
                }
            elif shape in ["Disk2D", "Drum2D"]:
                container_params = {'r': float(self.r_input.text())}
            elif shape == "Couette2D":
                container_params = {
                    'rint': float(self.rint_input.text()),
                    'rext': float(self.rext_input.text())
                }
            
            # Seed
            seed_text = self.seed_input.text().strip()
            seed = int(seed_text) if seed_text else None
            
            # Créer la configuration
            config = GranuloGeneration(
                nb_particles=int(self.nb_input.text()),
                radius_min=float(self.rmin_input.text()),
                radius_max=float(self.rmax_input.text()),
                container_type=shape,
                container_params=container_params,
                model_name=self.model_combo.currentText(),
                material_name=self.material_combo.currentText(),
                avatar_type=self.avatar_combo.currentText(),
                color=self.color_input.text().strip(),
                seed=seed,
                group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
            )
            
            # Générer via le contrôleur
            indices = self.controller.generate_granulo(config)
            
            # Succès
            self.granulo_generated.emit()
            msg = f"{len(indices)} particules générées"
            if config.group_name:
                msg += f"\nGroupe : {config.group_name}"
            QMessageBox.information(self, "Succès", msg)
            
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération échouée :\n{e}")
    
    def _on_edit(self):
        pass

    def _on_delete(self):
        pass


    def refresh(self):
        """Rafraîchit les combos"""
        # Matériaux
        self.material_combo.clear()
        materials = self.controller.get_materials()
        self.material_combo.addItems([m.name for m in materials])
        
        # Modèles
        self.model_combo.clear()
        models = self.controller.get_models()
        self.model_combo.addItems([m.name for m in models])
        
        # Avatars manuels
        self.avatar_combo.clear()
        avatars = self.controller.get_avatars(include_generated=False)
        for i, avatar in enumerate(avatars):
            label = f"{avatar.avatar_type.value}"
            self.avatar_combo.addItem(label, avatar.avatar_type.value)

