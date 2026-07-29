# ============================================================================
# mesh_wizard_deformable.py
# Assistant PyQt6 pour la création de corps déformables (mesh2D / mesh3D)
# S'appuie directement sur pre.buildMesh2D() et pre.buildMeshH8() de pylmgc90,
# en suivant le même patron que setup_wizard.py et granulo_wizard.py.
# ============================================================================

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QLabel, QSpinBox, QDoubleSpinBox,
    QRadioButton, QGroupBox, QCheckBox, QMessageBox, QTextEdit,
    QPushButton, QFileDialog, QWidget
)
from PyQt6.QtCore import Qt
from typing import Dict, Any

from ...core.models import (
    Material, Model, Avatar,
    MaterialType, AvatarType, AvatarOrigin
)
from ...controllers.project_controller import ProjectController


# ─────────────────────────── constantes ───────────────────────────────────────

# Types d'éléments disponibles par dimension
_ELEMENTS_2D = ["T3xxx", "Q4xxx", "T6xxx", "Q8xxx", "Q9xxx"]
_ELEMENTS_3D = ["H8xxx", "H20xx", "TE4xx", "TE10x", "SHB8x", "SHB6x"]

# Descriptions des éléments
_ELEMENT_INFO = {
    "T3xxx": "Triangle linéaire à 3 nœuds",
    "Q4xxx": "Quadrangle bilinéaire à 4 nœuds",
    "T6xxx": "Triangle quadratique à 6 nœuds",
    "Q8xxx": "Quadrangle serendipity à 8 nœuds",
    "Q9xxx": "Quadrangle biquadratique complet à 9 nœuds",
    "H8xxx": "Hexaèdre trilinéaire à 8 nœuds",
    "H20xx": "Hexaèdre triquadratique à 20 nœuds",
    "TE4xx": "Tétraèdre linéaire à 4 nœuds",
    "TE10x": "Tétraèdre quadratique à 10 nœuds",
    "SHB8x": "Solide-coque hexaédrique SHB8 à 8 nœuds",
    "SHB6x": "Solide-coque prismatique SHB6 à 6 nœuds",
}

# Types de maillage pylmgc90 par dimension de géométrie
_MESH_TYPES_2D = ["Q4", "2T3", "4T3", "Q8"]
_MESH_TYPES_3D = ["H8"]        # buildMeshH8 — seul disponible nativement

# Options d'anisotropie pour le modèle
_ANISOTROPY = ["iso__", "ortho"]

# Options cinématique / formulation
_KINEMATIC    = ["small", "large"]
_FORMULATION  = ["UpdtL", "TotaL"]
_MASS_STORAGE = ["lump_", "coher"]

# Propriétés par défaut des matériaux élastiques
_MAT_DEFAULTS = {
    "ELAS":        {"elas": "standard", "young": 70e9,   "nu": 0.3,  "anisotropy": "isotropic"},
    "ELAS_DILA":   {"elas": "standard", "young": 70e9,   "nu": 0.3,  "anisotropy": "isotropic", "dilatation": 1e-5, "T_ref_meca": 20.0},
    "VISCO_ELAS":  {"elas": "standard", "anisotropy": "isotropic", "young": 1.17e11, "nu": 0.35,
                    "viscous_model": "KelvinVoigt", "viscous_young": 1.17e9, "viscous_nu": 0.35},
    "ELAS_PLAS":   {"elas": "standard", "anisotropy": "isotropic", "young": 1.17e11, "nu": 0.35,
                    "critere": "Von-Mises", "isoh": "linear", "iso_hard": 4e8,
                    "isoh_coeff": 1e8, "cinh": "none", "visc": "none"},
    "THERMO_ELAS": {"elas": "standard", "young": 0.0, "nu": 0.0, "anisotropy": "isotropic",
                    "dilatation": 0.0, "T_ref_meca": 0.0, "conductivity": "field", "specific_capacity": "field"},
    "PORO_ELAS":   {"elas": "standard", "young": 0.0, "nu": 0.0, "anisotropy": "isotropic",
                    "hydro_cpl": 0.0, "conductivity": "field", "specific_capacity": "field"},
}

_ELASTIC_TYPES = list(_MAT_DEFAULTS.keys())


# ─────────────────────────── helpers gmsh ─────────────────────────────────────

def _gmsh_disk(cx, cy, r, nr, ntheta, filepath):
    """\nGénère un maillage 2D de disque via gmsh et l'écrit dans filepath (.msh v2).\nlc est déduit du rayon et du nombre d'éléments angulaires.\n"""
    import gmsh
    lc = (2 * 3.14159 * r / ntheta)   # taille de maille ≈ arc / ntheta

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("disk")

    gmsh.model.occ.addDisk(cx, cy, 0.0, r, r)
    gmsh.model.occ.synchronize()

    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)
    gmsh.option.setNumber("Mesh.Algorithm", 6)          # Frontal-Delaunay
    gmsh.model.mesh.generate(2)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.write(filepath)
    gmsh.finalize()


def _gmsh_sphere(cx, cy, cz, r, nr, ntheta, nphi, filepath):
    """\nGénère un maillage 3D de sphère pleine via gmsh.\nlc déduit du rayon et de ntheta.\n"""
    import gmsh
    lc = (2 * 3.14159 * r / ntheta)

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("sphere")

    gmsh.model.occ.addSphere(cx, cy, cz, r)
    gmsh.model.occ.synchronize()

    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)
    gmsh.option.setNumber("Mesh.Algorithm3D", 4)        # Frontal
    gmsh.model.mesh.generate(3)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.write(filepath)
    gmsh.finalize()


def _gmsh_cylinder(cx, cy, cz, r, h, nr, ntheta, nz, filepath):
    """\nGénère un maillage 3D de cylindre plein via gmsh.\nLe cylindre est centré en (cx, cy, cz), axe Z, de rayon r et hauteur h.\nlc déduit de r et ntheta.\n"""
    import gmsh
    lc = (2 * 3.14159 * r / ntheta)

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("cylinder")

    # addCylinder(x, y, z, dx, dy, dz, r) — base en z0 = cz - h/2
    gmsh.model.occ.addCylinder(cx, cy, cz - h / 2.0, 0.0, 0.0, h, r)
    gmsh.model.occ.synchronize()

    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)
    gmsh.option.setNumber("Mesh.Algorithm3D", 4)
    gmsh.model.mesh.generate(3)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.write(filepath)
    gmsh.finalize()


# Wizard principal
# ═══════════════════════════════════════════════════════════════════════════════

