# ============================================================================
# mesh_wizard_deformable.py
# Assistant pour création de corps déformables (mesh2d / mesh3d)
# ============================================================================
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QLabel, QSpinBox, QDoubleSpinBox, QRadioButton,
    QGroupBox, QHBoxLayout, QCheckBox, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt
import numpy as np

from ...core.models import Material, Model, Avatar
from ...controllers.project_controller import ProjectController
from ...core.models import AvatarType, AvatarOrigin, MaterialType
from pylmgc90 import pre


class MeshWizard(QWizard):
    """Assistant création corps déformable (éléments finis)"""
    
    PAGE_INTRO = 0
    PAGE_DIM = 1
    PAGE_GEOM = 2
    PAGE_MESH = 3
    PAGE_MAT = 4
    PAGE_MODEL = 5
    PAGE_SUMMARY = 6
    
    def __init__(self, controller: ProjectController, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        self.setWindowTitle("🛠 Assistant Corps Déformable")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)
        self.resize(800, 600)
        
        self.addPage(IntroPage())
        self.addPage(DimensionPage())
        self.addPage(GeometryPage())
        self.addPage(MeshParamsPage())
        self.addPage(MaterialPage(self.controller))
        self.addPage(ModelPage(self.controller))
        self.addPage(SummaryPage())
        
        self.button(QWizard.WizardButton.FinishButton).setText("Créer l'avatar")
        self.button(QWizard.WizardButton.FinishButton).clicked.connect(self._generate_avatar)
    
    def _generate_avatar(self):
        try:
            dim = self.field("dimension")
            geom_type = self.field("geom_type")
            lx = self.field("lx")
            ly = self.field("ly")
            lz = self.field("lz") if dim == 3 else 0
            nx = self.field("nx")
            ny = self.field("ny")
            nz = self.field("nz") if dim == 3 else 1
            
            material = self.field("material")
            model = self.field("model")
            
            # Création du maillage
            if dim == 2:
                if geom_type == "rectangle":
                    mesh = pre.buildMesh2D(
                        type=model.element,   # ex: 'Q4xxx', 'T3xxx'
                        x0=0.0, y0=0.0,
                        lx=lx, ly=ly,
                        nb_elem_x=nx,
                        nb_elem_y=ny
                    )
                else:
                    raise NotImplementedError("Géométrie 2D non implémentée")
            else:  # 3D
                if geom_type == "box":
                    mesh = pre.buildMeshH8(   # ou buildMesh3D selon version
                        x0=0., y0=0., z0=0.,
                        lx=lx, ly=ly, lz=lz,
                        nb_elem_x=nx,
                        nb_elem_y=ny,
                        nb_elem_z=nz
                    )
                else:
                    raise NotImplementedError("Géométrie 3D non implémentée")
            
            # Création de l'avatar déformable
            avatar_pylmgc = pre.buildMeshedAvatar(
                mesh=mesh,
                model=model.name,      # nom du modèle
                material=material.name,
                color="GREENx"         # ou BLUEy, etc.
            )
            
            # Conversion vers ton modèle interne (à adapter selon ta classe Avatar)
            avatar = Avatar(
                avatar_type=AvatarType.MESH_DEFORMABLE,
                center=[0, 0, 0] if dim == 3 else [0, 0],
                material_name=material.name,
                model_name=model.name,
                color="GREENx",
                origin=AvatarOrigin.MANUAL,
                # Tu peux stocker plus d'infos si besoin (mesh, etc.)
            )
            
            # Ajout au projet
            self.controller.add_avatar(avatar)  # ← ta méthode existante
            
            # Optionnel : ajouter des groupes automatiques pour CL
            # avatar.addGroupFromConnectivity('BORD_GAUCHE', mesh.getBoundaryNodes('left'))
            
            QMessageBox.information(self, "Succès", 
                                  f"Avatar déformable créé !\n"
                                  f"{len(mesh.nodes)} nœuds, {len(mesh.bulks)} éléments")
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de la génération :\n{str(e)}")


# ──────────────────────────────────────────────── Pages ────────────────────────────────────────────────

class IntroPage(QWizardPage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel(
            "<h2>Création d'un corps déformable</h2>"
            "<p>Cet assistant permet de générer un maillage structuré simple "
            "(rectangle 2D ou boîte 3D) et de le transformer en avatar déformable.</p>"
        ))
        self.setLayout(layout)


