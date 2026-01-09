# ============================================================================
# Contrôleur principal (Controller dans MVC)
# ============================================================================
"""
Contrôleur principal gérant la logique métier.
Fait le lien entre Model et View.
"""
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path

from ..core.models import (
    ProjectState, Material, Model, Avatar, ContactLaw, VisibilityRule,
    DOFOperation, Loop, GranuloGeneration, PostProCommand, AvatarOrigin, ProjectPreferences
)
from ..core.validators import (
    MaterialValidator, ModelValidator, AvatarValidator, 
    ContactLawValidator, ValidationError
)
from ..core.generators import LoopGenerator, GranuloGenerator
from ..core.serializers import ProjectSerializer
from ..core.pylmgc_bridge import LMGC90Bridge
from pylmgc90 import pre


class ProjectController:
    """Contrôleur principal gérant l'état du projet"""
    
    def __init__(self):
        self.state = ProjectState(name="Nouveau_Projet")
        self.project_path: Optional[Path] = None
        self._is_loading = False 
        
        # Conteneurs pylmgc90
        self._materials_container = pre.materials()
        self._models_container = pre.models()
        self._bodies_container = pre.avatars()
        self._contact_laws_container = pre.tact_behavs()
        self._visibility_container = pre.see_tables()
        self._postpro_container = pre.postpro_commands()
        
        # Objets pylmgc90 créés
        self._pylmgc_materials: Dict[str, Any] = {}
        self._pylmgc_models: Dict[str, Any] = {}
        self._pylmgc_bodies: List[Any] = []
        self._pylmgc_laws: Dict[str, Any] = {}
    
    # ========== PROJET ==========
    
    def new_project(self, name: str) -> None:
        """Crée un nouveau projet vide"""
        self.state = ProjectState(name=name)
        self.project_path = None
        self._reset_containers()
    
    def save_project(self, filepath: Optional[Path] = None) -> Path:
        """
        Sauvegarde le projet.
        
        Args:
            filepath: Chemin de sauvegarde (optionnel)
            
        Returns:
            Chemin du fichier sauvegardé
            
        Raises:
            ValueError: Si aucun chemin défini et non fourni
        """
        if filepath:
            self.project_path = filepath
        elif not self.project_path:
            raise ValueError("Aucun chemin de sauvegarde défini")
        
        ProjectSerializer.save(self.state, self.project_path)
        return self.project_path
    
    def load_project(self, filepath: Path) -> None:
        """
        Charge un projet depuis un fichier.
        
        Args:
            filepath: Chemin du fichier à charger
        """
        try : 
            self._is_loading = True
            self.state = ProjectSerializer.load(filepath)
            self.project_path = filepath
            self._rebuild_pylmgc_objects()
        finally:
            self._is_loading = False
    
    # ========== MATÉRIAUX ==========
    
    def add_material(self, material: Material) -> None:
        """
        Ajoute un matériau au projet.
        
        Args:
            material: Matériau à ajouter
            
        Raises:
            ValidationError: Si validation échoue
        """
        MaterialValidator.validate_or_raise(material)
        
        # Créer l'objet pylmgc90
        mat_obj = LMGC90Bridge.create_material(material)
        self._materials_container.addMaterial(mat_obj)
        self._pylmgc_materials[material.name] = mat_obj
        
        # Ajouter au modèle
        self.state.materials.append(material)
    
    def update_material(self, old_name: str, material: Material) -> None:
        """
        Met à jour un matériau existant.
        
        Args:
            old_name: Ancien nom du matériau
            material: Nouveau matériau (peut avoir un nom différent)
        
        Raises:
            ValueError: Si matériau introuvable
            ValidationError: Si validation échoue
        """
        MaterialValidator.validate_or_raise(material)
        
        # Trouver l'ancien matériau
        old_mat = self._find_material(old_name)
        if not old_mat:
            raise ValueError(f"Matériau '{old_name}' introuvable")
        
        # Vérifier si renommage
        if old_name != material.name:
            # Vérifier que le nouveau nom n'existe pas déjà
            if self._find_material(material.name):
                raise ValueError(f"Un matériau nommé '{material.name}' existe déjà")
            
            # Mettre à jour les références dans les avatars
            for avatar in self.state.avatars:
                if avatar.material_name == old_name:
                    avatar.material_name = material.name
        
        # Supprimer l'ancien objet pylmgc90
        self._materials_container.pop(old_name)
        self._pylmgc_materials.pop(old_name, None)
        
        # Créer le nouveau
        mat_obj = LMGC90Bridge.create_material(material)
        self._materials_container.addMaterial(mat_obj)
        self._pylmgc_materials[material.name] = mat_obj
        
        # Mettre à jour dans l'état
        idx = self.state.materials.index(old_mat)
        self.state.materials[idx] = material
    
    def remove_material(self, name: str) -> bool:
        """
        Supprime un matériau.
        
        Args:
            name: Nom du matériau
            
        Returns:
            True si supprimé, False si introuvable
        """
        material = self._find_material(name)
        if not material:
            return False
        
        self.state.materials.remove(material)
        self._materials_container.pop(name)
        self._pylmgc_materials.pop(name, None)
        return True
    
    def get_materials(self) -> List[Material]:
        """Retourne tous les matériaux"""
        return self.state.materials.copy()
    
    def get_material(self, name: str) -> Optional[Material]:
        """Retourne un matériau par son nom"""
        return self._find_material(name)

    def _find_material(self, name: str) -> Optional[Material]:
        """Trouve un matériau par nom"""
        for mat in self.state.materials:
            if mat.name == name:
                return mat
        return None
    
    def is_material_used(self, name: str) -> tuple[bool, list[str]]:
        """
        Vérifie si un matériau est utilisé.
        
        Returns:
            (is_used, references) où references est une liste de descriptions
        """
        refs = []
        for i, avatar in enumerate(self.state.avatars):
            if avatar.material_name == name:
                refs.append(f"Avatar #{i} ({avatar.avatar_type.value})")
        
        return len(refs) > 0, refs
    
    # ========== MODÈLES ==========
    
    def add_model(self, model: Model) -> None:
        """
        Ajoute un modèle au projet.
        
        Args:
            model: Modèle à ajouter
            
        Raises:
            ValidationError: Si validation échoue
        """
        ModelValidator.validate_or_raise(model)
        
        # Créer l'objet pylmgc90
        mod_obj = LMGC90Bridge.create_model(model)
        self._models_container.addModel(mod_obj)
        self._pylmgc_models[model.name] = mod_obj
        
        # Ajouter au modèle
        self.state.models.append(model)
    
    def update_model(self, old_name: str, model: Model) -> None:
        """
        Met à jour un modèle existant.
        
        Args:
            old_name: Ancien nom du modèle
            model: Nouveau modèle
        
        Raises:
            ValueError: Si modèle introuvable
            ValidationError: Si validation échoue
        """
        ModelValidator.validate_or_raise(model)
        
        old_mod = self._find_model(old_name)
        if not old_mod:
            raise ValueError(f"Modèle '{old_name}' introuvable")
        
        # Vérifier renommage
        if old_name != model.name:
            if self._find_model(model.name):
                raise ValueError(f"Un modèle nommé '{model.name}' existe déjà")
            
            # Mettre à jour références
            for avatar in self.state.avatars:
                if avatar.model_name == old_name:
                    avatar.model_name = model.name
        
        # Supprimer ancien
        self._models_container.pop(old_name)
        self._pylmgc_models.pop(old_name, None)
        
        # Créer nouveau
        mod_obj = LMGC90Bridge.create_model(model)
        self._models_container.addModel(mod_obj)
        self._pylmgc_models[model.name] = mod_obj
        
        # Mettre à jour état
        idx = self.state.models.index(old_mod)
        self.state.models[idx] = model

    def get_model(self, name: str) -> Optional[Model]:
        """Retourne un modèle par son nom"""
        return self._find_model(name)

    def is_model_used(self, name: str) -> tuple[bool, list[str]]:
        """Vérifie si un modèle est utilisé"""
        refs = []
        for i, avatar in enumerate(self.state.avatars):
            if avatar.model_name == name:
                refs.append(f"Avatar #{i} ({avatar.avatar_type.value})")
        
        return len(refs) > 0, refs
    
    def remove_model(self, name: str) -> bool:
        """Supprime un modèle"""
        model = self._find_model(name)
        if not model:
            return False
        
        self.state.models.remove(model)
        self._models_container.pop(name)
        self._pylmgc_models.pop(name, None)
        return True
    
    def get_models(self) -> List[Model]:
        """Retourne tous les modèles"""
        return self.state.models.copy()
    
    def _find_model(self, name: str) -> Optional[Model]:
        """Trouve un modèle par nom"""
        for mod in self.state.models:
            if mod.name == name:
                return mod
        return None
    
    # ========== AVATARS ==========
    
    def add_avatar(self, avatar: Avatar) -> int:
        """
        Ajoute un avatar au projet.
        
        Args:
            avatar: Avatar à ajouter
            
        Returns:
            Index de l'avatar créé
            
        Raises:
            ValidationError: Si validation échoue
            ValueError: Si matériau ou modèle introuvable
        """
        AvatarValidator.validate_or_raise(avatar, self.state.dimension)
        
        # Récupérer les objets pylmgc90
        mat_obj = self._pylmgc_materials.get(avatar.material_name)
        mod_obj = self._pylmgc_models.get(avatar.model_name)
        
        if not mat_obj:
            raise ValueError(f"Matériau '{avatar.material_name}' introuvable")
        if not mod_obj:
            raise ValueError(f"Modèle '{avatar.model_name}' introuvable")
        
        # Créer l'objet pylmgc90
        body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
        self._bodies_container.addAvatar(body_obj)
        self._pylmgc_bodies.append(body_obj)
        
        # Ajouter au modèle
        self.state.avatars.append(avatar)
        
        return len(self.state.avatars) - 1
    
    def update_avatar(self, index: int, avatar: Avatar) -> None:
        """
        Met à jour un avatar existant.
        
        Args:
            index: Index de l'avatar
            avatar: Nouvel avatar
        
        Raises:
            ValueError: Si index invalide
            ValidationError: Si validation échoue
        """
        if not (0 <= index < len(self.state.avatars)):
            raise ValueError(f"Index {index} invalide")
        
        AvatarValidator.validate_or_raise(avatar, self.state.dimension)
        
        # Vérifier que matériau et modèle existent
        mat_obj = self._pylmgc_materials.get(avatar.material_name)
        mod_obj = self._pylmgc_models.get(avatar.model_name)
        
        if not mat_obj:
            raise ValueError(f"Matériau '{avatar.material_name}' introuvable")
        if not mod_obj:
            raise ValueError(f"Modèle '{avatar.model_name}' introuvable")
        
        # Supprimer ancien objet pylmgc90
        old_body = self._pylmgc_bodies[index]
        self._bodies_container.remove(old_body)
        
        # Créer nouveau
        body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
        self._bodies_container.addAvatar(body_obj)
        self._pylmgc_bodies[index] = body_obj
        
        # Mettre à jour état
        self.state.avatars[index] = avatar

    def get_avatar(self, index: int) -> Optional[Avatar]:
        """Retourne un avatar par son index"""
        if 0 <= index < len(self.state.avatars):
            return self.state.avatars[index]
        return None

    def is_avatar_used(self, index: int) -> tuple[bool, list[str]]:
        """Vérifie si un avatar est référencé (boucles, groupes)"""
        refs = []
        
        # Vérifier boucles
        for i, loop in enumerate(self.state.loops):
            if loop.model_avatar_index == index:
                refs.append(f"Boucle #{i+1} ({loop.loop_type})")
        
        # Vérifier groupes
        for group_name, indices in self.state.avatar_groups.items():
            if index in indices:
                refs.append(f"Groupe '{group_name}'")
        
        return len(refs) > 0, refs
    
    def remove_avatar(self, index: int) -> bool:
        """Supprime un avatar par index"""
        if 0 <= index < len(self.state.avatars):
            avatar = self.state.avatars[index]
            body = self._pylmgc_bodies[index]
            
            self.state.avatars.pop(index)
            self._bodies_container.remove(body)
            self._pylmgc_bodies.pop(index)
            return True
        return False
    
    def get_avatars(self, include_generated: bool = True) -> List[Avatar]:
        """
        Retourne les avatars.
        
        Args:
            include_generated: Inclure les avatars générés (boucles, granulo)
        """
        if include_generated:
            return self.state.avatars.copy()
        else:
            return [a for a in self.state.avatars if a.origin == AvatarOrigin.MANUAL]
    
    # ========== LOIS DE CONTACT ==========
    
    def add_contact_law(self, law: ContactLaw) -> None:
        """Ajoute une loi de contact"""
        ContactLawValidator.validate_or_raise(law)
        
        law_obj = LMGC90Bridge.create_contact_law(law)
        self._contact_laws_container.addBehav(law_obj)
        self._pylmgc_laws[law.name] = law_obj
        
        self.state.contact_laws.append(law)
    
    def update_contact_law(self, old_name: str, law: ContactLaw) -> None:
        """Met à jour une loi de contact"""
        ContactLawValidator.validate_or_raise(law)
        
        old_law = self._find_contact_law(old_name)
        if not old_law:
            raise ValueError(f"Loi '{old_name}' introuvable")
        
        # Vérifier renommage
        if old_name != law.name:
            if self._find_contact_law(law.name):
                raise ValueError(f"Une loi nommée '{law.name}' existe déjà")
            
            # Mettre à jour références dans visibilité
            for rule in self.state.visibility_rules:
                if rule.behavior_name == old_name:
                    rule.behavior_name = law.name
        
        # Supprimer ancien
        self._contact_laws_container.pop(old_name)
        self._pylmgc_laws.pop(old_name, None)
        
        # Créer nouveau
        law_obj = LMGC90Bridge.create_contact_law(law)
        self._contact_laws_container.addBehav(law_obj)
        self._pylmgc_laws[law.name] = law_obj
        
        # Mettre à jour état
        idx = self.state.contact_laws.index(old_law)
        self.state.contact_laws[idx] = law

    def get_contact_law(self, name: str) -> Optional[ContactLaw]:
        """Retourne une loi par son nom"""
        return self._find_contact_law(name)

    def is_contact_law_used(self, name: str) -> tuple[bool, list[str]]:
        """Vérifie si une loi est utilisée"""
        refs = []
        for i, rule in enumerate(self.state.visibility_rules):
            if rule.behavior_name == name:
                refs.append(f"Règle de visibilité #{i+1}")
        
        return len(refs) > 0, refs
    
    def remove_contact_law(self, name: str) -> bool:
        """Supprime une loi de contact"""
        law = self._find_contact_law(name)
        if not law:
            return False
        
        self.state.contact_laws.remove(law)
        self._contact_laws_container.pop(name)
        self._pylmgc_laws.pop(name, None)
        return True
    
    def get_contact_laws(self) -> List[ContactLaw]:
        """Retourne toutes les lois de contact"""
        return self.state.contact_laws.copy()
    
    def _find_contact_law(self, name: str) -> Optional[ContactLaw]:
        """Trouve une loi de contact par nom"""
        for law in self.state.contact_laws:
            if law.name == name:
                return law
        return None
    
    # ========== VISIBILITÉ ==========
    def add_visibility_rule(self, rule: VisibilityRule) -> None:
        """Ajoute une règle de visibilité"""
        behavior_obj = self._pylmgc_laws.get(rule.behavior_name)
        if not behavior_obj:
            raise ValueError(f"Loi '{rule.behavior_name}' introuvable")
        
        rule_obj = LMGC90Bridge.create_visibility_rule(rule, behavior_obj)
        self._visibility_container.addSeeTable(rule_obj)
        
        self.state.visibility_rules.append(rule)
    
    def update_visibility_rule(self, index: int, rule: VisibilityRule) -> None:
        """Met à jour une règle de visibilité"""
        if not (0 <= index < len(self.state.visibility_rules)):
            raise ValueError(f"Index {index} invalide")
        
        # Vérifier que la loi existe
        behavior_obj = self._pylmgc_laws.get(rule.behavior_name)
        if not behavior_obj:
            raise ValueError(f"Loi '{rule.behavior_name}' introuvable")
        
        # Supprimer ancienne règle (pylmgc90 ne permet pas de modifier)
        # Il faut reconstruire toute la table de visibilité
        self._visibility_container = pre.see_tables()
        
        # Mettre à jour état
        self.state.visibility_rules[index] = rule
        
        # Recréer toutes les règles
        for r in self.state.visibility_rules:
            behav = self._pylmgc_laws[r.behavior_name]
            rule_obj = LMGC90Bridge.create_visibility_rule(r, behav)
            self._visibility_container.addSeeTable(rule_obj)

    def get_visibility_rule(self, index: int) -> Optional[VisibilityRule]:
        """Retourne une règle par son index"""
        if 0 <= index < len(self.state.visibility_rules):
            return self.state.visibility_rules[index]
        return None
    
    def remove_visibility_rule(self, index: int) -> bool:
        """Supprime une règle de visibilité"""
        if 0 <= index < len(self.state.visibility_rules):
            self.state.visibility_rules.pop(index)
            return True
        return False
    
    def get_visibility_rules(self) -> List[VisibilityRule]:
        """Retourne toutes les règles"""
        return self.state.visibility_rules.copy()
    
    # ========== OPÉRATIONS DOF ==========
    def apply_dof_operation(self, operation: DOFOperation) -> None:
        """
        Applique une opération DOF sur les avatars (sans sauvegarder).
        """
        if operation.target_type == 'avatar':
            idx = operation.target_value
            if 0 <= idx < len(self._pylmgc_bodies):
                body = self._pylmgc_bodies[idx]
                LMGC90Bridge.apply_dof_operation(operation, body)
        
        elif operation.target_type == 'group':
            group_name = operation.target_value
            indices = self.state.avatar_groups.get(group_name, [])
            for idx in indices:
                if 0 <= idx < len(self._pylmgc_bodies):
                    body = self._pylmgc_bodies[idx]
                    LMGC90Bridge.apply_dof_operation(operation, body)


    def add_dof_operation(self, operation: DOFOperation) -> None:
        """
        Applique ET sauvegarde une opération DOF.
        Utilisé lors de la création d'une nouvelle opération par l'utilisateur.
        """
        self.apply_dof_operation(operation)  # ← Applique
        self.state.operations.append(operation)  # ← Sauvegarde
            
    def get_dof_operations(self) -> List[DOFOperation]:
        """Retourne toutes les opérations DOF"""
        return self.state.operations.copy()
    
    # ========== BOUCLES ==========
    def generate_loop(self, loop: Loop) -> List[int]:
        """
        Génère des avatars selon une boucle.
        
        Args:
            loop: Configuration de la boucle
        Returns:
            Liste des indices des avatars créés
        """
        if loop.model_avatar_index >= len(self.state.avatars):
            raise ValueError("Index du modèle d'avatar invalide")
        
        model_avatar = self.state.avatars[loop.model_avatar_index]
        centers = LoopGenerator.generate_positions(loop)
        
        generated_indices = []
        for center in centers:
            # Créer une copie de l'avatar avec nouveau centre
            new_avatar = Avatar(
                avatar_type=model_avatar.avatar_type,
                center=center,
                material_name=model_avatar.material_name,
                model_name=model_avatar.model_name,
                color=model_avatar.color,
                origin=AvatarOrigin.LOOP,
                radius=model_avatar.radius,
                axis=model_avatar.axis,
                vertices=model_avatar.vertices,
                nb_vertices=model_avatar.nb_vertices,
                generation_type=model_avatar.generation_type,
                is_hollow=model_avatar.is_hollow,
                wall_params=model_avatar.wall_params,
                contactors=model_avatar.contactors
            )
            
            idx = self.add_avatar(new_avatar)
            generated_indices.append(idx)
        
        loop.generated_indices = generated_indices
        if not self._is_loading:
            self.state.loops.append(loop)
        
        # Ajouter au groupe si spécifié
        if loop.group_name:
            if loop.group_name not in self.state.avatar_groups:
                self.state.avatar_groups[loop.group_name] = []
            self.state.avatar_groups[loop.group_name].extend(generated_indices)
        
        return generated_indices
    
    def remove_loop(self, index: int) -> bool:
        """
        Supprime une boucle ET ses avatars générés.
        
        Returns:
            True si supprimé
        """
        if not (0 <= index < len(self.state.loops)):
            return False
        
        loop = self.state.loops[index]
        
        # Supprimer les avatars générés (en ordre inverse pour garder les indices)
        for avatar_idx in sorted(loop.generated_indices, reverse=True):
            self.remove_avatar(avatar_idx)
        
        # Supprimer la boucle
        self.state.loops.pop(index)
        return True

    def get_loop(self, index: int) -> Optional[Loop]:
        """Retourne une boucle par son index"""
        if 0 <= index < len(self.state.loops):
            return self.state.loops[index]
        return None

    # ========== GRANULOMÉTRIE ==========
    def generate_granulo(self, config: GranuloGeneration) -> List[int]:
        """
        Génère une distribution granulométrique.
        
        Args:
            config: Configuration de la génération
            
        Returns:
            Liste des indices des particules créées
        """
        # Génération des positions et rayons
        nb_particles, coordinates, radii = GranuloGenerator.generate(config)
        
        generated_indices = []
        for i in range(nb_particles):
            center = coordinates[i].tolist()
            radius = float(radii[i])
            
            # Créer l'avatar
            from ..core.models import AvatarType
            avatar = Avatar(
                avatar_type=AvatarType(config.avatar_type),
                center=center,
                material_name=config.material_name,
                model_name=config.model_name,
                color=config.color,
                origin=AvatarOrigin.GRANULO,
                radius=radius
            )
            
            idx = self.add_avatar(avatar)
            generated_indices.append(idx)
        
        config.generated_indices = generated_indices
        if not self._is_loading:
            self.state.granulo_generations.append(config)
        
        # Ajouter au groupe si spécifié
        if config.group_name:
            if config.group_name not in self.state.avatar_groups:
                self.state.avatar_groups[config.group_name] = []
            self.state.avatar_groups[config.group_name].extend(generated_indices)
        
        return generated_indices
    
    def remove_granulo(self, index: int) -> bool:
        """Supprime une génération granulo ET ses avatars"""
        if not (0 <= index < len(self.state.granulo_generations)):
            return False
        
        granulo = self.state.granulo_generations[index]
        
        # Supprimer avatars générés
        for avatar_idx in sorted(granulo.generated_indices, reverse=True):
            self.remove_avatar(avatar_idx)
        
        # Supprimer la génération
        self.state.granulo_generations.pop(index)
        return True

    def get_granulo(self, index: int) -> Optional[GranuloGeneration]:
        """Retourne une génération granulo par son index"""
        if 0 <= index < len(self.state.granulo_generations):
            return self.state.granulo_generations[index]
        return None
    
    # ========== POST-TRAITEMENT ==========
    def add_postpro_command(self, command: PostProCommand) -> None:
        """Ajoute une commande post-pro"""
        # Créer l'objet pylmgc90
        rigid_set = None
        
        if command.target_type == 'avatar':
            idx = command.target_value
            if 0 <= idx < len(self._pylmgc_bodies):
                rigid_set = [self._pylmgc_bodies[idx]]
        
        elif command.target_type == 'group':
            group_name = command.target_value
            indices = self.state.avatar_groups.get(group_name, [])
            rigid_set = [self._pylmgc_bodies[i] for i in indices 
                        if 0 <= i < len(self._pylmgc_bodies)]
        
        # Créer la commande
        if rigid_set:
            cmd = pre.postpro_command(
                name=command.name, 
                step=command.step, 
                rigid_set=rigid_set
            )
        else:
            cmd = pre.postpro_command(
                name=command.name, 
                step=command.step
            )
        
        self._postpro_container.addCommand(cmd)
        self.state.postpro_commands.append(command)
    
    def remove_postpro_command(self, index: int) -> bool:
        """Supprime une commande post-pro"""
        if 0 <= index < len(self.state.postpro_commands):
            self.state.postpro_commands.pop(index)
            return True
        return False
    def update_postpro_command(self, index: int, command: PostProCommand) -> None:
        """Met à jour une commande post-pro"""
        if not (0 <= index < len(self.state.postpro_commands)):
            raise ValueError(f"Index {index} invalide")
        
        # Reconstruire toutes les commandes
        self._postpro_container = pre.postpro_commands()
        
        # Mettre à jour état
        self.state.postpro_commands[index] = command
        
        # Recréer toutes
        for cmd in self.state.postpro_commands:
            rigid_set = None
            
            if cmd.target_type == 'avatar':
                idx = cmd.target_value
                if 0 <= idx < len(self._pylmgc_bodies):
                    rigid_set = [self._pylmgc_bodies[idx]]
            
            elif cmd.target_type == 'group':
                group_name = cmd.target_value
                indices = self.state.avatar_groups.get(group_name, [])
                rigid_set = [self._pylmgc_bodies[i] for i in indices 
                            if 0 <= i < len(self._pylmgc_bodies)]
            
            if rigid_set:
                cmd_obj = pre.postpro_command(name=cmd.name, step=cmd.step, rigid_set=rigid_set)
            else:
                cmd_obj = pre.postpro_command(name=cmd.name, step=cmd.step)
            
            self._postpro_container.addCommand(cmd_obj)

    def get_postpro_command(self, index: int) -> Optional[PostProCommand]:
        """Retourne une commande post-pro par son index"""
        if 0 <= index < len(self.state.postpro_commands):
            return self.state.postpro_commands[index]
        return None
    # ========== GÉNÉRATION SCRIPT/DATBOX ==========
    
    def generate_datbox(self, output_path: Path) -> None:
        """
        Génère le fichier DATBOX.
        
        Args:
            output_path: Chemin du fichier de sortie
        """
        pre.writeDatbox(
            dim=self.state.dimension,
            mats=self._materials_container,
            mods=self._models_container,
            bodies=self._bodies_container,
            tacts=self._contact_laws_container,
            sees=self._visibility_container,
            post=self._postpro_container,
            datbox_path=str(output_path)
        )
    
    # ========== UTILITAIRES PRIVÉS ==========
    
    def _reset_containers(self) -> None:
        """Réinitialise tous les conteneurs"""
        self._materials_container = pre.materials()
        self._models_container = pre.models()
        self._bodies_container = pre.avatars()
        self._contact_laws_container = pre.tact_behavs()
        self._visibility_container = pre.see_tables()
        self._postpro_container = pre.postpro_commands()
        
        self._pylmgc_materials.clear()
        self._pylmgc_models.clear()
        self._pylmgc_bodies.clear()
        self._pylmgc_laws.clear()
    
    def _rebuild_pylmgc_objects(self) -> None:
        """Reconstruit tous les objets pylmgc90 depuis l'état"""
        self._reset_containers()
        
        # Recréer matériaux
        for mat in self.state.materials:
            mat_obj = LMGC90Bridge.create_material(mat)
            self._materials_container.addMaterial(mat_obj)
            self._pylmgc_materials[mat.name] = mat_obj
        
        # Recréer modèles
        for mod in self.state.models:
            mod_obj = LMGC90Bridge.create_model(mod)
            self._models_container.addModel(mod_obj)
            self._pylmgc_models[mod.name] = mod_obj
        
        # Recréer avatars manuels
        manual_avatars = [av for av in self.state.avatars if av.origin == AvatarOrigin.MANUAL]
        for avatar in manual_avatars:
            mat_obj = self._pylmgc_materials.get(avatar.material_name)
            mod_obj = self._pylmgc_models.get(avatar.model_name)
            
            if not mat_obj:
                raise ValueError(f"Matériau '{avatar.material_name}' introuvable lors de la reconstruction")
            if not mod_obj:
                raise ValueError(f"Modèle '{avatar.model_name}' introuvable lors de la reconstruction")
            
            body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
            self._bodies_container.addAvatar(body_obj)
            self._pylmgc_bodies.append(body_obj)
        
        # Régénérer boucles
        regeneration_errors = []
        for i, loop in enumerate(self.state.loops):
            try:
                if loop.model_avatar_index >= len(self.state.avatars):
                    raise ValueError(f"Index modèle {loop.model_avatar_index} invalide")
                self.generate_loop(loop)
            except Exception as e:
                regeneration_errors.append(f"Boucle {i+1}: {str(e)}")
        
        # Régénérer granulo
        for i, granulo in enumerate(self.state.granulo_generations):
            try:
                self.generate_granulo(granulo)
            except Exception as e:
                regeneration_errors.append(f"Granulo {i+1}: {str(e)}")

        if regeneration_errors:
            # Stocker pour affichage ultérieur dans l'UI
            self.state.load_warnings = regeneration_errors

        # Recréer lois de contact
        for law in self.state.contact_laws:
            law_obj = LMGC90Bridge.create_contact_law(law)
            self._contact_laws_container.addBehav(law_obj)
            self._pylmgc_laws[law.name] = law_obj
        
        # Recréer visibilité
        for rule in self.state.visibility_rules:
            behavior_obj = self._pylmgc_laws.get(rule.behavior_name)
            if not behavior_obj:
                raise ValueError(f"Loi '{rule.behavior_name}' introuvable lors de la reconstruction")
            
            rule_obj = LMGC90Bridge.create_visibility_rule(rule, behavior_obj)
            self._visibility_container.addSeeTable(rule_obj)
        
        # Réappliquer opérations DOF
        for op in self.state.operations:
            self.apply_dof_operation(op)