class MeshWizard(QWizard):
    """\nAssistant de création de corps déformables.\nGénère un maillage structuré 2D ou 3D via pre.buildMesh2D / pre.buildMeshH8,\ncrée le matériau élastique et le modèle EF, puis insère l'avatar MAILx\ndirectement dans les conteneurs pylmgc90 du controller.\n"""

    PAGE_INTRO   = 0
    PAGE_DIM     = 1
    PAGE_MAT     = 2
    PAGE_MODEL   = 3
    PAGE_GEOM    = 4
    PAGE_REFINE  = 5
    PAGE_BOUNDARY= 6
    PAGE_SUMMARY = 7

    def __init__(self, controller: ProjectController, parent=None):
        super().__init__(parent)
        self.controller = controller

        # Snapshot pour restauration sur Annuler / erreur
        self._saved_name         = controller.state.name
        self._saved_project_path = controller.project_path
        self._saved_dimension    = controller.state.dimension

        self.setWindowTitle("🔷 Assistant Corps Déformable (EF)")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)
        self.resize(820, 600)

        self.addPage(MeshIntroPage())
        self.addPage(MeshDimensionPage())
        self.addPage(MeshMaterialPage())
        self.addPage(MeshModelPage())
        self.addPage(MeshGeometryPage())
        self.addPage(MeshRefinementPage())
        self.addPage(MeshBoundaryPage())
        self.addPage(MeshSummaryPage())

        self.setButtonText(QWizard.WizardButton.NextButton,   "Suivant ➡️")
        self.setButtonText(QWizard.WizardButton.BackButton,   "⬅️ Retour")
        self.setButtonText(QWizard.WizardButton.FinishButton, "✅ Générer le maillage")
        self.setButtonText(QWizard.WizardButton.CancelButton, "❌ Annuler")

    # ── accept / reject ────────────────────────────────────────────────────────

    def accept(self):
        try:
            n_nodes, n_elems = self._generate_mesh()
            QMessageBox.information(
                self, "Succès",
                f"✅ Corps déformable généré avec succès !\n"
                f"   {n_nodes} nœuds · {n_elems} éléments"
            )
            super().accept()
        except Exception as e:
            self.controller.state.name      = self._saved_name
            self.controller.project_path    = self._saved_project_path
            self.controller.state.dimension = self._saved_dimension
            QMessageBox.critical(self, "Erreur", f"Génération échouée :\n{e}")

    def reject(self):
        self.controller.state.name      = self._saved_name
        self.controller.project_path    = self._saved_project_path
        self.controller.state.dimension = self._saved_dimension
        super().reject()

    # ── génération principale ──────────────────────────────────────────────────

    def _generate_mesh(self):
        """\nConstruit le maillage EF et l'insère dans le projet.\nRetourne (nb_noeuds, nb_elements).\n"""
        from pylmgc90.pre import buildMesh2D, buildMeshH8

        ctrl = self.controller

        # ── pages ─────────────────────────────────────────────────────────────
        dim_page    = self.page(self.PAGE_DIM)
        mat_page    = self.page(self.PAGE_MAT)
        mod_page    = self.page(self.PAGE_MODEL)
        geom_page   = self.page(self.PAGE_GEOM)
        ref_page    = self.page(self.PAGE_REFINE)
        bound_page  = self.page(self.PAGE_BOUNDARY)

        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        ok, reasons = self.controller.can_change_dimension(dimension)
        if not ok:
            reply = QMessageBox.question(
                self, "⚠️ Changement de dimension",
                "Ce projet contient déjà des éléments incompatibles avec "
                "la dimension choisie :\n\n• " + "\n• ".join(reasons) +
                "\n\nContinuer quand même ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                raise ValueError("Génération annulée : dimension incompatible avec le projet existant.")
            self.controller.set_dimension(dimension, force=True)
        else:
            self.controller.set_dimension(dimension)

        # ── matériau ──────────────────────────────────────────────────────────
        if mat_page.create_mat_check.isChecked():
            mat_name = mat_page.mat_name_input.text().strip()
            if not mat_name:
                raise ValueError("Le nom du matériau ne peut pas être vide.")
            mat_type_str = mat_page.mat_type_combo.currentText()
            props = self._collect_mat_properties(mat_page, mat_type_str)
            material = Material(
                name=mat_name,
                material_type=MaterialType(mat_type_str),
                density=mat_page.density_spin.value(),
                properties=props
            )
            ctrl.add_material(material)
        else:
            sel = mat_page.existing_mat_combo.currentText()
            if sel in ("", "(Aucun matériau élastique)", "(Aucun matériau)"):
                raise ValueError("Aucun matériau sélectionné.")
            mat_name = sel

        # ── modèle ────────────────────────────────────────────────────────────
        if mod_page.create_mod_check.isChecked():
            mod_name = mod_page.mod_name_input.text().strip()
            if not mod_name:
                raise ValueError("Le nom du modèle ne peut pas être vide.")
            element     = mod_page.element_combo.currentText()
            physics     = mod_page.physics_combo.currentText()
            anisotropy  = mod_page.anisotropy_combo.currentText()
            kinematic   = mod_page.kinematic_combo.currentText()
            formulation = mod_page.formulation_combo.currentText()
            mass_stor   = mod_page.mass_combo.currentText()
            options = {
                "anisotropy":   anisotropy,
                "kinematic":    kinematic,
                "formulation":  formulation,
                "mass_storage": mass_stor,
                "material":     "elas_",
                "external_model": "no___",
            }
            model = Model(
                name=mod_name,
                physics=physics,
                element=element,
                dimension=dimension,
                options=options
            )
            ctrl.add_model(model)
        else:
            sel = mod_page.existing_mod_combo.currentText()
            if sel in ("", f"(Aucun modèle {dimension}D)", "(Aucun modèle)"):
                raise ValueError("Aucun modèle sélectionné.")
            mod_name = sel

        # ── objets pylmgc90 du matériau et du modèle ─────────────────────────
        mat_obj = ctrl._pylmgc_materials.get(mat_name)
        mod_obj = ctrl._pylmgc_models.get(mod_name)
        if mat_obj is None:
            raise ValueError(f"Matériau pylmgc90 '{mat_name}' introuvable.")
        if mod_obj is None:
            raise ValueError(f"Modèle pylmgc90 '{mod_name}' introuvable.")

        # ── maillage ──────────────────────────────────────────────────────────
        if dimension == 2:
            mesh_obj = self._build_mesh_2d(geom_page, ref_page, mat_obj, mod_obj, buildMesh2D)
        else:
            mesh_obj = self._build_mesh_3d(geom_page, ref_page, mat_obj, mod_obj, buildMeshH8)

        # ── insertion dans les conteneurs pylmgc90 ────────────────────────────
        ctrl._bodies_container.addAvatar(mesh_obj)
        ctrl._pylmgc_bodies.append(mesh_obj)

        # ── enregistrement dans le state (avatar de type MESH_DEFORMABLE) ─────
        center    = geom_page.get_center(dimension)
        geom_type = geom_page.geom_type_combo.currentText()

        # Construire mesh_params pour la re-génération au chargement
        mp: Dict[str, Any] = {'geom': geom_type, 'dim': dimension}
        if geom_type == "Rectangle":
            mp.update({'lx': geom_page.lx_spin.value(), 'ly': geom_page.ly_spin.value(),
                       'mesh_type': ref_page.mesh_type_combo.currentText(),
                       'nx': ref_page.nx_spin.value(), 'ny': ref_page.ny_spin.value()})
        elif geom_type == "Disque":
            mp.update({'r': geom_page.radius_spin.value(),
                       'nr': ref_page.nr_spin.value(), 'ntheta': ref_page.ntheta_spin.value()})
        elif geom_type == "Boîte (H8)":
            mp.update({'lx': geom_page.lx_spin.value(), 'ly': geom_page.ly_spin.value(),
                       'lz': geom_page.lz_spin.value(),
                       'nx': ref_page.nx_spin.value(), 'ny': ref_page.ny_spin.value(),
                       'nz': ref_page.nz_spin.value()})
        elif geom_type == "Sphère":
            mp.update({'r': geom_page.radius_spin.value(),
                       'nr': ref_page.nr_spin.value(), 'ntheta': ref_page.ntheta_spin.value(),
                       'nphi': ref_page.nphi_spin.value()})
        elif geom_type == "Cylindre":
            mp.update({'r': geom_page.radius_spin.value(), 'h': geom_page.height_spin.value(),
                       'nr': ref_page.nr_spin.value(), 'ntheta': ref_page.ntheta_spin.value(),
                       'nz': ref_page.nz_spin.value()})
        elif geom_type == "Fichier externe":
            mp['filepath'] = geom_page.file_path_input.text().strip()
        mp['cx'] = center[0]; mp['cy'] = center[1]
        if dimension == 3:
            mp['cz'] = center[2]

        avatar = Avatar(
            avatar_type=AvatarType.MESH_DEFORMABLE,
            center=center,
            material_name=mat_name,
            model_name=mod_name,
            color="CYANx",
            origin=AvatarOrigin.MANUAL,
            contactors=[],
            mesh_params=mp,
        )
        ctrl.state.avatars.append(avatar)

        # ── Appliquer les conditions aux limites (DOF) ────────────────────
        boundary_page = self.page(self.PAGE_BOUNDARY)
        dof_conditions = boundary_page.get_dof_conditions()
        if dof_conditions:
            self._apply_boundary_conditions(mesh_obj, boundary_page)
            # Sauvegarder les conditions dans mesh_params pour reconstruction
            mp["dof_conditions"] = dof_conditions

        # Un seul signal pour rafraîchir l'UI
        ctrl.state_changed.emit()

        # Statistiques pour le message de succès
        n_nodes = len(mesh_obj.nodes) if hasattr(mesh_obj, 'nodes') else 0
        n_elems = len(mesh_obj.bulks) if hasattr(mesh_obj, 'bulks') else 0
        return n_nodes, n_elems

    # ── construction 2D ───────────────────────────────────────────────────────

    def _build_mesh_2d(self, geom_page, ref_page, mat_obj, mod_obj, buildMesh2D):
        """\nAppelle pre.buildMesh2D(mesh_type, x0, y0, lx, ly, nb_elem_x, nb_elem_y).\nRetourne l'avatar MAILx pylmgc90.\n"""
        geom_type = geom_page.geom_type_combo.currentText()
        mesh_type = ref_page.mesh_type_combo.currentText()   # Q4, 2T3, 4T3, Q8

        if geom_type == "Rectangle":
            lx = geom_page.lx_spin.value()
            ly = geom_page.ly_spin.value()
            x0 = geom_page.cx_spin.value() - lx / 2.0
            y0 = geom_page.cy_spin.value() - ly / 2.0
            nx = ref_page.nx_spin.value()
            ny = ref_page.ny_spin.value()

            # buildMesh2D renvoie un objet mesh (nodes + bulks) ;
            # on l'enveloppe ensuite dans un avatar MAILx via pre.buildMeshedAvatar.
            from pylmgc90 import pre as pre_mod
            surf_mesh = buildMesh2D(
                mesh_type,
                x0, y0,
                lx, ly,
                nx, ny
            )
            avatar = pre_mod.buildMeshedAvatar(
                mesh=surf_mesh,
                model=mod_obj,
                material=mat_obj
            )
            return avatar

        elif geom_type == "Disque":
            import tempfile, os
            from pylmgc90 import pre as pre_mod
            r      = geom_page.radius_spin.value()
            cx     = geom_page.cx_spin.value()
            cy     = geom_page.cy_spin.value()
            nr     = ref_page.nr_spin.value()
            ntheta = ref_page.ntheta_spin.value()

            with tempfile.NamedTemporaryFile(suffix=".msh", delete=False) as f:
                tmp = f.name
            try:
                _gmsh_disk(cx, cy, r, nr, ntheta, tmp)
                surf_mesh = pre_mod.readMesh(tmp, 2)
            finally:
                os.unlink(tmp)

            avatar = pre_mod.buildMeshedAvatar(
                mesh=surf_mesh,
                model=mod_obj,
                material=mat_obj,
            )
            return avatar

        elif geom_type == "Fichier externe":
            filepath = geom_page.file_path_input.text().strip()
            if not filepath:
                raise ValueError("Aucun fichier de maillage sélectionné.")
            from pylmgc90 import pre as pre_mod
            surf_mesh = pre_mod.readMesh(filepath, 2)
            avatar = pre_mod.buildMeshedAvatar(
                mesh=surf_mesh,
                model=mod_obj,
                material=mat_obj,
            )
            return avatar

        else:
            raise ValueError(f"Géométrie 2D non supportée : '{geom_type}'")

    # ── construction 3D ───────────────────────────────────────────────────────

    def _build_mesh_3d(self, geom_page, ref_page, mat_obj, mod_obj, buildMeshH8):
        """\nAppelle pre.buildMeshH8(x0, y0, z0, lx, ly, lz, nx, ny, nz).\nRetourne l'avatar MAILx pylmgc90.\n"""
        from pylmgc90 import pre as pre_mod

        geom_type = geom_page.geom_type_combo.currentText()

        if geom_type == "Boîte (H8)":
            lx = geom_page.lx_spin.value()
            ly = geom_page.ly_spin.value()
            lz = geom_page.lz_spin.value()
            x0 = geom_page.cx_spin.value() - lx / 2.0
            y0 = geom_page.cy_spin.value() - ly / 2.0
            z0 = geom_page.cz_spin.value() - lz / 2.0
            nx = ref_page.nx_spin.value()
            ny = ref_page.ny_spin.value()
            nz = ref_page.nz_spin.value()

            vol_mesh = buildMeshH8(
                x0, y0, z0,
                lx, ly, lz,
                nx, ny, nz
            )
            avatar = pre_mod.buildMeshedAvatar(
                mesh=vol_mesh,
                model=mod_obj,
                material=mat_obj,

            )
            return avatar

        elif geom_type == "Sphère":
            import tempfile, os
            r      = geom_page.radius_spin.value()
            cx     = geom_page.cx_spin.value()
            cy     = geom_page.cy_spin.value()
            cz     = geom_page.cz_spin.value()
            nr     = ref_page.nr_spin.value()
            ntheta = ref_page.ntheta_spin.value()
            nphi   = ref_page.nphi_spin.value()

            with tempfile.NamedTemporaryFile(suffix=".msh", delete=False) as f:
                tmp = f.name
            try:
                _gmsh_sphere(cx, cy, cz, r, nr, ntheta, nphi, tmp)
                vol_mesh = pre_mod.readMesh(tmp, 3)
            finally:
                os.unlink(tmp)

            avatar = pre_mod.buildMeshedAvatar(
                mesh=vol_mesh,
                model=mod_obj,
                material=mat_obj,
            )
            return avatar

        elif geom_type == "Cylindre":
            import tempfile, os
            r      = geom_page.radius_spin.value()
            h      = geom_page.height_spin.value()
            cx     = geom_page.cx_spin.value()
            cy     = geom_page.cy_spin.value()
            cz     = geom_page.cz_spin.value()
            nr     = ref_page.nr_spin.value()
            ntheta = ref_page.ntheta_spin.value()
            nz     = ref_page.nz_spin.value()

            with tempfile.NamedTemporaryFile(suffix=".msh", delete=False) as f:
                tmp = f.name
            try:
                _gmsh_cylinder(cx, cy, cz, r, h, nr, ntheta, nz, tmp)
                vol_mesh = pre_mod.readMesh(tmp, 3)
            finally:
                os.unlink(tmp)

            avatar = pre_mod.buildMeshedAvatar(
                mesh=vol_mesh,
                model=mod_obj,
                material=mat_obj,
            )
            return avatar

        elif geom_type == "Fichier externe":
            filepath = geom_page.file_path_input.text().strip()
            if not filepath:
                raise ValueError("Aucun fichier de maillage sélectionné.")
            vol_mesh = pre_mod.readMesh(filepath, 3)
            avatar = pre_mod.buildMeshedAvatar(
                mesh=vol_mesh,
                model=mod_obj,
                material=mat_obj,
            )
            return avatar

        else:
            raise ValueError(f"Géométrie 3D non supportée : '{geom_type}'")

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _collect_mat_properties(mat_page, mat_type_str):
        """\nCollecte les propriétés mécaniques saisies dans la page matériau.\nConstruit un dictionnaire compatible avec pre.material(**props).\n"""
        # Base commune à tous les types élastiques
        props = {
            "elas":       "standard",
            "anisotropy": "isotropic",
            "young":      mat_page.young_spin.value(),
            "nu":         mat_page.poisson_spin.value(),
        }

        if mat_type_str == "ELAS_DILA":
            props["dilatation"] = mat_page.dilatation_spin.value()
            props["T_ref_meca"] = mat_page.tref_spin.value()

        elif mat_type_str == "VISCO_ELAS":
            props["viscous_model"] = "KelvinVoigt"
            props["viscous_young"] = mat_page.viscous_young_spin.value()
            props["viscous_nu"]    = mat_page.viscous_nu_spin.value()

        elif mat_type_str == "ELAS_PLAS":
            props["critere"]    = "Von-Mises"
            props["isoh"]       = "linear"
            props["iso_hard"]   = mat_page.iso_hard_spin.value()
            props["isoh_coeff"] = mat_page.isoh_coeff_spin.value()
            props["cinh"]       = "none"
            props["visc"]       = "none"

        return props
    
    def _apply_boundary_conditions(self, mesh_obj, boundary_page):
        """\nConstruit les DOFOperation depuis les lignes de MeshBoundaryPage\net les transmet à controller.add_dof_operation() qui :\n- applique l'opération sur l'objet pylmgc90 via LMGC90Bridge\n- sauvegarde dans state.operations (visible dans l'onglet DOF)\n\nLes paramètres kwargs sont parsés depuis le texte libre de chaque\nQLineEdit (ex : 'component=[1,2], dofty="vlocy"').\n"""
        from ...core.models import DOFOperation
        from ...utils.safe_eval import SafeEvaluator

        _evaluator = SafeEvaluator()
        avatar_index = len(self.controller.state.avatars) - 1

        for condition in boundary_page.get_dof_conditions():
            dof_type   = condition["dof_type"]
            group      = condition["group"]
            params_str = condition["params_str"].strip()

            if not params_str:
                continue

            # Parser les kwargs depuis le texte libre
            # Exemple : 'component=[1,2], dofty="vlocy"'
            try:
                params = _evaluator.eval_dict(params_str)
            except Exception as exc:
                import warnings
                warnings.warn(
                    "DOF : impossible de parser les paramètres "
                    "\"{}\" — condition ignorée. ({})".format(params_str, exc)
                )
                continue

            # Ajouter le groupe comme paramètre pylmgc90
            params["group"] = group

            operation = DOFOperation(
                operation_type=dof_type,
                target_type="avatar",
                target_value=avatar_index,
                parameters=params,
            )

            # Applique ET sauvegarde dans state.operations
            self.controller.add_dof_operation(operation)


# ═══════════════════════════════════════════════════════════════════════════════
# Page 0 — Introduction
# ═══════════════════════════════════════════════════════════════════════════════

class MeshIntroPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("🔷 Assistant Corps Déformable")
        self.setSubTitle("Créez un corps déformable maillé avec des EF LMGC90.")

        layout = QVBoxLayout()
        intro = QLabel(
            "<h3>📋 Étapes :</h3>"
            "<ol>"
            "<li>✅ Choisir la dimension (2D ou 3D)</li>"
            "<li>✅ Définir le matériau déformable</li>"
            "<li>✅ Choisir le type d'élément fini</li>"
            "<li>✅ Sélectionner le type de maillage</li>"
            "<li>✅ Définir la géométrie</li>"
            "<li>✅ Configurer le raffinement du maillage</li>"
            "<li>✅ Appliquer les conditions aux limites</li>"
            "<li>✅ Générer le maillage</li>"
            "</ol>"
            "<p><b>💡 Astuce :</b> Les maillages permettent de simuler la déformation de solides.</p>"
            "<p><b>💡 Astuce :</b> Le maillage est construit via <code>buildMesh2D</code> "
            "ou <code>buildMeshH8</code> de pylmgc90 puis converti en avatar MAILx.</p>"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addStretch()
        self.setLayout(layout)


# ═══════════════════════════════════════════════════════════════════════════════
# Page 1 — Dimension
# ═══════════════════════════════════════════════════════════════════════════════

class MeshDimensionPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("📐 Dimension")
        self.setSubTitle("Choisissez si votre maillage sera 2D ou 3D.")

        layout = QVBoxLayout()
        group = QGroupBox("Dimension spatiale")
        g_layout = QVBoxLayout()

        self.dim_2d_radio = QRadioButton("2D — Maillage bidimensionnel")
        self.dim_2d_radio.setChecked(True)
        g_layout.addWidget(self.dim_2d_radio)

        info_2d = QLabel(
            "   💡 Éléments disponibles : T3, Q4, T6, Q8, Q9\n"
            "   Fonction pylmgc90 : pre.buildMesh2D()"
        )
        info_2d.setStyleSheet("color: gray; padding-left: 20px;")
        g_layout.addWidget(info_2d)
        g_layout.addSpacing(16)

        self.dim_3d_radio = QRadioButton("3D — Maillage tridimensionnel")
        g_layout.addWidget(self.dim_3d_radio)

        info_3d = QLabel(
            "   💡 Éléments disponibles : H8, H20, TE10, SHB8, SHB6\n"
            "   Fonction pylmgc90 : pre.buildMeshH8()"
        )
        info_3d.setStyleSheet("color: gray; padding-left: 20px;")
        g_layout.addWidget(info_3d)

        group.setLayout(g_layout)
        layout.addWidget(group)
        layout.addStretch()
        self.setLayout(layout)

# ═══════════════════════════════════════════════════════════════════════════════
# Page 2 — Matériau
# ═══════════════════════════════════════════════════════════════════════════════

class MeshMaterialPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("🧱 Matériau Déformable")
        self.setSubTitle("Sélectionnez ou créez un matériau élastique.")

        layout = QVBoxLayout()

        # ── Existants en premier ───────────────────────────────────────────────
        self.existing_group = QGroupBox("Utiliser un matériau existant")
        ef = QFormLayout()
        self.existing_mat_combo = QComboBox()
        ef.addRow("Sélectionner :", self.existing_mat_combo)
        self.existing_group.setLayout(ef)
        layout.addWidget(self.existing_group)

        # ── Créer nouveau ─────────────────────────────────────────────────────
        self.create_mat_check = QCheckBox("Créer un nouveau matériau à la place")
        self.create_mat_check.setChecked(False)
        self.create_mat_check.toggled.connect(self._toggle_mode)
        layout.addWidget(self.create_mat_check)

        self.new_mat_group = QGroupBox("Nouveau matériau")
        nf = QFormLayout()

        self.mat_name_input = QLineEdit("ELAS1")
        self.mat_name_input.setMaxLength(5)
        nf.addRow("Nom (max 5 car.) :", self.mat_name_input)

        self.mat_type_combo = QComboBox()
        self.mat_type_combo.addItems(_ELASTIC_TYPES)
        self.mat_type_combo.currentTextChanged.connect(self._on_mat_type_changed)
        nf.addRow("Type :", self.mat_type_combo)

        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(10.0, 25000.0)
        self.density_spin.setDecimals(1)
        self.density_spin.setValue(2700.0)
        self.density_spin.setSuffix(" kg/m³")
        nf.addRow("Densité :", self.density_spin)

        self.young_spin = QDoubleSpinBox()
        self.young_spin.setRange(1e3, 1e12)
        self.young_spin.setDecimals(3)
        self.young_spin.setValue(70e9)
        self.young_spin.setSuffix(" Pa")
        nf.addRow("Module de Young :", self.young_spin)

        self.poisson_spin = QDoubleSpinBox()
        self.poisson_spin.setRange(0.0, 0.4999)
        self.poisson_spin.setDecimals(4)
        self.poisson_spin.setValue(0.3)
        nf.addRow("Coefficient de Poisson (ν) :", self.poisson_spin)

        # ── Champs conditionnels ELAS_DILA ────────────────────────────────────
        self.dilatation_spin = QDoubleSpinBox()
        self.dilatation_spin.setRange(0.0, 1.0)
        self.dilatation_spin.setDecimals(6)
        self.dilatation_spin.setValue(1e-5)
        nf.addRow("Dilatation thermique :", self.dilatation_spin)

        self.tref_spin = QDoubleSpinBox()
        self.tref_spin.setRange(-273.15, 2000.0)
        self.tref_spin.setDecimals(2)
        self.tref_spin.setValue(20.0)
        self.tref_spin.setSuffix(" °C")
        nf.addRow("T_ref_meca :", self.tref_spin)

        # ── Champs conditionnels VISCO_ELAS ───────────────────────────────────
        self.viscous_young_spin = QDoubleSpinBox()
        self.viscous_young_spin.setRange(1e3, 1e12)
        self.viscous_young_spin.setDecimals(3)
        self.viscous_young_spin.setValue(1.17e9)
        self.viscous_young_spin.setSuffix(" Pa")
        nf.addRow("Young visqueux :", self.viscous_young_spin)

        self.viscous_nu_spin = QDoubleSpinBox()
        self.viscous_nu_spin.setRange(0.0, 0.4999)
        self.viscous_nu_spin.setDecimals(4)
        self.viscous_nu_spin.setValue(0.35)
        nf.addRow("Poisson visqueux :", self.viscous_nu_spin)

        # ── Champs conditionnels ELAS_PLAS ────────────────────────────────────
        self.iso_hard_spin = QDoubleSpinBox()
        self.iso_hard_spin.setRange(0.0, 1e12)
        self.iso_hard_spin.setDecimals(1)
        self.iso_hard_spin.setValue(4e8)
        self.iso_hard_spin.setSuffix(" Pa")
        nf.addRow("Limite élastique (iso_hard) :", self.iso_hard_spin)

        self.isoh_coeff_spin = QDoubleSpinBox()
        self.isoh_coeff_spin.setRange(0.0, 1e12)
        self.isoh_coeff_spin.setDecimals(1)
        self.isoh_coeff_spin.setValue(1e8)
        self.isoh_coeff_spin.setSuffix(" Pa")
        nf.addRow("Module d'écrouissage (isoh_coeff) :", self.isoh_coeff_spin)

        self.new_mat_group.setLayout(nf)
        self.new_mat_group.setVisible(False)
        layout.addWidget(self.new_mat_group)

        # Stocker les labels conditionnels pour les masquer/afficher
        self._conditional_rows = {
            "ELAS_DILA":  ["Dilatation thermique :", "T_ref_meca :"],
            "VISCO_ELAS": ["Young visqueux :", "Poisson visqueux :"],
            "ELAS_PLAS":  ["Limite élastique (iso_hard) :", "Module d'écrouissage (isoh_coeff) :"],
        }
        # Cache des formulaires
        self._nf = nf

        info = QLabel(
            "💡 <b>Rappel :</b> Les matériaux élastiques requièrent au minimum "
            "<code>elas='standard'</code>, <code>young</code>, <code>nu</code> "
            "et <code>anisotropy='isotropic'</code>."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background: #e3f2fd; padding: 8px; border-radius: 4px;")
        layout.addWidget(info)

        layout.addStretch()
        self.setLayout(layout)

        # Déclencher l'affichage initial des champs conditionnels
        self._on_mat_type_changed(self.mat_type_combo.currentText())

    def _toggle_mode(self, create_new):
        self.new_mat_group.setVisible(create_new)
        self.existing_group.setEnabled(not create_new)

    def _on_mat_type_changed(self, mat_type):
        """Affiche uniquement les champs pertinents pour le type de matériau."""
        active_labels = set(self._conditional_rows.get(mat_type, []))
        all_cond = {
            lbl
            for labels in self._conditional_rows.values()
            for lbl in labels
        }
        for i in range(self._nf.rowCount()):
            lbl_item = self._nf.itemAt(i, QFormLayout.ItemRole.LabelRole)
            fld_item = self._nf.itemAt(i, QFormLayout.ItemRole.FieldRole)
            if lbl_item and lbl_item.widget():
                text = lbl_item.widget().text()
                if text in all_cond:
                    visible = text in active_labels
                    lbl_item.widget().setVisible(visible)
                    if fld_item and fld_item.widget():
                        fld_item.widget().setVisible(visible)

    def initializePage(self):
        wizard    = self.wizard()
        materials = wizard.controller.get_materials()
        elastic   = [
            m for m in materials
            if m.material_type.value in _ELASTIC_TYPES
        ]
        self.existing_mat_combo.clear()
        if elastic:
            self.existing_mat_combo.addItems([m.name for m in elastic])
            self.existing_group.setEnabled(True)
            self.create_mat_check.setChecked(False)
            self._toggle_mode(False)
        else:
            self.existing_mat_combo.addItem("(Aucun matériau élastique)")
            self.existing_group.setEnabled(False)
            self.create_mat_check.setChecked(True)
            self._toggle_mode(True)


# ═══════════════════════════════════════════════════════════════════════════════
# Page 3 — Modèle EF
# ═══════════════════════════════════════════════════════════════════════════════

class MeshModelPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("⚙️ Modèle — Élément Fini")
        self.setSubTitle("Sélectionnez ou créez un modèle éléments finis.")

        layout = QVBoxLayout()

        # ── Existants en premier ───────────────────────────────────────────────
        self.existing_group = QGroupBox("Utiliser un modèle existant")
        ef = QFormLayout()
        self.existing_mod_combo = QComboBox()
        ef.addRow("Sélectionner :", self.existing_mod_combo)
        self.existing_group.setLayout(ef)
        layout.addWidget(self.existing_group)

        # ── Créer nouveau ─────────────────────────────────────────────────────
        self.create_mod_check = QCheckBox("Créer un nouveau modèle à la place")
        self.create_mod_check.setChecked(False)
        self.create_mod_check.toggled.connect(self._toggle_mode)
        layout.addWidget(self.create_mod_check)

        self.new_mod_group = QGroupBox("Nouveau modèle")
        nf = QFormLayout()

        self.mod_name_input = QLineEdit("femxx")
        self.mod_name_input.setMaxLength(5)
        nf.addRow("Nom (max 5 car.) :", self.mod_name_input)

        self.physics_combo = QComboBox()
        self.physics_combo.addItems(["MECAx", "THERx", "HYDRx"])
        nf.addRow("Physique :", self.physics_combo)

        self.element_combo = QComboBox()
        self.element_combo.currentTextChanged.connect(self._on_element_changed)
        nf.addRow("Élément fini :", self.element_combo)

        self.element_info_label = QLabel()
        self.element_info_label.setWordWrap(True)
        self.element_info_label.setStyleSheet(
            "background: #f5f5f5; padding: 6px; border-radius: 4px; font-size: 9pt;"
        )
        nf.addRow("", self.element_info_label)

        self.anisotropy_combo = QComboBox()
        self.anisotropy_combo.addItems(_ANISOTROPY)
        nf.addRow("Anisotropie :", self.anisotropy_combo)

        self.kinematic_combo = QComboBox()
        self.kinematic_combo.addItems(_KINEMATIC)
        nf.addRow("Cinématique :", self.kinematic_combo)

        self.formulation_combo = QComboBox()
        self.formulation_combo.addItems(_FORMULATION)
        nf.addRow("Formulation :", self.formulation_combo)

        self.mass_combo = QComboBox()
        self.mass_combo.addItems(_MASS_STORAGE)
        nf.addRow("Stockage masse :", self.mass_combo)

        self.new_mod_group.setLayout(nf)
        self.new_mod_group.setVisible(False)
        layout.addWidget(self.new_mod_group)

        layout.addStretch()
        self.setLayout(layout)

    def _toggle_mode(self, create_new):
        self.new_mod_group.setVisible(create_new)
        self.existing_group.setEnabled(not create_new)

    def _on_element_changed(self, element):
        self.element_info_label.setText(_ELEMENT_INFO.get(element, ""))

    def initializePage(self):
        wizard    = self.wizard()
        dim_page  = wizard.page(MeshWizard.PAGE_DIM)
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3

        # Éléments compatibles avec la dimension
        self.element_combo.blockSignals(True)
        self.element_combo.clear()
        self.element_combo.addItems(_ELEMENTS_2D if dimension == 2 else _ELEMENTS_3D)
        self.element_combo.blockSignals(False)
        self._on_element_changed(self.element_combo.currentText())

        # Modèles existants compatibles
        models    = wizard.controller.get_models()
        compat    = [m for m in models if m.dimension == dimension]
        self.existing_mod_combo.clear()
        if compat:
            self.existing_mod_combo.addItems([m.name for m in compat])
            self.existing_group.setEnabled(True)
            self.create_mod_check.setChecked(False)
            self._toggle_mode(False)
        else:
            self.existing_mod_combo.addItem(f"(Aucun modèle {dimension}D)")
            self.existing_group.setEnabled(False)
            self.create_mod_check.setChecked(True)
            self._toggle_mode(True)


# ═══════════════════════════════════════════════════════════════════════════════
# Page 4 — Géométrie
# ═══════════════════════════════════════════════════════════════════════════════

class MeshGeometryPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("📏 Géométrie")
        self.setSubTitle("Définissez la forme et les dimensions de votre corps.")

        # Un seul QFormLayout pour toute la page
        self.form = QFormLayout()
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        self.geom_type_combo = QComboBox()
        self.geom_type_combo.currentTextChanged.connect(self._on_type_changed)
        self.form.addRow("Forme :", self.geom_type_combo)

        self.cx_spin = QDoubleSpinBox()
        self.cx_spin.setRange(-1000.0, 1000.0); self.cx_spin.setDecimals(4)
        self.form.addRow("Centre X (m) :", self.cx_spin)

        self.cy_spin = QDoubleSpinBox()
        self.cy_spin.setRange(-1000.0, 1000.0); self.cy_spin.setDecimals(4)
        self.form.addRow("Centre Y (m) :", self.cy_spin)

        self.cz_spin = QDoubleSpinBox()
        self.cz_spin.setRange(-1000.0, 1000.0); self.cz_spin.setDecimals(4)
        self.form.addRow("Centre Z (m) :", self.cz_spin)

        self.lx_spin = QDoubleSpinBox()
        self.lx_spin.setRange(1e-6, 1e6); self.lx_spin.setDecimals(4)
        self.lx_spin.setValue(1.0); self.lx_spin.setSuffix(" m")
        self.form.addRow("Longueur X (lx) :", self.lx_spin)

        self.ly_spin = QDoubleSpinBox()
        self.ly_spin.setRange(1e-6, 1e6); self.ly_spin.setDecimals(4)
        self.ly_spin.setValue(1.0); self.ly_spin.setSuffix(" m")
        self.form.addRow("Longueur Y (ly) :", self.ly_spin)

        self.lz_spin = QDoubleSpinBox()
        self.lz_spin.setRange(1e-6, 1e6); self.lz_spin.setDecimals(4)
        self.lz_spin.setValue(1.0); self.lz_spin.setSuffix(" m")
        self.form.addRow("Longueur Z (lz) :", self.lz_spin)

        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(1e-6, 1e6); self.radius_spin.setDecimals(4)
        self.radius_spin.setValue(0.5); self.radius_spin.setSuffix(" m")
        self.form.addRow("Rayon (r) :", self.radius_spin)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1e-6, 1e6); self.height_spin.setDecimals(4)
        self.height_spin.setValue(1.0); self.height_spin.setSuffix(" m")
        self.form.addRow("Hauteur (h) :", self.height_spin)

        file_widget = QWidget()
        file_layout = QHBoxLayout(file_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("chemin/vers/maillage.msh")
        file_layout.addWidget(self.file_path_input)
        browse_btn = QPushButton("📁 Parcourir")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        self.form.addRow("Fichier maillage :", file_widget)

        layout = QVBoxLayout()
        layout.addLayout(self.form)
        layout.addStretch()
        self.setLayout(layout)

    def _browse_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner un fichier maillage",
            "", "Maillages (*.msh *.vtk *.mesh);;Tous (*)"
        )
        if filepath:
            self.file_path_input.setText(filepath)

    def _set_row_visible(self, label_text, visible):
        for i in range(self.form.rowCount()):
            lbl = self.form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            fld = self.form.itemAt(i, QFormLayout.ItemRole.FieldRole)
            if lbl and lbl.widget() and lbl.widget().text() == label_text:
                lbl.widget().setVisible(visible)
                if fld and fld.widget():
                    fld.widget().setVisible(visible)

    def _on_type_changed(self, geom_type):
        is_rect     = geom_type == "Rectangle"
        is_box      = geom_type == "Boîte (H8)"
        is_disk     = geom_type == "Disque"
        is_sphere   = geom_type == "Sphère"
        is_cylinder = geom_type == "Cylindre"
        is_file     = geom_type == "Fichier externe"

        self._set_row_visible("Longueur X (lx) :", is_rect or is_box)
        self._set_row_visible("Longueur Y (ly) :", is_rect or is_box)
        self._set_row_visible("Longueur Z (lz) :", is_box)
        self._set_row_visible("Rayon (r) :",       is_disk or is_sphere or is_cylinder)
        self._set_row_visible("Hauteur (h) :",     is_cylinder)
        self._set_row_visible("Fichier maillage :", is_file)

    def initializePage(self):
        wizard    = self.wizard()
        dim_page  = wizard.page(MeshWizard.PAGE_DIM)
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3

        self.geom_type_combo.blockSignals(True)
        self.geom_type_combo.clear()
        if dimension == 2:
            self.geom_type_combo.addItems(["Rectangle", "Disque", "Fichier externe"])
        else:
            self.geom_type_combo.addItems(["Boîte (H8)", "Sphère", "Cylindre", "Fichier externe"])
        self.geom_type_combo.blockSignals(False)

        self._set_row_visible("Centre Z (m) :", dimension == 3)
        self._on_type_changed(self.geom_type_combo.currentText())

    def get_center(self, dimension):
        if dimension == 2:
            return [self.cx_spin.value(), self.cy_spin.value()]
        return [self.cx_spin.value(), self.cy_spin.value(), self.cz_spin.value()]


# ═══════════════════════════════════════════════════════════════════════════════
# Page 5 — Raffinement
# ═══════════════════════════════════════════════════════════════════════════════

class MeshRefinementPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("🔢 Raffinement du maillage")
        self.setSubTitle("Définissez la finesse du maillage.")

        self.form = QFormLayout()

        self.mesh_type_combo = QComboBox()
        self.mesh_type_combo.addItems(_MESH_TYPES_2D)
        self.mesh_type_combo.currentTextChanged.connect(self._on_mesh_type_changed)
        self.form.addRow("Type structuré :", self.mesh_type_combo)

        self.mesh_type_info = QLabel()
        self.mesh_type_info.setWordWrap(True)
        self.mesh_type_info.setStyleSheet("color: gray; font-size: 9pt;")
        self.form.addRow("", self.mesh_type_info)

        self.nx_spin = QSpinBox()
        self.nx_spin.setRange(1, 500); self.nx_spin.setValue(10)
        self.form.addRow("Éléments en X (nx) :", self.nx_spin)

        self.ny_spin = QSpinBox()
        self.ny_spin.setRange(1, 500); self.ny_spin.setValue(10)
        self.form.addRow("Éléments en Y (ny) :", self.ny_spin)

        self.nz_spin = QSpinBox()
        self.nz_spin.setRange(1, 500); self.nz_spin.setValue(5)
        self.form.addRow("Éléments en Z (nz) :", self.nz_spin)

        self.nr_spin = QSpinBox()
        self.nr_spin.setRange(2, 200); self.nr_spin.setValue(5)
        self.form.addRow("Éléments radiaux (nr) :", self.nr_spin)

        self.ntheta_spin = QSpinBox()
        self.ntheta_spin.setRange(4, 200); self.ntheta_spin.setValue(16)
        self.form.addRow("Éléments angulaires (ntheta) :", self.ntheta_spin)

        self.nphi_spin = QSpinBox()
        self.nphi_spin.setRange(4, 200); self.nphi_spin.setValue(8)
        self.form.addRow("Éléments en phi (nphi) :", self.nphi_spin)

        self.count_label = QLabel()
        self.count_label.setStyleSheet(
            "background: #e8f5e9; padding: 6px; border-radius: 4px; font-weight: bold;"
        )

        for spin in (self.nx_spin, self.ny_spin, self.nz_spin,
                     self.nr_spin, self.ntheta_spin, self.nphi_spin):
            spin.valueChanged.connect(self._update_count)

        layout = QVBoxLayout()
        layout.addLayout(self.form)
        layout.addWidget(self.count_label)
        layout.addStretch()
        self.setLayout(layout)

    def _set_row_visible(self, label_text, visible):
        for i in range(self.form.rowCount()):
            lbl = self.form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            fld = self.form.itemAt(i, QFormLayout.ItemRole.FieldRole)
            if lbl and lbl.widget() and lbl.widget().text() == label_text:
                lbl.widget().setVisible(visible)
                if fld and fld.widget():
                    fld.widget().setVisible(visible)

    def _on_mesh_type_changed(self, t):
        infos = {
            "Q4":  "Quadrangles bilinéaires à 4 nœuds",
            "2T3": "Triangles à 3 nœuds (Q4 coupé en 2)",
            "4T3": "Triangles à 3 nœuds (Q4 coupé en 4)",
            "Q8":  "Quadrangles serendipity à 8 nœuds",
        }
        self.mesh_type_info.setText(infos.get(t, ""))

    def _update_count(self):
        wizard = self.wizard()
        if wizard is None:
            return
        geom_page = wizard.page(MeshWizard.PAGE_GEOM)
        geom_type = geom_page.geom_type_combo.currentText() if geom_page else ""
        counts = {
            "Rectangle":  self.nx_spin.value() * self.ny_spin.value(),
            "Disque":     self.nr_spin.value() * self.ntheta_spin.value(),
            "Boîte (H8)": self.nx_spin.value() * self.ny_spin.value() * self.nz_spin.value(),
            "Sphère":     self.nr_spin.value() * self.ntheta_spin.value() * self.nphi_spin.value(),
            "Cylindre":   self.nr_spin.value() * self.ntheta_spin.value() * self.nz_spin.value(),
        }
        n = counts.get(geom_type, 0)
        self.count_label.setText(f"📊 Éléments estimés : {n}")

    def initializePage(self):
        wizard    = self.wizard()
        geom_page = wizard.page(MeshWizard.PAGE_GEOM)
        geom_type = geom_page.geom_type_combo.currentText() if geom_page else ""

        # Type structuré uniquement pour Rectangle
        self._set_row_visible("Type structuré :", geom_type == "Rectangle")
        self._set_row_visible("", geom_type == "Rectangle")  # ligne info

        visible_map = {
            "Rectangle":  ["Éléments en X (nx) :", "Éléments en Y (ny) :"],
            "Disque":     ["Éléments radiaux (nr) :", "Éléments angulaires (ntheta) :"],
            "Boîte (H8)": ["Éléments en X (nx) :", "Éléments en Y (ny) :", "Éléments en Z (nz) :"],
            "Sphère":     ["Éléments radiaux (nr) :", "Éléments angulaires (ntheta) :", "Éléments en phi (nphi) :"],
            "Cylindre":   ["Éléments radiaux (nr) :", "Éléments angulaires (ntheta) :", "Éléments en Z (nz) :"],
        }
        all_rows = [
            "Éléments en X (nx) :", "Éléments en Y (ny) :", "Éléments en Z (nz) :",
            "Éléments radiaux (nr) :", "Éléments angulaires (ntheta) :", "Éléments en phi (nphi) :",
        ]
        to_show = set(visible_map.get(geom_type, []))
        for label in all_rows:
            self._set_row_visible(label, label in to_show)

        self._on_mesh_type_changed(self.mesh_type_combo.currentText())
        self._update_count()


# ═══════════════════════════════════════════════════════════════════════════════
# Page 6 — Boundary Conditions
# ═══════════════════════════════════════════════════════════════════════════════

class MeshBoundaryPage(QWizardPage):
    """\nPage des conditions aux limites (DOF).\n\nUI : pour chaque condition, l'utilisateur choisit\n- un groupe de surface via QComboBox (down/up/left/right/front/rear)\n- les paramètres DOF via QLineEdit texte libre, exactement comme\ndans le dof_tab : ex.  component=[1,2], dofty="vlocy"\n\nÀ la génération, chaque ligne est convertie en DOFOperation et transmise\nà controller.add_dof_operation() qui applique ET sauvegarde dans\nstate.operations (visible dans l'onglet DOF).\n"""

    # Groupes créés automatiquement par buildMesh2D et buildMeshH8
    _GROUPS_2D = ["down", "up", "left", "right"]
    _GROUPS_3D = ["down", "up", "left", "right", "front", "rear"]

    # Exemples de paramètres pour l'aide contextuelle
    _PARAM_EXAMPLES = (
        "Exemples de paramètres :\n"
        "  translation :  dx=0.0, dy= 1.0\"\n"
        "  rotation :   psi = -2*math.pi/3, center=[0.0, 0.0]\n"
        "  imposeDrivenDof  :   component=[1,2], dofty='vlocy'\n"
        "  imposeInitValue  :   component=[1,2,3], value=3.0\n"
    )

    def __init__(self):
        super().__init__()
        self.setTitle("🔒 Conditions aux Limites (DOF)")
        self.setSubTitle(
            "Définissez les conditions DOF sur les groupes de surface du maillage."
        )
        self._dof_rows = []
        main_layout = QVBoxLayout(self)

        # ── Note explicative ─────────────────────────────────────────────────
        note = QLabel(
            "💡 <b>Groupes :</b> "
            "<code>down</code> · <code>up</code> · "
            "<code>left</code> · <code>right</code>"
            " · <code>front</code> / <code>rear</code> (3D).<br>"
            "<b>Type :</b> "
            "<code>translation</code> ou <code>rotation</code> pour les conditions classiques, "
            "<code>imposeDrivenDof</code> ou <code>imposeInitValue</code>.<br>"
            "<b>Paramètres :</b> écrire directement les kwargs pylmgc90, "
            "ex : <code>component=[1,2], dofty=&quot;vlocy&quot;</code>"
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "background:#eaf4fb; padding:8px; border-radius:4px; font-size:9pt;"
        )
        main_layout.addWidget(note)

        # ── En-tête colonnes ─────────────────────────────────────────────────
        hdr = QHBoxLayout()
        for txt, w in [
            ("Type DOF",   150),
            ("Groupe",      90),
            ("Paramètres (kwargs pylmgc90)", 300),
        ]:
            lbl = QLabel("<b>{}</b>".format(txt))
            lbl.setFixedWidth(w)
            hdr.addWidget(lbl)
        hdr.addStretch()
        main_layout.addLayout(hdr)

        # ── Zone de lignes ───────────────────────────────────────────────────
        self._rows_widget = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(3)
        main_layout.addWidget(self._rows_widget)

        btn_add = QPushButton("+ Ajouter une condition DOF")
        btn_add.clicked.connect(self._add_dof_row)
        main_layout.addWidget(btn_add)

        # Attributs fantômes pour compatibilité avec l'ancien code
        for attr in ("fix_bottom_check", "fix_top_check", "fix_left_check",
                     "fix_right_check", "fix_front_check", "fix_rear_check",
                     "apply_load_check"):
            setattr(self, attr, QCheckBox())

        main_layout.addStretch()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _is_3d(self) -> bool:
        wiz = self.wizard()
        if wiz is None:
            return False
        return not wiz.page(MeshWizard.PAGE_DIM).dim_2d_radio.isChecked()

    def _add_dof_row(self, entry: dict = None):
        """\nAjoute une ligne de condition DOF.\nentry = dict optionnel : {"dof_type", "group", "params_str"}\n"""
        entry   = entry or {}
        is_3d   = self._is_3d()
        groups  = self._GROUPS_3D if is_3d else self._GROUPS_2D

        row_w   = QWidget()
        row_lay = QHBoxLayout(row_w)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(4)

        # ── Type DOF ─────────────────────────────────────────────────────────
        combo_type = QComboBox()
        combo_type.setFixedWidth(150)
        combo_type.addItem("translation")
        combo_type.addItem("rotation")  
        combo_type.addItem("imposeDrivenDof")
        combo_type.addItem("imposeInitValue")
       
        if entry.get("dof_type") in ("translation", "rotation", "imposeDrivenDof", "imposeInitValue"):
            combo_type.setCurrentText(entry["dof_type"])
        combo_type.setToolTip(
            "translation : translation \n"
            "rotation : rotation \n"
            "imposeDrivenDof : DDL piloté (déplacement ou force ou flux imposée)\n"
            "imposeInitValue : condition initiale (position ou vitesse)"
        )
        row_lay.addWidget(combo_type)

        # ── Groupe ───────────────────────────────────────────────────────────
        combo_grp = QComboBox()
        combo_grp.setFixedWidth(90)
        combo_grp.addItems(groups)
        if entry.get("group") in groups:
            combo_grp.setCurrentText(entry["group"])
        combo_grp.setToolTip(
            "Groupe de surface du maillage.\n"
            "Créé automatiquement par buildMesh2D / buildMeshH8."
        )
        row_lay.addWidget(combo_grp)

        # ── Paramètres kwargs ────────────────────────────────────────────────
        edit_params = QLineEdit()
        edit_params.setMinimumWidth(300)
        edit_params.setPlaceholderText(
            'ex : component=[1,2], dofty="vlocy"'
        )
        edit_params.setText(entry.get("params_str", ""))
        edit_params.setToolTip(self._PARAM_EXAMPLES)
        row_lay.addWidget(edit_params, stretch=1)

        # ── Bouton supprimer ─────────────────────────────────────────────────
        btn_del = QPushButton("x")
        btn_del.setFixedWidth(24)
        row_data = {
            "widget":      row_w,
            "combo_type":  combo_type,
            "combo_grp":   combo_grp,
            "edit_params": edit_params,
        }
        def _make_del(rd=row_data):
            def _do():
                self._dof_rows.remove(rd)
                self._rows_layout.removeWidget(rd["widget"])
                rd["widget"].deleteLater()
            return _do
        btn_del.clicked.connect(_make_del())
        row_lay.addWidget(btn_del)

        self._rows_layout.addWidget(row_w)
        self._dof_rows.append(row_data)

    def _read_dof_row(self, row: dict) -> dict:
        """Lit une ligne et retourne un dict sérialisable."""
        return {
            "dof_type":  row["combo_type"].currentText(),
            "group":     row["combo_grp"].currentText(),
            "params_str": row["edit_params"].text().strip(),
        }

    def get_dof_conditions(self) -> list:
        """Retourne la liste des conditions DOF configurées."""
        return [self._read_dof_row(r) for r in self._dof_rows]

    def initializePage(self):
        """Met à jour les combos groupe selon la dimension."""
        is_3d  = self._is_3d()
        groups = self._GROUPS_3D if is_3d else self._GROUPS_2D
        for row in self._dof_rows:
            cur = row["combo_grp"].currentText()
            row["combo_grp"].blockSignals(True)
            row["combo_grp"].clear()
            row["combo_grp"].addItems(groups)
            if cur in groups:
                row["combo_grp"].setCurrentText(cur)
            row["combo_grp"].blockSignals(False)
# ═══════════════════════════════════════════════════════════════════════════════
# Page 7 — Récapitulatif
# ═══════════════════════════════════════════════════════════════════════════════

class MeshSummaryPage(QWizardPage):

    def __init__(self):
        super().__init__()
        self.setTitle("📋 Récapitulatif")
        self.setSubTitle("Vérifiez la configuration avant de générer le maillage.")

        layout = QVBoxLayout()
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)
        self.setLayout(layout)

    def initializePage(self):
        wizard     = self.wizard()
        dim_page   = wizard.page(MeshWizard.PAGE_DIM)
        mat_page   = wizard.page(MeshWizard.PAGE_MAT)
        mod_page   = wizard.page(MeshWizard.PAGE_MODEL)
        geom_page  = wizard.page(MeshWizard.PAGE_GEOM)
        ref_page   = wizard.page(MeshWizard.PAGE_REFINE)
        bound_page = wizard.page(MeshWizard.PAGE_BOUNDARY)

        dimension  = "2D" if dim_page.dim_2d_radio.isChecked() else "3D"
        geom_type  = geom_page.geom_type_combo.currentText()
        mesh_type  = ref_page.mesh_type_combo.currentText() if dimension == "2D" else "H8"

        # ── Géométrie ─────────────────────────────────────────────────────────
        if geom_type in ("Rectangle", "Boîte (H8)"):
            lx = geom_page.lx_spin.value()
            ly = geom_page.ly_spin.value()
            dims_html = f"<li><b>lx</b> = {lx:.4f} m &nbsp; <b>ly</b> = {ly:.4f} m"
            if dimension == "3D":
                lz = geom_page.lz_spin.value()
                dims_html += f" &nbsp; <b>lz</b> = {lz:.4f} m"
            dims_html += "</li>"
        elif geom_type == "Disque":
            dims_html = f"<li><b>Rayon :</b> {geom_page.radius_spin.value():.4f} m</li>"
        elif geom_type == "Sphère":
            dims_html = f"<li><b>Rayon :</b> {geom_page.radius_spin.value():.4f} m</li>"
        elif geom_type == "Cylindre":
            dims_html = (
                f"<li><b>Rayon :</b> {geom_page.radius_spin.value():.4f} m &nbsp;"
                f"<b>Hauteur :</b> {geom_page.height_spin.value():.4f} m</li>"
            )
        else:
            dims_html = f"<li><b>Fichier :</b> {geom_page.file_path_input.text()}</li>"

        cx = geom_page.cx_spin.value()
        cy = geom_page.cy_spin.value()
        center_str = f"({cx:.3f}, {cy:.3f}"
        if dimension == "3D":
            cz = geom_page.cz_spin.value()
            center_str += f", {cz:.3f}"
        center_str += ")"

        # ── Raffinement ───────────────────────────────────────────────────────
        if geom_type == "Rectangle":
            n_elem = ref_page.nx_spin.value() * ref_page.ny_spin.value()
            ref_html = (
                f"<li>{ref_page.nx_spin.value()} × {ref_page.ny_spin.value()} "
                f"= <b>{n_elem}</b> éléments estimés</li>"
                f"<li>Type structuré : {ref_page.mesh_type_combo.currentText()}</li>"
            )
        elif geom_type == "Disque":
            n_elem = ref_page.nr_spin.value() * ref_page.ntheta_spin.value()
            ref_html = (
                f"<li>nr = {ref_page.nr_spin.value()} &nbsp;"
                f"ntheta = {ref_page.ntheta_spin.value()} "
                f"→ <b>{n_elem}</b> éléments estimés</li>"
            )
        elif geom_type == "Boîte (H8)":
            n_elem = ref_page.nx_spin.value() * ref_page.ny_spin.value() * ref_page.nz_spin.value()
            ref_html = (
                f"<li>{ref_page.nx_spin.value()} × {ref_page.ny_spin.value()} × "
                f"{ref_page.nz_spin.value()} = <b>{n_elem}</b> éléments estimés</li>"
            )
        elif geom_type == "Sphère":
            n_elem = ref_page.nr_spin.value() * ref_page.ntheta_spin.value() * ref_page.nphi_spin.value()
            ref_html = (
                f"<li>nr = {ref_page.nr_spin.value()} &nbsp;"
                f"ntheta = {ref_page.ntheta_spin.value()} &nbsp;"
                f"nphi = {ref_page.nphi_spin.value()} "
                f"→ <b>{n_elem}</b> éléments estimés</li>"
            )
        elif geom_type == "Cylindre":
            n_elem = ref_page.nr_spin.value() * ref_page.ntheta_spin.value() * ref_page.nz_spin.value()
            ref_html = (
                f"<li>nr = {ref_page.nr_spin.value()} &nbsp;"
                f"ntheta = {ref_page.ntheta_spin.value()} &nbsp;"
                f"nz = {ref_page.nz_spin.value()} "
                f"→ <b>{n_elem}</b> éléments estimés</li>"
            )
        else:
            ref_html = "<li>Maillage depuis fichier — raffinement non estimable</li>"

        # ── Matériau ──────────────────────────────────────────────────────────
        if mat_page.create_mat_check.isChecked():
            mat_html = (
                f"<li><b>Nom :</b> {mat_page.mat_name_input.text()}</li>"
                f"<li><b>Type :</b> {mat_page.mat_type_combo.currentText()}</li>"
                f"<li><b>Densité :</b> {mat_page.density_spin.value():.1f} kg/m³</li>"
                f"<li><b>Young :</b> {mat_page.young_spin.value():.3e} Pa &nbsp;"
                f"<b>ν :</b> {mat_page.poisson_spin.value():.4f}</li>"
            )
        else:
            mat_html = f"<li><b>Existant :</b> {mat_page.existing_mat_combo.currentText()}</li>"

        # ── Modèle ────────────────────────────────────────────────────────────
        if mod_page.create_mod_check.isChecked():
            mod_html = (
                f"<li><b>Nom :</b> {mod_page.mod_name_input.text()}</li>"
                f"<li><b>Physique :</b> {mod_page.physics_combo.currentText()}</li>"
                f"<li><b>Élément :</b> {mod_page.element_combo.currentText()} "
                f"— {_ELEMENT_INFO.get(mod_page.element_combo.currentText(), '')}</li>"
                f"<li><b>Anisotropie :</b> {mod_page.anisotropy_combo.currentText()} &nbsp;"
                f"<b>Cinématique :</b> {mod_page.kinematic_combo.currentText()}</li>"
                f"<li><b>Formulation :</b> {mod_page.formulation_combo.currentText()} &nbsp;"
                f"<b>Masse :</b> {mod_page.mass_combo.currentText()}</li>"
            )
        else:
            mod_html = f"<li><b>Existant :</b> {mod_page.existing_mod_combo.currentText()}</li>"

        # ── Conditions aux Limites (DOF) ──────────────────────────────────────
        dof_conds = bound_page.get_dof_conditions()
        if dof_conds:
            cl_html = "".join(
                "<li><b>{}</b> — groupe <code>{}</code>"
                " &nbsp; <code>{}</code></li>".format(
                    c["dof_type"], c["group"], c["params_str"] or "(vide)"
                )
                for c in dof_conds
            )
        else:
            cl_html = "<li><i>Aucune condition DOF définie.</i></li>"

        html = f"""\n<h2>🔷 Corps Déformable {dimension}</h2>\n\n<h3>📐 Géométrie</h3>\n<ul>\n<li><b>Forme :</b> {geom_type}</li>\n<li><b>Type de maillage :</b> {mesh_type}</li>\n{dims_html}\n<li><b>Centre :</b> {center_str}</li>\n</ul>\n\n<h3>🔢 Raffinement</h3>\n<ul>\n{ref_html}\n</ul>\n\n<h3>🧱 Matériau</h3>\n<ul>\n{mat_html}\n</ul>\n\n<h3>⚙️ Modèle EF</h3>\n<ul>\n{mod_html}\n</ul>\n\n<h3>🔒 Conditions aux Limites (mémo)</h3>\n<ul>\n{cl_html}\n</ul>\n\n<hr>\n<h3 style="color: green;">✅ Prêt à générer !</h3>\n<p><b>Cliquez sur « Générer le maillage » pour créer le corps déformable.</b></p>\n<p style="color: #888;">\n⚠️ La génération peut prendre quelques secondes selon la finesse du maillage.\n</p>\n"""
        self.summary_text.setHtml(html)