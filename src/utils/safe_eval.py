# ============================================================================
# Évaluation sécurisée d'expressions
# ============================================================================
"""
Utilitaires pour évaluer des expressions de manière sécurisée.
Remplace les eval() dangereux.

=== REFACTOR "avatar_id stable" ===
- AvatarProxy expose désormais la propriété `.avatar_id`
- GroupProxy.__getitem__ résout des avatar_ids (str) et non plus des
  positions entières dans state.avatars.
"""
import ast
import math
import numpy as np
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..controllers.project_controller import ProjectController

from ..core.models import AvatarType, AvatarOrigin


# ============================================================================
# Proxies de nœuds
# ============================================================================

class NodeProxy:
    """
    Simule un nœud pylmgc90.
    pylmgc90 numérote les nœuds à partir de 1 : nodes[1] = nœud principal.
    On supporte donc nodes[0] (Python) ET nodes[1] (convention pylmgc90).
    """
    __slots__ = ('coor',)

    def __init__(self, coor):
        self.coor = list(coor) if coor is not None else []

    def __getitem__(self, key):
        return self.coor[key]

    def __repr__(self):
        return f"NodeProxy(coor={self.coor})"


class _NodeList:
    """
    Liste de nœuds supportant l'indexation depuis 0 ET depuis 1.
      nodes[0]  : nœud principal (convention Python)
      nodes[1]  : nœud principal (convention pylmgc90, number=1)
      nodes[i]  : pour les avatars polygonaux, le i-ième sommet
    """

    def __init__(self, avatar):
        self._list: List[NodeProxy] = []
        if avatar.vertices:
            for v in avatar.vertices:
                self._list.append(NodeProxy(v))
        else:
            self._list.append(NodeProxy(avatar.center))

    def __getitem__(self, idx: int) -> NodeProxy:
        if idx == 0:
            return self._list[0]
        if idx >= 1:
            real = idx - 1
            if real < len(self._list):
                return self._list[real]
            raise IndexError(
                f"Nœud {idx} invalide (cet avatar a {len(self._list)} nœud(s))"
            )
        raise IndexError(f"Index de nœud invalide : {idx}")

    def __len__(self):
        return len(self._list)

    def __iter__(self):
        return iter(self._list)


# ============================================================================
# AvatarProxy
# ============================================================================

