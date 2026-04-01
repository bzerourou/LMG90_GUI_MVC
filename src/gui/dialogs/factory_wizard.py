# ============================================================================
# factory_wizard.py
# ============================================================================
"""
Assistant de création de Factory Avatars
"""

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QGroupBox, QTextEdit, QWidget, QFrame,
    QScrollArea, QMessageBox, QButtonGroup, QToolButton,
    QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...core.particle_factory import (
    FactoryConfig, FactoryType, ZoneShape, ContainerShape,
    SizeDistribution, ParticleFactory
)
import math
from typing import List, Optional


# ── Styles (identiques aux autres wizards) ─────────────────────────────────
_STYLE_HEADER = """
    QLabel {
        background: #1a2a4a;
        color: #e0e8ff;
        font-size: 14pt;
        font-weight: bold;
        padding: 10px 14px;
        border-radius: 4px;
    }
"""
_STYLE_SUBTITLE = "color: #607090; font-size: 9pt; padding: 0 14px 6px;"
_STYLE_GROUP = """
    QGroupBox {
        font-weight: bold;
        border: 1px solid #3a5a9a;
        border-radius: 4px;
        margin-top: 6px;
        padding-top: 8px;
        color: #2a4a8a;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }
"""
_STYLE_TYPE_BTN = """
    QToolButton {
        font-size: 10pt;
        font-weight: bold;
        padding: 12px 8px;
        border: 2px solid #ccd;
        border-radius: 6px;
        background: #f4f6ff;
        min-width: 110px;
        min-height: 70px;
    }
    QToolButton:checked {
        background: #2a5aaa;
        color: white;
        border-color: #2a5aaa;
    }
    QToolButton:hover:!checked {
        background: #dde8ff;
        border-color: #5a8aee;
    }
"""
_STYLE_CODE = """
    QTextEdit {
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 8.5pt;
        background: #1e1e2e;
        color: #c8d0e8;
        border: 1px solid #3a4a6a;
        border-radius: 3px;
    }
"""
_LMGC90_COLORS = ['BLUEx', 'REDxx', 'VERTx', 'JAUNx', 'GRAYx',
                   'ORANx', 'CYANx', 'MAGEx', 'VIOLx', 'ROSEx',
                   'BROWx', 'GOLDx', 'WHITx']


# ── Helpers ────────────────────────────────────────────────────────────────
def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFrameShadow(QFrame.Shadow.Sunken)
    return f


def _label(text: str, bold: bool = False) -> QLabel:
    lbl = QLabel(text)
    if bold:
        font = lbl.font()
        font.setBold(True)
        lbl.setFont(font)
    return lbl


def _dbl(value: float, minimum: float = 0., maximum: float = 1e6,
         decimals: int = 4, step: float = 0.001) -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(minimum, maximum)
    sb.setDecimals(decimals)
    sb.setSingleStep(step)
    sb.setValue(value)
    return sb


def _spin(value: int, minimum: int = 0, maximum: int = 100_000) -> QSpinBox:
    sb = QSpinBox()
    sb.setRange(minimum, maximum)
    sb.setValue(value)
    return sb


