# Créer granulo_wizard.py dans gui/dialogs/:

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QLabel, QSpinBox, QDoubleSpinBox, QRadioButton,
    QGroupBox, QHBoxLayout, QCheckBox, QMessageBox, QTextEdit,
    QSlider
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
import random

from ...core.models import Material, Model, MaterialType, GranuloGeneration
from ...controllers.project_controller import ProjectController


class GranuloWizard(QWizard):
    """Assistant de configuration granulométrique"""
    
    PAGE_INTRO = 0
    PAGE_DIMENSION = 1
    PAGE_MATERIAL = 2
    PAGE_MODEL = 3
    PAGE_DISTRIBUTION = 4
    PAGE_CONTAINER = 5
    PAGE_PREVIEW = 6
    PAGE_SUMMARY = 7
    
    def __init__(self, controller: ProjectController, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        self.setWindowTitle("🎲 Assistant de Distribution Granulométrique")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)
        self.resize(800, 600)
        
        # Pages
        self.addPage(GranuloIntroPage())
        self.addPage(GranuloDimensionPage())
        self.addPage(GranuloMaterialPage())
        self.addPage(GranuloModelPage())
        self.addPage(DistributionPage())
        self.addPage(ContainerPage())
        self.addPage(PreviewPage())
        self.addPage(GranuloSummaryPage())
        
        self.setButtonText(QWizard.WizardButton.NextButton, "Suivant ➡️")
        self.setButtonText(QWizard.WizardButton.BackButton, "⬅️ Retour")
        self.setButtonText(QWizard.WizardButton.FinishButton, "✅ Générer")
        self.setButtonText(QWizard.WizardButton.CancelButton, "❌ Annuler")
    
    def accept(self):
        """Génération finale"""
        try:
            self._generate_granulo()
            QMessageBox.information(
                self, "Succès",
                "✅ Distribution granulométrique générée avec succès !"
            )
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération échouée :\n{e}")
    
    def _generate_granulo(self):
        """Génère la distribution"""
        # Dimension
        dim_page = self.page(self.PAGE_DIMENSION)
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        self.controller.state.dimension = dimension
        
        # Matériau
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
        
        # Modèle
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
        
        # Distribution
        dist_page = self.page(self.PAGE_DISTRIBUTION)
        nb_particles = dist_page.nb_particles_spin.value()
        radius_min = dist_page.radius_min_spin.value()
        radius_max = dist_page.radius_max_spin.value()
        seed = dist_page.seed_spin.value() if dist_page.use_seed_check.isChecked() else None
        
        # Conteneur
        cont_page = self.page(self.PAGE_CONTAINER)
        container_type = cont_page.container_combo.currentText()
        container_params = cont_page.get_container_params()
        
        # Type d'avatar
        avatar_type = "rigidDisk" if dimension == 2 else "rigidSphere"
        
        # Groupe
        group_name = f"granulo_{container_type.lower()}"
        
        # Génération
        config = GranuloGeneration(
            nb_particles=nb_particles,
            radius_min=radius_min,
            radius_max=radius_max,
            container_type=container_type,
            container_params=container_params,
            model_name=mod_name,
            material_name=mat_name,
            avatar_type=avatar_type,
            seed=seed,
            group_name=group_name
        )
        
        self.controller.generate_granulo(config)


