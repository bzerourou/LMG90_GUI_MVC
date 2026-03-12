# =============================================================================
# chipy_routines_dialog.py  —  LMGC90_GUI
# =============================================================================
"""\nDialogue de configuration des routines chipy pour la generationdu script de calcul command.py.4 onglets :  1. Modele      — mhyp, deformable, physique FEM, Rloc_tol, info projet  2. Routines    — corps rigides (RBDY2/3), detecteurs 2D/3D, FEM, mixtes,                   routines speciales  3. Extraction  — logs, visualisation, visibilite avatars,                   GetBodyVector RBDY2/3 (6 vecteurs chacun),                   forces de contact, energie, champs FEM  4. Pilotage    — restart, critere d'arret, multi-pas (dt variable)"""

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


# ── Helpers UI ────────────────────────────────────────────────────────────────

def _section(title: str) -> QGroupBox:
    """QGroupBox avec titre en gras et bordure subtile."""
    gb = QGroupBox(title)
    gb.setStyleSheet(
        "QGroupBox {"
        "  font-weight: bold;"
        "  border: 1px solid #b8b8b8;"
        "  border-radius: 4px;"
        "  margin-top: 8px;"
        "  padding-top: 4px;"
        "}"
        "QGroupBox::title {"
        "  subcontrol-origin: margin;"
        "  left: 10px;"
        "  padding: 0 4px;"
        "  color: #2c3e50;"
        "}"
    )
    return gb


def _scroll(widget: QWidget) -> QScrollArea:
    """Enrobe un widget dans un QScrollArea sans cadre."""
    sc = QScrollArea()
    sc.setWidget(widget)
    sc.setWidgetResizable(True)
    sc.setFrameShape(QFrame.Shape.NoFrame)
    return sc


def _cb(label: str, checked: bool = False, tip: str = "") -> QCheckBox:
    """Cree une QCheckBox avec tooltip optionnel."""
    c = QCheckBox(label)
    c.setChecked(checked)
    if tip:
        c.setToolTip(tip)
    return c


def _note(text: str) -> QLabel:
    """Label de note informatif."""
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        "color:#555; font-size:8pt;"
        "background:#f7f7f7; padding:4px 6px; border-radius:3px;"
    )
    return lbl


# =============================================================================
# ChipyRoutinesDialog
# =============================================================================

# Vecteurs d'etat disponibles pour RBDY2 et RBDY3
_GBV_VECTORS = [
    ("Coor0", "Position initiale                 (x0, y0[, z0])"),
    ("Coor_", "Position courante                 (x, y[, z])"),
    ("Coorb", "Position debut de pas             (xb, yb[, zb])"),
    ("Coorm", "Position milieu de pas            (xm, ym[, zm])"),
    ("X____", "Coordonnees generalisees          (x, y, angle[, ...])"),
    ("V____", "Vitesses generalisees             (vx, vy, omega[, ...])"),
    ("Vbeg_", "Vitesses debut de pas             (vxb, vyb[, ...])"),
    ("Vfree", "Vitesses libres (sans contact)    (vxf, vyf[, ...])"),
    ("Fext",  "Forces externes                   (Fx, Fy[, Fz, ...])"),
    ("Fint_", "Forces internes                   (Fix, Fiy[, Fiz, ...])"),
    ("Reac",  "Forces de reaction (contact)      (Rx, Ry[, Rz, ...])"),
    ("Ireac", "Impulsions de reaction             (IRx, IRy[, IRz, ...])"),
]

# Garde les anciennes listes pour compatibilite avec _load/_auto_detect
_GBV_VECTORS_2D = _GBV_VECTORS
_GBV_VECTORS_3D = _GBV_VECTORS


