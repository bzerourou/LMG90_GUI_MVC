# ============================================================================
# Onglet Tables de Visibilité 
# ============================================================================
"""
Onglet pour créer des tables de visibilité (règles de détection).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QLabel, QHBoxLayout, QGroupBox, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import VisibilityRule
from ...controllers.project_controller import ProjectController


class VisibilityTab(QWidget):
    """Onglet visibilité"""
    
    rule_created = pyqtSignal()
    rule_updated = pyqtSignal()
    rule_deleted = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.current_edit_index = None
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        main_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        scroll_widget.setLayout(layout)
        
        # === ARBRE ===
        tree_label = QLabel("<b>📋 Tables de Visibilité Existantes</b>")
        layout.addWidget(tree_label)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["#", "Candidat", "Antagoniste", "Loi", "Alert"])
        self.tree.setColumnWidth(0, 40)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 150)
        self.tree.setColumnWidth(3, 100)
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
        form_label = QLabel("<b>📝 Formulaire de Règle de Visibilité</b>")
        layout.addWidget(form_label)
        
        # Candidat
        candidate_group = QGroupBox("🔵 Candidat")
        candidate_form = QFormLayout()
        
        self.candidate_body_combo = QComboBox()
        self.candidate_body_combo.addItems(["RBDY2", "RBDY3"])
        candidate_form.addRow("Corps :", self.candidate_body_combo)
        
        self.candidate_contactor_combo = QComboBox()
        #self.candidate_contactor_combo.addItems(["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"])
        candidate_form.addRow("Contacteur :", self.candidate_contactor_combo)
        
        self.candidate_color_input = QLineEdit("BLUEx")
        candidate_form.addRow("Couleur :", self.candidate_color_input)
        
        candidate_group.setLayout(candidate_form)
        layout.addWidget(candidate_group)
        
        # Antagoniste
        antagonist_group = QGroupBox("🔴 Antagoniste")
        antagonist_form = QFormLayout()
        
        self.antagonist_body_combo = QComboBox()
        self.antagonist_body_combo.addItems(["RBDY2", "RBDY3"])
        antagonist_form.addRow("Corps :", self.antagonist_body_combo)
        
        self.antagonist_contactor_combo = QComboBox()
        #self.antagonist_contactor_combo.addItems(["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"])
        antagonist_form.addRow("Contacteur :", self.antagonist_contactor_combo)
        
        self.antagonist_color_input = QLineEdit("VERTx")
        antagonist_form.addRow("Couleur :", self.antagonist_color_input)
        
        antagonist_group.setLayout(antagonist_form)
        layout.addWidget(antagonist_group)
        
        # Loi de contact et Alert
        params_form = QFormLayout()
        
        self.behavior_combo = QComboBox()
        params_form.addRow("Loi de contact :", self.behavior_combo)
        
        self.alert_input = QLineEdit("0.1")
        params_form.addRow("Alert (distance) :", self.alert_input)
        
        layout.addLayout(params_form)
        
        # Aide
        help_label = QLabel(
            "💡 <i>La table de visibilité définit quels contacteurs peuvent interagir.<br>"
            "Candidat = corps actif, Antagoniste = corps passif.</i>"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(help_label)
        
        # === BOUTONS ===
        btn_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("✅ Créer Règle de Visibilité")
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
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.tree.itemDoubleClicked.connect(self._on_edit_from_tree)
        self.candidate_body_combo.currentTextChanged.connect(self._update_candidate_contactors)
        self.antagonist_body_combo.currentTextChanged.connect(self._update_antagonist_contactors)
    
    def _update_candidate_contactors(self, body_type):
        """Met à jour les contacteurs candidats selon le type de corps"""
        self.candidate_contactor_combo.clear()
        if body_type == "RBDY2":
            self.candidate_contactor_combo.addItems(["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"])
        else:  # RBDY3
            self.candidate_contactor_combo.addItems(["SPHER",  "PLANx", "CYLND", "POLYR", "PT3Dx"])

    def _update_antagonist_contactors(self, body_type):
        """Met à jour les contacteurs antagonistes selon le type de corps"""
        self.antagonist_contactor_combo.clear()
        if body_type == "RBDY2":
            self.antagonist_contactor_combo.addItems(["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"])
        else:  # RBDY3
            self.antagonist_contactor_combo.addItems(["SPHER",  "PLANx", "CYLND", "POLYR", "PT3Dx"])

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
        """Crée la règle de visibilité"""
        try:
            rule = VisibilityRule(
                candidate_body=self.candidate_body_combo.currentText(),
                candidate_contactor=self.candidate_contactor_combo.currentText(),
                candidate_color=self.candidate_color_input.text().strip(),
                antagonist_body=self.antagonist_body_combo.currentText(),
                antagonist_contactor=self.antagonist_contactor_combo.currentText(),
                antagonist_color=self.antagonist_color_input.text().strip(),
                behavior_name=self.behavior_combo.currentText(),
                alert=float(self.alert_input.text())
            )
            
            self.controller.add_visibility_rule(rule)
            
            self.rule_created.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", "✅ Règle de visibilité créée")
            self._clear_form()
            
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def _on_edit_from_tree(self):
        """Charge pour édition"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une règle")
            return
        
        rule_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        rule = self.controller.get_visibility_rule(rule_idx)
        
        if rule:
            self.load_for_edit(rule_idx, rule)
    
    def _on_update(self):
        """Met à jour"""
        try:
            rule = VisibilityRule(
                candidate_body=self.candidate_body_combo.currentText(),
                candidate_contactor=self.candidate_contactor_combo.currentText(),
                candidate_color=self.candidate_color_input.text().strip(),
                antagonist_body=self.antagonist_body_combo.currentText(),
                antagonist_contactor=self.antagonist_contactor_combo.currentText(),
                antagonist_color=self.antagonist_color_input.text().strip(),
                behavior_name=self.behavior_combo.currentText(),
                alert=float(self.alert_input.text())
            )
            
            self.controller.update_visibility_rule(self.current_edit_index, rule)
            
            self.rule_updated.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", "✅ Règle modifiée")
            self._on_cancel_edit()
            
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Modification échouée :\n{e}")
    
    def _on_delete(self):
        """Supprime"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une règle")
            return
        
        rule_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer la règle de visibilité #{rule_idx + 1} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.controller.remove_visibility_rule(rule_idx):
                self.rule_deleted.emit()
                self.refresh()
                QMessageBox.information(self, "Succès", "✅ Règle supprimée")
                if self.current_edit_index == rule_idx:
                    self._on_cancel_edit()
    
    def _show_info(self):
        """Affiche infos"""
        selected = self.tree.currentItem()
        if not selected:
            return
        
        rule_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        rule = self.controller.get_visibility_rule(rule_idx)
        
        if not rule:
            return
        
        info = f"<h3>Règle de Visibilité #{rule_idx + 1}</h3>"
        info += "<br><b>🔵 Candidat :</b><br>"
        info += f"  • Corps : {rule.candidate_body}<br>"
        info += f"  • Contacteur : {rule.candidate_contactor}<br>"
        info += f"  • Couleur : {rule.candidate_color}<br>"
        info += "<br><b>🔴 Antagoniste :</b><br>"
        info += f"  • Corps : {rule.antagonist_body}<br>"
        info += f"  • Contacteur : {rule.antagonist_contactor}<br>"
        info += f"  • Couleur : {rule.antagonist_color}<br>"
        info += f"<br><b>Loi de contact :</b> {rule.behavior_name}<br>"
        info += f"<b>Distance d'alerte :</b> {rule.alert}<br>"
        
        QMessageBox.information(self, f"Infos : Règle #{rule_idx + 1}", info)
    
    def _on_cancel_edit(self):
        """Annule édition"""
        self.current_edit_index = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self._clear_form()
    
    def _clear_form(self):
        """Réinitialise"""
        self.candidate_body_combo.setCurrentIndex(0)
        self.candidate_contactor_combo.setCurrentIndex(0)
        self.candidate_color_input.setText("BLUEx")
        
        self.antagonist_body_combo.setCurrentIndex(0)
        self.antagonist_contactor_combo.setCurrentIndex(0)
        self.antagonist_color_input.setText("VERTx")
        
        self.alert_input.setText("0.1")
        
        if self.behavior_combo.count() > 0:
            self.behavior_combo.setCurrentIndex(0)
    
    def load_for_edit(self, index: int, rule: VisibilityRule):
        """Charge pour édition"""
        self.current_edit_index = index
        
        self.candidate_body_combo.setCurrentText(rule.candidate_body)
        self.candidate_contactor_combo.setCurrentText(rule.candidate_contactor)
        self.candidate_color_input.setText(rule.candidate_color)
        
        self.antagonist_body_combo.setCurrentText(rule.antagonist_body)
        self.antagonist_contactor_combo.setCurrentText(rule.antagonist_contactor)
        self.antagonist_color_input.setText(rule.antagonist_color)
        
        self.behavior_combo.setCurrentText(rule.behavior_name)
        self.alert_input.setText(str(rule.alert))
        
        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.cancel_btn.setVisible(True)
    
    def refresh(self):
        """Rafraîchit"""
        self.tree.clear()
        
        self.behavior_combo.clear()
        laws = self.controller.get_contact_laws()
        self.behavior_combo.addItems([law.name for law in laws])
        
        rules = self.controller.get_visibility_rules()
        
        for idx, rule in enumerate(rules):
            candidat_str = f"{rule.candidate_contactor} ({rule.candidate_color})"
            antagonist_str = f"{rule.antagonist_contactor} ({rule.antagonist_color})"
            
            item = QTreeWidgetItem([
                str(idx + 1),
                candidat_str,
                antagonist_str,
                rule.behavior_name,
                str(rule.alert)
            ])
            
            item.setData(0, Qt.ItemDataRole.UserRole, idx)
            
            self.tree.addTopLevelItem(item)
        
        self._update_antagonist_contactors(self.antagonist_body_combo.currentText())
        self._update_candidate_contactors(self.candidate_body_combo.currentText())