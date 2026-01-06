# ============================================================================
# Vue arborescente du modèle
# ============================================================================
"""
Vue arborescente du modèle.
Affiche la structure du projet dans un QTreeWidget.
"""
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt

from ..controllers.project_controller import ProjectController
from ..core.models import AvatarOrigin


class ModelTreeView:
    """Gère l'arbre du modèle"""
    
    def __init__(self, controller: ProjectController):
        self.controller = controller
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Élément", "Type", "Détails"])
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(1, 100)
    
    def refresh(self):
        """Rafraîchit l'arbre complet"""
        self.tree.clear()
        
        root = QTreeWidgetItem(["Modèle LMGC90", "", ""])
        self.tree.addTopLevelItem(root)
        
        # Matériaux
        self._add_materials_node(root)
        
        # Modèles
        self._add_models_node(root)
        
        # Avatars
        self._add_avatars_node(root)
        
        # Groupes
        self._add_groups_node(root)
        
        # Lois de contact
        self._add_contact_laws_node(root)
        
        # Visibilité
        self._add_visibility_node(root)
        
        # Opérations DOF
        self._add_operations_node(root)
        
        # Boucles
        self._add_loops_node(root)
        
        # Granulométrie
        self._add_granulo_node(root)
        
        # Post-pro
        self._add_postpro_node(root)
        
        root.setExpanded(True)
    
    def _add_materials_node(self, parent: QTreeWidgetItem):
        """Ajoute le nœud Matériaux"""
        materials = self.controller.get_materials()
        mat_node = QTreeWidgetItem(parent, ["Matériaux", "", f"{len(materials)}"])
        
        for mat in materials:
            item = QTreeWidgetItem([
                f"{mat.name} - {mat.material_type.value}",
                "Matériau",
                f"ρ={mat.density}"
            ])
            mat_node.addChild(item)
        
        if len(materials) <= 10:
            mat_node.setExpanded(True)
    
    def _add_models_node(self, parent: QTreeWidgetItem):
        """Ajoute le nœud Modèles"""
        models = self.controller.get_models()
        mod_node = QTreeWidgetItem(parent, ["Modèles", "", f"{len(models)}"])
        
        for mod in models:
            item = QTreeWidgetItem([
                mod.name,
                "Modèle",
                f"{mod.element} dim={mod.dimension}"
            ])
            mod_node.addChild(item)
        
        if len(models) <= 10:
            mod_node.setExpanded(True)
    
    def _add_avatars_node(self, parent: QTreeWidgetItem):
        """Ajoute le nœud Avatars"""
        avatars = self.controller.get_avatars(include_generated=True)
        av_node = QTreeWidgetItem(parent, ["Avatars", "", f"{len(avatars)}"])
        
        for i, avatar in enumerate(avatars):
            center_str = ', '.join(f"{x:.2f}" for x in avatar.center)
            
            # Marqueur d'origine
            origin_mark = ""
            if avatar.origin == AvatarOrigin.LOOP:
                origin_mark = " [L]"
            elif avatar.origin == AvatarOrigin.GRANULO:
                origin_mark = " [G]"
            
            item = QTreeWidgetItem([
                f"{avatar.avatar_type.value} — {avatar.color} — ({center_str}){origin_mark}",
                "Avatar",
                str(i)
            ])
            av_node.addChild(item)
        
        if len(avatars) <= 20:
            av_node.setExpanded(True)
    
    def _add_groups_node(self, parent: QTreeWidgetItem):
        """Ajoute le nœud Groupes"""
        groups = self.controller.state.avatar_groups
        if not groups:
            return
        
        grp_node = QTreeWidgetItem(parent, ["Groupes d'avatars", "", f"{len(groups)}"])
        
        for name in sorted(groups.keys()):
            count = len(groups[name])
            item = QTreeWidgetItem([
                name,
                "Groupe",
                f"{count} avatars"
            ])
            grp_node.addChild(item)
        
        grp_node.setExpanded(True)
    
    def _add_contact_laws_node(self, parent: QTreeWidgetItem):
        """Ajoute le nœud Lois de contact"""
        laws = self.controller.get_contact_laws()
        law_node = QTreeWidgetItem(parent, ["Lois de contact", "", f"{len(laws)}"])
        
        for law in laws:
            info = f"μ={law.friction}" if law.friction else ""
            item = QTreeWidgetItem([
                f"{law.name} - {law.law_type.value}",
                "Loi",
                info
            ])
            law_node.addChild(item)
    
    def _add_visibility_node(self, parent: QTreeWidgetItem):
        """Ajoute le nœud Visibilité"""
        rules = self.controller.get_visibility_rules()
        if not rules:
            return
        
        vis_node = QTreeWidgetItem(parent, ["Tables de visibilité", "", f"{len(rules)}"])
        
        for rule in rules:
            item = QTreeWidgetItem([
                f"{rule.candidate_contactor}({rule.candidate_color}) ⇄ {rule.antagonist_contactor}",
                "Visibilité",
                f"→ {rule.behavior_name}"
            ])
            vis_node.addChild(item)
    
    def _add_operations_node(self, parent: QTreeWidgetItem):
        """Ajoute le nœud Opérations DOF"""
        ops = self.controller.get_dof_operations()
        if not ops:
            return
        
        ops_node = QTreeWidgetItem(parent, ["Opérations DOF", "", f"{len(ops)}"])
        
        for op in ops:
            if op.target_type == 'group':
                target = f"Groupe: {op.target_value}"
            else:
                target = f"Avatar #{op.target_value}"
            
            item = QTreeWidgetItem([
                op.operation_type,
                target,
                ""
            ])
            ops_node.addChild(item)
    
    def _add_loops_node(self, parent: QTreeWidgetItem):
        """Ajoute le nœud Boucles"""
        loops = self.controller.state.loops
        if not loops:
            return
        
        loop_node = QTreeWidgetItem(parent, ["Boucles", "", f"{len(loops)}"])
        
        for loop in loops:
            item = QTreeWidgetItem([
                loop.loop_type,
                "Boucle",
                f"{loop.count} → {loop.group_name or 'N/A'}"
            ])
            loop_node.addChild(item)
    
    def _add_granulo_node(self, parent: QTreeWidgetItem):
        """Ajoute le nœud Granulométrie"""
        granulos = self.controller.state.granulo_generations
        if not granulos:
            return
        
        gran_node = QTreeWidgetItem(parent, ["Dépôts Granulo", "", f"{len(granulos)}"])
        
        for i, gen in enumerate(granulos):
            item = QTreeWidgetItem([
                f"Granulo #{i+1}",
                gen.container_type,
                f"r=[{gen.radius_min:.3f}, {gen.radius_max:.3f}]"
            ])
            gran_node.addChild(item)
    
    def _add_postpro_node(self, parent: QTreeWidgetItem):
        """Ajoute le nœud Post-Pro"""
        commands = self.controller.state.postpro_commands
        if not commands:
            return
        
        post_node = QTreeWidgetItem(parent, ["Post-Processing", "", f"{len(commands)}"])
        
        for cmd in commands:
            target_info = "Global"
            if cmd.target_type == 'avatar':
                target_info = f"Avatar #{cmd.target_value}"
            elif cmd.target_type == 'group':
                target_info = f"Groupe: {cmd.target_value}"
            
            item = QTreeWidgetItem([
                cmd.name,
                f"step={cmd.step}",
                target_info
            ])
            post_node.addChild(item)
