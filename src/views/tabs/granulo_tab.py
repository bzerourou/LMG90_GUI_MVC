# ============================================================================
# Onglet Granulométrie
# ============================================================================
"""
Onglet pour générer des distributions granulométriques.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QCheckBox, QLabel, QGroupBox,
    QTreeWidget, QTreeWidgetItem, QMenu, QHBoxLayout, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import GranuloGeneration
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController


class GranuloTab(QWidget):
    """Onglet granulométrie"""
    
    granulo_generated = pyqtSignal()
    granulo_deleted = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        # ✅ AJOUTER UN SCROLL AREA PRINCIPAL
        main_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        scroll_widget.setLayout(layout)
        
        # === ARBRE ===
        tree_label = QLabel("<b>📋 Dépôts Granulométriques Existants</b>")
        layout.addWidget(tree_label)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["#", "Type", "Nb Part.", "Rayons", "Groupe"])
        self.tree.setColumnWidth(0, 40)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 80)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(150)
        layout.addWidget(self.tree)
        
        tree_btn_layout = QHBoxLayout()
        delete_tree_btn = QPushButton("🗑️ Supprimer Sélection")
        delete_tree_btn.clicked.connect(self._on_delete)
        tree_btn_layout.addWidget(delete_tree_btn)
        tree_btn_layout.addStretch()
        layout.addLayout(tree_btn_layout)
        
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
        
        self.params_widget = QWidget()
        self.params_layout = QFormLayout()
        self.params_widget.setLayout(self.params_layout)
        container_layout.addWidget(self.params_widget)
        
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
        
        # === BOUTONS ===
        btn_layout = QHBoxLayout()
        
        gen_btn = QPushButton("✅ Générer le Dépôt")
        gen_btn.setStyleSheet("font-weight: bold; padding: 10px;")
        gen_btn.clicked.connect(self._on_generate)
        btn_layout.addWidget(gen_btn)
        
        clear_btn = QPushButton("🔄 Réinitialiser")
        clear_btn.clicked.connect(self._clear_form)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # ✅ FIN DU LAYOUT SCROLLABLE
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
        
        self._update_container_params("Box2D")
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.shape_combo.currentTextChanged.connect(self._update_container_params)
        self.tree.itemDoubleClicked.connect(self._show_info)
    
    def _update_container_params(self, shape):
        """Met à jour les paramètres selon le conteneur"""
        while self.params_layout.count() > 0:
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        
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
    
    def _update_avatar_types(self, dimension):
        """Met à jour les types d'avatars selon la dimension"""
        self.avatar_combo.clear()
        if dimension == 2:
            avatar_types = ["rigidDisk"]
        else:  # dimension == 3
            avatar_types = ["rigidSphere", "rigidCylinder"]
        
        for avatar_type in avatar_types:
            self.avatar_combo.addItem(avatar_type, avatar_type)
    
    def _show_context_menu(self, position):
        """Menu contextuel"""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        delete_action = menu.addAction("🗑️ Supprimer")
        delete_action.triggered.connect(self._on_delete)
        
        menu.addSeparator()
        
        info_action = menu.addAction("ℹ️ Informations")
        info_action.triggered.connect(self._show_info)
        
        menu.exec(self.tree.viewport().mapToGlobal(position))
    
    def _on_generate(self):
        """Génère la granulométrie"""
        try:
            nb = int(self.nb_input.text())
            if nb <= 0 :
                raise ValidationError("Le nombre de particules doit être > 0")
            if nb > 10000:
                raise ValidationError("Maximum 50000 particules (performance)")
            rmin = float(self.rmin_input.text())
            rmax = float(self.rmax_input.text())
            if rmin <= 0:
                raise ValidationError("Le rayon minimum doit être > 0")
            
            if rmax <= rmin:
                raise ValidationError("Le rayon maximum doit être > rayon minimum")
            
            if rmax / rmin > 100:
                raise ValidationError("Le ratio Rmax/Rmin dépasse 100 (trop élevé)")
            material = self.material_combo.currentText()
            model = self.avatar_combo.currentData()
            if not self.material_combo.currentText():
                raise ValidationError("Sélectionnez un matériau")
            
            if not self.model_combo.currentText():
                raise ValidationError("Sélectionnez un modèle")
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
            
            seed_text = self.seed_input.text().strip()
            seed = int(seed_text) if seed_text else None
            
            config = GranuloGeneration(
                nb_particles= nb,
                radius_min=rmin,
                radius_max=rmax,
                container_type=shape,
                container_params=container_params,
                model_name=self.model_combo.currentText(),
                material_name=material,
                avatar_type=model,
                color=self.color_input.text().strip(),
                seed=seed,
                group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
            )
            
            indices = self.controller.generate_granulo(config)
            
            self.granulo_generated.emit()
            self.refresh()
            
            msg = f"✅ {len(indices)} particules générées"
            if config.group_name:
                msg += f"\nGroupe : {config.group_name}"
            QMessageBox.information(self, "Succès", msg)
            
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération échouée :\n{e}")
    
    def _on_delete(self):
        """Supprime le dépôt sélectionné"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un dépôt")
            return
        
        granulo_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        granulo = self.controller.get_granulo(granulo_idx)
        
        if not granulo:
            return
        
        nb_avatars = len(granulo.generated_indices)
        
        reply = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer le dépôt #{granulo_idx + 1} ?\n\n"
            f"⚠️ Cela supprimera également {nb_avatars} avatar(s) généré(s).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.controller.remove_granulo(granulo_idx):
                self.granulo_deleted.emit()
                self.refresh()
                QMessageBox.information(self, "Succès", "✅ Dépôt et avatars supprimés")
    
    def _show_info(self):
        """Affiche infos"""
        selected = self.tree.currentItem()
        if not selected:
            return
        
        granulo_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        granulo = self.controller.get_granulo(granulo_idx)
        
        if not granulo:
            return
        
        info = f"<h3>Dépôt Granulométrique #{granulo_idx + 1}</h3>"
        info += f"<b>Conteneur :</b> {granulo.container_type}<br>"
        info += f"<b>Particules demandées :</b> {granulo.nb_particles}<br>"
        info += f"<b>Particules générées :</b> {len(granulo.generated_indices)}<br>"
        info += f"<b>Rayons :</b> [{granulo.radius_min}, {granulo.radius_max}]<br>"
        info += f"<b>Type d'avatar :</b> {granulo.avatar_type}<br>"
        info += f"<b>Matériau :</b> {granulo.material_name}<br>"
        info += f"<b>Modèle :</b> {granulo.model_name}<br>"
        info += f"<b>Couleur :</b> {granulo.color}<br>"
        
        if granulo.seed:
            info += f"<b>Seed :</b> {granulo.seed}<br>"
        
        if granulo.group_name:
            info += f"<b>Groupe :</b> {granulo.group_name}<br>"
        
        info += f"<br><b>Paramètres conteneur :</b><br>"
        for key, value in granulo.container_params.items():
            info += f"  • {key} = {value}<br>"
        
        QMessageBox.information(self, f"Infos : Dépôt #{granulo_idx + 1}", info)
    
    def _clear_form(self):
        """Réinitialise"""
        self.nb_input.setText("200")
        self.rmin_input.setText("0.05")
        self.rmax_input.setText("0.15")
        self.seed_input.clear()
        self.color_input.setText("BLUEx")
        self.group_name_input.setText("depot_granulo")
        self.store_check.setChecked(True)
    
    def refresh(self):
        """Rafraîchit"""
        self.tree.clear()
        
        self.material_combo.clear()
        materials = self.controller.get_materials()
        self.material_combo.addItems([m.name for m in materials])
        
        self.model_combo.clear()
        models = self.controller.get_models()
        self.model_combo.addItems([m.name for m in models])
        
        self.avatar_combo.clear()
        dim = self.controller.state.dimension
        if dim == 2:
            avatar_types = ["rigidDisk"]
        else:
            avatar_types = ["rigidSphere", "rigidCylinder"]
        for avatar_type in avatar_types:
            self.avatar_combo.addItem(avatar_type, avatar_type)
        
        granulos = self.controller.state.granulo_generations
        
        for i, gen in enumerate(granulos):
            nb_generated = len(gen.generated_indices)
            
            item = QTreeWidgetItem([
                str(i + 1),
                gen.container_type,
                f"{nb_generated}/{gen.nb_particles}",
                f"[{gen.radius_min:.3f}, {gen.radius_max:.3f}]",
                gen.group_name or "N/A"
            ])
            
            item.setData(0, Qt.ItemDataRole.UserRole, i)
            
            if nb_generated < gen.nb_particles:
                item.setForeground(2, QBrush(QColor(255, 100, 0)))
            
            self.tree.addTopLevelItem(item)