class AvatarProxy:
    """
    Proxy d'accès à un avatar individuel.

    Propriétés exposées (toutes en lecture) :
      .avatar_id       - identifiant stable (uuid hex) ← NOUVEAU
      .center          - [x, y] ou [x, y, z]
      .x, .y, .z       - coordonnées individuelles
      .radius          - rayon (None si non applicable)
      .color           - couleur pylmgc90
      .material_name   - nom du matériau
      .model_name      - nom du modèle
      .avatar_type     - chaîne (ex: 'rigidDisk')
      .origin          - chaîne (ex: 'manual', 'loop', 'granulo')
      .generation_type - chaîne (ex: 'regular', 'full', 'bevel') ou None
      .is_hollow       - bool
      .nb_vertices     - int ou None
      .vertices        - liste de sommets ou None
      .axis            - dict axe1/axe2/axe3 ou None
      .contactors      - liste de contacteurs
      .wall_params     - dict brut des paramètres de mur
      .brick_lx        - alias wall_params['l']
      .brick_ly        - alias wall_params['h']
      .brick_lz        - alias wall_params['lz']
      .mesh_params     - dict paramètres de maillage ou None
      .nodes           - NodeList (nodes[1] = nœud principal comme pylmgc90)
      .index           - indice dans state.avatars
    """

    def __init__(self, avatar, index: int):
        self._av    = avatar
        self._idx   = index
        self._nodes = None

    # ── Identifiant stable ────────────────────────────────────────────────────

    @property
    def avatar_id(self) -> str:
        """Identifiant stable de l'avatar (uuid hex, jamais modifié)."""
        return self._av.avatar_id

    # ── Géométrie ─────────────────────────────────────────────────────────────

    @property
    def center(self):
        return list(self._av.center) if self._av.center else []

    @property
    def x(self):
        c = self._av.center
        return c[0] if c and len(c) > 0 else None

    @property
    def y(self):
        c = self._av.center
        return c[1] if c and len(c) > 1 else None

    @property
    def z(self):
        c = self._av.center
        return c[2] if c and len(c) > 2 else None

    @property
    def radius(self):
        return self._av.radius

    # ── Apparence ─────────────────────────────────────────────────────────────

    @property
    def color(self):
        return self._av.color

    # ── Matériau / modèle ─────────────────────────────────────────────────────

    @property
    def material_name(self):
        return self._av.material_name

    @property
    def model_name(self):
        return self._av.model_name

    # ── Type / origine ────────────────────────────────────────────────────────

    @property
    def avatar_type(self):
        return self._av.avatar_type.value

    @property
    def origin(self):
        return self._av.origin.value

    # ── Géométrie avancée ─────────────────────────────────────────────────────

    @property
    def generation_type(self):
        return self._av.generation_type

    @property
    def is_hollow(self):
        return self._av.is_hollow

    @property
    def nb_vertices(self):
        return self._av.nb_vertices

    @property
    def vertices(self):
        return self._av.vertices

    @property
    def axis(self):
        return self._av.axis

    @property
    def contactors(self):
        return self._av.contactors

    @property
    def wall_params(self):
        return self._av.wall_params or {}

    @property
    def brick_lx(self):
        """Longueur brique maçonnerie (alias wall_params['l'])."""
        wp = self._av.wall_params
        return wp.get('l') if wp else None

    @property
    def brick_ly(self):
        """Hauteur/profondeur brique maçonnerie (alias wall_params['h'])."""
        wp = self._av.wall_params
        return wp.get('h') if wp else None

    @property
    def brick_lz(self):
        """Hauteur 3D brique maçonnerie (alias wall_params['lz'])."""
        wp = self._av.wall_params
        return wp.get('lz') if wp else None

    @property
    def mesh_params(self):
        return self._av.mesh_params

    @property
    def index(self):
        return self._idx

    @property
    def nodes(self):
        if self._nodes is None:
            self._nodes = _NodeList(self._av)
        return self._nodes

    # ── Accès dict-like pour compatibilité ────────────────────────────────────

    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self):
        return (
            f"AvatarProxy(index={self._idx}, "
            f"id={self._av.avatar_id[:8]}…, "
            f"type={self.avatar_type}, center={self.center})"
        )


# ============================================================================
# AvatarCollectionProxy
# ============================================================================

class AvatarCollectionProxy:
    """
    Proxy d'accès à la collection complète des avatars.

    Usage :
        avatar[0]               - avatar par indice
        avatar[0].center        - centre
        avatar[0].nodes[1].coor - nœud principal (convention pylmgc90)
        avatar[0].avatar_id     - identifiant stable
        len(avatar)             - nombre d'avatars
        list(avatar)            - itérer sur tous les avatars
    """

    def __init__(self, controller: 'ProjectController'):
        self._ctrl = controller

    def __getitem__(self, index: int) -> AvatarProxy:
        avatars = self._ctrl.state.avatars
        if not isinstance(index, int):
            raise TypeError(
                f"L'index doit être un entier, reçu : {type(index).__name__}"
            )
        if index < 0 or index >= len(avatars):
            raise IndexError(
                f"Avatar index {index} invalide (0 à {len(avatars) - 1})"
            )
        return AvatarProxy(avatars[index], index)

    def __len__(self):
        return len(self._ctrl.state.avatars)

    def __iter__(self):
        for i, av in enumerate(self._ctrl.state.avatars):
            yield AvatarProxy(av, i)

    def __repr__(self):
        return f"AvatarCollectionProxy({len(self)} avatars)"


# ============================================================================
# GroupProxy
# ============================================================================

