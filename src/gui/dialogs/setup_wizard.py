# Créer setup_wizard.py dans gui/dialogs/:

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QLabel, QSpinBox, QDoubleSpinBox, QRadioButton,
    QGroupBox, QHBoxLayout, QCheckBox, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt

from ...core.models import Material, Model, Avatar, MaterialType, AvatarType
from ...controllers.project_controller import ProjectController


class ProjectSetupWizard(QWizard):
    """Assistant de configuration de projet complet"""
    
    # IDs des pages
    PAGE_INTRO = 0
    PAGE_PROJECT = 1
    PAGE_MATERIAL = 3
    PAGE_MODEL = 4
    PAGE_DIMENSION = 2
    PAGE_AVATAR = 5
    PAGE_SUMMARY = 6
    
    def __init__(self, controller: ProjectController, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        self.setWindowTitle("🧙 Assistant de Configuration de Projet")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)
        self.resize(700, 500)
        
        # Ajouter les pages
        self.addPage(IntroPage())
        self.addPage(ProjectPage())
        self.addPage(DimensionPage())
        self.addPage(MaterialPage())
        self.addPage(ModelPage())
        self.addPage(AvatarPage())
        self.addPage(SummaryPage())
        
        # Personnalisation des boutons
        self.setButtonText(QWizard.WizardButton.NextButton, "Suivant ➡️")
        self.setButtonText(QWizard.WizardButton.BackButton, "⬅️ Retour")
        self.setButtonText(QWizard.WizardButton.FinishButton, "✅ Créer le Projet")
        self.setButtonText(QWizard.WizardButton.CancelButton, "❌ Annuler")
    
    def accept(self):
        """Quand l'utilisateur clique sur Terminer"""
        try:
            self._create_project()
            QMessageBox.information(
                self, "Succès",
                "✅ Projet créé avec succès !\n\n"
                "Vous pouvez maintenant ajouter plus d'éléments."
            )
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def _create_project(self):
        """Crée le projet depuis les données du wizard"""
        # Page Projet
        project_page = self.page(self.PAGE_PROJECT)
        project_name = project_page.name_input.text().strip()
        
        if project_name:
            self.controller.new_project(project_name)
        
        # Page Dimension
        dim_page = self.page(self.PAGE_DIMENSION)
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        self.controller.state.dimension = dimension
        
        # Page Matériau
        mat_page = self.page(self.PAGE_MATERIAL)
        if mat_page.create_material_check.isChecked():
            material = Material(
                name=mat_page.mat_name_input.text().strip(),
                material_type=MaterialType(mat_page.mat_type_combo.currentText()),
                density=mat_page.density_spin.value()
            )
            self.controller.add_material(material)
        
        # Page Modèle
        mod_page = self.page(self.PAGE_MODEL)
        if mod_page.create_model_check.isChecked():
            model = Model(
                name=mod_page.mod_name_input.text().strip(),
                physics=mod_page.physics_combo.currentText(),
                element=mod_page.element_combo.currentText(),
                dimension=dimension
            )
            self.controller.add_model(model)
        
        # Page Avatar
        avatar_page = self.page(self.PAGE_AVATAR)
        radius = float(avatar_page.radius_spin.value() or "0.25")
        if avatar_page.create_avatar_check.isChecked():
            center = [0.0, 0.0] if dimension == 2 else [0.0, 0.0, 0.0]
            print(avatar_page.radius_spin.value())
            avatar = Avatar(
                avatar_type=AvatarType(avatar_page.avatar_type_combo.currentText()),
                center=center,
                material_name=mat_page.mat_name_input.text().strip(),
                model_name=mod_page.mod_name_input.text().strip(),
                radius=radius
            )

            
            self.controller.add_avatar(avatar)


class IntroPage(QWizardPage):
    """Page d'introduction"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("🎯 Bienvenue dans l'Assistant de Configuration")
        self.setSubTitle("Cet assistant vous guidera pas à pas pour créer votre projet LMGC90 avec seulemenr des éléments basiques.")
        
        layout = QVBoxLayout()
        
        intro = QLabel(
            "<h3>📋 Ce que nous allons faire :</h3>"
            "<ul>"
            "<li>✅ Définir les informations du projet</li>"
            "<li>✅ Choisir la dimension (2D ou 3D)</li>"
            "<li>✅ Créer un matériau de base</li>"
            "<li>✅ Créer un modèle physique</li>"
            "<li>✅ Optionnellement créer un premier avatar</li>"
            "</ul>"
            "<p><b>💡 Astuce :</b> Vous pourrez toujours modifier ces éléments après.</p>"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        
        layout.addStretch()
        self.setLayout(layout)


class ProjectPage(QWizardPage):
    """Page de configuration du projet"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("📁 Informations du Projet")
        self.setSubTitle("Définissez les informations de base de votre projet.")
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.name_input = QLineEdit("")
        self.name_input.setMaxLength(50)
        form.addRow("Nom du projet :", self.name_input)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        self.description_input.setPlaceholderText("Description optionnelle du projet...")
        form.addRow("Description :", self.description_input)
        
        layout.addLayout(form)
        layout.addStretch()
        self.setLayout(layout)
        
        # Enregistrer le champ pour validation
        self.registerField("projectName*", self.name_input)


