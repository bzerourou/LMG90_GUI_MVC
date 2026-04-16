# ============================================================================
# LoopTab 
# ============================================================================
"""
Onglet de gestion des boucles avec création, modification, suppression et régénération.
Style identique aux autres onglets (MaterialTab, AvatarTab, ModelTab...).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QLabel, QCheckBox, QGroupBox, QTextEdit, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import Loop, AvatarOrigin, ForLoop, AvatarType
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController
from ...views.tabs.base_tab import BaseTab
import json


class LoopTab(BaseTab):
    """Onglet génération et gestion des boucles"""
    
    loop_generated = pyqtSignal()
    loop_updated = pyqtSignal()
    loop_deleted = pyqtSignal()

    def __init__(self, controller: ProjectController):
        super().__init__(controller)
        self.controller = controller
        self.current_edit_index = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        scroll_widget.setLayout(layout)

        tree_label = QLabel("<b>📋 Liste des Boucles</b>")
        layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["#", "Type", "Nombre", "Avatar Modèle", "Groupe"])
        self.tree.setColumnWidth(0, 50)
        self.tree.setColumnWidth(1, 120)
        self.tree.setColumnWidth(2, 80)
        self.tree.setColumnWidth(3, 150)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(180)
        layout.addWidget(self.tree)

        actions_layout = QHBoxLayout()
        
        self.regen_btn = QPushButton("♻️ Régénérer sélection")
        self.regen_btn.clicked.connect(self._on_regenerate_from_tree)
        
        self.edit_btn = QPushButton("✏️ Modifier sélection")
        self.edit_btn.clicked.connect(self._on_edit_from_tree)
        
        self.delete_btn = QPushButton("🗑️ Supprimer sélection")
        self.delete_btn.clicked.connect(self._on_delete_from_tree)

        actions_layout.addWidget(self.regen_btn)
        actions_layout.addWidget(self.edit_btn)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        form_label = QLabel("<b>📝 Paramètres de la Boucle</b>")
        layout.addWidget(form_label)

        form = QFormLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Cercle", "Grille", "Ligne", "Spirale", "For"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type de boucle :", self.type_combo)

        layout.addLayout(form)

        self.classic_widget = QWidget()
        classic_layout = QVBoxLayout()
        classic_form = QFormLayout()
        
        self.avatar_combo = QComboBox()
        classic_form.addRow("Avatar à répéter :", self.avatar_combo)

        self.count_input = QLineEdit("10")
        classic_form.addRow("Nombre d'avatars :", self.count_input)

        self.radius_label = QLabel("Rayon :")
        self.radius_input = QLineEdit("2.0")
        classic_form.addRow(self.radius_label, self.radius_input)

        self.step_label = QLabel("Pas :")
        self.step_input = QLineEdit("1.0")
        classic_form.addRow(self.step_label, self.step_input)

        self.invert_check = QCheckBox("Inverser l'axe")
        classic_form.addRow("", self.invert_check)

        self.offset_x_label = QLabel("Offset X :")
        self.offset_x_input = QLineEdit("0.0")
        classic_form.addRow(self.offset_x_label, self.offset_x_input)

        self.offset_y_label = QLabel("Offset Y :")
        self.offset_y_input = QLineEdit("0.0")
        classic_form.addRow(self.offset_y_label, self.offset_y_input)

        self.spiral_label = QLabel("Facteur spirale :")
        self.spiral_input = QLineEdit("0.1")
        classic_form.addRow(self.spiral_label, self.spiral_input)
        
        classic_layout.addLayout(classic_form)
        self.classic_widget.setLayout(classic_layout)
        layout.addWidget(self.classic_widget)

        self.for_widget = QWidget()
        for_layout = QVBoxLayout()
        
        for_group = QGroupBox("⚙️ Configuration Boucle For")
        for_form = QFormLayout()
        
        self.loop_var_input = QLineEdit("i")
        for_form.addRow("Variable de boucle :", self.loop_var_input)
        
        self.start_input = QLineEdit("0")
        for_form.addRow("Début :", self.start_input)
        
        self.end_input = QLineEdit("10")
        for_form.addRow("Fin :", self.end_input)
        
        self.step_for_input = QLineEdit("1")
        for_form.addRow("Step :", self.step_for_input)
        
        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems([
            "avatar", "material", "model", "contact_law", "visibility", "dof"
        ])
        self.target_type_combo.currentTextChanged.connect(self._on_target_type_changed)
        for_form.addRow("Type d'élément :", self.target_type_combo)
        
        for_group.setLayout(for_form)
        for_layout.addWidget(for_group)
        
        template_group = QGroupBox("📝 Template JSON")
        template_layout = QVBoxLayout()
        
        help_text = QLabel(
            "💡 <b>Exemples de templates :</b><br>"
            "• Avatar : {\"avatar_type\": \"rigidDisk\", \"center\": \"[i*0.5, 0]\", \"material_name\": \"TDURx\", \"model_name\": \"rigid\", \"radius\": \"0.1+i*0.01\"}<br>"
            "• Matériau : {\"name\": \"'MAT'+str(i)\", \"material_type\": \"RIGID\", \"density\": \"2800+i*100\"}<br>"
            "• Variables : Utilisez 'i' (variable de boucle) et vos variables dynamiques"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666; font-size: 8pt; padding: 5px;")
        template_layout.addWidget(help_text)
        
        self.template_input = QTextEdit()
        self.template_input.setPlaceholderText('{"avatar_type": "rigidDisk", "center": "[i*0.5, 0]", ...}')
        self.template_input.setMaximumHeight(150)
        template_layout.addWidget(self.template_input)
        
        template_group.setLayout(template_layout)
        for_layout.addWidget(template_group)
        
        self.for_widget.setLayout(for_layout)
        self.for_widget.setVisible(False)
        layout.addWidget(self.for_widget)

        group_layout = QHBoxLayout()
        self.store_check = QCheckBox("Stocker dans un groupe")
        self.group_name_input = QLineEdit("boucle_groupe")
        group_layout.addWidget(self.store_check)
        group_layout.addWidget(self.group_name_input)
        group_layout.addStretch()
        layout.addLayout(group_layout)

        self.help_label = QLabel("Sélectionnez un type de boucle pour voir les paramètres adaptés.")
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.help_label)

        btn_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("✅ Créer boucle")
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
        
        self.add_expression_help_label(layout)
        
        layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def _connect_signals(self):
        """Connecte les signaux"""
        self.tree.itemDoubleClicked.connect(self._on_edit_from_tree)

    def _show_context_menu(self, position):
        """Affiche le menu contextuel"""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        edit_action = menu.addAction("✏️ Modifier")
        edit_action.triggered.connect(self._on_edit_from_tree)
        
        regen_action = menu.addAction("♻️ Régénérer")
        regen_action.triggered.connect(self._on_regenerate_from_tree)
        
        delete_action = menu.addAction("🗑️ Supprimer")
        delete_action.triggered.connect(self._on_delete_from_tree)
        
        menu.addSeparator()
        
        info_action = menu.addAction("ℹ️ Informations")
        info_action.triggered.connect(self._show_info)
        
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _on_type_changed(self, loop_type: str):
        """Appelé quand le type de boucle change"""
        self.radius_label.setVisible(loop_type in ["Cercle", "Spirale"])
        self.radius_input.setVisible(loop_type in ["Cercle", "Spirale"])
        
        self.step_label.setVisible(loop_type in ["Grille", "Ligne"])
        self.step_input.setVisible(loop_type in ["Grille", "Ligne"])
        
        self.spiral_label.setVisible(loop_type == "Spirale")
        self.spiral_input.setVisible(loop_type == "Spirale")
        
        self.offset_x_label.setVisible(loop_type == "Grille")
        self.offset_x_input.setVisible(loop_type == "Grille")
        
        self.offset_y_label.setVisible(loop_type == "Grille")
        self.offset_y_input.setVisible(loop_type == "Grille")
        
        self.classic_widget.setVisible(loop_type != "For")
        self.for_widget.setVisible(loop_type == "For")
        
        suggestions = {
            "Cercle": "Avatars disposés en cercle avec un rayon défini.",
            "Grille": "Avatars disposés en grille régulière avec un pas.",
            "Ligne": "Avatars disposés en ligne avec un espacement.",
            "Spirale": "Avatars en spirale avec rayon croissant.",
            "Manuel": "Configuration manuelle des positions.",
            "For": "Boucle For programmable pour génération avancée."
        }
        self.help_label.setText(suggestions.get(loop_type, ""))

    def _on_target_type_changed(self, target_type: str):
        """Appelé quand le type cible change (boucle For)"""
        templates = {
            "avatar": '{"avatar_type": "rigidDisk", "center": "[i*0.5, 0]", "material_name": "TDURx", "model_name": "rigid", "radius": "0.1+i*0.01"}',
            "material": '{"name": "\'MAT\'+str(i)", "material_type": "RIGID", "density": "2800+i*100"}',
            "model": '{"name": "\'MOD\'+str(i)", "physics": "MECAx", "element": "Rxx2D", "dimension": 2}',
        }
        if target_type in templates:
            self.template_input.setPlainText(templates[target_type])

    def _on_create(self):
        """Crée une nouvelle boucle"""
        try:
            loop_type = self.type_combo.currentText()
            
            if loop_type == "For":
                template_text = self.template_input.toPlainText().strip()
                if not template_text:
                    raise ValidationError("Le template JSON est requis pour les boucles For")
                
                template_config = json.loads(template_text)
                
                for_loop = ForLoop(
                    loop_var=self.loop_var_input.text().strip(),
                    start_expr=self.start_input.text().strip(),
                    end_expr=self.end_input.text().strip(),
                    step_expr=self.step_for_input.text().strip(),
                    target_type=self.target_type_combo.currentText(),
                    template_config=template_config,
                    group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
                )
                
                indices = self.controller.generate_for_loop(for_loop)
                self.loop_generated.emit()
                QMessageBox.information(
                    self, "Succès",
                    f"{len(indices)} éléments générés avec succès.\nGroupe : {for_loop.group_name or 'Aucun'}"
                )
            
            else:
                model_idx = self.avatar_combo.currentData()
                if model_idx is None:
                    raise ValidationError("Sélectionnez un avatar modèle")
                
                count = self.eval_int(self.count_input.text(), default=10, field_name="Nombre")
                radius = self.eval_float(self.radius_input.text(), default=2.0, field_name="Rayon")
                step = self.eval_float(self.step_input.text(), default=1.0, field_name="Pas")
                spiral_factor = self.eval_float(self.spiral_input.text(), default=0.1, field_name="Facteur spirale")
                offset_x = self.eval_float(self.offset_x_input.text(), default=0.0, field_name="Offset X")
                offset_y = self.eval_float(self.offset_y_input.text(), default=0.0, field_name="Offset Y")
                
                loop = Loop(
                    loop_type=loop_type,
                    model_avatar_index=model_idx,
                    count=count,
                    radius=radius,
                    step=step,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    spiral_factor=spiral_factor,
                    invert_axis=self.invert_check.isChecked(),
                    group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
                )
                
                indices = self.controller.generate_loop(loop)
                self.loop_generated.emit()
                QMessageBox.information(
                    self, "Succès",
                    f"{len(indices)} avatars générés avec succès.\nGroupe : {loop.group_name or 'Aucun'}"
                )
            
            self.refresh()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Erreur JSON", f"Template JSON invalide:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée:\n{e}")

    def _on_edit_from_tree(self):
        """Charge une boucle depuis l'arbre pour édition"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une boucle à modifier")
            return
        
        index = selected.data(0, Qt.ItemDataRole.UserRole)
        if index is None:
            return
        
        total_loops = len(self.controller.state.loops)
        
        if index < total_loops:
            loop = self.controller.state.loops[index]
            self.load_for_edit(index, loop)
        else:
            for_index = index - total_loops
            if for_index < len(self.controller.state.for_loops):
                for_loop = self.controller.state.for_loops[for_index]
                self.load_for_edit(index, for_loop=for_loop)

    def _on_update(self):
        """Met à jour une boucle existante"""
        if self.current_edit_index is None:
            return
        
        try:
            total_loops = len(self.controller.state.loops)
            loop_type = self.type_combo.currentText()
            
            if self.current_edit_index < total_loops:
                # Mise à jour boucle classique
                model_idx = self.avatar_combo.currentData()
                if model_idx is None:
                    raise ValidationError("Sélectionnez un avatar modèle")
                
                count = self.eval_int(self.count_input.text(), default=10, field_name="Nombre")
                radius = self.eval_float(self.radius_input.text(), default=2.0, field_name="Rayon")
                step = self.eval_float(self.step_input.text(), default=1.0, field_name="Pas")
                spiral_factor = self.eval_float(self.spiral_input.text(), default=0.1, field_name="Facteur spirale")
                offset_x = self.eval_float(self.offset_x_input.text(), default=0.0, field_name="Offset X")
                offset_y = self.eval_float(self.offset_y_input.text(), default=0.0, field_name="Offset Y")
                
                loop = Loop(
                    loop_type=loop_type,
                    model_avatar_index=model_idx,
                    count=count,
                    radius=radius,
                    step=step,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    spiral_factor=spiral_factor,
                    invert_axis=self.invert_check.isChecked(),
                    group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
                )
                
                self.controller.update_loop(self.current_edit_index, loop)
                self.loop_updated.emit()
                QMessageBox.information(self, "Succès", "✅ Boucle modifiée")
                
            else:
                # Mise à jour boucle For
                for_index = self.current_edit_index - total_loops
                template_text = self.template_input.toPlainText().strip()
                if not template_text:
                    raise ValidationError("Le template JSON est requis")
                
                template_config = json.loads(template_text)
                
                for_loop = ForLoop(
                    loop_var=self.loop_var_input.text().strip(),
                    start_expr=self.start_input.text().strip(),
                    end_expr=self.end_input.text().strip(),
                    step_expr=self.step_for_input.text().strip(),
                    target_type=self.target_type_combo.currentText(),
                    template_config=template_config,
                    group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
                )
                
                self.controller.update_for_loop(for_index, for_loop)
                self.loop_updated.emit()
                QMessageBox.information(self, "Succès", "✅ Boucle For modifiée")
            
            self.refresh()
            self._on_cancel_edit()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Erreur JSON", f"Template JSON invalide:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Modification échouée:\n{e}")

    def load_for_edit(self, index: int, loop=None, for_loop=None):
        """Charge une boucle pour édition"""
        self.current_edit_index = index
        total_loops = len(self.controller.state.loops)
        
        if index < total_loops and loop is not None:
            # Boucle classique
            self.type_combo.setCurrentText(loop.loop_type)
            self.count_input.setText(str(loop.count))
            
            # Trouver l'avatar modèle
            for i in range(self.avatar_combo.count()):
                if self.avatar_combo.itemData(i) == loop.model_avatar_index:
                    self.avatar_combo.setCurrentIndex(i)
                    break
            
            self.radius_input.setText(str(loop.radius))
            self.step_input.setText(str(loop.step))
            self.offset_x_input.setText(str(loop.offset_x))
            self.offset_y_input.setText(str(loop.offset_y))
            self.spiral_input.setText(str(loop.spiral_factor))
            self.invert_check.setChecked(loop.invert_axis)
            
            if loop.group_name:
                self.store_check.setChecked(True)
                self.group_name_input.setText(loop.group_name)
        
        elif for_loop is not None:
            # Boucle For
            self.type_combo.setCurrentText("For")
            self.loop_var_input.setText(for_loop.loop_var)
            self.start_input.setText(for_loop.start_expr)
            self.end_input.setText(for_loop.end_expr)
            self.step_for_input.setText(for_loop.step_expr)
            self.target_type_combo.setCurrentText(for_loop.target_type)
            
            self.template_input.setPlainText(json.dumps(for_loop.template_config, indent=2))
            
            if for_loop.group_name:
                self.store_check.setChecked(True)
                self.group_name_input.setText(for_loop.group_name)
        
        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.cancel_btn.setVisible(True)
        
        self.help_label.setText(f"🔧 Mode édition : Boucle #{index + 1}")
        self.help_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 5px;")

    def _on_delete_from_tree(self):
        """Supprime une boucle depuis l'arbre"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une boucle à supprimer")
            return
        
        index = selected.data(0, Qt.ItemDataRole.UserRole)
        if index is None:
            return
        
        self._on_delete(index)

    def _on_delete(self, index: int):
        """Supprime une boucle"""
        total_loops = len(self.controller.state.loops)
        
        if index < total_loops:
            loop = self.controller.state.loops[index]
            reply = QMessageBox.question(
                self,
                "Confirmer la suppression",
                f"Supprimer la boucle #{index+1} ({loop.loop_type}, {loop.count} avatars) ?\n"
                "Tous les avatars générés par cette boucle seront supprimés.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.controller.remove_loop(index)
                self.loop_deleted.emit()
                QMessageBox.information(self, "Succès", "✅ Boucle supprimée")
                
                if self.current_edit_index == index:
                    self._on_cancel_edit()
                
                self.refresh()
        else:
            for_index = index - total_loops
            if for_index < len(self.controller.state.for_loops):
                for_loop = self.controller.state.for_loops[for_index]
                reply = QMessageBox.question(
                    self,
                    "Confirmer la suppression",
                    f"Supprimer la boucle For #{for_index+1} ?\n"
                    "Tous les éléments générés seront supprimés.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self.controller.remove_for_loop(for_index)
                    self.loop_deleted.emit()
                    QMessageBox.information(self, "Succès", "✅ Boucle For supprimée")
                    
                    if self.current_edit_index == index:
                        self._on_cancel_edit()
                    
                    self.refresh()

    def _on_regenerate_from_tree(self):
        """Régénère une boucle depuis l'arbre"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une boucle à régénérer")
            return
        
        index = selected.data(0, Qt.ItemDataRole.UserRole)
        if index is None:
            return
        
        self._on_regenerate(index)

    def _on_regenerate(self, index: int):
        """Régénère une boucle"""
        total_loops = len(self.controller.state.loops)
        
        if index < total_loops:
            loop = self.controller.state.loops[index]
            try:
                indices = self.controller.generate_loop(loop)
                QMessageBox.information(self, "Succès", f"♻️ {len(indices)} avatars régénérés")
                self.loop_generated.emit()
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Échec de la régénération :\n{e}")
        else:
            for_index = index - total_loops
            if for_index < len(self.controller.state.for_loops):
                for_loop = self.controller.state.for_loops[for_index]
                try:
                    indices = self.controller.generate_for_loop(for_loop)
                    QMessageBox.information(self, "Succès", f"♻️ {len(indices)} éléments régénérés")
                    self.loop_generated.emit()
                    self.refresh()
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Échec de la régénération :\n{e}")

    def _show_info(self):
        """Affiche les informations d'une boucle"""
        selected = self.tree.currentItem()
        if not selected:
            return
        
        index = selected.data(0, Qt.ItemDataRole.UserRole)
        if index is None:
            return
        
        total_loops = len(self.controller.state.loops)
        
        if index < total_loops:
            loop = self.controller.state.loops[index]
            avatar_idx = loop.model_avatar_index
            avatar_label = f"#{avatar_idx}" if avatar_idx < len(self.controller.state.avatars) else "Inconnu"
            
            info = f"<h3>Boucle #{index + 1}</h3>"
            info += f"<b>Type :</b> {loop.loop_type}<br>"
            info += f"<b>Nombre d'avatars :</b> {loop.count}<br>"
            info += f"<b>Avatar modèle :</b> {avatar_label}<br>"
            info += f"<b>Rayon :</b> {loop.radius}<br>"
            info += f"<b>Pas :</b> {loop.step}<br>"
            info += f"<b>Offset X :</b> {loop.offset_x}<br>"
            info += f"<b>Offset Y :</b> {loop.offset_y}<br>"
            info += f"<b>Facteur spirale :</b> {loop.spiral_factor}<br>"
            info += f"<b>Axe inversé :</b> {'Oui' if loop.invert_axis else 'Non'}<br>"
            info += f"<b>Groupe :</b> {loop.group_name or 'Aucun'}<br>"
        else:
            for_index = index - total_loops
            if for_index < len(self.controller.state.for_loops):
                for_loop = self.controller.state.for_loops[for_index]
                
                info = f"<h3>Boucle For #{for_index + 1}</h3>"
                info += f"<b>Variable :</b> {for_loop.loop_var}<br>"
                info += f"<b>Début :</b> {for_loop.start_expr}<br>"
                info += f"<b>Fin :</b> {for_loop.end_expr}<br>"
                info += f"<b>Step :</b> {for_loop.step_expr}<br>"
                info += f"<b>Type cible :</b> {for_loop.target_type}<br>"
                info += f"<b>Éléments générés :</b> {len(for_loop.generated_indices)}<br>"
                info += f"<b>Groupe :</b> {for_loop.group_name or 'Aucun'}<br>"
                info += f"<br><b>Template :</b><br><pre>{json.dumps(for_loop.template_config, indent=2)}</pre>"
        
        QMessageBox.information(self, f"Infos : Boucle #{index + 1}", info)

    def _on_cancel_edit(self):
        """Annule l'édition"""
        self.current_edit_index = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        #self._clear_form()
        self.help_label.setText("Sélectionnez un type de boucle pour voir les paramètres adaptés.")
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")

    def _clear_form(self):
        """Réinitialise le formulaire"""
        self.type_combo.setCurrentIndex(0)
        self.count_input.setText("10")
        self.radius_input.setText("2.0")
        self.step_input.setText("1.0")
        self.offset_x_input.setText("0.0")
        self.offset_y_input.setText("0.0")
        self.spiral_input.setText("0.1")
        self.invert_check.setChecked(False)
        self.store_check.setChecked(False)
        self.group_name_input.setText("boucle_groupe")
        
        self.loop_var_input.setText("i")
        self.start_input.setText("0")
        self.end_input.setText("10")
        self.step_for_input.setText("1")
        self.template_input.clear()

    def refresh(self):
        """Rafraîchit l'affichage"""
        self.avatar_combo.clear()
        for i, avatar in enumerate(self.controller.state.avatars):
            if avatar.origin == AvatarOrigin.MANUAL:
                label = f"#{i} — {avatar.avatar_type.value} ({avatar.color})"
                self.avatar_combo.addItem(label, i)
        if self.avatar_combo.count() == 0:
            self.avatar_combo.addItem("(Aucun avatar manuel disponible)", None)

        self.tree.clear()
        
        for idx, loop in enumerate(self.controller.state.loops):
            avatar_idx = loop.model_avatar_index
            avatar_label = f"#{avatar_idx}" if avatar_idx < len(self.controller.state.avatars) else "Inconnu"
            group_str = loop.group_name or "—"

            item = QTreeWidgetItem([
                str(idx + 1),
                loop.loop_type,
                str(loop.count),
                avatar_label,
                group_str
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, idx)
            self.tree.addTopLevelItem(item)
        
        for idx, for_loop in enumerate(self.controller.state.for_loops):
            global_idx = len(self.controller.state.loops) + idx
            item = QTreeWidgetItem([
                str(global_idx + 1),
                f"For ({for_loop.target_type})",
                str(len(for_loop.generated_indices)),
                f"{for_loop.loop_var}: {for_loop.start_expr}→{for_loop.end_expr}",
                for_loop.group_name or "—"
            ])
            item.setForeground(1, QBrush(QColor(0, 100, 200)))
            item.setData(0, Qt.ItemDataRole.UserRole, global_idx)
            self.tree.addTopLevelItem(item)