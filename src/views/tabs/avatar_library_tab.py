
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMessageBox, QLabel, QFormLayout, QLineEdit, QGroupBox, QComboBox, 
    QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...core.avatar_factory import AvatarFactory, AvatarTemplate
from ...core.models import Avatar, AvatarOrigin
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController


class AvatarLibraryTab(QWidget):
    """Onglet bibliothèque d'avatars"""
    
    avatar_created = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.current_template = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout()
        
        # Panneau gauche : Bibliothèque
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("<b>📚 Bibliothèque d'Avatars</b>"))
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nom", "Description"])
        self.tree.setColumnWidth(0, 200)
        self.tree.itemClicked.connect(self._on_template_selected)
        left_panel.addWidget(self.tree)
        
        template_btn_layout = QHBoxLayout()
        
        new_template_btn = QPushButton("➕ Nouveau Template")
        new_template_btn.clicked.connect(self._on_new_template)
        template_btn_layout.addWidget(new_template_btn)
        
        save_template_btn = QPushButton("💾 Sauver comme Template")
        save_template_btn.clicked.connect(self._on_save_as_template)
        save_template_btn.setToolTip("Créer un template depuis un avatar existant")
        template_btn_layout.addWidget(save_template_btn)
        
        delete_template_btn = QPushButton("🗑️ Supprimer Template")
        delete_template_btn.clicked.connect(self._on_delete_template)
        template_btn_layout.addWidget(delete_template_btn)
        
        left_panel.addLayout(template_btn_layout)
        
        layout.addLayout(left_panel, 1)
        
        # Panneau droit : Paramètres
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("<b>⚙️ Paramètres</b>"))
        
        self.info_label = QLabel("<i>Sélectionnez un template</i>")
        self.info_label.setWordWrap(True)
        right_panel.addWidget(self.info_label)
        
        params_group = QGroupBox("Paramètres du Template")
        self.params_form = QFormLayout()
        params_group.setLayout(self.params_form)
        right_panel.addWidget(params_group)
        
        # Position
        position_group = QGroupBox("Position et Propriétés")
        pos_form = QFormLayout()
        
        self.center_input = QLineEdit("0.0, 0.0")
        pos_form.addRow("Centre:", self.center_input)
        
        self.material_combo = QLineEdit()
        pos_form.addRow("Matériau:", self.material_combo)
        
        self.model_combo = QLineEdit()
        pos_form.addRow("Modèle:", self.model_combo)
        
        self.color_input = QLineEdit("BLUEx")
        pos_form.addRow("Couleur:", self.color_input)
        
        position_group.setLayout(pos_form)
        right_panel.addWidget(position_group)
        
        # Boutons
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("✅ Créer Avatar")
        create_btn.clicked.connect(self._on_create)
        btn_layout.addWidget(create_btn)
        
        right_panel.addLayout(btn_layout)
        right_panel.addStretch()
        
        layout.addLayout(right_panel, 1)
        
        self.setLayout(layout)
        self.refresh()
    
  

    def _on_new_template(self):
        """Créer un nouveau template from scratch"""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QSpinBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Nouveau Template")
        dialog.resize(500, 600)
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Informations de base
        name_input = QLineEdit()
        name_input.setPlaceholderText("Ex: Particule Ovale")
        form.addRow("Nom:", name_input)
        
        desc_input = QLineEdit()
        desc_input.setPlaceholderText("Ex: Particule elliptique pour simulation")
        form.addRow("Description:", desc_input)
        
        category_input = QLineEdit("Personnalisés")
        form.addRow("Catégorie:", category_input)
        
        # Type d'avatar
        type_combo = QComboBox()
        dim = self.controller.state.dimension
        if dim == 2:
            types = ["rigidDisk", "rigidJonc", "rigidPolygon", "rigidOvoidPolygon",
                    "rigidDiscreteDisk", "rigidCluster", "roughWall", "fineWall", 
                    "smoothWall", "granuloRoughWall"]
        else:
            types = ["rigidSphere", "rigidPlan", "rigidCylinder", "rigidPolyhedron",
                    "roughWall3D", "granuloRoughWall3D"]
        
        type_combo.addItems(types)
        form.addRow("Type d'avatar:", type_combo)
        
        layout.addLayout(form)
        
        # Zone de paramètres
        params_group = QGroupBox("Paramètres par défaut")
        params_layout = QVBoxLayout()
        
        params_label = QLabel(
            "<i>Définissez les paramètres par défaut en JSON:</i><br>"
            "<b>Exemple pour rigidDisk:</b> {\"radius\": 0.1}<br>"
            "<b>Exemple pour rigidJonc:</b> {\"axis\": {\"axe1\": 0.2, \"axe2\": 0.1}}"
        )
        params_label.setWordWrap(True)
        params_layout.addWidget(params_label)
        
        params_input = QTextEdit()
        params_input.setPlainText('{"radius": 0.1}')
        params_input.setMaximumHeight(100)
        params_layout.addWidget(params_input)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Schema des paramètres (pour validation)
        schema_group = QGroupBox("Schéma de validation (optionnel)")
        schema_layout = QVBoxLayout()
        
        schema_label = QLabel(
            "<i>Définissez les contraintes sur les paramètres:</i><br>"
            "<b>Exemple:</b> {\"radius\": {\"type\": \"float\", \"min\": 0.001, \"max\": 10.0}}"
        )
        schema_label.setWordWrap(True)
        schema_layout.addWidget(schema_label)
        
        schema_input = QTextEdit()
        schema_input.setPlainText('{"radius": {"type": "float", "min": 0.001, "max": 10.0}}')
        schema_input.setMaximumHeight(100)
        schema_layout.addWidget(schema_input)
        
        schema_group.setLayout(schema_layout)
        layout.addWidget(schema_group)
        
        # Boutons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                import json
                from ...core.avatar_factory import AvatarTemplate
                from ...core.models import AvatarType
                
                name = name_input.text().strip()
                if not name:
                    raise ValueError("Le nom est requis")
                
                # Parser les paramètres
                default_params = json.loads(params_input.toPlainText())
                param_schema = json.loads(schema_input.toPlainText())
                
                # Créer le template
                template_id = f"custom_{name.lower().replace(' ', '_')}"
                
                template = AvatarTemplate(
                    name=name,
                    description=desc_input.text().strip(),
                    avatar_type=AvatarType(type_combo.currentText()),
                    default_params=default_params,
                    param_schema=param_schema
                )
                
                # Sauvegarder
                self._add_custom_template(
                    template_id, 
                    template, 
                    category_input.text().strip(), 
                    dim
                )
                
                QMessageBox.information(self, "Succès", 
                    f"✅ Template '{name}' créé")
                
                self.refresh()
                
            except json.JSONDecodeError as e:
                QMessageBox.critical(self, "Erreur JSON", 
                    f"Format JSON invalide:\n{e}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", 
                    f"Création échouée:\n{e}")
    
    def _on_template_selected(self, item: QTreeWidgetItem, column: int):
        """Quand un template est sélectionné"""
        template_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not template_id:
            return
        
        dim = self.controller.state.dimension
        template = AvatarFactory.get_template(template_id, dim)
        
        if not template:
            return
        
        self.current_template = template
        
        # Afficher les infos
        self.info_label.setText(f"<b>{template.name}</b><br>{template.description}")
        
        # Nettoyer le formulaire
        while self.params_form.count() > 0:
            item = self.params_form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Ajouter les paramètres
        for param_name, schema in template.param_schema.items():
            default = template.default_params.get(param_name, 0.1)
            input_field = QLineEdit(str(default))
            self.params_form.addRow(f"{param_name}:", input_field)
            input_field.setObjectName(param_name)
    
    # Dans avatar_library_tab.py, remplace la méthode _on_create():

    def _on_create(self):
        """Crée l'avatar depuis le template"""

        try:
            if not self.current_template:
                raise ValidationError("Sélectionnez un template dans la bibliothèque")
            # Parser le centre
            center = [float(x.strip()) for x in self.center_input.text().split(',')]
            if not center : 
                raise ValidationError("Le centre est requis")
            dim = self.controller.state.dimension
            if len(center) != dim:
                raise ValidationError(f"Le centre doit avoir {dim} coordonnées")
            material = self.material_combo.text().strip()
            if not material :
                raise ValidationError("Le matériau est requis")
            model  = self.model_combo.text().strip()
            if not model:
                raise ValidationError("Le modèle est requis")
            # Récupérer les paramètres personnalisés
            custom_params = {}
            
            for i in range(self.params_form.count()):
                item = self.params_form.itemAt(i)
                if item is None:
                    continue
                
                # Récupérer le widget
                widget = item.widget()
                if widget is None:
                    continue
                
                # Si c'est un QLineEdit avec objectName
                if isinstance(widget, QLineEdit) and widget.objectName():
                    param_name = widget.objectName()
                    try:
                        # Essayer de convertir en float
                        param_value = float(widget.text())
                        custom_params[param_name] = param_value
                    except ValueError:
                        # Garder comme string si pas un nombre
                        custom_params[param_name] = widget.text()
            
            # Créer l'avatar
            avatar = self.current_template.create(
                center=center,
                material=material,
                model=model,
                color=self.color_input.text().strip(),
                **custom_params
            )
            
            # Ajouter au projet
            self.controller.add_avatar(avatar)
            self.avatar_created.emit()
            self.refresh()

            QMessageBox.information(self, "Succès", f"✅ Avatar créé depuis '{self.current_template.name}'")
            
        except ValidationError as e:  
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Erreur", f"Création échouée:\n{e}\n\n{traceback.format_exc()}")
    
    def _on_save_as_template(self):
        """Créer un template depuis un avatar existant du projet"""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QComboBox
        
        # Liste des avatars manuels
        avatars = [a for a in self.controller.state.avatars 
                if a.origin == AvatarOrigin.MANUAL]
        
        if not avatars:
            QMessageBox.warning(self, "Aucun avatar", 
                "Créez d'abord un avatar manuellement pour en faire un template")
            return
        
        # Dialogue de sélection
        dialog = QDialog(self)
        dialog.setWindowTitle("Créer Template depuis Avatar")
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Sélection de l'avatar source
        avatar_combo = QComboBox()
        for i, avatar in enumerate(avatars):
            avatar_combo.addItem(
                f"#{i} - {avatar.avatar_type.value} ({avatar.color})",
                i
            )
        form.addRow("Avatar source:", avatar_combo)
        
        # Nom du template
        name_input = QLineEdit()
        name_input.setPlaceholderText("Ex: Ma Particule Custom")
        form.addRow("Nom du template:", name_input)
        
        # Description
        desc_input = QLineEdit()
        desc_input.setPlaceholderText("Ex: Particule hexagonale avec rayon 0.15m")
        form.addRow("Description:", desc_input)
        
        # Catégorie
        category_input = QLineEdit("Personnalisés")
        form.addRow("Catégorie:", category_input)
        
        layout.addLayout(form)
        
        # Boutons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            avatar_idx = avatar_combo.currentData()
            source_avatar = avatars[avatar_idx]
            
            template_name = name_input.text().strip()
            if not template_name:
                QMessageBox.warning(self, "Erreur", "Le nom est requis")
                return
            
            # Créer le template
            self._create_template_from_avatar(
                source_avatar,
                template_name,
                desc_input.text().strip(),
                category_input.text().strip()
            )

    def _create_template_from_avatar(self, avatar: Avatar, name: str, 
                                    description: str, category: str):
        """Crée un template depuis un avatar"""
        from ...core.avatar_factory import AvatarTemplate
        
        # Extraire les paramètres de l'avatar
        default_params = {}
        param_schema = {}
        
        if avatar.radius is not None:
            default_params['radius'] = avatar.radius
            param_schema['radius'] = {'type': float, 'min': 0.001, 'max': 10.0}
        
        if avatar.axis:
            default_params['axis'] = avatar.axis
            param_schema['axe1'] = {'type': float, 'min': 0.001, 'max': 10.0}
            param_schema['axe2'] = {'type': float, 'min': 0.001, 'max': 10.0}
        
        if avatar.nb_vertices:
            default_params['nb_vertices'] = avatar.nb_vertices
            param_schema['nb_vertices'] = {'type': int, 'min': 3, 'max': 100}
        
        if avatar.vertices:
            default_params['vertices'] = avatar.vertices
            default_params['generation_type'] = avatar.generation_type or 'full'
        
        if avatar.wall_params:
            default_params['wall_params'] = avatar.wall_params
            for key in avatar.wall_params.keys():
                param_schema[key] = {'type': float, 'min': 0.001, 'max': 100.0}
        
        # Créer le template
        template_id = f"custom_{name.lower().replace(' ', '_')}"
        
        template = AvatarTemplate(
            name=name,
            description=description,
            avatar_type=avatar.avatar_type,
            default_params=default_params,
            param_schema=param_schema
        )
        
        # Sauvegarder dans les templates personnalisés
        dim = self.controller.state.dimension
        self._add_custom_template(template_id, template, category, dim)
        
        QMessageBox.information(self, "Succès", 
            f"✅ Template '{name}' créé et ajouté à la bibliothèque")
        
        self.refresh()

    def _add_custom_template(self, template_id: str, template: AvatarTemplate, 
                            category: str, dimension: int):
        """Ajoute un template personnalisé"""
        # Charger les templates personnalisés depuis le projet
        if not hasattr(self.controller.state, 'custom_templates'):
            self.controller.state.custom_templates = {}
        
        if dimension not in self.controller.state.custom_templates:
            self.controller.state.custom_templates[dimension] = {}
        
        if category not in self.controller.state.custom_templates[dimension]:
            self.controller.state.custom_templates[dimension][category] = {}
        
        self.controller.state.custom_templates[dimension][category][template_id] = {
            'name': template.name,
            'description': template.description,
            'avatar_type': template.avatar_type.value,
            'default_params': template.default_params,
            'param_schema': template.param_schema
        }
        self.refresh()

    def _on_delete_template(self):
        """Supprime un template personnalisé"""
        selected = self.tree.currentItem()
        if not selected or not selected.data(0, Qt.ItemDataRole.UserRole):
            QMessageBox.warning(self, "Sélection", "Sélectionnez un template")
            return
        
        template_id = selected.data(0, Qt.ItemDataRole.UserRole)
        
        # Vérifier si c'est un template personnalisé
        if not template_id.startswith("custom_"):
            QMessageBox.warning(self, "Template système", 
                "Les templates système ne peuvent pas être supprimés")
            return
        
        reply = QMessageBox.question(self, "Confirmer",
            f"Supprimer le template '{selected.text(0)}' ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self._remove_custom_template(template_id)
            self.refresh()

    def _remove_custom_template(self, template_id: str):
        """Supprime un template personnalisé"""
        dim = self.controller.state.dimension
        
        if hasattr(self.controller.state, 'custom_templates'):
            for category, templates in self.controller.state.custom_templates.get(dim, {}).items():
                if template_id in templates:
                    del templates[template_id]
                    break

    def refresh(self):
        """Rafraîchit la bibliothèque (inclut templates personnalisés)"""
        self.tree.clear()
        
        dim = self.controller.state.dimension
        
        # Templates système
        categories = AvatarFactory.get_categories(dim)
        templates = AvatarFactory.list_templates(dim)
        
        for category, template_ids in categories.items():
            cat_item = QTreeWidgetItem([f"📦 {category}", ""])
            cat_item.setExpanded(True)
            
            for template_id in template_ids:
                template = templates.get(template_id)
                if template:
                    item = QTreeWidgetItem([template.name, template.description])
                    item.setData(0, Qt.ItemDataRole.UserRole, template_id)
                    cat_item.addChild(item)
            
            self.tree.addTopLevelItem(cat_item)
        
        # ✅ Templates personnalisés
        if hasattr(self.controller.state, 'custom_templates'):
            custom = self.controller.state.custom_templates.get(dim, {})
            
            for category, templates in custom.items():
                cat_item = QTreeWidgetItem([f"⭐ {category}", ""])
                cat_item.setExpanded(True)
                
                for template_id, template_data in templates.items():
                    from ...core.avatar_factory import AvatarTemplate
                    from ...core.models import AvatarType
                    
                    # Reconstruire le template
                    template = AvatarTemplate(
                        name=template_data['name'],
                        description=template_data['description'],
                        avatar_type=AvatarType(template_data['avatar_type']),
                        default_params=template_data['default_params'],
                        param_schema=template_data['param_schema']
                    )
                    
                    item = QTreeWidgetItem([template.name, template.description])
                    item.setData(0, Qt.ItemDataRole.UserRole, template_id)
                    cat_item.addChild(item)
                
                self.tree.addTopLevelItem(cat_item)
    
    