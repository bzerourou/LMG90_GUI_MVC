# ============================================================================
# Wizard pour la création de maillages déformables (mesh2d/mesh3d)
# ============================================================================
"""
Assistant de création de corps déformables avec éléments finis.
Gère mesh2d (2D) et mesh3d (3D) de pylmgc90.
"""
from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QLabel, QSpinBox, QDoubleSpinBox, QRadioButton,
    QGroupBox, QHBoxLayout, QCheckBox, QMessageBox, QTextEdit,
    QPushButton, QFileDialog
)
from PyQt6.QtCore import Qt
from pathlib import Path

from ...core.models import Material, Model, MaterialType, Avatar, AvatarType, AvatarOrigin
from ...controllers.project_controller import ProjectController


class MeshWizard(QWizard):
    """Assistant de création de maillages déformables"""
    
    PAGE_INTRO = 0
    PAGE_DIMENSION = 1
    PAGE_MESH_TYPE = 2
    PAGE_GEOMETRY = 3
    PAGE_MESH_PARAMS = 4
    PAGE_MATERIAL = 5
    PAGE_MODEL = 6
    PAGE_BOUNDARY = 7
    PAGE_SUMMARY = 8
    
    def __init__(self, controller: ProjectController, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        self.setWindowTitle("🔷 Assistant de Maillage Déformable")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)
        self.resize(800, 600)
        
        # Pages
        self.addPage(MeshIntroPage())
        self.addPage(MeshDimensionPage())
        self.addPage(MeshTypePage())
        self.addPage(GeometryPage())
        self.addPage(MeshParametersPage())
        self.addPage(MeshMaterialPage())
        self.addPage(MeshModelPage())
        self.addPage(BoundaryConditionsPage())
        self.addPage(MeshSummaryPage())
        
        self.setButtonText(QWizard.WizardButton.NextButton, "Suivant ➡️")
        self.setButtonText(QWizard.WizardButton.BackButton, "⬅️ Retour")
        self.setButtonText(QWizard.WizardButton.FinishButton, "✅ Générer Maillage")
        self.setButtonText(QWizard.WizardButton.CancelButton, "❌ Annuler")
    
    def accept(self):
        """Génération finale"""
        try:
            self._generate_mesh()
            QMessageBox.information(
                self, "Succès",
                "✅ Maillage déformable généré avec succès !"
            )
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération échouée :\n{e}")
    
    def _generate_mesh(self):
        """Génère le maillage déformable"""
        from pylmgc90 import pre
        
        # Dimension
        dim_page = self.page(self.PAGE_DIMENSION)
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        self.controller.state.dimension = dimension
        
        # Type de maillage
        mesh_type_page = self.page(self.PAGE_MESH_TYPE)
        mesh_type = mesh_type_page.type_combo.currentText()
        
        # Géométrie
        geom_page = self.page(self.PAGE_GEOMETRY)
        
        # Paramètres de maillage
        mesh_params = self.page(self.PAGE_MESH_PARAMS)
        
        # Matériau
        mat_page = self.page(self.PAGE_MATERIAL)
        if mat_page.create_mat_check.isChecked():
            material = Material(
                name=mat_page.mat_name_input.text().strip(),
                material_type=MaterialType(mat_page.mat_type_combo.currentText()),
                density=mat_page.density_spin.value(),
                properties={
                    'young': mat_page.young_spin.value(),
                    'poisson': mat_page.poisson_spin.value()
                }
            )
            self.controller.add_material(material)
            mat_name = material.name
        else:
            mat_name = mat_page.existing_combo.currentText()
        
        # Modèle
        mod_page = self.page(self.PAGE_MODEL)
        if mod_page.create_mod_check.isChecked():
            element = mod_page.element_combo.currentText()
            model = Model(
                name=mod_page.mod_name_input.text().strip(),
                physics=mod_page.physics_combo.currentText(),
                element=element,
                dimension=dimension
            )
            self.controller.add_model(model)
            mod_name = model.name
        else:
            mod_name = mod_page.existing_combo.currentText()
        
        # Récupérer les objets pylmgc
        mat_obj = self.controller._pylmgc_materials[mat_name]
        mod_obj = self.controller._pylmgc_models[mod_name]
        
        # Créer le maillage selon le type
        if dimension == 2:
            mesh_obj = self._create_mesh_2d(mesh_type, geom_page, mesh_params, mod_obj, mat_obj)
        else:
            mesh_obj = self._create_mesh_3d(mesh_type, geom_page, mesh_params, mod_obj, mat_obj)
        
        # Ajouter au controller
        self.controller._bodies_container.addAvatar(mesh_obj)
        self.controller._pylmgc_bodies.append(mesh_obj)
        
        # Créer l'avatar correspondant
        center = geom_page.get_center()
        avatar = Avatar(
            avatar_type=AvatarType.EMPTY_AVATAR,
            center=center,
            material_name=mat_name,
            model_name=mod_name,
            color="CYANx",
            origin=AvatarOrigin.MANUAL,
            contactors=[]
        )
        self.controller.state.avatars.append(avatar)
        
        # Appliquer les conditions aux limites
        boundary_page = self.page(self.PAGE_BOUNDARY)
        if boundary_page.fix_bottom_check.isChecked():
            # Appliquer fixation du bord inférieur
            self._apply_boundary_conditions(mesh_obj, boundary_page)
    
    def _create_mesh_2d(self, mesh_type, geom_page, mesh_params, mod_obj, mat_obj):
        """Crée un maillage 2D"""
        from pylmgc90 import pre
        
        if mesh_type == "Rectangle":
            # Dimensions
            width = geom_page.width_spin.value()
            height = geom_page.height_spin.value()
            center = geom_page.get_center()
            
            # Nombre d'éléments
            nx = mesh_params.nx_spin.value()
            ny = mesh_params.ny_spin.value()

            #il faut créer un mesh 
            mesh = pre.mesh()
            
            # Générer le maillage rectangulaire
            mesh = pre.buildMesh2D(
                mesh_type=='RECTANGLE',
                lx=width,
                ly=height,
                nx=nx,
                ny=ny,
                center=center,
                model=mod_obj,
                material=mat_obj
            )
            
            return mesh
        
        elif mesh_type == "Disque":
            # Rayon
            radius = geom_page.radius_spin.value()
            center = geom_page.get_center()
            
            # Nombre d'éléments radiaux et angulaires
            nr = mesh_params.nr_spin.value()
            ntheta = mesh_params.ntheta_spin.value()
            
            mesh = pre.mesh2D(
                shape='DISK',
                r=radius,
                nr=nr,
                ntheta=ntheta,
                center=center,
                model=mod_obj,
                material=mat_obj
            )
            
            return mesh
        
        elif mesh_type == "Fichier externe":
            # Charger depuis un fichier .msh ou .vtk
            filepath = geom_page.file_path_input.text()
            
            mesh = pre.mesh2D(
                mesh_file=filepath,
                model=mod_obj,
                material=mat_obj
            )
            
            return mesh
        else : 
             raise ValueError(f"Type de maillage 2D non supporté : {mesh_type}")
    
    
    def _create_mesh_3d(self, mesh_type, geom_page, mesh_params, mod_obj, mat_obj):
        """Crée un maillage 3D"""
        from pylmgc90 import pre
        
        if mesh_type == "Cube":
            # Dimensions
            lx = geom_page.lx_spin.value()
            ly = geom_page.ly_spin.value()
            lz = geom_page.lz_spin.value()
            center = geom_page.get_center()
            
            # Nombre d'éléments
            nx = mesh_params.nx_spin.value()
            ny = mesh_params.ny_spin.value()
            nz = mesh_params.nz_spin.value()
            
            mesh = pre.mesh3D(
                shape='BOX',
                lx=lx,
                ly=ly,
                lz=lz,
                nx=nx,
                ny=ny,
                nz=nz,
                center=center,
                model=mod_obj,
                material=mat_obj
            )
            
            return mesh
        
        elif mesh_type == "Sphère":
            # Rayon
            radius = geom_page.radius_spin.value()
            center = geom_page.get_center()
            
            # Nombre d'éléments
            nr = mesh_params.nr_spin.value()
            ntheta = mesh_params.ntheta_spin.value()
            nphi = mesh_params.nphi_spin.value()
            
            mesh = pre.mesh3D(
                shape='SPHERE',
                r=radius,
                nr=nr,
                ntheta=ntheta,
                nphi=nphi,
                center=center,
                model=mod_obj,
                material=mat_obj
            )
            
            return mesh
        
        elif mesh_type == "Cylindre":
            # Dimensions
            radius = geom_page.radius_spin.value()
            height = geom_page.height_spin.value()
            center = geom_page.get_center()
            
            # Nombre d'éléments
            nr = mesh_params.nr_spin.value()
            ntheta = mesh_params.ntheta_spin.value()
            nz = mesh_params.nz_spin.value()
            
            mesh = pre.mesh3D(
                shape='CYLINDER',
                r=radius,
                h=height,
                nr=nr,
                ntheta=ntheta,
                nz=nz,
                center=center,
                model=mod_obj,
                material=mat_obj
            )
            
            return mesh
        
        elif mesh_type == "Fichier externe":
            # Charger depuis un fichier .msh ou .vtk
            filepath = geom_page.file_path_input.text()
            
            mesh = pre.mesh3D(
                mesh_file=filepath,
                model=mod_obj,
                material=mat_obj
            )
            
            return mesh
        else  : 
            raise ValueError(f"Type de maillage 3D non supporté : {mesh_type}")
        
    def _apply_boundary_conditions(self, mesh_obj, boundary_page):
        """Applique les conditions aux limites au maillage"""
        # Fixation du bord inférieur
        if boundary_page.fix_bottom_check.isChecked():
            # TODO: Implémenter la fixation des nœuds du bord inférieur
            # mesh_obj.imposeInitValue(...)
            pass
        
        # Charge appliquée
        if boundary_page.apply_load_check.isChecked():
            load_value = boundary_page.load_value_spin.value()
            load_direction = boundary_page.load_direction_combo.currentText()
            
            # TODO: Implémenter l'application de la charge
            # mesh_obj.imposeDrivenDof(...)
            pass