class GroupProxy:
    """
    Accès aux groupes d'avatars par nom.

    Les groupes stockent désormais des avatar_ids (str) et non plus des
    positions entières. Ce proxy résout chaque avatar_id vers l'AvatarProxy
    correspondant à sa position COURANTE dans state.avatars.

    Usage :
        group['mur_briques']             - liste d'AvatarProxy du groupe
        group['mur_briques'][0].center   - centre du premier avatar
        group['mur_briques'][0].avatar_id
        len(group['mur_briques'])        - taille du groupe
        list(group)                      - noms de tous les groupes
        'mur_briques' in group           - test d'existence
    """

    def __init__(self, controller: 'ProjectController'):
        self._ctrl = controller

    def __getitem__(self, name: str) -> List[AvatarProxy]:
        groups = getattr(self._ctrl.state, 'avatar_groups', {}) or {}
        if name not in groups:
            raise KeyError(
                f"Groupe '{name}' introuvable. "
                f"Groupes disponibles : {list(groups.keys())}"
            )
        avatar_ids = groups[name]          # List[str] — ids stables
        avatars    = self._ctrl.state.avatars

        # Construire le mapping id → index une seule fois pour ce groupe
        id_to_idx: Dict[str, int] = {av.avatar_id: i for i, av in enumerate(avatars)}

        result: List[AvatarProxy] = []
        for aid in avatar_ids:
            idx = id_to_idx.get(aid)
            if idx is not None:
                result.append(AvatarProxy(avatars[idx], idx))
            # Si l'avatar n'existe plus (supprimé), on le saute silencieusement
        return result

    def __iter__(self):
        groups = getattr(self._ctrl.state, 'avatar_groups', {}) or {}
        return iter(groups.keys())

    def __len__(self):
        return len(getattr(self._ctrl.state, 'avatar_groups', {}) or {})

    def __contains__(self, name: str):
        groups = getattr(self._ctrl.state, 'avatar_groups', {}) or {}
        return name in groups

    def __repr__(self):
        groups = getattr(self._ctrl.state, 'avatar_groups', {}) or {}
        return f"GroupProxy(groupes={list(groups.keys())})"


# ============================================================================
# MaterialProxy
# ============================================================================

class MaterialProxy:
    """
    Accès aux matériaux par nom.

    Usage :
        material['beton'].density
        material['beton'].material_type
        material['beton']['young']   - propriété personnalisée
    """

    def __init__(self, controller: 'ProjectController'):
        self._ctrl = controller

    def __getitem__(self, name: str) -> '_MaterialData':
        mat = self._ctrl.get_material(name)
        if mat is None:
            available = [m.name for m in self._ctrl.state.materials]
            raise KeyError(
                f"Matériau '{name}' introuvable. "
                f"Disponibles : {available}"
            )
        return _MaterialData(mat)

    def __repr__(self):
        names = [m.name for m in self._ctrl.state.materials]
        return f"MaterialProxy(matériaux={names})"


class _MaterialData:
    def __init__(self, mat):
        self._mat = mat

    @property
    def name(self):
        return self._mat.name

    @property
    def density(self):
        return self._mat.density

    @property
    def material_type(self):
        return self._mat.material_type.value

    def __getattr__(self, key):
        props = self._mat.properties or {}
        if key in props:
            return props[key]
        raise AttributeError(
            f"Matériau '{self._mat.name}' n'a pas de propriété '{key}'"
        )

    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self):
        return f"Material(name={self._mat.name}, density={self._mat.density})"


# ============================================================================
# ModelProxy
# ============================================================================

class ModelProxy:
    """
    Accès aux modèles par nom.

    Usage :
        model['rigid'].physics
        model['rigid'].element
        model['rigid'].dimension
    """

    def __init__(self, controller: 'ProjectController'):
        self._ctrl = controller

    def __getitem__(self, name: str) -> '_ModelData':
        mod = self._ctrl.get_model(name)
        if mod is None:
            available = [m.name for m in self._ctrl.state.models]
            raise KeyError(
                f"Modèle '{name}' introuvable. "
                f"Disponibles : {available}"
            )
        return _ModelData(mod)

    def __repr__(self):
        names = [m.name for m in self._ctrl.state.models]
        return f"ModelProxy(modèles={names})"


class _ModelData:
    def __init__(self, mod):
        self._mod = mod

    @property
    def name(self):
        return self._mod.name

    @property
    def physics(self):
        return self._mod.physics

    @property
    def element(self):
        return self._mod.element

    @property
    def dimension(self):
        return self._mod.dimension

    def __getattr__(self, key):
        opts = self._mod.options or {}
        if key in opts:
            return opts[key]
        raise AttributeError(
            f"Modèle '{self._mod.name}' n'a pas d'option '{key}'"
        )

    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self):
        return f"Model(name={self._mod.name}, physics={self._mod.physics})"


