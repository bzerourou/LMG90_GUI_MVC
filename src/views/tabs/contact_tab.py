# ============================================================================
# ContactTab 
# ============================================================================
"""
Onglet de gestion des lois de contact avec création, modification et suppression.
Style identique aux autres onglets (MaterialTab, LoopTab, DOFTab...).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import ContactLaw, ContactLawType
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController
from ...views.tabs.base_tab import BaseTab


class ContactTab(BaseTab):
    """Onglet lois de contact"""
    
    law_created = pyqtSignal()
    law_updated = pyqtSignal()
    law_deleted = pyqtSignal()

    def __init__(self, controller: ProjectController):
        super().__init__(controller)
        self.controller = controller
        self.current_edit_index = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout()

        tree_label = QLabel("<b>📋 Liste des Lois de Contact</b>")
        layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nom", "Type", "Friction (µ)", "Autres propriétés"])
        self.tree.setColumnWidth(0, 150)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 100)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(180)
        layout.addWidget(self.tree)

        actions_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("✏️ Modifier sélection")
        self.edit_btn.setToolTip("Charge la loi sélectionnée dans le formulaire pour modification")
        
        self.delete_btn = QPushButton("🗑️ Supprimer sélection")
        self.delete_btn.setToolTip("Supprime la loi de contact sélectionnée")

        actions_layout.addWidget(self.edit_btn)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        form_label = QLabel("<b>📝 Paramètres de la Loi de Contact</b>")
        layout.addWidget(form_label)

        form = QFormLayout()

        self.name_input = QLineEdit("iqsc0")
        self.name_input.setMaxLength(10)
        form.addRow("Nom :", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems([lt.value for lt in ContactLawType])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type :", self.type_combo)

        self.friction_label = QLabel("Friction (µ) :")
        self.friction_input = QLineEdit("0.3")
        form.addRow(self.friction_label, self.friction_input)

        self.props_input = QLineEdit()
        self.props_input.setPlaceholderText("ex: alert=0.01, pressure=1e5")
        form.addRow("Autres propriétés :", self.props_input)

        layout.addLayout(form)

        self.help_label = QLabel("Sélectionnez un type de loi pour voir les paramètres adaptés.")
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.help_label)

        btn_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("✅ Créer loi")
        self.update_btn = QPushButton("✏️ Modifier loi")
        self.update_btn.setVisible(False)
        
        self.reset_btn = QPushButton("🔄 Réinitialiser")

        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.add_expression_help_label(layout)
        layout.addStretch()
        self.setLayout(layout)

        self._on_type_changed(self.type_combo.currentText())

    def _connect_signals(self):
        self.create_btn.clicked.connect(self._on_create)
        self.update_btn.clicked.connect(self._on_edit)
        self.reset_btn.clicked.connect(self._clear_form)
        self.edit_btn.clicked.connect(self._on_edit_selected)
        self.delete_btn.clicked.connect(self._on_delete_selected)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)

    def _on_type_changed(self, law_type: str):
        needs_friction = law_type in ["IQS_CLB", "IQS_CLB_G0"]
        
        self.friction_label.setVisible(needs_friction)
        self.friction_input.setVisible(needs_friction)
        
        if needs_friction:
            self.help_label.setText("Ce type de loi nécessite un coefficient de friction > 0.")
        else:
            self.help_label.setText("Propriétés optionnelles sous forme clé=valeur (ex: alert=0.01).")

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
        index = self.tree.indexOfTopLevelItem(item)
        menu = QMenu()
        menu.addAction("✏️ Modifier", lambda idx=index: self.load_for_edit(idx))
        menu.addSeparator()
        menu.addAction("🗑️ Supprimer", lambda idx=index: self._on_delete(idx))

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        index = self.tree.indexOfTopLevelItem(item)
        self.load_for_edit(index)

    def _on_edit_selected(self):
        if self.current_edit_index is not None:
            self.load_for_edit(self.current_edit_index)
        else:
            QMessageBox.information(self, "Sélection", "Veuillez d'abord sélectionner une loi dans la liste.")

    def _on_delete_selected(self):
        if self.current_edit_index is not None:
            self._on_delete(self.current_edit_index)
        else:
            QMessageBox.information(self, "Sélection", "Veuillez d'abord sélectionner une loi à supprimer.")

    def _on_create(self):
        try:
            name = self.name_input.text().strip()
            if not name:
                raise ValidationError("Le nom de la loi ne peut pas être vide")
            if len(name) > 5:
                raise ValidationError("Le nom doit faire maximum 5 caractères")
            
            friction = None
            if self.friction_input.isVisible():
                friction = self.eval_float(
                    self.friction_input.text(),
                    default=0.3,
                    field_name="Friction"
                )
                if friction < 0:
                    raise ValueError("Le coefficient de friction doit être positif")

            law = ContactLaw(
                name=name,
                law_type=ContactLawType(self.type_combo.currentText()),
                friction=friction,
                properties=self.eval_dict(
                    self.props_input.text(),
                    field_name="Propriétés"
                )
            )

            self.controller.add_contact_law(law)
            self.law_created.emit()
            QMessageBox.information(self, "Succès", f"Loi de contact '{law.name}' créée avec succès.")
            self._clear_form()
            self.refresh()

        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la création :\n{e}")

    def _on_edit(self):
        if self.current_edit_index is None:
            return

        try:
            friction = None
            if self.friction_input.isVisible():
                friction = self.eval_float(
                    self.friction_input.text(),
                    default=0.3,
                    field_name="Friction"
                )
                if friction < 0:
                    raise ValueError("Le coefficient de friction doit être positif")

            updated_law = ContactLaw(
                name=self.name_input.text().strip(),
                law_type=ContactLawType(self.type_combo.currentText()),
                friction=friction,
                properties=self.eval_dict(
                    self.props_input.text(),
                    field_name="Propriétés"
                )
            )

            self.controller.update_contact_law(self.current_edit_index, updated_law)
            self.law_updated.emit()
            QMessageBox.information(self, "Succès", f"Loi de contact modifiée avec succès.")
            self._clear_form()
            self.refresh()

        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la modification :\n{e}")

    def _on_delete(self, index: int):
        law = self.controller.state.contact_laws[index]
        
        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Supprimer la loi de contact '{law.name}' ({law.law_type.value}) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.controller.remove_contact_law(index)
            self.law_deleted.emit()
            self._clear_form()
            self.refresh()

    def load_for_edit(self, index: int):
        if not isinstance(index, int):
            print(f"ERREUR : index reçu n'est pas un int : {type(index)} -> {index}")
            return
        if index < 0 or index >= len(self.controller.state.contact_laws):
            print(f"ERREUR : index hors limites : {index}")
            return
        law = self.controller.state.contact_laws[index]
        self.current_edit_index = index

        self.name_input.setText(law.name)
        self.type_combo.setCurrentText(law.law_type.value)
        
        if law.friction is not None:
            self.friction_input.setText(str(law.friction))

        if law.properties:
            props_str = ", ".join(f"{k}={v}" for k, v in law.properties.items())
            self.props_input.setText(props_str)

        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)

        self.help_label.setText(f"🔧 Mode édition — Loi '{law.name}'")
        self.help_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 5px;")

    def _clear_form(self):
        self.name_input.setText("iqsc0")
        self.type_combo.setCurrentIndex(0)
        self.friction_input.setText("0.3")
        self.props_input.clear()
        self.current_edit_index = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.help_label.setText("Sélectionnez un type de loi pour voir les paramètres adaptés.")
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")

    def refresh(self):
        self.tree.clear()
        for law in self.controller.state.contact_laws:
            friction_str = f"{law.friction:.3f}" if law.friction is not None else "-"
            props_str = ", ".join(f"{k}={v}" for k, v in list(law.properties.items())[:3])
            if len(law.properties) > 3:
                props_str += "..."

            item = QTreeWidgetItem([
                law.name,
                law.law_type.value,
                friction_str,
                props_str or "-"
            ])
            
            is_used, _ = self.controller.is_contact_law_used(law.name)
            if is_used:
                item.setForeground(0, QBrush(QColor(0, 100, 0)))

            self.tree.addTopLevelItem(item)

        self._clear_form()
    """Onglet lois de contact"""
    
    law_created = pyqtSignal()
    law_updated = pyqtSignal()
    law_deleted = pyqtSignal()

    def __init__(self, controller: ProjectController):
        super().__init__(controller)
        self.controller = controller
        self.current_edit_index = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # === SECTION 1: ARBRE DES LOIS DE CONTACT ===
        tree_label = QLabel("<b>📋 Liste des Lois de Contact</b>")
        layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nom", "Type", "Friction (µ)", "Autres propriétés"])
        self.tree.setColumnWidth(0, 150)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 100)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(180)
        layout.addWidget(self.tree)

        # === BOUTONS SOUS L'ARBRE : Modifier et Supprimer ===
        actions_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("✏️ Modifier sélection")
        self.edit_btn.setToolTip("Charge la loi sélectionnée dans le formulaire pour modification")
        
        self.delete_btn = QPushButton("🗑️ Supprimer sélection")
        self.delete_btn.setToolTip("Supprime la loi de contact sélectionnée")

        actions_layout.addWidget(self.edit_btn)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # === SECTION 2: FORMULAIRE ===
        form_label = QLabel("<b>📝 Paramètres de la Loi de Contact</b>")
        layout.addWidget(form_label)

        form = QFormLayout()

        # Nom
        self.name_input = QLineEdit("iqsc0")
        self.name_input.setMaxLength(10)
        form.addRow("Nom :", self.name_input)

        # Type de loi
        self.type_combo = QComboBox()
        self.type_combo.addItems([lt.value for lt in ContactLawType])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type :", self.type_combo)

        # Friction (visible selon le type)
        self.friction_label = QLabel("Friction (µ) :")
        self.friction_input = QLineEdit("0.3")
        form.addRow(self.friction_label, self.friction_input)

        # Propriétés supplémentaires
        self.props_input = QLineEdit()
        self.props_input.setPlaceholderText("ex: alert=0.01, pressure=1e5")
        form.addRow("Autres propriétés :", self.props_input)

        layout.addLayout(form)

        # Aide contextuelle
        self.help_label = QLabel("Sélectionnez un type de loi pour voir les paramètres adaptés.")
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.help_label)

        # === BOUTONS PRINCIPAUX EN BAS ===
        btn_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("✅ Créer loi")
        self.update_btn = QPushButton("✏️ Modifier loi")
        self.update_btn.setVisible(False)
        
        self.reset_btn = QPushButton("🔄 Réinitialiser")

        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.add_expression_help_label(layout)
        layout.addStretch()
        self.setLayout(layout)

        self._on_type_changed(self.type_combo.currentText())

    def _connect_signals(self):
        self.create_btn.clicked.connect(self._on_create)
        self.update_btn.clicked.connect(self._on_edit)
        self.reset_btn.clicked.connect(self._clear_form)
        self.edit_btn.clicked.connect(self._on_edit_selected)
        self.delete_btn.clicked.connect(self._on_delete_selected)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)

    def _on_type_changed(self, law_type: str):
        """Affiche/masque le champ friction selon le type"""
        needs_friction = law_type in ["IQS_CLB", "IQS_CLB_G0"]
        
        self.friction_label.setVisible(needs_friction)
        self.friction_input.setVisible(needs_friction)
        
        if needs_friction:
            self.help_label.setText("Ce type de loi nécessite un coefficient de friction > 0.")
        else:
            self.help_label.setText("Propriétés optionnelles sous forme clé=valeur (ex: alert=0.01).")

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
        index = self.tree.indexOfTopLevelItem(item)
        menu = QMenu()
        menu.addAction("✏️ Modifier", lambda idx=index: self.load_for_edit(idx))
        menu.addSeparator()
        menu.addAction("🗑️ Supprimer", lambda idx=index: self._on_delete(idx))

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        index = self.tree.indexOfTopLevelItem(item)
        self.load_for_edit(index)

    def _on_edit_selected(self):
        if self.current_edit_index is not None:
            self.load_for_edit(self.current_edit_index)
        else:
            QMessageBox.information(self, "Sélection", "Veuillez d'abord sélectionner une loi dans la liste.")

    def _on_delete_selected(self):
        if self.current_edit_index is not None:
            self._on_delete(self.current_edit_index)
        else:
            QMessageBox.information(self, "Sélection", "Veuillez d'abord sélectionner une loi à supprimer.")

    def _parse_properties(self, text: str) -> dict:
        if not text.strip():
            return {}
        props = {}
        for pair in text.split(','):
            pair = pair.strip()
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                try:
                    if '.' in value or 'e' in value.lower():
                        props[key] = float(value)
                    else:
                        props[key] = int(value)
                except ValueError:
                    props[key] = value
        return props

    def _on_create(self):
        try:
            name = self.name_input.text().strip()
            if not name:
                raise ValidationError("Le nom de la loi ne peut pas être vide")
            if len(name) > 5:
                raise ValidationError("Le nom doit faire maximum 5 caractères")
            friction = None
            if self.friction_input.isVisible():
                friction = float(self.friction_input.text())
                if friction < 0:
                    raise ValueError("Le coefficient de friction doit être positif")

            law = ContactLaw(
                name=name,
                law_type=ContactLawType(self.type_combo.currentText()),
                friction=friction,
                properties=self._parse_properties(self.props_input.text())
            )

            self.controller.add_contact_law(law)
            self.law_created.emit()
            QMessageBox.information(self, "Succès", f"Loi de contact '{law.name}' créée avec succès.")
            self._clear_form()
            self.refresh()

        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Erreur de saisie", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la création :\n{e}")

    def _on_edit(self):
        if self.current_edit_index is None:
            return

        try:
            friction = None
            if self.friction_input.isVisible():
                friction = float(self.friction_input.text())
                if friction < 0:
                    raise ValueError("Le coefficient de friction doit être positif")

            updated_law = ContactLaw(
                name=self.name_input.text().strip(),
                law_type=ContactLawType(self.type_combo.currentText()),
                friction=friction,
                properties=self._parse_properties(self.props_input.text())
            )

            self.controller.update_contact_law(self.current_edit_index, updated_law)
            self.law_updated.emit()
            QMessageBox.information(self, "Succès", f"Loi de contact modifiée avec succès.")
            self._clear_form()
            self.refresh()

        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Erreur de saisie", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la modification :\n{e}")

    def _on_delete(self, index: int):
        law = self.controller.state.contact_laws[index]
        
        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Supprimer la loi de contact '{law.name}' ({law.law_type.value}) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.controller.remove_contact_law(index)
            self.law_deleted.emit()
            self._clear_form()
            self.refresh()

    def load_for_edit(self, index: int):
        """Charge une loi existante dans le formulaire"""
        if not isinstance(index, int):
            print(f"ERREUR : index reçu n'est pas un int : {type(index)} -> {index}")
            return
        if index < 0 or index >= len(self.controller.state.contact_laws):
            print(f"ERREUR : index hors limites : {index}")
            return
        law = self.controller.state.contact_laws[index]
        self.current_edit_index = index

        self.name_input.setText(law.name)
        self.type_combo.setCurrentText(law.law_type.value)
        
        if law.friction is not None:
            self.friction_input.setText(str(law.friction))

        if law.properties:
            props_str = ", ".join(f"{k}={v}" for k, v in law.properties.items())
            self.props_input.setText(props_str)

        # Passage en mode édition
        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)

        self.help_label.setText(f"🔧 Mode édition — Loi '{law.name}'")
        self.help_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 5px;")

    def _clear_form(self):
        """Réinitialise le formulaire et repasse en mode création"""
        self.name_input.setText("iqsc0")
        self.type_combo.setCurrentIndex(0)
        self.friction_input.setText("0.3")
        self.props_input.clear()
        self.current_edit_index = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.help_label.setText("Sélectionnez un type de loi pour voir les paramètres adaptés.")
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")

    def refresh(self):
        """Rafraîchit l'arbre des lois de contact"""
        self.tree.clear()
        for law in self.controller.state.contact_laws:
            friction_str = f"{law.friction:.3f}" if law.friction is not None else "-"
            props_str = ", ".join(f"{k}={v}" for k, v in list(law.properties.items())[:3])
            if len(law.properties) > 3:
                props_str += "..."

            item = QTreeWidgetItem([
                law.name,
                law.law_type.value,
                friction_str,
                props_str or "-"
            ])
            
            # Colorer si utilisée dans une visibilité
            is_used, _ = self.controller.is_contact_law_used(law.name)
            if is_used:
                item.setForeground(0, QBrush(QColor(0, 100, 0)))  # Vert foncé

            self.tree.addTopLevelItem(item)

        self._clear_form()