from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import DOFOperation, AvatarOrigin
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController
from ...views.tabs.base_tab import BaseTab
from typing import Dict, Any


class DOFTab(BaseTab):
    """Onglet opérations DOF"""
    
    operation_applied = pyqtSignal()
    operation_updated = pyqtSignal()
    operation_deleted = pyqtSignal()

    def __init__(self, controller: ProjectController):
        super().__init__(controller)
        self.controller = controller
        self.current_edit_index = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout()

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

        actions_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("✏️ Modifier sélection")
        self.edit_btn.setToolTip("Charge l'opération sélectionnée pour modification")
        
        self.delete_btn = QPushButton("🗑️ Supprimer sélection")
        self.delete_btn.setToolTip("Supprime l'opération sélectionnée")

        actions_layout.addWidget(self.edit_btn)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        form_label = QLabel("<b>📝 Paramètres de l'Opération DOF</b>")
        layout.addWidget(form_label)

        form = QFormLayout()

        self.target_combo = QComboBox()
        form.addRow("Cible :", self.target_combo)

        self.action_combo = QComboBox()
        self.action_combo.addItems([
            "translate", "rotate", "imposeDrivenDof", "imposeInitValue"
        ])
        self.action_combo.currentTextChanged.connect(self._on_action_changed)
        form.addRow("Action :", self.action_combo)

        self.params_input = QLineEdit("dx=0.0, dy=0.0, ramp=1.0")
        self.params_input.setPlaceholderText("Ex: dx=1.0, dy=-0.5, dofty='vlocy'")
        form.addRow("Paramètres :", self.params_input)

        layout.addLayout(form)

        self.help_label = QLabel("Sélectionnez une action pour voir des exemples de paramètres.")
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.help_label)

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

        self.add_expression_help_label(layout)
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
            "translate": "dx=0.0, dy=2.0",
            "rotate": "psi=math.pi/2.0, center=[0.0, 0.0]",
            "imposeDrivenDof": "component=[1,2,3], dofty='vlocy'",
            "imposeInitValue": "component=1, value=3.0"
        }

        self.params_input.setText(help_texts[action])
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

    def _parse_params(self, text: str) -> Dict[str, Any]:
        """Parse avec évaluateur - VERSION CORRIGÉE"""
        try:
            return self.eval_dict(text, field_name="Paramètres DOF")
        except Exception as e:
            raise ValidationError(f"Paramètres invalides: {e}")

    def _on_apply(self):
        try:
            target_type, target_value = self.target_combo.currentData()
            if target_value is None:
                raise ValueError("Aucune cible valide sélectionnée")
            
            params_str = self.params_input.text().strip()
            params = {}
            if not params_str:
                raise ValidationError("Aucun paramètre valide détecté")
            else:
                params = self._parse_params(params_str)
            
            operation = DOFOperation(
                target_type=target_type,
                target_value=target_value,
                operation_type=self.action_combo.currentText(),
                parameters=params
            )
            self.controller.add_dof_operation(operation)
            self.operation_applied.emit()
            QMessageBox.information(self, "Succès", "Opération DOF appliquée avec succès.")
            self.refresh()

        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
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
            #self._clear_form()
            self.refresh()

        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
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
            #self._clear_form()
            self.refresh()

    def load_for_edit(self, index: int, option=None):
        operation = self.controller.state.operations[index]
        self.current_edit_index = index

        for i in range(self.target_combo.count()):
            if self.target_combo.itemData(i) == (operation.target_type, operation.target_value):
                self.target_combo.setCurrentIndex(i)
                break

        self.action_combo.setCurrentText(operation.operation_type)

        if operation.parameters:
            params_str = ", ".join(f"{k}={v}" for k, v in operation.parameters.items())
            self.params_input.setText(params_str)
        else:
            self.params_input.clear()

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
        current_target = self.target_combo.currentData() if self.target_combo.count() > 0 else None

        # affichage
        show_individually = getattr(
            getattr(self.controller.state, 'preferences', None),
            'show_granulo_individually', True
        )

        self.target_combo.clear()

        for i, avatar in enumerate(self.controller.state.avatars):
            if avatar.origin == AvatarOrigin.GRANULO and not show_individually:
                continue
            origin_mark = ""
            if avatar.origin == AvatarOrigin.LOOP:
                origin_mark = " [Boucle]"
            elif avatar.origin == AvatarOrigin.GRANULO:
                origin_mark = " [Granulo]"
            label = f"Avatar #{i} — {avatar.avatar_type.value} ({avatar.color}){origin_mark}"
            self.target_combo.addItem(label, ('avatar', i))

        for group_name, indices in self.controller.state.avatar_groups.items():
            label = f"📷 GROUPE : {group_name} ({len(indices)} avatars)"
            self.target_combo.addItem(label, ('group', group_name))

        if self.target_combo.count() == 0:
            self.target_combo.addItem("(Aucun avatar disponible)", None)

        if current_target and current_target in [self.target_combo.itemData(i) for i in range(self.target_combo.count())]:
            idx = [self.target_combo.itemData(i) for i in range(self.target_combo.count())].index(current_target)
            self.target_combo.setCurrentIndex(idx)

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