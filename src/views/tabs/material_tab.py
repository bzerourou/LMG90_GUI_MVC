
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
from ...views.tabs.base_tab import BaseTab


class MaterialTab(BaseTab):
    """Onglet de gestion des matériaux"""
    
    material_created = pyqtSignal()
    material_updated = pyqtSignal()
    material_deleted = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__(controller)
        self.controller = controller
        self.current_edit_name = None
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
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
        
        tree_btn_layout = QHBoxLayout()
        
        edit_tree_btn = QPushButton("✏️ Modifier Sélection")
        edit_tree_btn.clicked.connect(self._on_edit_from_tree)
        tree_btn_layout.addWidget(edit_tree_btn)
        
        delete_tree_btn = QPushButton("🗑️ Supprimer Sélection")
        delete_tree_btn.clicked.connect(self._on_delete)
        tree_btn_layout.addWidget(delete_tree_btn)
        
        tree_btn_layout.addStretch()
        layout.addLayout(tree_btn_layout)
        
        form_label = QLabel("<b>📝 Formulaire</b>")
        layout.addWidget(form_label)
        
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setMaxLength(5)
        self.name_input.setText("TDURx")
        form.addRow("Nom (max 5 car.) :", self.name_input)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([mt.value for mt in MaterialType])
        form.addRow("Type :", self.type_combo)
        
        self.density_input = QLineEdit()
        self.density_input.setText("2800")
        form.addRow("Densité (kg/m³) :", self.density_input)
        
        self.props_input = QLineEdit()
        self.props_input.setPlaceholderText("ex: young=1e9, nu=0.3")
        form.addRow("Propriétés :", self.props_input)
        
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        form.addRow("", self.help_label)
        
        layout.addLayout(form)
        
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
        self.add_expression_help_label(layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _connect_signals(self):
        self.tree.itemDoubleClicked.connect(self._on_edit_from_tree)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
    
    def _on_type_changed(self, mat_type: str):
        self.density_input.setText("2800")
        self.name_input.setText("TDURx")
        suggestions = {
            "RIGID": "",
            "ELAS": "elas='standard', young=0.1e+15, nu=0.2, anisotropy='isotropic'",
            "ELAS_DILA": "elas='standard', young=0.1e+15, nu=0.2, anisotropy='isotropic',dilatation=1e-5, T_ref_meca=20.",
            "VISCO_ELAS": "elas='standard', anisotropy='isotropic', young=1.17e11, nu=0.35,viscous_model='KelvinVoigt', viscous_young=1.17e9, viscous_nu=0.35",
            "ELAS_PLAS": "elas='standard', anisotropy='isotropic', young=1.17e11, nu=0.35,critere='Von-Mises', isoh='linear', iso_hard=4.e8, isoh_coeff=1e8, cinh='none', visc='none'",
            "THERMO_ELAS": "elas='standard', young=0.0, nu=0.0, anisotropy='isotropic', dilatation = 0.0,T_ref_meca = 0.0, conductivity='field', specific_capacity='field'",
            "PORO_ELAS": "elas='standard', young=0.0, nu=0.0, anisotropy='isotropic',hydro_cpl = 0.0, conductivity='field', specific_capacity='field'"
        }
        
        if mat_type in suggestions:
            self.help_label.setText(f"💡 Suggestion : {suggestions[mat_type]}")
            
            if mat_type != "RIGID":
                self.props_input.setText(suggestions[mat_type])
            else:
                self.props_input.setText("")
        else:
            self.help_label.setText("")
    
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
            density = self.eval_float(
                self.density_input.text(),
                default=2800,
                field_name="Densité"
            )
            
            props = self.eval_dict(
                self.props_input.text(),
                field_name="Propriétés"
            )
            
            material = Material(
                name=self.name_input.text().strip(),
                material_type=MaterialType(self.type_combo.currentText()),
                density=density,
                properties=props
            )
            
            self.controller.add_material(material)
            self.material_created.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"✅ Matériau '{material.name}' créé")
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def _on_edit_from_tree(self):
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
        try:
            density = self.eval_float(
                self.density_input.text(),
                default=2800,
                field_name="Densité"
            )
            
            props = self.eval_dict(
                self.props_input.text(),
                field_name="Propriétés"
            )
            
            material = Material(
                name=self.name_input.text().strip(),
                material_type=MaterialType(self.type_combo.currentText()),
                density=density,
                properties=props
            )
            
            self.controller.update_material(self.current_edit_name, material)
            
            self.material_updated.emit()
            self.refresh()
            QMessageBox.information(self, "Succès", f"✅ Matériau '{material.name}' modifié")
            self._on_cancel_edit()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Modification échouée :\n{e}")
    
    def _on_delete(self):
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez un matériau à supprimer")
            return
        
        mat_name = selected.text(0)
        
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
        
        try:
            if self.controller.remove_material(mat_name):
                self.material_deleted.emit()
                self.refresh()

                if hasattr(self.parent(), 'tree_view'):
                    self.parent().tree_view.refresh()
                QMessageBox.information(self, "Succès", f"✅ Matériau '{mat_name}' supprimé")
                
                if self.current_edit_name == mat_name:
                    self._on_cancel_edit()
            else:
                QMessageBox.warning(self, "Erreur", "Impossible de supprimer")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Suppression échouée :\n{e}")
    
    def _show_info(self):
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
        self.current_edit_name = None
        
        self.create_btn.setVisible(True)
        self.update_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        
        #self._clear_form()
    
    def _clear_form(self):
        self.name_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.density_input.clear()
        self.props_input.clear()
        self.help_label.clear()
        self.name_input.setFocus()
    
    def load_for_edit(self, material: Material):
        self.current_edit_name = material.name
        
        self.name_input.setText(material.name)
        self.type_combo.setCurrentText(material.material_type.value)
        self.density_input.setText(str(material.density))
        
        if material.properties:
            props_str = ", ".join(f"{k}={v}" for k, v in material.properties.items())
            self.props_input.setText(props_str)
        else:
            self.props_input.clear()
        
        self.create_btn.setVisible(False)
        self.update_btn.setVisible(True)
        self.cancel_btn.setVisible(True)
        
        self.name_input.setFocus()
        self.name_input.selectAll()
        
        self.help_label.setText(f"🔧 Mode édition : {material.name}")
        self.help_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 5px;")
    
    def refresh(self):
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
            
            is_used, _ = self.controller.is_material_used(mat.name)
            if is_used:
                item.setForeground(0, QBrush(QColor(0, 100, 0)))
            
            self.tree.addTopLevelItem(item)