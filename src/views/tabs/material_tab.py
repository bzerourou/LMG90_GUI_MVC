# ============================================================================
#♀MaterialTab
# ============================================================================
"""
Onglet de gestion des matériaux avec création, modification et suppression.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QBrush, QColor

from ...core.models import Material, MaterialType
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController


class MaterialTab(QWidget):
    """Onglet de gestion des matériaux"""
    
    material_created = pyqtSignal()
    material_updated = pyqtSignal()
    material_deleted = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self.current_edit_name = None  # Pour tracking du mode édition
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        # === SECTION 1: ARBRE DES MATÉRIAUX ===
        tree_label = QLabel("<b>📋 Liste des Matériaux</b>")
        layout.addWidget(tree_label)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nom", "Type", "Densité", "Propriétés"])
        self.tree.setColumnWidth(0, 100)
        self.tree.setColumnWidth(1, 120)
        self.tree.setColumnWidth(2, 100)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setMaximumHeight(200)
        layout.addWidget(self.tree)
        
        # Boutons d'action rapide sur l'arbre
        tree_btn_layout = QHBoxLayout()
        
        edit_tree_btn = QPushButton("✏️ Modifier Sélection")
        edit_tree_btn.clicked.connect(self._on_edit_from_tree)
        tree_btn_layout.addWidget(edit_tree_btn)
        
        delete_tree_btn = QPushButton("🗑️ Supprimer Sélection")
        delete_tree_btn.clicked.connect(self._on_delete)
        tree_btn_layout.addWidget(delete_tree_btn)
        
        tree_btn_layout.addStretch()
        layout.addLayout(tree_btn_layout)
        
        # === SECTION 2: FORMULAIRE ===
        form_label = QLabel("<b>📝 Formulaire</b>")
        layout.addWidget(form_label)
        
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setMaxLength(5)
        self.name_input.setPlaceholderText("Ex: MAT1")
        form.addRow("Nom (max 5 car.) :", self.name_input)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([mt.value for mt in MaterialType])
        form.addRow("Type :", self.type_combo)
        
        self.density_input = QLineEdit()
        self.density_input.setPlaceholderText("Ex: 1000.0")
        form.addRow("Densité (kg/m³) :", self.density_input)
        
        self.props_input = QLineEdit()
        self.props_input.setPlaceholderText("ex: young=1e9, nu=0.3")
        form.addRow("Propriétés :", self.props_input)
        
        # Aide contextuelle
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        form.addRow("", self.help_label)
        
        layout.addLayout(form)
        
        # === SECTION 3: BOUTONS D'ACTION ===
        btn_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("✅ Créer Matériau")
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
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.tree.itemDoubleClicked.connect(self._on_edit_from_tree)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
    
    def _on_type_changed(self, mat_type: str):
        """Quand le type change, suggère des propriétés"""
        suggestions = {
            "RIGID": "Pas de propriétés requises pour un corps rigide",
            "ELAS": "young=1e11, nu=0.3",
            "ELAS_DILA": "young=1e11, nu=0.3, dilatation=1e-5",
            "VISCO_ELAS": "young=1e11, nu=0.3, viscous_young=1e9",
        }
        
        if mat_type in suggestions:
            self.help_label.setText(f"💡 Suggestion : {suggestions[mat_type]}")
            if mat_type != "RIGID" and not self.props_input.text():
                self.props_input.setPlaceholderText(suggestions[mat_type])
        else:
            self.help_label.setText("")
    
    def _show_context_menu(self, position):
        """Menu contextuel clic droit"""
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
        """Crée un nouveau matériau"""
        try:
            # Parser les propriétés
            props = self._parse_properties(self.props_input.text())
            
            # Créer le matériau
            material = Material(
                name=self.name_input.text().strip(),
                material_type=MaterialType(self.type_combo.currentText()),
                density=float(self.density_input.text()),
                properties=props
            )
            
            # Ajouter via le contrôleur
            self.controller.add_material(material)
            
            # Succès
            self.material_created.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"✅ Matériau '{material.name}' créé")
            
            # Réinitialiser le formulaire
            self._clear_form()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeur invalide :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def _on_edit_from_tree(self):
        """Charge le matériau sélectionné pour édition"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un matériau à modifier")
            return
        
        mat_name = selected.text(0)
        material = self.controller.get_material(mat_name)
        
        if not material:
            QMessageBox.warning(self, "Erreur", f"Matériau '{mat_name}' introuvable")
            return
        
        self.load_for_edit(material)
    
    def _on_update(self):
        """Met à jour le matériau existant"""
        try:
            # Parser les propriétés
            props = self._parse_properties(self.props_input.text())
            
            # Créer le nouveau matériau
            material = Material(
                name=self.name_input.text().strip(),
                material_type=MaterialType(self.type_combo.currentText()),
                density=float(self.density_input.text()),
                properties=props
            )
            
            # Mettre à jour via le contrôleur
            self.controller.update_material(self.current_edit_name, material)
            
            # Succès
            self.material_updated.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"✅ Matériau '{material.name}' modifié")
            
            # Sortir du mode édition
            self._on_cancel_edit()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeur invalide :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Modification échouée :\n{e}")
    
    def _on_delete(self):
        """Supprime le matériau sélectionné"""
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un matériau à supprimer")
            return
        
        mat_name = selected.text(0)
        
        # Vérifier si utilisé
        is_used, refs = self.controller.is_material_used(mat_name)
        
        if is_used:
            refs_text = "\n• ".join(refs[:10])
            if len(refs) > 10:
                refs_text += f"\n... et {len(refs) - 10} autre(s)"
            
            reply = QMessageBox.question(
                self, "⚠️ Matériau Utilisé",
                f"Le matériau '{mat_name}' est utilisé par :\n\n• {refs_text}\n\n"
                f"⚠️ ATTENTION : Supprimer ce matériau causera des erreurs.\n\n"
                f"Continuer quand même ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        else:
            reply = QMessageBox.question(
                self, "Confirmer",
                f"Supprimer le matériau '{mat_name}' ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Supprimer
        try:
            if self.controller.remove_material(mat_name):
                self.material_deleted.emit()
                self.refresh()

                if hasattr(self.parent(), 'tree_view'):
                    self.parent().tree_view.refresh()
                QMessageBox.information(self, "Succès", f"✅ Matériau '{mat_name}' supprimé")
                
                # Si c'était le matériau en cours d'édition, sortir du mode édition
                if self.current_edit_name == mat_name:
                    self._on_cancel_edit()
            else:
                QMessageBox.warning(self, "Erreur", "Impossible de supprimer")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Suppression échouée :\n{e}")
    
    def _show_info(self):
        """Affiche les informations détaillées"""
        selected = self.tree.currentItem()
        if not selected:
            return
        
        mat_name = selected.text(0)
        material = self.controller.get_material(mat_name)
        
        if not material:
            return
        
        is_used, refs = self.controller.is_material_used(mat_name)
        
        info = f"<h3>Matériau : {material.name}</h3>"
        info += f"<b>Type :</b> {material.material_type.value}<br>"
        info += f"<b>Densité :</b> {material.density} kg/m³<br>"
        
        if material.properties:
            info += "<br><b>Propriétés :</b><br>"
            for key, value in material.properties.items():
                info += f"  • {key} = {value}<br>"
        
        if is_used:
            info += f"<br><b>✅ Utilisé par :</b> {len(refs)} avatar(s)"
        else:
            info += "<br><i>❌ Non utilisé</i>"
        
        QMessageBox.information(self, f"Infos : {mat_name}", info)
    
    def _on_cancel_edit(self):
        """Annule le mode édition"""
        self.current_edit_name = None
        
        # Revenir en mode création
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        
        # Réinitialiser le formulaire
        self._clear_form()
    
    def _clear_form(self):
        """Réinitialise le formulaire"""
        self.name_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.density_input.clear()
        self.props_input.clear()
        self.help_label.clear()
        self.name_input.setFocus()
    
    def _parse_properties(self, text: str) -> dict:
        """Parse la chaîne de propriétés"""
        if not text.strip():
            return {}
        
        props = {}
        for pair in text.split(','):
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Essayer de convertir en nombre
                try:
                    if '.' in value or 'e' in value.lower():
                        props[key] = float(value)
                    else:
                        props[key] = int(value)
                except ValueError:
                    props[key] = value
        
        return props
    
    def load_for_edit(self, material: Material):
        """Charge un matériau pour édition"""
        self.current_edit_name = material.name
        
        # Remplir le formulaire
        self.name_input.setText(material.name)
        self.type_combo.setCurrentText(material.material_type.value)
        self.density_input.setText(str(material.density))
        
        if material.properties:
            props_str = ", ".join(f"{k}={v}" for k, v in material.properties.items())
            self.props_input.setText(props_str)
        else:
            self.props_input.clear()
        
        # Passer en mode édition
        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.cancel_btn.setVisible(True)
        
        # Highlight visuel
        self.name_input.setFocus()
        self.name_input.selectAll()
        
        # Message dans la barre d'aide
        self.help_label.setText(f"🔧 Mode édition : {material.name}")
        self.help_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 5px;")
    
    def refresh(self):
        """Rafraîchit l'arbre"""
        self.tree.clear()
        
        materials = self.controller.get_materials()
        
        for mat in materials:
            props_str = ", ".join(f"{k}={v}" for k, v in list(mat.properties.items())[:3])
            if len(mat.properties) > 3:
                props_str += "..."
            
            item = QTreeWidgetItem([
                mat.name,
                mat.material_type.value,
                str(mat.density),
                props_str
            ])
            
            # Colorer si utilisé
            is_used, _ = self.controller.is_material_used(mat.name)
            if is_used:
                item.setForeground(0, QBrush(QColor(0, 100, 0)))  # Vert foncé
            
            self.tree.addTopLevelItem(item)