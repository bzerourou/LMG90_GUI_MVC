# ============================================================================
# Onglet Lois de Contact
# ============================================================================
"""
Onglet pour créer des lois de contact.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QLabel, QHBoxLayout
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
        
        # Friction (séparé pour plus de clarté)
        self.friction_input = QLineEdit("0.3")
        self.friction_label = QLabel("Friction (µ) :")
        form.addRow(self.friction_label, self.friction_input)
        
        # Propriétés supplémentaires
        self.props_input = QLineEdit()
        self.props_input.setPlaceholderText("Autres propriétés (ex: prop1=val1, prop2=val2)")
        form.addRow("Propriétés :", self.props_input)
        
        # Aide
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        form.addRow("", self.help_label)
        
        layout.addLayout(form)
        
        # Bouton créer
        create_btn = QPushButton("Créer Loi de Contact")
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
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
    
    def _on_type_changed(self, law_type):
        """Suggère des propriétés selon le type"""
        help_texts = {
            "IQS_CLB": "Loi de contact Signorini-Coulomb avec friction. Friction requise.",
            "IQS_CLB_g0": "Loi de contact Signorini-Coulomb avec gap initial. Friction requise.",
            "COUPLED_DOF": "Couplage de degrés de liberté. Pas de friction."
        }
        
        if law_type in ["IQS_CLB", "IQS_CLB_g0"]:
            self.friction_label.setVisible(True)
            self.friction_input.setVisible(True)
            self.friction_input.setEnabled(True)
            if not self.friction_input.text():
                self.friction_input.setText("0.3")
        else:
            self.friction_label.setVisible(True)
            self.friction_input.setVisible(True)
            self.friction_input.setEnabled(False)
            self.friction_input.setText("")
        
        self.help_label.setText(f"ℹ️ {help_texts.get(law_type, '')}")
    
    def _on_create(self):
        """Crée la loi de contact"""
        try:
            # Récupérer le nom
            name = self.name_input.text().strip()
            if not name:
                raise ValueError("Le nom ne peut pas être vide")
            
            # Récupérer le type
            law_type = ContactLawType(self.type_combo.currentText())
            
            # Récupérer la friction
            friction = None
            friction_text = self.friction_input.text().strip()
            if friction_text:
                try:
                    friction = float(friction_text)
                    if friction < 0:
                        raise ValueError("La friction doit être positive ou nulle")
                except ValueError as e:
                    if "could not convert" in str(e):
                        raise ValueError(f"Friction invalide : '{friction_text}' n'est pas un nombre")
                    raise
            
            # Vérifier que friction est fournie si requise
            if law_type in [ContactLawType.IQS_CLB, ContactLawType.IQS_CLB_G0]:
                if friction is None:
                    raise ValueError(f"La friction est requise pour {law_type.value}")
            
            # Parser les propriétés supplémentaires
            props_text = self.props_input.text().strip()
            props = self._parse_properties(props_text) if props_text else {}
            
            # Créer la loi
            law = ContactLaw(
                name=name,
                law_type=law_type,
                friction=friction,
                properties=props
            )
            
            # Ajouter via le contrôleur
            self.controller.add_contact_law(law)
            
            # Succès
            self.law_created.emit()
            QMessageBox.information(self, "Succès", f"✅ Loi '{law.name}' créée")
            
            # Réinitialiser le formulaire
            self.name_input.clear()
            self.friction_input.setText("0.3")
            self.props_input.clear()
            
        except ValidationError as e:
            QMessageBox.warning(self, "Validation", str(e))
        except ValueError as e:
            QMessageBox.critical(self, "Erreur de Valeur", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
    
    def _on_edit(self):
        pass

    def _on_delete(self):
        pass

    
    def _parse_properties(self, text: str) -> dict:
        """
        Parse les propriétés de contact de manière sécurisée.
        
        Format accepté : "key1=value1, key2=value2"
        Valeurs acceptées : nombres (int/float) ou chaînes
        
        Args:
            text: Chaîne de propriétés
        
        Returns:
            Dictionnaire de propriétés
        
        Raises:
            ValueError: Si format invalide
        
        Example:
            >>> _parse_properties("prop1=1.5, prop2=test")
            {'prop1': 1.5, 'prop2': 'test'}
        """
        if not text.strip():
            return {}
        
        props = {}
        
        # Séparer par virgules
        for pair in text.split(','):
            pair = pair.strip()
            
            if not pair:
                continue
            
            if '=' not in pair:
                raise ValueError(f"Format invalide : '{pair}' (attendu 'clé=valeur')")
            
            key, value = pair.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            if not key:
                raise ValueError(f"Clé vide dans : '{pair}'")
            
            if not value:
                raise ValueError(f"Valeur vide pour la clé '{key}'")
            
            # Essayer de convertir en nombre
            try:
                if '.' in value or 'e' in value.lower():
                    props[key] = float(value)
                else:
                    props[key] = int(value)
            except ValueError:
                # Garder comme string si ce n'est pas un nombre
                props[key] = value
        
        return props
    
    def refresh(self):
        """Rafraîchit l'onglet"""
        # Trigger l'affichage de l'aide
        self._on_type_changed(self.type_combo.currentText())