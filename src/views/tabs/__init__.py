# ============================================================================
# Initialisation du package tabs
# ============================================================================
"""
Onglets de l'interface utilisateur.
Chaque onglet est responsable d'une fonctionnalité spécifique.
"""
from .material_tab import MaterialTab
from .model_tab import ModelTab
from .avatar_tab import AvatarTab
from .empty_avatar_tab import EmptyAvatarTab
from .avatar_library_tab import AvatarLibraryTab
from .loop_tab import LoopTab
from .granulo_tab import GranuloTab
from .dof_tab import DOFTab
from .contact_tab import ContactTab
from .visibility_tab import VisibilityTab
from .postpro_tab import PostProTab
from .compute_tab import ComputeTab
from .viewer_tab import ViewerTab

__all__ = [
    'MaterialTab', 'ModelTab', 'AvatarTab', 'EmptyAvatarTab', 'AvatarLibraryTab'
    'LoopTab', 'GranuloTab', 'DOFTab', 'ContactTab',
    'VisibilityTab', 'PostProTab', 'ComputeTab', 'ViewerTab'
]