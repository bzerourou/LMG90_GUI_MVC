# ============================================================================
#AvatarTzb
# ============================================================================
"""
Onglet de gestion des avatars standards avec création, modification et suppression.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QLabel, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import Avatar, AvatarType, AvatarOrigin
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController


class AvatarTab(QWidget):
    """Onglet de gestion des avatars"""
    
    avatar_created = pyqtSignal()
    avatar_updated = pyqtSignal()
    avatar_deleted = pyqtSignal()
    
    AVATAR_TYPES_2D = [
        "rigidDisk", "rigidJonc", "rigidPolygon", "rigidOvoidPolygon",
        "rigidDiscreteDisk", "rigidCluster",
        "roughWall", "fineWall", "smoothWall", "granuloRoughWall"
    ]
    
    AVATAR_TYPES_3D = ["rigidSphere"]
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.current_edit_index = None
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        # === ARBRE ===
        tree_label = QLabel("<b>📋 Liste des Avatars</b>")
        layout.addWidget(tree_label)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["#", "Type", "Couleur", "Centre", "Origine"])
        self.tree.setColumnWidth(0, 40)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 80)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(200)
        layout.addWidget(self.tree)
        
        tree_btn_layout = QHBoxLayout()
        edit_tree_btn = QPushButton("✏️ Modifier Sélection")
        edit_tree_btn.clicked.connect(self._on_edit_from_tree)
        tree_btn_layout.addWidget(edit_tree_btn)
        
        delete_tree_btn = QPushButton("🗑️ Supprimer Sélection")
        delete_tree_btn.clicked.connect(self._on_delete)
        tree_btn_layout.addWidget(delete_tree_btn)
        
        tree_btn_layout.addStretch()
        layout.addLayout(tree_btn_layout)
        
        # === FORMULAIRE ===
        form_label = QLabel("<b>📝 Formulaire</b>")
        layout.addWidget(form_label)
        
        form = QFormLayout()
        
        self.type_combo = QComboBox()
        form.addRow("Type :", self.type_combo)
        
        self.center_label = QLabel("Centre (x,y) :")
        self.center_input = QLineEdit("0.0, 0.0")
        form.addRow(self.center_label, self.center_input)
        
        self.material_combo = QComboBox()
        form.addRow("Matériau :", self.material_combo)
        
        self.model_combo = QComboBox()
        form.addRow("Modèle :", self.model_combo)
        
        self.color_input = QLineEdit("BLUEx")
        form.addRow("Couleur :", self.color_input)
        
        # Champs spécifiques
        self.radius_label = QLabel("Rayon :")
        self.radius_input = QLineEdit("0.1")
        form.addRow(self.radius_label, self.radius_input)
        
        self.hollow_check = QCheckBox("Disque creux (hollow)")
        form.addRow("", self.hollow_check)
        
        self.axes_label = QLabel("Axes (axe1, axe2) :")
        self.axes_input = QLineEdit("2.0, 0.05")
        form.addRow(self.axes_label, self.axes_input)
        
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
        
        self.ovoid_label = QLabel("Rayons (ra, rb) :")
        self.ovoid_input = QLineEdit("1.0, 0.5")
        form.addRow(self.ovoid_label, self.ovoid_input)
        
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
        
        # === BOUTONS ===
        btn_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("✅ Créer Avatar")
        self.create_btn.setStyleSheet("font-weight: bold;")
        self.create_btn.clicked.connect(self._on_create)
        btn_layout.addWidget(self.create_btn)
        
        self.update_btn = QPushButton("💾 Enregistrer Modifications")
        self.update_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        self.update_btn.clicked.connect(self._on_update)
        self.update_btn.setVisible(False)
        btn_layout.addWidget(self.update_btn)
        
        self.cancel_btn = QPushButton("❌ Annuler")
        self.cancel_btn.clicked.connect(self._on_cancel_edit)
        self.cancel_btn.setVisible(False)
        btn_layout.addWidget(self.cancel_btn)
        
        clear_btn = QPushButton("🔄 Réinitialiser")
        clear_btn.clicked.connect(self._clear_form)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self._update_avatar_types()
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.tree.itemDoubleClicked.connect(self._on_edit_from_tree)
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
        
        center_default = "0.0, 0.0" if dim == 2 else "0.0, 0.0, 0.0"
        self.center_input.setText(center_default)
        self.center_label.setText(f"Centre ({'x,y' if dim == 2 else 'x,y,z'}) :")
        
        self._on_type_changed(self.type_combo.currentText())
    
    def _on_type_changed(self, avatar_type):
        """Affiche/masque les champs selon le type"""
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
        """Affiche vertices ou nb_vertices"""
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
    
    def _show_context_menu(self, position):
        """Menu contextuel"""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        avatar_idx = item.data(0, Qt.ItemDataRole.UserRole)
        avatar = self.controller.get_avatar(avatar_idx)
        
        if avatar and avatar.origin == AvatarOrigin.MANUAL:
            edit_action = menu.addAction("✏️ Modifier")
            edit_action.triggered.connect(self._on_edit_from_tree)
        
        delete_action = menu.addAction("🗑️ Supprimer")
        delete_action.triggered.connect(self._on_delete)
        
        menu.addSeparator()
        info_action = menu.addAction("ℹ️ Informations")
        info_action.triggered.connect(self._show_info)
        
        menu.exec(self.tree.viewport().mapToGlobal(position))
    
    def _on_create(self):
        """Crée l'avatar"""
        try:
            avatar = self._build_avatar_from_form()
            avatar.origin = AvatarOrigin.MANUAL
            
            idx = self.controller.add_avatar(avatar)
            self.avatar_created.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"✅ Avatar #{idx} créé")
            self._clear_form()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def _on_edit_from_tree(self):
        """Charge pour édition"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un avatar")
            return
        
        avatar_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        avatar = self.controller.get_avatar(avatar_idx)
        
        if not avatar:
            return
        
        if avatar.origin != AvatarOrigin.MANUAL:
            QMessageBox.warning(
                self, "Modification impossible",
                "Seuls les avatars créés manuellement peuvent être modifiés.\n"
                "Cet avatar a été généré automatiquement."
            )
            return
        
        self.load_for_edit(avatar_idx, avatar)
    
    def _on_update(self):
        """Met à jour"""
        try:
            avatar = self._build_avatar_from_form()
            avatar.origin = AvatarOrigin.MANUAL
            
            self.controller.update_avatar(self.current_edit_index, avatar)
            self.avatar_updated.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", "✅ Avatar modifié")
            self._on_cancel_edit()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Modification échouée :\n{e}")
    
    def _on_delete(self):
        """Supprime"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un avatar")
            return
        
        avatar_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        avatar = self.controller.get_avatar(avatar_idx)
        
        if not avatar:
            return
        
        is_used, refs = self.controller.is_avatar_used(avatar_idx)
        
        if is_used:
            refs_text = "\n• ".join(refs)
            QMessageBox.warning(
                self, "Avatar Référencé",
                f"Cet avatar est référencé par :\n\n• {refs_text}\n\n"
                f"Supprimez d'abord ces références."
            )
            return
        
        reply = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer l'avatar #{avatar_idx} ({avatar.avatar_type.value}) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.controller.remove_avatar(avatar_idx):
                self.avatar_deleted.emit()
                self.refresh()
                QMessageBox.information(self, "Succès", "✅ Avatar supprimé")
                if self.current_edit_index == avatar_idx:
                    self._on_cancel_edit()
    
    def _show_info(self):
        """Affiche infos"""
        selected = self.tree.currentItem()
        if not selected:
            return
        
        avatar_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        avatar = self.controller.get_avatar(avatar_idx)
        if not avatar:
            return
        
        is_used, refs = self.controller.is_avatar_used(avatar_idx)
        
        center_str = ', '.join(str(x) for x in avatar.center)
        
        info = f"<h3>Avatar #{avatar_idx}</h3>"
        info += f"<b>Type :</b> {avatar.avatar_type.value}<br>"
        info += f"<b>Centre :</b> ({center_str})<br>"
        info += f"<b>Matériau :</b> {avatar.material_name}<br>"
        info += f"<b>Modèle :</b> {avatar.model_name}<br>"
        info += f"<b>Couleur :</b> {avatar.color}<br>"
        info += f"<b>Origine :</b> {avatar.origin.value}<br>"
        
        if avatar.radius:
            info += f"<b>Rayon :</b> {avatar.radius}<br>"
        
        if is_used:
            info += f"<br><b>✅ Référencé par :</b><br>• {', '.join(refs)}"
        else:
            info += "<br><i>❌ Non référencé</i>"
        
        QMessageBox.information(self, f"Infos : Avatar #{avatar_idx}", info)
    
    def _on_cancel_edit(self):
        """Annule édition"""
        self.current_edit_index = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self._clear_form()
    
    def _clear_form(self):
        """Réinitialise"""
        dim = self.controller.state.dimension
        self.center_input.setText("0.0, 0.0" if dim == 2 else "0.0, 0.0, 0.0")
        self.color_input.setText("BLUEx")
        self.radius_input.setText("0.1")
        self.hollow_check.setChecked(False)
    
    def _build_avatar_from_form(self) -> Avatar:
        """Construit un avatar depuis le formulaire"""
        center = [float(x.strip()) for x in self.center_input.text().split(',')]
        avatar_type = AvatarType(self.type_combo.currentText())
        
        avatar = Avatar(
            avatar_type=avatar_type,
            center=center,
            material_name=self.material_combo.currentText(),
            model_name=self.model_combo.currentText(),
            color=self.color_input.text().strip()
        )
        
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
            wall_params = {'l': float(self.wall_length_input.text())}
            
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
        
        return avatar
    
    def load_for_edit(self, index: int, avatar: Avatar):
        """Charge pour édition"""
        self.current_edit_index = index
        
        self.type_combo.setCurrentText(avatar.avatar_type.value)
        
        center_str = ", ".join(str(x) for x in avatar.center)
        self.center_input.setText(center_str)
        
        self.material_combo.setCurrentText(avatar.material_name)
        self.model_combo.setCurrentText(avatar.model_name)
        self.color_input.setText(avatar.color)
        
        if avatar.radius:
            self.radius_input.setText(str(avatar.radius))
        if avatar.is_hollow:
            self.hollow_check.setChecked(True)
        if avatar.axis:
            self.axes_input.setText(f"{avatar.axis['axe1']}, {avatar.axis['axe2']}")
        if avatar.nb_vertices:
            self.nb_vertices_input.setText(str(avatar.nb_vertices))
        if avatar.vertices:
            self.vertices_input.setText(str(avatar.vertices))
        
        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.cancel_btn.setVisible(True)
    
    def refresh(self):
        """Rafraîchit"""
        self.tree.clear()
        
        self.material_combo.clear()
        materials = self.controller.get_materials()
        self.material_combo.addItems([m.name for m in materials])
        
        self.model_combo.clear()
        models = self.controller.get_models()
        self.model_combo.addItems([m.name for m in models])
        
        self._update_avatar_types()
        
        all_avatars = self.controller.state.avatars
        
        for real_index, avatar in enumerate(all_avatars):
            center_str = ', '.join(f"{x:.2f}" for x in avatar.center)
            
            origin_str = ""
            if avatar.origin == AvatarOrigin.LOOP:
                origin_str = "Boucle"
            elif avatar.origin == AvatarOrigin.GRANULO:
                origin_str = "Granulo"
            else:
                origin_str = "Manuel"
            
            item = QTreeWidgetItem([
                str(real_index),
                avatar.avatar_type.value,
                avatar.color,
                f"({center_str})",
                origin_str
            ])
            
            item.setData(0, Qt.ItemDataRole.UserRole, real_index)
            
            if avatar.origin != AvatarOrigin.MANUAL:
                item.setForeground(0, QBrush(QColor(100, 100, 100)))
            
            self.tree.addTopLevelItem(item)