# ============================================================================
# Fonctions de filtrage
# ============================================================================

def _avatars_by_color(
    controller: 'ProjectController', color: str
) -> List[AvatarProxy]:
    """Retourne tous les avatars ayant la couleur donnée."""
    return [
        AvatarProxy(av, i)
        for i, av in enumerate(controller.state.avatars)
        if av.color == color
    ]


def _avatars_by_material(
    controller: 'ProjectController', material_name: str
) -> List[AvatarProxy]:
    """Retourne tous les avatars utilisant le matériau donné."""
    return [
        AvatarProxy(av, i)
        for i, av in enumerate(controller.state.avatars)
        if av.material_name == material_name
    ]


def _avatars_by_type(
    controller: 'ProjectController', avatar_type
) -> List[AvatarProxy]:
    """
    Retourne tous les avatars du type donné.
    Accepte une chaîne ('rigidDisk') ou un AvatarType.
    """
    if isinstance(avatar_type, AvatarType):
        avatar_type = avatar_type.value
    return [
        AvatarProxy(av, i)
        for i, av in enumerate(controller.state.avatars)
        if av.avatar_type.value == avatar_type
    ]


def _avatars_by_origin(
    controller: 'ProjectController', origin
) -> List[AvatarProxy]:
    """
    Retourne tous les avatars d'une origine donnée.
    Accepte une chaîne ('manual', 'loop', 'granulo') ou un AvatarOrigin.
    """
    if isinstance(origin, AvatarOrigin):
        origin = origin.value
    return [
        AvatarProxy(av, i)
        for i, av in enumerate(controller.state.avatars)
        if av.origin.value == origin
    ]


# ============================================================================
# Construction du contexte d'évaluation complet
# ============================================================================

