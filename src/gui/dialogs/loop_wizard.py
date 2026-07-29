from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QLabel, QSpinBox, QDoubleSpinBox, QRadioButton,
    QGroupBox, QHBoxLayout, QCheckBox, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt

from ...core.models import Loop, ContactLaw, ContactLawType, VisibilityRule, Avatar, AvatarOrigin
from ...controllers.project_controller import ProjectController


class LoopWizardAdvanced(QWizard):
    
    PAGE_INTRO = 0
    PAGE_TARGET = 1
    PAGE_AVATAR_LOOP = 2
    PAGE_CONTACT_LOOP = 3
    PAGE_VISIBILITY_LOOP = 4
    PAGE_SUMMARY = 5
    
    def __init__(self, controller: ProjectController, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        self.setWindowTitle("🔁 Assistant de Boucles Avancé")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)
        self.resize(800, 600)
        
        self.addPage(LoopIntroPage())
        self.addPage(LoopTargetPage())
        self.addPage(AvatarLoopPage())
        self.addPage(ContactLoopPage())
        self.addPage(VisibilityLoopPage())
        self.addPage(LoopSummaryPage())
        
        self.setButtonText(QWizard.WizardButton.NextButton, "Suivant ➡️")
        self.setButtonText(QWizard.WizardButton.BackButton, "⬅️ Retour")
        self.setButtonText(QWizard.WizardButton.FinishButton, "✅ Générer")
        self.setButtonText(QWizard.WizardButton.CancelButton, "❌ Annuler")
    
    def accept(self):
        try:
            self._generate_loop()
            QMessageBox.information(
                self, "Succès",
                "✅ Boucle générée avec succès !"
            )
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Génération échouée :\n{e}")
    
    def _generate_loop(self):
        target_page = self.page(self.PAGE_TARGET)
        target_type = target_page.target_combo.currentText()
        
        if target_type == "Avatars":
            self._generate_avatar_loop()
        elif target_type == "Lois de Contact":
            self._generate_contact_loop()
        elif target_type == "Tables de Visibilité":
            self._generate_visibility_loop()
    
    def _generate_avatar_loop(self):
        avatar_page = self.page(self.PAGE_AVATAR_LOOP)
        
        model_avatar_id = avatar_page.avatar_combo.currentData()
        if model_avatar_id is None:
            raise ValueError("Sélectionnez un avatar modèle")
        
        loop = Loop(
            loop_type=avatar_page.loop_type_combo.currentText(),
            model_avatar_id=model_avatar_id,
            count=avatar_page.count_spin.value(),
            radius=avatar_page.radius_spin.value() if avatar_page.radius_spin.isVisible() else 0.0,
            step=avatar_page.step_spin.value() if avatar_page.step_spin.isVisible() else 0.0,
            offset_x=avatar_page.offset_x_spin.value(),
            offset_y=avatar_page.offset_y_spin.value(),
            spiral_factor=avatar_page.spiral_spin.value() if avatar_page.spiral_spin.isVisible() else 0.0,
            invert_axis=avatar_page.invert_check.isChecked(),
            group_name=avatar_page.group_input.text().strip() if avatar_page.store_check.isChecked() else None
        )
        
        self.controller.generate_loop(loop)
    
    def _generate_contact_loop(self):
        contact_page = self.page(self.PAGE_CONTACT_LOOP)
        
        base_name = contact_page.base_name_input.text().strip()
        law_type = ContactLawType(contact_page.law_type_combo.currentText())
        count = contact_page.count_spin.value()
        
        if law_type in [ContactLawType.IQS_CLB, ContactLawType.IQS_CLB_G0]:
            friction_start = contact_page.friction_start_spin.value()
            friction_end = contact_page.friction_end_spin.value()
            friction_step = (friction_end - friction_start) / max(1, count - 1)
            
            for i in range(count):
                name = f"{base_name}_{i+1}"
                friction = friction_start + i * friction_step
                
                law = ContactLaw(
                    name=name,
                    law_type=law_type,
                    friction=friction
                )
                self.controller.add_contact_law(law)
        else:
            for i in range(count):
                name = f"{base_name}_{i+1}"
                law = ContactLaw(
                    name=name,
                    law_type=law_type,
                    friction=None
                )
                self.controller.add_contact_law(law)
    
    def _generate_visibility_loop(self):
        vis_page = self.page(self.PAGE_VISIBILITY_LOOP)
        
        pattern = vis_page.pattern_combo.currentText()
        
        if pattern == "Même couleur (candidat = antagoniste)":
            colors = vis_page.colors_input.text().strip().split(',')
            colors = [c.strip() for c in colors if c.strip()]
            
            for color in colors:
                rule = VisibilityRule(
                    candidate_body=vis_page.cand_body_combo.currentText(),
                    candidate_contactor=vis_page.cand_cont_combo.currentText(),
                    candidate_color=color,
                    antagonist_body=vis_page.ant_body_combo.currentText(),
                    antagonist_contactor=vis_page.ant_cont_combo.currentText(),
                    antagonist_color=color,
                    behavior_name=vis_page.law_combo.currentText(),
                    alert=vis_page.alert_spin.value()
                )
                self.controller.add_visibility_rule(rule)
        
        elif pattern == "Couleurs croisées":
            cand_colors = vis_page.cand_colors_input.text().strip().split(',')
            ant_colors = vis_page.ant_colors_input.text().strip().split(',')
            cand_colors = [c.strip() for c in cand_colors if c.strip()]
            ant_colors = [c.strip() for c in ant_colors if c.strip()]
            
            for cand_color in cand_colors:
                for ant_color in ant_colors:
                    rule = VisibilityRule(
                        candidate_body=vis_page.cand_body_combo.currentText(),
                        candidate_contactor=vis_page.cand_cont_combo.currentText(),
                        candidate_color=cand_color,
                        antagonist_body=vis_page.ant_body_combo.currentText(),
                        antagonist_contactor=vis_page.ant_cont_combo.currentText(),
                        antagonist_color=ant_color,
                        behavior_name=vis_page.law_combo.currentText(),
                        alert=vis_page.alert_spin.value()
                    )
                    self.controller.add_visibility_rule(rule)
        
        elif pattern == "Toutes les couleurs du projet":
            all_colors = set()
            for avatar in self.controller.state.avatars:
                all_colors.add(avatar.color)
            
            for color in all_colors:
                rule = VisibilityRule(
                    candidate_body=vis_page.cand_body_combo.currentText(),
                    candidate_contactor=vis_page.cand_cont_combo.currentText(),
                    candidate_color=color,
                    antagonist_body=vis_page.ant_body_combo.currentText(),
                    antagonist_contactor=vis_page.ant_cont_combo.currentText(),
                    antagonist_color=color,
                    behavior_name=vis_page.law_combo.currentText(),
                    alert=vis_page.alert_spin.value()
                )
                self.controller.add_visibility_rule(rule)


class LoopIntroPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("🔁 Assistant de Boucles Avancé")
        self.setSubTitle("Créez des boucles sur différents éléments du projet.")
        
        layout = QVBoxLayout()
        
        intro = QLabel(
            "<h3>📋 Types de boucles disponibles :</h3>"
            "<ul>"
            "<li>🎯 <b>Boucle d'avatars</b> : Répétez un avatar selon un motif géométrique</li>"
            "<li>⚡ <b>Boucle de lois de contact</b> : Créez plusieurs lois avec variation de paramètres</li>"
            "<li>👁️ <b>Boucle de tables de visibilité</b> : Générez des règles pour plusieurs couleurs</li>"
            "</ul>"
            "<p><b>💡 Astuce :</b> Les boucles permettent d'automatiser la création répétitive d'éléments.</p>"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        
        layout.addStretch()
        self.setLayout(layout)


class LoopTargetPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("🎯 Type de Boucle")
        self.setSubTitle("Choisissez le type d'éléments à générer en boucle.")
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.target_combo = QComboBox()
        self.target_combo.addItems([
            "Avatars",
            "Lois de Contact",
            "Tables de Visibilité"
        ])
        self.target_combo.currentTextChanged.connect(self._on_target_changed)
        form.addRow("Type de boucle :", self.target_combo)
        
        layout.addLayout(form)
        
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self._on_target_changed("Avatars")
    
    def _on_target_changed(self, target):
        infos = {
            "Avatars": "Répète un avatar selon un motif (cercle, grille, ligne, spirale)",
            "Lois de Contact": "Crée plusieurs lois de contact avec variation de paramètres (ex: friction)",
            "Tables de Visibilité": "Génère des règles de visibilité pour plusieurs couleurs automatiquement"
        }
        self.info_label.setText(f"<b>{target}</b><br>{infos.get(target, '')}")
    
    def nextId(self):
        target = self.target_combo.currentText()
        wizard = self.wizard()
        
        if target == "Avatars":
            return wizard.PAGE_AVATAR_LOOP
        elif target == "Lois de Contact":
            return wizard.PAGE_CONTACT_LOOP
        elif target == "Tables de Visibilité":
            return wizard.PAGE_VISIBILITY_LOOP
        
        return wizard.PAGE_SUMMARY


class AvatarLoopPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("🎯 Boucle d'Avatars")
        self.setSubTitle("Configurez la répétition d'avatars.")
        
        layout = QVBoxLayout()
        
        model_group = QGroupBox("Avatar modèle")
        model_form = QFormLayout()
        
        self.avatar_combo = QComboBox()
        model_form.addRow("Avatar à répéter :", self.avatar_combo)
        
        model_group.setLayout(model_form)
        layout.addWidget(model_group)
        
        pattern_group = QGroupBox("Motif de répétition")
        pattern_form = QFormLayout()
        
        self.loop_type_combo = QComboBox()
        self.loop_type_combo.addItems(["Cercle", "Grille", "Ligne", "Spirale"])
        self.loop_type_combo.currentTextChanged.connect(self._on_loop_type_changed)
        pattern_form.addRow("Type :", self.loop_type_combo)
        
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1000)
        self.count_spin.setValue(10)
        pattern_form.addRow("Nombre :", self.count_spin)
        
        pattern_group.setLayout(pattern_form)
        layout.addWidget(pattern_group)
        
        params_group = QGroupBox("Paramètres")
        self.params_form = QFormLayout()
        
        self.radius_label = QLabel("Rayon :")
        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.1, 100.0)
        self.radius_spin.setValue(2.0)
        self.radius_spin.setSuffix(" m")
        self.params_form.addRow(self.radius_label, self.radius_spin)
        
        self.step_label = QLabel("Pas :")
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.01, 10.0)
        self.step_spin.setValue(0.5)
        self.step_spin.setSuffix(" m")
        self.params_form.addRow(self.step_label, self.step_spin)
        
        self.spiral_label = QLabel("Facteur spirale :")
        self.spiral_spin = QDoubleSpinBox()
        self.spiral_spin.setRange(0.01, 1.0)
        self.spiral_spin.setValue(0.1)
        self.params_form.addRow(self.spiral_label, self.spiral_spin)
        
        self.invert_check = QCheckBox("Inverser l'axe")
        self.params_form.addRow("", self.invert_check)
        
        self.offset_x_spin = QDoubleSpinBox()
        self.offset_x_spin.setRange(-100.0, 100.0)
        self.offset_x_spin.setValue(0.0)
        self.offset_x_spin.setSuffix(" m")
        self.params_form.addRow("Offset X :", self.offset_x_spin)
        
        self.offset_y_spin = QDoubleSpinBox()
        self.offset_y_spin.setRange(-100.0, 100.0)
        self.offset_y_spin.setValue(0.0)
        self.offset_y_spin.setSuffix(" m")
        self.params_form.addRow("Offset Y :", self.offset_y_spin)
        
        params_group.setLayout(self.params_form)
        layout.addWidget(params_group)
        
        group_layout = QHBoxLayout()
        self.store_check = QCheckBox("Stocker dans un groupe")
        self.store_check.setChecked(True)
        self.group_input = QLineEdit("boucle_avatars")
        group_layout.addWidget(self.store_check)
        group_layout.addWidget(self.group_input)
        layout.addLayout(group_layout)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self._on_loop_type_changed("Cercle")
    
    def _on_loop_type_changed(self, loop_type):
        show_radius = loop_type in ["Cercle", "Spirale"]
        show_step = loop_type in ["Grille", "Ligne"]
        show_spiral = loop_type == "Spirale"
        show_invert = loop_type == "Ligne"
        
        self.radius_label.setVisible(show_radius)
        self.radius_spin.setVisible(show_radius)
        self.step_label.setVisible(show_step)
        self.step_spin.setVisible(show_step)
        self.spiral_label.setVisible(show_spiral)
        self.spiral_spin.setVisible(show_spiral)
        self.invert_check.setVisible(show_invert)
    
    def initializePage(self):
        wizard = self.wizard()
        
        self.avatar_combo.clear()
        for i, avatar in enumerate(wizard.controller.state.avatars):
            if avatar.origin == AvatarOrigin.MANUAL:
                label = f"#{i} — {avatar.avatar_type.value} ({avatar.color})"
                self.avatar_combo.addItem(label, avatar.avatar_id)
        
        if self.avatar_combo.count() == 0:
            self.avatar_combo.addItem("(Aucun avatar manuel)", None)
    
    def nextId(self):
        return self.wizard().PAGE_SUMMARY


class ContactLoopPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("⚡ Boucle de Lois de Contact")
        self.setSubTitle("Créez plusieurs lois avec variation de paramètres.")
        
        layout = QVBoxLayout()
        
        naming_group = QGroupBox("Nommage")
        naming_form = QFormLayout()
        
        self.base_name_input = QLineEdit("law")
        naming_form.addRow("Nom de base :", self.base_name_input)
        
        info = QLabel("<i>Les lois seront nommées : law_1, law_2, law_3, ...</i>")
        info.setStyleSheet("color: #666;")
        naming_form.addRow("", info)
        
        naming_group.setLayout(naming_form)
        layout.addWidget(naming_group)
        
        params_group = QGroupBox("Paramètres")
        params_form = QFormLayout()
        
        self.law_type_combo = QComboBox()
        self.law_type_combo.addItems([lt.value for lt in ContactLawType])
        self.law_type_combo.currentTextChanged.connect(self._on_law_changed)
        params_form.addRow("Type de loi :", self.law_type_combo)
        
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 100)
        self.count_spin.setValue(5)
        params_form.addRow("Nombre de lois :", self.count_spin)
        
        params_group.setLayout(params_form)
        layout.addWidget(params_group)
        
        self.friction_group = QGroupBox("Variation de friction")
        friction_form = QFormLayout()
        
        self.friction_start_spin = QDoubleSpinBox()
        self.friction_start_spin.setRange(0.0, 10.0)
        self.friction_start_spin.setValue(0.1)
        self.friction_start_spin.setSingleStep(0.1)
        friction_form.addRow("Friction début :", self.friction_start_spin)
        
        self.friction_end_spin = QDoubleSpinBox()
        self.friction_end_spin.setRange(0.0, 10.0)
        self.friction_end_spin.setValue(0.5)
        self.friction_end_spin.setSingleStep(0.1)
        friction_form.addRow("Friction fin :", self.friction_end_spin)
        
        self.friction_group.setLayout(friction_form)
        layout.addWidget(self.friction_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self._on_law_changed("IQS_CLB")
    
    def _on_law_changed(self, law_type):
        needs_friction = law_type in ["IQS_CLB", "IQS_CLB_G0"]
        self.friction_group.setVisible(needs_friction)
    
    def nextId(self):
        return self.wizard().PAGE_SUMMARY


class VisibilityLoopPage(QWizardPage):
    
    def __init__(self):
        super().__init__()
        self.setTitle("👁️ Boucle de Tables de Visibilité")
        self.setSubTitle("Générez des règles pour plusieurs couleurs.")
        
        layout = QVBoxLayout()
        
        pattern_group = QGroupBox("Motif de génération")
        pattern_form = QFormLayout()
        
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Même couleur (candidat = antagoniste)",
            "Couleurs croisées",
            "Toutes les couleurs du projet"
        ])
        self.pattern_combo.currentTextChanged.connect(self._on_pattern_changed)
        pattern_form.addRow("Motif :", self.pattern_combo)
        
        pattern_group.setLayout(pattern_form)
        layout.addWidget(pattern_group)
        
        self.same_color_group = QGroupBox("Couleurs")
        same_form = QFormLayout()
        
        self.colors_input = QLineEdit("BLUEx, REDxx, VERTx")
        same_form.addRow("Liste (séparées par virgule) :", self.colors_input)
        
        self.same_color_group.setLayout(same_form)
        layout.addWidget(self.same_color_group)
        
        self.cross_color_group = QGroupBox("Couleurs croisées")
        cross_form = QFormLayout()
        
        self.cand_colors_input = QLineEdit("BLUEx, REDxx")
        cross_form.addRow("Couleurs candidat :", self.cand_colors_input)
        
        self.ant_colors_input = QLineEdit("VERTx, JAUNx")
        cross_form.addRow("Couleurs antagoniste :", self.ant_colors_input)
        
        self.cross_color_group.setLayout(cross_form)
        self.cross_color_group.setVisible(False)
        layout.addWidget(self.cross_color_group)
        
        bodies_group = QGroupBox("Configuration")
        bodies_form = QFormLayout()
        
        self.cand_body_combo = QComboBox()
        self.cand_body_combo.addItems(["RBDY2", "RBDY3"])
        self.cand_body_combo.currentTextChanged.connect(self._update_cand_cont)
        bodies_form.addRow("Corps candidat :", self.cand_body_combo)
        
        self.cand_cont_combo = QComboBox()
        bodies_form.addRow("Contacteur candidat :", self.cand_cont_combo)
        
        self.ant_body_combo = QComboBox()
        self.ant_body_combo.addItems(["RBDY2", "RBDY3"])
        self.ant_body_combo.currentTextChanged.connect(self._update_ant_cont)
        bodies_form.addRow("Corps antagoniste :", self.ant_body_combo)
        
        self.ant_cont_combo = QComboBox()
        bodies_form.addRow("Contacteur antagoniste :", self.ant_cont_combo)
        
        self.law_combo = QComboBox()
        bodies_form.addRow("Loi de contact :", self.law_combo)
        
        self.alert_spin = QDoubleSpinBox()
        self.alert_spin.setRange(0.001, 10.0)
        self.alert_spin.setValue(0.1)
        self.alert_spin.setSuffix(" m")
        bodies_form.addRow("Distance d'alerte :", self.alert_spin)
        
        bodies_group.setLayout(bodies_form)
        layout.addWidget(bodies_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self._update_cand_cont("RBDY2")
        self._update_ant_cont("RBDY2")
    
    def _on_pattern_changed(self, pattern):
        self.same_color_group.setVisible(pattern == "Même couleur (candidat = antagoniste)")
        self.cross_color_group.setVisible(pattern == "Couleurs croisées")
    
    def _update_cand_cont(self, body):
        self.cand_cont_combo.clear()
        if body == "RBDY2":
            self.cand_cont_combo.addItems(["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"])
        else:
            self.cand_cont_combo.addItems(["SPHER", "PLANx", "CYLND", "POLYR", "PT3Dx"])
    
    def _update_ant_cont(self, body):
        self.ant_cont_combo.clear()
        if body == "RBDY2":
            self.ant_cont_combo.addItems(["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"])
        else:
            self.ant_cont_combo.addItems(["SPHER", "PLANx", "CYLND", "POLYR", "PT3Dx"])
    
    def initializePage(self):
        wizard = self.wizard()
        
        self.law_combo.clear()
        laws = wizard.controller.get_contact_laws()
        if laws:
            self.law_combo.addItems([law.name for law in laws])
        else:
            self.law_combo.addItem("(Aucune loi)")
    
    def nextId(self):
        return self.wizard().PAGE_SUMMARY


class LoopSummaryPage(QWizardPage):
    
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
        target_page = wizard.page(wizard.PAGE_TARGET)
        target = target_page.target_combo.currentText()
        
        summary = f"<h2>🔁 Boucle : {target}</h2>"
        
        if target == "Avatars":
            avatar_page = wizard.page(wizard.PAGE_AVATAR_LOOP)
            summary += f"""
            <h3>🎯 Configuration</h3>
            <ul>
            <li><b>Avatar modèle :</b> {avatar_page.avatar_combo.currentText()}</li>
            <li><b>Type de boucle :</b> {avatar_page.loop_type_combo.currentText()}</li>
            <li><b>Nombre :</b> {avatar_page.count_spin.value()}</li>
            """
            
            if avatar_page.store_check.isChecked():
                summary += f"<li><b>Groupe :</b> {avatar_page.group_input.text()}</li>"
            
            summary += "</ul>"
        
        elif target == "Lois de Contact":
            contact_page = wizard.page(wizard.PAGE_CONTACT_LOOP)
            summary += f"""
            <h3>⚡ Configuration</h3>
            <ul>
            <li><b>Nom de base :</b> {contact_page.base_name_input.text()}</li>
            <li><b>Type :</b> {contact_page.law_type_combo.currentText()}</li>
            <li><b>Nombre :</b> {contact_page.count_spin.value()}</li>
            """
            
            if contact_page.friction_group.isVisible():
                summary += f"""
                <li><b>Friction :</b> {contact_page.friction_start_spin.value()} → {contact_page.friction_end_spin.value()}</li>
                """
            
            summary += "</ul>"
        
        elif target == "Tables de Visibilité":
            vis_page = wizard.page(wizard.PAGE_VISIBILITY_LOOP)
            summary += f"""
            <h3>👁️ Configuration</h3>
            <ul>
            <li><b>Motif :</b> {vis_page.pattern_combo.currentText()}</li>
            <li><b>Loi :</b> {vis_page.law_combo.currentText()}</li>
            <li><b>Alert :</b> {vis_page.alert_spin.value()} m</li>
            </ul>
            """
        
        summary += "<hr><p><b>✅ Cliquez sur 'Générer' pour créer la boucle.</b></p>"
        
        self.summary_text.setHtml(summary)