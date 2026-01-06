# ============================================================================
# Dialogues personnalisés
# ============================================================================
"""
Dialogues personnalisés de l'application.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QDialogButtonBox, 
    QInputDialog, QLabel
)
from PyQt6.QtCore import Qt
from typing import Dict, Any


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
