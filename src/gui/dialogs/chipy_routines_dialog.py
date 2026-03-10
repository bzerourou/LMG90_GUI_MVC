# ============================================================================
# chipy_routines_dialog.py  —  LMGC90_GUI
# ============================================================================
"""
Dialogue de configuration des routines chipy pour la generation
du script de calcul command.py.

4 onglets :
  1. Modele      — mhyp, deformable, physique FEM, Rloc_tol, info projet
  2. Routines    — corps rigides (RBDY2/3), detecteurs 2D/3D, FEM, mixtes,
                   routines speciales
  3. Extraction  — visualisation, forces de contact, energie, champs FEM
  4. Pilotage    — restart, critere d'arret, multi-pas (dt variable)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QFormLayout, QLabel, QLineEdit, QComboBox,
    QCheckBox, QSpinBox, QDoubleSpinBox, QDialogButtonBox,
    QScrollArea, QFrame, QButtonGroup, QRadioButton,
    QMessageBox, QPushButton, QTextEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import Dict, Any, Optional


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section(title: str) -> QGroupBox:
    """QGroupBox avec titre en gras et bordure subtile."""
    gb = QGroupBox(title)
    gb.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 1px solid #b8b8b8;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 4px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: #2c3e50;
        }
    """)
    return gb


def _scroll(w: QWidget) -> QScrollArea:
    sc = QScrollArea()
    sc.setWidget(w)
    sc.setWidgetResizable(True)
    sc.setFrameShape(QFrame.Shape.NoFrame)
    return sc


def _cb(label: str, checked: bool = False, tip: str = "") -> QCheckBox:
    c = QCheckBox(label)
    c.setChecked(checked)
    if tip:
        c.setToolTip(tip)
    return c

def _note(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        "color:#555; font-size:8pt; "
        "background:#f7f7f7; padding:4px 6px; border-radius:3px;"
    )
    return lbl


# ============================================================================
# ChipyRoutinesDialog
# ============================================================================
# Vecteurs d'etat disponibles pour RBDY2 et RBDY3
_GBV_VECTORS_2D = [
    ("Coor0",          "Coordonnees de références  (x, y, angle)"),
    ("Coor_",          "Coordonnees generalisees  (x, y, angle)"),
    ("Coorb",          "Coordonnees premier pas  (x, y, angle)"),
    ("Coorm",          "Coordonnees en detection  (x, y, angle)"),
    ("X____",          "déplacements cumulés   (x, y, angle)"),
    ("V____",          "Vitesses generalisees     (vx, vy, omega)"),
    ("Vbeg_",          "vitesse  premier pas  (vx, vy, omega)"),
    ("Vfree",          "vitesse  libre de contact  (vx, vy, omega)"),
    ("Fext_",          "Forces externes           (Fx, Fy, Mz)"),
    ("Fint_",          "Forces interne         (Fix, Fiy, Mz)"),
    ("Reac_",          "Forces de reaction        (Rx, Ry, Rz)"),
    ("Ireac",          "impulsion de contact       (Ix, Iy)"),

]

# en 3D
_GBV_VECTORS_3D = [
    ("Coor0",          "Coordonnees de références  (x, y, z, q0, q1, q2, q3)"),
    ("Coor_",          "Coordonnees generalisees  (x, y, z, q0, q1, q2, q3)"),
    ("Coorb",          "Coordonnees premier pas  (x, y, z, q0, q1, q2, q3)"),
    ("Coorm",          "Coordonnees en detection  (x, y, z, q0, q1, q2, q3)"),
    ("X____",          "déplacements cumulés   (x, y, z, q0, q1, q2, q3)"),
    ("V____",          "Vitesses generalisees     (vx, vy, vz, wx, wy, wz)"),
    ("Vbeg_",          "vitesse  premier pas  (vx, vy, vz, wx, wy, wz)"),
    ("Vfree",          "vitesse  libre de contact  (vx, vy, vz, wx, wy, wz)"),
    ("Fext_",          "Forces externes           (Fx, Fy, Fz, Mx, My, Mz)"),
    ("Fint_",          "Forces interne         (Fix, Fiy, Fiz, Mx, My, Mz)"),
    ("Reac_",          "Forces de reaction        (Rx, Ry, Rz)"),
    ("Ireac",          "impulsion de contact       (Ix, Iy, Iz)"),
]


