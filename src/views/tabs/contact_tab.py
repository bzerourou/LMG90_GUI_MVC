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
    QMenu, QLabel, QScrollArea
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
        self.current_edit_name = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Configure l'interface avec scroll"""
        # Layout principal
        main_layout = QVBoxLayout()
        
        # Créer une zone de défilement
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget contenant tout le contenu
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        scroll_widget.setLayout(layout)
        
        # === ARBRE DES LOIS ===
        tree_label = QLabel("<b>📋 Liste des Lois de Contact</b>")
        layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nom", "Type", "Friction", "Propriétés"])
        self.tree.setColumnWidth(0, 120)
        self.tree.setColumnWidth(1, 180)
        self.tree.setColumnWidth(2, 80)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(200)
        layout.addWidget(self.tree)

        # Boutons arbre
        tree_btn_layout = QHBoxLayout()
        edit_btn = QPushButton("✏️ Modifier Sélection")
        edit_btn.clicked.connect(self._on_edit_from_tree)
        tree_btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Supprimer Sélection")
        delete_btn.clicked.connect(self._on_delete)
        tree_btn_layout.addWidget(delete_btn)
        tree_btn_layout.addStretch()
        layout.addLayout(tree_btn_layout)

        # === FORMULAIRE ===
        form_label = QLabel("<b>📝 Paramètres de la Loi</b>")
        layout.addWidget(form_label)

        form = QFormLayout()

        # Nom
        self.name_input = QLineEdit()
        self.name_input.setMaxLength(20)
        form.addRow("Nom :", self.name_input)

        # Type de loi
        self.type_combo = QComboBox()
        self.type_combo.addItems([lt.value for lt in ContactLawType])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type :", self.type_combo)

        layout.addLayout(form)

        # === CHAMPS SPÉCIFIQUES PAR TYPE ===
        
        # Friction
        self.friction_label = QLabel("Coefficient de friction (fric) :")
        self.friction_input = QLineEdit("0.3")
        
        # IQS_DS_CLB : stfr, dyfr
        self.stfr_label = QLabel("Rigidité statique (stfr) :")
        self.stfr_input = QLineEdit("1e8")
        
        self.dyfr_label = QLabel("Rigidité dynamique (dyfr) :")
        self.dyfr_input = QLineEdit("1e8")
        
        # IQS_MOHR_DS_CLB : stfr, dyfr, cohn, coht
        self.cohn_label = QLabel("Cohésion normale (cohn) :")
        self.cohn_input = QLineEdit("0.0")
        
        self.coht_label = QLabel("Cohésion tangentielle (coht) :")
        self.coht_input = QLineEdit("0.0")
        
        # IQS_MAC_CZM : stfr, dyfr, cn, ct, b, w
        self.cn_label = QLabel("Résistance normale (cn) :")
        self.cn_input = QLineEdit("1e6")
        
        self.ct_label = QLabel("Résistance tangentielle (ct) :")
        self.ct_input = QLineEdit("1e6")
        
        self.b_label = QLabel("Paramètre b :")
        self.b_input = QLineEdit("1.0")
        
        self.w_label = QLabel("Paramètre w :")
        self.w_input = QLineEdit("0.01")
        
        # ELASTIC_WIRE : stiffness, prestrain
        self.stiffness_label = QLabel("Rigidité (stiffness) :")
        self.stiffness_input = QLineEdit("1e6")
        
        self.prestrain_label = QLabel("Pré-déformation (prestrain) :")
        self.prestrain_input = QLineEdit("0.0")
        
        # Créer un formulaire pour ces champs
        self.specific_form = QFormLayout()
        
        self.specific_form.addRow(self.friction_label, self.friction_input)
        self.specific_form.addRow(self.stfr_label, self.stfr_input)
        self.specific_form.addRow(self.dyfr_label, self.dyfr_input)
        self.specific_form.addRow(self.cohn_label, self.cohn_input)
        self.specific_form.addRow(self.coht_label, self.coht_input)
        self.specific_form.addRow(self.cn_label, self.cn_input)
        self.specific_form.addRow(self.ct_label, self.ct_input)
        self.specific_form.addRow(self.b_label, self.b_input)
        self.specific_form.addRow(self.w_label, self.w_input)
        self.specific_form.addRow(self.stiffness_label, self.stiffness_input)
        self.specific_form.addRow(self.prestrain_label, self.prestrain_input)
        
        layout.addLayout(self.specific_form)

        # Info contextuelle
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.help_label)

        # === BOUTONS ===
        btn_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("✅ Créer Loi")
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
        
        # Configurer le scroll
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
        
        # Initialiser l'affichage
        self._on_type_changed(self.type_combo.currentText())

    def _connect_signals(self):
        """Connecte les signaux"""
        self.tree.itemDoubleClicked.connect(self._on_edit_from_tree)

    def _on_type_changed(self, law_type: str):
        """Affiche/masque les champs selon le type de loi"""
        self.name_input.setText("law01")
        # Masquer tous les champs
        for widget in [
            self.friction_label, self.friction_input,
            self.stfr_label, self.stfr_input,
            self.dyfr_label, self.dyfr_input,
            self.cohn_label, self.cohn_input,
            self.coht_label, self.coht_input,
            self.cn_label, self.cn_input,
            self.ct_label, self.ct_input,
            self.b_label, self.b_input,
            self.w_label, self.w_input,
            self.stiffness_label, self.stiffness_input,
            self.prestrain_label, self.prestrain_input
        ]:
            widget.setVisible(False)
        
        # Afficher selon le type
        if law_type == "IQS_CLB":
            self.friction_label.setVisible(True)
            self.friction_input.setVisible(True)
            self.help_label.setText(
                "<b>IQS_CLB</b> : Loi de contact inégalité avec friction de Coulomb.<br>"
                "<b>Paramètres :</b> fric (coefficient de friction)"
            )
        
        elif law_type == "IQS_CLB_g0":
            self.friction_label.setVisible(True)
            self.friction_input.setVisible(True)
            self.help_label.setText(
                "<b>IQS_CLB_g0</b> : Loi IQS_CLB avec initialisation à g0.<br>"
                "<b>Paramètres :</b> fric (coefficient de friction)"
            )
        
        elif law_type == "IQS_DS_CLB":
            self.friction_label.setVisible(True)
            self.friction_input.setVisible(True)
            self.stfr_label.setVisible(True)
            self.stfr_input.setVisible(True)
            self.dyfr_label.setVisible(True)
            self.dyfr_input.setVisible(True)
            self.help_label.setText(
                "<b>IQS_DS_CLB</b> : Loi discrète avec rigidités.<br>"
                "<b>Paramètres :</b> fric, stfr (rigidité statique), dyfr (rigidité dynamique)"
            )
        
        elif law_type == "IQS_MOHR_DS_CLB":
            self.friction_label.setVisible(True)
            self.friction_input.setVisible(True)
            self.stfr_label.setVisible(True)
            self.stfr_input.setVisible(True)
            self.dyfr_label.setVisible(True)
            self.dyfr_input.setVisible(True)
            self.cohn_label.setVisible(True)
            self.cohn_input.setVisible(True)
            self.coht_label.setVisible(True)
            self.coht_input.setVisible(True)
            self.help_label.setText(
                "<b>IQS_MOHR_DS_CLB</b> : Critère de rupture de Mohr-Coulomb.<br>"
                "<b>Paramètres :</b> fric, stfr, dyfr, cohn (cohésion normale), coht (cohésion tangentielle)"
            )
        
        elif law_type == "IQS_MAC_CZM":
            self.stfr_label.setVisible(True)
            self.stfr_input.setVisible(True)
            self.dyfr_label.setVisible(True)
            self.dyfr_input.setVisible(True)
            self.cn_label.setVisible(True)
            self.cn_input.setVisible(True)
            self.ct_label.setVisible(True)
            self.ct_input.setVisible(True)
            self.b_label.setVisible(True)
            self.b_input.setVisible(True)
            self.w_label.setVisible(True)
            self.w_input.setVisible(True)
            self.help_label.setText(
                "<b>IQS_MAC_CZM</b> : Modèle de zone cohésive (Cohesive Zone Model).<br>"
                "<b>Paramètres :</b> stfr, dyfr, cn (résistance normale), ct (résistance tangentielle), b, w"
            )
        
        elif law_type == "ELASTIC_WIRE":
            self.stiffness_label.setVisible(True)
            self.stiffness_input.setVisible(True)
            self.prestrain_label.setVisible(True)
            self.prestrain_input.setVisible(True)
            self.help_label.setText(
                "<b>ELASTIC_WIRE</b> : Loi de fil élastique.<br>"
                "<b>Paramètres :</b> stiffness (rigidité), prestrain (pré-déformation)"
            )
        
        elif law_type == "ELASTIC_REPELL_CLB":
            self.friction_label.setVisible(True)
            self.friction_input.setVisible(True)
            self.help_label.setText(
                "<b>ELASTIC_REPELL_CLB</b> : Répulsion élastique avec friction.<br>"
                "<b>Paramètres :</b> fric (coefficient de friction)"
            )
        
        elif law_type == "COUPLED_DOF":
            self.help_label.setText(
                "<b>COUPLED_DOF</b> : Couplage de degrés de liberté.<br>"
                "<b>Paramètres :</b> Aucun paramètre requis."
            )
        
        else:
            self.help_label.setText("Sélectionnez un type de loi.")

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
        """Crée une nouvelle loi"""
        try:
            law = self._build_law_from_form()
            
            self.controller.add_contact_law(law)
            self.law_created.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"✅ Loi '{law.name}' créée")
            self._clear_form()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")

    def _on_edit_from_tree(self):
        """Charge pour édition depuis l'arbre"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une loi")
            return
        
        law_name = selected.text(0)
        law = self.controller.get_contact_law(law_name)
        
        if not law:
            return
        
        self.load_for_edit(law)

    def _on_update(self):
        """Met à jour la loi"""
        try:
            law = self._build_law_from_form()
            
            self.controller.update_contact_law(self.current_edit_name, law)
            self.law_updated.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", "✅ Loi modifiée")
            self._on_cancel_edit()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Modification échouée :\n{e}")

    def _on_delete(self):
        """Supprime la loi"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une loi")
            return
        
        law_name = selected.text(0)
        law = self.controller.get_contact_law(law_name)
        
        if not law:
            return
        
        # Vérifier si utilisée
        is_used, refs = self.controller.is_contact_law_used(law_name)
        
        if is_used:
            refs_text = "\n• ".join(refs)
            QMessageBox.warning(
                self, "Loi Référencée",
                f"Cette loi est référencée par :\n\n• {refs_text}\n\n"
                f"Supprimez d'abord ces références."
            )
            return
        
        reply = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer la loi '{law_name}' ({law.law_type.value}) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.controller.remove_contact_law(law_name):
                self.law_deleted.emit()
                self.refresh()
                QMessageBox.information(self, "Succès", "✅ Loi supprimée")
                if self.current_edit_name == law_name:
                    self._on_cancel_edit()

    def _show_info(self):
        """Affiche les informations"""
        selected = self.tree.currentItem()
        if not selected:
            return
        
        law_name = selected.text(0)
        law = self.controller.get_contact_law(law_name)
        
        if not law:
            return
        
        is_used, refs = self.controller.is_contact_law_used(law_name)
        
        info = f"<h3>Loi de Contact : {law_name}</h3>"
        info += f"<b>Type :</b> {law.law_type.value}<br>"
        
        if law.friction is not None:
            info += f"<b>Friction :</b> {law.friction}<br>"
        
        if law.properties:
            info += "<br><b>Propriétés :</b><br>"
            for key, value in law.properties.items():
                info += f"  • {key} = {value}<br>"
        
        if is_used:
            info += f"<br><b>✅ Référencée par :</b><br>• {', '.join(refs)}"
        else:
            info += "<br><i>❌ Non référencée</i>"
        
        QMessageBox.information(self, f"Infos : {law_name}", info)

    def _on_cancel_edit(self):
        """Annule l'édition"""
        self.current_edit_name = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self._clear_form()

    def _clear_form(self):
        """Réinitialise le formulaire"""
        self.name_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.friction_input.setText("0.3")
        self.stfr_input.setText("1e8")
        self.dyfr_input.setText("1e8")
        self.cohn_input.setText("0.0")
        self.coht_input.setText("0.0")
        self.cn_input.setText("1e6")
        self.ct_input.setText("1e6")
        self.b_input.setText("1.0")
        self.w_input.setText("0.01")
        self.stiffness_input.setText("1e6")
        self.prestrain_input.setText("0.0")

    def _build_law_from_form(self) -> ContactLaw:
        """Construit une loi depuis le formulaire"""
        name = self.name_input.text().strip()
        if not name:
            raise ValidationError("Le nom ne peut pas être vide")
        
        law_type = ContactLawType(self.type_combo.currentText())
        
        friction = None
        properties = {}
        
        # Récupérer les paramètres selon le type
        if law_type in [ContactLawType.IQS_CLB, ContactLawType.IQS_CLB_G0]:
            friction = self.eval_float(self.friction_input.text(), default=0.3, field_name="Friction")
        
        elif law_type == ContactLawType.IQS_DS_CLB:
            friction = self.eval_float(self.friction_input.text(), default=0.3, field_name="Friction")
            properties['stfr'] = self.eval_float(self.stfr_input.text(), default=1e8, field_name="stfr")
            properties['dyfr'] = self.eval_float(self.dyfr_input.text(), default=1e8, field_name="dyfr")
        
        elif law_type == ContactLawType.IQS_MOHR_DS_CLB:
            friction = self.eval_float(self.friction_input.text(), default=0.3, field_name="Friction")
            properties['stfr'] = self.eval_float(self.stfr_input.text(), default=1e8, field_name="stfr")
            properties['dyfr'] = self.eval_float(self.dyfr_input.text(), default=1e8, field_name="dyfr")
            properties['cohn'] = self.eval_float(self.cohn_input.text(), default=0.0, field_name="cohn")
            properties['coht'] = self.eval_float(self.coht_input.text(), default=0.0, field_name="coht")
        
        elif law_type == ContactLawType.IQS_MAC_CZM:
            properties['stfr'] = self.eval_float(self.stfr_input.text(), default=1e10, field_name="stfr")
            properties['dyfr'] = self.eval_float(self.dyfr_input.text(), default=1e10, field_name="dyfr")
            properties['cn'] = self.eval_float(self.cn_input.text(), default=1e6, field_name="cn")
            properties['ct'] = self.eval_float(self.ct_input.text(), default=1e6, field_name="ct")
            properties['b'] = self.eval_float(self.b_input.text(), default=1.0, field_name="b")
            properties['w'] = self.eval_float(self.w_input.text(), default=0.01, field_name="w")
        
        elif law_type == ContactLawType.ELASTIC_WIRE:
            properties['stiffness'] = self.eval_float(self.stiffness_input.text(), default=1e6, field_name="stiffness")
            properties['prestrain'] = self.eval_float(self.prestrain_input.text(), default=0.0, field_name="prestrain")
        
        elif law_type == ContactLawType.ELASTIC_REPELL_CLB:
            friction = self.eval_float(self.friction_input.text(), default=0.3, field_name="Friction")
        
        return ContactLaw(
            name=name,
            law_type=law_type,
            friction=friction,
            properties=properties
        )

    def load_for_edit(self, law: ContactLaw):
        """Charge une loi pour édition"""
        if not law:
            return
        
        self.current_edit_name = law.name
        
        self.name_input.setText(law.name)
        self.type_combo.setCurrentText(law.law_type.value)
        
        if law.friction is not None:
            self.friction_input.setText(str(law.friction))
        
        # Charger les propriétés
        if 'stfr' in law.properties:
            self.stfr_input.setText(str(law.properties['stfr']))
        if 'dyfr' in law.properties:
            self.dyfr_input.setText(str(law.properties['dyfr']))
        if 'cohn' in law.properties:
            self.cohn_input.setText(str(law.properties['cohn']))
        if 'coht' in law.properties:
            self.coht_input.setText(str(law.properties['coht']))
        if 'cn' in law.properties:
            self.cn_input.setText(str(law.properties['cn']))
        if 'ct' in law.properties:
            self.ct_input.setText(str(law.properties['ct']))
        if 'b' in law.properties:
            self.b_input.setText(str(law.properties['b']))
        if 'w' in law.properties:
            self.w_input.setText(str(law.properties['w']))
        if 'stiffness' in law.properties:
            self.stiffness_input.setText(str(law.properties['stiffness']))
        if 'prestrain' in law.properties:
            self.prestrain_input.setText(str(law.properties['prestrain']))
        
        # Mode édition
        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.cancel_btn.setVisible(True)

    def refresh(self):
        """Rafraîchit l'arbre"""
        self.tree.clear()
        
        for law in self.controller.get_contact_laws():
            friction_str = f"{law.friction:.3f}" if law.friction is not None else "-"
            
            # Afficher max 3 propriétés
            props_list = list(law.properties.items())[:3]
            props_str = ", ".join(f"{k}={v}" for k, v in props_list)
            if len(law.properties) > 3:
                props_str += "..."
            
            item = QTreeWidgetItem([
                law.name,
                law.law_type.value,
                friction_str,
                props_str or "-"
            ])
            
            # Colorer si utilisée
            is_used, _ = self.controller.is_contact_law_used(law.name)
            if is_used:
                item.setForeground(0, QBrush(QColor("green")))
            
            self.tree.addTopLevelItem(item)