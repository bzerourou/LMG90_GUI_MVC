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


class EmptyAvatarTab(QWidget):
    """Onglet création d'avatars vides"""
    
    avatar_created = pyqtSignal()
    avatar_updated = pyqtSignal()
    avatar_deleted = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.current_edit_index = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        # === ARBRE ===
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
        
        # === FORMULAIRE ===
        form_label = QLabel("<b>📝 Formulaire Avatar Vide</b>")
        layout.addWidget(form_label)
        
        form = QFormLayout()
        
        self.dim_combo = QComboBox()
        self.dim_combo.addItems(["2", "3"])
        self.dim_combo.currentTextChanged.connect(self._on_dim_changed)
        form.addRow("Dimension :", self.dim_combo)
        
        self.center_label = QLabel("Centre (x,y) :")
        self.center_input = QLineEdit("0.0, 0.0")
        form.addRow(self.center_label, self.center_input)
        
        self.material_combo = QComboBox()
        form.addRow("Matériau :", self.material_combo)
        
        self.model_combo = QComboBox()
        form.addRow("Modèle :", self.model_combo)
        
        self.color_input = QLineEdit("BLUEx")
        form.addRow("Couleur :", self.color_input)
        
        layout.addLayout(form)
        
        # === CONTACTEURS ===
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
        
        # === BOUTONS ===
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
        
        self.setLayout(layout)
        
        self._add_contactor_row()
    
    def _on_dim_changed(self, dim_text):
        """Quand dimension change"""
        dim = int(dim_text)
        center_default = "0.0, 0.0" if dim == 2 else "0.0, 0.0, 0.0"
        self.center_input.setText(center_default)
        self.center_label.setText(f"Centre ({'x,y' if dim == 2 else 'x,y,z'}) :")
        for i in reversed(range(self.contactors_layout.count())):
            widget = self.contactors_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self._add_contactor_row()
    
    def _add_contactor_row(self):
        """Ajoute une ligne de contacteur"""
        row = QHBoxLayout()
        
        row.addWidget(QLabel("Forme :"))
        
        shape_combo = QComboBox()
        dim = int(self.dim_combo.currentText())
        if dim == 2:
            shape_combo.addItems(["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"])
        else:
            shape_combo.addItems(["SPHER",  "PLANx", "CYLND", "POLYR", "PT3Dx"])

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
        """Quand le type de contacteur change"""
        shape = row.shape_combo.currentText()
        
        if shape in ["DISKx", "xKSID"]:
            row.params_input.setText("byrd=0.3")
            row.params_label.setText("Params (byrd) :")
        elif shape == "JONCx":
            row.params_input.setText("axe1=1.0, axe2=0.1")
            row.params_label.setText("Params (axes) :")
        elif shape == "POLYG":
            row.params_input.setText("nb_vertices=4, vertices=[[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]]")
            row.params_label.setText("Params (vertices) :")
        elif shape == "PT2Dx":
            row.params_input.setText("")
            row.params_label.setText("Params :")
    
    def _remove_contactor_row(self, row):
        """Supprime une ligne de contacteur"""
        for i in range(self.contactors_layout.count()):
            widget = self.contactors_layout.itemAt(i).widget()
            if widget and widget.layout() == row:
                widget.deleteLater()
                return
    
    def _show_context_menu(self, position):
        """Menu contextuel"""
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
        """Crée l'avatar vide"""
        try:
            avatar = self._build_avatar_from_form()
            
            idx = self.controller.add_avatar(avatar)
            
            self.avatar_created.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"✅ Avatar vide #{idx} créé avec {len(avatar.contactors)} contacteur(s)")
            self._clear_form()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Erreur de Valeur", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def _on_edit_from_tree(self):
        """Charge pour édition"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un avatar")
            return
        
        avatar_idx = selected.data(0, Qt.ItemDataRole.UserRole)
        avatar = self.controller.get_avatar(avatar_idx)
        
        if avatar:
            self.load_for_edit(avatar_idx, avatar)
    
    def _on_update(self):
        """Met à jour"""
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
        """Supprime"""
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
        """Affiche infos"""
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
        """Annule édition"""
        self.current_edit_index = None
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self._clear_form()
    
    def _clear_form(self):
        """Réinitialise"""
        dim = int(self.dim_combo.currentText())
        self.center_input.setText("0.0, 0.0" if dim == 2 else "0.0, 0.0, 0.0")
        self.color_input.setText("BLUEx")
        
        # Supprimer tous les contacteurs
        for i in reversed(range(self.contactors_layout.count())):
            widget = self.contactors_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Ajouter un contacteur par défaut
        self._add_contactor_row()
    
    def _build_avatar_from_form(self) -> Avatar:
        """Construit un avatar depuis le formulaire"""
        dim = int(self.dim_combo.currentText())
        center = [float(x.strip()) for x in self.center_input.text().split(',')]
        
        if len(center) != dim:
            raise ValueError(f"Centre doit avoir {dim} coordonnées")
        
        # Parser les contacteurs
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
            model_name= model,
            color=self.color_input.text().strip(),
            origin=AvatarOrigin.MANUAL,
            contactors=contactors
        )
        
        return avatar
    
    def _parse_params(self, params_text: str) -> dict:
        """Parse les paramètres de contacteur"""
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
                        if '.' in val or 'e' in val.lower():
                            params[key] = float(val)
                        else:
                            params[key] = int(val)
                    except ValueError:
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
                    if '.' in value_str or 'e' in value_str.lower():
                        params[key] = float(value_str)
                    else:
                        params[key] = int(value_str)
                except ValueError:
                    raise ValueError(f"Valeur numérique invalide pour '{key}': {value_str}")
        
        return params
    
    def load_for_edit(self, index: int, avatar: Avatar):
        """Charge pour édition"""
        self.current_edit_index = index
        
        self.dim_combo.setCurrentText(str(len(avatar.center)))
        
        center_str = ", ".join(str(x) for x in avatar.center)
        self.center_input.setText(center_str)
        
        self.material_combo.setCurrentText(avatar.material_name)
        self.model_combo.setCurrentText(avatar.model_name)
        self.color_input.setText(avatar.color)
        
        # Supprimer contacteurs existants
        for i in reversed(range(self.contactors_layout.count())):
            widget = self.contactors_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Charger les contacteurs
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
        """Rafraîchit"""
        self.tree.clear()
        
        self.material_combo.clear()
        materials = self.controller.get_materials()
        self.material_combo.addItems([m.name for m in materials])
        
        self.model_combo.clear()
        models = self.controller.get_models()
        self.model_combo.addItems([m.name for m in models])
        
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