# ============================================================================
# Dialogues personnalisés
# ============================================================================
"""
Dialogues personnalisés de l'application.
"""
from PyQt6.QtWidgets import (
    QWidget,QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QDialogButtonBox, 
    QTabWidget, QLabel, QLineEdit, QFormLayout,
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
    """Dialogue de préférences — onglets verticaux à droite."""

    def __init__(self, preferences: ProjectPreferences, parent=None):
        super().__init__(parent)
        self.preferences = preferences
        self.setWindowTitle("⚙️ Préférences")
        self.resize(780, 560)
        self._setup_ui()
        self._load_preferences()

    # ─────────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # ── QTabWidget avec onglets à gauche (West = vertical) ────────────────
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.West)
        self._tabs.setDocumentMode(False)
        self._tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 140px;
                min-height: 36px;
                padding: 6px 12px;
                text-align: left;
                font-size: 10pt;
            }
            QTabBar::tab:selected {
                font-weight: bold;
            }
        """)

        self._tabs.addTab(self._build_paths_tab(),    "📁  Chemins")
        self._tabs.addTab(self._build_units_tab(),    "📏  Unités")
        self._tabs.addTab(self._build_save_tab(),     "💾  Sauvegarde")
        self._tabs.addTab(self._build_perf_tab(),     "⚡  Performances")

        root.addWidget(self._tabs, stretch=1)

        # ── Boutons OK / Annuler ──────────────────────────────────────────────
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

    # ── Onglet 1 : Chemins ────────────────────────────────────────────────────
    def _build_paths_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("<b>📁 Chemins et Fichiers</b>"))

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        path_row = QHBoxLayout()
        self.project_path_input = QLineEdit()
        self.project_path_input.setReadOnly(True)
        self.project_path_input.setPlaceholderText("Aucun chemin par défaut")
        path_row.addWidget(self.project_path_input)

        browse_btn = QPushButton("📂 Parcourir…")
        browse_btn.clicked.connect(self._browse_project_path)
        path_row.addWidget(browse_btn)

        clear_btn = QPushButton("✖")
        clear_btn.setMaximumWidth(36)
        clear_btn.setToolTip("Effacer")
        clear_btn.clicked.connect(lambda: self.project_path_input.clear())
        path_row.addWidget(clear_btn)

        form.addRow("Dossier par défaut :", path_row)
        layout.addLayout(form)

        info = QLabel(
            "💡 Les nouveaux projets seront ouverts dans ce dossier par défaut."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 9pt; padding: 4px;")
        layout.addWidget(info)
        layout.addStretch()
        return w

    # ── Onglet 2 : Unités ─────────────────────────────────────────────────────
    def _build_units_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("<b>📏 Système d'Unités</b>"))

        form = QFormLayout()
        self.unit_system_combo = QComboBox()
        self.unit_system_combo.addItem(
            "SI — Système International  (m, kg, s, N, Pa)", UnitSystem.SI)
        self.unit_system_combo.addItem(
            "CGS — Centimètre-Gramme-Seconde  (cm, g, s)",   UnitSystem.CGS)
        self.unit_system_combo.currentIndexChanged.connect(self._update_unit_preview)
        form.addRow("Système :", self.unit_system_combo)
        layout.addLayout(form)

        layout.addWidget(QLabel("<b>Aperçu des unités :</b>"))
        self.units_preview = QLabel()
        self.units_preview.setWordWrap(True)
        self.units_preview.setStyleSheet(
            "background-color: #f0f0f0; padding: 10px; "
            "border-radius: 5px; font-family: monospace;"
        )
        layout.addWidget(self.units_preview)
        layout.addStretch()
        return w

    # ── Onglet 3 : Sauvegarde + Projets récents ───────────────────────────────
    def _build_save_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Sauvegarde automatique
        auto_group = QGroupBox("💾 Sauvegarde automatique")
        auto_form  = QFormLayout()

        self.auto_save_check = QCheckBox("Activer la sauvegarde automatique")
        auto_form.addRow("", self.auto_save_check)

        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setMinimum(60)
        self.auto_save_interval.setMaximum(3600)
        self.auto_save_interval.setSingleStep(60)
        self.auto_save_interval.setSuffix(" secondes")
        auto_form.addRow("Intervalle :", self.auto_save_interval)

        self.backup_check = QCheckBox("Créer des sauvegardes de sécurité (.bak)")
        auto_form.addRow("", self.backup_check)

        auto_group.setLayout(auto_form)
        layout.addWidget(auto_group)

        # Projets récents
        recent_group = QGroupBox("🕐 Projets récents")
        recent_form  = QFormLayout()

        self.max_recent_spin = QSpinBox()
        self.max_recent_spin.setMinimum(0)
        self.max_recent_spin.setMaximum(20)
        recent_form.addRow("Nombre maximum :", self.max_recent_spin)

        clear_recent_btn = QPushButton("🗑️ Effacer l'historique")
        clear_recent_btn.clicked.connect(self._clear_recent_projects)
        recent_form.addRow("", clear_recent_btn)

        recent_group.setLayout(recent_form)
        layout.addWidget(recent_group)

        layout.addStretch()
        return w

    # ── Onglet 4 : Performances / Affichage avatars ───────────────────────────
    def _build_perf_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("<b>⚡ Performances — Affichage des avatars</b>"))

        # Granulo
        granulo_group = QGroupBox("🎲 Granulométrie")
        granulo_layout = QVBoxLayout()

        self.show_granulo_check = QCheckBox(
            "Afficher les avatars granulométriques individuellement"
        )
        self.show_granulo_check.setToolTip(
            "Coché : chaque avatar apparaît dans l'arbre, les listes DOF et PostPro.\n"
            "Décoché (recommandé >500 particules) : seuls les groupes sont visibles."
        )
        granulo_layout.addWidget(self.show_granulo_check)

        self.create_pylmgc_check = QCheckBox(
            "Créer les objets pylmgc lors de la génération massive  (plus lent)"
        )
        self.create_pylmgc_check.setToolTip(
            "Décoché : génération massive accélérée — objets pylmgc créés à la demande."
        )
        granulo_layout.addWidget(self.create_pylmgc_check)

        info = QLabel(
            "ℹ️  Quand l'affichage individuel est désactivé :\n"
            "  • Les avatars n'apparaissent pas un par un dans l'arbre\n"
            "  • Les listes DOF et Post-Pro ne montrent que les groupes"
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "color: #555; font-size: 9pt; padding: 6px; "
            "background-color: #f5f5f5; border-radius: 4px;"
        )
        granulo_layout.addWidget(info)
        granulo_group.setLayout(granulo_layout)
        layout.addWidget(granulo_group)

        # Visualisation 3D
        viewer_group = QGroupBox("🎨 Visualisation 3D")
        viewer_layout = QVBoxLayout()

        self.auto_refresh_viewer_check = QCheckBox(
            "Rafraîchir automatiquement la vue 3D après chaque modification"
        )
        self.auto_refresh_viewer_check.setToolTip(
            "Décocher si la vue 3D ralentit l'interface (nombreux avatars)."
        )
        viewer_layout.addWidget(self.auto_refresh_viewer_check)

        viewer_group.setLayout(viewer_layout)
        layout.addWidget(viewer_group)

        layout.addStretch()
        return w

    # ── Méthodes utilitaires ──────────────────────────────────────────────────
    def _browse_project_path(self):
        current   = self.project_path_input.text()
        start_dir = current if current else str(Path.home())
        directory = QFileDialog.getExistingDirectory(
            self, "Sélectionner le dossier par défaut", start_dir
        )
        if directory:
            self.project_path_input.setText(directory)

    def _update_unit_preview(self):
        unit_system = self.unit_system_combo.currentData()
        temp_prefs  = ProjectPreferences(unit_system=unit_system)
        labels      = temp_prefs.get_unit_labels()
        self.units_preview.setText(
            f"Longueur      : {labels['length']}\n"
            f"Masse         : {labels['mass']}\n"
            f"Temps         : {labels['time']}\n"
            f"Force         : {labels['force']}\n"
            f"Pression      : {labels['pressure']}\n"
            f"Énergie       : {labels['energy']}\n"
            f"Densité       : {labels['density']}\n"
            f"Vitesse       : {labels['velocity']}\n"
            f"Accélération  : {labels['acceleration']}"
        )

    def _clear_recent_projects(self):
        reply = QMessageBox.question(
            self, "Confirmer",
            "Effacer l'historique des projets récents ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.preferences.recent_projects.clear()
            QMessageBox.information(self, "Historique effacé",
                                    "L'historique a été effacé.")

    def _load_preferences(self):
        # Chemin
        if self.preferences.default_project_path:
            self.project_path_input.setText(str(self.preferences.default_project_path))

        # Unités
        for i in range(self.unit_system_combo.count()):
            if self.unit_system_combo.itemData(i) == self.preferences.unit_system:
                self.unit_system_combo.setCurrentIndex(i)
                break
        self._update_unit_preview()

        # Sauvegarde
        self.auto_save_check.setChecked(self.preferences.auto_save)
        self.auto_save_interval.setValue(self.preferences.auto_save_interval)
        self.backup_check.setChecked(self.preferences.backup_enabled)

        # Récents
        self.max_recent_spin.setValue(self.preferences.max_recent_projects)

        # Performances
        self.show_granulo_check.setChecked(
            getattr(self.preferences, 'show_granulo_individually', True)
        )
        self.create_pylmgc_check.setChecked(
            getattr(self.preferences, 'create_pylmgc_on_generate', True)
        )
        self.auto_refresh_viewer_check.setChecked(
            getattr(self.preferences, 'auto_refresh_viewer', True)
        )

    def get_preferences(self) -> ProjectPreferences:
        path_text = self.project_path_input.text().strip()
        self.preferences.default_project_path = Path(path_text) if path_text else None
        self.preferences.unit_system          = self.unit_system_combo.currentData()
        self.preferences.auto_save            = self.auto_save_check.isChecked()
        self.preferences.auto_save_interval   = self.auto_save_interval.value()
        self.preferences.backup_enabled       = self.backup_check.isChecked()
        self.preferences.max_recent_projects  = self.max_recent_spin.value()

        self.preferences.show_granulo_individually  = self.show_granulo_check.isChecked()
        self.preferences.create_pylmgc_on_generate  = self.create_pylmgc_check.isChecked()
        self.preferences.auto_refresh_viewer        = self.auto_refresh_viewer_check.isChecked()

        return self.preferences
class DuplicateDialog(QDialog):
    """
    Dialogue de duplication d'un avatar ou d'un groupe d'avatars.

    Permet à l'utilisateur de choisir :
      - Le nombre de copies à créer
      - Le décalage (offset) X / Y / Z appliqué à chaque copie
      - Un nom de groupe destination (optionnel)

    Le mode ('avatar' ou 'group') est passé en paramètre pour adapter
    le titre et le libellé informatif.
    """

    def __init__(self, source_label: str, dimension: int,
                 mode: str = 'avatar', parent=None):
        """
        Args:
            source_label: Texte décrivant la source (affiché dans le dialogue).
            dimension:    2 (2D) ou 3 (3D) — détermine si le champ Z est visible.
            mode:         'avatar' ou 'group'.
            parent:       Widget parent Qt.
        """
        super().__init__(parent)
        self._dimension = dimension
        self._mode      = mode

        title = "📋 Dupliquer un avatar" if mode == 'avatar' \
                else "📋 Dupliquer un groupe"
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self._setup_ui(source_label)

    # ── Construction de l'interface ───────────────────────────────────────────
    def _setup_ui(self, source_label: str):
        layout = QVBoxLayout(self)

        # Bandeau d'information
        info = QLabel(
            f"<b>Source :</b> {source_label}<br>"
            "Chaque copie <i>k</i> est positionnée à :<br>"
            "&nbsp;&nbsp;&nbsp;<code>center + k × offset</code>"
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "background-color: #e8f5e9; padding: 10px; border-radius: 5px;"
        )
        layout.addWidget(info)

        # ── Nombre de copies ─────────────────────────────────────────────────
        copies_group = QGroupBox("Nombre de copies")
        copies_form  = QFormLayout()

        self._n_spin = QSpinBox()
        self._n_spin.setRange(1, 10000)
        self._n_spin.setValue(1)
        self._n_spin.setToolTip("Nombre de séries de copies à créer.")
        copies_form.addRow("Nombre de copies :", self._n_spin)

        copies_group.setLayout(copies_form)
        layout.addWidget(copies_group)

        # ── Offset ───────────────────────────────────────────────────────────
        offset_group = QGroupBox("Décalage par copie (offset)")
        offset_form  = QFormLayout()

        from PyQt6.QtWidgets import QDoubleSpinBox as _DSB

        def _make_dspin(val=0.0):
            w = _DSB()
            w.setRange(-1e6, 1e6)
            w.setDecimals(6)
            w.setSingleStep(0.01)
            w.setValue(val)
            w.setSuffix(" m")
            return w

        self._dx = _make_dspin()
        self._dy = _make_dspin()
        self._dz = _make_dspin()

        offset_form.addRow("Offset X :", self._dx)
        offset_form.addRow("Offset Y :", self._dy)

        self._dz_label = QLabel("Offset Z :")
        offset_form.addRow(self._dz_label, self._dz)

        # Masquer Z en 2D
        self._dz_label.setVisible(self._dimension == 3)
        self._dz.setVisible(self._dimension == 3)

        offset_group.setLayout(offset_form)
        layout.addWidget(offset_group)

        # ── Groupe destination ────────────────────────────────────────────────
        grp_group = QGroupBox("Groupe destination (optionnel)")
        grp_form  = QFormLayout()

        self._group_check = QCheckBox("Stocker les copies dans un groupe")
        self._group_check.setChecked(True)
        self._group_check.toggled.connect(self._on_group_toggled)
        grp_form.addRow(self._group_check)

        self._group_input = QLineEdit()
        self._group_input.setPlaceholderText("Ex: mur_copie, pile_2…")
        grp_form.addRow("Nom du groupe :", self._group_input)

        grp_group.setLayout(grp_form)
        layout.addWidget(grp_group)

        # ── Aperçu ────────────────────────────────────────────────────────────
        self._preview_label = QLabel()
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet(
            "color: #555; font-size: 9pt; padding: 4px;"
        )
        layout.addWidget(self._preview_label)

        self._n_spin.valueChanged.connect(self._update_preview)
        self._dx.valueChanged.connect(self._update_preview)
        self._dy.valueChanged.connect(self._update_preview)
        self._dz.valueChanged.connect(self._update_preview)
        self._update_preview()

        # ── Boutons OK / Annuler ──────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── Slots ─────────────────────────────────────────────────────────────────
    def _on_group_toggled(self, checked: bool):
        self._group_input.setEnabled(checked)

    def _update_preview(self):
        n  = self._n_spin.value()
        dx = self._dx.value()
        dy = self._dy.value()
        dz = self._dz.value() if self._dimension == 3 else 0.0

        if self._dimension == 3:
            off_str = f"({dx:.4g}, {dy:.4g}, {dz:.4g})"
        else:
            off_str = f"({dx:.4g}, {dy:.4g})"

        noun = "avatar" if self._mode == 'avatar' else "groupe"
        self._preview_label.setText(
            f"ℹ️  {n} copie(s) du {noun} avec offset {off_str} par copie."
        )

    def _on_accept(self):
        # Vérifier qu'au moins un axe a un offset non nul
        dx = self._dx.value()
        dy = self._dy.value()
        dz = self._dz.value() if self._dimension == 3 else 0.0

        if dx == 0.0 and dy == 0.0 and dz == 0.0:
            reply = QMessageBox.question(
                self, "Offset nul",
                "L'offset est nul sur tous les axes : les copies seront\n"
                "superposées à la source. Continuer quand même ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if self._group_check.isChecked() and not self._group_input.text().strip():
            QMessageBox.warning(
                self, "Nom requis",
                "Entrez un nom de groupe ou décochez l'option."
            )
            return

        self.accept()

    # ── Accesseurs (appelés par tree_view après accept()) ─────────────────────
    def get_n_copies(self) -> int:
        """Retourne le nombre de copies demandé."""
        return self._n_spin.value()

    def get_offset(self) -> list:
        """Retourne l'offset sous forme [dx, dy] ou [dx, dy, dz]."""
        if self._dimension == 3:
            return [self._dx.value(), self._dy.value(), self._dz.value()]
        return [self._dx.value(), self._dy.value()]

    def get_group_name(self) -> str:
        """Retourne le nom du groupe destination, ou '' si non demandé."""
        if self._group_check.isChecked():
            return self._group_input.text().strip()
        return ""