class DimensionPage(QWizardPage):
    """Page de sélection de dimension"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("📐 Dimension du Problème")
        self.setSubTitle("Choisissez si votre simulation sera en 2D ou 3D.")
        
        layout = QVBoxLayout()
        
        dim_group = QGroupBox("Dimension spatiale")
        dim_layout = QVBoxLayout()
        
        self.dim_2d_radio = QRadioButton("2D - Problème bidimensionnel")
        self.dim_2d_radio.setChecked(True)
        dim_layout.addWidget(self.dim_2d_radio)
        
        info_2d = QLabel(
            "   💡 Exemples : compression biaxiale, essai œdométrique,\n"
            "   écoulement granulaire 2D, tambour rotatif 2D"
        )
        info_2d.setStyleSheet("color: gray; padding-left: 20px;")
        dim_layout.addWidget(info_2d)
        
        dim_layout.addSpacing(20)
        
        self.dim_3d_radio = QRadioButton("3D - Problème tridimensionnel")
        dim_layout.addWidget(self.dim_3d_radio)
        
        info_3d = QLabel(
            "   💡 Exemples : compression triaxiale, trémie 3D,\n"
            "   tambour cylindrique, mélangeur 3D"
        )
        info_3d.setStyleSheet("color: gray; padding-left: 20px;")
        dim_layout.addWidget(info_3d)
        
        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)
        
        layout.addStretch()
        self.setLayout(layout)


class MaterialPage(QWizardPage):
    """Page de création de matériau"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("🧱 Matériau")
        self.setSubTitle("Créez un matériau de base pour vos particules.")
        
        layout = QVBoxLayout()
        
        self.create_material_check = QCheckBox("Créer un matériau maintenant")
        self.create_material_check.setChecked(True)
        self.create_material_check.toggled.connect(self._toggle_form)
        layout.addWidget(self.create_material_check)
        
        self.form_widget = QGroupBox("Paramètres du matériau")
        form = QFormLayout()
        
        self.mat_name_input = QLineEdit("rockx")
        self.mat_name_input.setMaxLength(5)
        form.addRow("Nom (max 5 car.) :", self.mat_name_input)
        
        self.mat_type_combo = QComboBox()
        self.mat_type_combo.addItems([mt.value for mt in MaterialType])
        self.mat_type_combo.setCurrentText("RIGID")
        form.addRow("Type :", self.mat_type_combo)
        
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.1, 100000.0)
        self.density_spin.setValue(2500.0)
        self.density_spin.setSuffix(" kg/m³")
        form.addRow("Densité :", self.density_spin)
        
        self.form_widget.setLayout(form)
        layout.addWidget(self.form_widget)
        
        info = QLabel(
            "💡 <b>Conseil :</b> Pour des simulations granulaires simples,\n"
            "utilisez RIGID avec une densité typique de 2500 kg/m³ (sable/gravier)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #0066cc; padding: 10px; background-color: #e6f2ff; border-radius: 5px;")
        layout.addWidget(info)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _toggle_form(self, checked):
        self.form_widget.setEnabled(checked)


