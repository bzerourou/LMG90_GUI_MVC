# ============================================================================
# Dialogues personnalisés
# ============================================================================
"""
Dialogues personnalisés de l'application.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QDialogButtonBox, 
    QInputDialog, QLabel, QLineEdit, QFormLayout,
    QGroupBox, QFileDialog, QSpinBox, QCheckBox, QComboBox, QMessageBox
)

from PyQt6.QtCore import Qt
from typing import Dict, Any
from pathlib import Path
from typing import Optional
from ..core.models import Material, MaterialType, ProjectPreferences, UnitSystem


class DynamicVarsDialog(QDialog):
    """Dialogue pour gérer les variables dynamiques avec support des références internes"""
    
    def __init__(self, current_vars: Dict[str, Any], controller, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Variables dynamiques")
        self.resize(800, 600)
        self.current_vars = current_vars.copy()
        self.controller = controller
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        # Info en haut
        info = QLabel(
            "<b>💡 Variables Dynamiques Avancées</b><br>"
            "Définissez des variables réutilisables dans tout le projet.<br><br>"
            "<b>Types supportés :</b><br>"
            "• <b>Constantes</b> : thickness = 0.5<br>"
            "• <b>Expressions</b> : radius = thickness * 2<br>"
            "• <b>Références avatars</b> : x_pos = avatar[0].nodes[1].coor[0]<br>"
            "• <b>Propriétés matériaux</b> : dens = material['MAT1'].density"
        )
        info.setWordWrap(True)
        info.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(info)
        
        # Tableau des variables
        self.table = QTreeWidget()
        self.table.setHeaderLabels(["Nom", "Expression", "Valeur Évaluée", "Type"])
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 250)
        self.table.setColumnWidth(2, 150)
        self._populate_table()
        layout.addWidget(self.table)
        
        # Formulaire d'ajout
        form_group = QGroupBox("➕ Ajouter/Modifier une Variable")
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex: thickness, radius, x_wall")
        form.addRow("Nom de variable :", self.name_input)
        
        self.expr_input = QLineEdit()
        self.expr_input.setPlaceholderText("Ex: 0.5 ou avatar[0].center[0] + 1.0")
        self.expr_input.textChanged.connect(self._on_expr_changed)
        form.addRow("Expression :", self.expr_input)
        
        self.preview_label = QLabel("<i>Entrez une expression pour voir le résultat</i>")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: #666; font-style: italic;")
        form.addRow("Aperçu :", self.preview_label)
        
        form_group.setLayout(form)
        layout.addWidget(form_group)
        
        # Exemples
        examples_group = QGroupBox("📋 Exemples d'Expressions")
        examples_layout = QVBoxLayout()
        
        examples = [
            ("Constante simple", "thickness = 0.5"),
            ("Expression mathématique", "radius = thickness * 2 + 0.1"),
            ("Centre X du 1er avatar", "x0 = avatar[0].center[0]"),
            ("Rayon du 3ème avatar", "r3 = avatar[2].radius"),
            ("Densité d'un matériau", "dens = material['MAT1'].density"),
            ("Nombre total d'avatars", "nb_avatars = len(avatar)"),
            ("Distance entre 2 avatars", "dist = sqrt((avatar[1].center[0] - avatar[0].center[0])**2)"),
        ]
        
        for title, example in examples:
            btn = QPushButton(f"{title}: {example}")
            btn.setStyleSheet("text-align: left; padding: 5px;")
            btn.clicked.connect(lambda checked, e=example: self._load_example(e))
            examples_layout.addWidget(btn)
        
        examples_group.setLayout(examples_layout)
        layout.addWidget(examples_group)
        
        # Boutons actions
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ Ajouter/Modifier")
        add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton("🗑️ Supprimer")
        del_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(del_btn)
        
        refresh_btn = QPushButton("🔄 Rafraîchir Tout")
        refresh_btn.clicked.connect(self._refresh_all_values)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Boutons OK/Annuler
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def _load_example(self, example: str):
        """Charge un exemple dans le formulaire"""
        if '=' in example:
            name, expr = example.split('=', 1)
            self.name_input.setText(name.strip())
            self.expr_input.setText(expr.strip())
    
    def _on_expr_changed(self):
        """Quand l'expression change, évaluer en temps réel"""
        expr = self.expr_input.text().strip()
        if not expr:
            self.preview_label.setText("<i>Entrez une expression</i>")
            self.preview_label.setStyleSheet("color: #666;")
            return
        
        try:
            value = self._evaluate_expression(expr)
            self.preview_label.setText(f"✅ Résultat : {value} (type: {type(value).__name__})")
            self.preview_label.setStyleSheet("color: green;")
        except Exception as e:
            self.preview_label.setText(f"❌ Erreur : {str(e)}")
            self.preview_label.setStyleSheet("color: red;")
    
    def _evaluate_expression(self, expr: str) -> Any:
        """Évalue une expression avec accès aux avatars et matériaux"""
        import math
        import numpy as np
        
        evaluated_vars = {}
        for var_name, var_expr in self.current_vars.items():
            try:
                if isinstance(var_expr, str):
                    # Évaluer récursivement
                    evaluated_vars[var_name] = self._evaluate_single(var_expr, evaluated_vars)
                else:
                    evaluated_vars[var_name] = var_expr
            except:
                evaluated_vars[var_name] = var_expr
        # Créer le contexte d'évaluation
        context = {
            'math': math,
            'np': np,
            'sqrt': math.sqrt,
            'pi': math.pi,
            'e': math.e,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'len': len,
            'avatar': self._create_avatar_proxy(),
            'material': self._create_material_proxy(),
            'model': self._create_model_proxy(),
        }
        
        # Ajouter les variables déjà définies
        context.update(evaluated_vars)
        
        # Évaluer de manière sécurisée
        try:
            result = eval(expr, {"__builtins__": {}}, context)
            return result
        except Exception as e:
            raise ValueError(f"Expression invalide : {e}")
    
    def _evaluate_single(self, expr: str, existing_vars: dict) -> Any:
        """Évalue une seule expression avec variables existantes"""
        import math
        import numpy as np
        
        context = {
            'math': math,
            'np': np,
            'sqrt': math.sqrt,
            'pi': math.pi,
            'e': math.e,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'len': len,
            'avatar': self._create_avatar_proxy(),
            'material': self._create_material_proxy(),
            'model': self._create_model_proxy(),
        }
        
        context.update(existing_vars)
        
        return eval(expr, {"__builtins__": {}}, context)    
    
    def _create_avatar_proxy(self):
        """Crée un proxy pour accéder aux avatars comme avatar[i].center[0]"""
        class AvatarProxy:
            def __init__(self, controller):
                self.controller = controller
            
            def __getitem__(self, index):
                avatars = self.controller.state.avatars
                if not isinstance(index, int) or index < 0 or index >= len(avatars):
                    raise IndexError(f"Avatar index {index} invalide (0-{len(avatars)-1})")
                return self._avatar_to_dict(avatars[index])
            
            def __len__(self):
                return len(self.controller.state.avatars)
            
            def _avatar_to_dict(self, avatar):
                """Convertit un avatar en dict accessible"""
                class AvatarDict(dict):
                    def __init__(self, av):
                        super().__init__()
                        self['center'] = av.center
                        self['radius'] = av.radius
                        self['color'] = av.color
                        self['material_name'] = av.material_name
                        self['model_name'] = av.model_name
                        self['avatar_type'] = av.avatar_type.value
                        # Simuler nodes (pour compatibilité)
                        self['nodes'] = [{'coor': av.center}]
                    
                    def __getattr__(self, name):
                        return self.get(name)
                
                return AvatarDict(avatar)
        
        return AvatarProxy(self.controller)
    
    def _create_material_proxy(self):
        """Crée un proxy pour accéder aux matériaux comme material['MAT1'].density"""
        class MaterialProxy:
            def __init__(self, controller):
                self.controller = controller
            
            def __getitem__(self, name):
                mat = self.controller.get_material(name)
                if not mat:
                    raise KeyError(f"Matériau '{name}' introuvable")
                
                class MaterialDict(dict):
                    def __init__(self, m):
                        super().__init__()
                        self['name'] = m.name
                        self['density'] = m.density
                        self['material_type'] = m.material_type.value
                        self.update(m.properties)
                    
                    def __getattr__(self, name):
                        return self.get(name)
                
                return MaterialDict(mat)
        
        return MaterialProxy(self.controller)
    
    def _create_model_proxy(self):
        """Crée un proxy pour accéder aux modèles"""
        class ModelProxy:
            def __init__(self, controller):
                self.controller = controller
            
            def __getitem__(self, name):
                mod = self.controller.get_model(name)
                if not mod:
                    raise KeyError(f"Modèle '{name}' introuvable")
                
                class ModelDict(dict):
                    def __init__(self, m):
                        super().__init__()
                        self['name'] = m.name
                        self['physics'] = m.physics
                        self['element'] = m.element
                        self['dimension'] = m.dimension
                        self.update(m.options)
                    
                    def __getattr__(self, name):
                        return self.get(name)
                
                return ModelDict(mod)
        
        return ModelProxy(self.controller)
    
    def _populate_table(self):
        """Remplit le tableau"""
        self.table.clear()
        evaluated = {}
        for name, expr in self.current_vars.items():
            # Évaluer la valeur
            try:
                if isinstance(expr, str):
                    value = self._evaluate_single(expr, evaluated)
                else:
                    value = expr
                evaluated[name] = value
                value_str = str(value)
                if isinstance(value, float):
                    value_str = f"{value:.6g}"
                
                type_str = type(value).__name__
                status = "✅"
            except Exception as e:
                value_str = f"Erreur: {e}"
                type_str = "error"
                status = "❌"
            
            item = QTreeWidgetItem([
                name,
                str(expr),
                value_str,
                type_str
            ])
            
            # Colorer selon le statut
            if status == "❌":
                from PyQt6.QtGui import QBrush, QColor
                item.setForeground(2, QBrush(QColor("red")))
            
            self.table.addTopLevelItem(item)
    
    def _on_add(self):
        """Ajoute ou modifie une variable"""
        name = self.name_input.text().strip()
        expr = self.expr_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Nom requis", "Entrez un nom de variable")
            return
        
        if not expr:
            QMessageBox.warning(self, "Expression requise", "Entrez une expression")
            return
        
        # Vérifier que l'expression est valide
        try:
            self._evaluate_expression(expr)
        except Exception as e:
            QMessageBox.critical(self, "Expression invalide", f"Erreur : {e}")
            return
        
        # Ajouter ou modifier
        self.current_vars[name] = expr
        self._populate_table()
        
        # Réinitialiser le formulaire
        self.name_input.clear()
        self.expr_input.clear()
    
    def _on_delete(self):
        """Supprime la variable sélectionnée"""
        selected = self.table.currentItem()
        if selected:
            name = selected.text(0)
            
            reply = QMessageBox.question(
                self, "Confirmer",
                f"Supprimer la variable '{name}' ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                del self.current_vars[name]
                self._populate_table()
    
    def _refresh_all_values(self):
        """Rafraîchit toutes les valeurs évaluées"""
        self._populate_table()
    
    def get_vars(self) -> Dict[str, Any]:
        """Retourne les variables"""
        return self.current_vars

class PreferencesDialog(QDialog):
    """Dialogue de préférences du projet"""
    
    def __init__(self, preferences: ProjectPreferences, parent=None):
        super().__init__(parent)
        self.preferences = preferences
        self.setWindowTitle("⚙️ Préférences du Projet")
        self.resize(600, 500)
        
        self._setup_ui()
        self._load_preferences()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        # ========== GROUPE 1 : Chemins ==========
        paths_group = QGroupBox("📁 Chemins et Fichiers")
        paths_layout = QFormLayout()
        
        # Chemin par défaut du projet
        path_layout = QHBoxLayout()
        self.project_path_input = QLineEdit()
        self.project_path_input.setReadOnly(True)
        self.project_path_input.setPlaceholderText("Aucun chemin par défaut")
        path_layout.addWidget(self.project_path_input)
        
        browse_btn = QPushButton("📂 Parcourir")
        browse_btn.clicked.connect(self._browse_project_path)
        path_layout.addWidget(browse_btn)
        
        clear_btn = QPushButton("✖")
        clear_btn.setMaximumWidth(40)
        clear_btn.clicked.connect(lambda: self.project_path_input.clear())
        path_layout.addWidget(clear_btn)
        
        paths_layout.addRow("Dossier par défaut :", path_layout)
        
        # Info
        info_label = QLabel(
            "💡 Les nouveaux projets seront créés dans ce dossier par défaut."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        paths_layout.addRow("", info_label)
        
        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)
        
        # ========== GROUPE 2 : Unités ==========
        units_group = QGroupBox("📏 Système d'Unités")
        units_layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.unit_system_combo = QComboBox()
        self.unit_system_combo.addItem("SI - Système International (m, kg, s, N, Pa)", UnitSystem.SI)
        self.unit_system_combo.addItem("CGS - Centimètre-Gramme-Seconde (cm, g, s)", UnitSystem.CGS)
        self.unit_system_combo.currentIndexChanged.connect(self._update_unit_preview)
        form.addRow("Système :", self.unit_system_combo)
        
        units_layout.addLayout(form)
        
        # Aperçu des unités
        self.units_preview = QLabel()
        self.units_preview.setWordWrap(True)
        self.units_preview.setStyleSheet(
            "background-color: #f0f0f0; padding: 10px; border-radius: 5px; font-family: monospace;"
        )
        units_layout.addWidget(QLabel("<b>Aperçu des unités :</b>"))
        units_layout.addWidget(self.units_preview)
        
        units_group.setLayout(units_layout)
        layout.addWidget(units_group)
        
        # ========== GROUPE 3 : Sauvegarde Automatique ==========
        autosave_group = QGroupBox("💾 Sauvegarde Automatique")
        autosave_layout = QFormLayout()
        
        self.auto_save_check = QCheckBox("Activer la sauvegarde automatique")
        autosave_layout.addRow("", self.auto_save_check)
        
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setMinimum(60)
        self.auto_save_interval.setMaximum(3600)
        self.auto_save_interval.setSingleStep(60)
        self.auto_save_interval.setSuffix(" secondes")
        autosave_layout.addRow("Intervalle :", self.auto_save_interval)
        
        self.backup_check = QCheckBox("Créer des sauvegardes de sécurité")
        autosave_layout.addRow("", self.backup_check)
        
        autosave_group.setLayout(autosave_layout)
        layout.addWidget(autosave_group)
        
        # ========== GROUPE 4 : Projets Récents ==========
        recent_group = QGroupBox("🕐 Projets Récents")
        recent_layout = QFormLayout()
        
        self.max_recent_spin = QSpinBox()
        self.max_recent_spin.setMinimum(0)
        self.max_recent_spin.setMaximum(20)
        recent_layout.addRow("Nombre max de projets récents :", self.max_recent_spin)
        
        clear_recent_btn = QPushButton("🗑️ Effacer l'historique")
        clear_recent_btn.clicked.connect(self._clear_recent_projects)
        recent_layout.addRow("", clear_recent_btn)
        
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        # Boutons OK/Annuler
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def _browse_project_path(self):
        """Sélectionne le dossier par défaut"""
        current = self.project_path_input.text()
        start_dir = current if current else str(Path.home())
        
        directory = QFileDialog.getExistingDirectory(
            self, "Sélectionner le dossier par défaut", start_dir
        )
        
        if directory:
            self.project_path_input.setText(directory)
    
    def _update_unit_preview(self):
        """Met à jour l'aperçu des unités"""
        unit_system = self.unit_system_combo.currentData()
        
        # Créer une préférence temporaire pour obtenir les labels
        temp_prefs = ProjectPreferences(unit_system=unit_system)
        labels = temp_prefs.get_unit_labels()
        
        preview_text = (
            f"Longueur : {labels['length']}\n"
            f"Masse : {labels['mass']}\n"
            f"Temps : {labels['time']}\n"
            f"Force : {labels['force']}\n"
            f"Pression : {labels['pressure']}\n"
            f"Énergie : {labels['energy']}\n"
            f"Densité : {labels['density']}\n"
            f"Vitesse : {labels['velocity']}\n"
            f"Accélération : {labels['acceleration']}"
        )
        
        self.units_preview.setText(preview_text)
    
    def _clear_recent_projects(self):
        """Efface l'historique des projets récents"""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, "Confirmer",
            "Effacer l'historique des projets récents ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.preferences.recent_projects.clear()
            QMessageBox.information(self, "Historique effacé", "L'historique a été effacé.")
    
    def _load_preferences(self):
        """Charge les préférences dans le formulaire"""
        # Chemin
        if self.preferences.default_project_path:
            self.project_path_input.setText(str(self.preferences.default_project_path))
        
        # Unités
        for i in range(self.unit_system_combo.count()):
            if self.unit_system_combo.itemData(i) == self.preferences.unit_system:
                self.unit_system_combo.setCurrentIndex(i)
                break
        
        # Sauvegarde auto
        self.auto_save_check.setChecked(self.preferences.auto_save)
        self.auto_save_interval.setValue(self.preferences.auto_save_interval)
        self.backup_check.setChecked(self.preferences.backup_enabled)
        
        # Projets récents
        self.max_recent_spin.setValue(self.preferences.max_recent_projects)
        
        # Mise à jour de l'aperçu
        self._update_unit_preview()
    
    def get_preferences(self) -> ProjectPreferences:
        """Retourne les préférences depuis le formulaire"""
        # Chemin
        path_text = self.project_path_input.text().strip()
        default_path = Path(path_text) if path_text else None
        
        # Mettre à jour les préférences
        self.preferences.default_project_path = default_path
        self.preferences.unit_system = self.unit_system_combo.currentData()
        self.preferences.auto_save = self.auto_save_check.isChecked()
        self.preferences.auto_save_interval = self.auto_save_interval.value()
        self.preferences.backup_enabled = self.backup_check.isChecked()
        self.preferences.max_recent_projects = self.max_recent_spin.value()
        
        return self.preferences