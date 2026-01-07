# ============================================================================
# Onglet Avatar
# ============================================================================
"""
Onglet de création d'avatars standards.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QPushButton, QMessageBox, QCheckBox, QLabel, QTreeWidgetItem
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import Avatar, AvatarType, AvatarOrigin
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController


class AvatarTab(QWidget):
    """Onglet de création d'avatars"""
    
    avatar_created = pyqtSignal()
    
    AVATAR_TYPES_2D = [
        "rigidDisk", "rigidJonc", "rigidPolygon", "rigidOvoidPolygon",
        "rigidDiscreteDisk", "rigidCluster",
        "roughWall", "fineWall", "smoothWall", "granuloRoughWall"
    ]
    
    AVATAR_TYPES_3D = ["rigidSphere"]
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Type d'avatar
        self.type_combo = QComboBox()
        form.addRow("Type :", self.type_combo)
        
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
        
        # --- Champs spécifiques (masqués par défaut) ---
        
        # Rayon
        self.radius_label = QLabel("Rayon :")
        self.radius_input = QLineEdit("0.1")
        form.addRow(self.radius_label, self.radius_input)
        
        # Hollow (pour rigidDisk)
        self.hollow_check = QCheckBox("Disque creux (hollow)")
        form.addRow("", self.hollow_check)
        
        # Axes (pour rigidJonc)
        self.axes_label = QLabel("Axes (axe1, axe2) :")
        self.axes_input = QLineEdit("2.0, 0.05")
        form.addRow(self.axes_label, self.axes_input)
        
        # Polygone
        self.gen_type_label = QLabel("Type génération :")
        self.gen_type_combo = QComboBox()
        self.gen_type_combo.addItems(["regular", "full", "bevel"])
        form.addRow(self.gen_type_label, self.gen_type_combo)
        
        self.nb_vertices_label = QLabel("Nb vertices :")
        self.nb_vertices_input = QLineEdit("5")
        form.addRow(self.nb_vertices_label, self.nb_vertices_input)
        
        self.vertices_label = QLabel("Vertices (liste) :")
        self.vertices_input = QLineEdit("[[-0.5,-0.5],[0.5,-0.5],[0.5,0.5],[-0.5,0.5]]")
        form.addRow(self.vertices_label, self.vertices_input)
        
        # Ovoid
        self.ovoid_label = QLabel("Rayons (ra, rb) :")
        self.ovoid_input = QLineEdit("1.0, 0.5")
        form.addRow(self.ovoid_label, self.ovoid_input)
        
        # Walls
        self.wall_length_label = QLabel("Longueur :")
        self.wall_length_input = QLineEdit("2.0")
        form.addRow(self.wall_length_label, self.wall_length_input)
        
        self.wall_height_label = QLabel("Hauteur/Rayon :")
        self.wall_height_input = QLineEdit("0.15")
        form.addRow(self.wall_height_label, self.wall_height_input)
        
        self.wall_nb_label = QLabel("Nb vertices/polyg :")
        self.wall_nb_input = QLineEdit("10")
        form.addRow(self.wall_nb_label, self.wall_nb_input)
        
        layout.addLayout(form)
        
        # Bouton créer
        create_btn = QPushButton("Créer Avatar")
        create_btn.clicked.connect(self._on_create)
        layout.addWidget(create_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Initialiser
        self._update_avatar_types()
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.gen_type_combo.currentTextChanged.connect(self._on_gen_type_changed)
    
    def _update_avatar_types(self):
        """Met à jour les types selon dimension"""
        dim = self.controller.state.dimension
        types = self.AVATAR_TYPES_2D if dim == 2 else self.AVATAR_TYPES_3D
        
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        self.type_combo.addItems(types)
        self.type_combo.blockSignals(False)
        
        # Mettre à jour le centre
        center_default = "0.0, 0.0" if dim == 2 else "0.0, 0.0, 0.0"
        self.center_input.setText(center_default)
        self.center_label.setText(f"Centre ({'x,y' if dim == 2 else 'x,y,z'}) :")
        
        self._on_type_changed(self.type_combo.currentText())
    
    def _on_type_changed(self, avatar_type):
        """Affiche/masque les champs selon le type"""
        # Masquer tout
        for widget in [
            self.radius_label, self.radius_input, self.hollow_check,
            self.axes_label, self.axes_input,
            self.gen_type_label, self.gen_type_combo,
            self.nb_vertices_label, self.nb_vertices_input,
            self.vertices_label, self.vertices_input,
            self.ovoid_label, self.ovoid_input,
            self.wall_length_label, self.wall_length_input,
            self.wall_height_label, self.wall_height_input,
            self.wall_nb_label, self.wall_nb_input
        ]:
            widget.setVisible(False)
        
        # Afficher selon le type
        if avatar_type in ["rigidDisk", "rigidDiscreteDisk", "rigidCluster"]:
            self.radius_label.setVisible(True)
            self.radius_input.setVisible(True)
            if avatar_type == "rigidDisk":
                self.hollow_check.setVisible(True)
            if avatar_type == "rigidCluster":
                self.nb_vertices_label.setText("Nb disques :")
                self.nb_vertices_label.setVisible(True)
                self.nb_vertices_input.setVisible(True)
        
        elif avatar_type == "rigidJonc":
            self.axes_label.setVisible(True)
            self.axes_input.setVisible(True)
        
        elif avatar_type == "rigidPolygon":
            self.radius_label.setVisible(True)
            self.radius_input.setVisible(True)
            self.gen_type_label.setVisible(True)
            self.gen_type_combo.setVisible(True)
            self._on_gen_type_changed(self.gen_type_combo.currentText())
        
        elif avatar_type == "rigidOvoidPolygon":
            self.ovoid_label.setVisible(True)
            self.ovoid_input.setVisible(True)
            self.nb_vertices_label.setText("Nb vertices :")
            self.nb_vertices_label.setVisible(True)
            self.nb_vertices_input.setVisible(True)
        
        elif avatar_type in ["roughWall", "fineWall", "smoothWall", "granuloRoughWall"]:
            self.wall_length_label.setVisible(True)
            self.wall_length_input.setVisible(True)
            self.wall_height_label.setVisible(True)
            self.wall_height_input.setVisible(True)
            self.wall_nb_label.setVisible(True)
            self.wall_nb_input.setVisible(True)
            
            if avatar_type == "granuloRoughWall":
                self.wall_height_label.setText("Rayons (rmin, rmax) :")
                self.wall_height_input.setText("0.1, 0.2")
            elif avatar_type == "smoothWall":
                self.wall_height_label.setText("Hauteur (h) :")
                self.wall_nb_label.setText("Nb polygones :")
            else:
                self.wall_height_label.setText("Rayon (r) :")
                self.wall_nb_label.setText("Nb vertices :")
    
    def _on_gen_type_changed(self, gen_type):
        """Affiche vertices ou nb_vertices selon le type"""
        if gen_type == "regular":
            self.nb_vertices_label.setText("Nb vertices :")
            self.nb_vertices_label.setVisible(True)
            self.nb_vertices_input.setVisible(True)
            self.vertices_label.setVisible(False)
            self.vertices_input.setVisible(False)
        else:
            self.nb_vertices_label.setVisible(False)
            self.nb_vertices_input.setVisible(False)
            self.vertices_label.setVisible(True)
            self.vertices_input.setVisible(True)
    
    def _on_create(self):
        """Crée l'avatar"""
        try:
            # Parser le centre
            center = [float(x.strip()) for x in self.center_input.text().split(',')]
            
            # Type d'avatar
            avatar_type = AvatarType(self.type_combo.currentText())
            
            # Créer l'avatar de base
            avatar = Avatar(
                avatar_type=avatar_type,
                center=center,
                material_name=self.material_combo.currentText(),
                model_name=self.model_combo.currentText(),
                color=self.color_input.text().strip(),
                origin=AvatarOrigin.MANUAL
            )
            
            # Ajouter les champs spécifiques
            if avatar_type in [AvatarType.RIGID_DISK, AvatarType.RIGID_DISCRETE, AvatarType.RIGID_CLUSTER]:
                avatar.radius = float(self.radius_input.text())
                if avatar_type == AvatarType.RIGID_DISK:
                    avatar.is_hollow = self.hollow_check.isChecked()
                if avatar_type == AvatarType.RIGID_CLUSTER:
                    avatar.nb_vertices = int(self.nb_vertices_input.text())
            
            elif avatar_type == AvatarType.RIGID_JONC:
                axes = [float(x.strip()) for x in self.axes_input.text().split(',')]
                avatar.axis = {'axe1': axes[0], 'axe2': axes[1]}
            
            elif avatar_type == AvatarType.RIGID_POLYGON:
                avatar.radius = float(self.radius_input.text())
                avatar.generation_type = self.gen_type_combo.currentText()
                if avatar.generation_type == "regular":
                    avatar.nb_vertices = int(self.nb_vertices_input.text())
                else:
                    import ast
                    avatar.vertices = ast.literal_eval(self.vertices_input.text())
            
            elif avatar_type == AvatarType.RIGID_OVOID:
                radii = [float(x.strip()) for x in self.ovoid_input.text().split(',')]
                avatar.wall_params = {'ra': radii[0], 'rb': radii[1]}
                avatar.nb_vertices = int(self.nb_vertices_input.text())
            
            elif avatar_type in [AvatarType.ROUGH_WALL, AvatarType.FINE_WALL, 
                                AvatarType.SMOOTH_WALL, AvatarType.GRANULO_WALL]:
                wall_params = {
                    'l': float(self.wall_length_input.text())
                }
                
                if avatar_type == AvatarType.GRANULO_WALL:
                    radii = [float(x.strip()) for x in self.wall_height_input.text().split(',')]
                    wall_params['rmin'] = radii[0]
                    wall_params['rmax'] = radii[1]
                    wall_params['nb_vertex'] = int(self.wall_nb_input.text())
                elif avatar_type == AvatarType.SMOOTH_WALL:
                    wall_params['h'] = float(self.wall_height_input.text())
                    wall_params['nb_polyg'] = int(self.wall_nb_input.text())
                else:
                    wall_params['r'] = float(self.wall_height_input.text())
                    wall_params['nb_vertex'] = int(self.wall_nb_input.text())
                
                avatar.wall_params = wall_params
            
            # Ajouter via le contrôleur
            idx = self.controller.add_avatar(avatar)
            
            # Succès
            self.avatar_created.emit()
            QMessageBox.information(self, "Succès", f"Avatar #{idx} créé")
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
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
        
        # Types d'avatars
        self._update_avatar_types()
        if hasattr(self, 'tree'):
                self._refresh_tree()

    def _refresh_tree(self):
        """Rafraîchit l'arbre des avatars"""
        if not hasattr(self, 'tree'):
            return
        self.tree.clear()

        avatars = self.controller.state.avatars
    
        from ...core.models import AvatarOrigin
        from PyQt6.QtCore import Qt
        
        for i, avatar in enumerate(avatars):
            # Marquer l'origine
            origin_str = ""
            if avatar.origin == AvatarOrigin.LOOP:
                origin_str = " [Boucle]"
            elif avatar.origin == AvatarOrigin.GRANULO:
                origin_str = " [Granulo]"
            
            # Créer l'item
            center_str = ', '.join(f"{x:.2f}" for x in avatar.center)
            
            item = QTreeWidgetItem([
                f"#{i}",
                avatar.avatar_type.value,
                avatar.color,
                f"({center_str})",
                origin_str
            ])
            
            # Stocker l'index réel
            item.setData(0, Qt.ItemDataRole.UserRole, i)
            
            # Colorer selon origine
            if avatar.origin != AvatarOrigin.MANUAL:
                from PyQt6.QtGui import QBrush, QColor
                item.setForeground(0, QBrush(QColor(100, 100, 100)))  # Gris
            
            self.tree.addTopLevelItem(item)