class DimensionPage(QWizardPage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.dim_2d = QRadioButton("2D (plan)")
        self.dim_3d = QRadioButton("3D (volume)")
        self.dim_2d.setChecked(True)
        
        layout.addWidget(QLabel("Dimension du problème :"))
        layout.addWidget(self.dim_2d)
        layout.addWidget(self.dim_3d)
        self.setLayout(layout)
        
        self.registerField("dimension", self.dim_2d, "checked", self.dim_2d.toggled)
        self.dim_2d.toggled.connect(lambda c: self.setField("dimension", 2 if c else 3))


class GeometryPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.form = QFormLayout()
        self.layout.addLayout(self.form)
        self.setLayout(self.layout)
    
    def initializePage(self):
        for i in reversed(range(self.form.count())): 
            w = self.form.itemAt(i).widget()
            if w: w.setParent(None)
        
        dim = self.field("dimension")
        
        self.geom_combo = QComboBox()
        if dim == 2:
            self.geom_combo.addItems(["rectangle"])
        else:
            self.geom_combo.addItems(["box"])
        self.form.addRow("Géométrie :", self.geom_combo)
        
        self.lx = QDoubleSpinBox()
        self.lx.setRange(0.01, 1000)
        self.lx.setValue(1.0)
        self.lx.setDecimals(3)
        self.form.addRow("Longueur X (m) :", self.lx)
        
        self.ly = QDoubleSpinBox()
        self.ly.setRange(0.01, 1000)
        self.ly.setValue(1.0)
        self.ly.setDecimals(3)
        self.form.addRow("Longueur Y (m) :", self.ly)
        
        if dim == 3:
            self.lz = QDoubleSpinBox()
            self.lz.setRange(0.01, 1000)
            self.lz.setValue(1.0)
            self.lz.setDecimals(3)
            self.form.addRow("Longueur Z (m) :", self.lz)
        
        self.registerField("geom_type", self.geom_combo, "currentText")
        self.registerField("lx", self.lx, "value")
        self.registerField("ly", self.ly, "value")
        if dim == 3:
            self.registerField("lz", self.lz, "value")


class MeshParamsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.form = QFormLayout()
        self.layout.addLayout(self.form)
        self.setLayout(self.layout)
    
    def initializePage(self):
        for i in reversed(range(self.form.count())): 
            w = self.form.itemAt(i).widget()
            if w: w.setParent(None)
        
        dim = self.field("dimension")
        
        self.nx = QSpinBox()
        self.nx.setRange(2, 500)
        self.nx.setValue(20)
        self.form.addRow("Nb éléments en X :", self.nx)
        
        self.ny = QSpinBox()
        self.ny.setRange(2, 500)
        self.ny.setValue(10)
        self.form.addRow("Nb éléments en Y :", self.ny)
        
        if dim == 3:
            self.nz = QSpinBox()
            self.nz.setRange(2, 500)
            self.nz.setValue(10)
            self.form.addRow("Nb éléments en Z :", self.nz)
        
        self.registerField("nx", self.nx, "value")
        self.registerField("ny", self.ny, "value")
        if dim == 3:
            self.registerField("nz", self.nz, "value")


class MaterialPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        layout = QVBoxLayout()
        
        self.new_mat = QCheckBox("Créer un nouveau matériau")
        self.new_mat.toggled.connect(self._toggle)
        layout.addWidget(self.new_mat)
        
        self.new_group = QGroupBox("Nouveau matériau")
        f = QFormLayout()
        self.mat_name = QLineEdit("MATxx")
        f.addRow("Nom :", self.mat_name)
        self.density = QDoubleSpinBox(value=7800, maximum=20000)
        f.addRow("Densité :", self.density)
        self.young = QDoubleSpinBox(value=210e9, maximum=1e12, decimals=1)
        f.addRow("Young (Pa) :", self.young)
        self.poisson = QDoubleSpinBox(value=0.3, maximum=0.49, decimals=3)
        f.addRow("Poisson :", self.poisson)
        self.new_group.setLayout(f)
        layout.addWidget(self.new_group)
        
        self.exist_group = QGroupBox("Matériau existant")
        f2 = QFormLayout()
        self.mat_combo = QComboBox()
        f2.addRow("Choisir :", self.mat_combo)
        self.exist_group.setLayout(f2)
        layout.addWidget(self.exist_group)
        
        self.setLayout(layout)
    
    def initializePage(self):
        self.mat_combo.clear()
        mats = self.controller.get_materials()
        self.mat_combo.addItems([m.name for m in mats])
        self._toggle(self.new_mat.isChecked())
    
    def _toggle(self, new):
        self.new_group.setEnabled(new)
        self.exist_group.setEnabled(not new)
    
    def validatePage(self):
        if self.new_mat.isChecked():
            mat = Material(
                name=self.mat_name.text(),
                material_type=MaterialType.ELAS,  # ou autre
                density=self.density.value(),
                properties={"young": self.young.value(), "nu": self.poisson.value(), "" : self}
            )
            try:
                self.controller.add_material(mat)
                self.setField("material", mat)
            except Exception as e:
                QMessageBox.warning(self, "Erreur", str(e))
                return False
        else:
            name = self.mat_combo.currentText()
            mat = next((m for m in self.controller.get_materials() if m.name == name), None)
            if mat:
                self.setField("material", mat)
            else:
                return False
        return True


class ModelPage(QWizardPage):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        layout = QVBoxLayout()
        
        self.new_model = QCheckBox("Créer un nouveau modèle")
        self.new_model.toggled.connect(self._toggle)
        layout.addWidget(self.new_model)
        
        self.new_group = QGroupBox("Nouveau modèle")
        f = QFormLayout()
        self.model_name = QLineEdit("MECAxx")
        f.addRow("Nom :", self.model_name)
        self.physics = QComboBox()
        self.physics.addItems(["MECAx"])
        f.addRow("Physique :", self.physics)
        self.element = QComboBox()
        f.addRow("Élément :", self.element)
        self.anisotropy = QLineEdit("iso__")
        f.addRow("isotropie :", self.anisotropy)
        self.new_group.setLayout(f)
        layout.addWidget(self.new_group)        

        
        self.exist_group = QGroupBox("Modèle existant")
        f2 = QFormLayout()
        self.model_combo = QComboBox()
        f2.addRow("Choisir :", self.model_combo)
        self.exist_group.setLayout(f2)
        layout.addWidget(self.exist_group)
        
        self.setLayout(layout)
    
    def initializePage(self):
        dim = self.field("dimension")
        self.element.clear()
        elems = ["T3xxx", "Q4xxx", "T6xxx"] if dim == 2 else ["H8xxx", "TE10x"]
        self.element.addItems(elems)
        
        self.model_combo.clear()
        models = [m for m in self.controller.get_models() ]
        self.model_combo.addItems([m.name for m in models])
        self._toggle(self.new_model.isChecked())
    
    def _toggle(self, new):
        self.new_group.setEnabled(new)
        self.exist_group.setEnabled(not new)
    
    def validatePage(self):
        if self.new_model.isChecked():
            mod = Model(
                name=self.model_name.text(),
                physics=self.physics.currentText(),
                element=self.element.currentText(),
                dimension=self.field("dimension")
            )
            try:
                self.controller.add_model(mod)
                self.setField("model", mod)
            except Exception as e:
                QMessageBox.warning(self, "Erreur", str(e))
                return False
        else:
            name = self.model_combo.currentText()
            mod = next((m for m in self.controller.get_models() if m.name == name), None)
            if mod:
                self.setField("model", mod)
            else:
                return False
        return True


class SummaryPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.text = QTextEdit(readOnly=True)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)
    
    def initializePage(self):
        s = "<h2>Résumé</h2>"
        s += f"<b>Dimension :</b> {self.field('dimension')}D<br>"
        s += f"<b>Géométrie :</b> {self.field('geom_type')}<br>"
        s += f"<b>Dimensions :</b> {self.field('lx'):.3f} × {self.field('ly'):.3f}"
        if self.field("dimension") == 3:
            s += f" × {self.field('lz'):.3f}"
        s += " m<br>"
        s += f"<b>Maillage :</b> {self.field('nx')} × {self.field('ny')}"
        if self.field("dimension") == 3:
            s += f" × {self.field('nz')}"
        s += " éléments<br>"
        mat = self.field("material")
        s += f"<b>Matériau :</b> {mat.name if mat else '—'}<br>"
        mod = self.field("model")
        s += f"<b>Modèle :</b> {mod.name if mod else '—'} ({mod.element})"
        self.text.setHtml(s)