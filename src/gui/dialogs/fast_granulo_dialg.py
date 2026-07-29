# ============================================================================
# GranuloFastDialog — Interface haute performance pour dépôts granulométriques
# ============================================================================
"""
Dialog  pour générer des avatars rapidement.
Utilise GranuloFastEngine (numpy pur) dans un QThread dédié.
N'interagit avec controller qu'une seule fois à la fin (batch unique).
"""

from PyQt6.QtWidgets import (
    QDialog, QScrollArea, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QProgressBar,
    QGroupBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QDialogButtonBox, QWidget, QFrame, QSizePolicy,
    QMessageBox, QFileDialog, QToolButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

from pathlib import Path

from ...utils.fast_granulo_engin import GranuloFastEngine, GranuloFileWriter, GranuloStateIntegrator
from ...controllers.project_controller import ProjectController
from ...core.models import Material, MaterialType, Model
from ...core.validators import ValidationError
from .quick_material_model import (
    QuickModelDialog, QuickMaterialDialog, make_quick_add_button
)



def _dbl(value: float, minimum: float = 0., maximum: float = 1e6,
         decimals: int = 3, step: float = 1.0) -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(minimum, maximum)
    sb.setDecimals(decimals)
    sb.setSingleStep(step)
    sb.setValue(value)
    return sb


# ─────────────────────────────────────────────────────────────────────────────
#  Thread de calcul
# ─────────────────────────────────────────────────────────────────────────────

class FastGranuloThread(QThread):
    """Thread dédié au calcul — UI ne se fige jamais"""

    progress  = pyqtSignal(int, int, str)   # current, total, message
    finished  = pyqtSignal(object)           # FastGranuloResult
    error     = pyqtSignal(str)

    def __init__(self, engine: GranuloFastEngine, params: dict):
        super().__init__()
        self.engine = engine
        self.params = params
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        try:
            def cb(cur, tot, msg):
                if self._abort:
                    raise InterruptedError("Annulé par l'utilisateur")
                self.progress.emit(cur, tot, msg)

            result = self.engine.generate(
                progress_callback=cb,
                **self.params
            )
            if not self._abort:
                self.finished.emit(result)
        except InterruptedError:
            self.error.emit("Génération annulée.")
        except Exception as e:
            self.error.emit(str(e))


# #######################################
#  Dialog principal
# #######################################

class GranuloFastDialog(QDialog):
    """
    Dialog haute performance pour la génération de dépôts granulométriques.

    Indépendant du pipeline principal :
      - Calcul dans un thread (numpy pur)
      - Écriture DATBOX optionnelle
      - Intégration controller.state en batch unique

    """

    granulo_generated = pyqtSignal()

    def __init__(self, controller: ProjectController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.engine     = GranuloFastEngine()
        self.writer     = GranuloFileWriter()
        self.integrator = GranuloStateIntegrator()
        self._thread    = None
        self._result    = None

        self.setWindowTitle("⚡ Génération Granulométrique Rapide")
        self.setMinimumWidth(620)
        self.setModal(True)

        self._setup_ui()
        self._populate_combos()

    # ── Interface ────────────────────────────────────────────────────────────

    def _setup_ui(self):
        # ────────────────────────────────────────────────────────────────────
        main_layout = QVBoxLayout(self)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(15, 15, 15, 15)

        # ── Créer la QScrollArea ────────────────────────────────────────────
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(scroll_content)
        self.scroll_area.setWidgetResizable(True)  # Important : permet le redimensionnement
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: none; background: #f5f5f5; }"
        )

        # ── En-tête ─────────────────────────────────────────────────────────
        header = QLabel("⚡ Génération très rapide — jusqu'à 5 000+ particules")
        header.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #1565C0;"
            "padding: 8px; background: #E3F2FD; border-radius: 5px;"
        )
        scroll_layout.addWidget(header)

        # ── Ligne 1 : Propriétés physiques ──────────────────────────────────
        phys_group = QGroupBox("Propriétés physiques")
        phys_form  = QFormLayout(phys_group)

        self.material_combo = QComboBox()
        mat_row = QHBoxLayout()
        self._btn_add_material = make_quick_add_button("Créer rapidement un nouveau matériau")
        self._btn_add_material.clicked.connect(self._on_quick_add_material)
        mat_row.addWidget(self._btn_add_material)
        mat_row.addWidget(self.material_combo)
        phys_form.addRow("Matériau :", mat_row)

        self.model_combo = QComboBox()
        mod_row = QHBoxLayout()
        self._btn_add_model = make_quick_add_button("Créer rapidement un nouveau modèle")
        self._btn_add_model.clicked.connect(self._on_quick_add_model)
        mod_row.addWidget(self._btn_add_model)
        mod_row.addWidget(self.model_combo)
        phys_form.addRow("Modèle :", mod_row)

        dim = self.controller.state.dimension
        self.avatar_type = "rigidDisk" if dim == 2 else "rigidSphere"
        av_label = QLabel(self.avatar_type)
        av_label.setStyleSheet("color: #555;")
        phys_form.addRow("Type d'avatar :", av_label)

        self.color_input = QLineEdit("BLUEx")
        phys_form.addRow("Couleur :", self.color_input)

        scroll_layout.addWidget(phys_group)

        # ── Ligne 2 : Distribution ──────────────────────────────────────────
        dist_group = QGroupBox("Distribution des rayons")
        dist_form  = QFormLayout(dist_group)

        self.nb_spin = QSpinBox()
        self.nb_spin.setRange(1, 50000)
        self.nb_spin.setValue(500)
        self.nb_spin.setSingleStep(100)
        self.nb_spin.setSuffix(" particules")
        dist_form.addRow("Nombre :", self.nb_spin)

        self.rmin_spin = QDoubleSpinBox()
        self.rmin_spin.setRange(0.001, 100.0)
        self.rmin_spin.setValue(0.05)
        self.rmin_spin.setDecimals(4)
        self.rmin_spin.setSingleStep(0.01)
        dist_form.addRow("Rayon min :", self.rmin_spin)

        self.rmax_spin = QDoubleSpinBox()
        self.rmax_spin.setRange(0.001, 100.0)
        self.rmax_spin.setValue(0.15)
        self.rmax_spin.setDecimals(4)
        self.rmax_spin.setSingleStep(0.01)
        dist_form.addRow("Rayon max :", self.rmax_spin)

        seed_row = QHBoxLayout()
        self.seed_check = QCheckBox("Seed fixe :")
        self.seed_spin  = QSpinBox()
        self.seed_spin.setRange(0, 999999)
        self.seed_spin.setValue(42)
        self.seed_spin.setEnabled(False)
        self.seed_check.toggled.connect(self.seed_spin.setEnabled)
        seed_row.addWidget(self.seed_check)
        seed_row.addWidget(self.seed_spin)
        seed_row.addStretch()
        dist_form.addRow("", seed_row)

        scroll_layout.addWidget(dist_group)

        # ── Ligne 3 : Conteneur ─────────────────────────────────────────────
        cont_group = QGroupBox("Géométrie du conteneur")
        cont_vbox  = QVBoxLayout(cont_group)

        cont_form = QFormLayout()
        self.container_combo = QComboBox()
        dim = self.controller.state.dimension
        if dim == 2:
            self.container_combo.addItems(["Box2D", "Disk2D", "Couette2D", "Drum2D"])
        else:
            self.container_combo.addItems(["Box3D", "Sphere3D", "Cylinder3D"])
        self.container_combo.currentTextChanged.connect(self._update_container_params)
        cont_form.addRow("Type :", self.container_combo)
        cont_vbox.addLayout(cont_form)

        self._param_widget = QWidget()
        self._param_form   = QFormLayout(self._param_widget)
        cont_vbox.addWidget(self._param_widget)

        # Champs de paramètres (affichés selon le type)
        self._lx = QDoubleSpinBox(); self._lx.setRange(0.1, 1000); self._lx.setValue(4.0); self._lx.setSuffix(" m")
        self._ly = QDoubleSpinBox(); self._ly.setRange(0.1, 1000); self._ly.setValue(4.0); self._ly.setSuffix(" m")
        self._lz = QDoubleSpinBox(); self._lz.setRange(0.1, 1000); self._lz.setValue(4.0); self._lz.setSuffix(" m")
        self._r  = QDoubleSpinBox(); self._r.setRange(0.1, 1000);  self._r.setValue(2.0);  self._r.setSuffix(" m")
        self._rint = QDoubleSpinBox(); self._rint.setRange(0.1, 1000); self._rint.setValue(1.5); self._rint.setSuffix(" m")
        self._rext = QDoubleSpinBox(); self._rext.setRange(0.1, 1000); self._rext.setValue(3.0); self._rext.setSuffix(" m")

        # Labels associés (gardés en attribut pour pouvoir les cacher aussi)
        self._lbl_lx   = QLabel("Largeur lx :")
        self._lbl_ly   = QLabel("Hauteur ly :")
        self._lbl_lz   = QLabel("Profondeur lz :")
        self._lbl_r    = QLabel("Rayon r :")
        self._lbl_rint = QLabel("Rayon interne :")
        self._lbl_rext = QLabel("Rayon externe :")

        # Ajout une seule fois dans le form — on ne supprime jamais
        self._param_form.addRow(self._lbl_lx,   self._lx)
        self._param_form.addRow(self._lbl_ly,   self._ly)
        self._param_form.addRow(self._lbl_lz,   self._lz)
        self._param_form.addRow(self._lbl_r,    self._r)
        self._param_form.addRow(self._lbl_rint, self._rint)
        self._param_form.addRow(self._lbl_rext, self._rext)
        scroll_layout.addWidget(cont_group)
        self._update_container_params(self.container_combo.currentText())

        # ── Ligne 4 : Groupe & sortie ───────────────────────────────────────
        out_group = QGroupBox("Groupe & export fichier")
        out_form  = QFormLayout(out_group)

        self.group_name_input = QLineEdit("depot_fast")
        out_form.addRow("Nom du groupe :", self.group_name_input)

        file_row = QHBoxLayout()
        self.write_file_check = QCheckBox("Écrire DATBOX/BODIES.DAT")
        self.write_file_check.setChecked(False)
        self.write_file_check.toggled.connect(self._on_write_file_toggled)
        file_row.addWidget(self.write_file_check)
        out_form.addRow("", file_row)

        dir_row = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("Dossier de sortie DATBOX...")
        self.output_dir_input.setEnabled(False)
        browse_btn = QPushButton("📂")
        browse_btn.setMaximumWidth(36)
        browse_btn.clicked.connect(self._browse_output_dir)
        browse_btn.setEnabled(False)
        self._browse_btn = browse_btn
        dir_row.addWidget(self.output_dir_input)
        dir_row.addWidget(browse_btn)
        out_form.addRow("Dossier :", dir_row)

        scroll_layout.addWidget(out_group)

        # ── Progression ─────────────────────────────────────────────────────
        prog_group = QGroupBox("Progression")
        prog_vbox  = QVBoxLayout(prog_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #bbb; border-radius: 4px; height: 20px; }"
            "QProgressBar::chunk { background: #1976D2; border-radius: 3px; }"
        )
        prog_vbox.addWidget(self.progress_bar)

        self.status_label = QLabel("Prêt.")
        self.status_label.setStyleSheet("color: #555; font-size: 10px; padding: 2px;")
        prog_vbox.addWidget(self.status_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(90)
        self.log_text.setStyleSheet(
            "background: #1a1a2e; color: #00E676; font-family: monospace; font-size: 10px;"
        )
        prog_vbox.addWidget(self.log_text)

        scroll_layout.addWidget(prog_group)

        # ── Boutons ─────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self.gen_btn = QPushButton("⚡ Générer")
        self.gen_btn.setStyleSheet(
            "QPushButton { background: #1565C0; color: white; font-weight: bold;"
            "padding: 10px 24px; border-radius: 5px; font-size: 12px; }"
            "QPushButton:hover { background: #1976D2; }"
            "QPushButton:disabled { background: #bbb; }"
        )
        self.gen_btn.clicked.connect(self._on_generate)

        self.cancel_btn = QPushButton("⏹ Annuler")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("padding: 10px 16px;")
        self.cancel_btn.clicked.connect(self._on_cancel)

        self.close_btn = QPushButton("Fermer")
        self.close_btn.setStyleSheet("padding: 10px 16px;")
        self.close_btn.clicked.connect(self.accept)

        btn_row.addWidget(self.gen_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.close_btn)
        scroll_layout.addLayout(btn_row)

        # ── Ajouter un espacement final ─────────────────────────────────────
        scroll_layout.addStretch()

        # ── Définir la QScrollArea comme layout principal ───────────────────

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.scroll_area)

    def _populate_combos(self):
        self.material_combo.clear()
        for m in self.controller.get_materials():
            self.material_combo.addItem(m.name)

        self.model_combo.clear()
        for m in self.controller.get_models():
            self.model_combo.addItem(m.name)

    def _on_quick_add_material(self):
        """Ouvre une boîte de dialogue pour créer rapidement un matériau simple."""
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
        """Ouvre une boîte de dialogue pour créer rapidement un modèle simple."""
        dim = getattr(self.controller.state, 'dimension', 3)
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

    def _update_container_params(self, container_type):
        """Affiche/cache les champs selon le conteneur — sans jamais détruire les widgets."""
        all_widgets = [
            self._lbl_lx,   self._lx,
            self._lbl_ly,   self._ly,
            self._lbl_lz,   self._lz,
            self._lbl_r,    self._r,
            self._lbl_rint, self._rint,
            self._lbl_rext, self._rext,
        ]
        for w in all_widgets:
            w.setVisible(False)

        if container_type == "Box2D":
            self._lbl_lx.setVisible(True); self._lx.setVisible(True)
            self._lbl_ly.setVisible(True); self._ly.setVisible(True)

        elif container_type in ("Disk2D", "Drum2D", "Sphere3D", "Cylinder3D"):
            self._lbl_r.setVisible(True); self._r.setVisible(True)

        elif container_type == "Couette2D":
            self._lbl_rint.setVisible(True); self._rint.setVisible(True)
            self._lbl_rext.setVisible(True); self._rext.setVisible(True)

        elif container_type == "Box3D":
            self._lbl_lx.setVisible(True); self._lx.setVisible(True)
            self._lbl_ly.setVisible(True); self._ly.setVisible(True)
            self._lbl_lz.setVisible(True); self._lz.setVisible(True)

    def _on_write_file_toggled(self, checked):
        self.output_dir_input.setEnabled(checked)
        self._browse_btn.setEnabled(checked)

    def _browse_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Dossier de sortie DATBOX")
        if d:
            self.output_dir_input.setText(d)

    # ── Génération ───────────────────────────────────────────────────────────

    def _on_generate(self):
        # Validation
        if not self.material_combo.currentText():
            QMessageBox.warning(self, "Erreur", "Aucun matériau disponible.")
            return
        if not self.model_combo.currentText():
            QMessageBox.warning(self, "Erreur", "Aucun modèle disponible.")
            return
        if self.rmin_spin.value() >= self.rmax_spin.value():
            QMessageBox.warning(self, "Erreur", "Rayon min doit être < rayon max.")
            return
        if not self.group_name_input.text().strip():
            QMessageBox.warning(self, "Erreur", "Entrez un nom de groupe.")
            return
        if self.write_file_check.isChecked() and not self.output_dir_input.text().strip():
            QMessageBox.warning(self, "Erreur", "Sélectionnez un dossier de sortie.")
            return

        container_type = self.container_combo.currentText()
        params = self._get_container_params(container_type)

        gen_params = dict(
            nb_particles    = self.nb_spin.value(),
            radius_min      = self.rmin_spin.value(),
            radius_max      = self.rmax_spin.value(),
            container_type  = container_type,
            container_params= params,
            material_name   = self.material_combo.currentText(),
            model_name      = self.model_combo.currentText(),
            avatar_type     = self.avatar_type,
            color           = self.color_input.text().strip() or "BLUEx",
            group_name      = self.group_name_input.text().strip(),
            dimension       = self.controller.state.dimension,
            seed            = self.seed_spin.value() if self.seed_check.isChecked() else None,
        )

        # UI : état "en cours"
        self._set_running(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self._log(f"⚡ Démarrage : {gen_params['nb_particles']} particules | {container_type}")

        # Lancer le thread
        self._thread = FastGranuloThread(self.engine, gen_params)
        self._thread.progress.connect(self._on_progress)
        self._thread.finished.connect(self._on_finished)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_cancel(self):
        if self._thread and self._thread.isRunning():
            self._thread.abort()
            self._log("⏹ Annulation demandée...")

    def _on_progress(self, current, total, message):
        pct = int(current * 100 / total) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.status_label.setText(message)
        if current % max(1, total // 20) == 0:
            self._log(f"  {message}")

    def _on_finished(self, result):
        self._result = result
        self.progress_bar.setValue(100)

        self._log(f"✅ {result.nb_generated}/{result.nb_requested} particules en {result.elapsed_seconds:.2f}s")
        self._log(f"   Taux de remplissage : {result.success_rate:.1f}%")
        rate = result.nb_generated / result.elapsed_seconds if result.elapsed_seconds > 0 else 0
        self._log(f"   Vitesse : {rate:.0f} particules/s")

        # Écrire le fichier si demandé
        if self.write_file_check.isChecked() and self.output_dir_input.text().strip():
            try:
                path = self.writer.write(result, Path(self.output_dir_input.text().strip()))
                self._log(f"📄 Fichier écrit : {path}")
            except Exception as e:
                self._log(f"❌ Erreur écriture fichier : {e}")

        # Intégrer dans controller.state
        try:
            indices = self.integrator.integrate(result, self.controller)
            self._log(f"🔗 Intégré dans le projet : {len(indices)} avatars → groupe '{result.group_name}'")
            self.granulo_generated.emit()
        except Exception as e:
            self._log(f"❌ Erreur intégration : {e}")

        self.status_label.setText(
            f"✅ Terminé — {result.nb_generated} particules | {result.elapsed_seconds:.1f}s"
        )
        self._set_running(False)

        if result.nb_generated < result.nb_requested * 0.9:
            QMessageBox.warning(
                self, "Taux de remplissage faible",
                f"Seulement {result.success_rate:.0f}% des particules ont été placées.\n"
                "Essayez d'augmenter le conteneur ou de réduire les rayons."
            )

    def _on_error(self, msg):
        self._log(f"❌ {msg}")
        self.status_label.setText(f"Erreur : {msg}")
        self._set_running(False)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_container_params(self, container_type):
        if container_type == "Box2D":
            return {'lx': self._lx.value(), 'ly': self._ly.value()}
        elif container_type in ("Disk2D", "Drum2D", "Sphere3D", "Cylinder3D"):
            return {'r': self._r.value()}
        elif container_type == "Couette2D":
            return {'rint': self._rint.value(), 'rext': self._rext.value()}
        elif container_type == "Box3D":
            return {'lx': self._lx.value(), 'ly': self._ly.value(), 'lz': self._lz.value()}
        return {}

    def _set_running(self, running: bool):
        self.gen_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        self.close_btn.setEnabled(not running)

    def _log(self, msg: str):
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )