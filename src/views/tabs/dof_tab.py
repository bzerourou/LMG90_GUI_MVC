# ============================================================================
# Onglet DOF (Degrés de liberté)
# ============================================================================
"""
Onglet pour appliquer des conditions aux limites.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import DOFOperation
from ...controllers.project_controller import ProjectController
from ...utils.safe_eval import SafeEvaluator


class DOFTab(QWidget):
    """Onglet opérations DOF"""
    
    operation_applied = pyqtSignal()
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Sélection avatar/groupe
        self.target_combo = QComboBox()
        form.addRow("Cible :", self.target_combo)
        
        # Action
        self.action_combo = QComboBox()
        self.action_combo.addItems([
            "translate", "rotate", "imposeDrivenDof", "imposeInitValue"
        ])
        form.addRow("Action :", self.action_combo)
        
        # Paramètres
        self.params_input = QLineEdit("dx=0.0, dy=2.0")
        form.addRow("Paramètres :", self.params_input)
        
        layout.addLayout(form)
        
        # Bouton appliquer
        apply_btn = QPushButton("Appliquer")
        apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(apply_btn)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.action_combo.currentTextChanged.connect(self._on_action_changed)
    
    def _on_action_changed(self, action):
        """Suggère des paramètres selon l'action"""
        suggestions = {
            "translate": "dx=0.0, dy=2.0",
            "rotate": "psi=3.14159/2.0, center=[0.0, 0.0]",
            "imposeDrivenDof": "component=[1,2,3], dofty='vlocy'",
            "imposeInitValue": "component=1, value=3.0"
        }
        self.params_input.setText(suggestions.get(action, ""))
    
    def _on_apply(self):
        """Applique l'opération"""
        try:
            # Parser la cible
            target_data = self.target_combo.currentData()
            if not target_data:
                raise ValueError("Aucune cible sélectionnée")
            
            target_type, target_value = target_data
            
            # Parser les paramètres
            evaluator = SafeEvaluator()
            params = evaluator.eval_dict(self.params_input.text())
            
            # Créer l'opération
            operation = DOFOperation(
                operation_type=self.action_combo.currentText(),
                target_type=target_type,
                target_value=target_value,
                parameters=params
            )
            
            # Appliquer via le contrôleur
            self.controller.add_dof_operation(operation)
            
            # Succès
            self.operation_applied.emit()
            
            target_name = f"Avatar #{target_value}" if target_type == 'avatar' else f"Groupe: {target_value}"
            QMessageBox.information(
                self, "Succès",
                f"Action '{operation.operation_type}' appliquée à {target_name}"
            )
            
        except ValueError as e:
            QMessageBox.critical(self, "Erreur", f"Paramètres invalides :\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Application échouée :\n{e}")
    
    def refresh(self):
        """Rafraîchit le combo des cibles"""
        self.target_combo.clear()
        
        # Avatars individuels
        avatars = self.controller.get_avatars(include_generated=True)
        for i, avatar in enumerate(avatars):
            label = f"Avatar #{i} ({avatar.color})"
            self.target_combo.addItem(label, ('avatar', i))
        
        # Groupes
        for group_name, indices in self.controller.state.avatar_groups.items():
            label = f"GROUPE: {group_name} ({len(indices)} avatars)"
            self.target_combo.addItem(label, ('group', group_name))

