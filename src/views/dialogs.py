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
    QGroupBox, QFileDialog, QSpinBox, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any
from pathlib import Path
from typing import Optional
from ..core.models import Material, MaterialType, ProjectPreferences, UnitSystem


class DynamicVarsDialog(QDialog):
    """Dialogue pour gérer les variables dynamiques"""
    
    def __init__(self, current_vars: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Variables dynamiques")
        self.resize(500, 400)
        self.current_vars = current_vars.copy()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        # Tableau des variables
        self.table = QTreeWidget()
        self.table.setHeaderLabels(["Nom", "Valeur"])
        self.table.setColumnWidth(0, 150)
        self._populate_table()
        layout.addWidget(self.table)
        
        # Boutons ajouter/supprimer
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Ajouter")
        add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton("Supprimer")
        del_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(del_btn)
        
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
    
    def _populate_table(self):
        """Remplit le tableau"""
        self.table.clear()
        for name, value in self.current_vars.items():
            item = QTreeWidgetItem([name, str(value)])
            self.table.addTopLevelItem(item)
    
    def _on_add(self):
        """Ajoute une variable"""
        name, ok1 = QInputDialog.getText(
            self, "Nom de variable",
            "Entrez le nom (ex: thickness, offset) :"
        )
        
        if not ok1 or not name.strip():
            return
        
        value, ok2 = QInputDialog.getText(
            self, "Valeur",
            f"Valeur pour {name} :"
        )
        
        if not ok2:
            return
        
        # Convertir en nombre si possible
        try:
            if '.' in value or 'e' in value.lower():
                val = float(value)
            else:
                val = int(value)
        except ValueError:
            val = value  # Garder comme string
        
        self.current_vars[name] = val
        self._populate_table()
    
    def _on_delete(self):
        """Supprime la variable sélectionnée"""
        selected = self.table.currentItem()
        if selected:
            name = selected.text(0)
            del self.current_vars[name]
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