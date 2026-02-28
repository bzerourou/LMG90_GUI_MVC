# ============================================================================
# ModèleTab
# ============================================================================
"""
Onglet de gestion des modèles avec création, modification et suppression.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QLabel, QGroupBox, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import Model
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController


class ModelTab(QWidget):
    """Onglet de gestion des modèles"""
    dimension_changed = pyqtSignal(int)
    model_created = pyqtSignal()
    model_updated = pyqtSignal()
    model_deleted = pyqtSignal()
    
    ELEMENTS_2D = ["Rxx2D", 
                   "T3xxx","T3Lxx", "T33xx",  
                   "T6xxx", "T63xx",
                   "Q4xxx", "Q4P0x", "Q44xx",
                   "Q8xxx", "Q8Rxx", "Q84xx",
                   "Q9xxx", 
                   "BARxx", 
                   "SPRG2",
                   "S2xth"]
    
    ELEMENTS_3D = ["Rxx3D", 
                   "TE4xx", "TE4Lx", "TE44x",
                   "TE10x", "TE104",
                    "H8xxx", "H88xx",
                    "H20xx", "H20Rx", "H208x",
                    "PRI6x", "SHB6x",
                    "PRI15",  
                    "DKTxx", 
                    "BARxx", 
                    "SPRG3" ]
    
    ELEMENT_OPTIONS = {
        # ── 2D ───────────────────────────────────────────────────────────────
        "T3xxx": ["kinematic", "formulation", "mass_storage"],
        "T3Lxx": ["kinematic", "formulation", "mass_storage"],
        "T33xx": ["kinematic", "formulation", "mass_storage"],
        "T6xxx": ["kinematic", "formulation", "mass_storage"],
        "T63xx": ["kinematic", "formulation", "mass_storage"],
        "DKTxx": ["kinematic", "formulation", "mass_storage"],
        "Q4xxx": ["kinematic", "formulation", "mass_storage"],
        "Q4P0x": ["kinematic", "formulation", "mass_storage"],
        "Q44xx": ["kinematic", "formulation", "mass_storage"],
        "Q8xxx": ["kinematic", "formulation", "mass_storage"],
        "Q8Rxx": ["kinematic", "formulation", "mass_storage"],
        "Q84xx": ["kinematic", "formulation", "mass_storage"],
        "Q9xxx": ["kinematic", "formulation", "mass_storage"],
        "BARxx": ["kinematic", "formulation", "mass_storage"],
        "SPRG2": ["kinematic", "formulation", "mass_storage"],
        "S2xth": ["kinematic", "formulation", "mass_storage"],
        # ── 3D ───────────────────────────────────────────────────────────────
        "TE4xx": ["kinematic", "formulation", "mass_storage"],
        "TE4Lx": ["kinematic", "formulation", "mass_storage"],
        "TE44x": ["kinematic", "formulation", "mass_storage"],
        "TE10x": ["kinematic", "formulation", "mass_storage"],
        "TE104":  ["kinematic", "formulation", "mass_storage"],
        "H8xxx": ["kinematic", "formulation", "mass_storage"],
        "H88xx": ["kinematic", "formulation", "mass_storage"],
        "H20xx": ["kinematic", "formulation", "mass_storage"],
        "H20Rx": ["kinematic", "formulation", "mass_storage"],
        "H208x": ["kinematic", "formulation", "mass_storage"],
        "PRI6x": ["kinematic", "formulation", "mass_storage"],
        "SHB6x": ["kinematic", "formulation", "mass_storage"],
        "PRI15": ["kinematic", "formulation", "mass_storage"],
        "SPRG3": ["kinematic", "formulation", "mass_storage"],
    }
    
    OPTION_VALUES = {
        "kinematic": ["small", "large"],
        "formulation": ["UpdtL", "TotaL"],
        "mass_storage": ["lump_", "coher"],
        "material": ["elas_", "elasd", "J2iso", "J2mix", "kvisc"],
        "anisotropy": ["iso__", "ortho"],
        "external_model": ["MatL_", "Demfi", "Umat_", "no___", "yes__"],
        
    }
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.current_edit_name = None
        self.option_combos = {}
        self._setup_ui()
        self._connect_signals()
        self.refresh()
    
    def _setup_ui(self):
        """Configure l'interface"""
        #Ajouter un scroll
        main_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        scroll_widget.setLayout(layout)
        
        # === ARBRE ===
        tree_label = QLabel("<b>📋 Liste des Modèles</b>")
        layout.addWidget(tree_label)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nom", "Type", "Élément", "Dimension"])
        self.tree.setColumnWidth(0, 100)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 100)
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
        
        self.name_input = QLineEdit()
        self.name_input.setMaxLength(5)
        self.name_input.setText("rigid")
        form.addRow("Nom (max 5 car.) :", self.name_input)
        
        self.physics_combo = QComboBox()
        self.physics_combo.addItems(["MECAx"])
        form.addRow("Physique :", self.physics_combo)
        
        self.dimension_combo = QComboBox()
        self.dimension_combo.addItems(["2", "3"])
        form.addRow("Dimension :", self.dimension_combo)
        
        self.element_combo = QComboBox()
        form.addRow("Élément :", self.element_combo)
        
        layout.addLayout(form)
        
        # === OPTIONS ===
        self.options_group = QGroupBox("Options du modèle")
        self.options_layout = QFormLayout()
        self.options_group.setLayout(self.options_layout)
        self.options_group.setVisible(False)
        layout.addWidget(self.options_group)
        
        # === BOUTONS ===
        btn_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("✅ Créer Modèle")
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
        
        # fin du scroll
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
        
        self._update_elements()
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.tree.itemDoubleClicked.connect(self._on_edit_from_tree)
        self.dimension_combo.currentTextChanged.connect(self._on_dimension_changed)
        self.element_combo.currentTextChanged.connect(self._on_element_changed)
        #self.dimension_changed.connect(lambda dim : self.on_dimension_combo_changed(dim))

    
    def _on_dimension_changed(self, dim_text):
        """Quand la dimension change"""
        dim = int(dim_text)
        self._update_elements()
        self.controller.state.dimension = int(dim_text)    
        self.dimension_changed.emit(int(dim_text))
        

    def _update_elements(self):
        """Met à jour la liste des éléments selon dimension"""
        dim = int(self.dimension_combo.currentText())
        elements = self.ELEMENTS_2D if dim == 2 else self.ELEMENTS_3D
        
        current = self.element_combo.currentText()
        self.element_combo.blockSignals(True)
        self.element_combo.clear()
        self.element_combo.addItems(elements)
        
        if current in elements:
            self.element_combo.setCurrentText(current)
        
        self.element_combo.blockSignals(False)
        self._on_element_changed(self.element_combo.currentText())
    
    def _on_element_changed(self, element):
        """Quand l'élément change"""
        self.name_input.setText("rigid")
        for i in reversed(range(self.options_layout.count())):
            item = self.options_layout.takeAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        self.option_combos.clear()
        
        if element in ["Rxx2D", "Rxx3D"]:
            self.options_group.setVisible(False)
            return
        
        self.options_group.setVisible(True)
        
        specific_options = self.ELEMENT_OPTIONS.get(element, [])
        for opt_name in specific_options:
            combo = QComboBox()
            combo.addItems(self.OPTION_VALUES.get(opt_name, []))
            self.options_layout.addRow(f"{opt_name} :", combo)
            self.option_combos[opt_name] = combo
        
        for opt_name in ["material", "anisotropy", "external_model"]:
            combo = QComboBox()
            combo.addItems(self.OPTION_VALUES[opt_name])
            self.options_layout.addRow(f"{opt_name} :", combo)
            self.option_combos[opt_name] = combo
    
    
    def _show_context_menu(self, position):
        """Menu contextuel"""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        edit_action = menu.addAction("✏️ Modifier")
        edit_action.triggered.connect(self._on_edit_from_tree)
        
        delete_action = menu.addAction("🗑️ Supprimer")
        delete_action.triggered.connect(self._on_delete)
        
        menu.addSeparator()
        info_action = menu.addAction("ℹ️ Informations")
        info_action.triggered.connect(self._show_info)
        
        menu.exec(self.tree.viewport().mapToGlobal(position))
    
    def _on_create(self):
        """Crée un modèle"""
        try:
            options = {k: v.currentText() for k, v in self.option_combos.items() if v.currentText()}
            _DISCRETE_ELEMENTS = {"SPRG2", "SPRG3"}
            if self.element_combo.currentText() in _DISCRETE_ELEMENTS:
                options['discrete'] = "yes__"
            
            model = Model(
                name=self.name_input.text().strip(),
                physics=self.physics_combo.currentText(),
                element=self.element_combo.currentText(),
                dimension=int(self.dimension_combo.currentText()),
                options=options
            )
            
            self.controller.add_model(model)
            self.model_created.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"✅ Modèle '{model.name}' créé")
            #self._clear_form()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def _on_edit_from_tree(self):
        """Charge pour édition"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un modèle")
            return
        
        mod_name = selected.text(0)
        model = self.controller.get_model(mod_name)
        
        if model:
            self.load_for_edit(model)
    
    def _on_update(self):
        """Met à jour"""
        try:
            options = {k: v.currentText() for k, v in self.option_combos.items() if v.currentText()}
            
            model = Model(
                name=self.name_input.text().strip(),
                physics=self.physics_combo.currentText(),
                element=self.element_combo.currentText(),
                dimension=int(self.dimension_combo.currentText()),
                options=options
            )
            
            self.controller.update_model(self.current_edit_name, model)
            self.model_updated.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"✅ Modèle '{model.name}' modifié")
            self._on_cancel_edit()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Modification échouée :\n{e}")
    
    def _on_delete(self):
        """Supprime"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un modèle")
            return
        
        mod_name = selected.text(0)
        is_used, refs = self.controller.is_model_used(mod_name)
        
        if is_used:
            refs_text = "\n• ".join(refs[:10])
            if len(refs) > 10:
                refs_text += f"\n... et {len(refs) - 10} autre(s)"
            
            reply = QMessageBox.question(
                self, "⚠️ Modèle Utilisé",
                f"Le modèle '{mod_name}' est utilisé par :\n\n• {refs_text}\n\n"
                f"Continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        else:
            reply = QMessageBox.question(
                self, "Confirmer",
                f"Supprimer le modèle '{mod_name}' ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        try:
            if self.controller.remove_model(mod_name):
                self.model_deleted.emit()
                self.refresh()
                QMessageBox.information(self, "Succès", f"✅ Modèle '{mod_name}' supprimé")
                if self.current_edit_name == mod_name:
                    self._on_cancel_edit()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Suppression échouée :\n{e}")
    
    def _show_info(self):
        """Affiche infos"""
        selected = self.tree.currentItem()
        if not selected:
            return
        
        mod_name = selected.text(0)
        model = self.controller.get_model(mod_name)
        if not model:
            return
        
        is_used, refs = self.controller.is_model_used(mod_name)
        
        info = f"<h3>Modèle : {model.name}</h3>"
        info += f"<b>Physique :</b> {model.physics}<br>"
        info += f"<b>Élément :</b> {model.element}<br>"
        info += f"<b>Dimension :</b> {model.dimension}<br>"
        
        if model.options:
            info += "<br><b>Options :</b><br>"
            for key, value in model.options.items():
                info += f"  • {key} = {value}<br>"
        
        if is_used:
            info += f"<br><b>✅ Utilisé par :</b> {len(refs)} avatar(s)"
        else:
            info += "<br><i>❌ Non utilisé</i>"
        
        QMessageBox.information(self, f"Infos : {mod_name}", info)
    
    def _on_cancel_edit(self):
        """Annule édition"""
        self.current_edit_name = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        #self._clear_form()
    
    def _clear_form(self):
        """Réinitialise"""
        self.name_input.clear()
        self.physics_combo.setCurrentIndex(0)
        self.dimension_combo.setCurrentIndex(0)
        self.name_input.setFocus()
    
    def load_for_edit(self, model: Model):
        """Charge pour édition"""
        if not model : 
            return 
        self.current_edit_name = model.name
        
        self.name_input.setText(model.name)
        self.physics_combo.setCurrentText(model.physics)
        self.dimension_combo.setCurrentText(str(model.dimension))
        
        self._update_elements()
        
        elem_idx = self.element_combo.findText(model.element)
        if elem_idx >= 0:
            self.element_combo.setCurrentIndex(elem_idx)

        self._on_element_changed(model.element)
        
        if model.options:
            for opt_name, opt_value in model.options.items():
                if opt_name in self.option_combos:
                    combo = self.option_combos[opt_name]
                    index = combo.findText(opt_value)
                    if index >= 0:
                        combo.setCurrentIndex(index)
        
        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.cancel_btn.setVisible(True)
        
        self.name_input.setFocus()
        self.name_input.selectAll()
    
    def refresh(self):
        """Rafraîchit"""
        self.tree.clear()
        models = self.controller.get_models()
        
        for mod in models:
            item = QTreeWidgetItem([
                mod.name,
                mod.physics,
                mod.element,
                str(mod.dimension)
            ])
            
            is_used, _ = self.controller.is_model_used(mod.name)
            if is_used:
                item.setForeground(0, QBrush(QColor(0, 100, 0)))
            
            self.tree.addTopLevelItem(item)