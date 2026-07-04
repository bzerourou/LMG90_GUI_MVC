# ============================================================================
# Contrôleur principal
# ============================================================================
"""
Contrôleur principal gérant la logique métier.
Fait le lien entre Model et View.

=== REFACTOR "avatar_id stable" ===
Toutes les références à des avatars utilisent désormais avatar_id (str)
plutôt que la position dans state.avatars (int), qui est instable dès
qu'un autre avatar est supprimé.

Points de vigilance :
  - avatar_groups : Dict[str, List[str]]  (avatar_ids, non positions)
  - Loop.model_avatar_id / Loop.generated_ids
  - GranuloGeneration.generated_ids
  - ForLoop.generated_refs
  - DOFOperation.target_value  pour 'avatar'  → avatar_id
  - PostProCommand.target_value pour 'avatar' → avatar_id
"""
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from ..core.models import (
    AvatarType, ProjectState, Material, Model, Avatar, ContactLaw, VisibilityRule,
    DOFOperation, Loop, ForLoop, GranuloGeneration, PostProCommand, AvatarOrigin,
    new_avatar_id,
)
from ..core.validators import (
    MaterialValidator, ModelValidator, AvatarValidator,
    ContactLawValidator, ValidationError
)
from ..core.generators import LoopGenerator, GranuloGenerator
from ..core.serializers import ProjectSerializer
from ..core.pylmgc_bridge import LMGC90Bridge
import math
from pylmgc90 import pre


