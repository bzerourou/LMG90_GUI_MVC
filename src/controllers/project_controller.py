# ============================================================================
# project_controller.py  —  Contrôleur principal LMGC90_GUI
# ============================================================================
"""
Contrôleur principal : hérite de tous les mixins de domaine.

Architecture
────────────
ProjectController(QObject, mixins…)

  QObject             → signaux PyQt6
  IOMixin             → new/save/load/datbox
  MaterialsMixin      → CRUD matériaux
  ModelsMixin         → CRUD modèles
  AvatarsMixin        → CRUD avatars + duplication
  ContactLawsMixin    → CRUD lois de contact
  VisibilityMixin     → tables de visibilité
  DOFMixin            → opérations DOF
  LoopsMixin          → boucles géométriques
  GranuloMixin        → génération granulométrique
  FactoryMixin        → chargement avatars factory
  ForLoopsMixin       → boucles For génériques
  PostProMixin        → post-traitement
  BaseMixin           → utilitaires + _rebuild + _restore

QObject doit être en première position dans le MRO pour que pyqtSignal
fonctionne. Les mixins n'héritent que de object (pas de QObject), ce qui
garantit la compatibilité du MRO Python.
"""
from typing import Optional, Dict, Any, List
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from pylmgc90 import pre

from ..core.models import ProjectState

# Mixins de domaine
from .io_mixin import IOMixin
from .materials_mixin import MaterialsMixin
from .models_mixin import ModelsMixin
from .avatars_mixin import AvatarsMixin
from .contact_laws_mixin import ContactLawsMixin
from .visibility_mixin import VisibilityMixin
from .dof_mixin import DOFMixin
from .loops_mixin import LoopsMixin
from .granulo_mixin import GranuloMixin
from .factory_mixin import FactoryMixin
from .for_loops_mixin import ForLoopsMixin
from .postpro_mixin import PostProMixin
from .base_mixin import BaseMixin

class ProjectController(
    QObject,
    IOMixin,
    MaterialsMixin,
    ModelsMixin,
    AvatarsMixin,
    ContactLawsMixin,
    VisibilityMixin,
    DOFMixin,
    LoopsMixin,
    GranuloMixin,
    FactoryMixin,
    ForLoopsMixin,
    PostProMixin,
    BaseMixin,
):
    """Contrôleur principal : assemble tous les mixins de domaine."""

    state_changed = pyqtSignal()

    def __init__(self, state: Optional[ProjectState] = None):
        super().__init__()

        self.state: ProjectState = state or ProjectState(name="Nouveau_Projet")
        self.project_path: Optional[Path] = None
        self._is_loading: bool  = False
        self._batch_mode: bool  = False

        # ── Conteneurs pylmgc90 ───────────────────────────────────────────
        self._materials_container    = pre.materials()
        self._models_container       = pre.models()
        self._bodies_container       = pre.avatars()
        self._contact_laws_container = pre.tact_behavs()
        self._visibility_container   = pre.see_tables()
        self._postpro_container      = pre.postpro_commands()

        # ── Objets pylmgc90 créés ─────────────────────────────────────────
        self._pylmgc_materials: Dict[str, Any] = {}
        self._pylmgc_models:    Dict[str, Any] = {}
        self._pylmgc_bodies:    List[Any]       = []
        self._pylmgc_laws:      Dict[str, Any] = {}
