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
        self.edit_btn = QPushButton("✏️ Modifier sélection")
        self.delete_btn = QPushButton("🗑️ Supprimer sélection")

        actions_layout.addWidget(self.regen_btn)
        actions_layout.addWidget(self.edit_btn)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        form_label = QLabel("<b>📝 Paramètres de la Boucle</b>")
        layout.addWidget(form_label)

        form = QFormLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Cercle", "Grille", "Ligne", "Spirale", "Manuel", "For"])
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
        self.update_btn = QPushButton("✏️ Modifier boucle")
        self.update_btn.setVisible(False)
        self.reset_btn = QPushButton("🔄 Réinitialiser")

        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.add_expression_help_label(layout)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

        self._on_type_changed(self.type_combo.currentText())

    def _connect_signals(self):
        self.create_btn.clicked.connect(self._on_create)
        self.update_btn.clicked.connect(self._on_edit)
        self.reset_btn.clicked.connect(self._clear_form)
        self.regen_btn.clicked.connect(self._on_regenerate_selected)
        self.edit_btn.clicked.connect(self._on_edit_selected)
        self.delete_btn.clicked.connect(self._on_delete_selected)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)

    def _on_type_changed(self, loop_type: str):
        is_for = loop_type == "For"
        self.classic_widget.setVisible(not is_for)
        self.for_widget.setVisible(is_for)
        
        if not is_for:
            show_radius = loop_type in ["Cercle", "Spirale"]
            show_step = loop_type in ["Grille", "Ligne"]
            show_invert = loop_type == "Ligne"
            show_spiral = loop_type == "Spirale"

            self.radius_label.setVisible(show_radius)
            self.radius_input.setVisible(show_radius)
            self.step_label.setVisible(show_step)
            self.step_input.setVisible(show_step)
            self.invert_check.setVisible(show_invert)
            self.spiral_label.setVisible(show_spiral)
            self.spiral_input.setVisible(show_spiral)

            help_texts = {
                "Cercle": "Disposition circulaire autour du centre de l'avatar modèle.",
                "Grille": "Disposition en grille carrée.",
                "Ligne": "Disposition linéaire horizontale ou verticale (selon inversion).",
                "Spirale": "Spirale arquimédienne à partir du centre.",
                "Manuel": "Positions définies manuellement (non implémenté dans cette version)."
            }
            self.help_label.setText(help_texts.get(loop_type, ""))
        else:
            self.help_label.setText("Boucle For générique - Utilisez des expressions avec la variable de boucle")

    def _on_target_type_changed(self, target_type: str):
        templates = {
            "avatar": {
                "avatar_type": "rigidDisk",
                "center": "[i*0.5, 0]",
                "material_name": "TDURx",
                "model_name": "rigid",
                "color": "BLUEx",
                "radius": "0.1"
            },
            "material": {
                "name": "'MAT'+str(i)",
                "material_type": "RIGID",
                "density": "2800"
            },
            "model": {
                "name": "'MOD'+str(i)",
                "physics": "MECAx",
                "element": "Rxx2D",
                "dimension": 2
            },
            "contact_law": {
                "name": "'LAW'+str(i)",
                "law_type": "IQS_CLB",
                "friction": "0.3"
            },
            "visibility": {
                "candidate_body": "RBDY2",
                "candidate_contactor": "DISKx",
                "candidate_color": "BLUEx",
                "antagonist_body": "RBDY2",
                "antagonist_contactor": "DISKx",
                "antagonist_color": "VERTx",
                "behavior_name": "iqsc0",
                "alert": "0.1"
            },
            "dof": {
                "operation_type": "translate",
                "target_type": "avatar",
                "target_value": "i",
                "parameters": {"dx": "i*0.1", "dy": "0"}
            }
        }
        
        if target_type in templates:
            self.template_input.setPlainText(json.dumps(templates[target_type], indent=2))

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return

        menu = QMenu()
        menu.addAction("✏️ Modifier", lambda: self.load_for_edit(self.tree.indexOfTopLevelItem(item)))
        menu.addAction("♻️ Régénérer", lambda: self._on_regenerate(self.tree.indexOfTopLevelItem(item)))
        menu.addSeparator()
        menu.addAction("🗑️ Supprimer", lambda: self._on_delete(self.tree.indexOfTopLevelItem(item)))

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        index = self.tree.indexOfTopLevelItem(item)
        self.load_for_edit(index)

    def _on_edit_selected(self):
        if self.current_edit_index is not None:
            self.load_for_edit(self.current_edit_index)
        else:
            QMessageBox.information(self, "Sélection", "Veuillez d'abord sélectionner une boucle dans la liste.")

    def _on_delete_selected(self):
        if self.current_edit_index is not None:
            self._on_delete(self.current_edit_index)
        else:
            QMessageBox.information(self, "Sélection", "Veuillez d'abord sélectionner une boucle à supprimer.")

    def _on_regenerate_selected(self):
        if self.current_edit_index is not None:
            self._on_regenerate(self.current_edit_index)
        else:
            QMessageBox.information(self, "Sélection", "Veuillez d'abord sélectionner une boucle à régénérer.")

    def _on_create(self):
        try:
            loop_type = self.type_combo.currentText()
            
            if loop_type == "For":
                for_loop = ForLoop(
                    loop_var=self.loop_var_input.text().strip(),
                    start_expr=self.start_input.text().strip(),
                    end_expr=self.end_input.text().strip(),
                    step_expr=self.step_for_input.text().strip(),
                    target_type=self.target_type_combo.currentText(),
                    template_config=json.loads(self.template_input.toPlainText()),
                    group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
                )
                
                indices = self.controller.generate_for_loop(for_loop)
                self.loop_generated.emit()
                QMessageBox.information(
                    self, "Succès",
                    f"{len(indices)} éléments générés.\nGroupe : {for_loop.group_name or 'Aucun'}"
                )
            else:
                count = self.eval_int(self.count_input.text(), default=10, field_name="Nombre d'avatars")
                if count <= 0:
                    raise ValidationError("Le nombre d'avatars doit être > 0")
                if count > 10000:
                    raise ValidationError("Maximum 10000 avatars par boucle")
                
                model_idx = self.avatar_combo.currentData()
                if model_idx is None:
                    raise ValidationError("Sélectionnez un avatar modèle")
                
                radius = 0.0
                if self.radius_input.isVisible():
                    radius = self.eval_float(self.radius_input.text(), default=2.0, field_name="Rayon")
                    if radius <= 0:
                        raise ValidationError("Le rayon doit être > 0")
                
                step = 0.0
                if self.step_input.isVisible():
                    step = self.eval_float(self.step_input.text(), default=1.0, field_name="Pas")
                    if step <= 0:
                        raise ValidationError("Le pas doit être > 0")
                
                spiral_factor = 0.0
                if self.spiral_input.isVisible():
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

    def _on_edit(self):
        QMessageBox.information(self, "Info", "Modification non implémentée pour les boucles For")

    def load_for_edit(self, index: int, loop=None):
        """Charge une boucle pour visualisation"""
        total_loops = len(self.controller.state.loops)
        
        if index < total_loops:
            # Boucle classique
            if loop is None:
                loop = self.controller.state.loops[index]
            
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
        
        else:
            # Boucle For
            for_index = index - total_loops
            if for_index < len(self.controller.state.for_loops):
                for_loop = self.controller.state.for_loops[for_index]
                
                self.type_combo.setCurrentText("For")
                self.loop_var_input.setText(for_loop.loop_var)
                self.start_input.setText(for_loop.start_expr)
                self.end_input.setText(for_loop.end_expr)
                self.step_for_input.setText(for_loop.step_expr)
                self.target_type_combo.setCurrentText(for_loop.target_type)
                
                import json
                self.template_input.setPlainText(json.dumps(for_loop.template_config, indent=2))
                
                if for_loop.group_name:
                    self.store_check.setChecked(True)
                    self.group_name_input.setText(for_loop.group_name)

    def _on_delete(self, index: int):
        if index < len(self.controller.state.loops):
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
                self._clear_form()
                self.refresh()
        else:
            for_index = index - len(self.controller.state.loops)
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
                    self._clear_form()
                    self.refresh()

    def _on_regenerate(self, index: int):
        if index < len(self.controller.state.loops):
            loop = self.controller.state.loops[index]
            try:
                indices = self.controller.generate_loop(loop)
                QMessageBox.information(self, "Succès", f"{len(indices)} avatars régénérés.")
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Échec de la régénération :\n{e}")

    def load_for_edit(self, index: int):
        QMessageBox.information(self, "Info", "Édition non implémentée - recréez la boucle")

    def _clear_form(self):
        self.type_combo.setCurrentIndex(0)
        self.count_input.setText("10")
        self.radius_input.setText("2.0")
        self.step_input.setText("1.0")
        self.offset_x_input.setText("0.0")
        self.offset_y_input.setText("0.0")
        self.spiral_input.setText("0.1")
        self.invert_check.setChecked(False)
        self.store_check.setChecked(False)
        self.group_name_input.clear()
        
        self.loop_var_input.setText("i")
        self.start_input.setText("0")
        self.end_input.setText("10")
        self.step_for_input.setText("1")
        self.template_input.clear()

        self.current_edit_index = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)

    def refresh(self):
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
            self.tree.addTopLevelItem(item)
        
        if hasattr(self.controller.state, 'for_loops'):
            for idx, for_loop in enumerate(self.controller.state.for_loops):
                item = QTreeWidgetItem([
                    str(len(self.controller.state.loops) + idx + 1),
                    f"For ({for_loop.target_type})",
                    str(len(for_loop.generated_indices)),
                    f"{for_loop.loop_var}: {for_loop.start_expr}→{for_loop.end_expr}",
                    for_loop.group_name or "—"
                ])
                item.setForeground(1, QBrush(QColor(0, 100, 200)))
                self.tree.addTopLevelItem(item)

        self._clear_form()