class GranuloIntroPage(QWizardPage):
    """Introduction"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("🎲 Assistant de Distribution Granulométrique")
        self.setSubTitle("Créez rapidement une distribution de particules avec dépôt gravitaire.")
        
        layout = QVBoxLayout()
        
        intro = QLabel(
            "<h3>📋 Étapes :</h3>"
            "<ol>"
            "<li>✅ Choisir la dimension (2D ou 3D)</li>"
            "<li>✅ Définir le matériau des particules</li>"
            "<li>✅ Définir le modèle physique</li>"
            "<li>✅ Configurer la distribution des rayons</li>"
            "<li>✅ Choisir le type de conteneur</li>"
            "<li>✅ Prévisualiser et générer</li>"
            "</ol>"
            "<p><b>💡 Astuce :</b> L'algorithme de dépôt place les particules par gravité sans chevauchement.</p>"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        
        layout.addStretch()
        self.setLayout(layout)


class GranuloDimensionPage(QWizardPage):
    """Dimension"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("📐 Dimension")
        self.setSubTitle("Choisissez si votre distribution sera en 2D ou 3D.")
        
        layout = QVBoxLayout()
        
        dim_group = QGroupBox("Dimension spatiale")
        dim_layout = QVBoxLayout()
        
        self.dim_2d_radio = QRadioButton("2D - Distribution bidimensionnelle")
        self.dim_2d_radio.setChecked(True)
        dim_layout.addWidget(self.dim_2d_radio)
        
        info_2d = QLabel(
            "   💡 Conteneurs 2D : Box2D, Disk2D, Couette2D, Drum2D\n"
            "   Particules : Disques rigides"
        )
        info_2d.setStyleSheet("color: gray; padding-left: 20px;")
        dim_layout.addWidget(info_2d)
        
        dim_layout.addSpacing(20)
        
        self.dim_3d_radio = QRadioButton("3D - Distribution tridimensionnelle")
        dim_layout.addWidget(self.dim_3d_radio)
        
        info_3d = QLabel(
            "   💡 Conteneurs 3D : Box3D, Sphere3D, Cylinder3D\n"
            "   Particules : Sphères rigides"
        )
        info_3d.setStyleSheet("color: gray; padding-left: 20px;")
        dim_layout.addWidget(info_3d)
        
        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)
        
        layout.addStretch()
        self.setLayout(layout)


class GranuloMaterialPage(QWizardPage):
    """Matériau"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("🧱 Matériau des Particules")
        self.setSubTitle("Créez un nouveau matériau ou utilisez un existant.")
        
        layout = QVBoxLayout()
        
        # Choix
        choice_group = QGroupBox("Source du matériau")
        choice_layout = QVBoxLayout()
        
        self.create_material_check = QCheckBox("Créer un nouveau matériau")
        self.create_material_check.setChecked(True)
        self.create_material_check.toggled.connect(self._toggle_mode)
        choice_layout.addWidget(self.create_material_check)
        
        choice_group.setLayout(choice_layout)
        layout.addWidget(choice_group)
        
        # Nouveau matériau
        self.new_material_group = QGroupBox("Nouveau matériau")
        new_form = QFormLayout()
        
        self.mat_name_input = QLineEdit("GRAN")
        self.mat_name_input.setMaxLength(5)
        new_form.addRow("Nom :", self.mat_name_input)
        
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(100, 20000)
        self.density_spin.setValue(2500)
        self.density_spin.setSuffix(" kg/m³")
        new_form.addRow("Densité :", self.density_spin)
        
        self.new_material_group.setLayout(new_form)
        layout.addWidget(self.new_material_group)
        
        # Matériau existant
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
        """Charger les matériaux existants"""
        wizard = self.wizard()
        materials = wizard.controller.get_materials()
        
        self.existing_combo.clear()
        if materials:
            self.existing_combo.addItems([m.name for m in materials])
        else:
            self.existing_combo.addItem("(Aucun matériau)")


class GranuloModelPage(QWizardPage):
    """Modèle"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("⚙️ Modèle Physique")
        self.setSubTitle("Créez un nouveau modèle ou utilisez un existant.")
        
        layout = QVBoxLayout()
        
        # Choix
        choice_group = QGroupBox("Source du modèle")
        choice_layout = QVBoxLayout()
        
        self.create_model_check = QCheckBox("Créer un nouveau modèle")
        self.create_model_check.setChecked(True)
        self.create_model_check.toggled.connect(self._toggle_mode)
        choice_layout.addWidget(self.create_model_check)
        
        choice_group.setLayout(choice_layout)
        layout.addWidget(choice_group)
        
        # Nouveau modèle
        self.new_model_group = QGroupBox("Nouveau modèle")
        new_form = QFormLayout()
        
        self.mod_name_input = QLineEdit("rigid")
        self.mod_name_input.setMaxLength(5)
        new_form.addRow("Nom :", self.mod_name_input)
        
        self.new_model_group.setLayout(new_form)
        layout.addWidget(self.new_model_group)
        
        # Modèle existant
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
        """Charger les modèles existants"""
        wizard = self.wizard()
        models = wizard.controller.get_models()
        
        self.existing_combo.clear()
        if models:
            self.existing_combo.addItems([m.name for m in models])
        else:
            self.existing_combo.addItem("(Aucun modèle)")


