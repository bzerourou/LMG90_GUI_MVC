# ============================================================================
# ContactTab
# ============================================================================
"""
Onglet de gestion des lois de contact avec création, modification et suppression.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QLabel, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import (
    ContactLaw, ContactLawType, CONTACT_LAW_CATEGORIES,
)
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

    # ── Construction de l'interface ───────────────────────────────────────────
    def _setup_ui(self):
        main_layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_widget = QWidget()
        layout = QVBoxLayout()
        scroll_widget.setLayout(layout)

        # ── Arbre des lois existantes ─────────────────────────────────────────
        layout.addWidget(QLabel("<b>📋 Liste des Lois de Contact</b>"))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nom", "Type", "Friction", "Propriétés"])
        self.tree.setColumnWidth(0, 120)
        self.tree.setColumnWidth(1, 200)
        self.tree.setColumnWidth(2, 70)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(200)
        layout.addWidget(self.tree)

        tree_btn_layout = QHBoxLayout()
        edit_btn = QPushButton("✏️ Modifier Sélection")
        edit_btn.clicked.connect(self._on_edit_from_tree)
        tree_btn_layout.addWidget(edit_btn)
        delete_btn = QPushButton("🗑️ Supprimer Sélection")
        delete_btn.clicked.connect(self._on_delete)
        tree_btn_layout.addWidget(delete_btn)
        tree_btn_layout.addStretch()
        layout.addLayout(tree_btn_layout)

        # ── Formulaire principal ──────────────────────────────────────────────
        layout.addWidget(QLabel("<b>📝 Paramètres de la Loi</b>"))
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setMaxLength(20)
        form.addRow("Nom :", self.name_input)

        # Combo catégorie
        self.category_combo = QComboBox()
        self.category_combo.addItems(list(CONTACT_LAW_CATEGORIES.keys()))
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        form.addRow("Catégorie :", self.category_combo)

        # Combo type (filtré par catégorie)
        self.type_combo = QComboBox()
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type :", self.type_combo)

        layout.addLayout(form)

        # ── Champs spécifiques (tous créés ici, visibilité contrôlée) ─────────

        # fric
        self.friction_label = QLabel("Coefficient de friction (fric) :")
        self.friction_input = QLineEdit("0.3")

        # rstn / rstt (RST_CLB)
        self.rstn_label = QLabel("Coefficient de restitution normale (rstn) :")
        self.rstn_input = QLineEdit("0.1")  
        self.rstt_label = QLabel("Coefficient de restitution tangentielle (rstt) :")    
        self.rstt_input = QLineEdit("0.1")

        # stfr / dyfr
        self.stfr_label = QLabel("Rigidité de contact statique (stfr) :")
        self.stfr_input = QLineEdit("1e8")
        self.dyfr_label = QLabel("Rigidité de contact dynamique (dyfr) :")
        self.dyfr_input = QLineEdit("1e8")

        # cohn / coht
        self.cohn_label = QLabel("Cohésion normale (cohn) :")
        self.cohn_input = QLineEdit("0.0")
        self.coht_label = QLabel("Cohésion tangentielle (coht) :")
        self.coht_input = QLineEdit("0.0")

        # cn / ct / b / w
        self.cn_label = QLabel("Résistance normale (cn) :")
        self.cn_input = QLineEdit("1e6")
        self.ct_label = QLabel("Résistance tangentielle (ct) :")
        self.ct_input = QLineEdit("1e6")
        self.b_label  = QLabel("Paramètre de mélange (b) :")
        self.b_input  = QLineEdit("1.0")
        self.w_label  = QLabel("Énergie de rupture (w) :")
        self.w_input  = QLineEdit("0.01")
        self.s1_label = QLabel("Paramètre de surface 1 (s1) :")
        self.s1_input = QLineEdit("0.0")
        self.s2_label = QLabel("Paramètre de surface 2 (s2) :")
        self.s2_input = QLineEdit("0.0")
        self.g1_label = QLabel("Paramètre de glissement 1 (g1) :")
        self.g1_input = QLineEdit("0.0")
        self.g2_label = QLabel("Paramètre de glissement 2 (g2) :")
        self.g2_input = QLineEdit("0.0")

        # stiffness / prestrain
        self.stiffness_label = QLabel("Rigidité axiale (stiffness) :")
        self.stiffness_input = QLineEdit("1e6")
        self.prestrain_label = QLabel("Pré-déformation (prestrain) :")
        self.prestrain_input = QLineEdit("0.0")

        # sigc  (BRITTLE_ELASTIC_WIRE)
        self.sigc_label = QLabel("Fmax :")
        self.sigc_input = QLineEdit("1e6")

        # viscosity  (VOIGT_ROD)
        self.viscosity_label = QLabel("Viscosité (viscosity) :")
        self.viscosity_input = QLineEdit("1e3")

        # Kn  (ELASTIC_REPELL_CLB)
        self.kn_label = QLabel("Rigidité axiale (stiffness) :")
        self.kn_input = QLineEdit("1e8")

        # Formulaire des champs spécifiques
        self.specific_form = QFormLayout()
        self.specific_form.addRow(self.friction_label,  self.friction_input)
        self.specific_form.addRow(self.rstn_label,      self.rstn_input)
        self.specific_form.addRow(self.rstt_label,      self.rstt_input)
        self.specific_form.addRow(self.stfr_label,      self.stfr_input)
        self.specific_form.addRow(self.dyfr_label,      self.dyfr_input)
        self.specific_form.addRow(self.cohn_label,      self.cohn_input)
        self.specific_form.addRow(self.coht_label,      self.coht_input)
        self.specific_form.addRow(self.cn_label,        self.cn_input)
        self.specific_form.addRow(self.ct_label,        self.ct_input)
        self.specific_form.addRow(self.b_label,         self.b_input)
        self.specific_form.addRow(self.w_label,         self.w_input)
        self.specific_form.addRow(self.stiffness_label, self.stiffness_input)
        self.specific_form.addRow(self.prestrain_label, self.prestrain_input)
        self.specific_form.addRow(self.sigc_label,      self.sigc_input)
        self.specific_form.addRow(self.s1_label,        self.s1_input)
        self.specific_form.addRow(self.s2_label,        self.s2_input)
        self.specific_form.addRow(self.g1_label,        self.g1_input)
        self.specific_form.addRow(self.g2_label,        self.g2_input)
        self.specific_form.addRow(self.viscosity_label, self.viscosity_input)
        self.specific_form.addRow(self.kn_label,        self.kn_input)
        layout.addLayout(self.specific_form)

        # Aide contextuelle
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet(
            "background-color: #e3f2fd; padding: 10px; border-radius: 5px;"
        )
        layout.addWidget(self.help_label)

        # ── Boutons ───────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()

        self.create_btn = QPushButton("✅ Créer Loi")
        self.create_btn.setStyleSheet("font-weight: bold;")
        self.create_btn.clicked.connect(self._on_create)
        btn_layout.addWidget(self.create_btn)

        self.update_btn = QPushButton("💾 Enregistrer Modifications")
        self.update_btn.setStyleSheet(
            "font-weight: bold; background-color: #4CAF50; color: white;"
        )
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

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

        # Initialiser le combo type via la catégorie par défaut
        self._on_category_changed(self.category_combo.currentText())

    def _connect_signals(self):
        self.tree.itemDoubleClicked.connect(self._on_edit_from_tree)

    # ── Gestion catégorie / type ──────────────────────────────────────────────
    def _on_category_changed(self, category: str):
        """Recharge le combo type selon la catégorie sélectionnée."""
        laws    = CONTACT_LAW_CATEGORIES.get(category, [])
        current = self.type_combo.currentText()
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        self.type_combo.addItems(laws)
        if current in laws:
            self.type_combo.setCurrentText(current)
        self.type_combo.blockSignals(False)
        self._on_type_changed(self.type_combo.currentText())

    def _all_specific_widgets(self):
        """Retourne tous les widgets spécifiques pour masquage groupé."""
        return [
            self.friction_label,  self.friction_input,
            self.rstn_label,      self.rstn_input,
            self.rstt_label,      self.rstt_input,
            self.stfr_label,      self.stfr_input,
            self.dyfr_label,      self.dyfr_input,
            self.cohn_label,      self.cohn_input,
            self.coht_label,      self.coht_input,
            self.cn_label,        self.cn_input,
            self.ct_label,        self.ct_input,
            self.b_label,         self.b_input,
            self.w_label,         self.w_input,
            self.stiffness_label, self.stiffness_input,
            self.prestrain_label, self.prestrain_input,
            self.sigc_label,      self.sigc_input,
            self.viscosity_label, self.viscosity_input,
            self.kn_label,        self.kn_input,
            self.s1_label,        self.s1_input,
            self.s2_label,        self.s2_input,
            self.g1_label,        self.g1_input,
            self.g2_label,        self.g2_input,
        ]

    def _show(self, *widgets):
        """Rend visibles les widgets passés en argument."""
        for w in widgets:
            w.setVisible(True)

    def _on_type_changed(self, law_type: str):
        """Affiche/masque les champs et met à jour l'aide selon le type."""
        self.name_input.setText("law01")
        for w in self._all_specific_widgets():
            w.setVisible(False)

        # ── Rigide / Rigide ───────────────────────────────────────────────────
        if law_type == "IQS_CLB":
            self._show(self.friction_label, self.friction_input)
            self.help_label.setText(
                "<b>IQS_CLB</b> — Contact inégalité avec friction de Coulomb (rigide/rigide).<br>"
                "<b>Paramètres :</b> fric"
            )

        elif law_type == "IQS_CLB_g0":
            self._show(self.friction_label, self.friction_input)
            self.help_label.setText(
                "<b>IQS_CLB_g0</b> — IQS_CLB avec initialisation du jeu à g0 (rigide/rigide).<br>"
                "<b>Paramètres :</b> fric"
            )

        elif law_type == "IQS_DS_CLB":
            self._show(
                self.friction_label, self.friction_input,
                self.stfr_label,     self.stfr_input,
                self.dyfr_label,     self.dyfr_input,
            )
            self.help_label.setText(
                "<b>IQS_DS_CLB</b> — Loi discrète avec rigidités de contact (rigide/rigide).<br>"
                "<b>Paramètres :</b> fric, stfr (rigidité statique), dyfr (rigidité dynamique)"
            )

        elif law_type == "IQS_MOHR_DS_CLB":
            self._show(
                self.friction_label, self.friction_input,
                self.stfr_label,     self.stfr_input,
                self.dyfr_label,     self.dyfr_input,
                self.cohn_label,     self.cohn_input,
                self.coht_label,     self.coht_input,
            )
            self.help_label.setText(
                "<b>IQS_MOHR_DS_CLB</b> — Critère de Mohr-Coulomb avec cohésion (rigide/rigide).<br>"
                "<b>Paramètres :</b> fric, stfr, dyfr, cohn (cohésion normale), coht (cohésion tangentielle)"
            )

        elif law_type == "IQS_MAC_CZM":
            self._show(
                self.stfr_label, self.stfr_input,
                self.dyfr_label, self.dyfr_input,
                self.cn_label,   self.cn_input,
                self.ct_label,   self.ct_input,
                self.b_label,    self.b_input,
                self.w_label,    self.w_input,
            )
            self.help_label.setText(
                "<b>IQS_MAC_CZM</b> — Modèle de zone cohésive MAC (rigide/rigide).<br>"
                "<b>Paramètres :</b> stfr, dyfr, cn (résistance normale), ct (résistance tangentielle), b, w"
            )

        elif law_type == "RST_CLB":
            self._show(self.friction_label, self.friction_input,
                        self.rstn_label, self.rstn_input,
                       self.rstt_label, self.rstt_input)
            self.help_label.setText(
                "<b>RST_CLB</b> — Contact avec restitution et friction de Coulomb (rigide/rigide).<br>"
                "<b>Paramètres :</b> rstn (coefficient de restitution normale), rstt (coefficient de restitution tangentielle)"
            )

        # ── Rigide / Déformable ───────────────────────────────────────────────
        elif law_type == "GAP_SGR_CLB":
            self._show(self.friction_label, self.friction_input)
            self.help_label.setText(
                "<b>GAP_SGR_CLB</b> — Contact avec jeu et friction de Coulomb (rigide/déformable).<br>"
                "<b>Paramètres :</b> fric"
            )

        elif law_type == "GAP_SGR_CLB_g0":
            self._show(self.friction_label, self.friction_input)
            self.help_label.setText(
                "<b>GAP_SGR_CLB_g0</b> — GAP_SGR_CLB avec initialisation à g0 (rigide/déformable).<br>"
                "<b>Paramètres :</b> fric"
            )

        elif law_type == "GAP_MOHR_DS_CLB":
            self._show(
                self.friction_label, self.friction_input,
                self.stfr_label,     self.stfr_input,
                self.dyfr_label,     self.dyfr_input,
                self.cohn_label,     self.cohn_input,
                self.coht_label,     self.coht_input,
            )
            self.help_label.setText(
                "<b>GAP_MOHR_DS_CLB</b> — Critère de Mohr-Coulomb avec jeu (rigide/déformable).<br>"
                "<b>Paramètres :</b> fric, stfr, dyfr, cohn, coht"
            )

        elif law_type == "MAC_CZM":
            self._show(
                self.stfr_label, self.stfr_input,
                self.dyfr_label, self.dyfr_input,
                self.cn_label,   self.cn_input,
                self.ct_label,   self.ct_input,
                self.b_label,    self.b_input,
                self.w_label,    self.w_input,
            )
            self.help_label.setText(
                "<b>MAC_CZM</b> — Modèle de zone cohésive MAC (rigide/déformable ou déf/déf).<br>"
                "<b>Paramètres :</b> stfr, dyfr, cn, ct, b, w"
            )

        elif law_type == "MAL_CZM":
            self._show(
                self.stfr_label, self.stfr_input,
                self.dyfr_label, self.dyfr_input,
                self.cn_label,   self.cn_input,
                self.ct_label,   self.ct_input,
                self.s1_label,    self.s1_input,
                self.s2_label,    self.s2_input,
                self.g1_label,    self.g1_input,
                self.g2_label,    self.g2_input,
            )
            self.help_label.setText(
                "<b>MAL_CZM</b> — Modèle de zone cohésive MAL (rigide/déformable ou déf/déf).<br>"
                "<b>Paramètres :</b> stfr, dyfr, cn, ct, s1, s2, G1, G2"
            )

        # ── Point / Point ─────────────────────────────────────────────────────
        elif law_type == "ELASTIC_WIRE":
            self._show(
                self.stiffness_label, self.stiffness_input,
                self.prestrain_label, self.prestrain_input,
            )
            self.help_label.setText(
                "<b>ELASTIC_WIRE</b> — Câble élastique (point/point).<br>"
                "<b>Paramètres :</b> stiffness (rigidité axiale), prestrain (pré-déformation)"
            )

        elif law_type == "BRITTLE_ELASTIC_WIRE":
            self._show(
                self.stiffness_label, self.stiffness_input,
                self.prestrain_label, self.prestrain_input,
                self.sigc_label,      self.sigc_input,
            )
            self.help_label.setText(
                "<b>BRITTLE_ELASTIC_WIRE</b> — Câble élastique fragile (point/point).<br>"
                "<b>Paramètres :</b> stiffness, prestrain, Fmax (force maximale à la rupture)"
            )

        elif law_type == "ELASTIC_ROD":
            self._show(
                self.stiffness_label, self.stiffness_input,
                self.prestrain_label, self.prestrain_input,
            )
            self.help_label.setText(
                "<b>ELASTIC_ROD</b> — Barre élastique (point/point).<br>"
                "<b>Paramètres :</b> stiffness (rigidité axiale), prestrain (pré-déformation)"
            )

        elif law_type == "VOIGT_ROD":
            self._show(
                self.stiffness_label,  self.stiffness_input,
                self.viscosity_label,  self.viscosity_input,
                self.prestrain_label,  self.prestrain_input,
            )
            self.help_label.setText(
                "<b>VOIGT_ROD</b> — Barre visco-élastique de Voigt (point/point).<br>"
                "<b>Paramètres :</b> stiffness, viscosity (viscosité), prestrain"
            )

        # ── Any / Any ─────────────────────────────────────────────────────────
        elif law_type == "COUPLED_DOF":
            self.help_label.setText(
                "<b>COUPLED_DOF</b> — Couplage de degrés de liberté (any/any).<br>"
                "<b>Paramètres :</b> aucun paramètre requis."
            )

        elif law_type == "NORMAL_COUPLED_DOF":
            self.help_label.setText(
                "<b>NORMAL_COUPLED_DOF</b> — Couplage en direction normale uniquement (any/any).<br>"
                "<b>Paramètres :</b> aucun paramètre requis."
            )

        elif law_type == "ELASTIC_REPELL_CLB":
            self._show(
                self.friction_label, self.friction_input,
                self.kn_label,       self.kn_input,
            )
            self.help_label.setText(
                "<b>ELASTIC_REPELL_CLB</b> — Répulsion élastique avec friction de Coulomb (any/any).<br>"
                "<b>Paramètres :</b> fric, stiffness (rigidité normale)"
            )

        else:
            self.help_label.setText("Sélectionnez un type de loi.")

    # ── Menu contextuel ───────────────────────────────────────────────────────
    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
        menu = QMenu()
        menu.addAction("✏️ Modifier").triggered.connect(self._on_edit_from_tree)
        menu.addAction("🗑️ Supprimer").triggered.connect(self._on_delete)
        menu.addSeparator()
        menu.addAction("ℹ️ Informations").triggered.connect(self._show_info)
        menu.exec(self.tree.viewport().mapToGlobal(position))

    # ── Actions CRUD ──────────────────────────────────────────────────────────
    def _on_create(self):
        try:
            law = self._build_law_from_form()
            self.controller.add_contact_law(law)
            self.law_created.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"✅ Loi '{law.name}' créée")
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")

    def _on_edit_from_tree(self):
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une loi")
            return
        law = self.controller.get_contact_law(selected.text(0))
        if law:
            self.load_for_edit(law)

    def _on_update(self):
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
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une loi")
            return
        law_name = selected.text(0)
        law = self.controller.get_contact_law(law_name)
        if not law:
            return
        is_used, refs = self.controller.is_contact_law_used(law_name)
        if is_used:
            QMessageBox.warning(
                self, "Loi Référencée",
                f"Cette loi est référencée par :\n\n• {chr(10).join(refs)}\n\n"
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
        selected = self.tree.currentItem()
        if not selected:
            return
        law_name = selected.text(0)
        law = self.controller.get_contact_law(law_name)
        if not law:
            return
        is_used, refs = self.controller.is_contact_law_used(law_name)
        info  = f"<h3>Loi de Contact : {law_name}</h3>"
        info += f"<b>Type :</b> {law.law_type.value}<br>"
        if law.friction is not None:
            info += f"<b>Friction :</b> {law.friction}<br>"
        if law.properties:
            info += "<br><b>Propriétés :</b><br>"
            for k, v in law.properties.items():
                info += f"  • {k} = {v}<br>"
        if is_used:
            info += f"<br><b>✅ Référencée par :</b><br>• {', '.join(refs)}"
        else:
            info += "<br><i>❌ Non référencée</i>"
        QMessageBox.information(self, f"Infos : {law_name}", info)

    def _on_cancel_edit(self):
        self.current_edit_name = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)

    def _clear_form(self):
        self.name_input.clear()
        self.category_combo.setCurrentIndex(0)
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
        self.sigc_input.setText("1e6")
        self.viscosity_input.setText("1e3")
        self.kn_input.setText("1e8")

    # ── Construction de la loi depuis le formulaire ───────────────────────────
    def _build_law_from_form(self) -> ContactLaw:
        name = self.name_input.text().strip()
        if not name:
            raise ValidationError("Le nom ne peut pas être vide")

        law_type   = ContactLawType(self.type_combo.currentText())
        friction   = None
        properties = {}
        ef         = self.eval_float  # raccourci

        # ── Rigide / Rigide ───────────────────────────────────────────────────
        if law_type in (ContactLawType.IQS_CLB, ContactLawType.IQS_CLB_G0):
            friction = ef(self.friction_input.text(), default=0.3, field_name="fric")
        elif law_type == ContactLawType.RST_CLB:
            friction = ef(self.friction_input.text(), default=0.3, field_name="fric")
            rstn = ef(self.rstn_input.text(), default=0.0, field_name="rstn")
            rstt = ef(self.rstt_input.text(), default=0.0, field_name="rstt")
            properties['rstn'] = rstn
            properties['rstt'] = rstt

        elif law_type == ContactLawType.IQS_DS_CLB:
            friction           = ef(self.friction_input.text(), default=0.3, field_name="fric")
            properties['stfr'] = ef(self.stfr_input.text(),     default=1e8, field_name="stfr")
            properties['dyfr'] = ef(self.dyfr_input.text(),     default=1e8, field_name="dyfr")

        elif law_type == ContactLawType.IQS_MOHR_DS_CLB:
            friction           = ef(self.friction_input.text(), default=0.3, field_name="fric")
            properties['stfr'] = ef(self.stfr_input.text(),     default=1e8, field_name="stfr")
            properties['dyfr'] = ef(self.dyfr_input.text(),     default=1e8, field_name="dyfr")
            properties['cohn'] = ef(self.cohn_input.text(),     default=0.0, field_name="cohn")
            properties['coht'] = ef(self.coht_input.text(),     default=0.0, field_name="coht")

        elif law_type == ContactLawType.IQS_MAC_CZM:
            properties['stfr'] = ef(self.stfr_input.text(), default=1e10, field_name="stfr")
            properties['dyfr'] = ef(self.dyfr_input.text(), default=1e10, field_name="dyfr")
            properties['cn']   = ef(self.cn_input.text(),   default=1e6,  field_name="cn")
            properties['ct']   = ef(self.ct_input.text(),   default=1e6,  field_name="ct")
            properties['b']    = ef(self.b_input.text(),    default=1.0,  field_name="b")
            properties['w']    = ef(self.w_input.text(),    default=0.01, field_name="w")

        # ── Rigide / Déformable ───────────────────────────────────────────────
        elif law_type in (ContactLawType.GAP_SGR_CLB, ContactLawType.GAP_SGR_CLB_G0):
            friction = ef(self.friction_input.text(), default=0.3, field_name="fric")

        elif law_type == ContactLawType.GAP_MOHR_DS_CLB:
            friction           = ef(self.friction_input.text(), default=0.3, field_name="fric")
            properties['stfr'] = ef(self.stfr_input.text(),     default=1e8, field_name="stfr")
            properties['dyfr'] = ef(self.dyfr_input.text(),     default=1e8, field_name="dyfr")
            properties['cohn'] = ef(self.cohn_input.text(),     default=0.0, field_name="cohn")
            properties['coht'] = ef(self.coht_input.text(),     default=0.0, field_name="coht")

        elif law_type == ContactLawType.MAC_CZM:
            properties['stfr'] = ef(self.stfr_input.text(), default=1e10, field_name="stfr")
            properties['dyfr'] = ef(self.dyfr_input.text(), default=1e10, field_name="dyfr")
            properties['cn']   = ef(self.cn_input.text(),   default=1e6,  field_name="cn")
            properties['ct']   = ef(self.ct_input.text(),   default=1e6,  field_name="ct")
            properties['b']    = ef(self.b_input.text(),    default=1.0,  field_name="b")
            properties['w']    = ef(self.w_input.text(),    default=0.01, field_name="w")
        elif law_type == ContactLawType.MAL_CZM:
            properties['stfr'] = ef(self.stfr_input.text(), default=1e10, field_name="stfr")
            properties['dyfr'] = ef(self.dyfr_input.text(), default=1e10, field_name="dyfr")
            properties['cn']   = ef(self.cn_input.text(),   default=1e6,  field_name="cn")
            properties['ct']   = ef(self.ct_input.text(),   default=1e6,  field_name="ct")
            properties['s1']    = ef(self.s1_input.text(),    default=1.0,  field_name="s1")
            properties['s2']    = ef(self.s2_input.text(),    default=1.0,  field_name="s2")
            properties['G1']    = ef(self.g1_input.text(),    default=1.0,  field_name="G1")
            properties['G2']    = ef(self.g2_input.text(),    default=1.0,  field_name="G2")
        # ── Point / Point ─────────────────────────────────────────────────────
        elif law_type in (ContactLawType.ELASTIC_WIRE, ContactLawType.ELASTIC_ROD):
            properties['stiffness'] = ef(self.stiffness_input.text(), default=1e6, field_name="stiffness")
            properties['prestrain'] = ef(self.prestrain_input.text(), default=0.0, field_name="prestrain")

        elif law_type == ContactLawType.BRITTLE_ELASTIC_WIRE:
            properties['stiffness'] = ef(self.stiffness_input.text(), default=1e6, field_name="stiffness")
            properties['prestrain'] = ef(self.prestrain_input.text(), default=0.0, field_name="prestrain")
            properties['Fmax']      = ef(self.sigc_input.text(),      default=1e6, field_name="Fmax")

        elif law_type == ContactLawType.VOIGT_ROD:
            properties['stiffness'] = ef(self.stiffness_input.text(),  default=1e6, field_name="stiffness")
            properties['viscosity'] = ef(self.viscosity_input.text(),  default=1e3, field_name="viscosity")
            properties['prestrain'] = ef(self.prestrain_input.text(),  default=0.0, field_name="prestrain")

        # ── Any / Any ─────────────────────────────────────────────────────────
        elif law_type in (ContactLawType.COUPLED_DOF, ContactLawType.NORMAL_COUPLED_DOF):
            pass  # aucun paramètre

        elif law_type == ContactLawType.ELASTIC_REPELL_CLB:
            friction         = ef(self.friction_input.text(), default=0.3, field_name="fric")
            properties['stiffness'] = ef(self.kn_input.text(),       default=1e8, field_name="stiffness")

        return ContactLaw(
            name=name,
            law_type=law_type,
            friction=friction,
            properties=properties,
        )

    # ── Chargement pour édition ───────────────────────────────────────────────
    def load_for_edit(self, law: ContactLaw):
        if not law:
            return
        self.current_edit_name = law.name
        self.name_input.setText(law.name)

        # Sélectionner la bonne catégorie puis le bon type
        law_value = law.law_type.value.strip()
        for cat, laws in CONTACT_LAW_CATEGORIES.items():
            if law_value in laws:
                self.category_combo.setCurrentText(cat)
                break
        self.type_combo.setCurrentText(law_value)

        if law.friction is not None:
            self.friction_input.setText(str(law.friction))

        p = law.properties
        if 'stfr'      in p: self.stfr_input.setText(str(p['stfr']))
        if 'dyfr'      in p: self.dyfr_input.setText(str(p['dyfr']))
        if 'cohn'      in p: self.cohn_input.setText(str(p['cohn']))
        if 'coht'      in p: self.coht_input.setText(str(p['coht']))
        if 'cn'        in p: self.cn_input.setText(str(p['cn']))
        if 'ct'        in p: self.ct_input.setText(str(p['ct']))
        if 'b'         in p: self.b_input.setText(str(p['b']))
        if 'w'         in p: self.w_input.setText(str(p['w']))
        if 'stiffness' in p: self.stiffness_input.setText(str(p['stiffness']))
        if 'prestrain' in p: self.prestrain_input.setText(str(p['prestrain']))
        if 'sigc'      in p: self.sigc_input.setText(str(p['sigc']))
        if 'viscosity' in p: self.viscosity_input.setText(str(p['viscosity']))
        if 'Kn'        in p: self.kn_input.setText(str(p['Kn']))

        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.cancel_btn.setVisible(True)

    # ── Rafraîchissement de l'arbre ───────────────────────────────────────────
    def refresh(self):
        self.tree.clear()
        for law in self.controller.get_contact_laws():
            friction_str = f"{law.friction:.3f}" if law.friction is not None else "-"
            props_items  = list(law.properties.items())[:3]
            props_str    = ", ".join(f"{k}={v}" for k, v in props_items)
            if len(law.properties) > 3:
                props_str += "…"
            item = QTreeWidgetItem([
                law.name,
                law.law_type.value,
                friction_str,
                props_str or "-",
            ])
            is_used, _ = self.controller.is_contact_law_used(law.name)
            if is_used:
                item.setForeground(0, QBrush(QColor("green")))
            self.tree.addTopLevelItem(item)