class ProjectController(QObject):
    """Contrôleur principal gérant l'état du projet"""
    state_changed = pyqtSignal()

    def __init__(self, state=None):
        super().__init__()
        self.state = state or ProjectState(name="Nouveau_Projet")
        self.project_path: Optional[Path] = None
        self._is_loading = False
        self._batch_mode = False

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

    # =========================================================================
    # Utilitaires internes – avatar_id
    # =========================================================================

    def _find_avatar_by_id(self, avatar_id: str) -> Optional[Tuple[int, Avatar]]:
        """
        Retourne (index, avatar) pour l'avatar_id donné, ou None si introuvable.
        Le scan est linéaire ; utilisez _build_id_to_idx() quand vous avez
        besoin de résoudre plusieurs ids à la suite.
        """
        for i, av in enumerate(self.state.avatars):
            if av.avatar_id == avatar_id:
                return i, av
        return None

    def _build_id_to_idx(self) -> Dict[str, int]:
        """Construit un dictionnaire avatar_id → index (accès O(1) en lot)."""
        return {av.avatar_id: i for i, av in enumerate(self.state.avatars)}

    # =========================================================================
    # PROJET
    # =========================================================================

    def new_project(self, name: str) -> None:
        """Crée un nouveau projet vide"""
        self.state = ProjectState(name=name)
        self.project_path = None
        self._reset_containers()

    def save_project(self, filepath: Optional[Path] = None) -> Path:
        if filepath:
            self.project_path = filepath
        elif not self.project_path:
            raise ValueError("Aucun chemin de sauvegarde défini")
        ProjectSerializer.save(self.state, self.project_path)
        return self.project_path

    def load_project(self, filepath: Path) -> None:
        try:
            self._is_loading = True
            self.state = ProjectSerializer.load(filepath)
            self.project_path = filepath
            self._rebuild_pylmgc_objects()
            # Ajouter les factory avatars APRÈS rebuild (alignement garanti)
            self._restore_factory_avatars()
        finally:
            self._is_loading = False

    # =========================================================================
    # MATÉRIAUX
    # =========================================================================

    def add_material(self, material: Material) -> None:
        if any(m.name == material.name for m in self.state.materials):
            raise ValidationError(
                f"Nom de matériau '{material.name}' déjà utilisé. Les noms doivent être uniques."
            )
        MaterialValidator.validate_or_raise(material)
        mat_obj = LMGC90Bridge.create_material(material)
        self._materials_container.addMaterial(mat_obj)
        self._pylmgc_materials[material.name] = mat_obj
        self.state.materials.append(material)
        self.state_changed.emit()

    def update_material(self, old_name: str, material: Material) -> None:
        MaterialValidator.validate_or_raise(material)
        old_mat = self._find_material(old_name)
        if not old_mat:
            raise ValueError(f"Matériau '{old_name}' introuvable")
        if old_name != material.name:
            if self._find_material(material.name):
                raise ValueError(f"Un matériau nommé '{material.name}' existe déjà")
            for avatar in self.state.avatars:
                if avatar.material_name == old_name:
                    avatar.material_name = material.name
        self._materials_container.pop(old_name)
        self._pylmgc_materials.pop(old_name, None)
        mat_obj = LMGC90Bridge.create_material(material)
        self._materials_container.addMaterial(mat_obj)
        self._pylmgc_materials[material.name] = mat_obj
        idx = self.state.materials.index(old_mat)
        self.state.materials[idx] = material

    def remove_material(self, name: str) -> bool:
        material = self._find_material(name)
        if not material:
            return False
        self.state.materials.remove(material)
        self._materials_container.pop(name)
        self._pylmgc_materials.pop(name, None)
        return True

    def get_materials(self) -> List[Material]:
        return self.state.materials.copy()

    def get_material(self, name: str) -> Optional[Material]:
        return self._find_material(name)

    def _find_material(self, name: str) -> Optional[Material]:
        for mat in self.state.materials:
            if mat.name == name:
                return mat
        return None

    def is_material_used(self, name: str) -> tuple[bool, list[str]]:
        refs = []
        for i, avatar in enumerate(self.state.avatars):
            if avatar.material_name == name:
                refs.append(f"Avatar #{i} ({avatar.avatar_type.value})")
        return len(refs) > 0, refs

    # =========================================================================
    # MODÈLES
    # =========================================================================

    def add_model(self, model: Model) -> None:
        if any(m.name == model.name for m in self.state.models):
            raise ValidationError(
                f"Nom de modèle '{model.name}' déjà utilisé. Les noms doivent être uniques."
            )
        ModelValidator.validate_or_raise(model)
        mod_obj = LMGC90Bridge.create_model(model)
        self._models_container.addModel(mod_obj)
        self._pylmgc_models[model.name] = mod_obj
        self.state.models.append(model)
        self.state_changed.emit()

    def update_model(self, old_name: str, model: Model) -> None:
        ModelValidator.validate_or_raise(model)
        old_mod = self._find_model(old_name)
        if not old_mod:
            raise ValueError(f"Modèle '{old_name}' introuvable")
        if old_name != model.name:
            if self._find_model(model.name):
                raise ValueError(f"Un modèle nommé '{model.name}' existe déjà")
            for avatar in self.state.avatars:
                if avatar.model_name == old_name:
                    avatar.model_name = model.name
        self._models_container.pop(old_name)
        self._pylmgc_models.pop(old_name, None)
        mod_obj = LMGC90Bridge.create_model(model)
        self._models_container.addModel(mod_obj)
        self._pylmgc_models[model.name] = mod_obj
        idx = self.state.models.index(old_mod)
        self.state.models[idx] = model

    def get_model(self, name: str) -> Optional[Model]:
        return self._find_model(name)

    def is_model_used(self, name: str) -> tuple[bool, list[str]]:
        refs = []
        for i, avatar in enumerate(self.state.avatars):
            if avatar.model_name == name:
                refs.append(f"Avatar #{i} ({avatar.avatar_type.value})")
        return len(refs) > 0, refs

    def remove_model(self, name: str) -> bool:
        model = self._find_model(name)
        if not model:
            return False
        self.state.models.remove(model)
        self._models_container.pop(name)
        self._pylmgc_models.pop(name, None)
        return True

    def get_models(self) -> List[Model]:
        return self.state.models.copy()

    def _find_model(self, name: str) -> Optional[Model]:
        for mod in self.state.models:
            if mod.name == name:
                return mod
        return None

    # =========================================================================
    # AVATARS
    # =========================================================================

    def add_avatar(self, avatar: Avatar, create_pylmgc: bool = True) -> int:
        model = next((m for m in self.state.models if m.name == avatar.model_name), None)
        if not model:
            raise ValueError(f"Modèle '{avatar.model_name}' introuvable")
        AvatarValidator.validate_or_raise(avatar, model)
        if create_pylmgc:
            mat_obj = self._pylmgc_materials.get(avatar.material_name)
            mod_obj = self._pylmgc_models.get(avatar.model_name)
            if not mat_obj:
                raise ValueError(f"Matériau '{avatar.material_name}' introuvable")
            if not mod_obj:
                raise ValueError(f"Modèle '{avatar.model_name}' introuvable")
            body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
            # create_avatar retourne None pour MESH_DEFORMABLE sans mesh_params.
            # On ne crashe pas : on ajoute un placeholder None dans _pylmgc_bodies
            # pour maintenir l'alignement avec state.avatars (1 entrée par avatar).
            if body_obj is not None:
                self._bodies_container.addAvatar(body_obj)
            self._pylmgc_bodies.append(body_obj)  # None ou objet valide
        else:
            self._pylmgc_bodies.append(None)
        self.state.avatars.append(avatar)
        if not self._batch_mode:
            self.state_changed.emit()
        return len(self.state.avatars) - 1

    def update_avatar(self, index: int, avatar: Avatar) -> None:
        if not (0 <= index < len(self.state.avatars)):
            raise ValueError(f"Index {index} invalide")
        model = next((m for m in self.state.models if m.name == avatar.model_name), None)
        if not model:
            raise ValueError(f"Modèle '{avatar.model_name}' introuvable")
        AvatarValidator.validate_or_raise(avatar, model)
        mat_obj = self._pylmgc_materials.get(avatar.material_name)
        mod_obj = self._pylmgc_models.get(avatar.model_name)
        if not mat_obj:
            raise ValueError(f"Matériau '{avatar.material_name}' introuvable")
        if not mod_obj:
            raise ValueError(f"Modèle '{avatar.model_name}' introuvable")
        old_body = self._pylmgc_bodies[index]
        if old_body is not None:
            self._bodies_container.remove(old_body)
        body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
        if body_obj is not None:
            self._bodies_container.addAvatar(body_obj)
        self._pylmgc_bodies[index] = body_obj  # None ou objet valide
        self.state.avatars[index] = avatar

    def get_avatar(self, index: int) -> Optional[Avatar]:
        if 0 <= index < len(self.state.avatars):
            return self.state.avatars[index]
        return None

    def is_avatar_used(self, index: int) -> tuple[bool, list[str]]:
        """Vérifie si un avatar (par position) est référencé."""
        refs = []
        if not (0 <= index < len(self.state.avatars)):
            return False, []
        avatar = self.state.avatars[index]
        aid = avatar.avatar_id

        # Vérifier boucles (référence par avatar_id)
        for i, loop in enumerate(self.state.loops):
            if loop.model_avatar_id == aid:
                refs.append(f"Boucle #{i + 1} ({loop.loop_type})")

        # Vérifier groupes (contiennent des avatar_ids)
        for group_name, avatar_ids in self.state.avatar_groups.items():
            if aid in avatar_ids:
                refs.append(f"Groupe '{group_name}'")

        return len(refs) > 0, refs

    def remove_avatar(self, index: int) -> bool:
        if 0 <= index < len(self.state.avatars):
            self.state.avatars.pop(index)
            body = None
            if index < len(self._pylmgc_bodies):
                body = self._pylmgc_bodies.pop(index)
            if body is not None:
                try:
                    self._bodies_container.remove(body)
                except Exception as e:
                    from ..core.app_logger import get_logger
                    get_logger('controller').warning(f"Erreur suppression avatar #{index}: {e}")
            return True
        return False

    def get_avatars(self, include_generated: bool = True) -> List[Avatar]:
        if include_generated:
            return self.state.avatars.copy()
        else:
            return [a for a in self.state.avatars if a.origin == AvatarOrigin.MANUAL]

    def duplicate_avatar(
        self, index: int, n_copies: int, offset: list, group_name: str = None
    ) -> list:
        import copy as _copy
        if not (0 <= index < len(self.state.avatars)):
            raise IndexError(f"Index avatar {index} hors bornes.")
        if n_copies < 1:
            raise ValueError("n_copies doit être ≥ 1.")
        if not offset:
            raise ValueError("offset ne peut pas être vide.")

        source = self.state.avatars[index]
        new_indices = []
        dim = len(source.center)

        self._batch_mode = True
        try:
            for k in range(1, n_copies + 1):
                clone = _copy.deepcopy(source)
                clone.center = [
                    source.center[i] + k * (offset[i] if i < len(offset) else 0.0)
                    for i in range(dim)
                ]
                idx = self._add_avatar_no_validate(clone)
                new_indices.append(idx)
        finally:
            self._batch_mode = False

        if group_name:
            # Stocker les avatar_ids stables (pas les positions)
            new_ids = [self.state.avatars[i].avatar_id for i in new_indices]
            self.state.avatar_groups.setdefault(group_name, []).extend(new_ids)

        self.state_changed.emit()
        return new_indices

    def duplicate_group(
        self,
        group_name: str,
        n_copies: int,
        offset: list,
        new_group_prefix: str = None,
    ) -> dict:
        import copy as _copy

        if group_name not in self.state.avatar_groups:
            raise KeyError(f"Groupe '{group_name}' introuvable.")
        if n_copies < 1:
            raise ValueError("n_copies doit être ≥ 1.")
        if not offset:
            raise ValueError("offset ne peut pas être vide.")

        source_avatar_ids = self.state.avatar_groups[group_name]  # List[str]
        prefix = new_group_prefix or group_name
        result: Dict[str, list] = {}

        self._batch_mode = True
        try:
            for k in range(1, n_copies + 1):
                serie_indices = []
                for aid in source_avatar_ids:
                    res = self._find_avatar_by_id(aid)
                    if res is None:
                        continue
                    src_idx, source = res
                    dim = len(source.center)
                    clone = _copy.deepcopy(source)
                    clone.center = [
                        source.center[i] + k * (offset[i] if i < len(offset) else 0.0)
                        for i in range(dim)
                    ]
                    idx = self._add_avatar_no_validate(clone)
                    serie_indices.append(idx)

                # Stocker les avatar_ids des copies
                serie_ids = [self.state.avatars[i].avatar_id for i in serie_indices]
                grp = f"{prefix}_copie_{k}"
                self.state.avatar_groups.setdefault(grp, []).extend(serie_ids)
                result[grp] = serie_ids
        finally:
            self._batch_mode = False

        self.state_changed.emit()
        return result

    def _add_avatar_no_validate(self, avatar: Avatar, create_pylmgc: bool = True) -> int:
        if create_pylmgc:
            mat_obj = self._pylmgc_materials.get(avatar.material_name)
            mod_obj = self._pylmgc_models.get(avatar.model_name)
            if mat_obj and mod_obj:
                body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
                if body_obj is not None:
                    self._bodies_container.addAvatar(body_obj)
                self._pylmgc_bodies.append(body_obj)  # None ou objet valide
            else:
                self._pylmgc_bodies.append(None)
        else:
            self._pylmgc_bodies.append(None)
        self.state.avatars.append(avatar)
        if not self._batch_mode:
            self.state_changed.emit()
        return len(self.state.avatars) - 1

    # =========================================================================
    # LOIS DE CONTACT
    # =========================================================================

    def add_contact_law(self, law: ContactLaw) -> None:
        if self._find_contact_law(law.name):
            raise ValidationError(f"Une loi nommée '{law.name}' existe déjà")
        ContactLawValidator.validate_or_raise(law)
        law_obj = LMGC90Bridge.create_contact_law(law)
        self._contact_laws_container.addBehav(law_obj)
        self._pylmgc_laws[law.name] = law_obj
        self.state.contact_laws.append(law)
        self.state_changed.emit()

    def update_contact_law(self, old_name: str, law: ContactLaw) -> None:
        ContactLawValidator.validate_or_raise(law)
        old_law = self._find_contact_law(old_name)
        if not old_law:
            raise ValueError(f"Loi '{old_name}' introuvable")
        if old_name != law.name:
            if self._find_contact_law(law.name):
                raise ValueError(f"Une loi nommée '{law.name}' existe déjà")
            for rule in self.state.visibility_rules:
                if rule.behavior_name == old_name:
                    rule.behavior_name = law.name
        self._contact_laws_container.pop(old_name)
        self._pylmgc_laws.pop(old_name, None)
        law_obj = LMGC90Bridge.create_contact_law(law)
        self._contact_laws_container.addBehav(law_obj)
        self._pylmgc_laws[law.name] = law_obj
        idx = self.state.contact_laws.index(old_law)
        self.state.contact_laws[idx] = law

    def get_contact_law(self, name: str) -> Optional[ContactLaw]:
        return self._find_contact_law(name)

    def is_contact_law_used(self, name: str) -> tuple[bool, list[str]]:
        refs = []
        for i, rule in enumerate(self.state.visibility_rules):
            if rule.behavior_name == name:
                refs.append(f"Règle de visibilité #{i + 1}")
        return len(refs) > 0, refs

    def remove_contact_law(self, name: str) -> bool:
        law = self._find_contact_law(name)
        if not law:
            return False
        self.state.contact_laws.remove(law)
        self._contact_laws_container.pop(name)
        self._pylmgc_laws.pop(name, None)
        return True

    def get_contact_laws(self) -> List[ContactLaw]:
        return self.state.contact_laws.copy()

    def _find_contact_law(self, name: str) -> Optional[ContactLaw]:
        for law in self.state.contact_laws:
            if law.name == name:
                return law
        return None

    # =========================================================================
    # VISIBILITÉ
    # =========================================================================

    def add_visibility_rule(self, rule: VisibilityRule) -> None:
        behavior_obj = self._pylmgc_laws.get(rule.behavior_name)
        if not behavior_obj:
            raise ValueError(f"Loi '{rule.behavior_name}' introuvable")
        rule_obj = LMGC90Bridge.create_visibility_rule(rule, behavior_obj)
        self._visibility_container.addSeeTable(rule_obj)
        self.state.visibility_rules.append(rule)

    def update_visibility_rule(self, index: int, rule: VisibilityRule) -> None:
        if not (0 <= index < len(self.state.visibility_rules)):
            raise ValueError(f"Index {index} invalide")
        behavior_obj = self._pylmgc_laws.get(rule.behavior_name)
        if not behavior_obj:
            raise ValueError(f"Loi '{rule.behavior_name}' introuvable")
        self._visibility_container = pre.see_tables()
        self.state.visibility_rules[index] = rule
        for r in self.state.visibility_rules:
            behav = self._pylmgc_laws[r.behavior_name]
            rule_obj = LMGC90Bridge.create_visibility_rule(r, behav)
            self._visibility_container.addSeeTable(rule_obj)

    def get_visibility_rule(self, index: int) -> Optional[VisibilityRule]:
        if 0 <= index < len(self.state.visibility_rules):
            return self.state.visibility_rules[index]
        return None

    def remove_visibility_rule(self, index: int) -> bool:
        if 0 <= index < len(self.state.visibility_rules):
            self.state.visibility_rules.pop(index)
            return True
        return False

    def get_visibility_rules(self) -> List[VisibilityRule]:
        return self.state.visibility_rules.copy()

    # =========================================================================
    # OPÉRATIONS DOF
    # =========================================================================

    def apply_dof_operation(self, operation: DOFOperation) -> None:
        """Applique une opération DOF sur les avatars (sans sauvegarder)."""
        if operation.target_type == 'avatar':
            # target_value est désormais un avatar_id (str)
            res = self._find_avatar_by_id(operation.target_value)
            if res:
                idx, _ = res
                if 0 <= idx < len(self._pylmgc_bodies):
                    body = self._pylmgc_bodies[idx]
                    if body is not None:
                        LMGC90Bridge.apply_dof_operation(operation, body)
                        self._sync_avatar_position(idx, body)

        elif operation.target_type == 'group':
            group_name = operation.target_value
            avatar_ids = self.state.avatar_groups.get(group_name, [])
            for aid in avatar_ids:
                res = self._find_avatar_by_id(aid)
                if res:
                    idx, _ = res
                    if 0 <= idx < len(self._pylmgc_bodies):
                        body = self._pylmgc_bodies[idx]
                        if body is not None:
                            LMGC90Bridge.apply_dof_operation(operation, body)
                            self._sync_avatar_position(idx, body)

    def add_dof_operation(self, operation: DOFOperation) -> None:
        """Applique ET sauvegarde une opération DOF."""
        self.apply_dof_operation(operation)
        self.state.operations.append(operation)

    def get_dof_operations(self) -> List[DOFOperation]:
        return self.state.operations.copy()

    def get_dof_operation(self, index: int) -> DOFOperation:
        if index < 0 or index >= len(self.state.operations):
            raise IndexError(f"Index DOF invalide: {index}")
        return self.state.operations[index]

    def update_dof_operation(self, index: int, operation: DOFOperation) -> None:
        self.state.operations[index] = operation
        self.apply_dof_operation(operation)

    def remove_dof_operation(self, index: int) -> None:
        del self.state.operations[index]

    def _sync_avatar_position(self, index: int, body) -> None:
        if index >= len(self.state.avatars):
            return
        try:
            if hasattr(body, 'nodes') and len(body.nodes) > 0:
                new_center = body.nodes[1].coor
                self.state.avatars[index].center = new_center
        except Exception as e:
            print(f"⚠️ Erreur synchronisation position avatar {index}: {e}")

    # =========================================================================
    # BOUCLES
    # =========================================================================

    def generate_loop(self, loop: Loop) -> List[int]:
        """Génère des avatars selon une boucle (référence par avatar_id)."""
        res = self._find_avatar_by_id(loop.model_avatar_id)
        if res is None:
            raise ValueError(
                f"Avatar modèle '{loop.model_avatar_id}' introuvable"
            )
        _, model_avatar = res

        centers = LoopGenerator.generate_positions(loop)

        generated_indices = []
        for center in centers:
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
                contactors=model_avatar.contactors,
            )
            idx = self.add_avatar(new_avatar)
            generated_indices.append(idx)

        # Stocker les ids stables (non les positions)
        loop.generated_ids = [
            self.state.avatars[idx].avatar_id for idx in generated_indices
        ]

        if not self._is_loading:
            self.state.loops.append(loop)

        if loop.group_name:
            self.state.avatar_groups.setdefault(loop.group_name, []).extend(
                loop.generated_ids
            )

        return generated_indices

    def remove_loop(self, index: int) -> bool:
        if not (0 <= index < len(self.state.loops)):
            return False
        loop = self.state.loops[index]
        # Suppression par avatar_id (ordre quelconque, lookup frais à chaque fois)
        for aid in loop.generated_ids:
            res = self._find_avatar_by_id(aid)
            if res:
                self.remove_avatar(res[0])
        self.state.loops.pop(index)
        return True

    def get_loop(self, index: int) -> Optional[Loop]:
        if 0 <= index < len(self.state.loops):
            return self.state.loops[index]
        return None

    def update_loop(self, index: int, loop: Loop) -> None:
        if not (0 <= index < len(self.state.loops)):
            raise ValueError(f"Index {index} invalide")

        old_loop = self.state.loops[index]

        # Supprimer les avatars de l'ancienne boucle
        old_generated_ids = list(old_loop.generated_ids)
        for aid in old_generated_ids:
            res = self._find_avatar_by_id(aid)
            if res:
                self.remove_avatar(res[0])

        self.state.loops[index] = loop

        # Trouver l'avatar modèle par id
        res = self._find_avatar_by_id(loop.model_avatar_id)
        if res is None:
            raise ValueError(
                f"Avatar modèle '{loop.model_avatar_id}' introuvable"
            )
        _, model_avatar = res

        centers = LoopGenerator.generate_positions(loop)
        generated_indices = []
        for center in centers:
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
                contactors=model_avatar.contactors,
            )
            idx = self.add_avatar(new_avatar)
            generated_indices.append(idx)

        loop.generated_ids = [
            self.state.avatars[idx].avatar_id for idx in generated_indices
        ]

        # Mettre à jour les groupes
        if old_loop.group_name and old_loop.group_name in self.state.avatar_groups:
            old_ids = set(old_generated_ids)
            self.state.avatar_groups[old_loop.group_name] = [
                aid for aid in self.state.avatar_groups[old_loop.group_name]
                if aid not in old_ids
            ]

        if loop.group_name:
            self.state.avatar_groups.setdefault(loop.group_name, []).extend(
                loop.generated_ids
            )

    # =========================================================================
    # GRANULOMÉTRIE
    # =========================================================================

    def generate_granulo(self, config: GranuloGeneration) -> List[int]:
        nb_particles, coordinates, radii = GranuloGenerator.generate(config)

        generated_indices = []
        prev_batch = self._batch_mode
        self._batch_mode = True
        try:
            for i in range(nb_particles):
                center = coordinates[i].tolist()
                radius = float(radii[i])
                avatar = Avatar(
                    avatar_type=AvatarType(config.avatar_type),
                    center=center,
                    material_name=config.material_name,
                    model_name=config.model_name,
                    color=config.color,
                    origin=AvatarOrigin.GRANULO,
                    radius=radius,
                )
                idx = self.add_avatar(avatar)
                generated_indices.append(idx)
        finally:
            self._batch_mode = prev_batch

        # Stocker les ids stables
        config.generated_ids = [
            self.state.avatars[idx].avatar_id for idx in generated_indices
        ]

        if not self._is_loading:
            self.state.granulo_generations.append(config)

        if config.group_name:
            self.state.avatar_groups.setdefault(config.group_name, []).extend(
                config.generated_ids
            )

        return generated_indices

    def remove_granulo(self, index: int) -> bool:
        if not (0 <= index < len(self.state.granulo_generations)):
            return False
        granulo = self.state.granulo_generations[index]
        for aid in granulo.generated_ids:
            res = self._find_avatar_by_id(aid)
            if res:
                self.remove_avatar(res[0])
        self.state.granulo_generations.pop(index)
        return True

    def get_granulo(self, index: int) -> Optional[GranuloGeneration]:
        if 0 <= index < len(self.state.granulo_generations):
            return self.state.granulo_generations[index]
        return None

    def create_granulo_avatar(
        self, center: list, radius: float, config: GranuloGeneration
    ) -> int:
        avatar = Avatar(
            avatar_type=AvatarType(config.avatar_type),
            center=center,
            material_name=config.material_name,
            model_name=config.model_name,
            color=config.color,
            origin=AvatarOrigin.GRANULO,
            radius=radius,
        )
        return self.add_avatar(avatar)

    def finalize_granulo(self, config: GranuloGeneration, indices: List[int]) -> None:
        """Finalise la génération granulo (appelé depuis le thread UI)."""
        config.generated_ids = [
            self.state.avatars[i].avatar_id for i in indices
        ]
        if not self._is_loading:
            self.state.granulo_generations.append(config)
        if config.group_name:
            self.state.avatar_groups.setdefault(config.group_name, []).extend(
                config.generated_ids
            )

    # =========================================================================
    # FACTORY AVATARS
    # =========================================================================

    def load_factory_avatars_from_json(
        self, json_path: str = 'factory_avatars_metadata.json'
    ) -> List[int]:
        from ..core.particle_factory import (
            load_factory_avatars_from_json,
            create_avatars_from_factory_metadata,
        )
        try:
            metadata = load_factory_avatars_from_json(json_path)
        except FileNotFoundError as e:
            print(f"⚠ Impossible de charger factory avatars: {e}")
            return []

        avatars_to_add = create_avatars_from_factory_metadata(metadata)
        if not avatars_to_add:
            print("⚠ Aucun avatar à créer depuis le JSON de factory")
            return []

        was_batch = self._batch_mode
        self._batch_mode = True
        try:
            indices = []
            for avatar in avatars_to_add:
                idx = self.add_avatar(avatar, create_pylmgc=False)
                indices.append(idx)
            self.state_changed.emit()
            print(f'✅ {len(indices)} factory avatar(s) créé(s)')
            return indices
        finally:
            self._batch_mode = was_batch

    # =========================================================================
    # BOUCLES FOR
    # =========================================================================

    def generate_for_loop(self, for_loop: ForLoop) -> List[int]:
        """
        Génère des éléments selon une boucle For.
        Les avatars produits sont référencés par avatar_id dans generated_refs.
        Les matériaux/modèles restent référencés par position (inchangé).
        """
        from ..utils.safe_eval import SafeEvaluator
        from ..core.generators import GranuloGenerator
        import math

        generated_indices = []
        evaluator = SafeEvaluator()

        base_context = {
            'math': math, 'sqrt': math.sqrt, 'pi': math.pi, 'e': math.e,
            'abs': abs, 'min': min, 'max': max, 'sum': sum, 'len': len,
            'str': str, 'int': int, 'float': float,
        }

        # ── Cas granulo ────────────────────────────────────────────────────────
        if for_loop.target_type == 'granulo':
            evaluator.allowed_names = base_context
            start = evaluator.eval_expression(for_loop.start_expr)
            end   = evaluator.eval_expression(for_loop.end_expr)
            step  = evaluator.eval_expression(for_loop.step_expr)

            tc       = for_loop.template_config
            loop_var = for_loop.loop_var

            def _ev(val, ctx):
                if not isinstance(val, str):
                    return val
                evaluator.allowed_names = ctx
                try:
                    return evaluator.eval_expression(val)
                except Exception:
                    return val

            try:
                base_config = GranuloGeneration(
                    nb_particles   = int(tc.get('nb_particles', 50)),
                    radius_min     = float(tc.get('radius_min', 0.01)),
                    radius_max     = float(tc.get('radius_max', 0.05)),
                    container_type = str(tc.get('container_type', 'Box2D')),
                    container_params={k: float(v) for k, v in tc.get('container_params', {}).items()},
                    material_name  = str(tc.get('material_name', '')),
                    model_name     = str(tc.get('model_name', '')),
                    avatar_type    = str(tc.get('avatar_type', 'rigidDisk')),
                    color          = str(tc.get('color', 'BLUEx')),
                    seed           = tc.get('seed'),
                    group_name     = for_loop.group_name,
                )
            except Exception as exc:
                raise ValueError(f"Erreur dans le template granulo : {exc}")

            nb_p, coords_ref, radii_ref = GranuloGenerator.generate(base_config)

            av_type_obj = AvatarType(base_config.avatar_type)

            prev_batch       = self._batch_mode
            self._batch_mode = True
            try:
                current = start
                while (step > 0 and current < end) or (step < 0 and current > end):
                    ctx    = {**base_context, loop_var: current, 'i': current}
                    origin = list(_ev(tc.get('origin', '[0.0, 0.0]'), ctx))
                    for k in range(nb_p):
                        coord  = coords_ref[k].tolist()
                        center = [
                            coord[j] + (origin[j] if j < len(origin) else 0.0)
                            for j in range(len(coord))
                        ]
                        avatar = Avatar(
                            avatar_type   = av_type_obj,
                            center        = center,
                            material_name = base_config.material_name,
                            model_name    = base_config.model_name,
                            color         = base_config.color,
                            origin        = AvatarOrigin.GRANULO,
                            radius        = float(radii_ref[k]),
                        )
                        idx = self.add_avatar(avatar)
                        generated_indices.append(idx)
                    current += step
            finally:
                self._batch_mode = prev_batch

            # Stocker les ids stables
            for_loop.generated_refs = [
                self.state.avatars[idx].avatar_id for idx in generated_indices
            ]
            if not self._is_loading:
                self.state.for_loops.append(for_loop)
            if for_loop.group_name:
                self.state.avatar_groups.setdefault(
                    for_loop.group_name, []
                ).extend(for_loop.generated_refs)
            self.state_changed.emit()
            return generated_indices

        # ── Boucle For classique ───────────────────────────────────────────────
        evaluator.allowed_names = base_context
        start = evaluator.eval_expression(for_loop.start_expr)
        end   = evaluator.eval_expression(for_loop.end_expr)
        step  = evaluator.eval_expression(for_loop.step_expr)

        loop_var = for_loop.loop_var
        current  = start

        while (step > 0 and current < end) or (step < 0 and current > end):
            context = {**base_context, loop_var: current}
            evaluator.allowed_names = context

            evaluated_config = {}
            for key, value in for_loop.template_config.items():
                if isinstance(value, str):
                    try:
                        evaluated_config[key] = evaluator.eval_expression(value)
                    except (ValueError, NameError, SyntaxError):
                        if any(op in value for op in [
                            '+', '-', '*', '/', '(', '[',
                            'str(', 'int(', 'float(', 'math.',
                        ]):
                            raise
                        else:
                            evaluated_config[key] = value
                else:
                    evaluated_config[key] = value

            if for_loop.target_type == 'avatar':
                avatar = Avatar(
                    avatar_type   = AvatarType(evaluated_config['avatar_type']),
                    center        = evaluated_config['center'],
                    material_name = evaluated_config.get('material_name', 'TDURx'),
                    model_name    = evaluated_config.get('model_name', 'rigid'),
                    color         = evaluated_config.get('color', 'BLUEx'),
                    origin        = AvatarOrigin.LOOP,
                    radius        = evaluated_config.get('radius'),
                    axis          = evaluated_config.get('axis'),
                    vertices      = evaluated_config.get('vertices'),
                    nb_vertices   = evaluated_config.get('nb_vertices'),
                    generation_type = evaluated_config.get('generation_type'),
                    is_hollow     = evaluated_config.get('is_hollow', False),
                    wall_params   = evaluated_config.get('wall_params'),
                    contactors    = evaluated_config.get('contactors'),
                )
                idx = self.add_avatar(avatar)
                generated_indices.append(idx)

            elif for_loop.target_type == 'material':
                from ..core.models import Material, MaterialType
                material = Material(
                    name          = evaluated_config['name'],
                    material_type = MaterialType(evaluated_config.get('material_type', 'RIGID')),
                    density       = evaluated_config.get('density', 2800),
                    properties    = evaluated_config.get('properties', {}),
                )
                self.add_material(material)
                generated_indices.append(len(self.state.materials) - 1)

            elif for_loop.target_type == 'model':
                from ..core.models import Model
                model = Model(
                    name      = evaluated_config['name'],
                    physics   = evaluated_config.get('physics', 'MECAx'),
                    element   = evaluated_config.get('element', 'Rxx2D'),
                    dimension = evaluated_config.get('dimension', 2),
                    options   = evaluated_config.get('options', {}),
                )
                self.add_model(model)
                generated_indices.append(len(self.state.models) - 1)

            current += step

        # Stocker refs : avatar_id pour 'avatar', position pour material/model
        if for_loop.target_type == 'avatar':
            for_loop.generated_refs = [
                self.state.avatars[idx].avatar_id for idx in generated_indices
            ]
        else:
            for_loop.generated_refs = generated_indices

        if not self._is_loading:
            self.state.for_loops.append(for_loop)

        if for_loop.group_name and for_loop.target_type in ('avatar', 'granulo'):
            self.state.avatar_groups.setdefault(
                for_loop.group_name, []
            ).extend(for_loop.generated_refs)

        return generated_indices

    def update_for_loop(self, index: int, for_loop: ForLoop) -> None:
        if not (0 <= index < len(self.state.for_loops)):
            raise ValueError(f"Index {index} invalide")

        old_for_loop = self.state.for_loops[index]

        # Supprimer les anciens éléments générés
        if old_for_loop.target_type == 'avatar':
            for aid in old_for_loop.generated_refs:
                res = self._find_avatar_by_id(aid)
                if res:
                    self.remove_avatar(res[0])
        elif old_for_loop.target_type == 'material':
            for elem_idx in sorted(old_for_loop.generated_refs, reverse=True):
                if elem_idx < len(self.state.materials):
                    self.remove_material(self.state.materials[elem_idx].name)
        elif old_for_loop.target_type == 'model':
            for elem_idx in sorted(old_for_loop.generated_refs, reverse=True):
                if elem_idx < len(self.state.models):
                    self.remove_model(self.state.models[elem_idx].name)

        self.state.for_loops[index] = for_loop

        # Régénérer (copie de la logique de generate_for_loop, sans append)
        from ..utils.safe_eval import SafeEvaluator
        import math

        generated_indices = []
        evaluator = SafeEvaluator()
        base_context = {
            'math': math, 'sqrt': math.sqrt, 'pi': math.pi, 'e': math.e,
            'abs': abs, 'min': min, 'max': max, 'sum': sum, 'len': len,
            'str': str, 'int': int, 'float': float,
        }
        evaluator.allowed_names = base_context
        start = evaluator.eval_expression(for_loop.start_expr)
        end   = evaluator.eval_expression(for_loop.end_expr)
        step  = evaluator.eval_expression(for_loop.step_expr)
        loop_var = for_loop.loop_var
        current  = start

        while (step > 0 and current < end) or (step < 0 and current > end):
            context = {**base_context, loop_var: current}
            evaluator.allowed_names = context
            evaluated_config = {}
            for key, value in for_loop.template_config.items():
                if isinstance(value, str):
                    evaluated_config[key] = evaluator.eval_expression(value)
                else:
                    evaluated_config[key] = value

            if for_loop.target_type == 'avatar':
                avatar = Avatar(
                    avatar_type   = AvatarType(evaluated_config['avatar_type']),
                    center        = evaluated_config['center'],
                    material_name = evaluated_config.get('material_name', 'TDURx'),
                    model_name    = evaluated_config.get('model_name', 'rigid'),
                    color         = evaluated_config.get('color', 'BLUEx'),
                    origin        = AvatarOrigin.LOOP,
                    radius        = evaluated_config.get('radius'),
                    axis          = evaluated_config.get('axis'),
                    vertices      = evaluated_config.get('vertices'),
                    nb_vertices   = evaluated_config.get('nb_vertices'),
                    generation_type = evaluated_config.get('generation_type'),
                    is_hollow     = evaluated_config.get('is_hollow', False),
                    wall_params   = evaluated_config.get('wall_params'),
                    contactors    = evaluated_config.get('contactors'),
                )
                idx = self.add_avatar(avatar)
                generated_indices.append(idx)
            elif for_loop.target_type == 'material':
                from ..core.models import Material, MaterialType
                material = Material(
                    name          = evaluated_config['name'],
                    material_type = MaterialType(evaluated_config.get('material_type', 'RIGID')),
                    density       = evaluated_config.get('density', 2800),
                    properties    = evaluated_config.get('properties', {}),
                )
                self.add_material(material)
                generated_indices.append(len(self.state.materials) - 1)
            elif for_loop.target_type == 'model':
                from ..core.models import Model
                model = Model(
                    name      = evaluated_config['name'],
                    physics   = evaluated_config.get('physics', 'MECAx'),
                    element   = evaluated_config.get('element', 'Rxx2D'),
                    dimension = evaluated_config.get('dimension', 2),
                    options   = evaluated_config.get('options', {}),
                )
                self.add_model(model)
                generated_indices.append(len(self.state.models) - 1)

            current += step

        if for_loop.target_type == 'avatar':
            for_loop.generated_refs = [
                self.state.avatars[idx].avatar_id for idx in generated_indices
            ]
        else:
            for_loop.generated_refs = generated_indices

        # Mettre à jour les groupes
        if old_for_loop.group_name and old_for_loop.group_name in self.state.avatar_groups:
            if old_for_loop.target_type == 'avatar':
                old_ids = set(old_for_loop.generated_refs)
                self.state.avatar_groups[old_for_loop.group_name] = [
                    aid for aid in self.state.avatar_groups[old_for_loop.group_name]
                    if aid not in old_ids
                ]

        if for_loop.group_name and for_loop.target_type == 'avatar':
            self.state.avatar_groups.setdefault(for_loop.group_name, []).extend(
                for_loop.generated_refs
            )

    def remove_for_loop(self, index: int) -> bool:
        if not (0 <= index < len(self.state.for_loops)):
            return False
        for_loop = self.state.for_loops[index]

        if for_loop.target_type == 'avatar':
            for aid in for_loop.generated_refs:
                res = self._find_avatar_by_id(aid)
                if res:
                    self.remove_avatar(res[0])
        elif for_loop.target_type == 'material':
            for elem_idx in sorted(for_loop.generated_refs, reverse=True):
                if elem_idx < len(self.state.materials):
                    self.remove_material(self.state.materials[elem_idx].name)
        elif for_loop.target_type == 'model':
            for elem_idx in sorted(for_loop.generated_refs, reverse=True):
                if elem_idx < len(self.state.models):
                    self.remove_model(self.state.models[elem_idx].name)

        self.state.for_loops.pop(index)
        return True

    def get_for_loop(self, index: int) -> Optional[ForLoop]:
        if 0 <= index < len(self.state.for_loops):
            return self.state.for_loops[index]
        return None

    # =========================================================================
    # POST-TRAITEMENT
    # =========================================================================

    def add_postpro_command(self, command) -> None:
        rigid_set = None

        if command.target_type == 'avatar':
            # target_value est un avatar_id
            res = self._find_avatar_by_id(command.target_value)
            if res:
                idx, _ = res
                if 0 <= idx < len(self._pylmgc_bodies):
                    body = self._pylmgc_bodies[idx]
                    if body is not None:
                        rigid_set = [body]

        elif command.target_type == 'group':
            group_name = command.target_value
            avatar_ids = self.state.avatar_groups.get(group_name, [])
            rigid_set  = []
            for aid in avatar_ids:
                res = self._find_avatar_by_id(aid)
                if res:
                    idx, _ = res
                    if (0 <= idx < len(self._pylmgc_bodies)
                            and self._pylmgc_bodies[idx] is not None):
                        rigid_set.append(self._pylmgc_bodies[idx])

        if rigid_set:
            cmd = pre.postpro_command(
                name=command.name, step=command.step, rigid_set=rigid_set
            )
        else:
            cmd = pre.postpro_command(name=command.name, step=command.step)

        self._postpro_container.addCommand(cmd)
        self.state.postpro_commands.append(command)

    def remove_postpro_command(self, index: int) -> bool:
        if 0 <= index < len(self.state.postpro_commands):
            self.state.postpro_commands.pop(index)
            return True
        return False

    def update_postpro_command(self, index: int, command) -> None:
        if not (0 <= index < len(self.state.postpro_commands)):
            raise ValueError(f"Index {index} invalide")
        self._postpro_container = pre.postpro_commands()
        self.state.postpro_commands[index] = command
        for cmd in self.state.postpro_commands:
            rigid_set = None
            if cmd.target_type == 'avatar':
                res = self._find_avatar_by_id(cmd.target_value)
                if res:
                    idx, _ = res
                    if 0 <= idx < len(self._pylmgc_bodies):
                        rigid_set = [self._pylmgc_bodies[idx]]
            elif cmd.target_type == 'group':
                group_name = cmd.target_value
                avatar_ids = self.state.avatar_groups.get(group_name, [])
                rigid_set  = []
                for aid in avatar_ids:
                    res = self._find_avatar_by_id(aid)
                    if res:
                        idx, _ = res
                        if (0 <= idx < len(self._pylmgc_bodies)
                                and self._pylmgc_bodies[idx] is not None):
                            rigid_set.append(self._pylmgc_bodies[idx])
            if rigid_set:
                cmd_obj = pre.postpro_command(
                    name=cmd.name, step=cmd.step, rigid_set=rigid_set
                )
            else:
                cmd_obj = pre.postpro_command(name=cmd.name, step=cmd.step)
            self._postpro_container.addCommand(cmd_obj)

    def get_postpro_command(self, index: int):
        if 0 <= index < len(self.state.postpro_commands):
            return self.state.postpro_commands[index]
        return None

    # =========================================================================
    # GÉNÉRATION DATBOX
    # =========================================================================

    def generate_datbox(self, output_path: Path) -> None:
        pre.writeDatbox(
            dim=self.state.dimension,
            mats=self._materials_container,
            mods=self._models_container,
            bodies=self._bodies_container,
            tacts=self._contact_laws_container,
            sees=self._visibility_container,
            post=self._postpro_container,
            datbox_path=str(output_path),
        )

    # =========================================================================
    # UTILITAIRES PRIVÉS
    # =========================================================================

    def _restore_factory_avatars(self) -> None:
        """
        Restaure les factory avatars sauvegardés après _rebuild_pylmgc_objects.

        Pourquoi après et pas avant ?
        ─────────────────────────────
        _rebuild_pylmgc_objects reconstruit state.avatars + _pylmgc_bodies en
        parallèle (1 entrée pylmgc par avatar). Si on ajoutait les factory
        avatars avant le rebuild, les boucles/granulos ajoutés ensuite
        décaleraient les indices et _pylmgc_bodies[i] ne correspondrait plus
        à state.avatars[i] pour i > nombre d'avatars manuels.

        En ajoutant les factory avatars APRÈS, on garantit :
          state.avatars     = [manuels | loops | granulos | factory]
          _pylmgc_bodies    = [manuels | loops | granulos | None…  ]
        L'alignement 1:1 est maintenu. Les None sont gérés proprement par
        toutes les méthodes du contrôleur (check `if body is not None`).
        """
        factory_avs = getattr(self.state, '_factory_avatars_staged', [])
        if not factory_avs:
            return

        for av in factory_avs:
            self.state.avatars.append(av)
            # Pas d'objet pylmgc pour les factory avatars (ils viennent du
            # DATBOX généré par pre.py) — placeholder None pour l'alignement
            self._pylmgc_bodies.append(None)

        # Nettoyer le champ temporaire
        self.state._factory_avatars_staged = []

    def _reset_containers(self) -> None:
        self._materials_container = pre.materials()
        self._models_container    = pre.models()
        self._bodies_container    = pre.avatars()
        self._contact_laws_container = pre.tact_behavs()
        self._visibility_container = pre.see_tables()
        self._postpro_container   = pre.postpro_commands()
        self._pylmgc_materials.clear()
        self._pylmgc_models.clear()
        self._pylmgc_bodies.clear()
        self._pylmgc_laws.clear()

    def _rebuild_pylmgc_objects(self) -> None:
        """Reconstruit tous les objets pylmgc90 depuis l'état chargé."""
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
        regeneration_errors = []
        manual_avatars = [av for av in self.state.avatars if av.origin == AvatarOrigin.MANUAL]
        for avatar in manual_avatars:
            mat_obj = self._pylmgc_materials.get(avatar.material_name)
            mod_obj = self._pylmgc_models.get(avatar.model_name)
            if not mat_obj:
                raise ValueError(
                    f"Matériau '{avatar.material_name}' introuvable lors de la reconstruction"
                )
            if not mod_obj:
                raise ValueError(
                    f"Modèle '{avatar.model_name}' introuvable lors de la reconstruction"
                )
            body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
            if body_obj is None:
                self._pylmgc_bodies.append(None)
                regeneration_errors.append(
                    f"Corps déformable '{avatar.material_name}/{avatar.model_name}' : "
                    f"mesh_params absent — recréez-le via le wizard."
                )
                continue
            self._bodies_container.addAvatar(body_obj)
            self._pylmgc_bodies.append(body_obj)

        # ── Nettoyer les groupes AVANT régénération ──────────────────────────
        # On retire uniquement les ids d'avatars qui n'existent plus ET qui ne
        # sont pas des factory avatars en attente de restauration.
        # Sans ce filtre, les factory avatar_ids (ex: "factory_…") seraient
        # supprimés des groupes car les factory avatars ne sont pas encore
        # dans state.avatars à ce stade.
        existing_ids    = {av.avatar_id for av in self.state.avatars}
        staged_fac_ids  = {av.avatar_id
                           for av in getattr(self.state, '_factory_avatars_staged', [])}
        valid_ids = existing_ids | staged_fac_ids
        for grp_name in list(self.state.avatar_groups.keys()):
            self.state.avatar_groups[grp_name] = [
                aid for aid in self.state.avatar_groups[grp_name]
                if aid in valid_ids
            ]

        # Régénérer boucles (utilise model_avatar_id)
        for i, loop in enumerate(self.state.loops):
            try:
                if not loop.model_avatar_id:
                    raise ValueError("Avatar modèle non défini (model_avatar_id vide)")
                self.generate_loop(loop)
            except Exception as e:
                regeneration_errors.append(f"Boucle {i + 1}: {e}")

        # Régénérer granulo
        for i, granulo in enumerate(self.state.granulo_generations):
            try:
                self.generate_granulo(granulo)
            except Exception as e:
                regeneration_errors.append(f"Granulo {i + 1}: {e}")

        # Régénérer boucles For
        for i, for_loop in enumerate(self.state.for_loops):
            try:
                self.generate_for_loop(for_loop)
            except Exception as e:
                regeneration_errors.append(f"Boucle For {i + 1}: {e}")

        if regeneration_errors:
            existing = getattr(self.state, 'load_warnings', [])
            self.state.load_warnings = existing + regeneration_errors

        # Recréer lois de contact
        for law in self.state.contact_laws:
            law_obj = LMGC90Bridge.create_contact_law(law)
            self._contact_laws_container.addBehav(law_obj)
            self._pylmgc_laws[law.name] = law_obj

        # Recréer visibilité
        for rule in self.state.visibility_rules:
            behavior_obj = self._pylmgc_laws.get(rule.behavior_name)
            if not behavior_obj:
                raise ValueError(
                    f"Loi '{rule.behavior_name}' introuvable lors de la reconstruction"
                )
            rule_obj = LMGC90Bridge.create_visibility_rule(rule, behavior_obj)
            self._visibility_container.addSeeTable(rule_obj)

        # Réappliquer opérations DOF
        for op in self.state.operations:
            self.apply_dof_operation(op)