class ChipyRoutinesDialog(QDialog):
    """\n    Dialogue de configuration des routines chipy.    Utilisation :        dlg = ChipyRoutinesDialog(current_params, controller, parent)        if dlg.exec() == QDialog.DialogCode.Accepted:            params = dlg.get_params()    """

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
        # Visibilite — liste d'entrees dynamiques
        # Chaque entree : {"action": "visible"|"invisible",
        #   "dim": "2D"|"3D", "ids": str, "group": str,
        #   "step_mode": "all"|"every_n"|"at_k"|"after",
        #   "step_val": int}
        "vis_entries": [],
        # GetBodyVector RBDY2 — liste d'entrees configurables
        # Chaque entree : {"vec": str, "ids": str, "group": str,
        #   "step_mode": "all"|"every_n"|"at_k",
        #   "step_val": int}  (N pour every_n, k pour at_k)
        "gbv2_entries": [],
        # GetBodyVector RBDY3
        "gbv3_entries": [],
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
        # ── Inspection 2D ────────────────────────────────────────────────────
        # Chaque entree : {"func": str, "ids": str, "group": str,
        #   "step_mode": "all"|"every_n"|"at_k",
        #   "step_val": int, "store": str}
        "insp2d_entries": [],
        # ── Inspection 3D ────────────────────────────────────────────────────
        "insp3d_entries": [],
        # ── Inspection Interactions ───────────────────────────────────────────
        "inspi_entries": [],
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
        self._tabs.addTab(self._tab_insp_2d(),  "Inspect. 2D")
        self._tabs.addTab(self._tab_insp_3d(),  "Inspect. 3D")
        self._tabs.addTab(self._tab_insp_int(), "Inspect. Interact.")
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
        vb_visi = QVBoxLayout()

        # En-tete colonnes
        hdr_vis = QHBoxLayout()
        for _lbl_v, _w_v in [
            ("Action",        110),
            ("Dim.",           50),
            ("IDs avatars",   120),
            ("Groupe",        110),
            ("Mode / Timing", 185),
        ]:
            _lv = QLabel("<b>{}</b>".format(_lbl_v))
            _lv.setFixedWidth(_w_v)
            hdr_vis.addWidget(_lv)
        hdr_vis.addStretch()
        vb_visi.addLayout(hdr_vis)

        # Zone de lignes
        self._vis_rows = []
        self._vis_rows_widget = QWidget()
        self._vis_rows_layout = QVBoxLayout(self._vis_rows_widget)
        self._vis_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._vis_rows_layout.setSpacing(2)
        vb_visi.addWidget(self._vis_rows_widget)

        btn_add_vis = QPushButton("+ Creer une visibilite")
        btn_add_vis.clicked.connect(lambda: self._add_vis_row())
        vb_visi.addWidget(btn_add_vis)
        vb_visi.addWidget(_note(
            "chipy.RBDY2_SetVisible(id) / chipy.RBDY2_SetInvisible(id) appeles avant "
            "ou pendant la boucle selon le mode choisi. "
            "IDs ou groupe : si les deux sont remplis les IDs ont la priorite."
        ))
        grp_visi.setLayout(vb_visi)
        vb.addWidget(grp_visi)

        # ── 4. GetBodyVector RBDY2 ────────────────────────────────────────────
        grp_gbv2 = _section(
            "Extraction vecteurs d'etat RBDY2  (RBDY2_GetBodyVector)"
        )
        grp_gbv2.setToolTip(
            "chipy.RBDY2_GetBodyVector(vecteur, id_avatar) retourne le vecteur "
            "d'etat de l'avatar id. Le script genere une boucle for sur les IDs."
        )
        vb_gbv2 = QVBoxLayout()
        self._gbv2_rows = []

        hdr2 = QHBoxLayout()
        for _lbl, _w in [("Vecteur", 110), ("IDs avatars", 120),
                          ("Groupe", 110), ("Mode / Timing", 185)]:
            _l = QLabel("<b>{}</b>".format(_lbl))
            _l.setFixedWidth(_w)
            hdr2.addWidget(_l)
        hdr2.addStretch()
        vb_gbv2.addLayout(hdr2)

        self._gbv2_rows_widget = QWidget()
        self._gbv2_rows_layout = QVBoxLayout(self._gbv2_rows_widget)
        self._gbv2_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._gbv2_rows_layout.setSpacing(2)
        vb_gbv2.addWidget(self._gbv2_rows_widget)

        btn_add2 = QPushButton("+ Ajouter une extraction RBDY2")
        btn_add2.clicked.connect(lambda: self._add_gbv_row("2D"))
        vb_gbv2.addWidget(btn_add2)
        vb_gbv2.addWidget(_note(
            "Vecteurs : Coor0, Coor_, Coorb, Coorm, X____, V____, Vbeg_, Vfree, "
            "Fext, Fint_, Reac, Ireac.  "
            "Le generateur produit une boucle for sur les IDs ou sur le groupe."
        ))
        grp_gbv2.setLayout(vb_gbv2)
        vb.addWidget(grp_gbv2)

        # ── 5. GetBodyVector RBDY3 ────────────────────────────────────────────
        grp_gbv3 = _section(
            "Extraction vecteurs d'etat RBDY3  (RBDY3_GetBodyVector)"
        )
        grp_gbv3.setToolTip(
            "chipy.RBDY3_GetBodyVector(vecteur, id_avatar) -- memes vecteurs que RBDY2."
        )
        vb_gbv3 = QVBoxLayout()
        self._gbv3_rows = []

        hdr3 = QHBoxLayout()
        for _lbl, _w in [("Vecteur", 110), ("IDs avatars", 120),
                          ("Groupe", 110), ("Mode / Timing", 185)]:
            _l = QLabel("<b>{}</b>".format(_lbl))
            _l.setFixedWidth(_w)
            hdr3.addWidget(_l)
        hdr3.addStretch()
        vb_gbv3.addLayout(hdr3)

        self._gbv3_rows_widget = QWidget()
        self._gbv3_rows_layout = QVBoxLayout(self._gbv3_rows_widget)
        self._gbv3_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._gbv3_rows_layout.setSpacing(2)
        vb_gbv3.addWidget(self._gbv3_rows_widget)

        btn_add3 = QPushButton("+ Ajouter une extraction RBDY3")
        btn_add3.clicked.connect(lambda: self._add_gbv_row("3D"))
        vb_gbv3.addWidget(btn_add3)
        vb_gbv3.addWidget(_note(
            "Memes vecteurs que RBDY2. "
            "Le generateur produit une boucle for sur les IDs ou sur le groupe."
        ))
        grp_gbv3.setLayout(vb_gbv3)
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
    # Catalogues de fonctions chipy pour l'inspection
    # =========================================================================

    # ── Contacteurs 2D : (nom_chipy, description, nb_params)
    # nb_params : 0 = pas d'ID, 1 = ID contacteur, 2 = ID corps
    _INSP2D_FUNCS = [
        # ---- DISKx ---------------------------------------------------------
        ("DISKx_GetNbDISKx",          "Nombre total de contacteurs DISKx",                    0),
        ("DISKx_GetBodyId",           "ID corps RBDY2 du contacteur i",                       1),
        ("DISKx_GetPtrDISKx2BDYTY",   "Index local du contacteur dans son corps RBDY2",       1),
        ("DISKx_GetPtrTactBehav",     "Loi de comportement associee au contacteur i",         1),
        ("DISKx_GetRadius",           "Rayon du disque i",                                    1),
        ("DISKx_GetCoor",             "Coordonnees du centre du disque i",                    1),
        ("DISKx_GetVelocity",         "Vitesse du centre du disque i",                        1),
        # ---- JONCx ---------------------------------------------------------
        ("JONCx_GetNbJONCx",          "Nombre total de contacteurs JONCx (joncs/ellipses)",   0),
        ("JONCx_GetBodyId",           "ID corps RBDY2 du jonc i",                             1),
        ("JONCx_GetPtrJONCx2BDYTY",   "Index local du jonc dans son corps RBDY2",             1),
        ("JONCx_GetPtrTactBehav",     "Loi de comportement associee au jonc i",               1),
        ("JONCx_GetAxes",             "Demi-axes (a, b) du jonc i",                           1),
        ("JONCx_GetCoor",             "Coordonnees du centre du jonc i",                      1),
        # ---- POLYR ---------------------------------------------------------
        ("POLYR_GetNbPOLYR",          "Nombre total de contacteurs POLYR (polygones rigides)", 0),
        ("POLYR_GetBodyId",           "ID corps RBDY2 du polygone i",                         1),
        ("POLYR_GetPtrPOLYR2BDYTY",   "Index local du polygone dans son corps RBDY2",         1),
        ("POLYR_GetPtrTactBehav",     "Loi de comportement associee au polygone i",           1),
        ("POLYR_GetNbVerti",          "Nombre de sommets du polygone i",                      1),
        ("POLYR_GetVerti",            "Coordonnees des sommets du polygone i",                1),
        ("POLYR_GetCoor",             "Coordonnees du centre de reference du polygone i",     1),
        # ---- xKSID (cluster discret) ----------------------------------------
        ("xKSID_GetNbxKSID",          "Nombre total de contacteurs xKSID (disques discrets)", 0),
        ("xKSID_GetBodyId",           "ID corps RBDY2 du contacteur xKSID i",                 1),
        ("xKSID_GetPtrxKSID2BDYTY",   "Index local du xKSID dans son corps RBDY2",            1),
        ("xKSID_GetRadius",           "Rayon du disque discret i",                            1),
        # ---- RBDY2 corps ---------------------------------------------------
        ("RBDY2_GetNbRBDY2",          "Nombre total de corps rigides 2D",                     0),
        ("RBDY2_KineticEnergy",       "Energie cinetique totale (tous corps RBDY2)",           0),
        # ---- PT2Dx noeuds FEM 2D -------------------------------------------
        ("PT2Dx_GetNbPT2Dx",          "Nombre de noeuds contacteurs 2D (FEM)",                0),
        ("PT2Dx_GetBodyId",           "ID du corps FEM parent du noeud i",                    1),
        ("PT2Dx_GetCoor",             "Coordonnees du noeud contacteur 2D i",                 1),
    ]

    # ── Contacteurs 3D
    _INSP3D_FUNCS = [
        # ---- SPHER ---------------------------------------------------------
        ("SPHER_GetNbSPHER",          "Nombre total de contacteurs SPHER (spheres)",           0),
        ("SPHER_GetBodyId",           "ID corps RBDY3 de la sphere i",                         1),
        ("SPHER_GetPtrSPHER2BDYTY",   "Index local de la sphere dans son corps RBDY3",         1),
        ("SPHER_GetPtrTactBehav",     "Loi de comportement associee a la sphere i",            1),
        ("SPHER_GetRadius",           "Rayon de la sphere i",                                  1),
        ("SPHER_GetCoor",             "Coordonnees du centre de la sphere i",                  1),
        ("SPHER_GetVelocity",         "Vitesse du centre de la sphere i",                      1),
        # ---- POLYH ---------------------------------------------------------
        ("POLYH_GetNbPOLYH",          "Nombre total de contacteurs POLYH (polyedres)",         0),
        ("POLYH_GetBodyId",           "ID corps RBDY3 du polyedre i",                          1),
        ("POLYH_GetPtrPOLYH2BDYTY",   "Index local du polyedre dans son corps RBDY3",          1),
        ("POLYH_GetPtrTactBehav",     "Loi de comportement associee au polyedre i",            1),
        ("POLYH_GetNbFaces",          "Nombre de faces du polyedre i",                         1),
        ("POLYH_GetNbVerti",          "Nombre de sommets du polyedre i",                       1),
        ("POLYH_GetVerti",            "Coordonnees des sommets du polyedre i",                 1),
        ("POLYH_GetCoor",             "Coordonnees du centre de reference du polyedre i",      1),
        # ---- CYLND ---------------------------------------------------------
        ("CYLND_GetNbCYLND",          "Nombre total de contacteurs CYLND (cylindres)",         0),
        ("CYLND_GetBodyId",           "ID corps RBDY3 du cylindre i",                          1),
        ("CYLND_GetPtrCYLND2BDYTY",   "Index local du cylindre dans son corps RBDY3",          1),
        ("CYLND_GetPtrTactBehav",     "Loi de comportement associee au cylindre i",            1),
        ("CYLND_GetRadius",           "Rayon du cylindre i",                                   1),
        ("CYLND_GetLength",           "Longueur du cylindre i",                                1),
        ("CYLND_GetCoor",             "Coordonnees du centre du cylindre i",                   1),
        # ---- PLANE 3D (parois planes) ----------------------------------------
        ("PLANE_GetNbPLANE",          "Nombre total de contacteurs PLANE (plans rigides 3D)",  0),
        ("PLANE_GetBodyId",           "ID corps RBDY3 du plan i",                              1),
        ("PLANE_GetNormal",           "Normale unitaire du plan i",                            1),
        ("PLANE_GetCoor",             "Point d'ancrage du plan i",                             1),
        # ---- RBDY3 corps ---------------------------------------------------
        ("RBDY3_GetNbRBDY3",          "Nombre total de corps rigides 3D",                      0),
        # ---- PT3Dx noeuds FEM 3D -------------------------------------------
        ("PT3Dx_GetNbPT3Dx",          "Nombre de noeuds contacteurs 3D (FEM)",                 0),
        ("PT3Dx_GetBodyId",           "ID du corps FEM parent du noeud 3D i",                  1),
        ("PT3Dx_GetCoor",             "Coordonnees du noeud contacteur 3D i",                  1),
    ]

    # ── Interactions (paires de contacteurs)
    _INSPI_FUNCS = [
        # ---- DKDKx (Disque-Disque) -----------------------------------------
        ("DKDKx_GetNbDKDKx",          "Nombre de paires actives Disque-Disque",                0),
        ("DKDKx_GetBodyIds",          "IDs RBDY2 des deux corps de la paire i",                1),
        ("DKDKx_GetTactors",          "IDs des deux contacteurs DISKx de la paire i",          1),
        ("DKDKx_GetGapTT",            "Gap (jeu) de la paire i",                               1),
        ("DKDKx_GetStatusTT",         "Statut de contact de la paire i (0=gap, 1=contact)",    1),
        ("DKDKx_GetRlocTT",           "Reaction locale (Rn, Rt) de la paire i",                1),
        ("DKDKx_GetVlocTT",           "Vitesse locale (Vn, Vt) de la paire i",                 1),
        # ---- DKJCx (Disque-Jonc) --------------------------------------------
        ("DKJCx_GetNbDKJCx",          "Nombre de paires actives Disque-Jonc",                  0),
        ("DKJCx_GetBodyIds",          "IDs RBDY2 des deux corps de la paire i",                1),
        ("DKJCx_GetTactors",          "IDs des deux contacteurs (DISKx, JONCx) de la paire i", 1),
        ("DKJCx_GetGapTT",            "Gap de la paire i",                                     1),
        ("DKJCx_GetStatusTT",         "Statut de contact de la paire i",                       1),
        ("DKJCx_GetRlocTT",           "Reaction locale (Rn, Rt) de la paire i",                1),
        # ---- DKKDx (Disque-Corde) -------------------------------------------
        ("DKKDx_GetNbDKKDx",          "Nombre de paires actives Disque-Corde",                 0),
        ("DKKDx_GetBodyIds",          "IDs RBDY2 des deux corps de la paire i",                1),
        ("DKKDx_GetGapTT",            "Gap de la paire i",                                     1),
        ("DKKDx_GetRlocTT",           "Reaction locale de la paire i",                         1),
        # ---- PLPLx (Polygone-Polygone) ----------------------------------------
        ("PLPLx_GetNbPLPLx",          "Nombre de paires actives Polygone-Polygone",            0),
        ("PLPLx_GetBodyIds",          "IDs RBDY2 des deux corps de la paire i",                1),
        ("PLPLx_GetTactors",          "IDs des deux contacteurs POLYR de la paire i",          1),
        ("PLPLx_GetGapTT",            "Gap de la paire i",                                     1),
        ("PLPLx_GetStatusTT",         "Statut de contact de la paire i",                       1),
        ("PLPLx_GetRlocTT",           "Reaction locale (Rn, Rt) de la paire i",                1),
        ("PLPLx_GetVlocTT",           "Vitesse locale (Vn, Vt) de la paire i",                 1),
        # ---- CLALp (Brique-Brique maconnerie) --------------------------------
        ("CLALp_GetNbCLALp",          "Nombre de paires actives Brique-Brique (maconnerie)",   0),
        ("CLALp_GetBodyIds",          "IDs des deux corps de la paire i",                      1),
        ("CLALp_GetGapTT",            "Gap de la paire i",                                     1),
        ("CLALp_GetStatusTT",         "Statut de contact de la paire i",                       1),
        ("CLALp_GetRlocTT",           "Reaction locale de la paire i",                         1),
        # ---- ALpALp ---------------------------------------------------------
        ("ALpALp_GetNbALpALp",        "Nombre de paires actives ALp-ALp",                     0),
        ("ALpALp_GetBodyIds",         "IDs des deux corps de la paire i",                      1),
        ("ALpALp_GetGapTT",           "Gap de la paire i",                                     1),
        ("ALpALp_GetRlocTT",          "Reaction locale de la paire i",                         1),
        # ---- SPSPx (Sphere-Sphere) -------------------------------------------
        ("SPSPx_GetNbSPSPx",          "Nombre de paires actives Sphere-Sphere",                0),
        ("SPSPx_GetBodyIds",          "IDs RBDY3 des deux corps de la paire i",                1),
        ("SPSPx_GetTactors",          "IDs des deux contacteurs SPHER de la paire i",          1),
        ("SPSPx_GetGapTT",            "Gap de la paire i",                                     1),
        ("SPSPx_GetStatusTT",         "Statut de contact de la paire i",                       1),
        ("SPSPx_GetRlocTT",           "Reaction locale (Rn, Rt, Rs) de la paire i",            1),
        ("SPSPx_GetVlocTT",           "Vitesse locale (Vn, Vt, Vs) de la paire i",             1),
        # ---- SPCDx (Sphere-Cylindre) -----------------------------------------
        ("SPCDx_GetNbSPCDx",          "Nombre de paires actives Sphere-Cylindre",              0),
        ("SPCDx_GetBodyIds",          "IDs RBDY3 des deux corps de la paire i",                1),
        ("SPCDx_GetTactors",          "IDs des contacteurs (SPHER, CYLND) de la paire i",      1),
        ("SPCDx_GetGapTT",            "Gap de la paire i",                                     1),
        ("SPCDx_GetRlocTT",           "Reaction locale de la paire i",                         1),
        # ---- SPPLx (Sphere-Plan) ---------------------------------------------
        ("SPPLx_GetNbSPPLx",          "Nombre de paires actives Sphere-Plan",                  0),
        ("SPPLx_GetBodyIds",          "IDs RBDY3 des deux corps de la paire i",                1),
        ("SPPLx_GetGapTT",            "Gap de la paire i",                                     1),
        ("SPPLx_GetRlocTT",           "Reaction locale de la paire i",                         1),
        # ---- CDCDx (Cylindre-Cylindre) ----------------------------------------
        ("CDCDx_GetNbCDCDx",          "Nombre de paires actives Cylindre-Cylindre",            0),
        ("CDCDx_GetBodyIds",          "IDs RBDY3 des deux corps de la paire i",                1),
        ("CDCDx_GetGapTT",            "Gap de la paire i",                                     1),
        ("CDCDx_GetRlocTT",           "Reaction locale de la paire i",                         1),
        # ---- CDPLx (Cylindre-Plan) -------------------------------------------
        ("CDPLx_GetNbCDPLx",          "Nombre de paires actives Cylindre-Plan",                0),
        ("CDPLx_GetBodyIds",          "IDs RBDY3 des deux corps de la paire i",                1),
        ("CDPLx_GetGapTT",            "Gap de la paire i",                                     1),
        ("CDPLx_GetRlocTT",           "Reaction locale de la paire i",                         1),
        # ---- PRPRx (Polyedre-Polyedre) ----------------------------------------
        ("PRPRx_GetNbPRPRx",          "Nombre de paires actives Polyedre-Polyedre",            0),
        ("PRPRx_GetBodyIds",          "IDs RBDY3 des deux corps de la paire i",                1),
        ("PRPRx_GetTactors",          "IDs des deux contacteurs POLYH de la paire i",          1),
        ("PRPRx_GetGapTT",            "Gap de la paire i",                                     1),
        ("PRPRx_GetStatusTT",         "Statut de contact de la paire i",                       1),
        ("PRPRx_GetRlocTT",           "Reaction locale (Rn, Rt, Rs) de la paire i",            1),
        # ---- DKMECAx / ALpMECAx / SPMECAx (rigide-deformable) ---------------
        ("DKMECAx_GetNbDKMECAx",      "Nombre de paires actives Disque-MECAx (FEM)",           0),
        ("DKMECAx_GetBodyIds",        "IDs des deux corps de la paire i",                      1),
        ("DKMECAx_GetGapTT",          "Gap de la paire i",                                     1),
        ("DKMECAx_GetRlocTT",         "Reaction locale de la paire i",                         1),
        ("ALpMECAx_GetNbALpMECAx",    "Nombre de paires actives ALp-MECAx",                   0),
        ("ALpMECAx_GetBodyIds",       "IDs des deux corps de la paire i",                      1),
        ("ALpMECAx_GetRlocTT",        "Reaction locale de la paire i",                         1),
        ("SPMECAx_GetNbSPMECAx",      "Nombre de paires actives Sphere-MECAx",                 0),
        ("SPMECAx_GetBodyIds",        "IDs des deux corps de la paire i",                      1),
        ("SPMECAx_GetRlocTT",         "Reaction locale de la paire i",                         1),
    ]

    def _make_insp_tab(
        self,
        dim_label: str,
        funcs_catalog: list,
        rows_list_attr: str,
        rows_layout_attr: str,
        add_cb_label: str,
    ) -> "QWidget":
        """
        Construit un onglet d'inspection generique.
        Parametres :
            dim_label        : "2D", "3D" ou "INT"
            funcs_catalog    : liste de tuples (nom_func, description, nb_params)
            rows_list_attr   : nom de l'attribut self._insp??_rows
            rows_layout_attr : nom de l'attribut self._insp??_rows_layout
            add_cb_label     : texte du bouton "Ajouter"
        """
        w = QWidget()
        vb = QVBoxLayout(w)
        vb.setSpacing(6)

        # ── Explication ──────────────────────────────────────────────────────
        note_text = {
            "2D":  ("Fonctions chipy pour inspecter les contacteurs 2D : "
                    "DISKx, JONCx, POLYR, xKSID, PT2Dx, RBDY2. "
                    "Les fonctions sans ID (GetNb...) s'appellent sans argument."),
            "3D":  ("Fonctions chipy pour inspecter les contacteurs 3D : "
                    "SPHER, POLYH, CYLND, PLANE, PT3Dx, RBDY3. "
                    "Les fonctions sans ID (GetNb...) s'appellent sans argument."),
            "INT": ("Fonctions chipy pour inspecter les interactions (paires de contacteurs) : "
                    "DKDKx, DKJCx, DKKDx, PLPLx, CLALp, ALpALp, "
                    "SPSPx, SPCDx, SPPLx, CDCDx, CDPLx, PRPRx, "
                    "DKMECAx, ALpMECAx, SPMECAx. "
                    "ID = index de la paire dans la liste chipy (1-based)."),
        }.get(dim_label, "")
        note_lbl = QLabel(note_text)
        note_lbl.setWordWrap(True)
        note_lbl.setStyleSheet(
            "background:#e8f5e9; padding:6px; border-radius:4px; font-size:8pt;"
        )
        vb.addWidget(note_lbl)

        # ── En-tete colonnes ─────────────────────────────────────────────────
        hdr = QHBoxLayout()
        for lbl_txt, lbl_w in [
            ("Fonction chipy", 230),
            ("IDs (paires/contacteurs)", 145),
            ("Groupe", 110),
            ("Mode / Timing", 185),
            ("Var. Python", 110),
        ]:
            lbl = QLabel("<b>{}</b>".format(lbl_txt))
            lbl.setFixedWidth(lbl_w)
            hdr.addWidget(lbl)
        hdr.addStretch()
        vb.addLayout(hdr)

        # ── Zone de lignes scrollable ─────────────────────────────────────────
        rows_widget = QWidget()
        rows_layout = QVBoxLayout(rows_widget)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(2)

        setattr(self, rows_list_attr,   [])
        setattr(self, rows_layout_attr, rows_layout)

        vb.addWidget(rows_widget)

        # ── Bouton Ajouter ────────────────────────────────────────────────────
        btn_add = QPushButton(add_cb_label)
        btn_add.clicked.connect(
            lambda checked=False, d=dim_label: self._add_insp_row(d)
        )
        vb.addWidget(btn_add)
        vb.addStretch()
        return _scroll(w)

    def _tab_insp_2d(self) -> "QWidget":
        """Onglet inspection contacteurs 2D."""
        return self._make_insp_tab(
            dim_label        = "2D",
            funcs_catalog    = self._INSP2D_FUNCS,
            rows_list_attr   = "_insp2d_rows",
            rows_layout_attr = "_insp2d_rows_layout",
            add_cb_label     = "+ Ajouter une inspection 2D",
        )

    def _tab_insp_3d(self) -> "QWidget":
        """Onglet inspection contacteurs 3D."""
        return self._make_insp_tab(
            dim_label        = "3D",
            funcs_catalog    = self._INSP3D_FUNCS,
            rows_list_attr   = "_insp3d_rows",
            rows_layout_attr = "_insp3d_rows_layout",
            add_cb_label     = "+ Ajouter une inspection 3D",
        )

    def _tab_insp_int(self) -> "QWidget":
        """Onglet inspection interactions (paires)."""
        return self._make_insp_tab(
            dim_label        = "INT",
            funcs_catalog    = self._INSPI_FUNCS,
            rows_list_attr   = "_inspi_rows",
            rows_layout_attr = "_inspi_rows_layout",
            add_cb_label     = "+ Ajouter une inspection interaction",
        )

    def _get_catalog_for_dim(self, dim: str) -> list:
        return {
            "2D":  self._INSP2D_FUNCS,
            "3D":  self._INSP3D_FUNCS,
            "INT": self._INSPI_FUNCS,
        }.get(dim, self._INSP2D_FUNCS)

    def _add_insp_row(self, dim: str, entry: dict = None):
        """
        Ajoute une ligne d'inspection dans l'onglet dim.
        entry : dict optionnel {"func": str, "ids": str, "group": str,
                                "in_loop": bool, "freq": int, "store": str}
        """
        entry = entry or {}
        catalog = self._get_catalog_for_dim(dim)
        func_names = [f[0] for f in catalog]

        _dim_key = {"2D": "2d", "3D": "3d"}.get(dim)
        rows_list   = getattr(self,
            "_insp{}_rows".format(_dim_key) if _dim_key else "_inspi_rows")
        rows_layout = getattr(self,
            "_insp{}_rows_layout".format(_dim_key) if _dim_key else "_inspi_rows_layout")

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)

        # ── ComboBox fonction ─────────────────────────────────────────────────
        combo_func = QComboBox()
        combo_func.setFixedWidth(230)
        for fname, fdesc, _ in catalog:
            combo_func.addItem(fname)
            combo_func.setItemData(
                combo_func.count() - 1, fdesc, 3  # Qt.ToolTipRole = 3
            )
        if entry.get("func") in func_names:
            combo_func.setCurrentText(entry["func"])

        def _update_tip(idx, cb=combo_func, cat=catalog):
            if 0 <= idx < len(cat):
                cb.setToolTip("{} -- {}".format(cat[idx][0], cat[idx][1]))
        combo_func.currentIndexChanged.connect(_update_tip)
        _update_tip(combo_func.currentIndex())
        row_layout.addWidget(combo_func)

        # ── IDs ───────────────────────────────────────────────────────────────
        edit_ids = QLineEdit()
        edit_ids.setFixedWidth(100)
        edit_ids.setPlaceholderText("1, 3, 5")
        edit_ids.setText(entry.get("ids", ""))
        edit_ids.setToolTip(
            "IDs (1-based) des contacteurs ou paires a inspecter. "
            "Laisser vide si la fonction ne prend pas d'ID (GetNb...)."
        )

        btn_pick = QPushButton("...")
        btn_pick.setFixedWidth(28)
        btn_pick.setToolTip("Choisir depuis la liste du projet.")
        pick_dim = "2D" if dim in ("2D", "INT") else "3D"
        def _make_pick(e=edit_ids, d=pick_dim):
            return lambda: self._pick_avatar_ids(e, d)
        btn_pick.clicked.connect(_make_pick())
        row_layout.addWidget(edit_ids)
        row_layout.addWidget(btn_pick)

        # ── Groupe ────────────────────────────────────────────────────────────
        combo_grp = QComboBox()
        combo_grp.setFixedWidth(110)
        combo_grp.setEditable(True)
        combo_grp.addItem("")
        groups = list(
            (getattr(getattr(self, "controller", None), "state", None)
             and getattr(self.controller.state, "avatar_groups", {}) or {}).keys()
        )
        combo_grp.addItems(groups)
        if entry.get("group"):
            idx_g = combo_grp.findText(entry["group"])
            if idx_g >= 0:
                combo_grp.setCurrentIndex(idx_g)
            else:
                combo_grp.setCurrentText(entry["group"])
        combo_grp.setToolTip(
            "Groupe d'avatars. Si vide, les IDs ci-contre sont utilises. "
            "Les IDs du groupe sont resolus au moment de la generation du script."
        )
        row_layout.addWidget(combo_grp)

        # ── Mode d'execution (timing) ──────────────────────────────────────
        _tc_i, _combo_mode_i, _spin_val_i = self._make_timing_widget(entry)
        row_layout.addWidget(_tc_i)

        # ── Variable de stockage ─────────────────────────────────────────────
        edit_store = QLineEdit()
        edit_store.setFixedWidth(110)
        edit_store.setPlaceholderText("ex: res_Rn")
        edit_store.setText(entry.get("store", ""))
        edit_store.setToolTip(
            "Nom de variable Python pour stocker le resultat. "
            "Ex: res_Rn  =>  res_Rn = chipy.DKDKx_GetRlocTT(i). "
            "Laisser vide si le resultat n'est pas utilise."
        )
        row_layout.addWidget(edit_store)

        # ── Bouton supprimer ─────────────────────────────────────────────────
        btn_del = QPushButton("x")
        btn_del.setFixedWidth(24)
        row_data = {
            "widget":     row_widget,
            "combo_func": combo_func,
            "edit_ids":   edit_ids,
            "combo_grp":  combo_grp,
            "combo_mode": _combo_mode_i,
            "spin_val":   _spin_val_i,
            "edit_store": edit_store,
            "dim":        dim,
        }
        def _make_del(rd=row_data, rl=rows_list, rlay=rows_layout):
            def _do():
                rl.remove(rd)
                rlay.removeWidget(rd["widget"])
                rd["widget"].deleteLater()
            return _do
        btn_del.clicked.connect(_make_del())
        row_layout.addWidget(btn_del)
        row_layout.addStretch()

        rows_layout.addWidget(row_widget)
        rows_list.append(row_data)

    def _read_insp_row(self, row: dict) -> dict:
        """Lit une ligne d'inspection et retourne un dict serialisable."""
        _mode = row["combo_mode"].currentData()
        return {
            "func":      row["combo_func"].currentText(),
            "ids":       row["edit_ids"].text().strip(),
            "group":     row["combo_grp"].currentText().strip(),
            "step_mode": _mode,
            "step_val":  row["spin_val"].value(),
            "store":     row["edit_store"].text().strip(),
            # compat ascendante
            "in_loop":   _mode != "after",
            "freq":      row["spin_val"].value() if _mode == "every_n" else 1,
        }

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

        # Visibilite — lignes dynamiques
        self._vis_rows.clear()
        while self._vis_rows_layout.count():
            _wv = self._vis_rows_layout.takeAt(0).widget()
            if _wv: _wv.deleteLater()
        for _ve in p.get("vis_entries", []):
            self._add_vis_row(_ve)

        # Inspection 2D / 3D / Interactions — charger les entrees
        self._insp2d_rows.clear()
        while self._insp2d_rows_layout.count():
            w2 = self._insp2d_rows_layout.takeAt(0).widget()
            if w2: w2.deleteLater()
        for entry in p.get("insp2d_entries", []):
            self._add_insp_row("2D", entry)
        self._insp3d_rows.clear()
        while self._insp3d_rows_layout.count():
            w3 = self._insp3d_rows_layout.takeAt(0).widget()
            if w3: w3.deleteLater()
        for entry in p.get("insp3d_entries", []):
            self._add_insp_row("3D", entry)
        self._inspi_rows.clear()
        while self._inspi_rows_layout.count():
            wi = self._inspi_rows_layout.takeAt(0).widget()
            if wi: wi.deleteLater()
        for entry in p.get("inspi_entries", []):
            self._add_insp_row("INT", entry)

        # GetBodyVector RBDY2/3 — charger les entrees depuis _params
        self._gbv2_rows.clear()
        while self._gbv2_rows_layout.count():
            w = self._gbv2_rows_layout.takeAt(0).widget()
            if w: w.deleteLater()
        for entry in p.get("gbv2_entries", []):
            self._add_gbv_row("2D", entry)
        self._gbv3_rows.clear()
        while self._gbv3_rows_layout.count():
            w = self._gbv3_rows_layout.takeAt(0).widget()
            if w: w.deleteLater()
        for entry in p.get("gbv3_entries", []):
            self._add_gbv_row("3D", entry)

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

    # =========================================================================
    # Gestion des lignes GetBodyVector (ajout / lecture)
    # =========================================================================

    _GBV_VECS = [
        "Coor0", "Coor_", "Coorb", "Coorm",
        "X____", "V____", "Vbeg_", "Vfree",
        "Fext",  "Fint_", "Reac",  "Ireac",
    ]

    def _add_vis_row(self, entry: dict = None):
        """
        Ajoute une ligne de visibilite dans la section Visibilite.
        entry : dict {"action": str, "dim": str, "ids": str, "group": str,
                      "step_mode": str, "step_val": int}
        """
        entry = entry or {}

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)

        # ── Action : SetVisible / SetInvisible ────────────────────────────
        combo_action = QComboBox()
        combo_action.setFixedWidth(110)
        combo_action.addItem("SetVisible",   "visible")
        combo_action.addItem("SetInvisible", "invisible")
        combo_action.setToolTip(
            "SetVisible   : chipy.RBDY2_SetVisible(id)\n"
            "SetInvisible : chipy.RBDY2_SetInvisible(id)"
        )
        if entry.get("action") == "invisible":
            combo_action.setCurrentIndex(1)
        row_layout.addWidget(combo_action)

        # ── Dimension 2D / 3D ─────────────────────────────────────────────
        combo_dim = QComboBox()
        combo_dim.setFixedWidth(55)
        combo_dim.addItem("2D", "2D")
        combo_dim.addItem("3D", "3D")
        combo_dim.setToolTip("RBDY2 (2D) ou RBDY3 (3D)")
        if entry.get("dim") == "3D":
            combo_dim.setCurrentIndex(1)
        row_layout.addWidget(combo_dim)

        # ── IDs ───────────────────────────────────────────────────────────
        edit_ids = QLineEdit()
        edit_ids.setFixedWidth(100)
        edit_ids.setPlaceholderText("1, 3, 5")
        edit_ids.setText(entry.get("ids", ""))
        edit_ids.setToolTip(
            "IDs des avatars (1-based). "
            "Prioritaire sur le groupe si les deux sont remplis."
        )
        btn_pick = QPushButton("...")
        btn_pick.setFixedWidth(28)
        btn_pick.setToolTip("Choisir depuis la liste des avatars du projet.")
        def _make_pick(e=edit_ids, cb=combo_dim):
            return lambda: self._pick_avatar_ids(e, cb.currentData())
        btn_pick.clicked.connect(_make_pick())
        row_layout.addWidget(edit_ids)
        row_layout.addWidget(btn_pick)

        # ── Groupe ────────────────────────────────────────────────────────
        combo_grp = QComboBox()
        combo_grp.setFixedWidth(110)
        combo_grp.setEditable(True)
        combo_grp.addItem("")
        _groups = list(
            (getattr(getattr(self, "controller", None), "state", None)
             and getattr(self.controller.state, "avatar_groups", {}) or {}).keys()
        )
        combo_grp.addItems(_groups)
        if entry.get("group"):
            idx_g = combo_grp.findText(entry["group"])
            if idx_g >= 0:
                combo_grp.setCurrentIndex(idx_g)
            else:
                combo_grp.setCurrentText(entry["group"])
        combo_grp.setToolTip(
            "Groupe d'avatars. Si vide, les IDs ci-contre sont utilises. "
            "Si les deux sont remplis, les IDs ont la priorite."
        )
        row_layout.addWidget(combo_grp)

        # ── Mode / Timing (memes options que GBV/Inspection) ──────────────
        _tc, _combo_mode, _spin_val = self._make_timing_widget(entry)
        row_layout.addWidget(_tc)

        # ── Bouton supprimer ──────────────────────────────────────────────
        btn_del = QPushButton("x")
        btn_del.setFixedWidth(24)
        btn_del.setToolTip("Supprimer cette ligne.")
        row_data = {
            "widget":       row_widget,
            "combo_action": combo_action,
            "combo_dim":    combo_dim,
            "edit_ids":     edit_ids,
            "combo_grp":    combo_grp,
            "combo_mode":   _combo_mode,
            "spin_val":     _spin_val,
        }
        def _make_del(rd=row_data):
            def _do():
                self._vis_rows.remove(rd)
                self._vis_rows_layout.removeWidget(rd["widget"])
                rd["widget"].deleteLater()
            return _do
        btn_del.clicked.connect(_make_del())
        row_layout.addWidget(btn_del)
        row_layout.addStretch()

        self._vis_rows_layout.addWidget(row_widget)
        self._vis_rows.append(row_data)

    def _read_vis_row(self, row: dict) -> dict:
        """Lit une ligne de visibilite et retourne un dict serialisable."""
        _mode = row["combo_mode"].currentData()
        return {
            "action":    row["combo_action"].currentData(),
            "dim":       row["combo_dim"].currentData(),
            "ids":       row["edit_ids"].text().strip(),
            "group":     row["combo_grp"].currentText().strip(),
            "step_mode": _mode,
            "step_val":  row["spin_val"].value(),
            "in_loop":   _mode != "after",
        }

    @staticmethod
    def _make_timing_widget(entry: dict):
        """
        Construit un widget horizontal compact pour le mode d'execution :
          [ComboBox mode] [SpinBox valeur]
        Retourne (container_widget, combo_mode, spin_val).
        step_mode : "all" | "every_n" | "at_k" | "after"
        step_val  : N (every_n) ou k (at_k), ignore sinon
        """
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)

        combo = QComboBox()
        combo.setFixedWidth(105)
        combo.addItem("Tous les pas",   "all")
        combo.addItem("Tous les N pas", "every_n")
        combo.addItem("Au pas k =",     "at_k")
        combo.addItem("Apres boucle",   "after")
        combo.setToolTip(
            "Tous les pas   : appel a chaque iteration.\n"
            "Tous les N pas : appel si k % N == 0.\n"
            "Au pas k =     : appel seulement si k == valeur.\n"
            "Apres boucle   : appel unique apres la boucle."
        )

        spin = QSpinBox()
        spin.setRange(1, 9_999_999)
        spin.setFixedWidth(72)
        spin.setToolTip("N (frequence) ou k (pas unique)")

        # Restaurer depuis entry
        mode = entry.get("step_mode", "all")
        # Compatibilite ascendante : in_loop=False => "after"
        if not entry.get("in_loop", True) and "step_mode" not in entry:
            mode = "after"
        elif "step_mode" not in entry and entry.get("freq", 1) > 1:
            mode = "every_n"
        val = entry.get("step_val", entry.get("freq", 1))

        idx = {d: i for i, d in enumerate(["all","every_n","at_k","after"])}.get(mode, 0)
        combo.setCurrentIndex(idx)
        spin.setValue(int(val))

        def _on_mode(i, s=spin):
            s.setEnabled(i in (1, 2))  # every_n ou at_k
        combo.currentIndexChanged.connect(_on_mode)
        _on_mode(combo.currentIndex())

        lay.addWidget(combo)
        lay.addWidget(spin)
        return container, combo, spin

    def _add_gbv_row(self, dim: str, entry: dict = None):
        """\n        Ajoute une ligne de configuration GetBodyVector.        dim    : "2D" ou "3D"        entry  : dict optionnel pour pre-remplir la ligne                 {"vec": str, "ids": str, "group": str,                  "in_loop": bool, "freq": int}        """
        from PyQt6.QtWidgets import QListWidget, QListWidgetItem

        entry = entry or {}
        rows_list   = self._gbv2_rows   if dim == "2D" else self._gbv3_rows
        rows_layout = self._gbv2_rows_layout if dim == "2D" else self._gbv3_rows_layout

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)

        # ── Vecteur ──────────────────────────────────────────────────────────
        combo_vec = QComboBox()
        combo_vec.addItems(self._GBV_VECS)
        combo_vec.setFixedWidth(110)
        if entry.get("vec") in self._GBV_VECS:
            combo_vec.setCurrentText(entry["vec"])
        combo_vec.setToolTip(
            "Vecteur d'etat a extraire.\n"
            "Coor0=pos init, Coor_=pos courante, X____=coord gen, "
            "V____=vitesses gen, Vfree=vitesses libres, "
            "Fext=forces ext, Fint_=forces int, "
            "Reac=reaction contact, Ireac=impulsion contact."
        )
        row_layout.addWidget(combo_vec)

        # ── IDs avatars ───────────────────────────────────────────────────────
        edit_ids = QLineEdit()
        edit_ids.setFixedWidth(120)
        edit_ids.setPlaceholderText("Ex : 1, 3, 5")
        edit_ids.setText(entry.get("ids", ""))
        edit_ids.setToolTip(
            "IDs des avatars (numerotation 1-based, ordre de creation). "
            "Prioritaire sur le groupe si les deux sont remplis."
        )
        btn_pick = QPushButton("...")
        btn_pick.setFixedWidth(28)
        btn_pick.setToolTip("Choisir les avatars depuis la liste du projet.")
        def _make_pick(e=edit_ids, d=dim):
            return lambda: self._pick_avatar_ids(e, d)
        btn_pick.clicked.connect(_make_pick())
        row_layout.addWidget(edit_ids)
        row_layout.addWidget(btn_pick)

        # ── Groupe ────────────────────────────────────────────────────────────
        combo_grp = QComboBox()
        combo_grp.setFixedWidth(110)
        combo_grp.setEditable(True)
        combo_grp.addItem("")          # vide = pas de groupe
        groups = list(
            (getattr(getattr(self, "controller", None),
                     "state", None) and
             getattr(self.controller.state, "avatar_groups", {}) or {}).keys()
        )
        combo_grp.addItems(groups)
        if entry.get("group"):
            idx = combo_grp.findText(entry["group"])
            if idx >= 0:
                combo_grp.setCurrentIndex(idx)
            else:
                combo_grp.setCurrentText(entry["group"])
        combo_grp.setToolTip(
            "Groupe d'avatars a extraire. "
            "Si vide, les IDs ci-contre sont utilises. "
            "Si les deux sont remplis, les IDs ont la priorite."
        )
        row_layout.addWidget(combo_grp)

        # ── Mode d'execution (timing) ──────────────────────────────────────
        _tc, _combo_mode, _spin_val = self._make_timing_widget(entry)
        row_layout.addWidget(_tc)

        # ── Bouton supprimer ──────────────────────────────────────────────────
        btn_del = QPushButton("x")
        btn_del.setFixedWidth(24)
        btn_del.setToolTip("Supprimer cette ligne.")
        row_data = {
            "widget":     row_widget,
            "combo_vec":  combo_vec,
            "edit_ids":   edit_ids,
            "combo_grp":  combo_grp,
            "combo_mode": _combo_mode,
            "spin_val":   _spin_val,
            "dim":        dim,
        }
        def _make_del(rd=row_data, rl=rows_list, rlay=rows_layout):
            def _do_del():
                rl.remove(rd)
                rlay.removeWidget(rd["widget"])
                rd["widget"].deleteLater()
            return _do_del
        btn_del.clicked.connect(_make_del())
        row_layout.addWidget(btn_del)
        row_layout.addStretch()

        rows_layout.addWidget(row_widget)
        rows_list.append(row_data)

    def _read_gbv_row(self, row: dict) -> dict:
        """Lit les valeurs d'une ligne GBV et retourne un dict serialisable."""
        _mode = row["combo_mode"].currentData()
        return {
            "vec":       row["combo_vec"].currentText(),
            "ids":       row["edit_ids"].text().strip(),
            "group":     row["combo_grp"].currentText().strip(),
            "step_mode": _mode,
            "step_val":  row["spin_val"].value(),
            # compat ascendante
            "in_loop":   _mode != "after",
            "freq":      row["spin_val"].value() if _mode == "every_n" else 1,
        }

    def _pick_avatar_ids(self, target_edit: "QLineEdit", dim: str):
        """\n        Ouvre un dialogue de selection d'avatars du projet.        Insere les IDs selectionnes (1-bases) dans target_edit.        dim : "2D" ou "3D" pour filtrer les avatars affichables.        """
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
        """\n        Retourne le dict complet des parametres configures.        Fusionnable avec ComputeTab.get_parameters().        """
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

        # Visibilite — lignes dynamiques
        p["vis_entries"] = [self._read_vis_row(r) for r in self._vis_rows]

        # Inspection
        p["insp2d_entries"] = [self._read_insp_row(r) for r in self._insp2d_rows]
        p["insp3d_entries"] = [self._read_insp_row(r) for r in self._insp3d_rows]
        p["inspi_entries"]  = [self._read_insp_row(r) for r in self._inspi_rows]

        # GetBodyVector RBDY2/3 — collecter toutes les entrees
        p["gbv2_entries"] = [self._read_gbv_row(row) for row in self._gbv2_rows]
        p["gbv3_entries"] = [self._read_gbv_row(row) for row in self._gbv3_rows]

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