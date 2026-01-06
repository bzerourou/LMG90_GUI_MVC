# ============================================================================
# Onglet Post-Processing
# ============================================================================
"""
Onglet pour configurer les commandes de post-traitement.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem, QGroupBox, QLabel
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import PostProCommand
from ...controllers.project_controller import ProjectController


class PostProTab(QWidget):
    """Onglet post-traitement"""
    
    command_added = pyqtSignal()
    
    # Commandes disponibles
    COMMANDS = [
        "SOLVER INFORMATIONS", "Dep EVOLUTION", "Fint EVOLUTION",
        "KINETIC ENERGY", "DISSIPATED ENERGY", "COORDINATION NUMBER",
        "DISPLAY TENSORS", "DRY CONTACT NATURE", "WET CONTACT NATURE",
        "INTER ANALYSIS", "VISIBILITY STATE", "TORQUE EVOLUTION",
        "VIOLATION EVOLUTION", "BODY TRACKING", "NEW RIGID SETS"
    ]
    
    # Commandes nécessitant un rigid_set
    NEEDS_RIGID_SET = ["TORQUE EVOLUTION", "BODY TRACKING", "NEW RIGID SETS"]
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configure l'interface"""
        layout = QVBoxLayout()
        
        # Formulaire
        form_group = QGroupBox("Ajouter une commande")
        form = QFormLayout()
        
        self.name_combo = QComboBox()
        self.name_combo.addItems(self.COMMANDS)
        form.addRow("Commande :", self.name_combo)
        
        self.step_input = QLineEdit("1")
        form.addRow("Step (fréquence) :", self.step_input)
        
        # Sélecteur d'avatar/groupe (masqué par défaut)
        self.target_label = QLabel("Avatar(s) ou groupe(s) :")
        self.target_combo = QComboBox()
        self.target_combo.setEnabled(False)
        form.addRow(self.target_label, self.target_combo)
        
        form_group.setLayout(form)
        layout.addWidget(form_group)
        
        # Bouton ajouter
        add_btn = QPushButton("Ajouter la Commande")
        add_btn.clicked.connect(self._on_add)
        layout.addWidget(add_btn)
        
        # Liste des commandes
        layout.addWidget(QLabel("<b>Commandes actives :</b>"))
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Commande", "Step", "Cible"])
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 80)
        layout.addWidget(self.tree)
        
        # Bouton supprimer
        del_btn = QPushButton("Supprimer la commande sélectionnée")
        del_btn.clicked.connect(self._on_delete)
        layout.addWidget(del_btn)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connecte les signaux"""
        self.name_combo.currentTextChanged.connect(self._on_command_changed)
    
    def _on_command_changed(self, command):
        """Active/désactive le sélecteur selon la commande"""
        needs_target = command in self.NEEDS_RIGID_SET
        
        self.target_label.setVisible(needs_target)
        self.target_combo.setVisible(needs_target)
        self.target_combo.setEnabled(needs_target)
    
    def _on_add(self):
        """Ajoute une commande"""
        try:
            command_name = self.name_combo.currentText()
            step = int(self.step_input.text())
            
            if step <= 0:
                raise ValueError("Step doit être positif")
            
            # Cible si nécessaire
            target_type = None
            target_value = None
            
            if command_name in self.NEEDS_RIGID_SET:
                target_data = self.target_combo.currentData()
                if not target_data:
                    raise ValueError("Sélectionnez une cible pour cette commande")
                target_type, target_value = target_data
            
            # Créer la commande
            command = PostProCommand(
                name=command_name,
                step=step,
                target_type=target_type,
                target_value=target_value
            )
            
            # Ajouter via le contrôleur
            self.controller.add_postpro_command(command)
            
            # Mettre à jour l'arbre
            self._refresh_tree()
            
            # Succès
            self.command_added.emit()
            QMessageBox.information(self, "Succès", "Commande ajoutée")
            
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Ajout échoué :\n{e}")
    
    def _on_delete(self):
        """Supprime la commande sélectionnée"""
        selected = self.tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une commande à supprimer")
            return
        
        index = self.tree.indexOfTopLevelItem(selected[0])
        
        reply = QMessageBox.question(
            self, "Confirmer",
            "Supprimer cette commande ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.remove_postpro_command(index)
            self._refresh_tree()
    
    def _refresh_tree(self):
        """Rafraîchit l'arbre des commandes"""
        self.tree.clear()
        
        for cmd in self.controller.state.postpro_commands:
            target_text = "Global"
            if cmd.target_type == 'avatar':
                target_text = f"Avatar #{cmd.target_value}"
            elif cmd.target_type == 'group':
                indices = self.controller.state.avatar_groups.get(cmd.target_value, [])
                target_text = f"Groupe: {cmd.target_value} ({len(indices)} avatars)"
            
            item = QTreeWidgetItem([cmd.name, str(cmd.step), target_text])
            self.tree.addTopLevelItem(item)
    
    def refresh(self):
        """Rafraîchit le combo des cibles"""
        self.target_combo.clear()
        
        # Avatars
        avatars = self.controller.state.avatars
        for i, avatar in enumerate(avatars):
            from ...core.models import AvatarOrigin
            origin_mark = ""
            if avatar.origin == AvatarOrigin.LOOP:
                origin_mark = " [L]"
            elif avatar.origin == AvatarOrigin.GRANULO:
                origin_mark = " [G]"
            label = f"Avatar #{i} - {avatar.avatar_type.value} {origin_mark}"
            self.target_combo.addItem(label, ('avatar', i))
        
        # Groupes
        for group_name, indices in self.controller.state.avatar_groups.items():
            label = f"GROUPE: {group_name} ({len(indices)} avatars)"
            self.target_combo.addItem(label, ('group', group_name))
        
        # Rafraîchir l'arbre
        self._refresh_tree()
