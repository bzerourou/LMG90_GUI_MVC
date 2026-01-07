# ============================================================================
# Onglet Tables de Visibilité
# ============================================================================
"""
Onglet pour créer des tables de visibilité (règles de détection).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import VisibilityRule
from ...controllers.project_controller import ProjectController


class VisibilityTab(QWidget):
    """Onglet visibilité"""
    
    rule_created = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._setup_ui()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Candidat
        form.addRow("<b>Candidat</b>", QWidget())
        
        self.candidate_body_combo = QComboBox()
        self.candidate_body_combo.addItems(["RBDY2", "RBDY3"])
        form.addRow("Corps :", self.candidate_body_combo)
        
        self.candidate_contactor_combo = QComboBox()
        self.candidate_contactor_combo.addItems(["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"])
        form.addRow("Contacteur :", self.candidate_contactor_combo)
        
        self.candidate_color_input = QLineEdit("BLUEx")
        form.addRow("Couleur :", self.candidate_color_input)
        
        # Antagoniste
        form.addRow("<b>Antagoniste</b>", QWidget())
        
        self.antagonist_body_combo = QComboBox()
        self.antagonist_body_combo.addItems(["RBDY2", "RBDY3"])
        form.addRow("Corps :", self.antagonist_body_combo)
        
        self.antagonist_contactor_combo = QComboBox()
        self.antagonist_contactor_combo.addItems(["DISKx", "xKSID", "JONCx", "POLYG", "PT2Dx"])
        form.addRow("Contacteur :", self.antagonist_contactor_combo)
        
        self.antagonist_color_input = QLineEdit("VERTx")
        form.addRow("Couleur :", self.antagonist_color_input)
        
        # Loi de contact
        self.behavior_combo = QComboBox()
        form.addRow("Loi de contact :", self.behavior_combo)
        
        # Alert
        self.alert_input = QLineEdit("0.1")
        form.addRow("Alert (distance) :", self.alert_input)
        
        layout.addLayout(form)
        
        # Bouton créer
        create_btn = QPushButton("Créer Règle de Visibilité")
        edit_btn = QPushButton("Modifier")
        delete_btn = QPushButton("Supprimer")
        create_btn.clicked.connect(self._on_create)
        edit_btn.clicked.connect(self._on_edit)
        delete_btn.clicked.connect(self._on_delete)
        button_layout = QHBoxLayout()
        button_layout.addWidget(create_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _on_create(self):
        """Crée la règle de visibilité"""
        try:
            # Créer la règle
            rule = VisibilityRule(
                candidate_body=self.candidate_body_combo.currentText(),
                candidate_contactor=self.candidate_contactor_combo.currentText(),
                candidate_color=self.candidate_color_input.text().strip(),
                antagonist_body=self.antagonist_body_combo.currentText(),
                antagonist_contactor=self.antagonist_contactor_combo.currentText(),
                antagonist_color=self.antagonist_color_input.text().strip(),
                behavior_name=self.behavior_combo.currentText(),
                alert=float(self.alert_input.text())
            )
            
            # Ajouter via le contrôleur
            self.controller.add_visibility_rule(rule)
            
            # Succès
            self.rule_created.emit()
            QMessageBox.information(self, "Succès", "Règle de visibilité créée")
            
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def _on_edit(self):
        pass    

    def _on_delete(self):
        pass

    
    def refresh(self):
        """Rafraîchit le combo des lois"""
        self.behavior_combo.clear()
        laws = self.controller.get_contact_laws()
        self.behavior_combo.addItems([law.name for law in laws])