class ModelPage(QWizardPage):
    """Page de création de modèle"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("⚙️ Modèle Physique")
        self.setSubTitle("Créez un modèle de comportement mécanique.")
        
        layout = QVBoxLayout()
        
        self.create_model_check = QCheckBox("Créer un modèle maintenant")
        self.create_model_check.setChecked(True)
        self.create_model_check.toggled.connect(self._toggle_form)
        layout.addWidget(self.create_model_check)
        
        self.form_widget = QGroupBox("Paramètres du modèle")
        form = QFormLayout()
        
        self.mod_name_input = QLineEdit("rigid")
        self.mod_name_input.setMaxLength(5)
        form.addRow("Nom (max 5 car.) :", self.mod_name_input)
        
        self.physics_combo = QComboBox()
        self.physics_combo.addItems(["MECAx"])
        form.addRow("Physique :", self.physics_combo)
        
        self.element_combo = QComboBox()
        form.addRow("Élément :", self.element_combo)
        
        self.form_widget.setLayout(form)
        layout.addWidget(self.form_widget)
        
        info = QLabel(
            "💡 <b>Conseil :</b> Pour des corps rigides, utilisez Rxx2D (2D) ou Rxx3D (3D)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #0066cc; padding: 10px; background-color: #e6f2ff; border-radius: 5px;")
        layout.addWidget(info)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _toggle_form(self, checked):
        self.form_widget.setEnabled(checked)
    
    def initializePage(self):
        """Appelé quand la page est affichée"""
        # Récupérer la dimension depuis la page précédente
        wizard = self.wizard()
        dim_page = wizard.page(ProjectSetupWizard.PAGE_DIMENSION)
        
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        
        # Mettre à jour les éléments disponibles
        self.element_combo.clear()
        if dimension == 2:
            self.element_combo.addItems(["Rxx2D"])
        else:
            self.element_combo.addItems(["Rxx3D"])


class AvatarPage(QWizardPage):
    """Page de création d'avatar"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("🎯 Premier Avatar (Optionnel)")
        self.setSubTitle("Créez optionnellement un premier avatar de test.")
        
        layout = QVBoxLayout()
        
        self.create_avatar_check = QCheckBox("Créer un avatar de test")
        self.create_avatar_check.setChecked(False)
        self.create_avatar_check.toggled.connect(self._toggle_form)
        layout.addWidget(self.create_avatar_check)
        
        self.form_widget = QGroupBox("Paramètres de l'avatar")
        form = QFormLayout()
        
        self.avatar_type_combo = QComboBox()
        form.addRow("Type :", self.avatar_type_combo)
        
        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.001, 10.0)
        self.radius_spin.setValue(0.1)
        self.radius_spin.setSuffix(" m")
        form.addRow("Rayon :", self.radius_spin)
        
        self.form_widget.setLayout(form)
        self.form_widget.setEnabled(False)
        layout.addWidget(self.form_widget)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _toggle_form(self, checked):
        self.form_widget.setEnabled(checked)
    
    def initializePage(self):
        """Mise à jour selon dimension"""
        wizard = self.wizard()
        dim_page = wizard.page(ProjectSetupWizard.PAGE_DIMENSION)
        
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        
        self.avatar_type_combo.clear()
        if dimension == 2:
            self.avatar_type_combo.addItems(["rigidDisk"])
        else:
            self.avatar_type_combo.addItems(["rigidSphere"])


class SummaryPage(QWizardPage):
    """Page récapitulative"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("📋 Récapitulatif")
        self.setSubTitle("Vérifiez la configuration avant de créer le projet.")
        
        layout = QVBoxLayout()
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)
        
        self.setLayout(layout)
    
    def initializePage(self):
        """Génère le récapitulatif"""
        wizard = self.wizard()
        
        project_page = wizard.page(ProjectSetupWizard.PAGE_PROJECT)
        dim_page = wizard.page(ProjectSetupWizard.PAGE_DIMENSION)
        mat_page = wizard.page(ProjectSetupWizard.PAGE_MATERIAL)
        mod_page = wizard.page(ProjectSetupWizard.PAGE_MODEL)
        avatar_page = wizard.page(ProjectSetupWizard.PAGE_AVATAR)
        
        dimension = "2D" if dim_page.dim_2d_radio.isChecked() else "3D"
        
        summary = f"""
<h2>📁 Projet : {project_page.name_input.text()}</h2>

<h3>📐 Configuration</h3>
<ul>
<li><b>Dimension :</b> {dimension}</li>
</ul>

<h3>🧱 Matériau</h3>
"""
        
        if mat_page.create_material_check.isChecked():
            summary += f"""
<ul>
<li><b>Nom :</b> {mat_page.mat_name_input.text()}</li>
<li><b>Type :</b> {mat_page.mat_type_combo.currentText()}</li>
<li><b>Densité :</b> {mat_page.density_spin.value()} kg/m³</li>
</ul>
"""
        else:
            summary += "<p><i>Aucun matériau créé</i></p>"
        
        summary += "<h3>⚙️ Modèle</h3>"
        
        if mod_page.create_model_check.isChecked():
            summary += f"""
<ul>
<li><b>Nom :</b> {mod_page.mod_name_input.text()}</li>
<li><b>Physique :</b> {mod_page.physics_combo.currentText()}</li>
<li><b>Élément :</b> {mod_page.element_combo.currentText()}</li>
</ul>
"""
        else:
            summary += "<p><i>Aucun modèle créé</i></p>"
        
        summary += "<h3>🎯 Avatar</h3>"
        
        if avatar_page.create_avatar_check.isChecked():
            summary += f"""
<ul>
<li><b>Type :</b> {avatar_page.avatar_type_combo.currentText()}</li>
<li><b>Rayon :</b> {avatar_page.radius_spin.value()} m</li>
</ul>
"""
        else:
            summary += "<p><i>Aucun avatar créé</i></p>"
        
        summary += """
<hr>
<p><b>✅ Cliquez sur 'Créer le Projet' pour finaliser.</b></p>
"""
        
        self.summary_text.setHtml(summary)