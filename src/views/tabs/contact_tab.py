# ============================================================================
# Onglet Lois de Contact
# ============================================================================
"""
Onglet pour créer des lois de contact.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import ContactLaw, ContactLawType
from ...core.validators import ValidationError
from ...controllers.project_controller import ProjectController


class ContactTab(QWidget):
    """Onglet lois de contact"""
    
    law_created = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Nom
        self.name_input = QLineEdit("iqsc0")
        form.addRow("Nom :", self.name_input)
        
        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems([lt.value for lt in ContactLawType])
        form.addRow("Type :", self.type_combo)
        
        # Propriétés (friction, etc.)
        self.props_input = QLineEdit("fric=0.3")
        form.addRow("Propriétés :", self.props_input)
        
        layout.addLayout(form)
        
        # Bouton créer
        create_btn = QPushButton("Créer Loi de Contact")
        create_btn.clicked.connect(self._on_create)
        layout.addWidget(create_btn)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
    
    def _on_type_changed(self, law_type):
        """Suggère des propriétés selon le type"""
        if law_type in ["IQS_CLB", "IQS_CLB_g0"]:
            self.props_input.setText("fric=0.3")
        else:
            self.props_input.setText("")
    
    def _on_create(self):
        """Crée la loi de contact"""
        try:
            # Parser les propriétés
            from ...utils.safe_eval import SafeEvaluator
            evaluator = SafeEvaluator()
            props = evaluator.eval_dict(self.props_input.text())
            
            # Extraire friction si présente
            friction = props.pop('fric', None)
            
            # Créer la loi
            law = ContactLaw(
                name=self.name_input.text().strip(),
                law_type=ContactLawType(self.type_combo.currentText()),
                friction=friction,
                properties=props
            )
            
            # Ajouter via le contrôleur
            self.controller.add_contact_law(law)
            
            # Succès
            self.law_created.emit()
            QMessageBox.information(self, "Succès", f"Loi '{law.name}' créée")
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def refresh(self):
        """Rafraîchit l'onglet"""
        pass