class DistributionPage(QWizardPage):
    """Configuration distribution"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("📊 Distribution des Particules")
        self.setSubTitle("Définissez le nombre et la taille des particules.")
        
        layout = QVBoxLayout()
        
        # Nombre de particules
        nb_group = QGroupBox("Nombre de particules")
        nb_form = QFormLayout()
        
        self.nb_particles_spin = QSpinBox()
        self.nb_particles_spin.setRange(10, 10000)
        self.nb_particles_spin.setValue(200)
        self.nb_particles_spin.valueChanged.connect(self._update_info)
        nb_form.addRow("Nombre demandé :", self.nb_particles_spin)
        
        self.nb_info_label = QLabel()
        nb_form.addRow("", self.nb_info_label)
        
        nb_group.setLayout(nb_form)
        layout.addWidget(nb_group)
        
        # Distribution des rayons
        radius_group = QGroupBox("Distribution des rayons")
        radius_form = QFormLayout()
        
        self.radius_min_spin = QDoubleSpinBox()
        self.radius_min_spin.setRange(0.001, 10.0)
        self.radius_min_spin.setValue(0.05)
        self.radius_min_spin.setSuffix(" m")
        self.radius_min_spin.valueChanged.connect(self._update_histogram)
        radius_form.addRow("Rayon minimum :", self.radius_min_spin)
        
        self.radius_max_spin = QDoubleSpinBox()
        self.radius_max_spin.setRange(0.001, 10.0)
        self.radius_max_spin.setValue(0.15)
        self.radius_max_spin.setSuffix(" m")
        self.radius_max_spin.valueChanged.connect(self._update_histogram)
        radius_form.addRow("Rayon maximum :", self.radius_max_spin)
        
        self.ratio_label = QLabel()
        radius_form.addRow("Ratio Rmax/Rmin :", self.ratio_label)
        
        radius_group.setLayout(radius_form)
        layout.addWidget(radius_group)
        
        # Histogramme visuel
        self.histogram_label = QLabel()
        self.histogram_label.setMinimumHeight(100)
        layout.addWidget(QLabel("<b>Aperçu de la distribution :</b>"))
        layout.addWidget(self.histogram_label)
        
        # Seed
        seed_group = QGroupBox("Reproductibilité")
        seed_layout = QHBoxLayout()
        
        self.use_seed_check = QCheckBox("Utiliser une graine aléatoire")
        seed_layout.addWidget(self.use_seed_check)
        
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 999999)
        self.seed_spin.setValue(12345)
        self.seed_spin.setEnabled(False)
        seed_layout.addWidget(self.seed_spin)
        
        self.use_seed_check.toggled.connect(self.seed_spin.setEnabled)
        
        seed_group.setLayout(seed_layout)
        layout.addWidget(seed_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self._update_info()
        self._update_histogram()
    
    def _update_info(self):
        nb = self.nb_particles_spin.value()
        if nb < 100:
            level = "Faible"
            color = "orange"
        elif nb < 500:
            level = "Moyen"
            color = "blue"
        else:
            level = "Élevé"
            color = "green"
        
        self.nb_info_label.setText(f"<b style='color: {color};'>Niveau : {level}</b>")
        self._update_histogram()
    
    def _update_histogram(self):
        rmin = self.radius_min_spin.value()
        rmax = self.radius_max_spin.value()
        
        if rmin >= rmax:
            self.ratio_label.setText("<span style='color: red;'>⚠️ Rmax doit être > Rmin</span>")
            return
        
        ratio = rmax / rmin
        self.ratio_label.setText(f"<b>{ratio:.2f}</b>")
        
        # Dessiner histogramme
        pixmap = QPixmap(400, 100)
        pixmap.fill(Qt.GlobalColor.white)
        
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor("black"), 1))
        
        # Générer distribution aléatoire
        nb = min(self.nb_particles_spin.value(), 200)
        radii = [random.uniform(rmin, rmax) for _ in range(nb)]
        
        # Bins
        bins = 20
        counts, edges = self._make_histogram(radii, bins, rmin, rmax)
        max_count = max(counts) if counts else 1
        
        # Dessiner
        bar_width = 400 / bins
        for i, count in enumerate(counts):
            height = int(80 * count / max_count)
            x = i * bar_width
            y = 80 - height
            painter.fillRect(int(x), int(y), int(bar_width - 2), height, QColor("steelblue"))
        
        # Axes
        painter.drawLine(0, 80, 400, 80)
        painter.drawText(5, 95, f"{rmin:.3f}")
        painter.drawText(350, 95, f"{rmax:.3f}")
        
        painter.end()
        
        self.histogram_label.setPixmap(pixmap)
    
    def _make_histogram(self, data, bins, rmin, rmax):
        step = (rmax - rmin) / bins
        counts = [0] * bins
        edges = [rmin + i * step for i in range(bins + 1)]
        
        for value in data:
            idx = int((value - rmin) / step)
            if 0 <= idx < bins:
                counts[idx] += 1
        
        return counts, edges


class ContainerPage(QWizardPage):
    """Configuration conteneur"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("📦 Conteneur de Dépôt")
        self.setSubTitle("Choisissez la géométrie dans laquelle les particules seront déposées.")
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.container_combo = QComboBox()
        self.container_combo.currentTextChanged.connect(self._on_container_changed)
        form.addRow("Type de conteneur :", self.container_combo)
        
        layout.addLayout(form)
        
        # Widget paramètres
        self.params_widget = QGroupBox("Dimensions du conteneur")
        self.params_layout = QFormLayout()
        self.params_widget.setLayout(self.params_layout)
        layout.addWidget(self.params_widget)
        
        # Widgets pour chaque type
        self.lx_input = QDoubleSpinBox()
        self.lx_input.setRange(0.1, 100)
        self.lx_input.setValue(4.0)
        self.lx_input.setSuffix(" m")
        
        self.ly_input = QDoubleSpinBox()
        self.ly_input.setRange(0.1, 100)
        self.ly_input.setValue(4.0)
        self.ly_input.setSuffix(" m")
        
        self.r_input = QDoubleSpinBox()
        self.r_input.setRange(0.1, 100)
        self.r_input.setValue(2.0)
        self.r_input.setSuffix(" m")
        
        self.rint_input = QDoubleSpinBox()
        self.rint_input.setRange(0.1, 100)
        self.rint_input.setValue(2.0)
        self.rint_input.setSuffix(" m")
        
        self.rext_input = QDoubleSpinBox()
        self.rext_input.setRange(0.1, 100)
        self.rext_input.setValue(4.0)
        self.rext_input.setSuffix(" m")
        
        layout.addStretch()
        self.setLayout(layout)
    
    def initializePage(self):
        """Charger conteneurs selon dimension"""
        wizard = self.wizard()
        dim_page = wizard.page(GranuloWizard.PAGE_DIMENSION)
        
        dimension = 2 if dim_page.dim_2d_radio.isChecked() else 3
        
        self.container_combo.clear()
        if dimension == 2:
            self.container_combo.addItems(["Box2D", "Disk2D", "Couette2D", "Drum2D"])
        else:
            self.container_combo.addItems(["Box3D", "Sphere3D", "Cylinder3D"])
        
        self._on_container_changed(self.container_combo.currentText())
    
    def _on_container_changed(self, container_type):
        """Mise à jour paramètres"""
        # Nettoyer
        while self.params_layout.count() > 0:
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().setVisible(False)
        
        if container_type == "Box2D":
            self.params_layout.addRow("Largeur (lx) :", self.lx_input)
            self.params_layout.addRow("Hauteur (ly) :", self.ly_input)
            self.lx_input.setVisible(True)
            self.ly_input.setVisible(True)
        
        elif container_type in ["Disk2D", "Drum2D"]:
            self.params_layout.addRow("Rayon (r) :", self.r_input)
            self.r_input.setVisible(True)
        
        elif container_type == "Couette2D":
            self.params_layout.addRow("Rayon int (rint) :", self.rint_input)
            self.params_layout.addRow("Rayon ext (rext) :", self.rext_input)
            self.rint_input.setVisible(True)
            self.rext_input.setVisible(True)
    
    def get_container_params(self):
        """Retourne les paramètres du conteneur"""
        container_type = self.container_combo.currentText()
        
        if container_type == "Box2D":
            return {'lx': self.lx_input.value(), 'ly': self.ly_input.value()}
        elif container_type in ["Disk2D", "Drum2D"]:
            return {'r': self.r_input.value()}
        elif container_type == "Couette2D":
            return {'rint': self.rint_input.value(), 'rext': self.rext_input.value()}
        else:
            return {}


