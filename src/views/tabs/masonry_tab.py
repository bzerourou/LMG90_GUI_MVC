# ============================================================================
# MasonryTab — Structures de maçonnerie (persistant, CRUD)
# ============================================================================
"""
Onglet de gestion des structures de maçonnerie.

Reprend la logique de génération de gui/dialogs/masonery_wizard.py mais sous
forme d'onglet persistant (CRUD), suivant le pattern des autres onglets
(avatar_tab, loop_tab). Chaque structure est identifiée par son nom de
groupe (avatar_groups + masonry_patterns partagent la même clé).

Corrections apportées par rapport au wizard d'origine :
  - DOFOperation utilise operation_type=/parameters= (pas operation=/params=)
  - target_value des DOF est un avatar_id (str), jamais une position (int)
  - La copie décalée reconstruit les briques via pre.brick2D/3D + rigidBrick()
    plutôt qu'un copy.deepcopy() sur des objets pylmgc90 natifs (non garanti)
  - La dimension suit celle du projet (pas de re-sélection locale qui
    contournait can_change_dimension())
"""
import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QLabel, QCheckBox, QGroupBox, QScrollArea, QDialog
)
from PyQt6.QtCore import pyqtSignal, Qt

from pylmgc90 import pre

from ...core.models import (
    Avatar, AvatarType, AvatarOrigin, DOFOperation,
)
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController
from ...views.tabs.base_tab import BaseTab
from ...gui.dialogs.quick_material_model import (
    QuickMaterialDialog, QuickModelDialog, make_quick_add_button
)


_PATTERNS = [
    "Standard", "Running Bond", "Stack Bond", "Flemish Bond",
    "Paneresse simple (pylmgc90)", "Paneresse double (pylmgc90)",
]

_PATTERN_INFO = {
    "Standard":
        "Décalage d'une demi-brique entre rangs consécutifs.",
    "Running Bond":
        "Décalage progressif d'un tiers de brique par rang.",
    "Stack Bond":
        "Joints verticaux parfaitement alignés.",
    "Flemish Bond":
        "Alternance panneresse (brique entière) / boutisse (demi-brique).",
    "Paneresse simple (pylmgc90)":
        "pre.paneresse_simple — mur simple épaisseur (3D uniquement).",
    "Paneresse double (pylmgc90)":
        "pre.paneresse_double — mur double épaisseur (3D uniquement).",
}