# ============================================================================
# Page 0 — Accueil + Type de Factory
# ============================================================================
class FactoryIntroPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("🏭 Nouvelle Avatar Factory")
        self.setSubTitle("Inspiré de la fonction Factory d’EDEM.")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("🏭  Nouvelle Avatar Factory")
        title.setStyleSheet(_STYLE_HEADER)
        layout.addWidget(title)

        sub = QLabel(
            "Créez des injections progressives de particules pour éviter les chevauchements initiaux."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(_STYLE_SUBTITLE)
        layout.addWidget(sub)

        layout.addWidget(_sep())

        form = QFormLayout()
        self.name_input = QLineEdit("factory1")
        self.name_input.setMaxLength(32)
        form.addRow("Nom de la factory :", self.name_input)
        layout.addLayout(form)

        layout.addWidget(_label("Type d’injection :", bold=True))

        btn_layout = QHBoxLayout()
        self._type_group = QButtonGroup(self)
        self._type_group.setExclusive(True)

        _TYPES = [

            ("⚙️\nPériodique", FactoryType.PERIODIC.value,"Injections à intervalles réguliers"),
        ]

        for label, ftype, tooltip in _TYPES:
            btn = QToolButton()
            btn.setText(label)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setStyleSheet(_STYLE_TYPE_BTN)
            btn.setProperty('factory_type', ftype)
            btn.setMinimumSize(110, 80)
            self._type_group.addButton(btn)
            btn_layout.addWidget(btn)

        self._type_group.buttons()[0].setChecked(True)
        layout.addLayout(btn_layout)

        self._desc_label = QLabel()
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet(
            "color:#2a5a2a; background:#e8f4e8; padding:8px; border-radius:4px;"
        )
        self._type_group.buttonClicked.connect(self._on_type_changed)
        layout.addWidget(self._desc_label)
        self._on_type_changed(self._type_group.buttons()[0])

        layout.addStretch()

    def _on_type_changed(self, btn):
        descriptions = {
            FactoryType.PERIODIC.value:"⚙️ Injections à intervalles réguliers.",
        }
        ftype = btn.property('factory_type')
        self._desc_label.setText(descriptions.get(ftype, ""))

    @property
    def factory_type(self) -> str:
        checked = self._type_group.checkedButton()
        return checked.property('factory_type') if checked else FactoryType.RAIN.value

    @property
    def name(self) -> str:
        return self.name_input.text().strip() or "factory1"


# ============================================================================
# Page 1 — Zone d’injection
# ============================================================================
class FactoryZonePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("📐 Zone d’injection")
        self.setSubTitle("Définissez la région dans laquelle les particules apparaissent.")

        layout = QVBoxLayout(self)

        # Dimension
        dim_group = QGroupBox("Dimension")
        dim_layout = QHBoxLayout(dim_group)
        self.dim_combo = QComboBox()
        self.dim_combo.addItems(["3D", "2D"])
        self.dim_combo.currentIndexChanged.connect(self._on_dim_changed)
        dim_layout.addWidget(QLabel("Dimension du projet :"))
        dim_layout.addWidget(self.dim_combo)
        dim_layout.addStretch()
        layout.addWidget(dim_group)

        # Zone
        zone_group = QGroupBox("Géométrie de la zone")
        zf = QFormLayout(zone_group)

        self.zone_shape = QComboBox()
        self.zone_shape.addItems(["Boîte / Rectangle", "Cylindre / Disque"])
        zf.addRow("Forme :", self.zone_shape)

        self.zone_cx = _dbl(0.)
        self.zone_cy = _dbl(0.)
        self.zone_cz = _dbl(2.)
        zf.addRow("Centre X :", self.zone_cx)
        zf.addRow("Centre Y :", self.zone_cy)
        self._cz_label = QLabel("Centre Z :")
        zf.addRow(self._cz_label, self.zone_cz)

        self.zone_lx = _dbl(1.0)
        self.zone_ly = _dbl(1.0)
        self.zone_lz = _dbl(0.5)
        zf.addRow("Largeur X (lx) :", self.zone_lx)
        self._ly_label = QLabel("Largeur Y (ly) :")
        zf.addRow(self._ly_label, self.zone_ly)
        zf.addRow("Épaisseur Z (lz) :", self.zone_lz)

        layout.addWidget(zone_group)

        info = QLabel(
            "💡 Les avatars seront placées sur un réseau régulier avec "
            "perturbation dans cette zone.\nEspacement automatique = 2.2 × rayon_max."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()

    def _on_dim_changed(self, idx: int):
        is_3d = (idx == 0)
        self._cz_label.setVisible(is_3d)
        self.zone_cz.setVisible(is_3d)
        self._ly_label.setVisible(is_3d)
        self.zone_ly.setVisible(is_3d)
        self.zone_lz.setVisible(is_3d)

    @property
    def dimension(self) -> int:
        return 3 if self.dim_combo.currentIndex() == 0 else 2

    def get_zone_params(self) -> dict:
        dim = self.dimension
        shape = (ZoneShape.BOX.value if self.zone_shape.currentIndex() == 0
                 else ZoneShape.CYLINDER.value)
        center = ([self.zone_cx.value(), self.zone_cy.value(), self.zone_cz.value()]
                  if dim == 3 else [self.zone_cx.value(), self.zone_cy.value()])
        return {
            'dimension': dim,
            'zone_shape': shape,
            'zone_center': center,
            'zone_lx': self.zone_lx.value(),
            'zone_ly': self.zone_ly.value() if dim == 3 else self.zone_lx.value(),
            'zone_lz': self.zone_lz.value(),
        }


# ============================================================================
# Page 2 — Particules
# ============================================================================
class FactoryParticlesPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setTitle("⚛️ Paramètres des particules")
        self.setSubTitle("Type, taille, matériau, modèle, couleur.")

        layout = QVBoxLayout(self)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)

        # Type
        type_group = QGroupBox("Type")
        tf = QFormLayout(type_group)
        self.particle_type = QComboBox()
        self.particle_type.addItems(["rigidDisk (2D)", "rigidSphere (3D)"])
        tf.addRow("Type :", self.particle_type)
        inner_layout.addWidget(type_group)

        # Taille
        size_group = QGroupBox("Distribution de taille")
        sf = QFormLayout(size_group)
        self.dist_combo = QComboBox()
        self.dist_combo.addItems(["Uniforme (rayon fixe)",
                                  "Aléatoire [rmin, rmax]",
                                  "granulo_Random (LMGC90)"])
        sf.addRow("Distribution :", self.dist_combo)
        self.r_min = _dbl(0.010)
        self.r_max = _dbl(0.020)
        sf.addRow("Rayon min :", self.r_min)
        sf.addRow("Rayon max :", self.r_max)
        self.seed_check = QCheckBox("Graine aléatoire fixe")
        self.seed_spin = _spin(42)
        self.seed_spin.setEnabled(False)
        self.seed_check.toggled.connect(self.seed_spin.setEnabled)
        seed_row = QHBoxLayout()
        seed_row.addWidget(self.seed_check)
        seed_row.addWidget(self.seed_spin)
        sf.addRow("", seed_row)
        inner_layout.addWidget(size_group)

        # Matériau / Modèle
        mm_group = QGroupBox("Matériau et modèle")
        mf = QFormLayout(mm_group)
        self.material_combo = QComboBox()
        self.model_combo = QComboBox()
        mf.addRow("Matériau :", self.material_combo)
        mf.addRow("Modèle :", self.model_combo)
        inner_layout.addWidget(mm_group)

        # Nombre + couleur
        np_group = QGroupBox("Nombre et couleur")
        nf = QFormLayout(np_group)
        self.nb_spin = _spin(100, 1, 100_000)
        self.color_combo = QComboBox()
        for col in _LMGC90_COLORS:
            self.color_combo.addItem(col)
        nf.addRow("Nombre de particules :", self.nb_spin)
        nf.addRow("Couleur LMGC90 :", self.color_combo)
        inner_layout.addWidget(np_group)

        inner_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

    def initializePage(self):
        self.material_combo.clear()
        self.model_combo.clear()
        state = self.controller.state
        for mat in getattr(state, 'materials', []):
            self.material_combo.addItem(mat.name)
        for mod in getattr(state, 'models', []):
            self.model_combo.addItem(mod.name)

    def get_particle_params(self) -> dict:
        # Index 0 = "rigidDisk (2D)", index 1 = "rigidSphere (3D)"
        ptype = 'rigidDisk' if self.particle_type.currentIndex() == 0 else 'rigidSphere'
        dist_map = {0: SizeDistribution.UNIFORM.value,
                    1: SizeDistribution.RANDOM.value,
                    2: SizeDistribution.GRANULO.value}
        seed = self.seed_spin.value() if self.seed_check.isChecked() else None
        return {
            'particle_type': ptype,
            'distribution': dist_map.get(self.dist_combo.currentIndex(), SizeDistribution.RANDOM.value),
            'radius_min': self.r_min.value(),
            'radius_max': self.r_max.value(),
            'nb_particles': self.nb_spin.value(),
            'model_name': self.model_combo.currentText(),
            'material_name': self.material_combo.currentText(),
            'color': self.color_combo.currentText(),
            'seed': seed,
        }


# ============================================================================
# Page 3 — Conteneur
# ============================================================================
class FactoryContainerPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("🧱 Conteneur (parois)")
        self.setSubTitle("Optionnel — création automatique de parois.")

        layout = QVBoxLayout(self)

        self.enable_check = QCheckBox("Créer un conteneur automatiquement")
        self.enable_check.setChecked(False)
        self.enable_check.toggled.connect(self._on_toggle)
        layout.addWidget(self.enable_check)

        self._container_widget = QWidget()
        cw_layout = QVBoxLayout(self._container_widget)

        shape_group = QGroupBox("Type de conteneur")
        shf = QFormLayout(shape_group)
        self.shape_combo = QComboBox()
        self.shape_combo.addItems([
            "Boîte ouverte (sans couvercle)",
            "Boîte fermée",
            "Silo rectangulaire",
            "Trémie (entonnoir)",
        ])
        shf.addRow("Forme :", self.shape_combo)
        cw_layout.addWidget(shape_group)

        dim_group = QGroupBox("Dimensions du conteneur")
        df = QFormLayout(dim_group)
        self.c_lx = _dbl(2.0)
        self.c_ly = _dbl(2.0)
        self.c_lz = _dbl(3.0)
        self.c_wall_r = _dbl(0.01, 0.001, 1.)
        self.c_cx = _dbl(0.)
        self.c_cy = _dbl(0.)
        self.c_cz = _dbl(0.)
        df.addRow("Largeur (lx) :", self.c_lx)
        df.addRow("Profondeur (ly) :", self.c_ly)
        df.addRow("Hauteur (lz) :", self.c_lz)
        df.addRow("Épaisseur parois :", self.c_wall_r)
        df.addRow("Centre X :", self.c_cx)
        df.addRow("Centre Y :", self.c_cy)
        df.addRow("Centre Z :", self.c_cz)
        cw_layout.addWidget(dim_group)
        cw_layout.addStretch()

        self._container_widget.setEnabled(False)
        layout.addWidget(self._container_widget)
        layout.addStretch()

    def _on_toggle(self, checked: bool):
        self._container_widget.setEnabled(checked)

    def get_container_params(self) -> dict:
        if not self.enable_check.isChecked():
            return {'container_shape': ContainerShape.NONE.value}
        shape_map = {
            0: ContainerShape.BOX_OPEN.value,
            1: ContainerShape.BOX_CLOSED.value,
            2: ContainerShape.SILO_BOX.value,
            3: ContainerShape.HOPPER.value,
        }
        return {
            'container_shape': shape_map.get(self.shape_combo.currentIndex(), ContainerShape.BOX_OPEN.value),
            'container_lx': self.c_lx.value(),
            'container_ly': self.c_ly.value(),
            'container_lz': self.c_lz.value(),
            'container_wall_r': self.c_wall_r.value(),
            'container_center': [self.c_cx.value(), self.c_cy.value(), self.c_cz.value()],
        }


# ============================================================================
# Page 4 — Planning
# ============================================================================
class FactorySchedulePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("📅 Planning d’activation")
        self.setSubTitle("Définissez les vagues d’activation des particules.")

        layout = QVBoxLayout(self)

        wave_group = QGroupBox("Vagues d’activation")
        wf = QFormLayout(wave_group)
        self.batch_size = _spin(10, 1, 10000)
        self.start_step = _spin(1, 0, 1000000)
        self.interval = _spin(50, 1, 1000000)
        wf.addRow("Particules par vague :", self.batch_size)
        wf.addRow("Pas de départ :", self.start_step)
        wf.addRow("Intervalle entre vagues :", self.interval)
        layout.addWidget(wave_group)

        vel_group = QGroupBox("Vitesse initiale (optionnel)")
        vf = QFormLayout(vel_group)
        self.vx = _dbl(0., -1000., 1000.)
        self.vy = _dbl(0., -1000., 1000.)
        self.vz = _dbl(0., -1000., 1000.)
        self.v_noise = _dbl(0., 0., 100.)
        vf.addRow("Vx :", self.vx)
        vf.addRow("Vy :", self.vy)
        vf.addRow("Vz :", self.vz)
        vf.addRow("Bruit aléatoire :", self.v_noise)
        layout.addWidget(vel_group)

        # Aperçu
        preview_group = QGroupBox("Aperçu du planning")
        pl = QVBoxLayout(preview_group)
        self._preview_label = QLabel()
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("font-family: monospace; font-size: 8pt;")
        pl.addWidget(self._preview_label)
        layout.addWidget(preview_group)

        layout.addStretch()

        # Mise à jour aperçu
        for w in (self.batch_size, self.start_step, self.interval):
            w.valueChanged.connect(self._update_preview)

    def _update_preview(self):
        self.update_preview(100)  # valeur exemple

    def update_preview(self, nb_particles: int):
        bs = max(1, self.batch_size.value())
        st = self.start_step.value()
        iv = max(1, self.interval.value())
        nb_batches = math.ceil(nb_particles / bs)
        last = st + (nb_batches - 1) * iv

        lines = [
            f"Particules totales : {nb_particles}",
            f"Vagues             : {nb_batches} × {bs} particules",
            f"Première vague     : pas {st}",
            f"Intervalle         : {iv} pas",
            f"Dernière vague     : pas {last}",
            "",
        ]
        for i in range(min(5, nb_batches)):
            step = st + i * iv
            b_s = i * bs + 1
            b_e = min((i + 1) * bs, nb_particles)
            lines.append(f"  Vague {i+1:2d} → pas {step:6d} : particules {b_s}..{b_e}")
        if nb_batches > 5:
            lines.append(f"  … ({nb_batches - 5} vague(s) supplémentaire(s))")

        self._preview_label.setText('\n'.join(lines))

    def get_schedule_params(self) -> dict:
        return {
            'batch_size': self.batch_size.value(),
            'start_step': self.start_step.value(),
            'interval_steps': self.interval.value(),
            'velocity': [self.vx.value(), self.vy.value(), self.vz.value()],
            'velocity_random': self.v_noise.value(),
        }


# ============================================================================
# Page 5 — Résumé
# ============================================================================
class FactorySummaryPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("✅ Récapitulatif et code généré")
        self.setSubTitle("Vérifiez avant de créer la factory.")

        layout = QVBoxLayout(self)

        self._summary_label = QLabel()
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet(
            "background:#eef4ee; border:1px solid #aadaaa; padding:10px; border-radius:4px; font-size:9pt;"
        )
        layout.addWidget(self._summary_label)

        # Code tabs
        tabs_row = QHBoxLayout()
        self._btn_pre = QPushButton("Code pre.py")
        self._btn_chipy = QPushButton("Code chipy.py")
        self._btn_pre.setCheckable(True)
        self._btn_chipy.setCheckable(True)
        self._btn_pre.setChecked(True)
        self._btn_pre.clicked.connect(lambda: self._show_tab('pre'))
        self._btn_chipy.clicked.connect(lambda: self._show_tab('chipy'))
        tabs_row.addWidget(self._btn_pre)
        tabs_row.addWidget(self._btn_chipy)
        tabs_row.addStretch()
        layout.addLayout(tabs_row)

        self._code_edit = QTextEdit()
        self._code_edit.setReadOnly(True)
        self._code_edit.setStyleSheet(_STYLE_CODE)
        self._code_edit.setMinimumHeight(220)
        layout.addWidget(self._code_edit)

        # Paramètres chipy
        chipy_row = QHBoxLayout()
        chipy_row.addWidget(QLabel("nb_steps :"))
        self.nb_steps_spin = _spin(1000, 1, 10_000_000)
        self.nb_steps_spin.valueChanged.connect(self._refresh_chipy)
        chipy_row.addWidget(self.nb_steps_spin)
        chipy_row.addWidget(QLabel("freq_write :"))
        self.freq_spin = _spin(100, 1, 100_000)
        self.freq_spin.valueChanged.connect(self._refresh_chipy)
        chipy_row.addWidget(self.freq_spin)
        chipy_row.addStretch()
        layout.addLayout(chipy_row)

        layout.addStretch()

        self._pre_code = ""
        self._chipy_code = ""
        self._current_tab = 'pre'
        self._factory_engine = None
        self._dim = 3

    def initializePage(self):
        """
        Appelé automatiquement par QWizard dès que l'utilisateur arrive
        sur cette page (clic "Suivant"). C'est ici qu'on assemble et qu'on
        peuple le code — pas dans accept() qui est trop tardif.
        """
        wiz = self.wizard()
        if wiz is not None:
            wiz._prepare_summary()

    def _show_tab(self, tab: str):
        self._current_tab = tab
        self._btn_pre.setChecked(tab == 'pre')
        self._btn_chipy.setChecked(tab == 'chipy')
        self._code_edit.setPlainText(self._pre_code if tab == 'pre' else self._chipy_code)

    def _refresh_chipy(self):
        if self._factory_engine:
            self._chipy_code = self._factory_engine.generate_chipy_code(
                nb_steps=self.nb_steps_spin.value(),
                freq_write=self.freq_spin.value(),
                dimension=self._dim,
            )
            if self._current_tab == 'chipy':
                self._code_edit.setPlainText(self._chipy_code)

    def populate(self, config: FactoryConfig, factory_engine: ParticleFactory):
        self._factory_engine = factory_engine
        self._dim = config.dimension
        self._pre_code = factory_engine.generate_pre_code()
        self._chipy_code = factory_engine.generate_chipy_code(
            nb_steps=self.nb_steps_spin.value(),
            freq_write=self.freq_spin.value(),
            dimension=config.dimension,
        )
        self._code_edit.setPlainText(self._pre_code)
        self._current_tab = 'pre'

        lines = [
            f"✅ Factory « {config.name} » ({config.factory_type})",
            f"     {config.nb_particles} × {config.particle_type}",
            f"     Rayon : [{config.radius_min}, {config.radius_max}]",
            f"     Matériau : {config.material_name}  |  Modèle : {config.model_name}",
            f"     Zone : {config.zone_center} — {config.zone_lx}×{config.zone_ly}"
            + (f"×{config.zone_lz}" if config.dimension == 3 else ""),
            f"     {config.nb_batches} vague(s) de {config.batch_size}, dès le pas {config.start_step}",
        ]
        if config.container_shape != ContainerShape.NONE.value:
            lines.append(f"     Conteneur : {config.container_shape}")
        self._summary_label.setText('\n'.join(lines))

    @property
    def pre_code(self) -> str:
        return self._pre_code

    @property
    def chipy_code(self) -> str:
        return self._chipy_code


# ============================================================================
# Wizard principal
# ============================================================================
class FactoryWizard(QWizard):
    PAGE_INTRO      = 0
    PAGE_ZONE       = 1
    PAGE_PARTICLES  = 2
    PAGE_CONTAINER  = 3
    PAGE_SCHEDULE   = 4
    PAGE_SUMMARY    = 5

    factory_created = pyqtSignal(object)  # FactoryConfig

    def __init__(self, controller, parent=None, existing_engine: Optional[ParticleFactory] = None):
        super().__init__(parent)
        self.controller = controller
        self.engine = existing_engine or ParticleFactory()
        self.result_config: Optional[FactoryConfig] = None

        self.setWindowTitle("Assistant Avatar Factory — LMGC90_GUI")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(740, 680)

        self.addPage(FactoryIntroPage())
        self.addPage(FactoryZonePage())
        self.addPage(FactoryParticlesPage(controller))
        self.addPage(FactoryContainerPage())
        self.addPage(FactorySchedulePage())
        self.addPage(FactorySummaryPage())

        self.setButtonText(QWizard.WizardButton.NextButton, "Suivant ➡️")
        self.setButtonText(QWizard.WizardButton.BackButton, "⬅️ Retour")
        self.setButtonText(QWizard.WizardButton.FinishButton, "✅ Créer la Factory")
        self.setButtonText(QWizard.WizardButton.CancelButton, "❌ Annuler")

    def accept(self):
        if self._create_factory():
            self.factory_created.emit(self.result_config)
            super().accept()

    def _prepare_summary(self):
        """
        Assemble la config et peuple la page Résumé.
        Appelé depuis FactorySummaryPage.initializePage() dès que
        l'utilisateur arrive sur la page via "Suivant", avant "Terminer".
        C'est ce qui manquait : populate() n'était jamais appelé à ce stade.
        """
        try:
            zone  = self.page(self.PAGE_ZONE).get_zone_params()
            parts = self.page(self.PAGE_PARTICLES).get_particle_params()
            cont  = self.page(self.PAGE_CONTAINER).get_container_params()
            sched = self.page(self.PAGE_SCHEDULE).get_schedule_params()

            config = FactoryConfig(
                name=self.page(self.PAGE_INTRO).name,
                factory_type=self.page(self.PAGE_INTRO).factory_type,
                **zone, **parts, **cont, **sched
            )

            nb_existing = len(getattr(self.controller.state, 'avatars', []))
            engine = ParticleFactory()
            engine.reset_body_counter(nb_existing + 1)
            engine.add(config)

            self.page(self.PAGE_SUMMARY).populate(config, engine)

        except Exception as e:
            self.page(self.PAGE_SUMMARY)._summary_label.setText(
                f"⚠️ Erreur lors de la prévisualisation :\n{e}"
            )

    def _create_factory(self) -> bool:
        """Valide et finalise la factory au clic sur Terminer."""
        try:
            zone  = self.page(self.PAGE_ZONE).get_zone_params()
            parts = self.page(self.PAGE_PARTICLES).get_particle_params()
            cont  = self.page(self.PAGE_CONTAINER).get_container_params()
            sched = self.page(self.PAGE_SCHEDULE).get_schedule_params()

            config = FactoryConfig(
                name=self.page(self.PAGE_INTRO).name,
                factory_type=self.page(self.PAGE_INTRO).factory_type,
                **zone, **parts, **cont, **sched
            )

            ok, errors = self.engine.validate(config)
            if not ok:
                QMessageBox.warning(self, "Validation", "Erreurs :\n• " + "\n• ".join(errors))
                return False

            nb_existing = len(getattr(self.controller.state, 'avatars', []))
            self.engine.reset_body_counter(nb_existing + 1)
            self.engine.configs.clear()
            self.engine.add(config)

            self.result_config = config
            return True

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'assembler la config :\n{e}")
            return False


# ============================================================================
# Onglet FactoryTab — intégration complète avec ProjectState
# ============================================================================
class FactoryTab(QWidget):
    """
    Onglet Factories dans MainWindow.

    Responsabilités
    ───────────────
    • Lister les factories du projet (chargées depuis controller.state.factories)
    • Lancer le wizard pour en créer une nouvelle
    • Sauvegarder chaque factory dans controller.state.factories (persistance JSON)
    • Afficher et exporter le code pre.py et chipy.py généré
    • Activer/désactiver, supprimer une factory existante
    """

    factory_updated = pyqtSignal()

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._engine    = ParticleFactory()
        self._build_ui()
        self.refresh()

    # ── Construction UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        from PyQt6.QtWidgets import QListWidget, QFileDialog
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        # En-tête
        hdr = QLabel("<b>🏭  Particle Factories</b>")
        hdr.setStyleSheet("font-size:11pt; padding:4px;")
        layout.addWidget(hdr)

        desc = QLabel(
            "Injection progressive de particules inspirée de la Factory EDEM. "
            "Les particules sont créées invisibles dans le DATBOX et activées "
            "par vagues dans la boucle chipy."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#606090; font-size:8pt; padding-bottom:4px;")
        layout.addWidget(desc)

        layout.addWidget(_sep())

        # ── Liste ─────────────────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>Factories configurées</b>"))

        self._list = QListWidget()
        self._list.setMaximumHeight(160)
        self._list.setAlternatingRowColors(True)
        self._list.currentRowChanged.connect(self._on_select)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("➕ Nouvelle")
        self._edit_btn = QPushButton("✏️ Modifier")
        self._del_btn  = QPushButton("🗑️ Supprimer")
        self._tog_btn  = QPushButton("⏸️ Activer/Désactiver")
        for b in (self._add_btn, self._edit_btn, self._del_btn, self._tog_btn):
            btn_row.addWidget(b)
        btn_row.addStretch()
        self._add_btn.clicked.connect(self._on_add)
        self._del_btn.clicked.connect(self._on_delete)
        self._tog_btn.clicked.connect(self._on_toggle)
        self._edit_btn.clicked.connect(self._on_edit)
        layout.addLayout(btn_row)

        layout.addWidget(_sep())

        # ── Détail ────────────────────────────────────────────────────────────
        self._detail_label = QLabel("Sélectionnez une factory pour voir le détail.")
        self._detail_label.setWordWrap(True)
        self._detail_label.setStyleSheet(
            "background:#eef4ff; border:1px solid #aab8dd; "
            "padding:8px; border-radius:4px; font-size:8.5pt;"
        )
        self._detail_label.setMinimumHeight(60)
        layout.addWidget(self._detail_label)

        # ── Code généré ────────────────────────────────────────────────────────
        code_hdr = QHBoxLayout()
        code_hdr.addWidget(QLabel("<b>Code généré</b>"))
        code_hdr.addStretch()

        self._btn_pre   = QPushButton("pre.py")
        self._btn_chipy = QPushButton("chipy.py")
        self._btn_pre.setCheckable(True)
        self._btn_chipy.setCheckable(True)
        self._btn_pre.setChecked(True)
        self._btn_pre.setFixedWidth(70)
        self._btn_chipy.setFixedWidth(70)
        self._btn_pre.clicked.connect(lambda: self._show_code_tab('pre'))
        self._btn_chipy.clicked.connect(lambda: self._show_code_tab('chipy'))
        code_hdr.addWidget(self._btn_pre)
        code_hdr.addWidget(self._btn_chipy)

        code_hdr.addWidget(QLabel("  nb_steps :"))
        self._nb_steps_spin = QSpinBox()
        self._nb_steps_spin.setRange(1, 10_000_000)
        self._nb_steps_spin.setValue(1000)
        self._nb_steps_spin.setFixedWidth(90)
        self._nb_steps_spin.valueChanged.connect(self._refresh_codes)
        code_hdr.addWidget(self._nb_steps_spin)
        layout.addLayout(code_hdr)

        self._code_edit = QTextEdit()
        self._code_edit.setReadOnly(True)
        self._code_edit.setStyleSheet(_STYLE_CODE)
        self._code_edit.setMinimumHeight(160)
        layout.addWidget(self._code_edit)

        exp_row = QHBoxLayout()
        exp_pre   = QPushButton("💾 Exporter pre_factory.py")
        exp_chipy = QPushButton("💾 Exporter chipy_factory.py")
        exp_pre.clicked.connect(self._export_pre)
        exp_chipy.clicked.connect(self._export_chipy)
        exp_row.addWidget(exp_pre)
        exp_row.addWidget(exp_chipy)
        exp_row.addStretch()
        layout.addLayout(exp_row)

        layout.addStretch()

        self._current_tab = 'pre'
        self._pre_code    = ''
        self._chipy_code  = ''

    # ── Actions ────────────────────────────────────────────────────────────────

    def _on_add(self):
        """Lance le wizard et sauvegarde la factory créée dans ProjectState."""
        dlg = FactoryWizard(self.controller, self, self._engine)
        if dlg.exec() == QWizard.DialogCode.Accepted and dlg.result_config:
            # Persister dans ProjectState
            if not hasattr(self.controller.state, 'factories'):
                self.controller.state.factories = []
            self.controller.state.factories = self._engine.to_list_of_dicts()
            if hasattr(self.controller, 'mark_modified'):
                self.controller.mark_modified()
            self.refresh()
            self.factory_updated.emit()

    def _on_edit(self):
        """Supprime et recrée via le wizard (édition complète = évolution future)."""
        row = self._list.currentRow()
        if row < 0 or row >= len(self._engine.configs):
            QMessageBox.information(self, "Sélection",
                                    "Sélectionnez une factory à modifier.")
            return
        cfg = self._engine.configs[row]
        reply = QMessageBox.question(
            self, "Modifier",
            f"La factory « {cfg.name} » sera reconfigurée via l'assistant.\n"
            "La version actuelle sera remplacée. Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._engine.remove(cfg.name)
        self._on_add()

    def _on_delete(self):
        """Supprime la factory sélectionnée."""
        row = self._list.currentRow()
        if row < 0 or row >= len(self._engine.configs):
            QMessageBox.information(self, "Sélection",
                                    "Sélectionnez une factory à supprimer.")
            return
        name = self._engine.configs[row].name
        reply = QMessageBox.question(
            self, "Supprimer ?",
            f"Supprimer la factory « {name} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._engine.remove(name)
        self.controller.state.factories = self._engine.to_list_of_dicts()
        if hasattr(self.controller, 'mark_modified'):
            self.controller.mark_modified()
        self.refresh()
        self.factory_updated.emit()

    def _on_toggle(self):
        """Active ou désactive la factory sélectionnée."""
        row = self._list.currentRow()
        if row < 0 or row >= len(self._engine.configs):
            return
        cfg = self._engine.configs[row]
        cfg.enabled = not cfg.enabled
        self.controller.state.factories = self._engine.to_list_of_dicts()
        if hasattr(self.controller, 'mark_modified'):
            self.controller.mark_modified()
        self.refresh()
        self._list.setCurrentRow(row)

    def _on_select(self, row: int):
        """Affiche le détail de la factory sélectionnée."""
        if row < 0 or row >= len(self._engine.configs):
            self._detail_label.setText("Sélectionnez une factory pour voir le détail.")
            return
        cfg = self._engine.configs[row]
        status = "✅ Active" if cfg.enabled else "⏸️ Désactivée"
        lines = [
            f"<b>{cfg.name}</b>  ({cfg.factory_type})  — {status}",
            f"&nbsp;&nbsp;{cfg.nb_particles} × <b>{cfg.particle_type}</b>"
            f"  r=[{cfg.radius_min}, {cfg.radius_max}]"
            f"  matériau={cfg.material_name}  modèle={cfg.model_name}",
            f"&nbsp;&nbsp;Zone : centre={cfg.zone_center}"
            f"  {cfg.zone_lx}×{cfg.zone_ly}"
            + (f"×{cfg.zone_lz}" if cfg.dimension == 3 else ""),
            f"&nbsp;&nbsp;<b>{cfg.nb_batches} vague(s)</b> de {cfg.batch_size}"
            f"  |  départ pas {cfg.start_step}"
            f"  |  intervalle {cfg.interval_steps}"
            f"  |  fin pas {cfg.last_activation_step}",
            f"&nbsp;&nbsp;Corps LMGC90 : {cfg.body_index_start}..{cfg.body_index_end}",
        ]
        if cfg.container_shape and cfg.container_shape != ContainerShape.NONE.value:
            lines.append(f"&nbsp;&nbsp;Conteneur : {cfg.container_shape}"
                         f"  {cfg.container_lx}×{cfg.container_ly}×{cfg.container_lz}")
        self._detail_label.setText("<br>".join(lines))

    # ── Rafraîchissement ────────────────────────────────────────────────────────

    def refresh(self):
        """
        Recharge l'engine depuis controller.state.factories.
        Appelé par MainWindow._refresh_all() à chaque changement d'état.
        """
        saved = getattr(self.controller.state, 'factories', []) or []
        if saved:
            self._engine = ParticleFactory.from_list_of_dicts(saved)
            nb_existing  = len(getattr(self.controller.state, 'avatars', []))
            self._engine.reset_body_counter(nb_existing + 1)
            for cfg in self._engine.configs:
                self._engine._assign_body_indices(cfg)

        current_row = self._list.currentRow()
        self._list.clear()
        for cfg in self._engine.configs:
            status  = "✅" if cfg.enabled else "⏸️"
            self._list.addItem(
                f"[{status}] {cfg.name} — {cfg.nb_particles}× {cfg.particle_type}"
                f"  |  {cfg.nb_batches} vague(s) de {cfg.batch_size}"
                f"  |  pas {cfg.start_step}→{cfg.last_activation_step}"
            )

        if 0 <= current_row < self._list.count():
            self._list.setCurrentRow(current_row)
        elif self._list.count() > 0:
            self._list.setCurrentRow(0)
        else:
            self._detail_label.setText("Aucune factory — cliquez sur ➕ Nouvelle.")

        self._refresh_codes()

    def _refresh_codes(self):
        if not self._engine.configs:
            self._pre_code   = "# Aucune factory configurée."
            self._chipy_code = "# Aucune factory configurée."
        else:
            nb_existing = len(getattr(self.controller.state, 'avatars', []))
            dim = getattr(self.controller.state, 'dimension', 3)
            self._pre_code   = self._engine.generate_pre_code(
                body_counter_start=nb_existing + 1
            )
            self._chipy_code = self._engine.generate_chipy_code(
                nb_steps=self._nb_steps_spin.value(),
                dimension=dim,
            )
        self._update_code_display()

    def _show_code_tab(self, tab: str):
        self._current_tab = tab
        self._btn_pre.setChecked(tab == 'pre')
        self._btn_chipy.setChecked(tab == 'chipy')
        self._update_code_display()

    def _update_code_display(self):
        code = self._pre_code if self._current_tab == 'pre' else self._chipy_code
        self._code_edit.setPlainText(code)

    # ── Export ─────────────────────────────────────────────────────────────────

    def _export_pre(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter le code pre.py", "pre_factory.py",
            "Python (*.py);;Tous les fichiers (*)"
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self._pre_code)

    def _export_chipy(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter le code chipy.py", "chipy_factory.py",
            "Python (*.py);;Tous les fichiers (*)"
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self._chipy_code)