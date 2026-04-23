# ============================================================================
# LoopTab 
# ============================================================================
"""
Onglet de gestion des boucles avec création, modification, suppression et régénération.
Style identique aux autres onglets (MaterialTab, AvatarTab, ModelTab...).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QLabel, QCheckBox, QGroupBox, QTextEdit, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import Loop, AvatarOrigin, ForLoop, AvatarType
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController
from ...views.tabs.base_tab import BaseTab
import json


class LoopTab(BaseTab):
    """Onglet génération et gestion des boucles"""
    
    loop_generated = pyqtSignal()
    loop_updated = pyqtSignal()
    loop_deleted = pyqtSignal()

    def __init__(self, controller: ProjectController):
        super().__init__(controller)
        self.controller = controller
        self.current_edit_index = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        scroll_widget.setLayout(layout)

        tree_label = QLabel("<b>📋 Liste des Boucles</b>")
        layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["#", "Type", "Nombre", "Avatar Modèle", "Groupe"])
        self.tree.setColumnWidth(0, 50)
        self.tree.setColumnWidth(1, 120)
        self.tree.setColumnWidth(2, 80)
        self.tree.setColumnWidth(3, 150)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(180)
        layout.addWidget(self.tree)

        actions_layout = QHBoxLayout()
        
        self.regen_btn = QPushButton("♻️ Régénérer sélection")
        self.regen_btn.clicked.connect(self._on_regenerate_from_tree)
        
        self.edit_btn = QPushButton("✏️ Modifier sélection")
        self.edit_btn.clicked.connect(self._on_edit_from_tree)
        
        self.delete_btn = QPushButton("🗑️ Supprimer sélection")
        self.delete_btn.clicked.connect(self._on_delete_from_tree)

        actions_layout.addWidget(self.regen_btn)
        actions_layout.addWidget(self.edit_btn)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        form_label = QLabel("<b>📝 Paramètres de la Boucle</b>")
        layout.addWidget(form_label)

        form = QFormLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Cercle", "Grille", "Ligne", "Spirale", "For"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type de boucle :", self.type_combo)

        layout.addLayout(form)

        self.classic_widget = QWidget()
        classic_layout = QVBoxLayout()
        classic_form = QFormLayout()
        
        self.avatar_combo = QComboBox()
        classic_form.addRow("Avatar à répéter :", self.avatar_combo)

        self.count_input = QLineEdit("10")
        classic_form.addRow("Nombre d'avatars :", self.count_input)

        self.radius_label = QLabel("Rayon :")
        self.radius_input = QLineEdit("2.0")
        classic_form.addRow(self.radius_label, self.radius_input)

        self.step_label = QLabel("Pas :")
        self.step_input = QLineEdit("1.0")
        classic_form.addRow(self.step_label, self.step_input)

        self.invert_check = QCheckBox("Inverser l'axe")
        classic_form.addRow("", self.invert_check)

        self.offset_x_label = QLabel("Offset X :")
        self.offset_x_input = QLineEdit("0.0")
        classic_form.addRow(self.offset_x_label, self.offset_x_input)

        self.offset_y_label = QLabel("Offset Y :")
        self.offset_y_input = QLineEdit("0.0")
        classic_form.addRow(self.offset_y_label, self.offset_y_input)

        self.spiral_label = QLabel("Facteur spirale :")
        self.spiral_input = QLineEdit("0.1")
        classic_form.addRow(self.spiral_label, self.spiral_input)
        
        classic_layout.addLayout(classic_form)
        self.classic_widget.setLayout(classic_layout)
        layout.addWidget(self.classic_widget)

        self.for_widget = QWidget()
        for_layout = QVBoxLayout()

        for_group = QGroupBox("⚙️ Configuration Boucle For")
        for_form = QFormLayout()

        self.loop_var_input = QLineEdit("i")
        for_form.addRow("Variable de boucle :", self.loop_var_input)

        self.start_input = QLineEdit("0")
        for_form.addRow("Début :", self.start_input)

        self.end_input = QLineEdit("10")
        for_form.addRow("Fin :", self.end_input)

        self.step_for_input = QLineEdit("1")
        for_form.addRow("Step :", self.step_for_input)

        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems([
            "avatar", "material", "model", "contact_law", "visibility", "dof", "granulo"
        ])
        self.target_type_combo.currentTextChanged.connect(self._on_target_type_changed)
        for_form.addRow("Type d'élément :", self.target_type_combo)

        # Sélecteur de distribution — visible seulement quand target_type == "granulo"
        self.for_dist_label = QLabel("Distribution source :")
        self.for_dist_combo = QComboBox()
        self.for_dist_combo.setToolTip(
            "Distribution granulométrique créée dans l'onglet Granulométrie\n"
            "(mode « Distribution uniquement »).\n"
            "Chaque rayon de cette distribution devient la variable 'r' dans le template."
        )
        self.for_dist_combo.currentIndexChanged.connect(self._on_for_dist_changed)
        for_form.addRow(self.for_dist_label, self.for_dist_combo)
        self.for_dist_label.setVisible(False)
        self.for_dist_combo.setVisible(False)

        for_group.setLayout(for_form)
        for_layout.addWidget(for_group)

        template_group = QGroupBox("📝 Template JSON")
        template_layout = QVBoxLayout()

        self.for_help_text = QLabel()
        self.for_help_text.setWordWrap(True)
        self.for_help_text.setStyleSheet("color: #666; font-size: 8pt; padding: 5px;")
        template_layout.addWidget(self.for_help_text)

        self.template_input = QTextEdit()
        self.template_input.setPlaceholderText('{"avatar_type": "rigidDisk", "center": "[i*0.5, 0]", ...}')
        self.template_input.setMaximumHeight(150)
        template_layout.addWidget(self.template_input)

        template_group.setLayout(template_layout)
        for_layout.addWidget(template_group)

        self.for_widget.setLayout(for_layout)
        self.for_widget.setVisible(False)
        layout.addWidget(self.for_widget)

        # ── Widget Distribution ───────────────────────────────────────────────
        self.dist_widget = QGroupBox("🎲 Configuration Boucle Distribution")
        dist_form = QFormLayout()

        self.dist_combo = QComboBox()
        self.dist_combo.setToolTip(
            "Distributions disponibles dans le projet (générées depuis l'onglet Granulométrie)."
        )
        dist_form.addRow("Distribution :", self.dist_combo)

        self.dist_mat_combo = QComboBox()
        dist_form.addRow("Matériau des avatars :", self.dist_mat_combo)

        self.dist_mod_combo = QComboBox()
        dist_form.addRow("Modèle des avatars :", self.dist_mod_combo)

        self.dist_color_input = QLineEdit("BLUEx")
        dist_form.addRow("Couleur :", self.dist_color_input)

        self.dist_pattern_combo = QComboBox()
        self.dist_pattern_combo.addItems(["Grille", "Ligne"])
        self.dist_pattern_combo.setToolTip(
            "Grille : avatars disposés en grille carrée.\n"
            "Ligne  : avatars alignés sur l'axe X."
        )
        dist_form.addRow("Disposition :", self.dist_pattern_combo)

        from PyQt6.QtWidgets import QDoubleSpinBox as _DSB
        self.dist_step_spin = _DSB()
        self.dist_step_spin.setRange(1.0, 20.0)
        self.dist_step_spin.setDecimals(2)
        self.dist_step_spin.setSingleStep(0.1)
        self.dist_step_spin.setValue(2.2)
        self.dist_step_spin.setToolTip(
            "Multiplicateur de l'espacement entre avatars.\n"
            "Espacement = facteur × 2 × rayon_max de la distribution."
        )
        dist_form.addRow("Facteur d'espacement :", self.dist_step_spin)

        self.dist_ox_input = QLineEdit("0.0")
        dist_form.addRow("Offset X :", self.dist_ox_input)

        self.dist_oy_input = QLineEdit("0.0")
        dist_form.addRow("Offset Y :", self.dist_oy_input)

        self.dist_widget.setLayout(dist_form)
        self.dist_widget.setVisible(False)
        layout.addWidget(self.dist_widget)

        group_layout = QHBoxLayout()
        self.store_check = QCheckBox("Stocker dans un groupe")
        self.group_name_input = QLineEdit("boucle_groupe")
        group_layout.addWidget(self.store_check)
        group_layout.addWidget(self.group_name_input)
        group_layout.addStretch()
        layout.addLayout(group_layout)

        self.help_label = QLabel("Sélectionnez un type de boucle pour voir les paramètres adaptés.")
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.help_label)

        btn_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("✅ Créer boucle")
        self.create_btn.setStyleSheet("font-weight: bold;")
        self.create_btn.clicked.connect(self._on_create)
        btn_layout.addWidget(self.create_btn)
        
        self.update_btn = QPushButton("💾 Enregistrer Modifications")
        self.update_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        self.update_btn.clicked.connect(self._on_update)
        self.update_btn.setVisible(False)
        btn_layout.addWidget(self.update_btn)
        
        self.cancel_btn = QPushButton("❌ Annuler")
        self.cancel_btn.clicked.connect(self._on_cancel_edit)
        self.cancel_btn.setVisible(False)
        btn_layout.addWidget(self.cancel_btn)
        
        clear_btn = QPushButton("🔄 Réinitialiser")
        clear_btn.clicked.connect(self._clear_form)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.add_expression_help_label(layout)
        
        layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def _connect_signals(self):
        """Connecte les signaux"""
        self.tree.itemDoubleClicked.connect(self._on_edit_from_tree)

    def _show_context_menu(self, position):
        """Affiche le menu contextuel"""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        edit_action = menu.addAction("✏️ Modifier")
        edit_action.triggered.connect(self._on_edit_from_tree)
        
        regen_action = menu.addAction("♻️ Régénérer")
        regen_action.triggered.connect(self._on_regenerate_from_tree)
        
        delete_action = menu.addAction("🗑️ Supprimer")
        delete_action.triggered.connect(self._on_delete_from_tree)
        
        menu.addSeparator()
        
        info_action = menu.addAction("ℹ️ Informations")
        info_action.triggered.connect(self._show_info)
        
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _on_type_changed(self, loop_type: str):
        """Appelé quand le type de boucle change"""
        self.radius_label.setVisible(loop_type in ["Cercle", "Spirale"])
        self.radius_input.setVisible(loop_type in ["Cercle", "Spirale"])
        
        self.step_label.setVisible(loop_type in ["Grille", "Ligne"])
        self.step_input.setVisible(loop_type in ["Grille", "Ligne"])
        
        self.spiral_label.setVisible(loop_type == "Spirale")
        self.spiral_input.setVisible(loop_type == "Spirale")
        
        self.offset_x_label.setVisible(loop_type == "Grille")
        self.offset_x_input.setVisible(loop_type == "Grille")
        
        self.offset_y_label.setVisible(loop_type == "Grille")
        self.offset_y_input.setVisible(loop_type == "Grille")
        
        self.classic_widget.setVisible(loop_type not in ("For", "Distribution"))
        self.for_widget.setVisible(loop_type == "For")
        self.dist_widget.setVisible(loop_type == "Distribution")

        suggestions = {
            "Cercle":       "Avatars disposés en cercle avec un rayon défini.",
            "Grille":       "Avatars disposés en grille régulière avec un pas.",
            "Ligne":        "Avatars disposés en ligne avec un espacement.",
            "Spirale":      "Avatars en spirale avec rayon croissant.",
            "For":          "Boucle For programmable pour génération avancée.",
            "Distribution": (
                "Place un avatar par rayon d'une distribution granulométrique existante. "
                "Les rayons proviennent d'une distribution créée dans l'onglet Granulométrie."
            ),
        }
        self.help_label.setText(suggestions.get(loop_type, ""))

    def _on_target_type_changed(self, target_type: str):
        """Appelé quand le type cible change (boucle For)."""
        is_granulo = (target_type == "granulo")

        # Le sélecteur de distribution n'est plus nécessaire pour granulo
        self.for_dist_label.setVisible(False)
        self.for_dist_combo.setVisible(False)

        # start/end/step : toujours actifs pour granulo (c'est un range normal)
        for w in (self.start_input, self.end_input, self.step_for_input):
            w.setEnabled(True)

        # Templates d'exemple par type
        templates = {

            "avatar": (
                '{"avatar_type": "rigidDisk", '
                '"center": "[i*0.5, 0.0]", '
                '"material_name": "TDURx", '
                '"model_name": "rigid", '
                '"radius": "0.1+i*0.01"}'
            ),
            "material": (
                '{"name": "\'MAT\'+str(i)", '
                '"material_type": "RIGID", '
                '"density": "2800+i*100"}'
            ),
            "model": (
                '{"name": "\'MOD\'+str(i)", '
                '"physics": "MECAx", '
                '"element": "Rxx2D", '
                '"dimension": 2}'
            ),

            "contact_law" : (
                '{"name": "\'LAW\'+str(i)", ' 
                '"law": "IQS_CLB", '
                '"friction": 0.3 }'

            ),

            "visibility" : (
                '{"CorpsCandidat": "RBDY2", '
                '"candidat": "DISKx", '
                '"colorCandidat" : "BLUEx", '
                '"CorpsAntagoniste" :  "RBDY2", '
                '"antagoniste" : "DISKx", '
                '"colorAntagoniste" : "REDxx", '
                '"behav" : "LAW01", '
                '"alert": 0.05  '
                '}'
            ),
            "dof" : (
                '{"dof": "imposeDrivenDof", '
                '"component": "[1,2,3]", '
                '"dofty": "vlocy" }'
            ),

            "granulo": (
                '{\n'
                '  "nb_particles": 50,\n'
                '  "radius_min": 0.04,\n'
                '  "radius_max": 0.05,\n'
                '  "container_type": "Box2D",\n'
                '  "container_params": {\n'
                '    "lx": 4.0,\n'
                '    "ly": 2.0\n'
                '  },\n'
                '  "origin" : "[i* 3.0, 0.0]",\n'
                '  "material_name": "TDURx",\n'
                '  "model_name": "rigid",\n'
                '  "avatar_type": "rigidDisk"\n'
                '}'
            ),
        }

        help_texts = {
            "avatar": (
                "💡 Variable : <b>i</b> (valeur courante de la boucle).<br>"
                "Toutes les valeurs string sont évaluées comme expressions Python."
            ),
            "material": (
                "💡 Variable : <b>i</b> (valeur courante).<br>"
                "Exemple : <code>\"density\": \"2800 + i*100\"</code>"
            ),
            "model": (
                "💡 Variable : <b>i</b> (valeur courante).<br>"
                "Exemple : <code>\"element\": \"T3xxx\"</code>"
            ),
            "granulo": (
                "💡 Variable : <b>i</b> (valeur courante de la boucle).<br>"
                "Chaque itération crée un <b>dépôt granulométrique complet</b>.<br>"
                "Les valeurs de <code>container_params</code> peuvent être des expressions avec <b>i</b> "
                "pour espacer les dépôts.<br>"
                "Exemple : <code>\"xmin\": \"i * 2.0\"</code> — dépôt décalé de 2.0 à chaque tour."
            ),
        }

        if target_type in templates:
            self.template_input.setPlainText(templates[target_type])
        self.for_help_text.setText(help_texts.get(
            target_type, "💡 Variable : <b>i</b> (valeur courante de la boucle)."
        ))

    def _on_for_dist_changed(self, index: int):
        """Met à jour le template granulo quand la distribution sélectionnée change."""
        if self.target_type_combo.currentText() != "granulo":
            return
        dist_idx = self.for_dist_combo.itemData(index)
        if dist_idx is None:
            return
        gens = self.controller.state.granulo_generations
        if dist_idx < len(gens):
            g = gens[dist_idx]
            # Proposer un espacement automatique = 2.2 * rmax
            step = g.radius_max * 2.2
            dim  = self.controller.state.dimension
            if dim == 2:
                center_expr = f"[i * {step:.4g}, 0.0]"
            else:
                center_expr = f"[i * {step:.4g}, 0.0, 0.0]"
            av_type = "rigidDisk" if dim == 2 else "rigidSphere"
            self.template_input.setPlainText(
                f'{{"avatar_type": "{av_type}", '
                f'"center": "{center_expr}", '
                f'"material_name": "TDURx", '
                f'"model_name": "rigid", '
                f'"color": "BLUEx"}}'
            )

    def _on_create(self):
        """Crée une nouvelle boucle"""
        try:
            loop_type = self.type_combo.currentText()

            if loop_type == "Distribution":
                self._create_distribution_loop()
                return

            if loop_type == "For":
                target_type = self.target_type_combo.currentText()
                template_text = self.template_input.toPlainText().strip()
                if not template_text:
                    raise ValidationError("Le template JSON est requis pour les boucles For")

                template_config = json.loads(template_text)

                for_loop = ForLoop(
                    loop_var=self.loop_var_input.text().strip(),
                    start_expr=self.start_input.text().strip(),
                    end_expr=self.end_input.text().strip(),
                    step_expr=self.step_for_input.text().strip(),
                    target_type=target_type,
                    template_config=template_config,
                    group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
                )

                indices = self.controller.generate_for_loop(for_loop)
                self.loop_generated.emit()
                QMessageBox.information(
                    self, "Succès",
                    f"{len(indices)} éléments générés.\nGroupe : {for_loop.group_name or 'Aucun'}"
                )
            
            else:
                model_idx = self.avatar_combo.currentData()
                if model_idx is None:
                    raise ValidationError("Sélectionnez un avatar modèle")
                
                count = self.eval_int(self.count_input.text(), default=10, field_name="Nombre")
                radius = self.eval_float(self.radius_input.text(), default=2.0, field_name="Rayon")
                step = self.eval_float(self.step_input.text(), default=1.0, field_name="Pas")
                spiral_factor = self.eval_float(self.spiral_input.text(), default=0.1, field_name="Facteur spirale")
                offset_x = self.eval_float(self.offset_x_input.text(), default=0.0, field_name="Offset X")
                offset_y = self.eval_float(self.offset_y_input.text(), default=0.0, field_name="Offset Y")
                
                loop = Loop(
                    loop_type=loop_type,
                    model_avatar_index=model_idx,
                    count=count,
                    radius=radius,
                    step=step,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    spiral_factor=spiral_factor,
                    invert_axis=self.invert_check.isChecked(),
                    group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
                )
                
                indices = self.controller.generate_loop(loop)
                self.loop_generated.emit()
                QMessageBox.information(
                    self, "Succès",
                    f"{len(indices)} avatars générés avec succès.\nGroupe : {loop.group_name or 'Aucun'}"
                )
            
            self.refresh()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Erreur JSON", f"Template JSON invalide:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée:\n{e}")

    def _create_distribution_loop(self):
        """
        Type 'Distribution' : UI simplifiée pour créer N dépôts granulométriques
        identiques (même distribution) espacés automatiquement.
        Équivalent à un For (granulo) avec container_params construits depuis
        la distribution sélectionnée et la disposition choisie.
        """
        import math as _math
        from ...core.models import ForLoop

        # ── Distribution source ───────────────────────────────────────────────
        dist_idx = self.dist_combo.currentData()
        if dist_idx is None:
            raise ValidationError(
                "Aucune distribution disponible.\n"
                "Créez-en une depuis l'onglet Granulométrie (mode « Distribution uniquement »)."
            )
        dist_config = self.controller.state.granulo_generations[dist_idx]

        # ── Nombre de dépôts ──────────────────────────────────────────────────
        n_deposits = self.eval_int(
            getattr(self, 'dist_n_spin', None) and self.dist_n_spin.value() or "1",
            default=1, field_name="Nombre de dépôts"
        ) if hasattr(self, 'dist_n_spin') else 1

        # ── Paramètres avatars ────────────────────────────────────────────────
        material  = self.dist_mat_combo.currentText()
        model_nom = self.dist_mod_combo.currentText()
        color     = self.dist_color_input.text().strip() or "BLUEx"

        if not material:
            raise ValidationError("Sélectionnez un matériau pour les avatars.")
        if not model_nom:
            raise ValidationError("Sélectionnez un modèle pour les avatars.")

        # ── Paramètres position ───────────────────────────────────────────────
        step_factor = self.dist_step_spin.value()
        offset_x    = self.eval_float(self.dist_ox_input.text(), default=0.0, field_name="Offset X")
        offset_y    = self.eval_float(self.dist_oy_input.text(), default=0.0, field_name="Offset Y")
        dim         = self.controller.state.dimension

        # La taille d'un dépôt est estimée depuis container_params si dispo, sinon rmax*2
        cp   = dist_config.container_params or {}
        rmax = float(dist_config.radius_max)

        # Tenter d'estimer la largeur du conteneur (Box2D → xmax-xmin)
        if 'xmax' in cp and 'xmin' in cp:
            box_w = float(cp['xmax']) - float(cp['xmin'])
            box_h = float(cp.get('ymax', cp.get('ymin', 0)) or 0) - float(cp.get('ymin', 0) or 0)
        else:
            box_w = rmax * 2.0 * 10   # estimation grossière
            box_h = box_w

        step_x = (box_w + rmax * 2.0) * step_factor
        step_y = (box_h + rmax * 2.0) * step_factor

        pattern = self.dist_pattern_combo.currentText()

        # ── Construire les expressions container_params avec i ────────────────
        # On reprend les valeurs absolues de la distribution et on décale avec i
        base_cp = dict(cp)

        if pattern == "Ligne":
            # Décaler en X seulement
            ox   = f"{offset_x:.6g}"
            sx   = f"{step_x:.6g}"
            if 'xmin' in base_cp:
                xmin_base = float(base_cp['xmin'])
                xmax_base = float(base_cp.get('xmax', xmin_base + box_w))
                ymin_base = float(base_cp.get('ymin', -box_h/2))
                ymax_base = float(base_cp.get('ymax',  box_h/2))
                container_params = {
                    "xmin": f"{xmin_base + offset_x:.6g} + i * {sx}",
                    "xmax": f"{xmax_base + offset_x:.6g} + i * {sx}",
                    "ymin": f"{ymin_base + offset_y:.6g}",
                    "ymax": f"{ymax_base + offset_y:.6g}",
                }
            else:
                container_params = dict(base_cp)
        else:  # Grille
            # Décaler en X et Y selon la colonne/ligne
            nb   = n_deposits
            cols = max(1, int(_math.ceil(_math.sqrt(nb))))
            sx   = f"{step_x:.6g}"
            sy   = f"{step_y:.6g}"
            if 'xmin' in base_cp:
                xmin_base = float(base_cp['xmin'])
                xmax_base = float(base_cp.get('xmax', xmin_base + box_w))
                ymin_base = float(base_cp.get('ymin', -box_h/2))
                ymax_base = float(base_cp.get('ymax',  box_h/2))
                container_params = {
                    "xmin": f"{xmin_base + offset_x:.6g} + (i % {cols}) * {sx}",
                    "xmax": f"{xmax_base + offset_x:.6g} + (i % {cols}) * {sx}",
                    "ymin": f"{ymin_base + offset_y:.6g} + (i // {cols}) * {sy}",
                    "ymax": f"{ymax_base + offset_y:.6g} + (i // {cols}) * {sy}",
                }
            else:
                container_params = dict(base_cp)

        # ── Template config ───────────────────────────────────────────────────
        av_type = dist_config.avatar_type or ("rigidDisk" if dim == 2 else "rigidSphere")
        template_config = {
            "nb_particles":    dist_config.nb_particles,
            "radius_min":      dist_config.radius_min,
            "radius_max":      dist_config.radius_max,
            "container_type":  dist_config.container_type,
            "container_params": container_params,
            "material_name":   material,
            "model_name":      model_nom,
            "avatar_type":     av_type,
            "color":           color,
            "seed":            dist_config.seed,
        }

        group_name = (
            self.group_name_input.text().strip()
            if self.store_check.isChecked()
            else None
        )

        for_loop = ForLoop(
            loop_var='i',
            start_expr='0',
            end_expr=str(n_deposits),
            step_expr='1',
            target_type='granulo',
            template_config=template_config,
            group_name=group_name,
        )

        indices = self.controller.generate_for_loop(for_loop)
        self.loop_generated.emit()
        self.refresh()
        QMessageBox.information(
            self, "✅ Distribution(s) créée(s)",
            f"{n_deposits} dépôt(s) — {len(indices)} avatars au total.\n"
            f"Distribution : [{dist_config.radius_min:.4g} – {dist_config.radius_max:.4g}]  "
            f"({dist_config.nb_particles} particules)\n"
            f"Disposition : {pattern}  |  Groupe : {group_name or 'Aucun'}"
        )

    def _on_edit_from_tree(self):
        """Charge une boucle depuis l'arbre pour édition"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une boucle à modifier")
            return
        
        index = selected.data(0, Qt.ItemDataRole.UserRole)
        if index is None:
            return
        
        total_loops = len(self.controller.state.loops)
        
        if index < total_loops:
            loop = self.controller.state.loops[index]
            self.load_for_edit(index, loop)
        else:
            for_index = index - total_loops
            if for_index < len(self.controller.state.for_loops):
                for_loop = self.controller.state.for_loops[for_index]
                self.load_for_edit(index, for_loop=for_loop)

    def _on_update(self):
        """Met à jour une boucle existante"""
        if self.current_edit_index is None:
            return
        
        try:
            total_loops = len(self.controller.state.loops)
            loop_type = self.type_combo.currentText()
            
            if self.current_edit_index < total_loops:
                # Mise à jour boucle classique
                model_idx = self.avatar_combo.currentData()
                if model_idx is None:
                    raise ValidationError("Sélectionnez un avatar modèle")
                
                count = self.eval_int(self.count_input.text(), default=10, field_name="Nombre")
                radius = self.eval_float(self.radius_input.text(), default=2.0, field_name="Rayon")
                step = self.eval_float(self.step_input.text(), default=1.0, field_name="Pas")
                spiral_factor = self.eval_float(self.spiral_input.text(), default=0.1, field_name="Facteur spirale")
                offset_x = self.eval_float(self.offset_x_input.text(), default=0.0, field_name="Offset X")
                offset_y = self.eval_float(self.offset_y_input.text(), default=0.0, field_name="Offset Y")
                
                loop = Loop(
                    loop_type=loop_type,
                    model_avatar_index=model_idx,
                    count=count,
                    radius=radius,
                    step=step,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    spiral_factor=spiral_factor,
                    invert_axis=self.invert_check.isChecked(),
                    group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
                )
                
                self.controller.update_loop(self.current_edit_index, loop)
                self.loop_updated.emit()
                QMessageBox.information(self, "Succès", "✅ Boucle modifiée")
                
            else:
                # Mise à jour boucle For
                for_index = self.current_edit_index - total_loops
                template_text = self.template_input.toPlainText().strip()
                if not template_text:
                    raise ValidationError("Le template JSON est requis")
                
                template_config = json.loads(template_text)
                
                for_loop = ForLoop(
                    loop_var=self.loop_var_input.text().strip(),
                    start_expr=self.start_input.text().strip(),
                    end_expr=self.end_input.text().strip(),
                    step_expr=self.step_for_input.text().strip(),
                    target_type=self.target_type_combo.currentText(),
                    template_config=template_config,
                    group_name=self.group_name_input.text().strip() if self.store_check.isChecked() else None
                )
                
                self.controller.update_for_loop(for_index, for_loop)
                self.loop_updated.emit()
                QMessageBox.information(self, "Succès", "✅ Boucle For modifiée")
            
            self.refresh()
            self._on_cancel_edit()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Erreur JSON", f"Template JSON invalide:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Modification échouée:\n{e}")

    def load_for_edit(self, index: int, loop=None, for_loop=None):
        """Charge une boucle pour édition"""
        self.current_edit_index = index
        total_loops = len(self.controller.state.loops)
        
        if index < total_loops and loop is not None:
            # Boucle classique
            self.type_combo.setCurrentText(loop.loop_type)
            self.count_input.setText(str(loop.count))
            
            # Trouver l'avatar modèle
            for i in range(self.avatar_combo.count()):
                if self.avatar_combo.itemData(i) == loop.model_avatar_index:
                    self.avatar_combo.setCurrentIndex(i)
                    break
            
            self.radius_input.setText(str(loop.radius))
            self.step_input.setText(str(loop.step))
            self.offset_x_input.setText(str(loop.offset_x))
            self.offset_y_input.setText(str(loop.offset_y))
            self.spiral_input.setText(str(loop.spiral_factor))
            self.invert_check.setChecked(loop.invert_axis)
            
            if loop.group_name:
                self.store_check.setChecked(True)
                self.group_name_input.setText(loop.group_name)
        
        elif for_loop is not None:
            # Boucle For
            self.type_combo.setCurrentText("For")
            self.loop_var_input.setText(for_loop.loop_var)
            self.start_input.setText(for_loop.start_expr)
            self.end_input.setText(for_loop.end_expr)
            self.step_for_input.setText(for_loop.step_expr)
            self.target_type_combo.setCurrentText(for_loop.target_type)
            
            self.template_input.setPlainText(json.dumps(for_loop.template_config, indent=2))
            
            if for_loop.group_name:
                self.store_check.setChecked(True)
                self.group_name_input.setText(for_loop.group_name)
        
        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.cancel_btn.setVisible(True)
        
        self.help_label.setText(f"🔧 Mode édition : Boucle #{index + 1}")
        self.help_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 5px;")

    def _on_delete_from_tree(self):
        """Supprime une boucle depuis l'arbre"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une boucle à supprimer")
            return
        
        index = selected.data(0, Qt.ItemDataRole.UserRole)
        if index is None:
            return
        
        self._on_delete(index)

    def _on_delete(self, index: int):
        """Supprime une boucle"""
        total_loops = len(self.controller.state.loops)
        
        if index < total_loops:
            loop = self.controller.state.loops[index]
            reply = QMessageBox.question(
                self,
                "Confirmer la suppression",
                f"Supprimer la boucle #{index+1} ({loop.loop_type}, {loop.count} avatars) ?\n"
                "Tous les avatars générés par cette boucle seront supprimés.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.controller.remove_loop(index)
                self.loop_deleted.emit()
                QMessageBox.information(self, "Succès", "✅ Boucle supprimée")
                
                if self.current_edit_index == index:
                    self._on_cancel_edit()
                
                self.refresh()
        else:
            for_index = index - total_loops
            if for_index < len(self.controller.state.for_loops):
                for_loop = self.controller.state.for_loops[for_index]
                reply = QMessageBox.question(
                    self,
                    "Confirmer la suppression",
                    f"Supprimer la boucle For #{for_index+1} ?\n"
                    "Tous les éléments générés seront supprimés.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self.controller.remove_for_loop(for_index)
                    self.loop_deleted.emit()
                    QMessageBox.information(self, "Succès", "✅ Boucle For supprimée")
                    
                    if self.current_edit_index == index:
                        self._on_cancel_edit()
                    
                    self.refresh()

    def _on_regenerate_from_tree(self):
        """Régénère une boucle depuis l'arbre"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une boucle à régénérer")
            return
        
        index = selected.data(0, Qt.ItemDataRole.UserRole)
        if index is None:
            return
        
        self._on_regenerate(index)

    def _on_regenerate(self, index: int):
        """Régénère une boucle"""
        total_loops = len(self.controller.state.loops)
        
        if index < total_loops:
            loop = self.controller.state.loops[index]
            try:
                indices = self.controller.generate_loop(loop)
                QMessageBox.information(self, "Succès", f"♻️ {len(indices)} avatars régénérés")
                self.loop_generated.emit()
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Échec de la régénération :\n{e}")
        else:
            for_index = index - total_loops
            if for_index < len(self.controller.state.for_loops):
                for_loop = self.controller.state.for_loops[for_index]
                try:
                    indices = self.controller.generate_for_loop(for_loop)
                    QMessageBox.information(self, "Succès", f"♻️ {len(indices)} éléments régénérés")
                    self.loop_generated.emit()
                    self.refresh()
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Échec de la régénération :\n{e}")

    def _show_info(self):
        """Affiche les informations d'une boucle"""
        selected = self.tree.currentItem()
        if not selected:
            return
        
        index = selected.data(0, Qt.ItemDataRole.UserRole)
        if index is None:
            return
        
        total_loops = len(self.controller.state.loops)
        
        if index < total_loops:
            loop = self.controller.state.loops[index]
            avatar_idx = loop.model_avatar_index
            avatar_label = f"#{avatar_idx}" if avatar_idx < len(self.controller.state.avatars) else "Inconnu"
            
            info = f"<h3>Boucle #{index + 1}</h3>"
            info += f"<b>Type :</b> {loop.loop_type}<br>"
            info += f"<b>Nombre d'avatars :</b> {loop.count}<br>"
            info += f"<b>Avatar modèle :</b> {avatar_label}<br>"
            info += f"<b>Rayon :</b> {loop.radius}<br>"
            info += f"<b>Pas :</b> {loop.step}<br>"
            info += f"<b>Offset X :</b> {loop.offset_x}<br>"
            info += f"<b>Offset Y :</b> {loop.offset_y}<br>"
            info += f"<b>Facteur spirale :</b> {loop.spiral_factor}<br>"
            info += f"<b>Axe inversé :</b> {'Oui' if loop.invert_axis else 'Non'}<br>"
            info += f"<b>Groupe :</b> {loop.group_name or 'Aucun'}<br>"
        else:
            for_index = index - total_loops
            if for_index < len(self.controller.state.for_loops):
                for_loop = self.controller.state.for_loops[for_index]
                
                info = f"<h3>Boucle For #{for_index + 1}</h3>"
                info += f"<b>Variable :</b> {for_loop.loop_var}<br>"
                info += f"<b>Début :</b> {for_loop.start_expr}<br>"
                info += f"<b>Fin :</b> {for_loop.end_expr}<br>"
                info += f"<b>Step :</b> {for_loop.step_expr}<br>"
                info += f"<b>Type cible :</b> {for_loop.target_type}<br>"
                info += f"<b>Éléments générés :</b> {len(for_loop.generated_indices)}<br>"
                info += f"<b>Groupe :</b> {for_loop.group_name or 'Aucun'}<br>"
                info += f"<br><b>Template :</b><br><pre>{json.dumps(for_loop.template_config, indent=2)}</pre>"
        
        QMessageBox.information(self, f"Infos : Boucle #{index + 1}", info)

    def _on_cancel_edit(self):
        """Annule l'édition"""
        self.current_edit_index = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        #self._clear_form()
        self.help_label.setText("Sélectionnez un type de boucle pour voir les paramètres adaptés.")
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")

    def _clear_form(self):
        """Réinitialise le formulaire"""
        self.type_combo.setCurrentIndex(0)
        self.count_input.setText("10")
        self.radius_input.setText("2.0")
        self.step_input.setText("1.0")
        self.offset_x_input.setText("0.0")
        self.offset_y_input.setText("0.0")
        self.spiral_input.setText("0.1")
        self.invert_check.setChecked(False)
        self.store_check.setChecked(False)
        self.group_name_input.setText("boucle_groupe")

        self.loop_var_input.setText("i")
        self.start_input.setText("0")
        self.end_input.setText("10")
        self.step_for_input.setText("1")
        self.template_input.clear()

        # Réinitialiser le widget Distribution
        self.dist_color_input.setText("BLUEx")
        self.dist_step_spin.setValue(2.2)
        self.dist_ox_input.setText("0.0")
        self.dist_oy_input.setText("0.0")
        self.dist_pattern_combo.setCurrentIndex(0)

    def refresh(self):
        """Rafraîchit l'affichage"""
        # ── Avatar combo (boucles classiques) ─────────────────────────────────
        self.avatar_combo.clear()
        for i, avatar in enumerate(self.controller.state.avatars):
            if avatar.origin == AvatarOrigin.MANUAL:
                label = f"#{i} — {avatar.avatar_type.value} ({avatar.color})"
                self.avatar_combo.addItem(label, i)
        if self.avatar_combo.count() == 0:
            self.avatar_combo.addItem("(Aucun avatar manuel disponible)", None)

        # ── Distribution combos (widget Distribution + widget For/granulo) ────
        dist_items = []
        for i, gen in enumerate(self.controller.state.granulo_generations):
            label = (
                f"#{i+1}  [{gen.radius_min:.4g} – {gen.radius_max:.4g}]"
                f"  ({gen.nb_particles} rayons)"
            )
            dist_items.append((label, i))

        for combo in (self.dist_combo, self.for_dist_combo):
            combo.blockSignals(True)
            combo.clear()
            for label, idx in dist_items:
                combo.addItem(label, idx)
            if not dist_items:
                combo.addItem("(Aucune distribution disponible)", None)
            combo.blockSignals(False)

        # ── Combos matériau / modèle (widget Distribution) ───────────────────
        self.dist_mat_combo.clear()
        for m in self.controller.get_materials():
            self.dist_mat_combo.addItem(m.name)
        self.dist_mod_combo.clear()
        for m in self.controller.get_models():
            self.dist_mod_combo.addItem(m.name)

        # ── Arbre ─────────────────────────────────────────────────────────────
        self.tree.clear()

        for idx, loop in enumerate(self.controller.state.loops):
            avatar_idx   = loop.model_avatar_index
            avatar_label = (
                f"#{avatar_idx}"
                if avatar_idx < len(self.controller.state.avatars)
                else "Inconnu"
            )
            item = QTreeWidgetItem([
                str(idx + 1),
                loop.loop_type,
                str(loop.count),
                avatar_label,
                loop.group_name or "—",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, idx)
            self.tree.addTopLevelItem(item)

        if hasattr(self.controller.state, 'for_loops'):
            for idx, for_loop in enumerate(self.controller.state.for_loops):
                global_idx = len(self.controller.state.loops) + idx
                tc         = for_loop.template_config or {}

                if for_loop.target_type == 'granulo':
                    # Boucle sur distribution (For/granulo ou Distribution)
                    dist_idx = tc.get('dist_idx', '?')
                    gens     = self.controller.state.granulo_generations
                    if isinstance(dist_idx, int) and dist_idx < len(gens):
                        g      = gens[dist_idx]
                        detail = f"dist#{dist_idx+1}  [{g.radius_min:.4g}–{g.radius_max:.4g}]"
                    else:
                        detail = f"dist#{dist_idx}"
                    item = QTreeWidgetItem([
                        str(global_idx + 1),
                        "For (granulo)",
                        str(len(for_loop.generated_indices)),
                        detail,
                        for_loop.group_name or "—",
                    ])
                    item.setForeground(1, QBrush(QColor(160, 80, 0)))
                else:
                    item = QTreeWidgetItem([
                        str(global_idx + 1),
                        f"For ({for_loop.target_type})",
                        str(len(for_loop.generated_indices)),
                        f"{for_loop.loop_var}: {for_loop.start_expr}→{for_loop.end_expr}",
                        for_loop.group_name or "—",
                    ])
                    item.setForeground(1, QBrush(QColor(0, 100, 200)))

                item.setData(0, Qt.ItemDataRole.UserRole, global_idx)
                self.tree.addTopLevelItem(item)