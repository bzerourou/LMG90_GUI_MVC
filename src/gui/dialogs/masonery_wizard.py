from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QLabel, QSpinBox, QDoubleSpinBox, QRadioButton,
    QGroupBox, QHBoxLayout, QCheckBox, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt

from ...core.models import Material, Model, Avatar, MaterialType, AvatarType, AvatarOrigin
from ...controllers.project_controller import ProjectController


class MasonryWizard(QWizard):
    
    PAGE_INTRO = 0
    PAGE_DIMENSION = 1
    PAGE_MATERIAL = 2
    PAGE_MODEL = 3
    PAGE_BRICK_TYPE = 4
    PAGE_BRICK_DIM = 5
    PAGE_LAYOUT = 6
    PAGE_SUMMARY = 7
    
    def __init__(self, controller: ProjectController, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        self.setWindowTitle("🧱 Assistant de Maçonnerie")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)
        self.resize(800, 600)
        
        self.addPage(MasonryIntroPage())
        self.addPage(MasonryDimensionPage())
        self.addPage(MasonryMaterialPage())
        self.addPage(MasonryModelPage())
        self.addPage(BrickTypePage())
        self.addPage(BrickDimensionsPage())
        self.addPage(LayoutPage())
        self.addPage(MasonrySummaryPage())
        
        self.setButtonText(QWizard.WizardButton.NextButton, "Suivant ➡️")
        self.setButtonText(QWizard.WizardButton.BackButton, "⬅️ Retour")
        self.setButtonText(QWizard.WizardButton.FinishButton, "✅ Générer")
        self.setButtonText(QWizard.WizardButton.CancelButton, "❌ Annuler")
    
    def accept(self):
        try:
            self._generate_masonry()
            QMessageBox.information(
                self, "Succès",
                "✅ Structure maçonnée générée avec succès !"
            )
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération échouée :\n{e}")
    
    def _generate_masonry(self):
        from pylmgc90 import pre
        
        dim_page = self.page(self.PAGE_DIMENSION)
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        self.controller.state.dimension = dimension
        
        mat_page = self.page(self.PAGE_MATERIAL)
        if mat_page.create_material_check.isChecked():
            material = Material(
                name=mat_page.mat_name_input.text().strip(),
                material_type=MaterialType.RIGID,
                density=mat_page.density_spin.value()
            )
            self.controller.add_material(material)
            mat_name = material.name
        else:
            mat_name = mat_page.existing_combo.currentText()
        
        mod_page = self.page(self.PAGE_MODEL)
        if mod_page.create_model_check.isChecked():
            element = "Rxx2D" if dimension == 2 else "Rxx3D"
            model = Model(
                name=mod_page.mod_name_input.text().strip(),
                physics="MECAx",
                element=element,
                dimension=dimension
            )
            self.controller.add_model(model)
            mod_name = model.name
        else:
            mod_name = mod_page.existing_combo.currentText()
        
        mat_obj = self.controller._pylmgc_materials[mat_name]
        mod_obj = self.controller._pylmgc_models[mod_name]
        
        brick_page = self.page(self.PAGE_BRICK_TYPE)
        brick_type = brick_page.type_combo.currentText()
        
        dim_brick_page = self.page(self.PAGE_BRICK_DIM)
        lx = dim_brick_page.lx_spin.value()
        ly = dim_brick_page.ly_spin.value()
        lz = dim_brick_page.lz_spin.value() if dimension == 3 else None
        
        layout_page = self.page(self.PAGE_LAYOUT)
        pattern = layout_page.pattern_combo.currentText()
        nb_rows = layout_page.rows_spin.value()
        nb_cols = layout_page.cols_spin.value()
        offset_x = layout_page.offset_x_spin.value()
        offset_y = layout_page.offset_y_spin.value()
        joint = layout_page.joint_spin.value()
        color = layout_page.color_input.text().strip()
        
        group_name = layout_page.group_name_input.text().strip() if layout_page.store_check.isChecked() else None
        
        if dimension == 2:
            brick = pre.brick2D(brick_type, lx, ly)
        else:
            brick = pre.brick3D(brick_type, lx, ly, lz)
        
        generated_indices = []
        
        if pattern == "Standard":
            for row in range(nb_rows):
                row_offset = (lx / 2.0) if (row % 2 == 1) else 0.0
                for col in range(nb_cols):
                    cx = offset_x + col * (lx + joint) + row_offset
                    cy = offset_y + row * (ly + joint)
                    center = [cx, cy] if dimension == 2 else [cx, cy, 0.0]
                    
                    body = brick.rigidBrick(center=center, model=mod_obj, material=mat_obj, color=color)
                    self.controller._bodies_container.addAvatar(body)
                    self.controller._pylmgc_bodies.append(body)
                    
                    avatar = Avatar(
                        avatar_type=AvatarType.EMPTY_AVATAR,
                        center=center,
                        material_name=mat_name,
                        model_name=mod_name,
                        color=color,
                        origin=AvatarOrigin.MANUAL,
                        contactors=[]
                    )
                    self.controller.state.avatars.append(avatar)
                    generated_indices.append(len(self.controller.state.avatars) - 1)
        
        elif pattern == "Running Bond":
            for row in range(nb_rows):
                row_offset = (lx / 2.0) if (row % 2 == 1) else 0.0
                for col in range(nb_cols):
                    cx = offset_x + col * (lx + joint) + row_offset
                    cy = offset_y + row * (ly + joint)
                    center = [cx, cy] if dimension == 2 else [cx, cy, 0.0]
                    
                    body = brick.rigidBrick(center=center, model=mod_obj, material=mat_obj, color=color)
                    self.controller._bodies_container.addAvatar(body)
                    self.controller._pylmgc_bodies.append(body)
                    
                    avatar = Avatar(
                        avatar_type=AvatarType.EMPTY_AVATAR,
                        center=center,
                        material_name=mat_name,
                        model_name=mod_name,
                        color=color,
                        origin=AvatarOrigin.MANUAL,
                        contactors=[]
                    )
                    self.controller.state.avatars.append(avatar)
                    generated_indices.append(len(self.controller.state.avatars) - 1)
        
        elif pattern == "Stack Bond":
            for row in range(nb_rows):
                for col in range(nb_cols):
                    cx = offset_x + col * (lx + joint)
                    cy = offset_y + row * (ly + joint)
                    center = [cx, cy] if dimension == 2 else [cx, cy, 0.0]
                    
                    body = brick.rigidBrick(center=center, model=mod_obj, material=mat_obj, color=color)
                    self.controller._bodies_container.addAvatar(body)
                    self.controller._pylmgc_bodies.append(body)
                    
                    avatar = Avatar(
                        avatar_type=AvatarType.EMPTY_AVATAR,
                        center=center,
                        material_name=mat_name,
                        model_name=mod_name,
                        color=color,
                        origin=AvatarOrigin.MANUAL,
                        contactors=[]
                    )
                    self.controller.state.avatars.append(avatar)
                    generated_indices.append(len(self.controller.state.avatars) - 1)
        
        elif pattern == "Flemish Bond":
            for row in range(nb_rows):
                for col in range(nb_cols):
                    if (row + col) % 2 == 0:
                        brick_lx = lx
                    else:
                        brick_lx = lx / 2.0
                    
                    cx = offset_x + col * (lx + joint)
                    cy = offset_y + row * (ly + joint)
                    center = [cx, cy] if dimension == 2 else [cx, cy, 0.0]
                    
                    body = brick.rigidBrick(center=center, model=mod_obj, material=mat_obj, color=color)
                    self.controller._bodies_container.addAvatar(body)
                    self.controller._pylmgc_bodies.append(body)
                    
                    avatar = Avatar(
                        avatar_type=AvatarType.EMPTY_AVATAR,
                        center=center,
                        material_name=mat_name,
                        model_name=mod_name,
                        color=color,
                        origin=AvatarOrigin.MANUAL,
                        contactors=[]
                    )
                    self.controller.state.avatars.append(avatar)
                    generated_indices.append(len(self.controller.state.avatars) - 1)
        
        if group_name:
            if group_name not in self.controller.state.avatar_groups:
                self.controller.state.avatar_groups[group_name] = []
            self.controller.state.avatar_groups[group_name].extend(generated_indices)


class MasonryIntroPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("🧱 Assistant de Maçonnerie")
        self.setSubTitle("Créez des structures maçonnées (murs, voûtes, arches) avec des briques.")
        
        layout = QVBoxLayout()
        
        intro = QLabel(
            "<h3>📋 Étapes :</h3>"
            "<ol>"
            "<li>✅ Choisir la dimension (2D ou 3D)</li>"
            "<li>✅ Définir le matériau des briques</li>"
            "<li>✅ Définir le modèle physique</li>"
            "<li>✅ Choisir le type de brique</li>"
            "<li>✅ Configurer les dimensions</li>"
            "<li>✅ Définir l'appareil (pattern)</li>"
            "<li>✅ Générer la structure</li>"
            "</ol>"
            "<p><b>💡 Astuce :</b> Vous pouvez créer des murs, voûtes, arches avec différents appareils.</p>"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        
        layout.addStretch()
        self.setLayout(layout)


class MasonryDimensionPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("📐 Dimension")
        self.setSubTitle("Choisissez la dimension de votre structure.")
        
        layout = QVBoxLayout()
        
        dim_group = QGroupBox("Dimension spatiale")
        dim_layout = QVBoxLayout()
        
        self.dim_2d_radio = QRadioButton("2D - Structure bidimensionnelle")
        self.dim_2d_radio.setChecked(True)
        dim_layout.addWidget(self.dim_2d_radio)
        
        info_2d = QLabel("   💡 Murs plans, sections 2D")
        info_2d.setStyleSheet("color: gray; padding-left: 20px;")
        dim_layout.addWidget(info_2d)
        
        dim_layout.addSpacing(20)
        
        self.dim_3d_radio = QRadioButton("3D - Structure tridimensionnelle")
        dim_layout.addWidget(self.dim_3d_radio)
        
        info_3d = QLabel("   💡 Murs 3D, voûtes, arches")
        info_3d.setStyleSheet("color: gray; padding-left: 20px;")
        dim_layout.addWidget(info_3d)
        
        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)
        
        layout.addStretch()
        self.setLayout(layout)


class MasonryMaterialPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("🧱 Matériau des Briques")
        self.setSubTitle("Créez un nouveau matériau ou utilisez un existant.")
        
        layout = QVBoxLayout()
        
        choice_group = QGroupBox("Source du matériau")
        choice_layout = QVBoxLayout()
        
        self.create_material_check = QCheckBox("Créer un nouveau matériau")
        self.create_material_check.setChecked(True)
        self.create_material_check.toggled.connect(self._toggle_mode)
        choice_layout.addWidget(self.create_material_check)
        
        choice_group.setLayout(choice_layout)
        layout.addWidget(choice_group)
        
        self.new_material_group = QGroupBox("Nouveau matériau")
        new_form = QFormLayout()
        
        self.mat_name_input = QLineEdit("brick")
        self.mat_name_input.setMaxLength(5)
        new_form.addRow("Nom :", self.mat_name_input)
        
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(100, 20000)
        self.density_spin.setValue(1800)
        self.density_spin.setSuffix(" kg/m³")
        new_form.addRow("Densité :", self.density_spin)
        
        self.new_material_group.setLayout(new_form)
        layout.addWidget(self.new_material_group)
        
        self.existing_material_group = QGroupBox("Matériau existant")
        existing_form = QFormLayout()
        
        self.existing_combo = QComboBox()
        existing_form.addRow("Sélectionner :", self.existing_combo)
        
        self.existing_material_group.setLayout(existing_form)
        self.existing_material_group.setVisible(False)
        layout.addWidget(self.existing_material_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _toggle_mode(self, create_new):
        self.new_material_group.setVisible(create_new)
        self.existing_material_group.setVisible(not create_new)
    
    def initializePage(self):
        wizard = self.wizard()
        materials = wizard.controller.get_materials()
        
        self.existing_combo.clear()
        if materials:
            self.existing_combo.addItems([m.name for m in materials])
        else:
            self.existing_combo.addItem("(Aucun matériau)")


class MasonryModelPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("⚙️ Modèle Physique")
        self.setSubTitle("Créez un nouveau modèle ou utilisez un existant.")
        
        layout = QVBoxLayout()
        
        choice_group = QGroupBox("Source du modèle")
        choice_layout = QVBoxLayout()
        
        self.create_model_check = QCheckBox("Créer un nouveau modèle")
        self.create_model_check.setChecked(True)
        self.create_model_check.toggled.connect(self._toggle_mode)
        choice_layout.addWidget(self.create_model_check)
        
        choice_group.setLayout(choice_layout)
        layout.addWidget(choice_group)
        
        self.new_model_group = QGroupBox("Nouveau modèle")
        new_form = QFormLayout()
        
        self.mod_name_input = QLineEdit("rigid")
        self.mod_name_input.setMaxLength(5)
        new_form.addRow("Nom :", self.mod_name_input)
        
        self.new_model_group.setLayout(new_form)
        layout.addWidget(self.new_model_group)
        
        self.existing_model_group = QGroupBox("Modèle existant")
        existing_form = QFormLayout()
        
        self.existing_combo = QComboBox()
        existing_form.addRow("Sélectionner :", self.existing_combo)
        
        self.existing_model_group.setLayout(existing_form)
        self.existing_model_group.setVisible(False)
        layout.addWidget(self.existing_model_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _toggle_mode(self, create_new):
        self.new_model_group.setVisible(create_new)
        self.existing_model_group.setVisible(not create_new)
    
    def initializePage(self):
        wizard = self.wizard()
        models = wizard.controller.get_models()
        
        self.existing_combo.clear()
        if models:
            self.existing_combo.addItems([m.name for m in models])
        else:
            self.existing_combo.addItem("(Aucun modèle)")


class BrickTypePage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("🧱 Type de Brique")
        self.setSubTitle("Sélectionnez le type de brique à utiliser.")
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "std_brick",
            "half_brick",
            "quarter_brick",
            "voussoir",
            "custom"
        ])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type de brique :", self.type_combo)
        
        layout.addLayout(form)
        
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self._on_type_changed("std_brick")
    
    def _on_type_changed(self, brick_type):
        infos = {
            "std_brick": "Brique standard rectangulaire",
            "half_brick": "Demi-brique (moitié de largeur)",
            "quarter_brick": "Quart de brique",
            "voussoir": "Voussoir pour arches et voûtes",
            "custom": "Brique personnalisée"
        }
        self.info_label.setText(f"<b>{brick_type}</b><br>{infos.get(brick_type, '')}")


class BrickDimensionsPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("📏 Dimensions de la Brique")
        self.setSubTitle("Définissez les dimensions de la brique.")
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.lx_spin = QDoubleSpinBox()
        self.lx_spin.setRange(0.01, 10.0)
        self.lx_spin.setValue(0.20)
        self.lx_spin.setSuffix(" m")
        form.addRow("Longueur (lx) :", self.lx_spin)
        
        self.ly_spin = QDoubleSpinBox()
        self.ly_spin.setRange(0.01, 10.0)
        self.ly_spin.setValue(0.10)
        self.ly_spin.setSuffix(" m")
        form.addRow("Hauteur (ly) :", self.ly_spin)
        
        self.lz_label = QLabel("Profondeur (lz) :")
        self.lz_spin = QDoubleSpinBox()
        self.lz_spin.setRange(0.01, 10.0)
        self.lz_spin.setValue(0.05)
        self.lz_spin.setSuffix(" m")
        form.addRow(self.lz_label, self.lz_spin)
        
        layout.addLayout(form)
        layout.addStretch()
        self.setLayout(layout)
    
    def initializePage(self):
        wizard = self.wizard()
        dim_page = wizard.page(MasonryWizard.PAGE_DIMENSION)
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        
        self.lz_label.setVisible(dimension == 3)
        self.lz_spin.setVisible(dimension == 3)


class LayoutPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("🏗️ Appareil de Maçonnerie")
        self.setSubTitle("Configurez la disposition des briques.")
        
        layout = QVBoxLayout()
        
        pattern_group = QGroupBox("Type d'appareil")
        pattern_form = QFormLayout()
        
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Standard",
            "Running Bond",
            "Stack Bond",
            "Flemish Bond"
        ])
        self.pattern_combo.currentTextChanged.connect(self._on_pattern_changed)
        pattern_form.addRow("Appareil :", self.pattern_combo)
        
        pattern_group.setLayout(pattern_form)
        layout.addWidget(pattern_group)
        
        self.pattern_info = QLabel()
        self.pattern_info.setWordWrap(True)
        self.pattern_info.setStyleSheet("background-color: #f0f0f0; padding: 8px; border-radius: 5px;")
        layout.addWidget(self.pattern_info)
        
        dimensions_group = QGroupBox("Dimensions du mur")
        dim_form = QFormLayout()
        
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 100)
        self.rows_spin.setValue(10)
        dim_form.addRow("Nombre de rangs :", self.rows_spin)
        
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 100)
        self.cols_spin.setValue(15)
        dim_form.addRow("Nombre de colonnes :", self.cols_spin)
        
        self.joint_spin = QDoubleSpinBox()
        self.joint_spin.setRange(0.0, 0.1)
        self.joint_spin.setValue(0.01)
        self.joint_spin.setSuffix(" m")
        self.joint_spin.setSingleStep(0.001)
        dim_form.addRow("Épaisseur joint :", self.joint_spin)
        
        dimensions_group.setLayout(dim_form)
        layout.addWidget(dimensions_group)
        
        position_group = QGroupBox("Position initiale")
        pos_form = QFormLayout()
        
        self.offset_x_spin = QDoubleSpinBox()
        self.offset_x_spin.setRange(-100.0, 100.0)
        self.offset_x_spin.setValue(0.0)
        self.offset_x_spin.setSuffix(" m")
        pos_form.addRow("Offset X :", self.offset_x_spin)
        
        self.offset_y_spin = QDoubleSpinBox()
        self.offset_y_spin.setRange(-100.0, 100.0)
        self.offset_y_spin.setValue(0.0)
        self.offset_y_spin.setSuffix(" m")
        pos_form.addRow("Offset Y :", self.offset_y_spin)
        
        position_group.setLayout(pos_form)
        layout.addWidget(position_group)
        
        options_group = QGroupBox("Options")
        opt_form = QFormLayout()
        
        self.color_input = QLineEdit("BLUEx")
        opt_form.addRow("Couleur :", self.color_input)
        
        self.store_check = QCheckBox("Stocker dans un groupe")
        self.store_check.setChecked(True)
        self.group_name_input = QLineEdit("mur_briques")
        opt_form.addRow(self.store_check, self.group_name_input)
        
        options_group.setLayout(opt_form)
        layout.addWidget(options_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self._on_pattern_changed("Standard")
    
    def _on_pattern_changed(self, pattern):
        infos = {
            "Standard": "Appareil standard avec décalage d'une demi-brique entre rangs",
            "Running Bond": "Appareil courant avec décalage régulier",
            "Stack Bond": "Appareil à joints continus (empilage vertical)",
            "Flemish Bond": "Appareil flamand alternant boutisses et panneresses"
        }
        self.pattern_info.setText(infos.get(pattern, ""))


class MasonrySummaryPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("📋 Récapitulatif")
        self.setSubTitle("Vérifiez la configuration avant de générer.")
        
        layout = QVBoxLayout()
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)
        
        self.setLayout(layout)
    
    def initializePage(self):
        wizard = self.wizard()
        
        dim_page = wizard.page(MasonryWizard.PAGE_DIMENSION)
        mat_page = wizard.page(MasonryWizard.PAGE_MATERIAL)
        mod_page = wizard.page(MasonryWizard.PAGE_MODEL)
        brick_page = wizard.page(MasonryWizard.PAGE_BRICK_TYPE)
        dim_brick_page = wizard.page(MasonryWizard.PAGE_BRICK_DIM)
        layout_page = wizard.page(MasonryWizard.PAGE_LAYOUT)
        
        dimension = "2D" if dim_page.dim_2d_radio.isChecked() else "3D"
        
        summary = f"""
        <h2>🧱 Structure Maçonnée {dimension}</h2>

        <h3>📐 Dimension</h3>
        <ul>
        <li><b>Type :</b> {dimension}</li>
        </ul>

        <h3>🧱 Matériau</h3>
"""
        
        if mat_page.create_material_check.isChecked():
            summary += f"""
        <ul>
        <li><b>Nom :</b> {mat_page.mat_name_input.text()}</li>
        <li><b>Densité :</b> {mat_page.density_spin.value()} kg/m³</li>
        </ul>
        """
        else:
            summary += f"<ul><li><b>Existant :</b> {mat_page.existing_combo.currentText()}</li></ul>"
        
        summary += "<h3>⚙️ Modèle</h3>"
        
        if mod_page.create_model_check.isChecked():
            summary += f"<ul><li><b>Nom :</b> {mod_page.mod_name_input.text()}</li></ul>"
        else:
            summary += f"<ul><li><b>Existant :</b> {mod_page.existing_combo.currentText()}</li></ul>"
        
        summary += f"""
        <h3>🧱 Brique</h3>
        <ul>
        <li><b>Type :</b> {brick_page.type_combo.currentText()}</li>
        <li><b>Dimensions :</b> {dim_brick_page.lx_spin.value()} × {dim_brick_page.ly_spin.value()}"""
        
        if dimension == "3D":
            summary += f" × {dim_brick_page.lz_spin.value()}"
        
        summary += f""" m</li>
        </ul>

        <h3>🏗️ Appareil</h3>
        <ul>
        <li><b>Type :</b> {layout_page.pattern_combo.currentText()}</li>
        <li><b>Dimensions :</b> {layout_page.rows_spin.value()} rangs × {layout_page.cols_spin.value()} colonnes</li>
        <li><b>Joints :</b> {layout_page.joint_spin.value()} m</li>
        <li><b>Position :</b> ({layout_page.offset_x_spin.value()}, {layout_page.offset_y_spin.value()})</li>
        <li><b>Couleur :</b> {layout_page.color_input.text()}</li>"""
        
        if layout_page.store_check.isChecked():
            summary += f"<li><b>Groupe :</b> {layout_page.group_name_input.text()}</li>"
        
        summary += """
        </ul>
        <hr>
        <p><b>✅ Cliquez sur 'Générer' pour créer la structure.</b></p>
        """
        
        total_bricks = layout_page.rows_spin.value() * layout_page.cols_spin.value()
        summary += f"<p><i>⚠️ Environ {total_bricks} briques seront créées.</i></p>"
        
        self.summary_text.setHtml(summary)