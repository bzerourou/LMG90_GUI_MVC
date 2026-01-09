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
    QMenu, QLabel, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import Loop, AvatarOrigin
from ...controllers.project_controller import ProjectController


class LoopTab(QWidget):
    """Onglet génération et gestion des boucles"""
    
    loop_generated = pyqtSignal()
    loop_updated = pyqtSignal()
    loop_deleted = pyqtSignal()

    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.current_edit_index = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # === SECTION 1: ARBRE DES BOUCLES ===
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

        # === BOUTONS SOUS L'ARBRE : Régénérer, Modifier, Supprimer ===
        actions_layout = QHBoxLayout()
        
        self.regen_btn = QPushButton("♻️ Régénérer sélection")
        self.regen_btn.setToolTip("Régénère les avatars de la boucle sélectionnée sans modifier les paramètres")
        
        self.edit_btn = QPushButton("✏️ Modifier sélection")
        self.edit_btn.setToolTip("Charge la boucle sélectionnée dans le formulaire pour modification")
        
        self.delete_btn = QPushButton("🗑️ Supprimer sélection")
        self.delete_btn.setToolTip("Supprime la boucle sélectionnée et tous ses avatars générés")

        actions_layout.addWidget(self.regen_btn)
        actions_layout.addWidget(self.edit_btn)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # === SECTION 2: FORMULAIRE ===
        form_label = QLabel("<b>📝 Paramètres de la Boucle</b>")
        layout.addWidget(form_label)

        form = QFormLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Cercle", "Grille", "Ligne", "Spirale", "Manuel"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type de boucle :", self.type_combo)

        self.avatar_combo = QComboBox()
        form.addRow("Avatar à répéter :", self.avatar_combo)

        self.count_input = QLineEdit("10")
        form.addRow("Nombre d'avatars :", self.count_input)

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

        # Stockage dans un groupe
        group_layout = QHBoxLayout()
        self.store_check = QCheckBox("Stocker dans un groupe")
        self.group_name_input = QLineEdit("boucle_groupe")
        self.group_name_input.setPlaceholderText("Nom du groupe")
        group_layout.addWidget(self.store_check)
        group_layout.addWidget(self.group_name_input)
        group_layout.addStretch()
        layout.addLayout(group_layout)

        # Aide contextuelle
        self.help_label = QLabel("Sélectionnez un type de boucle pour voir les paramètres adaptés.")
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.help_label)

        # === BOUTONS PRINCIPAUX EN BAS ===
        btn_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("✅ Créer boucle")
        self.update_btn = QPushButton("✏️ Modifier boucle")
        self.update_btn.setVisible(False)
        
        self.reset_btn = QPushButton("🔄 Réinitialiser")
        self.reset_btn.setVisible(True)  # Toujours visible

        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        self.setLayout(layout)

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
            loop = Loop(
                loop_type=self.type_combo.currentText(),
                model_avatar_index=self.avatar_combo.currentData(),
                count=int(self.count_input.text()),
                radius=float(self.radius_input.text()) if self.radius_input.isVisible() else 0.0,
                step=float(self.step_input.text()) if self.step_input.isVisible() else 0.0,
                offset_x=float(self.offset_x_input.text()),
                offset_y=float(self.offset_y_input.text()),
                spiral_factor=float(self.spiral_input.text()) if self.spiral_input.isVisible() else 0.0,
                invert_axis=self.invert_check.isChecked(),
                group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
            )

            indices = self.controller.generate_loop(loop)
            self.loop_generated.emit()
            QMessageBox.information(
                self, "Succès",
                f"{len(indices)} avatars générés avec succès.\nGroupe : {loop.group_name or 'Aucun'}"
            )
            self._clear_form()
            self.refresh()

        except ValueError as e:
            QMessageBox.critical(self, "Erreur de saisie", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la génération :\n{e}")

    def _on_edit(self):
        if self.current_edit_index is None:
            return

        try:
            updated_loop = Loop(
                loop_type=self.type_combo.currentText(),
                model_avatar_index=self.avatar_combo.currentData(),
                count=int(self.count_input.text()),
                radius=float(self.radius_input.text()) if self.radius_input.isVisible() else 0.0,
                step=float(self.step_input.text()) if self.step_input.isVisible() else 0.0,
                offset_x=float(self.offset_x_input.text()),
                offset_y=float(self.offset_y_input.text()),
                spiral_factor=float(self.spiral_input.text()) if self.spiral_input.isVisible() else 0.0,
                invert_axis=self.invert_check.isChecked(),
                group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
            )

            self.controller.update_loop(self.current_edit_index, updated_loop)
            self.loop_updated.emit()
            QMessageBox.information(self, "Succès", "Boucle modifiée et avatars régénérés.")
            self._clear_form()
            self.refresh()

        except ValueError as e:
            QMessageBox.critical(self, "Erreur de saisie", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la mise à jour :\n{e}")

    def _on_delete(self, index: int):
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

    def _on_regenerate(self, index: int):
        loop = self.controller.state.loops[index]
        try:
            indices = self.controller.generate_loop(loop)
            QMessageBox.information(self, "Succès", f"{len(indices)} avatars régénérés.")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la régénération :\n{e}")

    def load_for_edit(self, index: int):
        loop = self.controller.state.loops[index]
        self.current_edit_index = index

        self.type_combo.setCurrentText(loop.loop_type)
        self.avatar_combo.setCurrentIndex(self.avatar_combo.findData(loop.model_avatar_index))
        self.count_input.setText(str(loop.count))
        self.offset_x_input.setText(str(loop.offset_x))
        self.offset_y_input.setText(str(loop.offset_y))

        if hasattr(loop, 'radius') and self.radius_input.isVisible():
            self.radius_input.setText(str(loop.radius))
        if hasattr(loop, 'step') and self.step_input.isVisible():
            self.step_input.setText(str(loop.step))
        if hasattr(loop, 'spiral_factor') and self.spiral_input.isVisible():
            self.spiral_input.setText(str(loop.spiral_factor))
        if hasattr(loop, 'invert_axis'):
            self.invert_check.setChecked(loop.invert_axis)

        if loop.group_name:
            self.store_check.setChecked(True)
            self.group_name_input.setText(loop.group_name)
        else:
            self.store_check.setChecked(False)

        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.help_label.setText(f"🔧 Mode édition — Boucle #{index+1} ({loop.loop_type})")
        self.help_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 5px;")

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

        self.current_edit_index = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.help_label.setText("Sélectionnez un type de boucle pour voir les paramètres adaptés.")
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")

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

        self._clear_form()