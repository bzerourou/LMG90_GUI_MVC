# ============================================================================
# empty_avatar_tab
# ============================================================================
"""
Onglet pour créer des avatars vides avec contacteurs personnalisés.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QPushButton, QMessageBox, QScrollArea, QLabel, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QMenu
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import Avatar, AvatarType, AvatarOrigin
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController
from ...views.tabs.base_tab import BaseTab


class EmptyAvatarTab(BaseTab):
    """Onglet création d'avatars vides"""
    
    avatar_created = pyqtSignal()
    avatar_updated = pyqtSignal()
    avatar_deleted = pyqtSignal()

    
    shapes_2d = ["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"]
    shapes_3d = ["SPHER",  "PLANx", "CYLND", "DNLYC", "POLYR", "PT3Dx"]
    mesh_shapes_2d = ["ALpxx", "CLxx" , "DISKL", "PT2TL"  ]  # contacteurs pour corps déformable 2d
    mesh_shapes_3d = [ "ASpxx", "CSpxx", "PT3Dx"  ]  # contacteurs pour corps déformable 3d
    
    def __init__(self, controller: ProjectController):
        super().__init__(controller)
        self.controller = controller
        self.current_edit_index = None
        self._setup_ui()
    
    def _setup_ui(self):
        # Layout principal
        main_layout = QVBoxLayout()
        
        # Créer une zone de défilement
        scroll_p = QScrollArea()
        scroll_p.setWidgetResizable(True)
        scroll_p.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_p.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget contenant tout le contenu
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        scroll_widget.setLayout(layout)
        
        tree_label = QLabel("<b>📋 Avatars Vides Existants</b>")
        layout.addWidget(tree_label)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["#", "Couleur", "Centre", "Contacteurs"])
        self.tree.setColumnWidth(0, 40)
        self.tree.setColumnWidth(1, 80)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(150)
        layout.addWidget(self.tree)
        
        tree_btn_layout = QHBoxLayout()
        edit_tree_btn = QPushButton("✏️ Modifier Sélection")
        edit_tree_btn.clicked.connect(self._on_edit_from_tree)
        tree_btn_layout.addWidget(edit_tree_btn)
        
        delete_tree_btn = QPushButton("🗑️ Supprimer Sélection")
        delete_tree_btn.clicked.connect(self._on_delete)
        tree_btn_layout.addWidget(delete_tree_btn)
        
        tree_btn_layout.addStretch()
        layout.addLayout(tree_btn_layout)
        
        form_label = QLabel("<b>📝 Formulaire Avatar Vide</b>")
        layout.addWidget(form_label)
        
        form = QFormLayout()

        # ── Mode : Avatar vide ou Corps déformable ────────────────────────────
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Avatar vide (emptyAvatar)", "Corps déformable existant"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        form.addRow("Mode :", self.mode_combo)

        # Sélecteur du corps déformable (visible en mode déformable uniquement)
        self.deformable_combo = QComboBox()
        self.deformable_label = QLabel("Corps déformable :")
        form.addRow(self.deformable_label, self.deformable_combo)
        self.deformable_label.setVisible(False)
        self.deformable_combo.setVisible(False)
        
        self.dim_combo = QComboBox()
        self.dim_combo.addItems(["2", "3"])
        self.dim_combo.currentTextChanged.connect(self._on_dim_changed)
        self._dim_label = QLabel("Dimension :")
        form.addRow(self._dim_label, self.dim_combo)
        
        self.center_label = QLabel("Centre (x,y) :")
        self.center_input = QLineEdit("0.0, 0.0")
        form.addRow(self.center_label, self.center_input)
        
        self.material_combo = QComboBox()
        self._mat_label = QLabel("Matériau :")
        form.addRow(self._mat_label, self.material_combo)
        
        self.model_combo = QComboBox()
        self._mod_label = QLabel("Modèle :")
        form.addRow(self._mod_label, self.model_combo)
        
        self.color_input = QLineEdit("BLUEx")
        self._color_label = QLabel("Couleur :")
        form.addRow(self._color_label, self.color_input)
        
        # Champ groupe (visible en mode déformable uniquement)
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("ex: 102  (laisser vide si aucun)")
        self._group_label = QLabel("Groupe (group=) :")
        form.addRow(self._group_label, self.group_input)
        self._group_label.setVisible(False)
        self.group_input.setVisible(False)
        
        layout.addLayout(form)
        
        layout.addWidget(QLabel("<b>Contacteurs à ajouter :</b>"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        contactors_widget = QWidget()
        self.contactors_layout = QVBoxLayout()
        contactors_widget.setLayout(self.contactors_layout)
        scroll.setWidget(contactors_widget)
        scroll.setMaximumHeight(200)
        
        layout.addWidget(scroll)
        
        add_cont_btn = QPushButton("➕ Ajouter un contacteur")
        add_cont_btn.clicked.connect(self._add_contactor_row)
        layout.addWidget(add_cont_btn)
        
        btn_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("✅ Créer Avatar Vide")
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
        
        scroll_p.setWidget(scroll_widget)
        main_layout.addWidget(scroll_p)
        self.setLayout(main_layout)
        
        self._add_contactor_row()
    
    def _on_dim_changed(self, dim_text):
        dim = int(dim_text)
        center_default = "0.0, 0.0" if dim == 2 else "0.0, 0.0, 0.0"
        self.center_input.setText(center_default)
        self.center_label.setText(f"Centre ({'x,y' if dim == 2 else 'x,y,z'}) :")
        for i in reversed(range(self.contactors_layout.count())):
            widget = self.contactors_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self._add_contactor_row()

    def _on_mode_changed(self, index):
        """Bascule entre mode emptyAvatar et mode corps déformable."""
        is_deformable = (index == 1)

        # Champs spécifiques emptyAvatar
        for w in (self._dim_label, self.dim_combo,
                  self.center_label, self.center_input,
                  self._mat_label, self.material_combo,
                  self._mod_label, self.model_combo,
                  self._color_label, self.color_input):
            w.setVisible(not is_deformable)

        # Champs spécifiques déformable
        self._dim_label.setVisible(True), self.dim_combo.setVisible(True),
        self.deformable_label.setVisible(is_deformable)
        self.deformable_combo.setVisible(is_deformable)
        self._group_label.setVisible(is_deformable)
        self.group_input.setVisible(is_deformable)

        # Forme des contacteurs : ajouter ASpxx en mode déformable
        self._refresh_contactor_shapes()

        self.create_btn.setText(
            "✅ Ajouter contacteurs au corps" if is_deformable else "✅ Créer Avatar Vide"
        )

    def _refresh_contactor_shapes(self):
        """Met à jour les combos de forme dans toutes les lignes de contacteurs."""
        is_deformable = self.mode_combo.currentIndex() == 1
        dim = int(self.dim_combo.currentText()) if not is_deformable else 3

        if dim == 2:
            shapes = self.mesh_shapes_2d if is_deformable else self.shapes_2d
        else:
            shapes = self.mesh_shapes_3d if is_deformable else self.shapes_3d

        for i in range(self.contactors_layout.count()):
            widget = self.contactors_layout.itemAt(i).widget()
            if not widget:
                continue
            row = widget.layout()
            if not hasattr(row, 'shape_combo'):
                continue
            current = row.shape_combo.currentText()
            row.shape_combo.blockSignals(True)
            row.shape_combo.clear()
            row.shape_combo.addItems(shapes)
            if current in shapes:
                row.shape_combo.setCurrentText(current)
            row.shape_combo.blockSignals(False)

        center_default = "0.0, 0.0" if dim == 2 else "0.0, 0.0, 0.0"
        self.center_input.setText(center_default)
        self.center_label.setText(f"Centre ({'x,y' if dim == 2 else 'x,y,z'}) :")
        for i in reversed(range(self.contactors_layout.count())):
            widget = self.contactors_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self._add_contactor_row()
    
    def _add_contactor_row(self):
        row = QHBoxLayout()
        
        row.addWidget(QLabel("Forme :"))
        
        shape_combo = QComboBox()
        dim = int(self.dim_combo.currentText())
        is_deformable = self.mode_combo.currentIndex() == 1
        if dim ==2 and is_deformable:
            shape_combo.addItems(self.mesh_shapes_2d)
        elif dim == 3 and is_deformable:
            shape_combo.addItems(self.mesh_shapes_3d)
        else:

            if dim == 2:
                shape_combo.addItems(self.shapes_2d)
            else:
                shape_combo.addItems(self.shapes_3d)

        shape_combo.currentTextChanged.connect(
            lambda: self._on_contactor_type_changed(row)
        )
        row.addWidget(shape_combo)
        
        row.addWidget(QLabel("Couleur :"))
        
        color_input = QLineEdit("BLUEx")
        row.addWidget(color_input)
        
        params_label = QLabel("Params :")
        row.addWidget(params_label)
        
        params_input = QLineEdit("byrd=0.3")
        row.addWidget(params_input)
        
        remove_btn = QPushButton("×")
        remove_btn.setFixedWidth(30)
        remove_btn.clicked.connect(lambda: self._remove_contactor_row(row))
        row.addWidget(remove_btn)
        
        row.shape_combo = shape_combo
        row.color_input = color_input
        row.params_label = params_label
        row.params_input = params_input
        
        widget = QWidget()
        widget.setLayout(row)
        self.contactors_layout.addWidget(widget)
    
    def _on_contactor_type_changed(self, row):
        shape = row.shape_combo.currentText()
        
        if shape in ["DISKx", "xKSID", "SPHER"]:
            row.params_input.setText("byrd=0.3")
            row.params_label.setText("Params (byrd) :")
        elif shape == "JONCx":
            row.params_input.setText("axe1=1.0, axe2=0.1")
            row.params_label.setText("Params (axes) :")
        elif shape == "POLYG":
            row.params_input.setText("nb_vertices=4, vertices=[[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]]")
            row.params_label.setText("Params (vertices) :")
        elif shape in  ["PT2Dx", "PT3Dx", "PT2TL", "PT3Dx"]:
            row.params_input.setText("")
            row.params_label.setText("Params :")
        elif shape == "PLANx":
            row.params_input.setText("axe1=1.0, axe2=1.0, axe3=0.1")
            row.params_label.setText("Params (axes) :")
        elif shape in [ "CYLND", "DNLYC"] :
            row.params_input.setText("byrd=0.5, High=1.0")
            row.params_label.setText("Params (radius, height) :")
        elif shape == "POLYR":
            row.params_input.setText("nb_vertices=4, vertices=[[-1.,-1.,-1.],[1.,-1.,-1.],[1.,1.,-1.],[-1.,1.,-1.],[-1.,-1.,1.],[1.,-1.,1.],[1.,1.,1.],[-1.,1.,1.]]")
            row.params_label.setText("Params (vertices) :")
        
        
    def _remove_contactor_row(self, row):
        for i in range(self.contactors_layout.count()):
            widget = self.contactors_layout.itemAt(i).widget()
            if widget and widget.layout() == row:
                widget.deleteLater()
                return
    
    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        edit_action = menu.addAction("✏️ Modifier")
        edit_action.triggered.connect(self._on_edit_from_tree)
        
        delete_action = menu.addAction("🗑️ Supprimer")
        delete_action.triggered.connect(self._on_delete)
        
        menu.addSeparator()
        
        info_action = menu.addAction("ℹ️ Informations")
        info_action.triggered.connect(self._show_info)
        
        menu.exec(self.tree.viewport().mapToGlobal(position))
    
    def _on_create(self):
        try:
            if self.mode_combo.currentIndex() == 1:
                self._add_contactors_to_deformable()
            else:
                avatar = self._build_avatar_from_form()
                idx = self.controller.add_avatar(avatar)
                self.avatar_created.emit()
                self.refresh()
                QMessageBox.information(self, "Succès", f"✅ Avatar vide #{idx} créé avec {len(avatar.contactors)} contacteur(s)")
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")

    def _add_contactors_to_deformable(self):
        """Applique addContactors sur un corps déformable pylmgc90 existant."""
        avatar_idx = self.deformable_combo.currentData()
        if avatar_idx is None:
            raise ValueError("Aucun corps déformable sélectionné.")

        body_obj = self.controller._pylmgc_bodies[avatar_idx]
        if body_obj is None:
            raise ValueError("Corps pylmgc90 introuvable (non reconstruit ?).")

        group = self.group_input.text().strip() or None
        n_added = 0

        for i in range(self.contactors_layout.count()):
            widget = self.contactors_layout.itemAt(i).widget()
            if not widget:
                continue
            row = widget.layout()
            shape = row.shape_combo.currentText()
            color = row.color_input.text().strip() or "BLEUx"
            params_text = row.params_input.text().strip()

            params = {}
            if params_text:
                params = self._parse_params(params_text)

            kwargs = {'shape': shape, 'color': color, **params}
            if group:
                kwargs['group'] = group

            body_obj.addContactors(**kwargs)
            n_added += 1

        # Mettre à jour les contacteurs dans l'avatar du state pour la sérialisation
        avatar = self.controller.state.avatars[avatar_idx]
        if avatar.contactors is None:
            avatar.contactors = []
        for i in range(self.contactors_layout.count()):
            widget = self.contactors_layout.itemAt(i).widget()
            if not widget:
                continue
            row = widget.layout()
            params_text = row.params_input.text().strip()
            params = self._parse_params(params_text) if params_text else {}
            entry = {'shape': row.shape_combo.currentText(),
                     'color': row.color_input.text().strip() or "BLEUx",
                     'params': params}
            if group:
                entry['group'] = group
            avatar.contactors.append(entry)

        self.controller.state_changed.emit()
        QMessageBox.information(self, "Succès",
            f"✅ {n_added} contacteur(s) ajouté(s) au corps déformable #{avatar_idx}")

    
    
    def _on_edit_from_tree(self):
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un avatar")
            return
        
        avatar_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        avatar = self.controller.get_avatar(avatar_idx)
        
        if avatar:
            self.load_for_edit(avatar_idx, avatar)
    
    def _on_update(self):
        try:
            avatar = self._build_avatar_from_form()
            
            self.controller.update_avatar(self.current_edit_index, avatar)
            
            self.avatar_updated.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", "✅ Avatar modifié")
            self._on_cancel_edit()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Modification échouée :\n{e}")
    
    def _on_delete(self):
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un avatar")
            return
        
        avatar_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        
        is_used, refs = self.controller.is_avatar_used(avatar_idx)
        
        if is_used:
            refs_text = "\n• ".join(refs)
            QMessageBox.warning(
                self, "Avatar Référencé",
                f"Cet avatar est référencé par :\n\n• {refs_text}\n\n"
                f"Supprimez d'abord ces références."
            )
            return
        
        reply = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer l'avatar vide #{avatar_idx} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.controller.remove_avatar(avatar_idx):
                self.avatar_deleted.emit()
                self.refresh()
                QMessageBox.information(self, "Succès", "✅ Avatar supprimé")
                if self.current_edit_index == avatar_idx:
                    self._on_cancel_edit()
    
    def _show_info(self):
        selected = self.tree.currentItem()
        if not selected:
            return
        
        avatar_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        avatar = self.controller.get_avatar(avatar_idx)
        if not avatar:
            return
        
        center_str = ', '.join(str(x) for x in avatar.center)
        
        info = f"<h3>Avatar Vide #{avatar_idx}</h3>"
        info += f"<b>Centre :</b> ({center_str})<br>"
        info += f"<b>Matériau :</b> {avatar.material_name}<br>"
        info += f"<b>Modèle :</b> {avatar.model_name}<br>"
        info += f"<b>Couleur :</b> {avatar.color}<br>"
        info += f"<br><b>Contacteurs ({len(avatar.contactors)}) :</b><br>"
        
        for i, cont in enumerate(avatar.contactors):
            info += f"  {i+1}. {cont['shape']} ({cont.get('color', 'N/A')})<br>"
        
        QMessageBox.information(self, f"Infos : Avatar #{avatar_idx}", info)
    
    def _on_cancel_edit(self):
        self.current_edit_index = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        #self._clear_form()
    
    def _clear_form(self):
        dim = int(self.dim_combo.currentText())
        self.center_input.setText("0.0, 0.0" if dim == 2 else "0.0, 0.0, 0.0")
        self.color_input.setText("BLUEx")
        
        for i in reversed(range(self.contactors_layout.count())):
            widget = self.contactors_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        self._add_contactor_row()
    
    def _build_avatar_from_form(self) -> Avatar:
        dim = int(self.dim_combo.currentText())
        center = self.eval_list(
            self.center_input.text(),
            expected_length=dim,
            field_name="Centre"
        )
        
        contactors = []
        for i in range(self.contactors_layout.count()):
            widget = self.contactors_layout.itemAt(i).widget()
            if not widget:
                continue
            
            row = widget.layout()
            shape = row.shape_combo.currentText()
            color = row.color_input.text().strip()
            params_text = row.params_input.text().strip()
            material = self.material_combo.currentText()
            model = self.model_combo.currentText()
            
            if not material:
                raise ValidationError("Le matériau est requis")
            
            if not model:
                raise ValidationError("Le modèle est requis")

            params = {}
            if params_text:
                try:
                    params = self._parse_params(params_text)
                except ValueError as e:
                    raise ValueError(f"Erreur dans les paramètres du contacteur : {e}")
            
            contactors.append({
                'shape': shape,
                'color': color or self.color_input.text(),
                'params': params
            })
        
        if not contactors:
            raise ValueError("Ajoutez au moins un contacteur")
        
        avatar = Avatar(
            avatar_type=AvatarType.EMPTY_AVATAR,
            center=center,
            material_name=material,
            model_name=model,
            color=self.color_input.text().strip(),
            origin=AvatarOrigin.MANUAL,
            contactors=contactors
        )
        
        return avatar
    
    def _parse_params(self, params_text: str) -> dict:
        import re
        import ast
        
        params = {}
        
        pattern = r'(\w+)\s*=\s*([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?|\[(?:[^\[\]]|\[[^\]]*\])*\])'
        
        matches = re.findall(pattern, params_text)
        
        if not matches:
            for pair in params_text.split(','):
                if '=' in pair:
                    key, val = pair.split('=', 1)
                    key = key.strip()
                    val = val.strip()
                    
                    try:
                        params[key] = self.eval_float(val, field_name=f"Paramètre {key}")
                    except:
                        params[key] = val
            
            return params
        
        for key, value_str in matches:
            key = key.strip()
            value_str = value_str.strip()
            
            if value_str.startswith('['):
                try:
                    value = ast.literal_eval(value_str)
                    if not isinstance(value, list):
                        raise ValueError(f"{key} : attendu une liste")
                    params[key] = value
                except Exception as e:
                    raise ValueError(f"Format de liste invalide pour '{key}': {value_str}")
            else:
                try:
                    params[key] = self.eval_float(value_str, field_name=f"Paramètre {key}")
                except:
                    params[key] = value_str
        
        return params
    
    def load_for_edit(self, index: int, avatar: Avatar):
        self.current_edit_index = index
        
        self.dim_combo.setCurrentText(str(len(avatar.center)))
        
        center_str = ", ".join(str(x) for x in avatar.center)
        self.center_input.setText(center_str)
        
        self.material_combo.setCurrentText(avatar.material_name)
        self.model_combo.setCurrentText(avatar.model_name)
        self.color_input.setText(avatar.color)
        
        for i in reversed(range(self.contactors_layout.count())):
            widget = self.contactors_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        for cont in avatar.contactors:
            self._add_contactor_row()
            widget = self.contactors_layout.itemAt(self.contactors_layout.count() - 1).widget()
            row = widget.layout()
            
            row.shape_combo.setCurrentText(cont['shape'])
            row.color_input.setText(cont.get('color', avatar.color))
            
            params = cont.get('params', {})
            if params:
                params_str = ", ".join(f"{k}={v}" for k, v in params.items())
                row.params_input.setText(params_str)
        
        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.cancel_btn.setVisible(True)
    
    def refresh(self):
        self.tree.clear()
        
        self.material_combo.clear()
        materials = self.controller.get_materials()
        self.material_combo.addItems([m.name for m in materials])
        
        self.model_combo.clear()
        models = self.controller.get_models()
        self.model_combo.addItems([m.name for m in models])

        # Peupler le combo des corps déformables
        self.deformable_combo.clear()
        for idx, av in enumerate(self.controller.state.avatars):
            if av.avatar_type == AvatarType.MESH_DEFORMABLE:
                mp = av.mesh_params or {}
                label = f"#{idx} — {mp.get('geom','mesh')}  ({av.material_name}/{av.model_name})"
                self.deformable_combo.addItem(label, idx)
        
        all_avatars = self.controller.state.avatars
        
        for real_index, avatar in enumerate(all_avatars):
            if avatar.avatar_type != AvatarType.EMPTY_AVATAR:
                continue
            
            center_str = ', '.join(f"{x:.2f}" for x in avatar.center)
            nb_contactors = len(avatar.contactors) if avatar.contactors else 0
            
            item = QTreeWidgetItem([
                str(real_index),
                avatar.color,
                f"({center_str})",
                f"{nb_contactors} contacteur(s)"
            ])
            
            item.setData(0, Qt.ItemDataRole.UserRole, real_index)
            
            self.tree.addTopLevelItem(item)