def build_eval_context(
    controller: 'ProjectController',
    extra_vars: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Construit le contexte d'évaluation complet pour un projet.

    Retourne un dict prêt à passer à eval() (avec __builtins__={}).

    Contenu :
      Mathématiques   : math, np, sqrt, pi, e, abs, min, max, sum, len, round
      Avatars         : avatar[i], len(avatar), list(avatar)
                        avatar[i].avatar_id  ← NOUVEAU
      Groupes         : group['nom'] → List[AvatarProxy] résolu par avatar_id
                        list(group), 'nom' in group
      Matériaux       : material['nom'].density, material['nom']['young']
      Modèles         : model['nom'].physics, model['nom'].dimension
      Filtres         : avatars_by_color('BLUEx')
                        avatars_by_material('beton')
                        avatars_by_type('rigidDisk')
                        avatars_by_origin('manual')
      Types           : AvatarType, AvatarOrigin
      Variables dyn.  : toutes les clés de state.dynamic_vars (évaluées)
      extra_vars      : variables supplémentaires (priorité la plus haute)
    """
    ctx: Dict[str, Any] = {
        # Mathématiques
        'math':  math,
        'np':    np,
        'sqrt':  math.sqrt,
        'pi':    math.pi,
        'e':     math.e,
        'abs':   abs,
        'min':   min,
        'max':   max,
        'sum':   sum,
        'len':   len,
        'round': round,
        'list':  list,
        'range': range,
        'str':   str,
        'int':   int,
        'float': float,
        'bool':  bool,

        # Types pylmgc90_gui
        'AvatarType':   AvatarType,
        'AvatarOrigin': AvatarOrigin,

        # Proxies principaux
        'avatar':   AvatarCollectionProxy(controller),
        'group':    GroupProxy(controller),
        'material': MaterialProxy(controller),
        'model':    ModelProxy(controller),

        # Fonctions de filtrage
        'avatars_by_color':    lambda col:  _avatars_by_color(controller, col),
        'avatars_by_material': lambda mat:  _avatars_by_material(controller, mat),
        'avatars_by_type':     lambda typ:  _avatars_by_type(controller, typ),
        'avatars_by_origin':   lambda orig: _avatars_by_origin(controller, orig),
    }

    # Variables dynamiques du projet évaluées dans l'ordre de définition
    dyn_vars = getattr(controller.state, 'dynamic_vars', {}) or {}
    evaluated: Dict[str, Any] = {}
    for var_name, var_expr in dyn_vars.items():
        try:
            if isinstance(var_expr, str):
                tmp = {**ctx, **evaluated}
                evaluated[var_name] = eval(
                    var_expr, {"__builtins__": {}}, tmp
                )
            else:
                evaluated[var_name] = var_expr
        except Exception:
            evaluated[var_name] = var_expr   # garder brut si échec
    ctx.update(evaluated)

    # Variables supplémentaires (priorité maximale)
    if extra_vars:
        ctx.update(extra_vars)

    return ctx


# ============================================================================
# SafeEvaluator
# ============================================================================

class SafeEvaluator:
    """Évaluateur sécurisé d'expressions Python."""

    _SAFE_NODES = (
        ast.Expression, ast.Constant, ast.Name, ast.Load,
        ast.BinOp, ast.UnaryOp, ast.Compare,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
        ast.Mod, ast.Pow, ast.MatMult,
        ast.USub, ast.UAdd, ast.Not,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.And, ast.Or, ast.BoolOp,
        ast.List, ast.Tuple, ast.Dict, ast.Set,
        ast.Call, ast.Attribute, ast.keyword,
        ast.Subscript, ast.Index, ast.Slice,
        ast.IfExp,
        ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
        ast.comprehension,
        ast.Store,
        ast.Starred,
    )

    def __init__(self, allowed_names: Optional[Dict[str, Any]] = None):
        self.allowed_names: Dict[str, Any] = {
            'math':  math,
            'np':    np,
            'pi':    math.pi,
            'e':     math.e,
            'sqrt':  math.sqrt,
            'abs':   abs,
            'min':   min,
            'max':   max,
            'sum':   sum,
            'len':   len,
            'round': round,
            'list':  list,
            'range': range,
            'str':   str,
            'int':   int,
            'float': float,
            'bool':  bool,
            'tuple': tuple,
            'dict':  dict,
            'AvatarType':   AvatarType,
            'AvatarOrigin': AvatarOrigin,
        }
        if allowed_names:
            self.allowed_names.update(allowed_names)

    def eval_expression(self, expression: str) -> Any:
        """Évalue une expression simple de façon sécurisée."""
        try:
            tree = ast.parse(expression.strip(), mode='eval')
            self._check_safe(tree)
            return eval(
                compile(tree, '<string>', 'eval'),
                {"__builtins__": {}},
                self.allowed_names,
            )
        except ValueError:
            raise
        except SyntaxError as e:
            raise ValueError(f"Syntaxe invalide : {e}")
        except Exception as e:
            raise ValueError(f"Erreur d'évaluation : {e}")

    def eval_dict(self, expression: str) -> Dict[str, Any]:
        """
        Évalue une expression sous forme de dictionnaire.
        Format : "cle1=val1, cle2=val2"
        """
        if not expression.strip():
            return {}
        try:
            dict_expr = f"dict({expression})"
            tree = ast.parse(dict_expr, mode='eval')
            self._check_safe(tree)
            return eval(
                compile(tree, '<dict_expr>', 'eval'),
                {"__builtins__": {}},
                self.allowed_names,
            )
        except ValueError:
            raise
        except SyntaxError as e:
            raise ValueError(f"Syntaxe invalide : {e}")
        except Exception as e:
            raise ValueError(f"Erreur d'évaluation : {e}")

    def _check_safe(self, node: ast.AST) -> None:
        """Vérifie qu'un nœud AST est sûr."""
        for n in ast.walk(node):
            if not isinstance(n, self._SAFE_NODES):
                raise ValueError(
                    f"Opération non autorisée : {n.__class__.__name__}"
                )
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                if n.func.id not in self.allowed_names:
                    raise ValueError(f"Fonction non autorisée : {n.func.id}")
            if isinstance(n, ast.Attribute) : 
                if n.attr.startswith('_'):
                    raise ValueError(f"Accès à un attribut privé non autorisé : '{n.attr}'"
                                     f"(les attributs commençant par '_' sont interdits pour la sécurité)")