class MasonryTab(BaseTab):
    """Onglet de gestion des structures de maçonnerie (murs de briques)."""

    masonry_created = pyqtSignal()
    masonry_updated = pyqtSignal()
    masonry_deleted = pyqtSignal()

    def __init__(self, controller: ProjectController):
        super().__init__(controller)
        self.controller = controller
        self.current_edit_group: str | None = None
        self._setup_ui()
        self._connect_signals()

    # =========================================================================
    # Interface
    # =========================================================================

    def _setup_ui(self):
        main_layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        scroll_widget.setLayout(layout)

        # ── Liste des structures existantes ─────────────────────────────────
        layout.addWidget(QLabel("<b>📋 Structures de Maçonnerie</b>"))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nom (groupe)", "Appareil", "Dim.", "Briques"])
        self.tree.setColumnWidth(0, 160)
        self.tree.setColumnWidth(1, 180)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(160)
        layout.addWidget(self.tree)

        tree_btn_layout = QHBoxLayout()
        edit_btn = QPushButton("✏️ Modifier")
        edit_btn.clicked.connect(self._on_edit_from_tree)
        tree_btn_layout.addWidget(edit_btn)

        regen_btn = QPushButton("♻️ Régénérer (mêmes paramètres)")
        regen_btn.clicked.connect(self._on_regenerate_from_tree)
        tree_btn_layout.addWidget(regen_btn)

        delete_btn = QPushButton("🗑️ Supprimer")
        delete_btn.clicked.connect(self._on_delete)
        tree_btn_layout.addWidget(delete_btn)
        tree_btn_layout.addStretch()
        layout.addLayout(tree_btn_layout)

        # ── Matériau / modèle ────────────────────────────────────────────────
        mm_group = QGroupBox("🧱 Matériau et modèle")
        mm_form = QFormLayout()

        self.material_combo = QComboBox()
        mat_row = QHBoxLayout()
        self._btn_add_material = make_quick_add_button("Créer rapidement un nouveau matériau")
        self._btn_add_material.clicked.connect(self._on_quick_add_material)
        mat_row.addWidget(self._btn_add_material)
        mat_row.addWidget(self.material_combo)
        mm_form.addRow("Matériau :", mat_row)

        self.model_combo = QComboBox()
        mod_row = QHBoxLayout()
        self._btn_add_model = make_quick_add_button("Créer rapidement un nouveau modèle")
        self._btn_add_model.clicked.connect(self._on_quick_add_model)
        mod_row.addWidget(self._btn_add_model)
        mod_row.addWidget(self.model_combo)
        mm_form.addRow("Modèle :", mod_row)

        mm_group.setLayout(mm_form)
        layout.addWidget(mm_group)

        # ── Dimensions de la brique ──────────────────────────────────────────
        brick_group = QGroupBox("📏 Dimensions de la brique")
        brick_form = QFormLayout()

        self.brick_name_input = QLineEdit("std")
        self.brick_name_input.setMaxLength(8)
        brick_form.addRow("Nom brique :", self.brick_name_input)

        self.lx_input = self.make_unit_field(default="0.20", unit_key="length")
        brick_form.addRow("lx — longueur :", self.lx_input)

        self.ly_label = QLabel("ly — hauteur (2D) :")
        self.ly_input = self.make_unit_field(default="0.065", unit_key="length")
        brick_form.addRow(self.ly_label, self.ly_input)

        self.lz_label = QLabel("lz — hauteur (3D) :")
        self.lz_input = self.make_unit_field(default="0.065", unit_key="length")
        brick_form.addRow(self.lz_label, self.lz_input)

        brick_group.setLayout(brick_form)
        layout.addWidget(brick_group)

        # ── Appareil ──────────────────────────────────────────────────────────
        layout_group = QGroupBox("🏗️ Appareil et disposition")
        layout_form = QFormLayout()

        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(_PATTERNS)
        self.pattern_combo.currentTextChanged.connect(self._on_pattern_changed)
        layout_form.addRow("Appareil :", self.pattern_combo)

        self.pattern_info_label = QLabel()
        self.pattern_info_label.setWordWrap(True)
        self.pattern_info_label.setStyleSheet(
            "background-color:#f0f0f0; padding:6px; border-radius:4px; font-size:8pt;"
        )
        layout_form.addRow("", self.pattern_info_label)

        self.rows_input = QLineEdit("5")
        layout_form.addRow("Nombre de rangs :", self.rows_input)

        self.cols_input = QLineEdit("8")
        layout_form.addRow("Nombre de colonnes :", self.cols_input)

        self.joint_input = self.make_unit_field(default="0.010", unit_key="length")
        layout_form.addRow("Épaisseur joint :", self.joint_input)

        layout_group.setLayout(layout_form)
        layout.addWidget(layout_group)

        # ── Options paneresse (pylmgc90, 3D uniquement) ─────────────────────
        self.paneresse_group = QGroupBox("Options paneresse (pylmgc90 — 3D uniquement)")
        pan_form = QFormLayout()

        self.disposition_combo = QComboBox()
        self.disposition_combo.addItems(["paneresse", "boutisse", "chant"])
        pan_form.addRow("Disposition :", self.disposition_combo)

        self.first_brick_combo = QComboBox()
        self.first_brick_combo.addItems(["1", "1/2", "1/4", "3/4"])
        pan_form.addRow("Première brique :", self.first_brick_combo)

        self.pan_size_mode_combo = QComboBox()
        self.pan_size_mode_combo.addItems(["Nombre de briques", "Longueur totale (m)"])
        self.pan_size_mode_combo.currentIndexChanged.connect(self._on_pan_size_mode_changed)
        pan_form.addRow("Dimensionnement :", self.pan_size_mode_combo)

        self.pan_length_label = QLabel("Longueur totale :")
        self.pan_length_input = self.make_unit_field(default="3.0", unit_key="length")
        pan_form.addRow(self.pan_length_label, self.pan_length_input)
        self.pan_length_label.setVisible(False)
        self.pan_length_input.setVisible(False)

        self.no_half_check = QCheckBox("Sans demi-briques (buildRigidWallWithoutHalfBricks)")
        pan_form.addRow(self.no_half_check)

        self.paneresse_group.setLayout(pan_form)
        self.paneresse_group.setVisible(False)
        layout.addWidget(self.paneresse_group)

        # ── Position ──────────────────────────────────────────────────────────
        pos_group = QGroupBox("📍 Position (coin inférieur gauche)")
        pos_form = QFormLayout()

        self.offset_x_input = self.make_unit_field(default="0.0", unit_key="length")
        pos_form.addRow("Offset X :", self.offset_x_input)

        self.offset_y_input = self.make_unit_field(default="0.0", unit_key="length")
        pos_form.addRow("Offset Y :", self.offset_y_input)

        self.offset_z_label = QLabel("Offset Z :")
        self.offset_z_input = self.make_unit_field(default="0.0", unit_key="length")
        pos_form.addRow(self.offset_z_label, self.offset_z_input)

        pos_group.setLayout(pos_form)
        layout.addWidget(pos_group)

        # ── Options générales ────────────────────────────────────────────────
        opt_group = QGroupBox("⚙️ Options")
        opt_form = QFormLayout()

        self.color_input = QLineEdit("BLUEx")
        opt_form.addRow("Couleur LMGC90 :", self.color_input)

        self.group_name_input = QLineEdit("mur_briques")
        opt_form.addRow("Nom (groupe, identifiant) :", self.group_name_input)

        self.fast_mode_check = QCheckBox(
            "Mode rapide (regroupe les signaux — recommandé au-delà de ~500 briques)"
        )
        opt_form.addRow("", self.fast_mode_check)

        opt_group.setLayout(opt_form)
        layout.addWidget(opt_group)

        # ── Transformations ───────────────────────────────────────────────────
        tf_group = QGroupBox("🔄 Transformations (optionnel)")
        tf_layout = QVBoxLayout()

        tr_form = QFormLayout()
        self.translate_check = QCheckBox("Translation")
        self.translate_check.toggled.connect(self._on_translate_toggled)
        tr_form.addRow(self.translate_check)
        self.tx_input = self.make_unit_field(default="0.0", unit_key="length")
        self.tx_input.setEnabled(False)
        tr_form.addRow("dx :", self.tx_input)
        self.ty_input = self.make_unit_field(default="0.0", unit_key="length")
        self.ty_input.setEnabled(False)
        tr_form.addRow("dy :", self.ty_input)
        self.tz_label = QLabel("dz :")
        self.tz_input = self.make_unit_field(default="0.0", unit_key="length")
        self.tz_input.setEnabled(False)
        tr_form.addRow(self.tz_label, self.tz_input)
        tf_layout.addLayout(tr_form)

        rot_form = QFormLayout()
        self.rotate_check = QCheckBox("Rotation")
        self.rotate_check.toggled.connect(self._on_rotate_toggled)
        rot_form.addRow(self.rotate_check)
        self.cx_input = self.make_unit_field(default="0.0", unit_key="length")
        self.cx_input.setEnabled(False)
        rot_form.addRow("Centre x :", self.cx_input)
        self.cy_input = self.make_unit_field(default="0.0", unit_key="length")
        self.cy_input.setEnabled(False)
        rot_form.addRow("Centre y :", self.cy_input)
        self.cz_label = QLabel("Centre z :")
        self.cz_input = self.make_unit_field(default="0.0", unit_key="length")
        self.cz_input.setEnabled(False)
        rot_form.addRow(self.cz_label, self.cz_input)
        self.axis_combo = QComboBox()
        self.axis_combo.addItem("Z")
        self.axis_combo.setEnabled(False)
        rot_form.addRow("Axe :", self.axis_combo)
        self.alpha_input = QLineEdit("90.0")
        self.alpha_input.setEnabled(False)
        rot_form.addRow("Angle α (°) :", self.alpha_input)
        tf_layout.addLayout(rot_form)

        copy_form = QFormLayout()
        self.copy_check = QCheckBox("Copie décalée (duplique la structure)")
        self.copy_check.toggled.connect(self._on_copy_toggled)
        copy_form.addRow(self.copy_check)
        self.copy_dx_input = self.make_unit_field(default="0.0", unit_key="length")
        self.copy_dx_input.setEnabled(False)
        copy_form.addRow("Décalage dx :", self.copy_dx_input)
        self.copy_dy_input = self.make_unit_field(default="0.0", unit_key="length")
        self.copy_dy_input.setEnabled(False)
        copy_form.addRow("Décalage dy :", self.copy_dy_input)
        self.copy_dz_label = QLabel("Décalage dz :")
        self.copy_dz_input = self.make_unit_field(default="0.0", unit_key="length")
        self.copy_dz_input.setEnabled(False)
        copy_form.addRow(self.copy_dz_label, self.copy_dz_input)
        tf_layout.addLayout(copy_form)

        tf_group.setLayout(tf_layout)
        layout.addWidget(tf_group)

        # ── Boutons ───────────────────────────────────────────────────────────
        self.help_label = QLabel("Configurez une structure et cliquez sur Créer.")
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.help_label)

        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("✅ Créer la structure")
        self.create_btn.setStyleSheet("font-weight: bold;")
        self.create_btn.clicked.connect(self._on_create)
        btn_layout.addWidget(self.create_btn)

        self.update_btn = QPushButton("💾 Enregistrer et régénérer")
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

        self._on_pattern_changed(self.pattern_combo.currentText())

    def _connect_signals(self):
        self.tree.itemDoubleClicked.connect(self._on_edit_from_tree)

    # =========================================================================
    # Réactions UI
    # =========================================================================

    def _on_pattern_changed(self, pattern: str):
        self.pattern_info_label.setText(_PATTERN_INFO.get(pattern, ""))
        self.paneresse_group.setVisible(
            pattern in ("Paneresse simple (pylmgc90)", "Paneresse double (pylmgc90)")
        )

    def _on_pan_size_mode_changed(self, idx: int):
        use_length = (idx == 1)
        self.pan_length_label.setVisible(use_length)
        self.pan_length_input.setVisible(use_length)

    def _on_translate_toggled(self, v: bool):
        for w in (self.tx_input, self.ty_input, self.tz_input):
            w.setEnabled(v)

    def _on_rotate_toggled(self, v: bool):
        is3d = self.controller.state.dimension == 3
        self.cx_input.setEnabled(v)
        self.cy_input.setEnabled(v)
        self.alpha_input.setEnabled(v)
        self.cz_input.setEnabled(v and is3d)
        self.axis_combo.setEnabled(v and is3d)

    def _on_copy_toggled(self, v: bool):
        for w in (self.copy_dx_input, self.copy_dy_input, self.copy_dz_input):
            w.setEnabled(v)

    def _on_dimension_refresh(self):
        is3d = (self.controller.state.dimension == 3)
        for w in (self.lz_label, self.lz_input, self.offset_z_label, self.offset_z_input,
                  self.tz_label, self.tz_input, self.cz_label, self.cz_input,
                  self.copy_dz_label, self.copy_dz_input):
            w.setVisible(is3d)

        self.ly_label.setText("ly — profondeur (3D) :" if is3d else "ly — hauteur (2D) :")

        self.axis_combo.blockSignals(True)
        self.axis_combo.clear()
        if is3d:
            self.axis_combo.addItems(["X", "Y", "Z"])
        else:
            self.axis_combo.addItem("Z")
        self.axis_combo.blockSignals(False)

        for item_name in ("Paneresse simple (pylmgc90)", "Paneresse double (pylmgc90)"):
            idx = self.pattern_combo.findText(item_name)
            if idx >= 0:
                self.pattern_combo.model().item(idx).setEnabled(is3d)
        if not is3d and self.pattern_combo.currentText().startswith("Paneresse"):
            self.pattern_combo.setCurrentIndex(0)

    def _on_quick_add_material(self):
        dlg = QuickMaterialDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        material = dlg.get_material()
        try:
            self.controller.add_material(material)
        except ValidationError as e:
            QMessageBox.warning(self, "Matériau invalide", str(e))
            return
        self.material_combo.addItem(material.name)
        self.material_combo.setCurrentText(material.name)

    def _on_quick_add_model(self):
        dim = self.controller.state.dimension
        dlg = QuickModelDialog(dimension=dim, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        model = dlg.get_model()
        try:
            self.controller.add_model(model)
        except ValidationError as e:
            QMessageBox.warning(self, "Modèle invalide", str(e))
            return
        self.model_combo.addItem(model.name)
        self.model_combo.setCurrentText(model.name)

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
        menu = QMenu()
        menu.addAction("✏️ Modifier").triggered.connect(self._on_edit_from_tree)
        menu.addAction("♻️ Régénérer (mêmes paramètres)").triggered.connect(self._on_regenerate_from_tree)
        menu.addAction("🗑️ Supprimer").triggered.connect(self._on_delete)
        menu.exec(self.tree.viewport().mapToGlobal(position))

    # =========================================================================
    # Collecte des paramètres du formulaire
    # =========================================================================

    def _collect_params_from_form(self) -> dict:
        dimension = self.controller.state.dimension

        material_name = self.material_combo.currentText().strip()
        model_name = self.model_combo.currentText().strip()
        if not material_name:
            raise ValidationError("Sélectionnez ou créez un matériau.")
        if not model_name:
            raise ValidationError("Sélectionnez ou créez un modèle.")

        brick_name = self.brick_name_input.text().strip() or "std"
        lx = self.eval_float(self.lx_input.text(), default=0.20, field_name="lx")
        ly = self.eval_float(self.ly_input.text(), default=0.065, field_name="ly")
        lz = (
            self.eval_float(self.lz_input.text(), default=0.065, field_name="lz")
            if dimension == 3 else None
        )
        if lx <= 0 or ly <= 0 or (dimension == 3 and lz <= 0):
            raise ValidationError("Les dimensions de la brique doivent être strictement positives.")

        pattern = self.pattern_combo.currentText()
        nb_rows = self.eval_int(self.rows_input.text(), default=5, field_name="Nombre de rangs")
        nb_cols = self.eval_int(self.cols_input.text(), default=8, field_name="Nombre de colonnes")
        joint   = self.eval_float(self.joint_input.text(), default=0.01, field_name="Épaisseur joint")
        if nb_rows <= 0 or nb_cols <= 0:
            raise ValidationError("Le nombre de rangs et de colonnes doit être > 0.")
        if joint < 0:
            raise ValidationError("L'épaisseur de joint doit être >= 0.")

        offset_x = self.eval_float(self.offset_x_input.text(), default=0.0, field_name="Offset X")
        offset_y = self.eval_float(self.offset_y_input.text(), default=0.0, field_name="Offset Y")
        offset_z = (
            self.eval_float(self.offset_z_input.text(), default=0.0, field_name="Offset Z")
            if dimension == 3 else 0.0
        )

        color = self.color_input.text().strip() or "BLUEx"
        group_name = self.group_name_input.text().strip()
        if not group_name:
            raise ValidationError("Le nom du groupe (identifiant de la structure) est requis.")
        if not all(c.isalnum() or c in "_-" for c in group_name):
            raise ValidationError("Le nom du groupe ne doit contenir que lettres, chiffres, '_' ou '-'.")

        params = {
            'material_name': material_name, 'model_name': model_name,
            'brick_name': brick_name, 'lx': lx, 'ly': ly, 'lz': lz,
            'pattern': pattern, 'nb_rows': nb_rows, 'nb_cols': nb_cols, 'joint': joint,
            'offset_x': offset_x, 'offset_y': offset_y, 'offset_z': offset_z,
            'color': color, 'group_name': group_name,
            'fast_mode': self.fast_mode_check.isChecked(),
        }

        if pattern in ("Paneresse simple (pylmgc90)", "Paneresse double (pylmgc90)"):
            if dimension != 3:
                raise ValidationError("Les appareils paneresse (pylmgc90) nécessitent un projet 3D.")
            params['disposition']    = self.disposition_combo.currentText()
            params['first_type']     = self.first_brick_combo.currentText()
            params['pan_use_length'] = (self.pan_size_mode_combo.currentIndex() == 1)
            params['pan_length']     = self.eval_float(
                self.pan_length_input.text(), default=1.0, field_name="Longueur totale"
            )
            params['pan_no_half']    = self.no_half_check.isChecked()

        params['tf_translate'] = self.translate_check.isChecked()
        if params['tf_translate']:
            params['tf_tx'] = self.eval_float(self.tx_input.text(), default=0.0, field_name="dx")
            params['tf_ty'] = self.eval_float(self.ty_input.text(), default=0.0, field_name="dy")
            if dimension == 3:
                params['tf_tz'] = self.eval_float(self.tz_input.text(), default=0.0, field_name="dz")

        params['tf_rotate'] = self.rotate_check.isChecked()
        if params['tf_rotate']:
            params['tf_cx'] = self.eval_float(self.cx_input.text(), default=0.0, field_name="Centre x")
            params['tf_cy'] = self.eval_float(self.cy_input.text(), default=0.0, field_name="Centre y")
            if dimension == 3:
                params['tf_cz']   = self.eval_float(self.cz_input.text(), default=0.0, field_name="Centre z")
                params['tf_axis'] = self.axis_combo.currentText()
            else:
                params['tf_axis'] = 'Z'
            params['tf_alpha_deg'] = self.eval_float(
                self.alpha_input.text(), default=90.0, field_name="Angle"
            )

        params['tf_copy'] = self.copy_check.isChecked()
        if params['tf_copy']:
            params['tf_copy_dx'] = self.eval_float(self.copy_dx_input.text(), default=0.0, field_name="Décalage dx")
            params['tf_copy_dy'] = self.eval_float(self.copy_dy_input.text(), default=0.0, field_name="Décalage dy")
            if dimension == 3:
                params['tf_copy_dz'] = self.eval_float(
                    self.copy_dz_input.text(), default=0.0, field_name="Décalage dz"
                )

        return params

    # =========================================================================
    # Génération (portée depuis masonery_wizard.py, corrigée)
    # =========================================================================

    def _generate_masonry_structure(self, params: dict) -> list[str]:
        """Construit les briques via pylmgc90 et retourne la liste des avatar_id créés."""
        dimension  = self.controller.state.dimension
        mat_name   = params['material_name']
        mod_name   = params['model_name']
        mat_obj    = self.controller._pylmgc_materials.get(mat_name)
        mod_obj    = self.controller._pylmgc_models.get(mod_name)
        if mat_obj is None:
            raise ValidationError(f"Matériau pylmgc90 '{mat_name}' introuvable.")
        if mod_obj is None:
            raise ValidationError(f"Modèle pylmgc90 '{mod_name}' introuvable.")

        lx, ly, lz = params['lx'], params['ly'], params.get('lz')
        brick_name = params['brick_name']
        pattern    = params['pattern']
        nb_rows    = params['nb_rows']
        nb_cols    = params['nb_cols']
        joint      = params['joint']
        offset_x   = params['offset_x']
        offset_y   = params['offset_y']
        offset_z   = params.get('offset_z', 0.0)
        color      = params['color']

        was_batch = self.controller._batch_mode
        if params.get('fast_mode'):
            self.controller._batch_mode = True

        generated_ids: list[str] = []

        def _place_body(body, center, bx, by, bz=None):
            self.controller._bodies_container.addAvatar(body)
            self.controller._pylmgc_bodies.append(body)
            wp = {'l': bx, 'h': by, 'brick_name': brick_name}
            if bz is not None:
                wp['lz'] = bz
            av = Avatar(
                avatar_type=AvatarType.EMPTY_AVATAR,
                center=list(center),
                material_name=mat_name,
                model_name=mod_name,
                color=color,
                origin=AvatarOrigin.MANUAL,
                wall_params=wp,
                contactors=[],
            )
            self.controller.state.avatars.append(av)
            generated_ids.append(av.avatar_id)

        def _place(cx, cy, bx, by):
            center = [cx, cy] if dimension == 2 else [cx, cy, offset_z]
            if dimension == 2:
                b = pre.brick2D(brick_name, bx, by)
            else:
                b = pre.brick3D(brick_name, bx, by, lz)
            body = b.rigidBrick(center=center, model=mod_obj, material=mat_obj, color=color)
            _place_body(body, center, bx, by, lz)

        try:
            if pattern == "Standard":
                for row in range(nb_rows):
                    row_offset = (lx / 2.0) if (row % 2 == 1) else 0.0
                    for col in range(nb_cols):
                        cx = offset_x + col * (lx + joint) + row_offset + lx / 2.0
                        cy = offset_y + row * (ly + joint) + ly / 2.0
                        _place(cx, cy, lx, ly)

            elif pattern == "Running Bond":
                for row in range(nb_rows):
                    row_offset = (row % 3) * (lx / 3.0)
                    for col in range(nb_cols):
                        cx = offset_x + col * (lx + joint) + row_offset + lx / 2.0
                        cy = offset_y + row * (ly + joint) + ly / 2.0
                        _place(cx, cy, lx, ly)

            elif pattern == "Stack Bond":
                for row in range(nb_rows):
                    for col in range(nb_cols):
                        cx = offset_x + col * (lx + joint) + lx / 2.0
                        cy = offset_y + row * (ly + joint) + ly / 2.0
                        _place(cx, cy, lx, ly)

            elif pattern == "Flemish Bond":
                for row in range(nb_rows):
                    x_cursor = offset_x
                    for col in range(nb_cols):
                        brick_lx = lx if (row + col) % 2 == 0 else lx / 2.0
                        cx = x_cursor + brick_lx / 2.0
                        cy = offset_y + row * (ly + joint) + ly / 2.0
                        _place(cx, cy, brick_lx, ly)
                        x_cursor += brick_lx + joint

            elif pattern in ("Paneresse simple (pylmgc90)", "Paneresse double (pylmgc90)"):
                # Validé 3D-only en amont (_collect_params_from_form)
                disposition    = params['disposition']
                first_type     = params['first_type']
                pan_use_length = params.get('pan_use_length', False)
                pan_length     = params.get('pan_length', 1.0)
                pan_no_half    = params.get('pan_no_half', False)

                brick_ref_wall = pre.brick3D(brick_name, lx, ly, lz)
                if "double" in pattern:
                    wall = pre.paneresse_double(brick_ref=brick_ref_wall, disposition=disposition)
                else:
                    wall = pre.paneresse_simple(brick_ref=brick_ref_wall, disposition=disposition)

                wall.setNumberOfRows(nb_rows)
                wall.setJointThicknessBetweenRows(joint)
                wall.computeHeight()

                if pan_use_length:
                    wall.setFirstRowByLength(
                        first_brick_type=first_type, length=pan_length, joint_thickness=joint
                    )
                else:
                    wall.setFirstRowByNumberOfBricks(
                        first_brick_type=first_type, nb_bricks=nb_cols, joint_thickness=joint
                    )

                origin = [offset_x, offset_y, offset_z]
                build_fn = (
                    wall.buildRigidWallWithoutHalfBricks if pan_no_half
                    else wall.buildRigidWall
                )
                bodies_container = build_fn(
                    origin=origin, model=mod_obj, material=mat_obj, colors=[color, color]
                )
                for body in bodies_container:
                    center = list(body.nodes[1].coor)
                    _place_body(body, center, lx, ly, lz)

            else:
                raise ValidationError(f"Appareil inconnu : '{pattern}'")
        finally:
            self.controller._batch_mode = was_batch

        return generated_ids

    def _apply_transforms(self, avatar_ids: list[str], params: dict) -> None:
        """
        Applique translation/rotation via DOFOperation.
        target_value = avatar_id (str), operation_type/parameters (pas
        operation/params) — corrige les bugs identifiés dans masonery_wizard.py.
        """
        dimension = self.controller.state.dimension

        if params.get('tf_translate'):
            p = {'dx': params.get('tf_tx', 0.0), 'dy': params.get('tf_ty', 0.0)}
            if dimension == 3:
                p['dz'] = params.get('tf_tz', 0.0)
            for aid in avatar_ids:
                self.controller.add_dof_operation(DOFOperation(
                    operation_type='translate',
                    target_type='avatar',
                    target_value=aid,
                    parameters=dict(p),
                ))

        if params.get('tf_rotate'):
            alpha = math.radians(params.get('tf_alpha_deg', 0.0))
            axis_map = {'X': [1., 0., 0.], 'Y': [0., 1., 0.], 'Z': [0., 0., 1.]}
            axis = axis_map.get(params.get('tf_axis', 'Z'), [0., 0., 1.])
            center = (
                [params.get('tf_cx', 0.0), params.get('tf_cy', 0.0), params.get('tf_cz', 0.0)]
                if dimension == 3 else
                [params.get('tf_cx', 0.0), params.get('tf_cy', 0.0)]
            )
            for aid in avatar_ids:
                self.controller.add_dof_operation(DOFOperation(
                    operation_type='rotate',
                    target_type='avatar',
                    target_value=aid,
                    parameters={
                        'description': 'axis',
                        'center': list(center),
                        'axis': list(axis),
                        'alpha': alpha,
                    },
                ))

    def _apply_copy(self, avatar_ids: list[str], params: dict) -> list[str]:
        """
        Crée une copie décalée en reconstruisant chaque brique explicitement
        via pre.brick2D/3D + rigidBrick() — pas de copy.deepcopy() sur des
        objets pylmgc90 natifs (non garanti, cf. correctif appliqué).
        Retourne les avatar_id des nouvelles briques.
        """
        if not params.get('tf_copy'):
            return []
        dimension = self.controller.state.dimension
        dx = params.get('tf_copy_dx', 0.0)
        dy = params.get('tf_copy_dy', 0.0)
        dz = params.get('tf_copy_dz', 0.0)

        mat_name = params['material_name']
        mod_name = params['model_name']
        color    = params['color']
        mat_obj  = self.controller._pylmgc_materials.get(mat_name)
        mod_obj  = self.controller._pylmgc_models.get(mod_name)

        id_to_idx = {av.avatar_id: i for i, av in enumerate(self.controller.state.avatars)}
        new_ids: list[str] = []

        for aid in avatar_ids:
            idx = id_to_idx.get(aid)
            if idx is None:
                continue
            src = self.controller.state.avatars[idx]
            src_center = list(src.center)
            wp = src.wall_params or {}
            b_lx = wp.get('l', 0.2)
            b_ly = wp.get('h', 0.1)
            b_lz = wp.get('lz')
            b_name = wp.get('brick_name', 'std')

            if dimension == 3:
                new_center = [src_center[0] + dx, src_center[1] + dy, src_center[2] + dz]
                b = pre.brick3D(b_name, b_lx, b_ly, b_lz or b_ly).rigidBrick(
                    center=new_center, model=mod_obj, material=mat_obj, color=color
                )
            else:
                new_center = [src_center[0] + dx, src_center[1] + dy]
                b = pre.brick2D(b_name, b_lx, b_ly).rigidBrick(
                    center=new_center, model=mod_obj, material=mat_obj, color=color
                )

            self.controller._bodies_container.addAvatar(b)
            self.controller._pylmgc_bodies.append(b)

            wp_new = {'l': b_lx, 'h': b_ly, 'brick_name': b_name, 'copy': True}
            if dimension == 3:
                wp_new['lz'] = b_lz

            new_av = Avatar(
                avatar_type=AvatarType.EMPTY_AVATAR,
                center=new_center,
                material_name=mat_name,
                model_name=mod_name,
                color=color,
                origin=AvatarOrigin.MANUAL,
                wall_params=wp_new,
                contactors=[],
            )
            self.controller.state.avatars.append(new_av)
            new_ids.append(new_av.avatar_id)

        return new_ids

    # =========================================================================
    # Suppression propre (ordre décroissant d'index — jamais de décalage)
    # =========================================================================

    def _delete_group_avatars(self, group_name: str) -> None:
        avatar_ids = list(self.controller.state.avatar_groups.get(group_name, []))
        id_to_idx = {av.avatar_id: i for i, av in enumerate(self.controller.state.avatars)}
        indices = sorted(
            (id_to_idx[aid] for aid in avatar_ids if aid in id_to_idx),
            reverse=True,
        )
        failed = [idx for idx in indices if not self.controller.remove_avatar(idx)]
        self.controller.state.avatar_groups.pop(group_name, None)
        if failed:
            QMessageBox.warning(
                self, "Suppression incomplète",
                f"⚠️ Certaines briques n'ont pas pu être supprimées : {len(failed)}"
            )

    # =========================================================================
    # Actions CRUD
    # =========================================================================

    def _on_create(self):
        try:
            params = self._collect_params_from_form()
            group_name = params['group_name']

            if self.controller.state.avatar_groups.get(group_name):
                raise ValidationError(
                    f"Le groupe '{group_name}' existe déjà et n'est pas vide. "
                    f"Choisissez un autre nom, ou modifiez la structure "
                    f"existante depuis la liste."
                )

            avatar_ids = self._generate_masonry_structure(params)
            if not avatar_ids:
                raise ValidationError("Aucune brique n'a été générée — vérifiez les paramètres.")

            self.controller.state.avatar_groups.setdefault(group_name, []).extend(avatar_ids)

            mp = dict(params)
            mp.pop('group_name', None)
            mp['dim'] = self.controller.state.dimension
            mp['mat'] = params['material_name']
            mp['mod'] = params['model_name']
            self.controller.state.masonry_patterns[group_name] = mp

            if params['tf_translate'] or params['tf_rotate']:
                self._apply_transforms(avatar_ids, params)

            if params['tf_copy']:
                copy_ids = self._apply_copy(avatar_ids, params)
                if copy_ids:
                    self.controller.state.avatar_groups.setdefault(
                        f"{group_name}_copie", []
                    ).extend(copy_ids)

            self.controller.state_changed.emit()
            self.masonry_created.emit()
            self.refresh()
            QMessageBox.information(
                self, "Succès",
                f"✅ Structure '{group_name}' créée : {len(avatar_ids)} brique(s)."
            )
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Erreur", f"Génération échouée :\n{e}\n\n{traceback.format_exc()}")

    def _on_update(self):
        if self.current_edit_group is None:
            return
        try:
            params = self._collect_params_from_form()
            group_name = self.current_edit_group  # figé pendant l'édition

            self._delete_group_avatars(group_name)

            avatar_ids = self._generate_masonry_structure(params)
            if not avatar_ids:
                raise ValidationError("Aucune brique n'a été générée — vérifiez les paramètres.")

            self.controller.state.avatar_groups[group_name] = list(avatar_ids)

            mp = dict(params)
            mp.pop('group_name', None)
            mp['dim'] = self.controller.state.dimension
            mp['mat'] = params['material_name']
            mp['mod'] = params['model_name']
            self.controller.state.masonry_patterns[group_name] = mp

            if params['tf_translate'] or params['tf_rotate']:
                self._apply_transforms(avatar_ids, params)

            if params['tf_copy']:
                copy_ids = self._apply_copy(avatar_ids, params)
                if copy_ids:
                    self.controller.state.avatar_groups.setdefault(
                        f"{group_name}_copie", []
                    ).extend(copy_ids)

            self.controller.state_changed.emit()
            self.masonry_updated.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"✅ Structure '{group_name}' régénérée.")
            self._on_cancel_edit()
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Erreur", f"Modification échouée :\n{e}\n\n{traceback.format_exc()}")

    def _on_regenerate_from_tree(self):
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une structure à régénérer.")
            return
        self._regenerate_group(selected.data(0, Qt.ItemDataRole.UserRole))

    def _regenerate_group(self, group_name: str):
        mp = self.controller.state.masonry_patterns.get(group_name)
        if mp is None:
            QMessageBox.warning(self, "Introuvable", f"Structure '{group_name}' introuvable.")
            return
        try:
            params = dict(mp)
            params['group_name']    = group_name
            params.setdefault('material_name', mp.get('mat'))
            params.setdefault('model_name', mp.get('mod'))

            self._delete_group_avatars(group_name)
            avatar_ids = self._generate_masonry_structure(params)
            if not avatar_ids:
                raise ValidationError("Aucune brique n'a été régénérée.")
            self.controller.state.avatar_groups[group_name] = list(avatar_ids)

            if params.get('tf_translate') or params.get('tf_rotate'):
                self._apply_transforms(avatar_ids, params)
            if params.get('tf_copy'):
                copy_ids = self._apply_copy(avatar_ids, params)
                if copy_ids:
                    self.controller.state.avatar_groups.setdefault(
                        f"{group_name}_copie", []
                    ).extend(copy_ids)

            self.controller.state_changed.emit()
            self.masonry_updated.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"♻️ Structure '{group_name}' régénérée.")
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Erreur", f"Régénération échouée :\n{e}\n\n{traceback.format_exc()}")

    def _on_edit_from_tree(self):
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une structure à modifier.")
            return
        self.load_for_edit(selected.data(0, Qt.ItemDataRole.UserRole))

    def _on_delete(self):
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une structure à supprimer.")
            return
        group_name = selected.data(0, Qt.ItemDataRole.UserRole)
        if not group_name:
            return

        nb = len(self.controller.state.avatar_groups.get(group_name, []))
        reply = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer la structure '{group_name}' ({nb} brique(s)) ?\n"
            f"Cette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._delete_group_avatars(group_name)
        self.controller.state.masonry_patterns.pop(group_name, None)

        copy_group = f"{group_name}_copie"
        if copy_group in self.controller.state.avatar_groups:
            self._delete_group_avatars(copy_group)

        self.controller.state_changed.emit()
        self.masonry_deleted.emit()
        self.refresh()
        if self.current_edit_group == group_name:
            self._on_cancel_edit()
        QMessageBox.information(self, "Succès", f"✅ Structure '{group_name}' supprimée.")

    def load_for_edit(self, group_name: str, mp: dict = None):
        if mp is None:
            mp = self.controller.state.masonry_patterns.get(group_name)
        if mp is None:
            QMessageBox.warning(self, "Introuvable", f"Structure '{group_name}' introuvable.")
            return

        self.current_edit_group = group_name

        self.material_combo.setCurrentText(mp.get('mat', mp.get('material_name', '')))
        self.model_combo.setCurrentText(mp.get('mod', mp.get('model_name', '')))
        self.brick_name_input.setText(mp.get('brick_name', 'std'))
        self.lx_input.setText(str(mp.get('lx', 0.2)))
        self.ly_input.setText(str(mp.get('ly', 0.065)))
        if mp.get('lz') is not None:
            self.lz_input.setText(str(mp.get('lz')))
        self.pattern_combo.setCurrentText(mp.get('pattern', 'Standard'))
        self.rows_input.setText(str(mp.get('nb_rows', 5)))
        self.cols_input.setText(str(mp.get('nb_cols', 8)))
        self.joint_input.setText(str(mp.get('joint', 0.01)))
        self.offset_x_input.setText(str(mp.get('offset_x', 0.0)))
        self.offset_y_input.setText(str(mp.get('offset_y', 0.0)))
        if mp.get('offset_z') is not None:
            self.offset_z_input.setText(str(mp.get('offset_z', 0.0)))
        self.color_input.setText(mp.get('color', 'BLUEx'))
        self.group_name_input.setText(group_name)
        self.group_name_input.setEnabled(False)
        self.fast_mode_check.setChecked(bool(mp.get('fast_mode', False)))

        if mp.get('disposition'):
            self.disposition_combo.setCurrentText(mp['disposition'])
        if mp.get('first_type'):
            self.first_brick_combo.setCurrentText(mp['first_type'])
        self.pan_size_mode_combo.setCurrentIndex(1 if mp.get('pan_use_length') else 0)
        if mp.get('pan_length') is not None:
            self.pan_length_input.setText(str(mp['pan_length']))
        self.no_half_check.setChecked(bool(mp.get('pan_no_half', False)))

        self.translate_check.setChecked(bool(mp.get('tf_translate', False)))
        self.tx_input.setText(str(mp.get('tf_tx', 0.0)))
        self.ty_input.setText(str(mp.get('tf_ty', 0.0)))
        self.tz_input.setText(str(mp.get('tf_tz', 0.0)))

        self.rotate_check.setChecked(bool(mp.get('tf_rotate', False)))
        self.cx_input.setText(str(mp.get('tf_cx', 0.0)))
        self.cy_input.setText(str(mp.get('tf_cy', 0.0)))
        self.cz_input.setText(str(mp.get('tf_cz', 0.0)))
        if mp.get('tf_axis'):
            self.axis_combo.setCurrentText(mp['tf_axis'])
        self.alpha_input.setText(str(mp.get('tf_alpha_deg', 90.0)))

        self.copy_check.setChecked(bool(mp.get('tf_copy', False)))
        self.copy_dx_input.setText(str(mp.get('tf_copy_dx', 0.0)))
        self.copy_dy_input.setText(str(mp.get('tf_copy_dy', 0.0)))
        self.copy_dz_input.setText(str(mp.get('tf_copy_dz', 0.0)))

        self._on_pattern_changed(self.pattern_combo.currentText())
        self._on_dimension_refresh()

        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.cancel_btn.setVisible(True)
        self.help_label.setText(f"🔧 Mode édition : {group_name}")
        self.help_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 5px;")

    def _on_cancel_edit(self):
        self.current_edit_group = None
        self.group_name_input.setEnabled(True)
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.help_label.setText("Configurez une structure et cliquez sur Créer.")
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")

    def _clear_form(self):
        if self.current_edit_group is not None : 
            self._on_cancel_edit()
            return
        self.brick_name_input.setText("std")
        self.lx_input.setText("0.20")
        self.ly_input.setText("0.065")
        self.lz_input.setText("0.065")
        self.pattern_combo.setCurrentIndex(0)
        self.rows_input.setText("5")
        self.cols_input.setText("8")
        self.joint_input.setText("0.010")
        self.offset_x_input.setText("0.0")
        self.offset_y_input.setText("0.0")
        self.offset_z_input.setText("0.0")
        self.color_input.setText("BLUEx")
        self.group_name_input.clear()
        self.fast_mode_check.setChecked(False)
        self.disposition_combo.setCurrentIndex(0)
        self.first_brick_combo.setCurrentIndex(0)
        self.pan_size_mode_combo.setCurrentIndex(0)
        self.pan_length_input.setText("3.0")
        self.no_half_check.setChecked(False)
        self.translate_check.setChecked(False)
        self.tx_input.setText("0.0")
        self.ty_input.setText("0.0")
        self.tz_input.setText("0.0")
        self.rotate_check.setChecked(False)
        self.cx_input.setText("0.0")
        self.cy_input.setText("0.0")
        self.cz_input.setText("0.0")
        self.alpha_input.setText("90.0")
        self.copy_check.setChecked(False)
        self.copy_dx_input.setText("0.0")
        self.copy_dy_input.setText("0.0")
        self.copy_dz_input.setText("0.0")

    # =========================================================================
    # Rafraîchissement
    # =========================================================================

    def refresh(self):
        cur_mat = self.material_combo.currentText()
        cur_mod = self.model_combo.currentText()
        self.material_combo.blockSignals(True)
        self.model_combo.blockSignals(True)
        self.material_combo.clear()
        for m in self.controller.get_materials():
            self.material_combo.addItem(m.name)
        self.model_combo.clear()
        for m in self.controller.get_models():
            self.model_combo.addItem(m.name)
        idx = self.material_combo.findText(cur_mat)
        if idx >= 0:
            self.material_combo.setCurrentIndex(idx)
        idx = self.model_combo.findText(cur_mod)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        self.material_combo.blockSignals(False)
        self.model_combo.blockSignals(False)

        self._on_dimension_refresh()

        self.tree.clear()
        masonry_patterns = getattr(self.controller.state, 'masonry_patterns', {}) or {}
        groups = self.controller.state.avatar_groups
        for group_name, mp in masonry_patterns.items():
            nb = len(groups.get(group_name, []))
            item = QTreeWidgetItem([
                group_name,
                mp.get('pattern', '—'),
                f"{mp.get('dim', '?')}D",
                str(nb),
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, group_name)
            self.tree.addTopLevelItem(item)

        self.refresh_units()