class ChipyRoutinesDialog(QDialog):
    """
    Dialogue de configuration des routines chipy.

    Utilisation :
        dlg = ChipyRoutinesDialog(current_params, controller, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            params = dlg.get_params()
    """

    # ── Valeurs par defaut ────────────────────────────────────────────────────
    DEFAULTS: Dict[str, Any] = {
        # Onglet Modele
        "mhyp":               1,
        "deformable":         False,
        "physics":            "MECAx",
        "Rloc_tol":           5e-2,
        # Onglet Routines — Corps rigides
        "use_RBDY2":          True,
        "use_RBDY3":          False,
        # Detecteurs 2D
        "use_DKDKx":          True,
        "use_DKJCx":          False,
        "use_DKKDx":          False,
        "use_PLPLx":          False,
        "use_CLALp":          False,
        "use_ALpALp":         False,
        # Detecteurs 3D
        "use_SPSPx":          False,
        "use_SPCDx":          False,
        "use_SPPLx":          False,
        "use_CDCDx":          False,
        "use_CDPLx":          False,
        "use_PRPRx":          False,
        # Deformables
        "use_mecaFEM":        False,
        "use_therFEM":        False,
        "use_hydrFEM":        False,
        # Contacteurs mixtes rigide/deformable
        "use_DKMECAx":        False,
        "use_ALpMECAx":       False,
        "use_SPMECAx":        False,
        # Routines speciales
        "use_PT2Dx":          False,
        "use_PT3Dx":          False,
        "use_NODES":          False,
        "use_bulk_behav":     False,
        # Onglet Extraction — Logs
        "disable_log":        False,
        # Visualisation
        "visu_RBDY2":         True,
        "visu_RBDY3":         False,
        "visu_mecaFEM":       False,
        "visu_therFEM":       False,
        "visu_hydrFEM":       False,
        "display_in_loop":    True,
        # Visibilite avatars — listes d'IDs (ex: "1, 3, 5") ou "" = desactive
        "vis_RBDY2_visible":   "",
        "vis_RBDY2_invisible": "",
        "vis_RBDY3_visible":   "",
        "vis_RBDY3_invisible": "",
        # GetBodyVector RBDY2 — booleen + frequence par vecteur
        "gbv2_Coor":          False,  "gbv2_Coor_freq":          1,
        "gbv2_Velo":          False,  "gbv2_Velo_freq":          1,
        "gbv2_Fext":          False,  "gbv2_Fext_freq":          1,
        "gbv2_Reac":          False,  "gbv2_Reac_freq":          1,
        "gbv2_Acce":          False,  "gbv2_Acce_freq":          1,
        "gbv2_RigidBodyMass": False,  "gbv2_RigidBodyMass_freq": 1,
        # GetBodyVector RBDY3
        "gbv3_Coor":          False,  "gbv3_Coor_freq":          1,
        "gbv3_Velo":          False,  "gbv3_Velo_freq":          1,
        "gbv3_Fext":          False,  "gbv3_Fext_freq":          1,
        "gbv3_Reac":          False,  "gbv3_Reac_freq":          1,
        "gbv3_Acce":          False,  "gbv3_Acce_freq":          1,
        "gbv3_RigidBodyMass": False,  "gbv3_RigidBodyMass_freq": 1,
        # Forces de contact
        "extract_Rnod":       False,
        "extract_Vloc":       False,
        "extract_Rloc":       False,
        # Energie
        "extract_energy":     False,
        "extract_KE":         False,
        # Champs FEM
        "extract_fields":     False,
        "extract_internal":   False,
        # Onglet Pilotage — Restart
        "use_restart":        False,
        "restart_step":       0,
        # Critere d'arret
        "use_stop_crit":      False,
        "stop_crit_type":     "energy",
        "stop_crit_val":      1e-6,
        "stop_crit_freq":     10,
        # Multi-pas
        "use_multi_step":     False,
        "multi_step_nb":      3,
        "multi_step_sizes":   "1e-3, 1e-4, 1e-5",
    }

    def __init__(
        self,
        current_params: Optional[Dict[str, Any]] = None,
        controller=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configuration des routines chipy")
        self.resize(800, 700)
        self.controller = controller

        self._params: Dict[str, Any] = dict(self.DEFAULTS)
        if current_params:
            self._params.update(
                {k: v for k, v in current_params.items() if k in self.DEFAULTS}
            )

        self._build_ui()
        self._load()
        self._wire()
        self._auto_detect()

    # =========================================================================
    # Construction de l'interface
    # =========================================================================

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._tab_model(),    "Modele")
        self._tabs.addTab(self._tab_routines(), "Routines")
        self._tabs.addTab(self._tab_extract(),  "Extraction")
        self._tabs.addTab(self._tab_pilot(),    "Pilotage")
        root.addWidget(self._tabs, stretch=1)

        btn_preview = QPushButton("Apercu du script command.py")
        btn_preview.setToolTip(
            "Genere et affiche le script de calcul avec les options courantes."
        )
        btn_preview.clicked.connect(self._show_preview)
        root.addWidget(btn_preview)

        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        box.accepted.connect(self._on_accept)
        box.rejected.connect(self.reject)
        box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        ).clicked.connect(self._on_restore_defaults)
        root.addWidget(box)

    # ── Onglet 1 : Modele ─────────────────────────────────────────────────────

    def _tab_model(self) -> QWidget:
        w = QWidget()
        vb = QVBoxLayout(w)
        vb.setSpacing(10)

        # Hypothese mecanique
        grp_h = _section("Hypothese mecanique  (mhyp)")
        vb_h = QVBoxLayout()
        self._rb_cp = QRadioButton("Contraintes planes       (mhyp = 1)  -- 2D")
        self._rb_dp = QRadioButton("Deformations planes      (mhyp = 2)  -- 2D")
        self._rb_3d = QRadioButton("Tridimensionnel          (mhyp = 3)  -- 3D")
        self._mhyp_grp = QButtonGroup(self)
        for rb in (self._rb_cp, self._rb_dp, self._rb_3d):
            self._mhyp_grp.addButton(rb)
            vb_h.addWidget(rb)
        vb_h.addWidget(_note(
            "La dimension du projet est detectee automatiquement. "
            "mhyp est pertinent uniquement en 2D."
        ))
        grp_h.setLayout(vb_h)
        vb.addWidget(grp_h)

        # Corps deformables
        grp_d = _section("Corps deformables")
        fl_d = QFormLayout()
        self._cb_deformable = _cb(
            "Activer les corps deformables  (ReadDatbox deformable=True)",
            tip="Active le chargement et le calcul des corps deformables "
                "(MESH_DEFORMABLE). Active mecaFEMx automatiquement si MECAx.",
        )
        fl_d.addRow(self._cb_deformable)

        self._combo_phys = QComboBox()
        self._combo_phys.addItems([
            "MECAx  -- Mecanique des solides",
            "THERx  -- Thermique",
            "HYDRx  -- Hydraulique",
            "THMx   -- Thermo-hydraulique-mecanique",
        ])
        fl_d.addRow("Physique FEM :", self._combo_phys)

        self._dspin_rloc = QDoubleSpinBox()
        self._dspin_rloc.setRange(1e-8, 1.0)
        self._dspin_rloc.setDecimals(4)
        self._dspin_rloc.setSingleStep(1e-3)
        self._dspin_rloc.setValue(5e-2)
        self._dspin_rloc.setToolTip(
            "Tolerance sur les efforts de contact pour la reprise de Rloc. "
            "Typiquement 5e-2."
        )
        fl_d.addRow("Rloc_tol :", self._dspin_rloc)
        grp_d.setLayout(fl_d)
        vb.addWidget(grp_d)

        # Resume projet
        grp_info = _section("Resume du projet (detection automatique)")
        vb_info = QVBoxLayout()
        self._lbl_info = QLabel("(aucun projet charge)")
        self._lbl_info.setWordWrap(True)
        self._lbl_info.setStyleSheet(
            "font-family: monospace; font-size: 8pt;"
            "background:#f0f4f8; padding:8px; border-radius:4px;"
        )
        vb_info.addWidget(self._lbl_info)
        grp_info.setLayout(vb_info)
        vb.addWidget(grp_info)

        vb.addStretch()
        return _scroll(w)

    # ── Onglet 2 : Routines ───────────────────────────────────────────────────

    def _tab_routines(self) -> QWidget:
        w = QWidget()
        vb = QVBoxLayout(w)
        vb.setSpacing(10)

        # Corps rigides 2D
        grp_r2d = _section("Corps rigides 2D  --  RBDY2")
        vb_r2d = QVBoxLayout()
        self._cb_RBDY2 = _cb(
            "Activer RBDY2  (NewStep / FreeVelocity / WriteOut)",
            checked=True,
            tip="Routines obligatoires pour tout corps rigide 2D.",
        )
        vb_r2d.addWidget(self._cb_RBDY2)
        grp_r2d.setLayout(vb_r2d)
        vb.addWidget(grp_r2d)

        # Corps rigides 3D
        grp_r3d = _section("Corps rigides 3D  --  RBDY3")
        vb_r3d = QVBoxLayout()
        self._cb_RBDY3 = _cb(
            "Activer RBDY3  (NewStep / FreeVelocity / WriteOut)",
            tip="Routines obligatoires pour tout corps rigide 3D.",
        )
        vb_r3d.addWidget(self._cb_RBDY3)
        grp_r3d.setLayout(vb_r3d)
        vb.addWidget(grp_r3d)

        # Detecteurs contact 2D
        grp_t2d = _section("Detecteurs de contact 2D")
        vb_t2d = QVBoxLayout()
        self._cb_DKDKx  = _cb("DKDKx   -- Disque / Disque",    checked=True)
        self._cb_DKJCx  = _cb("DKJCx   -- Disque / Jonc")
        self._cb_DKKDx  = _cb("DKKDx   -- Disque / Polygone")
        self._cb_PLPLx  = _cb("PLPLx   -- Plan / Plan")
        self._cb_CLALp  = _cb(
            "CLALp   -- Ligne / Ligne  (maconnerie)",
            tip="Detecteur pour les interfaces de briques (CLALp).",
        )
        self._cb_ALpALp = _cb("ALpALp  -- Ligne / Ligne (ALp)")
        for c in (self._cb_DKDKx, self._cb_DKJCx, self._cb_DKKDx,
                  self._cb_PLPLx, self._cb_CLALp, self._cb_ALpALp):
            vb_t2d.addWidget(c)
        grp_t2d.setLayout(vb_t2d)
        vb.addWidget(grp_t2d)

        # Detecteurs contact 3D
        grp_t3d = _section("Detecteurs de contact 3D")
        vb_t3d = QVBoxLayout()
        self._cb_SPSPx = _cb("SPSPx   -- Sphere / Sphere")
        self._cb_SPCDx = _cb("SPCDx   -- Sphere / Cylindre")
        self._cb_SPPLx = _cb("SPPLx   -- Sphere / Plan")
        self._cb_CDCDx = _cb("CDCDx   -- Cylindre / Cylindre")
        self._cb_CDPLx = _cb("CDPLx   -- Cylindre / Plan")
        self._cb_PRPRx = _cb("PRPRx   -- Polyedre / Polyedre")
        for c in (self._cb_SPSPx, self._cb_SPCDx, self._cb_SPPLx,
                  self._cb_CDCDx, self._cb_CDPLx, self._cb_PRPRx):
            vb_t3d.addWidget(c)
        grp_t3d.setLayout(vb_t3d)
        vb.addWidget(grp_t3d)

        # Deformables
        grp_fem = _section("Corps deformables  --  Routines FEM")
        vb_fem = QVBoxLayout()
        self._cb_mecaFEM = _cb(
            "mecaFEMx  -- Mecanique  (assembly / Fint / Fext / K / ComputeDof)",
            tip="Active l'assemblage et le calcul des forces internes mecaniques.",
        )
        self._cb_therFEM = _cb(
            "therFEMx  -- Thermique  (flux / bilan thermique / ComputeDof)",
            tip="Active les routines de diffusion thermique par elements finis.",
        )
        self._cb_hydrFEM = _cb(
            "hydrFEMx  -- Hydraulique  (pression / flux fluide / ComputeDof)",
            tip="Active les routines de pression hydraulique par elements finis.",
        )
        for c in (self._cb_mecaFEM, self._cb_therFEM, self._cb_hydrFEM):
            vb_fem.addWidget(c)
        grp_fem.setLayout(vb_fem)
        vb.addWidget(grp_fem)

        # Contacteurs mixtes
        grp_mix = _section("Contacteurs mixtes  --  Rigide / Deformable")
        vb_mix = QVBoxLayout()
        self._cb_DKMECAx  = _cb(
            "DKMECAx   -- Disque rigide / Meca FEM 2D",
            tip="Interaction entre disques rigides et elements finis mecaniques 2D.",
        )
        self._cb_ALpMECAx = _cb(
            "ALpMECAx  -- CLALp (maconnerie) / Meca FEM 2D",
            tip="Interaction interfaces maconnerie et elements finis mecaniques.",
        )
        self._cb_SPMECAx  = _cb(
            "SPMECAx   -- Sphere rigide / Meca FEM 3D",
            tip="Interaction entre spheres rigides et elements finis mecaniques 3D.",
        )
        for c in (self._cb_DKMECAx, self._cb_ALpMECAx, self._cb_SPMECAx):
            vb_mix.addWidget(c)
        grp_mix.setLayout(vb_mix)
        vb.addWidget(grp_mix)

        # Routines speciales
        grp_spe = _section("Routines speciales")
        vb_spe = QVBoxLayout()
        self._cb_PT2Dx = _cb(
            "PT2Dx   -- Noeuds ponctuels 2D  (cables, barres elastiques)",
            tip="Interaction point/point 2D pour ELASTIC_WIRE, ELASTIC_ROD, etc.",
        )
        self._cb_PT3Dx = _cb(
            "PT3Dx   -- Noeuds ponctuels 3D",
            tip="Interaction point/point 3D.",
        )
        self._cb_NODES = _cb(
            "NODES   -- Noeuds couples  (DOF couples, COUPLED_DOF)",
            tip="Routines de couplage de degres de liberte entre noeuds.",
        )
        self._cb_bulk = _cb(
            "UpdateBulkBehav  -- Lois de comportement volumique",
            tip="Appel a chipy.UpdateBulkBehav() pour les lois plastiques, "
                "d'endommagement, etc.",
        )
        for c in (self._cb_PT2Dx, self._cb_PT3Dx, self._cb_NODES, self._cb_bulk):
            vb_spe.addWidget(c)
        grp_spe.setLayout(vb_spe)
        vb.addWidget(grp_spe)

        vb.addStretch()
        return _scroll(w)

    # ── Onglet 3 : Extraction ─────────────────────────────────────────────────

    def _tab_extract(self) -> QWidget:
        w = QWidget()
        vb = QVBoxLayout(w)
        vb.setSpacing(10)

        # ── 1. Logs chipy ─────────────────────────────────────────────────────
        grp_log = _section("Messages chipy  (logs)")
        vb_log = QVBoxLayout()
        self._cb_disable_log = _cb(
            "Desactiver les messages chipy  (utilities_DisableLogMes)",
            tip=(
                "Appelle chipy.utilities_DisableLogMes() apres Initialize(). "
                "Supprime tous les messages de progression dans la console. "
                "Utile en production ou pour les calculs tres longs."
            ),
        )
        vb_log.addWidget(self._cb_disable_log)
        grp_log.setLayout(vb_log)
        vb.addWidget(grp_log)

        # ── 2. Visualisation ──────────────────────────────────────────────────
        grp_vis = _section("Visualisation  (WriteDisplayFiles)")
        vb_vis = QVBoxLayout()
        self._cb_vRBDY2    = _cb("RBDY2_WriteDisplayFiles  -- Corps rigides 2D",
                                  checked=True)
        self._cb_vRBDY3    = _cb("RBDY3_WriteDisplayFiles  -- Corps rigides 3D")
        self._cb_vMeca     = _cb("mecaFEMx_WriteDisplayFiles  -- Deformables mecanique")
        self._cb_vTher     = _cb("therFEMx_WriteDisplayFiles  -- Deformables thermique")
        self._cb_vHydr     = _cb("hydrFEMx_WriteDisplayFiles  -- Deformables hydraulique")
        self._cb_disp_loop = _cb(
            "Ecrire les fichiers display dans la boucle de calcul",
            checked=True,
            tip=(
                "Decocher pour n'ecrire qu'une seule fois a la fin du calcul. "
                "Utile pour les grands calculs."
            ),
        )
        for c in (self._cb_vRBDY2, self._cb_vRBDY3, self._cb_vMeca,
                  self._cb_vTher, self._cb_vHydr, self._cb_disp_loop):
            vb_vis.addWidget(c)
        grp_vis.setLayout(vb_vis)
        vb.addWidget(grp_vis)

        # ── 3. Visibilite des avatars ─────────────────────────────────────────
        grp_visi = _section("Visibilite des avatars  (SetVisible / SetInvisible)")
        fl_visi = QFormLayout()

        # Chaque entree : label + QLineEdit IDs + bouton picker
        # IDs = numeros 1-bases dans l'ordre des avatars du projet
        self._edit_vis2_vis   = QLineEdit()
        self._edit_vis2_invis = QLineEdit()
        self._edit_vis3_vis   = QLineEdit()
        self._edit_vis3_invis = QLineEdit()

        _vis_entries = [
            ("RBDY2_SetVisible   (IDs avatars 2D a rendre visibles) :",
             self._edit_vis2_vis,   "2D", "visible"),
            ("RBDY2_SetInvisible (IDs avatars 2D a rendre invisibles) :",
             self._edit_vis2_invis, "2D", "invisible"),
            ("RBDY3_SetVisible   (IDs avatars 3D a rendre visibles) :",
             self._edit_vis3_vis,   "3D", "visible"),
            ("RBDY3_SetInvisible (IDs avatars 3D a rendre invisibles) :",
             self._edit_vis3_invis, "3D", "invisible"),
        ]
        for lbl_txt, edit, dim_str, action in _vis_entries:
            edit.setPlaceholderText("Ex : 1, 3, 5  (IDs separes par virgules)")
            edit.setToolTip(
                "Entrez les IDs des avatars {} (numerotation 1-based, "
                "ordre de creation dans le projet). "
                "Laisser vide pour desactiver cet appel.".format(dim_str)
            )
            row = QHBoxLayout()
            row.addWidget(edit, stretch=1)
            btn = QPushButton("Choisir...")
            btn.setMaximumWidth(90)
            btn.setToolTip("Ouvre la liste des avatars du projet pour selectionner les IDs.")
            # Capturer edit et dim_str dans la closure
            def _make_handler(e=edit, d=dim_str):
                return lambda: self._pick_avatar_ids(e, d)
            btn.clicked.connect(_make_handler())
            row.addWidget(btn)
            fl_visi.addRow(lbl_txt, row)

        fl_visi.addRow(_note(
            "chipy.RBDY2_SetVisible(id) / chipy.RBDY2_SetInvisible(id) "
            "sont appeles avant la boucle, une fois par ID. "
            "L'ID est le numero 1-base de l'avatar dans le projet. "
            "Laisser un champ vide desactive l'appel correspondant."
        ))
        grp_visi.setLayout(fl_visi)
        vb.addWidget(grp_visi)

        # ── 4. GetBodyVector RBDY2 ────────────────────────────────────────────
        grp_gbv2 = _section(
            "Extraction vecteurs d'etat RBDY2  (RBDY2_GetBodyVector)"
        )
        grp_gbv2.setToolTip(
            "chipy.RBDY2_GetBodyVector('NomVecteur') retourne un tableau numpy "
            "pour tous les corps rigides 2D. Le resultat est ecrit dans POSTPRO/."
        )
        fl_gbv2 = QFormLayout()
        self._gbv2_checks: Dict[str, QCheckBox] = {}
        self._gbv2_spins:  Dict[str, QSpinBox]  = {}

        for vec, desc in _GBV_VECTORS_2D:
            row = QHBoxLayout()
            cb = _cb(
                "{:<18}  {}".format(vec, desc),
                tip="chipy.RBDY2_GetBodyVector('{}')  --  {}".format(vec, desc),
            )
            self._gbv2_checks[vec] = cb

            spin = QSpinBox()
            spin.setRange(1, 100_000)
            spin.setValue(1)
            spin.setMaximumWidth(90)
            spin.setToolTip("Ecrire {} tous les N pas de temps.".format(vec))
            spin.setEnabled(False)
            self._gbv2_spins[vec] = spin

            cb.toggled.connect(spin.setEnabled)
            row.addWidget(cb, stretch=1)
            row.addWidget(QLabel("  tous les"))
            row.addWidget(spin)
            row.addWidget(QLabel("pas"))
            fl_gbv2.addRow(row)

        fl_gbv2.addRow(_note(
            "Vecteurs disponibles : Coor, Velo, Fext, Reac, Acce, RigidBodyMass. "
            "Chaque vecteur est ecrit dans un fichier separe dans POSTPRO/."
        ))
        grp_gbv2.setLayout(fl_gbv2)
        vb.addWidget(grp_gbv2)

        # ── 5. GetBodyVector RBDY3 ────────────────────────────────────────────
        grp_gbv3 = _section(
            "Extraction vecteurs d'etat RBDY3  (RBDY3_GetBodyVector)"
        )
        grp_gbv3.setToolTip(
            "chipy.RBDY3_GetBodyVector('NomVecteur') retourne un tableau numpy "
            "pour tous les corps rigides 3D."
        )
        fl_gbv3 = QFormLayout()
        self._gbv3_checks: Dict[str, QCheckBox] = {}
        self._gbv3_spins:  Dict[str, QSpinBox]  = {}

        for vec, desc in _GBV_VECTORS_3D:
            row = QHBoxLayout()
            cb = _cb(
                "{:<18}  {}".format(vec, desc),
                tip="chipy.RBDY3_GetBodyVector('{}')  --  {}".format(vec, desc),
            )
            self._gbv3_checks[vec] = cb

            spin = QSpinBox()
            spin.setRange(1, 100_000)
            spin.setValue(1)
            spin.setMaximumWidth(90)
            spin.setToolTip("Ecrire {} tous les N pas de temps.".format(vec))
            spin.setEnabled(False)
            self._gbv3_spins[vec] = spin

            cb.toggled.connect(spin.setEnabled)
            row.addWidget(cb, stretch=1)
            row.addWidget(QLabel("  tous les"))
            row.addWidget(spin)
            row.addWidget(QLabel("pas"))
            fl_gbv3.addRow(row)

        fl_gbv3.addRow(_note(
            "Vecteurs disponibles : Coor (x,y,z,q0..q3), Velo, Fext, Reac, "
            "Acce, RigidBodyMass. Chaque vecteur est ecrit dans POSTPRO/."
        ))
        grp_gbv3.setLayout(fl_gbv3)
        vb.addWidget(grp_gbv3)

        # ── 6. Forces de contact ──────────────────────────────────────────────
        grp_frc = _section("Forces et reactions de contact")
        vb_frc = QVBoxLayout()
        self._cb_Rnod = _cb(
            "Forces nodales         (inter_handler_Rnod)",
            tip="Extrait les forces nodales aux points de contact dans POSTPRO/.",
        )
        self._cb_Vloc = _cb(
            "Vitesses locales       (inter_handler_Vloc)",
            tip="Extrait les vitesses relatives dans le repere local de contact.",
        )
        self._cb_Rloc = _cb(
            "Forces locales         (inter_handler_Rloc)",
            tip="Extrait les impulsions/forces dans le repere local de contact.",
        )
        for c in (self._cb_Rnod, self._cb_Vloc, self._cb_Rloc):
            vb_frc.addWidget(c)
        grp_frc.setLayout(vb_frc)
        vb.addWidget(grp_frc)

        # ── 7. Energie ────────────────────────────────────────────────────────
        grp_nrj = _section("Energie")
        vb_nrj = QVBoxLayout()
        self._cb_energy = _cb(
            "Bilan energetique global  (ComputeEnergy + WriteEnergy)",
            tip=(
                "Calcule et ecrit l'energie totale : "
                "cinetique + potentielle + dissipee par friction."
            ),
        )
        self._cb_KE = _cb(
            "Energie cinetique RBDY2  (RBDY2_KineticEnergy)",
            tip="Ecrit l'energie cinetique de chaque corps rigide 2D.",
        )
        for c in (self._cb_energy, self._cb_KE):
            vb_nrj.addWidget(c)
        grp_nrj.setLayout(vb_nrj)
        vb.addWidget(grp_nrj)

        # ── 8. Champs FEM ─────────────────────────────────────────────────────
        grp_fld = _section(
            "Champs FEM  (contraintes, deformations, temperature...)"
        )
        vb_fld = QVBoxLayout()
        self._cb_fields = _cb(
            "Champs par element        (mecaFEMx_WriteBodies)",
            tip=(
                "Ecrit les champs par element : contraintes et deformations "
                "(MECAx), temperature (THERx), pression (HYDRx)."
            ),
        )
        self._cb_internal = _cb(
            "Variables internes        (mecaFEMx_WriteInternalVariables)",
            tip=(
                "Ecrit les variables internes aux points de Gauss : "
                "plasticite, endommagement, variables d'histoire."
            ),
        )
        vb_fld.addWidget(self._cb_fields)
        vb_fld.addWidget(self._cb_internal)
        vb_fld.addWidget(_note(
            "Ces extractions ne sont actives que si "
            "'mecaFEMx' est coche dans l'onglet Routines."
        ))
        grp_fld.setLayout(vb_fld)
        vb.addWidget(grp_fld)

        vb.addStretch()
        return _scroll(w)

    # ── Onglet 4 : Pilotage ───────────────────────────────────────────────────

    def _tab_pilot(self) -> QWidget:
        w = QWidget()
        vb = QVBoxLayout(w)
        vb.setSpacing(10)

        # Restart
        grp_rs = _section("Restart  --  Reprise de calcul")
        fl_rs = QFormLayout()
        self._cb_restart = _cb(
            "Activer le restart",
            tip=(
                "Charge l'etat depuis les fichiers .dat.last "
                "d'un calcul precedent avant de demarrer la boucle."
            ),
        )
        fl_rs.addRow(self._cb_restart)
        self._spin_rs_step = QSpinBox()
        self._spin_rs_step.setRange(0, 9_999_999)
        self._spin_rs_step.setValue(0)
        self._spin_rs_step.setEnabled(False)
        self._spin_rs_step.setToolTip(
            "Numero du pas de temps a partir duquel reprendre."
        )
        fl_rs.addRow("Pas de reprise :", self._spin_rs_step)
        fl_rs.addRow(_note(
            "Genere :  chipy.ReadIni()  +  chipy.SetStep(restart_step) "
            "avant la boucle de calcul."
        ))
        grp_rs.setLayout(fl_rs)
        vb.addWidget(grp_rs)

        # Critere d'arret
        grp_sc = _section("Critere d'arret automatique")
        fl_sc = QFormLayout()
        self._cb_stop = _cb(
            "Activer un critere d'arret",
            tip=(
                "Interrompt le calcul avant la fin des pas "
                "si le critere est satisfait."
            ),
        )
        fl_sc.addRow(self._cb_stop)
        self._combo_stop_type = QComboBox()
        self._combo_stop_type.addItems([
            "Energie residuelle      ||E_res|| < seuil",
            "Deplacement max         max|u|   < seuil",
            "Residu de force         ||F_res|| < seuil",
        ])
        self._combo_stop_type.setEnabled(False)
        fl_sc.addRow("Type de critere :", self._combo_stop_type)
        self._dspin_stop_val = QDoubleSpinBox()
        self._dspin_stop_val.setRange(1e-16, 1.0)
        self._dspin_stop_val.setDecimals(2)
        self._dspin_stop_val.setValue(1e-6)
        self._dspin_stop_val.setSingleStep(1e-7)
        self._dspin_stop_val.setEnabled(False)
        fl_sc.addRow("Seuil :", self._dspin_stop_val)
        self._spin_stop_freq = QSpinBox()
        self._spin_stop_freq.setRange(1, 100_000)
        self._spin_stop_freq.setValue(10)
        self._spin_stop_freq.setEnabled(False)
        self._spin_stop_freq.setToolTip("Evaluer le critere tous les N pas.")
        fl_sc.addRow("Frequence d'evaluation (pas) :", self._spin_stop_freq)
        grp_sc.setLayout(fl_sc)
        vb.addWidget(grp_sc)

        # Multi-pas
        grp_mp = _section("Sequence multi-pas  --  dt variable")
        fl_mp = QFormLayout()
        self._cb_multi = _cb(
            "Activer une sequence de pas de temps variables",
            tip=(
                "Definit plusieurs phases de calcul avec des dt differents. "
                "Genere une boucle externe sur les phases."
            ),
        )
        fl_mp.addRow(self._cb_multi)
        self._spin_mp_nb = QSpinBox()
        self._spin_mp_nb.setRange(2, 20)
        self._spin_mp_nb.setValue(3)
        self._spin_mp_nb.setEnabled(False)
        fl_mp.addRow("Nombre de phases :", self._spin_mp_nb)
        self._edit_mp_sizes = QLineEdit("1e-3, 1e-4, 1e-5")
        self._edit_mp_sizes.setPlaceholderText(
            "Ex : 1e-3, 1e-4, 1e-5  (un dt par phase, separes par virgules)"
        )
        self._edit_mp_sizes.setEnabled(False)
        fl_mp.addRow("dt par phase :", self._edit_mp_sizes)
        fl_mp.addRow(_note(
            "nb_steps est reparti equitablement entre les phases. "
            "Genere :  for _dt in dt_sequence: "
            "chipy.TimeEvolution_SetTimeStep(_dt) + boucle interne."
        ))
        grp_mp.setLayout(fl_mp)
        vb.addWidget(grp_mp)

        vb.addStretch()
        return _scroll(w)

    # =========================================================================
    # Chargement initial des widgets depuis _params
    # =========================================================================

    def _load(self):
        p = self._params

        # Modele
        {1: self._rb_cp, 2: self._rb_dp}.get(p["mhyp"], self._rb_3d).setChecked(True)
        self._cb_deformable.setChecked(p["deformable"])
        self._combo_phys.setCurrentIndex(
            {"MECAx": 0, "THERx": 1, "HYDRx": 2, "THMx": 3}.get(p["physics"], 0)
        )
        self._dspin_rloc.setValue(p["Rloc_tol"])

        # Routines (mapping attr -> cle)
        for attr, key in {
            "_cb_RBDY2":    "use_RBDY2",    "_cb_RBDY3":    "use_RBDY3",
            "_cb_DKDKx":    "use_DKDKx",    "_cb_DKJCx":    "use_DKJCx",
            "_cb_DKKDx":    "use_DKKDx",    "_cb_PLPLx":    "use_PLPLx",
            "_cb_CLALp":    "use_CLALp",    "_cb_ALpALp":   "use_ALpALp",
            "_cb_SPSPx":    "use_SPSPx",    "_cb_SPCDx":    "use_SPCDx",
            "_cb_SPPLx":    "use_SPPLx",    "_cb_CDCDx":    "use_CDCDx",
            "_cb_CDPLx":    "use_CDPLx",    "_cb_PRPRx":    "use_PRPRx",
            "_cb_mecaFEM":  "use_mecaFEM",  "_cb_therFEM":  "use_therFEM",
            "_cb_hydrFEM":  "use_hydrFEM",
            "_cb_DKMECAx":  "use_DKMECAx",  "_cb_ALpMECAx": "use_ALpMECAx",
            "_cb_SPMECAx":  "use_SPMECAx",
            "_cb_PT2Dx":    "use_PT2Dx",    "_cb_PT3Dx":    "use_PT3Dx",
            "_cb_NODES":    "use_NODES",    "_cb_bulk":     "use_bulk_behav",
        }.items():
            getattr(self, attr).setChecked(p.get(key, False))

        # Extraction — cases simples
        for attr, key in {
            "_cb_disable_log":  "disable_log",
            "_cb_vRBDY2":       "visu_RBDY2",     "_cb_vRBDY3":    "visu_RBDY3",
            "_cb_vMeca":        "visu_mecaFEM",   "_cb_vTher":     "visu_therFEM",
            "_cb_vHydr":        "visu_hydrFEM",   "_cb_disp_loop": "display_in_loop",
            # visibilite : gestion separee via QLineEdit
            "_cb_Rnod":         "extract_Rnod",   "_cb_Vloc":      "extract_Vloc",
            "_cb_Rloc":         "extract_Rloc",   "_cb_energy":    "extract_energy",
            "_cb_KE":           "extract_KE",     "_cb_fields":    "extract_fields",
            "_cb_internal":     "extract_internal",
        }.items():
            getattr(self, attr).setChecked(p.get(key, False))

        # Visibilite — QLineEdit
        self._edit_vis2_vis.setText(p.get("vis_RBDY2_visible", ""))
        self._edit_vis2_invis.setText(p.get("vis_RBDY2_invisible", ""))
        self._edit_vis3_vis.setText(p.get("vis_RBDY3_visible", ""))
        self._edit_vis3_invis.setText(p.get("vis_RBDY3_invisible", ""))

        # GetBodyVector RBDY2/3
        for vec, _ in _GBV_VECTORS_2D:
            self._gbv2_checks[vec].setChecked(p.get("gbv2_{}".format(vec), False))
            self._gbv2_spins[vec].setValue(p.get("gbv2_{}_freq".format(vec), 1))
            self._gbv2_spins[vec].setEnabled(p.get("gbv2_{}".format(vec), False))
        for vec, _ in _GBV_VECTORS_3D:
            self._gbv3_checks[vec].setChecked(p.get("gbv3_{}".format(vec), False))
            self._gbv3_spins[vec].setValue(p.get("gbv3_{}_freq".format(vec), 1))
            self._gbv3_spins[vec].setEnabled(p.get("gbv3_{}".format(vec), False))

        # Pilotage
        self._cb_restart.setChecked(p["use_restart"])
        self._spin_rs_step.setValue(p["restart_step"])
        self._spin_rs_step.setEnabled(p["use_restart"])
        self._cb_stop.setChecked(p["use_stop_crit"])
        self._combo_stop_type.setCurrentIndex(
            {"energy": 0, "disp_max": 1, "force_res": 2}.get(p["stop_crit_type"], 0)
        )
        self._combo_stop_type.setEnabled(p["use_stop_crit"])
        self._dspin_stop_val.setValue(p["stop_crit_val"])
        self._dspin_stop_val.setEnabled(p["use_stop_crit"])
        self._spin_stop_freq.setValue(p["stop_crit_freq"])
        self._spin_stop_freq.setEnabled(p["use_stop_crit"])
        self._cb_multi.setChecked(p["use_multi_step"])
        self._spin_mp_nb.setValue(p["multi_step_nb"])
        self._spin_mp_nb.setEnabled(p["use_multi_step"])
        self._edit_mp_sizes.setText(p["multi_step_sizes"])
        self._edit_mp_sizes.setEnabled(p["use_multi_step"])

        self._refresh_info()

    # =========================================================================
    # Connexions des signaux
    # =========================================================================

    def _wire(self):
        self._cb_restart.toggled.connect(self._spin_rs_step.setEnabled)
        self._cb_stop.toggled.connect(self._on_stop_toggled)
        self._cb_multi.toggled.connect(self._on_multi_toggled)
        self._rb_3d.toggled.connect(self._on_3d_toggled)
        self._cb_deformable.toggled.connect(self._on_deformable_toggled)
        self._combo_phys.currentIndexChanged.connect(self._on_phys_changed)

    def _on_stop_toggled(self, v: bool):
        self._combo_stop_type.setEnabled(v)
        self._dspin_stop_val.setEnabled(v)
        self._spin_stop_freq.setEnabled(v)

    def _on_multi_toggled(self, v: bool):
        self._spin_mp_nb.setEnabled(v)
        self._edit_mp_sizes.setEnabled(v)

    def _on_3d_toggled(self, is3d: bool):
        self._rb_cp.setEnabled(not is3d)
        self._rb_dp.setEnabled(not is3d)
        for c in (self._cb_DKDKx, self._cb_DKJCx, self._cb_DKKDx,
                  self._cb_PLPLx, self._cb_CLALp, self._cb_ALpALp):
            c.setEnabled(not is3d)
        for c in (self._cb_SPSPx, self._cb_SPCDx, self._cb_SPPLx,
                  self._cb_CDCDx, self._cb_CDPLx, self._cb_PRPRx):
            c.setEnabled(is3d)

    def _on_deformable_toggled(self, v: bool):
        if v:
            self._on_phys_changed(self._combo_phys.currentIndex())

    def _on_phys_changed(self, idx: int):
        if not self._cb_deformable.isChecked():
            return
        self._cb_mecaFEM.setChecked(idx == 0)
        self._cb_therFEM.setChecked(idx == 1)
        self._cb_hydrFEM.setChecked(idx in (2, 3))
        self._cb_vMeca.setChecked(idx == 0)
        self._cb_vTher.setChecked(idx == 1)
        self._cb_vHydr.setChecked(idx in (2, 3))

    # =========================================================================
    # Auto-detection depuis le projet courant
    # =========================================================================

    def _pick_avatar_ids(self, target_edit: "QLineEdit", dim: str):
        """
        Ouvre un dialogue de selection d'avatars du projet.
        Insere les IDs selectionnes (1-bases) dans target_edit.
        dim : "2D" ou "3D" pour filtrer les avatars affichables.
        """
        if self.controller is None:
            QMessageBox.information(
                self,
                "Aucun projet",
                "Ouvrez un projet pour pouvoir selectionner les avatars.",
            )
            return

        from PyQt6.QtWidgets import QListWidget, QListWidgetItem

        avatars = self.controller.state.avatars
        # Filtrer selon la dimension
        _3D_TYPES = {
            "rigidSphere", "rigidPlan", "rigidCylinder",
            "rigidPolyhedron", "roughWall3D", "granuloRoughWall3D",
        }
        _2D_TYPES = {
            "rigidDisk", "rigidJonc", "rigidPolygon", "rigidOvoid",
            "rigidDiscrete", "rigidCluster",
            "roughWall", "fineWall", "smoothWall", "granuloWall",
            "emptyAvatar", "mesh",
        }
        filter_set = _3D_TYPES if dim == "3D" else _2D_TYPES

        # Construire la liste : (id_1based, label)
        items = []
        for i, av in enumerate(avatars, start=1):
            av_type_val = getattr(
                getattr(av, "avatar_type", None), "value", ""
            )
            if av_type_val in filter_set:
                label = "{}  [{}]  type: {}".format(
                    i,
                    getattr(av, "color", ""),
                    av_type_val,
                )
                items.append((i, label))

        if not items:
            QMessageBox.information(
                self,
                "Aucun avatar {}".format(dim),
                "Le projet ne contient aucun avatar de type {}.".format(dim),
            )
            return

        # Dialogue de selection
        dlg = QDialog(self)
        dlg.setWindowTitle("Selectionner les avatars {}".format(dim))
        dlg.resize(420, 380)
        lay = QVBoxLayout(dlg)

        lay.addWidget(_note(
            "Selectionnez un ou plusieurs avatars (Ctrl+clic ou Maj+clic). "
            "L'ID est le numero 1-base dans l'ordre de creation du projet."
        ))

        lw = QListWidget()
        lw.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        for av_id, label in items:
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, av_id)
            lw.addItem(it)

        # Pre-selectionner les IDs deja presents dans le champ
        existing_ids = set()
        for tok in target_edit.text().split(","):
            tok = tok.strip()
            if tok.isdigit():
                existing_ids.add(int(tok))
        for row in range(lw.count()):
            it = lw.item(row)
            if it.data(Qt.ItemDataRole.UserRole) in existing_ids:
                it.setSelected(True)

        lay.addWidget(lw, stretch=1)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected_ids = sorted(
                it.data(Qt.ItemDataRole.UserRole)
                for it in lw.selectedItems()
            )
            target_edit.setText(
                ", ".join(str(i) for i in selected_ids)
            )

    def _auto_detect(self):
        if self.controller is None:
            self._lbl_info.setText("(aucun projet charge)")
            return

        st = self.controller.state
        dim = st.dimension

        if dim == 3:
            self._rb_3d.setChecked(True)
            self._cb_RBDY2.setChecked(False)
            self._cb_RBDY3.setChecked(True)
        else:
            self._rb_cp.setChecked(True)
            self._cb_RBDY2.setChecked(True)
            self._cb_RBDY3.setChecked(False)

        has_def = any(
            av.avatar_type.value == "mesh" for av in st.avatars
        )
        if has_def:
            self._cb_deformable.setChecked(True)
            self._on_phys_changed(self._combo_phys.currentIndex())

        has_masonry = bool(getattr(st, "masonry_patterns", {})) or any(
            getattr(av, "wall_params", None) for av in st.avatars
        )
        if has_masonry:
            self._cb_CLALp.setChecked(True)

        pt_laws  = {"ELASTIC_WIRE", "BRITTLE_ELASTIC_WIRE",
                    "ELASTIC_ROD", "VOIGT_ROD"}
        dof_laws = {"COUPLED_DOF", "NORMAL_COUPLED_DOF"}
        law_types = {
            cl.law_type.value for cl in getattr(st, "contact_laws", [])
        }
        if law_types & pt_laws:
            (self._cb_PT2Dx if dim == 2 else self._cb_PT3Dx).setChecked(True)
        if law_types & dof_laws:
            self._cb_NODES.setChecked(True)

        self._refresh_info()

    def _refresh_info(self):
        if self.controller is None:
            return
        st = self.controller.state
        n_av  = len(st.avatars)
        n_def = sum(1 for av in st.avatars if av.avatar_type.value == "mesh")
        n_mat = len(getattr(st, "materials", []))
        n_mod = len(getattr(st, "models", []))
        n_cl  = len(getattr(st, "contact_laws", []))
        groups = list((getattr(st, "avatar_groups", {}) or {}).keys())
        grp_str = (
            ", ".join(groups[:6]) + ("..." if len(groups) > 6 else "")
        ) if groups else "(aucun)"
        has_mas = bool(getattr(st, "masonry_patterns", {})) or any(
            getattr(av, "wall_params", None) for av in st.avatars
        )
        law_names = [cl.law_type.value for cl in getattr(st, "contact_laws", [])]
        self._lbl_info.setText(
            "Projet       : {}\n"
            "Dimension    : {}D\n"
            "Avatars      : {}  (dont {} deformable(s))\n"
            "Materiaux    : {}   Modeles : {}   Lois contact : {}\n"
            "Maconnerie   : {}\n"
            "Lois actives : {}{}\n"
            "Groupes      : {}".format(
                st.name,
                st.dimension,
                n_av, n_def,
                n_mat, n_mod, n_cl,
                "oui" if has_mas else "non",
                ", ".join(law_names[:5]) or "(aucune)",
                "..." if len(law_names) > 5 else "",
                grp_str,
            )
        )

    # =========================================================================
    # Collecte des parametres
    # =========================================================================

    def get_params(self) -> Dict[str, Any]:
        """
        Retourne le dict complet des parametres configures.
        Fusionnable avec ComputeTab.get_parameters().
        """
        p: Dict[str, Any] = {}

        # Modele
        p["mhyp"] = (
            3 if self._rb_3d.isChecked()
            else (2 if self._rb_dp.isChecked() else 1)
        )
        p["deformable"] = self._cb_deformable.isChecked()
        p["physics"] = ["MECAx", "THERx", "HYDRx", "THMx"][
            self._combo_phys.currentIndex()
        ]
        p["Rloc_tol"] = self._dspin_rloc.value()

        # Routines
        for attr, key in {
            "_cb_RBDY2":    "use_RBDY2",    "_cb_RBDY3":    "use_RBDY3",
            "_cb_DKDKx":    "use_DKDKx",    "_cb_DKJCx":    "use_DKJCx",
            "_cb_DKKDx":    "use_DKKDx",    "_cb_PLPLx":    "use_PLPLx",
            "_cb_CLALp":    "use_CLALp",    "_cb_ALpALp":   "use_ALpALp",
            "_cb_SPSPx":    "use_SPSPx",    "_cb_SPCDx":    "use_SPCDx",
            "_cb_SPPLx":    "use_SPPLx",    "_cb_CDCDx":    "use_CDCDx",
            "_cb_CDPLx":    "use_CDPLx",    "_cb_PRPRx":    "use_PRPRx",
            "_cb_mecaFEM":  "use_mecaFEM",  "_cb_therFEM":  "use_therFEM",
            "_cb_hydrFEM":  "use_hydrFEM",
            "_cb_DKMECAx":  "use_DKMECAx",  "_cb_ALpMECAx": "use_ALpMECAx",
            "_cb_SPMECAx":  "use_SPMECAx",
            "_cb_PT2Dx":    "use_PT2Dx",    "_cb_PT3Dx":    "use_PT3Dx",
            "_cb_NODES":    "use_NODES",    "_cb_bulk":     "use_bulk_behav",
        }.items():
            p[key] = getattr(self, attr).isChecked()

        # Extraction — cases simples
        for attr, key in {
            "_cb_disable_log":  "disable_log",
            "_cb_vRBDY2":       "visu_RBDY2",     "_cb_vRBDY3":    "visu_RBDY3",
            "_cb_vMeca":        "visu_mecaFEM",   "_cb_vTher":     "visu_therFEM",
            "_cb_vHydr":        "visu_hydrFEM",   "_cb_disp_loop": "display_in_loop",
            # visibilite : gestion separee via QLineEdit
            "_cb_Rnod":         "extract_Rnod",   "_cb_Vloc":      "extract_Vloc",
            "_cb_Rloc":         "extract_Rloc",   "_cb_energy":    "extract_energy",
            "_cb_KE":           "extract_KE",     "_cb_fields":    "extract_fields",
            "_cb_internal":     "extract_internal",
        }.items():
            p[key] = getattr(self, attr).isChecked()

        # Visibilite — lire les QLineEdit
        p["vis_RBDY2_visible"]   = self._edit_vis2_vis.text().strip()
        p["vis_RBDY2_invisible"] = self._edit_vis2_invis.text().strip()
        p["vis_RBDY3_visible"]   = self._edit_vis3_vis.text().strip()
        p["vis_RBDY3_invisible"] = self._edit_vis3_invis.text().strip()

        # GetBodyVector RBDY2/3
        for vec, _ in _GBV_VECTORS_2D:
            p["gbv2_{}".format(vec)]      = self._gbv2_checks[vec].isChecked()
            p["gbv2_{}_freq".format(vec)] = self._gbv2_spins[vec].value()
        for vec, _ in _GBV_VECTORS_3D:
            p["gbv3_{}".format(vec)]      = self._gbv3_checks[vec].isChecked()
            p["gbv3_{}_freq".format(vec)] = self._gbv3_spins[vec].value()

        # Pilotage
        p["use_restart"]      = self._cb_restart.isChecked()
        p["restart_step"]     = self._spin_rs_step.value()
        p["use_stop_crit"]    = self._cb_stop.isChecked()
        p["stop_crit_type"]   = ["energy", "disp_max", "force_res"][
            self._combo_stop_type.currentIndex()
        ]
        p["stop_crit_val"]    = self._dspin_stop_val.value()
        p["stop_crit_freq"]   = self._spin_stop_freq.value()
        p["use_multi_step"]   = self._cb_multi.isChecked()
        p["multi_step_nb"]    = self._spin_mp_nb.value()
        p["multi_step_sizes"] = self._edit_mp_sizes.text().strip()

        return p

    # =========================================================================
    # Validation a l'acceptation
    # =========================================================================

    def _on_accept(self):
        p = self.get_params()
        errors = []

        if p["use_multi_step"]:
            try:
                sizes = [float(x) for x in p["multi_step_sizes"].split(",")]
                if len(sizes) != p["multi_step_nb"]:
                    errors.append(
                        "{} phases declarees mais {} valeur(s) de dt fournies.".format(
                            p["multi_step_nb"], len(sizes)
                        )
                    )
                if any(s <= 0 for s in sizes):
                    errors.append("Multi-pas : tous les dt doivent etre > 0.")
            except ValueError:
                errors.append(
                    "Multi-pas : format invalide pour les dt "
                    "(exemple valide : 1e-3, 1e-4, 1e-5)."
                )

        if p["deformable"] and not any(
            p.get(k) for k in ("use_mecaFEM", "use_therFEM", "use_hydrFEM")
        ):
            errors.append(
                "Corps deformables actives mais aucune routine FEM "
                "(mecaFEMx / therFEMx / hydrFEMx) n'est cochee dans l'onglet Routines."
            )

        if errors:
            QMessageBox.warning(
                self,
                "Parametres invalides",
                "Les erreurs suivantes ont ete detectees :\n\n"
                + "\n".join("- {}".format(e) for e in errors)
                + "\n\nCorrigez-les avant de valider.",
            )
            return

        self.accept()

    # =========================================================================
    # Restauration des valeurs par defaut
    # =========================================================================

    def _on_restore_defaults(self):
        reply = QMessageBox.question(
            self,
            "Restaurer les valeurs par defaut",
            "Reinitialiser toutes les options chipy aux valeurs par defaut ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._params = dict(self.DEFAULTS)
            self._load()

    # =========================================================================
    # Apercu du script genere
    # =========================================================================

    def _show_preview(self):
        """Genere et affiche l'apercu du script command.py."""
        try:
            from ...utils.compute_script_generator import ComputeScriptGenerator
        except ImportError:
            try:
                from ..utils.compute_script_generator import ComputeScriptGenerator
            except ImportError:
                from compute_script_generator import ComputeScriptGenerator

        preview_params = {
            "dt": 1e-3, "nb_steps": 100, "theta": 0.5,
            "tol": 1.666e-4, "relax": 1.0, "norm": "Quad ",
            "gs_it1": 50, "gs_it2": 1000,
            "solver_type": "Stored_Delassus_Loops         ",
            "freq_write": 10, "freq_display": 10,
        }
        preview_params.update(self.get_params())

        if self.controller is None:
            script = (
                "# Apercu non disponible : aucun projet charge.\n"
                "# Ouvrez ou creez un projet, puis relancez l'apercu.\n"
            )
        else:
            try:
                gen = ComputeScriptGenerator(self.controller)
                script = gen.generate_string(preview_params)
            except Exception as exc:
                import traceback as _tb
                script = (
                    "# Erreur lors de la generation du script :\n"
                    "# {}\n\n".format(exc)
                    + "".join(
                        "# {}\n".format(line)
                        for line in _tb.format_exc().splitlines()
                    )
                )

        dlg = QDialog(self)
        dlg.setWindowTitle("Apercu -- command.py")
        dlg.resize(740, 580)
        lay = QVBoxLayout(dlg)

        te = QTextEdit()
        te.setReadOnly(True)
        te.setFont(QFont("Courier New", 9))
        te.setStyleSheet("background:#1e1e1e; color:#d4d4d4;")
        te.setPlainText(script)
        lay.addWidget(te)

        lbl = QLabel(
            "{} lignes  --  "
            "parametres numeriques indicatifs (apercu uniquement)".format(
                script.count("\n")
            )
        )
        lbl.setStyleSheet("color:#888; font-size:8pt;")
        lay.addWidget(lbl)

        btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn.rejected.connect(dlg.reject)
        lay.addWidget(btn)
        dlg.exec()