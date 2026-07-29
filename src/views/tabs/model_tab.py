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
    ELEMENTS_2D_THER = [
        "Rxx2D",
        "T3xxx", "T6xxx", "DKTxx",
        "Q4xxx", "Q4P0x", "Q8xxx", "Q8Rxx",
        "SPRG2", "S2xth",
    ]
    ELEMENTS_3D_THER = [
        "Rxx3D",
        "TE4xx", "TE10x",
        "H8xxx", "H20xx", "H20Rx",
        "PRI6x", "PRI15",
        "SPRG3",
    ]
    ELEMENTS_2D_PORO = [
        "T33xx", "T63xx", "Q44xx", "Q84xx",
    ]
    ELEMENTS_3D_PORO = [
        "TE44x", "TE104", "H88xx", "H208x",
    ]
    ELEMENTS_2D_MULTI = [
        "T33xx", "T63xx", "Q44xx", "Q84xx",
    ]
    ELEMENTS_3D_MULTI = [
        "TE44x", "TE104", "H8xxx", "H88xx", "H208x",
    ]
 
    # ── Correspondance géométrie → éléments (utilisé pour info/documentation) ─
    GEO2ELEMENT = {
        'Point' : ('Rxx2D', 'Rxx3D'),
        'S2xxx' : ('SPRG2', 'SPRG3', 'BARxx', 'S2xth'),
        'S3xxx' : (),
        'Q4xxx' : ('Q4xxx', 'Q4P0x', 'Q44xx'),
        'T3xxx' : ('T3xxx', 'T3Lxx', 'DKTxx', 'T33xx'),
        'Q8xxx' : ('Q8xxx', 'Q8Rxx', 'Q84xx'),
        'Q9xxx' : ('Q9xxx',),
        'T6xxx' : ('T6xxx', 'T63xx'),
        'TE4xx' : ('TE4xx', 'TE4Lx', 'TE44x'),
        'TE10x' : ('TE10x', 'TE104'),
        'H8xxx' : ('H8xxx', 'H88xx'),
        'H20xx' : ('H20xx', 'H20Rx', 'H208x'),
        'PRI6x' : ('PRI6x', 'SHB6x'),
        'PRI15' : ('PRI15',),
    }
 
    # ── Correspondance physique → listes d'éléments ──────────────────────────
    ELEMENTS_BY_PHYSICS = {
        "MECAx": {2: ELEMENTS_2D,      3: ELEMENTS_3D     },
        "THERx": {2: ELEMENTS_2D_THER, 3: ELEMENTS_3D_THER},
        "POROx": {2: ELEMENTS_2D_PORO, 3: ELEMENTS_3D_PORO},
        "MULTI": {2: ELEMENTS_2D_MULTI,3: ELEMENTS_3D_MULTI},
    }
 
    # ── Options par élément thermique ────────────────────────────────────────
    # Rigides (Rxx) = aucune option ; S2xth = thermique 1D (masse seulement)
    ELEMENT_OPTIONS_THER = {
        "Rxx2D":  [],
        "Rxx3D":  [],
        "T3xxx":  ["capacity_storage", "formulation", "convection_type"],
        "T6xxx":  ["capacity_storage", "formulation", "convection_type"],
        "DKTxx":  ["capacity_storage", "formulation", "convection_type"],
        "Q4xxx":  ["capacity_storage", "formulation", "convection_type"],
        "Q4P0x":  ["capacity_storage", "formulation", "convection_type"],
        "Q8xxx":  ["capacity_storage", "formulation", "convection_type"],
        "Q8Rxx":  ["capacity_storage", "formulation", "convection_type"],
        "SPRG2":  ["capacity_storage"],
        "S2xth":  ["capacity_storage", "formulation", "convection_type"],
        "TE4xx":  ["capacity_storage", "formulation", "convection_type"],
        "TE10x":  ["capacity_storage", "formulation", "convection_type"],
        "H8xxx":  ["capacity_storage", "formulation", "convection_type"],
        "H20xx":  ["capacity_storage", "formulation", "convection_type"],
        "H20Rx":  ["capacity_storage", "formulation", "convection_type"],
        "PRI6x":  ["capacity_storage", "formulation", "convection_type"],
        "PRI15":  ["capacity_storage", "formulation", "convection_type"],
        "SPRG3":  ["capacity_storage"],
    }
    # ── Valeurs des options thermiques ────────────────────────────────────────
    OPTION_VALUES_THER = {
        "capacity_storage":   ["coher"],
        "formulation":     ["class"],
        "external_model": [ "no___", "yes__"],
        "convection_type": ["supg_",  "char_", "center"]
    }
 
    # ── Options disponibles par élément ──────────────────────────────────────
    # Les éléments rigides (Rxx2D / Rxx3D) n'ont aucune option.
    # Les éléments sans entrée ici affichent uniquement les options communes
    # (material, anisotropy, external_model).
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

    # ── Options par élément poro ────────────────────────────────────────
    # Rigides (Rxx) = aucune option ; S2xth = thermique 1D (masse seulement)
    ELEMENT_OPTIONS_PORO = {
        "T33xx":  ["kinematic", "mass_storage", "capacity_storage"],
        "T63xx":  ["kinematic", "mass_storage", "capacity_storage"],
        "Q44xx":  ["kinematic", "mass_storage", "capacity_storage"],
        "Q84xx":  ["kinematic", "mass_storage", "capacity_storage"],
        "H88xx":  ["kinematic", "mass_storage", "capacity_storage"],
        "H208x":  ["kinematic", "mass_storage", "capacity_storage"],
        "TE44x":  ["kinematic", "mass_storage", "capacity_storage"],
        "TE104":  ["kinematic", "mass_storage", "capacity_storage"],

    }
    # ── Valeurs des options thermiques ────────────────────────────────────────
    OPTION_VALUES_PORO = {
        "kinematic": ["small", "large"],
        "mass_storage": ["lump_", "coher"],
        "capacity_storage":   ["lump_","coher"],
        "material": ["elas_", "elasd", "J2iso", "J2mix", "kvisc"],
        "anisotropy": ["iso__", "ortho"],
        "external_model": ["MatL_", "Demfi", "Umat_", "no___", "yes__"],
        "physical_type" : ["fluid", "solid"],
        "convection_type": ["supg_",  "char_", "center"]
        
    }

    ELEMENT_OPTIONS_MULTI = {
        "T33xx":  ["kinematic", "mass_storage", "formulation"],
        "T63xx":  ["kinematic", "mass_storage", "formulation"],
        "Q44xx":  ["kinematic", "mass_storage", "formulation"],
        "Q84xx":  ["kinematic", "mass_storage", "formulation"],
        "H8xxx":  ["kinematic", "mass_storage", "formulation"],
        "H88xx":  ["kinematic", "mass_storage", "formulation"],
        "H208x":  ["kinematic", "mass_storage", "formulation"],
        "TE44x":  ["kinematic", "mass_storage", "formulation"],
        "TE104":  ["kinematic", "mass_storage", "formulation"],
    }

    OPTION_VALUES_MULTI = {
        "kinematic": ["small", "large"],
        "mass_storage": ["lump_", "coher"],
        "material": ["elas_", "elasd", "J2iso", "J2mix", "kvisc"],
        "anisotropy": ["iso__", "ortho"],
        "external_model": ["no___", "yes__"],
        "fluid_comp_storage": ["lump_", "coher"],
        "formulation": ["UpdtL", "TotaL"],
        "convection_type": ["supg_",  "char_", "center"]
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
        self.physics_combo.addItems(["MECAx", "THERx", "POROx", "MULTI"])
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
        self.physics_combo.currentTextChanged.connect(self._on_physics_changed)
        self.dimension_combo.currentTextChanged.connect(self._on_dimension_changed)
        self.element_combo.currentTextChanged.connect(self._on_element_changed)
        #self.dimension_changed.connect(lambda dim : self.on_dimension_combo_changed(dim))
 
    
    def _on_dimension_changed(self, dim_text):
        """Quand la dimension change"""
        dim = int(dim_text)

        ok, reasons = self.controller.can_change_dimension(dim)
        if not ok:
            reply = QMessageBox.question(
                self, "⚠️ Changement de dimension",
                "Changer la dimension du projet peut invalider des "
                "éléments déjà créés :\n\n• " + "\n• ".join(reasons) +
                "\n\nContinuer quand même ?\n"
                "(les éléments incompatibles ne seront PAS supprimés "
                "automatiquement — vérifiez-les manuellement après ce changement)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                # Revenir à l'ancienne valeur dans le combo sans redéclencher le signal
                self.dimension_combo.blockSignals(True)
                self.dimension_combo.setCurrentText(str(self.controller.state.dimension))
                self.dimension_combo.blockSignals(False)
                return
            self.controller.set_dimension(dim, force=True)
        else:
            self.controller.set_dimension(dim)

        self._update_elements()
        self.dimension_changed.emit(dim)
 
    def _on_physics_changed(self, _):
        """Quand la physique change — recharge la liste d'éléments."""
        self._update_elements()
 
    def _update_elements(self):
        """Met à jour la liste des éléments selon dimension ET physique."""
        dim     = int(self.dimension_combo.currentText())
        physics = self.physics_combo.currentText()
 
        by_dim   = self.ELEMENTS_BY_PHYSICS.get(physics, self.ELEMENTS_BY_PHYSICS["MECAx"])
        elements = by_dim.get(dim, [])
 
        current = self.element_combo.currentText()
        self.element_combo.blockSignals(True)
        self.element_combo.clear()
        self.element_combo.addItems(elements)
 
        if current in elements:
            self.element_combo.setCurrentText(current)
 
        self.element_combo.blockSignals(False)
        self._on_element_changed(self.element_combo.currentText())
    
    def _on_element_changed(self, element):
        """Quand l'élément change — met à jour les options affichées."""
        self.name_input.setText("rigid")
 
        # Nettoyer les options précédentes
        for i in reversed(range(self.options_layout.count())):
            item = self.options_layout.takeAt(i)
            if item.widget():
                item.widget().deleteLater()
        self.option_combos.clear()
 
        physics = self.physics_combo.currentText()
 
        # ── Éléments rigides : aucune option ─────────────────────────────────
        _NO_OPTIONS = {"Rxx2D", "Rxx3D"}
        if element in _NO_OPTIONS or not element:
            self.options_group.setVisible(False)
            return
 
        self.options_group.setVisible(True)
 
        if physics == "THERx":
            # ── Options thermiques ────────────────────────────────────────────
            specific_options = self.ELEMENT_OPTIONS_THER.get(element, ["mass_storage"])
            for opt_name in specific_options:
                combo = QComboBox()
                combo.addItems(self.OPTION_VALUES_THER.get(opt_name, []))
                self.options_layout.addRow(f"{opt_name} :", combo)
                self.option_combos[opt_name] = combo
            # Options communes thermiques
            for opt_name in ["external_model"]:
                combo = QComboBox()
                combo.addItems(self.OPTION_VALUES_THER[opt_name])
                self.options_layout.addRow(f"{opt_name} :", combo)
                self.option_combos[opt_name] = combo
        elif physics == "POROx":
            # ── Options poro ────────────────────────────────────────────
            specific_options = self.ELEMENT_OPTIONS_PORO.get(element, ["mass_storage", "capacity_storage"])
            for opt_name in specific_options:
                combo = QComboBox()
                combo.addItems(self.OPTION_VALUES_PORO.get(opt_name, []))
                self.options_layout.addRow(f"{opt_name} :", combo)
                self.option_combos[opt_name] = combo
            # Options communes poro
            for opt_name in ["material", "anisotropy", "external_model", "physical_type", "convection_type"]:
                combo = QComboBox()
                combo.addItems(self.OPTION_VALUES_PORO[opt_name])
                self.options_layout.addRow(f"{opt_name} :", combo)
                self.option_combos[opt_name] = combo
        elif physics == "MULTI":
            # ── Options multi-physiques ────────────────────────────────────────────
            specific_options = self.ELEMENT_OPTIONS_MULTI.get(element, ["mass_storage", "capacity_storage"])
            for opt_name in specific_options:
                combo = QComboBox()
                combo.addItems(self.OPTION_VALUES_MULTI.get(opt_name, []))
                self.options_layout.addRow(f"{opt_name} :", combo)
                self.option_combos[opt_name] = combo
            # Options communes multi-physiques
            for opt_name in ["material", "anisotropy", "external_model", "fluid_comp_storage", "convection_type"]:
                combo = QComboBox()
                combo.addItems(self.OPTION_VALUES_MULTI[opt_name])
                self.options_layout.addRow(f"{opt_name} :", combo)
                self.option_combos[opt_name] = combo

        else:
            # ── Options mécaniques (MECAx) ────────────────────────────────────
            specific_options = self.ELEMENT_OPTIONS.get(element, [])
            for opt_name in specific_options:
                combo = QComboBox()
                combo.addItems(self.OPTION_VALUES.get(opt_name, []))
                self.options_layout.addRow(f"{opt_name} :", combo)
                self.option_combos[opt_name] = combo
            # Options communes mécaniques
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
            # Les éléments de type ressort/discret nécessitent l'option discrete=yes__
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