# ============================================================================
# DOFTab
# ============================================================================
"""
Onglet de gestion des conditions aux limites DOF avec création, modification et suppression.
Style identique aux autres onglets (MaterialTab, LoopTab, AvatarTab...).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import DOFOperation, AvatarOrigin
from ...controllers.project_controller import ProjectController


class DOFTab(QWidget):
    """Onglet opérations DOF"""
    
    operation_applied = pyqtSignal()
    operation_updated = pyqtSignal()
    operation_deleted = pyqtSignal()

    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.current_edit_index = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # === SECTION 1: ARBRE DES OPÉRATIONS DOF ===
        tree_label = QLabel("<b>📋 Liste des Opérations DOF</b>")
        layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["#", "Cible", "Action", "Paramètres"])
        self.tree.setColumnWidth(0, 50)
        self.tree.setColumnWidth(1, 200)
        self.tree.setColumnWidth(2, 120)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(180)
        layout.addWidget(self.tree)

        # Boutons sous l'arbre : Modifier et Supprimer sélection
        actions_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("✏️ Modifier sélection")
        self.edit_btn.setToolTip("Charge l'opération sélectionnée pour modification")
        
        self.delete_btn = QPushButton("🗑️ Supprimer sélection")
        self.delete_btn.setToolTip("Supprime l'opération sélectionnée")

        actions_layout.addWidget(self.edit_btn)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # === SECTION 2: FORMULAIRE ===
        form_label = QLabel("<b>📝 Paramètres de l'Opération DOF</b>")
        layout.addWidget(form_label)

        form = QFormLayout()

        # Cible (avatar ou groupe)
        self.target_combo = QComboBox()
        form.addRow("Cible :", self.target_combo)

        # Action
        self.action_combo = QComboBox()
        self.action_combo.addItems([
            "translate", "rotate", "imposeDrivenDof", "imposeInitValue",
            "blockDof", "driveDof"
        ])
        self.action_combo.currentTextChanged.connect(self._on_action_changed)
        form.addRow("Action :", self.action_combo)

        # Paramètres
        self.params_input = QLineEdit("dx=0.0, dy=0.0, ramp=1.0")
        self.params_input.setPlaceholderText("Ex: dx=1.0, dy=-0.5, dofty='vlocy'")
        form.addRow("Paramètres :", self.params_input)

        layout.addLayout(form)

        # Aide contextuelle
        self.help_label = QLabel("Sélectionnez une action pour voir des exemples de paramètres.")
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.help_label)

        # === BOUTONS PRINCIPAUX EN BAS ===
        btn_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("✅ Appliquer DOF")
        self.update_btn = QPushButton("✏️ Modifier DOF")
        self.update_btn.setVisible(False)
        
        self.reset_btn = QPushButton("🔄 Réinitialiser")

        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        self.setLayout(layout)

        self._on_action_changed(self.action_combo.currentText())

    def _connect_signals(self):
        self.apply_btn.clicked.connect(self._on_apply)
        self.update_btn.clicked.connect(self._on_edit)
        self.reset_btn.clicked.connect(self._clear_form)
        self.edit_btn.clicked.connect(self._on_edit_selected)
        self.delete_btn.clicked.connect(self._on_delete_selected)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)

    def _on_action_changed(self, action: str):
        help_texts = {
            "translate": "Ex: dx=1.0, dy=-0.5 → déplacement imposé",
            "rotate": "Ex: rz=90.0, centerx=0.0, centery=0.0 → rotation en degrés",
            "imposeDrivenDof": "Ex: dofx='vlocx', ramp=1.0, value=2.0",
            "imposeInitValue": "Ex: dofy='vlocy', value=0.0",
            "blockDof": "Ex: dofx=True, dofy=True → bloque les degrés",
            "driveDof": "Ex: dofrz='vrotz', ramp=1.0"
        }
        self.help_label.setText(help_texts.get(action, "Paramètres sous forme clé=valeur séparés par virgules."))

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return

        menu = QMenu()
        menu.addAction("✏️ Modifier", lambda: self.load_for_edit(self.tree.indexOfTopLevelItem(item)))
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
            QMessageBox.information(self, "Sélection", "Veuillez d'abord sélectionner une opération DOF.")

    def _on_delete_selected(self):
        if self.current_edit_index is not None:
            self._on_delete(self.current_edit_index)
        else:
            QMessageBox.information(self, "Sélection", "Veuillez d'abord sélectionner une opération à supprimer.")

    def _parse_params(self, text: str) -> dict:
        """Parse les paramètres saisis par l'utilisateur"""
        if not text.strip():
            return {}
        params = {}
        for pair in text.split(','):
            pair = pair.strip()
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip()
                value_str = value.strip()
                if value_str in ['True', 'False']:
                    params[key] = value_str == 'True'
                elif '.' in value_str or 'e' in value_str.lower():
                    params[key] = float(value_str)
                else:
                    try:
                        params[key] = int(value_str)
                    except ValueError:
                        params[key] = value_str  # garde comme string (ex: 'vlocy')
        return params

    def _on_apply(self):
        try:
            target_type, target_value = self.target_combo.currentData()
            if target_value is None:
                raise ValueError("Aucune cible valide sélectionnée")

            operation = DOFOperation(
                target_type=target_type,
                target_value=target_value,
                operation_type=self.action_combo.currentText(),
                parameters=self._parse_params(self.params_input.text())
            )

            self.controller.apply_dof_operation(operation)
            self.operation_applied.emit()
            QMessageBox.information(self, "Succès", "Opération DOF appliquée avec succès.")
            self._clear_form()
            self.refresh()

        except ValueError as e:
            QMessageBox.critical(self, "Erreur de saisie", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de l'application :\n{e}")

    def _on_edit(self):
        if self.current_edit_index is None:
            return

        try:
            target_type, target_value = self.target_combo.currentData()
            updated_operation = DOFOperation(
                target_type=target_type,
                target_value=target_value,
                operation_type=self.action_combo.currentText(),
                parameters=self._parse_params(self.params_input.text())
            )

            self.controller.update_dof_operation(self.current_edit_index, updated_operation)
            self.operation_updated.emit()
            QMessageBox.information(self, "Succès", "Opération DOF modifiée avec succès.")
            self._clear_form()
            self.refresh()

        except ValueError as e:
            QMessageBox.critical(self, "Erreur de saisie", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la modification :\n{e}")

    def _on_delete(self, index: int):
        operation = self.controller.state.operations[index]
        target_label = operation.target_value if isinstance(operation.target_value, str) else f"Avatar #{operation.target_value}"

        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Supprimer l'opération DOF #{index+1} sur {target_label} ({operation.operation_type}) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.controller.remove_dof_operation(index)
            self.operation_deleted.emit()
            self._clear_form()
            self.refresh()

    def load_for_edit(self, index: int, option = None):
        operation = self.controller.state.operations[index]
        self.current_edit_index = index

        # Sélectionner la cible
        for i in range(self.target_combo.count()):
            if self.target_combo.itemData(i) == (operation.target_type, operation.target_value):
                self.target_combo.setCurrentIndex(i)
                break

        self.action_combo.setCurrentText(operation.operation_type)

        # Reconstruire les paramètres
        if operation.parameters:
            params_str = ", ".join(f"{k}={v}" for k, v in operation.parameters.items())
            self.params_input.setText(params_str)
        else:
            self.params_input.clear()

        # Mode édition
        self.apply_btn.setVisible(False)
        self.update_btn.setVisible(True)

        self.help_label.setText(f"🔧 Mode édition — Opération DOF #{index+1}")
        self.help_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 5px;")

    def _clear_form(self):
        self.target_combo.setCurrentIndex(0)
        self.action_combo.setCurrentIndex(0)
        self.params_input.clear()
        self.current_edit_index = None
        self.apply_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.help_label.setText("Sélectionnez une action pour voir des exemples de paramètres.")
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")

    def refresh(self):
        """Rafraîchit le combo des cibles et l'arbre des opérations"""
        current_target = self.target_combo.currentData() if self.target_combo.count() > 0 else None

        self.target_combo.clear()

        # Avatars individuels
        for i, avatar in enumerate(self.controller.state.avatars):
            origin_mark = ""
            if avatar.origin == AvatarOrigin.LOOP:
                origin_mark = " [Boucle]"
            elif avatar.origin == AvatarOrigin.GRANULO:
                origin_mark = " [Granulo]"
            label = f"Avatar #{i} — {avatar.avatar_type.value} ({avatar.color}){origin_mark}"
            self.target_combo.addItem(label, ('avatar', i))

        # Groupes
        for group_name, indices in self.controller.state.avatar_groups.items():
            label = f"🔷 GROUPE : {group_name} ({len(indices)} avatars)"
            self.target_combo.addItem(label, ('group', group_name))

        if self.target_combo.count() == 0:
            self.target_combo.addItem("(Aucun avatar disponible)", None)

        # Restaurer la cible si possible
        if current_target and current_target in [self.target_combo.itemData(i) for i in range(self.target_combo.count())]:
            idx = [self.target_combo.itemData(i) for i in range(self.target_combo.count())].index(current_target)
            self.target_combo.setCurrentIndex(idx)

        # Rafraîchir l'arbre
        self.tree.clear()
        for idx, op in enumerate(self.controller.state.operations):
            target_label = op.target_value if isinstance(op.target_value, str) else f"Avatar #{op.target_value}"
            params_str = ", ".join(f"{k}={v}" for k, v in list(op.parameters.items())[:3])
            if len(op.parameters) > 3:
                params_str += "..."

            item = QTreeWidgetItem([
                str(idx + 1),
                target_label,
                op.operation_type,
                params_str or "—"
            ])
            self.tree.addTopLevelItem(item)

        self._clear_form()