class MeshIntroPage(QWizardPage):
    """Introduction"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("🔷 Assistant de Maillage Déformable")
        self.setSubTitle("Créez des corps déformables avec éléments finis (mesh2d/mesh3d).")
        
        layout = QVBoxLayout()
        
        intro = QLabel(
            "<h3>📋 Étapes :</h3>"
            "<ol>"
            "<li>✅ Choisir la dimension (2D ou 3D)</li>"
            "<li>✅ Sélectionner le type de maillage</li>"
            "<li>✅ Définir la géométrie</li>"
            "<li>✅ Configurer le raffinement du maillage</li>"
            "<li>✅ Définir le matériau déformable</li>"
            "<li>✅ Choisir le type d'élément fini</li>"
            "<li>✅ Appliquer les conditions aux limites</li>"
            "<li>✅ Générer le maillage</li>"
            "</ol>"
            "<p><b>💡 Astuce :</b> Les maillages permettent de simuler la déformation de solides.</p>"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        
        layout.addStretch()
        self.setLayout(layout)


class MeshDimensionPage(QWizardPage):
    """Dimension"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("📐 Dimension")
        self.setSubTitle("Choisissez si votre maillage sera 2D ou 3D.")
        
        layout = QVBoxLayout()
        
        dim_group = QGroupBox("Dimension spatiale")
        dim_layout = QVBoxLayout()
        
        self.dim_2d_radio = QRadioButton("2D - Maillage bidimensionnel")
        self.dim_2d_radio.setChecked(True)
        dim_layout.addWidget(self.dim_2d_radio)
        
        info_2d = QLabel("   💡 Éléments : T3, T6, Q4, Q8, Q9")
        info_2d.setStyleSheet("color: gray; padding-left: 20px;")
        dim_layout.addWidget(info_2d)
        
        dim_layout.addSpacing(20)
        
        self.dim_3d_radio = QRadioButton("3D - Maillage tridimensionnel")
        dim_layout.addWidget(self.dim_3d_radio)
        
        info_3d = QLabel("   💡 Éléments : H8, H20, TE10, SHB8")
        info_3d.setStyleSheet("color: gray; padding-left: 20px;")
        dim_layout.addWidget(info_3d)
        
        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)
        
        layout.addStretch()
        self.setLayout(layout)