class PreviewPage(QWizardPage):
    """Aperçu visuel"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("👁️ Aperçu")
        self.setSubTitle("Visualisation schématique de la configuration.")
        
        layout = QVBoxLayout()
        
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(600, 400)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_label)
        
        self.setLayout(layout)
    
    def initializePage(self):
        """Dessiner aperçu"""
        wizard = self.wizard()
        
        dist_page = wizard.page(GranuloWizard.PAGE_DISTRIBUTION)
        cont_page = wizard.page(GranuloWizard.PAGE_CONTAINER)
        
        nb = dist_page.nb_particles_spin.value()
        rmin = dist_page.radius_min_spin.value()
        rmax = dist_page.radius_max_spin.value()
        container = cont_page.container_combo.currentText()
        
        # Dessiner
        pixmap = QPixmap(600, 400)
        pixmap.fill(Qt.GlobalColor.white)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dessiner conteneur
        painter.setPen(QPen(QColor("black"), 3))
        
        if container == "Box2D":
            painter.drawRect(100, 100, 400, 200)
        elif container in ["Disk2D", "Drum2D"]:
            painter.drawEllipse(150, 100, 300, 300)
        elif container == "Couette2D":
            painter.drawEllipse(100, 50, 400, 400)
            painter.drawEllipse(200, 150, 200, 200)
        
        # Dessiner quelques particules
        painter.setPen(QPen(QColor("steelblue"), 1))
        painter.setBrush(QColor("lightblue"))
        
        for _ in range(min(50, nb)):
            r = random.uniform(rmin, rmax) * 500
            x = random.randint(150, 450)
            y = random.randint(150, 350)
            painter.drawEllipse(int(x - r), int(y - r), int(2*r), int(2*r))
        
        painter.end()
        
        self.preview_label.setPixmap(pixmap)


class GranuloSummaryPage(QWizardPage):
    """Résumé"""
    
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
        """Générer résumé"""
        wizard = self.wizard()
        
        dim_page = wizard.page(GranuloWizard.PAGE_DIMENSION)
        mat_page = wizard.page(GranuloWizard.PAGE_MATERIAL)
        mod_page = wizard.page(GranuloWizard.PAGE_MODEL)
        dist_page = wizard.page(GranuloWizard.PAGE_DISTRIBUTION)
        cont_page = wizard.page(GranuloWizard.PAGE_CONTAINER)
        
        dimension = "2D" if dim_page.dim_2d_radio.isChecked() else "3D"
        
        summary = f"""
        <h2>🎲 Distribution Granulométrique {dimension}</h2>

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
        <h3>📊 Distribution</h3>
        <ul>
        <li><b>Nombre de particules :</b> {dist_page.nb_particles_spin.value()}</li>
        <li><b>Rayon min :</b> {dist_page.radius_min_spin.value()} m</li>
        <li><b>Rayon max :</b> {dist_page.radius_max_spin.value()} m</li>
        <li><b>Ratio Rmax/Rmin :</b> {dist_page.radius_max_spin.value()} m</li>
        <li><b>Ratio Rmax/Rmin :</b>{dist_page.radius_min_spin.value()}m</li>"""
        if dist_page.use_seed_check.isChecked():
                summary += f"<li><b>Seed :</b> {dist_page.seed_spin.value()}</li>"
            
        summary += "</ul>"
            
        summary += f"""
        <h3>📦 Conteneur</h3>
        <ul>
        <li><b>Type :</b> {cont_page.container_combo.currentText()}</li>
        <li><b>Paramètres :</b> {cont_page.get_container_params()}</li>
        </ul>
        <hr>
        <p><b>✅ Cliquez sur 'Générer' pour créer la distribution.</b></p>
        <p><i>⚠️ Selon le nombre de particules, cela peut prendre quelques secondes.</i></p>"""
        self.summary_text.setHtml(summary)
