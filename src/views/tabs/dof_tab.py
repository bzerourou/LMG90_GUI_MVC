# ============================================================================
# Onglet DOF (Degrés de liberté)
# ============================================================================
"""
Onglet pour appliquer des conditions aux limites.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QLabel, QHBoxLayout
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import DOFOperation
from ...controllers.project_controller import ProjectController


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
        
        # Aide contextuelle
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        form.addRow("", self.help_label)
        
        layout.addLayout(form)
        
        # Bouton appliquer
        apply_btn = QPushButton("Appliquer DOF")
        edit_btn = QPushButton("Modifier")
        delete_btn = QPushButton("Supprimer")
        apply_btn.clicked.connect(self._on_apply)
        edit_btn.clicked.connect(self._on_edit)
        delete_btn.clicked.connect(self._on_delete)
        button_layout = QHBoxLayout()
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.action_combo.currentTextChanged.connect(self._on_action_changed)
    
    def _on_action_changed(self, action):
        """Suggère des paramètres selon l'action"""
        suggestions = {
            "translate": {
                "params": "dx=0.0, dy=2.0",
                "help": "Déplace l'avatar. dx/dy = déplacement en X/Y (ou dz en 3D)"
            },
            "rotate": {
                "params": "psi=3.14159, center=[0.0, 0.0]",
                "help": "Rotation. psi = angle en radians, center = centre de rotation [x,y]"
            },
            "imposeDrivenDof": {
                "params": "component=[1,2,3], dofty=vlocy",
                "help": "Impose un DDL piloté. component = liste de composantes, dofty = type (vlocy, accly, etc.)"
            },
            "imposeInitValue": {
                "params": "component=1, value=3.0",
                "help": "Impose une valeur initiale. component = numéro de composante, value = valeur"
            }
        }
        
        info = suggestions.get(action, {"params": "", "help": ""})
        self.params_input.setText(info["params"])
        self.help_label.setText(f"ℹ️ {info['help']}")
    
    def _on_apply(self):
        """Applique l'opération"""
        try:
            # Parser la cible
            target_data = self.target_combo.currentData()
            if not target_data:
                raise ValueError("Aucune cible sélectionnée")
            
            target_type, target_value = target_data
            
            # Parser les paramètres MANUELLEMENT (sans SafeEvaluator)
            params_text = self.params_input.text().strip()
            if not params_text:
                raise ValueError("Paramètres requis")
            
            params = self._parse_dof_params(params_text)
            
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
                f"✅ Action '{operation.operation_type}' appliquée à {target_name}"
            )
            
        except ValueError as e:
            QMessageBox.critical(self, "Erreur de Paramètres", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Application échouée :\n{e}")
    
    def _on_edit(self):
        pass

    def _on_delete(self):
        pass

    def _parse_dof_params(self, params_text: str) -> dict:
        """
        Parse les paramètres DOF de manière sécurisée.
        
        Formats acceptés :
            - "dx=1.0, dy=2.0"
            - "psi=3.14, center=[0, 0]"
            - "component=[1,2,3], dofty=vlocy"
            - "component=1, value=3.0"
        
        Args:
            params_text: Chaîne de paramètres
        
        Returns:
            Dictionnaire de paramètres
        
        Raises:
            ValueError: Si format invalide
        """
        import re
        import ast
        
        params = {}
        
        # Pattern pour capturer : nom = (nombre | liste | string)
        # Capture les listes avec [] et les chaînes sans quotes
        pattern = r'(\w+)\s*=\s*([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?|\[[^\]]*\]|\w+)'
        
        matches = re.findall(pattern, params_text)
        
        if not matches:
            raise ValueError(f"Format de paramètres invalide : '{params_text}'")
        
        for key, value_str in matches:
            key = key.strip()
            value_str = value_str.strip()
            
            # Déterminer le type de valeur
            if value_str.startswith('['):
                # C'est une liste
                try:
                    value = ast.literal_eval(value_str)
                    if not isinstance(value, list):
                        raise ValueError(f"{key} : attendu une liste")
                    params[key] = value
                except Exception as e:
                    raise ValueError(f"Format de liste invalide pour '{key}': {value_str}")
            
            elif self._is_number(value_str):
                # C'est un nombre
                try:
                    if '.' in value_str or 'e' in value_str.lower():
                        params[key] = float(value_str)
                    else:
                        params[key] = int(value_str)
                except ValueError:
                    raise ValueError(f"Valeur numérique invalide pour '{key}': {value_str}")
            
            else:
                # C'est une chaîne (ex: dofty='vlocy')
                params[key] = value_str
        
        return params
    
    def _is_number(self, s: str) -> bool:
        """Vérifie si une chaîne est un nombre"""
        try:
            float(s)
            return True
        except ValueError:
            return False
    
    def refresh(self):
        """Rafraîchit le combo des cibles"""
        self.target_combo.clear()
        
        # Avatars individuels
        avatars = self.controller.state.avatars
        for i, avatar in enumerate(avatars):
            from ...core.models import AvatarOrigin
            origin_mark = ""
            if avatar.origin == AvatarOrigin.LOOP:
                origin_mark = " [Boucle]"
            elif avatar.origin == AvatarOrigin.GRANULO:
                origin_mark = " [Granulo]"
            label = f"Avatar #{i}-{avatar.avatar_type.value} ({avatar.color}){origin_mark}"
            self.target_combo.addItem(label, ('avatar', i))
        
        # Groupes
        for group_name, indices in self.controller.state.avatar_groups.items():
            label = f"🔷 GROUPE: {group_name} ({len(indices)} avatars)"
            self.target_combo.addItem(label, ('group', group_name))
        
        if self.target_combo.count() == 0:
            self.target_combo.addItem("(Aucun avatar)", None)
        # Trigger l'affichage de l'aide
        if hasattr(self, 'action_combo'):
            self._on_action_changed(self.action_combo.currentText())