class MeshTypePage(QWizardPage):
    """Type de maillage"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("🔷 Type de Maillage")
        self.setSubTitle("Sélectionnez la forme géométrique à mailler.")
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.type_combo = QComboBox()
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type :", self.type_combo)
        
        layout.addLayout(form)
        
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _on_type_changed(self, mesh_type):
        infos = {
            "Rectangle": "Maillage rectangulaire structuré",
            "Disque": "Maillage de disque circulaire",
            "Cube": "Maillage de boîte parallélépipédique",
            "Sphère": "Maillage de sphère",
            "Cylindre": "Maillage cylindrique",
            "Fichier externe": "Import depuis fichier .msh ou .vtk (Gmsh, Salome)"
        }
        self.info_label.setText(f"<b>{mesh_type}</b><br>{infos.get(mesh_type, '')}")
    
    def initializePage(self):
        """Mise à jour selon dimension"""
        wizard = self.wizard()
        dim_page = wizard.page(MeshWizard.PAGE_DIMENSION)
        
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        
        self.type_combo.clear()
        if dimension == 2:
            self.type_combo.addItems(["Rectangle", "Disque", "Fichier externe"])
        else:
            self.type_combo.addItems(["Cube", "Sphère", "Cylindre", "Fichier externe"])
        
        self._on_type_changed(self.type_combo.currentText())


class GeometryPage(QWizardPage):
    """Géométrie"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("📏 Géométrie")
        self.setSubTitle("Définissez les dimensions de votre maillage.")
        
        layout = QVBoxLayout()
        
        # Position
        pos_group = QGroupBox("Position du centre")
        pos_form = QFormLayout()
        
        self.cx_spin = QDoubleSpinBox()
        self.cx_spin.setRange(-100, 100)
        self.cx_spin.setValue(0.0)
        pos_form.addRow("Centre X :", self.cx_spin)
        
        self.cy_spin = QDoubleSpinBox()
        self.cy_spin.setRange(-100, 100)
        self.cy_spin.setValue(0.0)
        pos_form.addRow("Centre Y :", self.cy_spin)
        
        self.cz_spin = QDoubleSpinBox()
        self.cz_spin.setRange(-100, 100)
        self.cz_spin.setValue(0.0)
        pos_form.addRow("Centre Z :", self.cz_spin)
        
        pos_group.setLayout(pos_form)
        layout.addWidget(pos_group)
        
        # Dimensions
        dim_group = QGroupBox("Dimensions")
        self.dim_form = QFormLayout()
        
        # Rectangle/Cube
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.1, 100)
        self.width_spin.setValue(1.0)
        self.dim_form.addRow("Largeur (lx) :", self.width_spin)
        
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0.1, 100)
        self.height_spin.setValue(1.0)
        self.dim_form.addRow("Hauteur (ly) :", self.height_spin)
        
        self.lx_spin = QDoubleSpinBox()
        self.lx_spin.setRange(0.1, 100)
        self.lx_spin.setValue(1.0)
        
        self.ly_spin = QDoubleSpinBox()
        self.ly_spin.setRange(0.1, 100)
        self.ly_spin.setValue(1.0)
        
        self.lz_spin = QDoubleSpinBox()
        self.lz_spin.setRange(0.1, 100)
        self.lz_spin.setValue(1.0)
        self.dim_form.addRow("Profondeur (lz) :", self.lz_spin)
        
        # Disque/Sphère/Cylindre
        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.1, 100)
        self.radius_spin.setValue(1.0)
        self.dim_form.addRow("Rayon :", self.radius_spin)
        
        # Fichier
        file_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        file_layout.addWidget(self.file_path_input)
        
        browse_btn = QPushButton("📁 Parcourir")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        
        self.dim_form.addRow("Fichier maillage :", file_layout)
        
        dim_group.setLayout(self.dim_form)
        layout.addWidget(dim_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _browse_file(self):
        """Parcourir fichier"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner fichier maillage",
            "", "Maillages (*.msh *.vtk *.mesh)"
        )
        if filepath:
            self.file_path_input.setText(filepath)
    
    def initializePage(self):
        """Mise à jour selon le type"""
        wizard = self.wizard()
        mesh_type_page = wizard.page(MeshWizard.PAGE_MESH_TYPE)
        dim_page = wizard.page(MeshWizard.PAGE_DIMENSION)
        
        mesh_type = mesh_type_page.type_combo.currentText()
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        
        # Masquer tous les widgets de dimensions
        for i in range(self.dim_form.rowCount()):
            label_item = self.dim_form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            field_item = self.dim_form.itemAt(i, QFormLayout.ItemRole.FieldRole)
            
            if label_item and label_item.widget():
                label_item.widget().setVisible(False)
            if field_item:
                widget = field_item.widget()
                if widget:
                    widget.setVisible(False)

        # Afficher selon type
        if mesh_type == "Rectangle":
            self._show_row("Largeur (lx) :")
            self._show_row("Hauteur (ly) :")
        elif mesh_type == "Cube":
            self._show_row("Longueur X (lx) :")
            self._show_row("Longueur Y (ly) :")
            self._show_row("Profondeur (lz) :")
        elif mesh_type in ["Disque", "Sphère"]:
            self._show_row("Rayon :")
        elif mesh_type == "Cylindre":
            self._show_row("Rayon :")
            self._show_row("Profondeur (lz) :")
        elif mesh_type == "Fichier externe":
            self._show_row("Fichier maillage :")
        
        # Z visible seulement en 3D
        self.cz_spin.parentWidget().setVisible(dimension == 3)
    
    def _show_row(self, label_text):
        """Affiche une ligne du formulaire"""
        for i in range(self.dim_form.rowCount()):
            label_item = self.dim_form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            field_item = self.dim_form.itemAt(i, QFormLayout.ItemRole.FieldRole)
            
            if label_item and label_item.widget():
                if label_item.widget().text() == label_text:
                    label_item.widget().setVisible(True)
                    if field_item and field_item.widget():
                        field_item.widget().setVisible(True)
        
    def get_center(self):
        """Retourne le centre"""
        wizard = self.wizard()
        dim_page = wizard.page(MeshWizard.PAGE_DIMENSION)
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        
        if dimension == 2:
            return [self.cx_spin.value(), self.cy_spin.value()]
        else:
            return [self.cx_spin.value(), self.cy_spin.value(), self.cz_spin.value()]


class MeshParametersPage(QWizardPage):
    """Paramètres de maillage"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("🔢 Raffinement du Maillage")
        self.setSubTitle("Définissez la finesse du maillage.")
        
        layout = QVBoxLayout()
        
        self.params_form = QFormLayout()
        
        self.nx_spin = QSpinBox()
        self.nx_spin.setRange(2, 200)
        self.nx_spin.setValue(10)
        self.params_form.addRow("Nombre d'éléments en X (nx) :", self.nx_spin)
        
        self.ny_spin = QSpinBox()
        self.ny_spin.setRange(2, 200)
        self.ny_spin.setValue(10)
        self.params_form.addRow("Nombre d'éléments en Y (ny) :", self.ny_spin)
        
        self.nz_spin = QSpinBox()
        self.nz_spin.setRange(2, 200)
        self.nz_spin.setValue(10)
        self.params_form.addRow("Nombre d'éléments en Z (nz) :", self.nz_spin)
        
        self.nr_spin = QSpinBox()
        self.nr_spin.setRange(2, 100)
        self.nr_spin.setValue(10)
        self.params_form.addRow("Nombre d'éléments radiaux (nr) :", self.nr_spin)
        
        self.ntheta_spin = QSpinBox()
        self.ntheta_spin.setRange(4, 100)
        self.ntheta_spin.setValue(20)
        self.params_form.addRow("Nombre d'éléments angulaires (ntheta) :", self.ntheta_spin)
        
        self.nphi_spin = QSpinBox()
        self.nphi_spin.setRange(4, 100)
        self.nphi_spin.setValue(20)
        self.params_form.addRow("Nombre d'éléments en phi (nphi) :", self.nphi_spin)
        
        layout.addLayout(self.params_form)
        # Info dynamique
        self.element_count_label = QLabel()
        self.element_count_label.setStyleSheet(
            "background-color: #e8f5e9; padding: 10px; border-radius: 5px; font-weight: bold;"
        )
        layout.addWidget(self.element_count_label)
        
        info = QLabel(
            "💡 <b>Conseil :</b> Plus le maillage est fin (nx, ny élevés), "
            "plus le calcul sera précis mais lent."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background-color: #fff3cd; padding: 10px; border-radius: 5px;")
        layout.addWidget(info)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _update_element_count(self):
        """Met à jour le nombre d'éléments estimé"""
        wizard = self.wizard()
        mesh_type_page = wizard.page(MeshWizard.PAGE_MESH_TYPE)
        mesh_type = mesh_type_page.type_combo.currentText()
        
        count = 0
        
        if mesh_type == "Rectangle":
            count = self.nx_spin.value() * self.ny_spin.value()
        elif mesh_type == "Disque":
            count = self.nr_spin.value() * self.ntheta_spin.value()
        elif mesh_type == "Cube":
            count = self.nx_spin.value() * self.ny_spin.value() * self.nz_spin.value()
        elif mesh_type == "Sphère":
            count = self.nr_spin.value() * self.ntheta_spin.value() * self.nphi_spin.value()
        elif mesh_type == "Cylindre":
            count = self.nr_spin.value() * self.ntheta_spin.value() * self.nz_spin.value()
        
        self.element_count_label.setText(f"📊 Nombre d'éléments estimé : {count}")
    
    def initializePage(self):
        """Mise à jour selon le type"""
        wizard = self.wizard()
        mesh_type_page = wizard.page(MeshWizard.PAGE_MESH_TYPE)
        mesh_type = mesh_type_page.type_combo.currentText()
        dim_page = wizard.page(MeshWizard.PAGE_DIMENSION)
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        
        # Masquer tous
        for i in range(self.params_form.rowCount()):
            self.params_form.itemAt(i, QFormLayout.ItemRole.LabelRole).widget().setVisible(False)
            self.params_form.itemAt(i, QFormLayout.ItemRole.FieldRole).widget().setVisible(False)
        
        # Afficher selon type
        if mesh_type == "Rectangle":
            self._show_param_row("Éléments en X (nx) :")
            self._show_param_row("Éléments en Y (ny) :")
        
        elif mesh_type == "Disque":
            self._show_param_row("Éléments radiaux (nr) :")
            self._show_param_row("Éléments angulaires (nθ) :")
        
        elif mesh_type == "Cube":
            self._show_param_row("Éléments en X (nx) :")
            self._show_param_row("Éléments en Y (ny) :")
            self._show_param_row("Éléments en Z (nz) :")
        
        elif mesh_type == "Sphère":
            self._show_param_row("Éléments radiaux (nr) :")
            self._show_param_row("Éléments angulaires (nθ) :")
            self._show_param_row("Éléments en φ (nphi) :")
        
        elif mesh_type == "Cylindre":
            self._show_param_row("Éléments radiaux (nr) :")
            self._show_param_row("Éléments angulaires (nθ) :")
            self._show_param_row("Éléments en Z (nz) :")
        self._update_element_count()

    def _show_param_row(self, label_text):
        """Affiche une ligne de paramètre"""
        for i in range(self.params_form.rowCount()):
            label_item = self.params_form.itemAt(i, QFormLayout.ItemRole.LabelRole)
            field_item = self.params_form.itemAt(i, QFormLayout.ItemRole.FieldRole)
            
            if label_item and label_item.widget():
                if label_item.widget().text() == label_text:
                    label_item.widget().setVisible(True)
                    if field_item and field_item.widget():
                        field_item.widget().setVisible(True)


class MeshMaterialPage(QWizardPage):
    """Matériau déformable"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("🧱 Matériau Déformable")
        self.setSubTitle("Définissez les propriétés mécaniques.")
        
        layout = QVBoxLayout()
        
        self.create_mat_check = QCheckBox("Créer un nouveau matériau")
        self.create_mat_check.setChecked(True)
        self.create_mat_check.toggled.connect(self._toggle_mode)
        layout.addWidget(self.create_mat_check)
        
        # Nouveau matériau
        self.new_mat_group = QGroupBox("Nouveau matériau")
        new_form = QFormLayout()
        
        self.mat_name_input = QLineEdit("ELAS1")
        new_form.addRow("Nom :", self.mat_name_input)
        
        self.mat_type_combo = QComboBox()
        self.mat_type_combo.addItems(["ELAS", "ELAS_DILA", "VISCO_ELAS", "ELAS_PLAS"])
        new_form.addRow("Type :", self.mat_type_combo)
        
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(100, 20000)
        self.density_spin.setValue(2700)
        new_form.addRow("Densité (kg/m³) :", self.density_spin)
        
        self.young_spin = QDoubleSpinBox()
        self.young_spin.setRange(1e6, 1e12)
        self.young_spin.setValue(70e9)
        self.young_spin.setDecimals(2)
        new_form.addRow("Module de Young (Pa) :", self.young_spin)
        
        self.poisson_spin = QDoubleSpinBox()
        self.poisson_spin.setRange(0.0, 0.5)
        self.poisson_spin.setValue(0.3)
        self.poisson_spin.setDecimals(3)
        new_form.addRow("Coefficient de Poisson :", self.poisson_spin)
        
        self.new_mat_group.setLayout(new_form)
        layout.addWidget(self.new_mat_group)
        
        # Existant
        self.exist_mat_group = QGroupBox("Matériau existant")
        exist_form = QFormLayout()
        
        self.existing_combo = QComboBox()
        exist_form.addRow("Sélectionner :", self.existing_combo)
        
        self.exist_mat_group.setLayout(exist_form)
        self.exist_mat_group.setVisible(False)
        layout.addWidget(self.exist_mat_group)
        
        layout.addStretch()
        self.setLayout(layout)

    def _toggle_mode(self, create_new):
        """Bascule entre nouveau/existant"""
        self.new_mat_group.setVisible(create_new)
        self.exist_mat_group.setVisible(not create_new)

    def initializePage(self):
        """Charge les matériaux existants"""
        wizard = self.wizard()
        materials = wizard.controller.get_materials()
        
        self.existing_combo.clear()
        if materials:
            # Filtrer les matériaux élastiques
            elastic_mats = [m for m in materials if m.material_type.value in ["ELAS", "ELAS_DILA", "VISCO_ELAS", "ELAS_PLAS"]]
            if elastic_mats:
                self.existing_combo.addItems([m.name for m in elastic_mats])
            else:
                self.existing_combo.addItem("(Aucun matériau élastique)")
        else:
            self.existing_combo.addItem("(Aucun matériau)")

class MeshModelPage(QWizardPage):
    """Page du modèle (type d'élément fini)"""
    def __init__(self):
        super().__init__()
        self.setTitle("⚙️ Modèle - Élément Fini")
        self.setSubTitle("Choisissez le type d'élément fini à utiliser.")
        
        layout = QVBoxLayout()
        
        self.create_mod_check = QCheckBox("Créer un nouveau modèle")
        self.create_mod_check.setChecked(True)
        self.create_mod_check.toggled.connect(self._toggle_mode)
        layout.addWidget(self.create_mod_check)
        
        # Nouveau modèle
        self.new_mod_group = QGroupBox("Nouveau modèle")
        new_form = QFormLayout()
        
        self.mod_name_input = QLineEdit("fem")
        self.mod_name_input.setMaxLength(5)
        new_form.addRow("Nom (max 5 car.) :", self.mod_name_input)
        
        self.physics_combo = QComboBox()
        self.physics_combo.addItems(["MECAx", "THERx", "HYDRx"])
        new_form.addRow("Physique :", self.physics_combo)
        
        self.element_combo = QComboBox()
        self.element_combo.currentTextChanged.connect(self._on_element_changed)
        new_form.addRow("Élément fini :", self.element_combo)
        
        self.element_info = QLabel()
        self.element_info.setWordWrap(True)
        self.element_info.setStyleSheet("background-color: #f0f0f0; padding: 8px; border-radius: 5px; font-size: 9pt;")
        new_form.addRow("", self.element_info)
        
        self.new_mod_group.setLayout(new_form)
        layout.addWidget(self.new_mod_group)
        
        # Modèle existant
        self.exist_mod_group = QGroupBox("Modèle existant")
        exist_form = QFormLayout()
        
        self.existing_combo = QComboBox()
        exist_form.addRow("Sélectionner :", self.existing_combo)
        
        self.exist_mod_group.setLayout(exist_form)
        self.exist_mod_group.setVisible(False)
        layout.addWidget(self.exist_mod_group)
        
        layout.addStretch()
        self.setLayout(layout)

    def _toggle_mode(self, create_new):
        """Bascule entre nouveau/existant"""
        self.new_mod_group.setVisible(create_new)
        self.exist_mod_group.setVisible(not create_new)

    def _on_element_changed(self, element):
        """Met à jour l'info de l'élément"""
        infos = {
            # 2D
            "T3xxx": "Triangle à 3 nœuds (linéaire)",
            "T6xxx": "Triangle à 6 nœuds (quadratique)",
            "Q4xxx": "Quadrangle à 4 nœuds (bilinéaire)",
            "Q8xxx": "Quadrangle à 8 nœuds (biquadratique)",
            "Q9xxx": "Quadrangle à 9 nœuds (biquadratique complet)",
            # 3D
            "H8xxx": "Hexaèdre à 8 nœuds (trilinéaire)",
            "H20xx": "Hexaèdre à 20 nœuds (triquadratique)",
            "TE10x": "Tétraèdre à 10 nœuds (quadratique)",
            "SHB8x": "Hexaèdre SHB8 à 8 nœuds (solide-coque)",
            "SHB6x": "Prisme SHB6 à 6 nœuds (solide-coque)"
        }
        self.element_info.setText(infos.get(element, ""))

    def initializePage(self):
        """Charge les modèles selon la dimension"""
        wizard = self.wizard()
        dim_page = wizard.page(MeshWizard.PAGE_DIMENSION)
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        
        # Remplir les éléments disponibles
        self.element_combo.clear()
        if dimension == 2:
            self.element_combo.addItems(["T3xxx", "T6xxx", "Q4xxx", "Q8xxx", "Q9xxx"])
        else:
            self.element_combo.addItems(["H8xxx", "H20xx", "TE10x", "SHB8x", "SHB6x"])
        
        # Charger modèles existants
        models = wizard.controller.get_models()
        self.existing_combo.clear()
        if models:
            compatible_models = [m for m in models if m.dimension == dimension]
            if compatible_models:
                self.existing_combo.addItems([m.name for m in compatible_models])
            else:
                self.existing_combo.addItem(f"(Aucun modèle {dimension}D)")
        else:
            self.existing_combo.addItem("(Aucun modèle)")
class BoundaryConditionsPage(QWizardPage):
    """Page des conditions aux limites"""
    def __init__(self):
        super().__init__()
        self.setTitle("🔒 Conditions aux Limites")
        self.setSubTitle("Définissez les conditions aux limites du maillage.")
        
        layout = QVBoxLayout()
        
        info = QLabel(
            "💡 <b>Les conditions aux limites seront appliquées au maillage.</b><br>"
            "Vous pourrez les modifier plus tard dans l'onglet DOF."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(info)
        
        # Fixations
        fix_group = QGroupBox("Fixations (conditions de Dirichlet)")
        fix_layout = QVBoxLayout()
        
        self.fix_bottom_check = QCheckBox("Fixer le bord inférieur (y = y_min)")
        self.fix_bottom_check.setChecked(True)
        fix_layout.addWidget(self.fix_bottom_check)
        
        self.fix_top_check = QCheckBox("Fixer le bord supérieur (y = y_max)")
        fix_layout.addWidget(self.fix_top_check)
        
        self.fix_left_check = QCheckBox("Fixer le bord gauche (x = x_min)")
        fix_layout.addWidget(self.fix_left_check)
        
        self.fix_right_check = QCheckBox("Fixer le bord droit (x = x_max)")
        fix_layout.addWidget(self.fix_right_check)
        
        fix_group.setLayout(fix_layout)
        layout.addWidget(fix_group)
        
        # Chargements
        load_group = QGroupBox("Chargements (conditions de Neumann)")
        load_layout = QVBoxLayout()
        
        self.apply_load_check = QCheckBox("Appliquer un chargement")
        load_layout.addWidget(self.apply_load_check)
        
        load_params = QFormLayout()
        
        self.load_value_spin = QDoubleSpinBox()
        self.load_value_spin.setRange(-1e6, 1e6)
        self.load_value_spin.setValue(1000)
        self.load_value_spin.setSuffix(" N")
        load_params.addRow("Valeur :", self.load_value_spin)
        
        self.load_direction_combo = QComboBox()
        self.load_direction_combo.addItems(["X", "Y", "Z"])
        load_params.addRow("Direction :", self.load_direction_combo)
        
        load_layout.addLayout(load_params)
        
        load_group.setLayout(load_layout)
        layout.addWidget(load_group)
        
        note = QLabel(
            "⚠️ <b>Note :</b> L'application des conditions aux limites nécessite "
            "une implémentation spécifique dans le code pylmgc90 (TODO)."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #ff9800; background-color: #fff3cd; padding: 8px; border-radius: 5px;")
        layout.addWidget(note)
        
        layout.addStretch()
        self.setLayout(layout)
class MeshSummaryPage(QWizardPage) : 
    """Page de récapitulatif"""
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
        """Génère le récapitulatif"""
        wizard = self.wizard()
        
        dim_page = wizard.page(MeshWizard.PAGE_DIMENSION)
        mesh_type_page = wizard.page(MeshWizard.PAGE_MESH_TYPE)
        geom_page = wizard.page(MeshWizard.PAGE_GEOMETRY)
        mesh_params = wizard.page(MeshWizard.PAGE_MESH_PARAMS)
        mat_page = wizard.page(MeshWizard.PAGE_MATERIAL)
        mod_page = wizard.page(MeshWizard.PAGE_MODEL)
        boundary_page = wizard.page(MeshWizard.PAGE_BOUNDARY)
        
        dimension = "2D" if dim_page.dim_2d_radio.isChecked() else "3D"
        mesh_type = mesh_type_page.type_combo.currentText()
        
        summary = f"""

<h2>🔷 Maillage Déformable {dimension}</h2>
<h3>📐 Configuration</h3>
<ul>
<li><b>Dimension :</b> {dimension}</li>
<li><b>Type de maillage :</b> {mesh_type}</li>
<li><b>Centre :</b> {geom_page.get_center()}</li>
</ul>
<h3>📏 Géométrie</h3>
"""
        if mesh_type == "Rectangle":
            summary += f"""
<ul>
<li><b>Largeur :</b> {geom_page.width_spin.value()} m</li>
<li><b>Hauteur :</b> {geom_page.height_spin.value()} m</li>
</ul>
"""
        elif mesh_type == "Cube":
            summary += f"""
<ul>
<li><b>Dimensions :</b> {geom_page.lx_spin.value()} × {geom_page.ly_spin.value()} × {geom_page.lz_spin.value()} m</li>
</ul>
"""
        elif mesh_type in ["Disque", "Sphère"]:
            summary += f"""
<ul>
<li><b>Rayon :</b> {geom_page.radius_spin.value()} m</li>
</ul>
"""
        elif mesh_type == "Cylindre":
            summary += f"""
<ul>
<li><b>Rayon :</b> {geom_page.radius_spin.value()} m</li>
<li><b>Hauteur :</b> {geom_page.lz_spin.value()} m</li>
</ul>
"""
        elif mesh_type == "Fichier externe":
            summary += f"""
<ul>
<li><b>Fichier :</b> {geom_page.file_path_input.text()}</li>
</ul>
"""
        summary += "<h3>🔢 Raffinement</h3>"
        
        if mesh_type == "Rectangle":
            count = mesh_params.nx_spin.value() * mesh_params.ny_spin.value()
            summary += f"""
<ul>
<li><b>Éléments en X :</b> {mesh_params.nx_spin.value()}</li>
<li><b>Éléments en Y :</b> {mesh_params.ny_spin.value()}</li>
<li><b>Total estimé :</b> {count} éléments</li>
</ul>
"""
        elif mesh_type == "Cube":
            count = mesh_params.nx_spin.value() * mesh_params.ny_spin.value() * mesh_params.nz_spin.value()
            summary += f"""
<ul>
<li><b>Éléments :</b> {mesh_params.nx_spin.value()} × {mesh_params.ny_spin.value()} × {mesh_params.nz_spin.value()}</li>
<li><b>Total estimé :</b> {count} éléments</li>
</ul>
    """
        summary += "<h3>🧱 Matériau</h3>"
        
        if mat_page.create_mat_check.isChecked():
            summary += f"""
<ul>
<li><b>Nom :</b> {mat_page.mat_name_input.text()}</li>
<li><b>Type :</b> {mat_page.mat_type_combo.currentText()}</li>
<li><b>Densité :</b> {mat_page.density_spin.value()} kg/m³</li>
<li><b>Module de Young :</b> {mat_page.young_spin.value():.2e} Pa</li>
<li><b>Coefficient de Poisson :</b> {mat_page.poisson_spin.value()}</li>
</ul>
"""
        else:
            summary += f"<ul><li><b>Existant :</b> {mat_page.existing_combo.currentText()}</li></ul>"
        summary += "<h3>⚙️ Modèle</h3>"
    
        if mod_page.create_mod_check.isChecked():
            summary += f"""
<ul>
<li><b>Nom :</b> {mod_page.mod_name_input.text()}</li>
<li><b>Physique :</b> {mod_page.physics_combo.currentText()}</li>
<li><b>Élément :</b> {mod_page.element_combo.currentText()}</li>
</ul>
"""
        else:
            summary += f"<ul><li><b>Existant :</b> {mod_page.existing_combo.currentText()}</li></ul>"
        summary += "<h3>🔒 Conditions aux Limites</h3><ul>"
        
        if boundary_page.fix_bottom_check.isChecked():
            summary += "<li>Bord inférieur fixé</li>"
        if boundary_page.fix_top_check.isChecked():
            summary += "<li>Bord supérieur fixé</li>"
        if boundary_page.fix_left_check.isChecked():
            summary += "<li>Bord gauche fixé</li>"
        if boundary_page.fix_right_check.isChecked():
            summary += "<li>Bord droit fixé</li>"
        if boundary_page.apply_load_check.isChecked():
            summary += f"<li>Charge appliquée : {boundary_page.load_value_spin.value()} N en {boundary_page.load_direction_combo.currentText()}</li>"
        
        if not any([
            boundary_page.fix_bottom_check.isChecked(),
            boundary_page.fix_top_check.isChecked(),
            boundary_page.fix_left_check.isChecked(),
            boundary_page.fix_right_check.isChecked(),
            boundary_page.apply_load_check.isChecked()
        ]):
            summary += "<li><i>Aucune condition définie</i></li>"
        
        summary += "</ul>"
        
        summary += """
<hr>
<h3 style='color: green;'>✅ Prêt à Générer !</h3>
<p><b>Cliquez sur 'Générer Maillage' pour créer le maillage déformable.</b></p>
<p><i>⚠️ La génération peut prendre quelques secondes selon la finesse du maillage.</i></p>
"""
        self.summary_text.setHtml(summary)
