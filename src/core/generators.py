# ============================================================================
# Générateurs (boucles, granulo)
# ============================================================================
"""
Générateurs pour avatars (boucles, granulométrie).
Logique pure sans dépendances GUI.
"""
import math
import numpy as np
from typing import List, Tuple, Dict, Any
from .models import Avatar, Loop, GranuloGeneration, AvatarType, AvatarOrigin


def _safe_copy_array(arr, dtype=np.float64) -> np.ndarray:
    """Copie sûre d'un tableau retourné par le Fortran/C de pylmgc90."""
    if arr is None:
        return np.array([], dtype=dtype)
    return np.array(arr, dtype=dtype, copy=True, order="C")


def _normalize_coords(coor, nb: int, dim: int = 2) -> np.ndarray:
    """
    Normalise les coordonnées renvoyées par depositInXxx.
    - flat (nb*dim,)  → (nb, dim)
    - déjà (nb, dim)  → inchangé
    Toujours une copie C-contiguous.
    """
    coor = _safe_copy_array(coor)
    if coor.size == 0:
        return np.zeros((0, dim), dtype=np.float64)

    if coor.ndim == 1:
        if coor.size % dim != 0:
            raise RuntimeError(
                f"Coordonnées invalides: taille={coor.size}, dim={dim} "
                f"(attendu multiple de {dim})"
            )
        coor = coor.reshape(-1, dim)
    elif coor.ndim == 2:
        if coor.shape[1] != dim and coor.shape[0] == dim:
            coor = coor.T
    else:
        raise RuntimeError(f"Forme de coordonnées inattendue: {coor.shape}")

    # Tronquer au nombre réellement posé
    if nb is not None and nb >= 0:
        coor = coor[:nb]

    return np.ascontiguousarray(coor, dtype=np.float64)


def _call_deposit(func, radii, *geom_args):
    """
    Appelle pre.depositInXxx de façon robuste.

    API officielle (pylmgc90 2025) :
        nb_laid, coors, radii = pre.depositInBox2D(radii, lx, ly)

    - Arguments positionnels uniquement (pas de kwargs radii=...)
    - Copie immédiate des tableaux (évite corruption mémoire / stack buffer overrun)
    - Compatible 2 ou 3 valeurs de retour
    """
    # radii doit être un ndarray float contigu côté Python
    radii_in = _safe_copy_array(radii)

    result = func(radii_in, *geom_args)

    if not isinstance(result, (tuple, list)):
        raise RuntimeError(
            f"{func.__name__}: retour inattendu ({type(result).__name__}), "
            f"tuple attendu. Vérifiez la version de pylmgc90."
        )
    if len(result) < 2:
        raise RuntimeError(
            f"{func.__name__}: seulement {len(result)} valeur(s) retournée(s), "
            f"au moins 2 attendues (nb, coor)."
        )

    nb_raw = result[0]
    coor_raw = result[1]
    radii_raw = result[2] if len(result) > 2 else radii_in

    # nb peut être int ou array-like selon version
    try:
        nb = int(nb_raw)
    except (TypeError, ValueError):
        nb = int(np.asarray(nb_raw).ravel()[0])

    if nb < 0:
        raise RuntimeError(f"{func.__name__}: nb_laid négatif ({nb})")

    dim = 2  # toutes les deposit*2D
    coor = _normalize_coords(coor_raw, nb, dim=dim)
    out_radii = _safe_copy_array(radii_raw)[:nb]

    if len(out_radii) < nb:
        # fallback si la version ne renvoie pas les rayons tronqués
        out_radii = radii_in[:nb]

    if coor.shape[0] != nb:
        # sécurité finale
        n = min(coor.shape[0], nb, len(out_radii))
        coor = coor[:n]
        out_radii = out_radii[:n]
        nb = n

    return nb, coor, out_radii

class LoopGenerator:
    """Génère des positions selon différents motifs"""

    @staticmethod
    def generate_circle(count: int, radius: float, offset_x: float = 0.0,
                        offset_y: float = 0.0) -> List[List[float]]:
        centers = []
        for i in range(count):
            angle = 2 * math.pi * i / count
            x = offset_x + radius * math.cos(angle)
            y = offset_y + radius * math.sin(angle)
            centers.append([x, y])
        return centers

    @staticmethod
    def generate_grid(count: int, step: float, offset_x: float = 0.0,
                      offset_y: float = 0.0) -> List[List[float]]:
        side = int(math.ceil(math.sqrt(count)))
        centers = []
        for i in range(count):
            x = offset_x + (i % side) * step
            y = offset_y + (i // side) * step
            centers.append([x, y])
        return centers

    @staticmethod
    def generate_line(count: int, step: float, offset_x: float = 0.0,
                      offset_y: float = 0.0, invert_axis: bool = False) -> List[List[float]]:
        centers = []
        for i in range(count):
            if invert_axis:
                x, y = offset_x, offset_y + i * step
            else:
                x, y = offset_x + i * step, offset_y
            centers.append([x, y])
        return centers

    @staticmethod
    def generate_spiral(count: int, radius: float, spiral_factor: float,
                        offset_x: float = 0.0, offset_y: float = 0.0) -> List[List[float]]:
        centers = []
        for i in range(count):
            angle = 2 * math.pi * i / max(1, count // 5)
            r = radius + i * spiral_factor
            x = offset_x + r * math.cos(angle)
            y = offset_y + r * math.sin(angle)
            centers.append([x, y])
        return centers

    @staticmethod
    def generate_positions(loop: Loop) -> List[List[float]]:
        if loop.loop_type == "Cercle":
            return LoopGenerator.generate_circle(
                loop.count, loop.radius, loop.offset_x, loop.offset_y
            )
        elif loop.loop_type == "Grille":
            return LoopGenerator.generate_grid(
                loop.count, loop.step, loop.offset_x, loop.offset_y
            )
        elif loop.loop_type == "Ligne":
            return LoopGenerator.generate_line(
                loop.count, loop.step, loop.offset_x, loop.offset_y, loop.invert_axis
            )
        elif loop.loop_type == "Spirale":
            return LoopGenerator.generate_spiral(
                loop.count, loop.radius, loop.spiral_factor, loop.offset_x, loop.offset_y
            )
        else:
            raise ValueError(f"Type de boucle inconnu: {loop.loop_type}")
        
class ForLoopGenerator:
    """Génère des éléments via boucle for avec expressions"""
    @staticmethod
    def generate_items(for_loop, controller, evaluator) -> List[Any]:
        """Génère les items de la boucle for"""
        items = []
        
        context = ForLoopGenerator._build_context(controller)
        
        start = int(evaluator.eval_expression(for_loop.start_expr, context))
        end = int(evaluator.eval_expression(for_loop.end_expr, context))
        step = int(evaluator.eval_expression(for_loop.step_expr, context))
        
        if step == 0:
            raise ValueError("Le step ne peut pas être 0")
        
        range_values = range(start, end, step) 
        for loop_value in range_values:
            context[for_loop.loop_var] = loop_value
            item = ForLoopGenerator._create_item(
                for_loop.target_type,
                for_loop.template_config,
                context,
                evaluator,
                controller
            )
            items.append(item)
        return items
    
    @staticmethod
    def _build_context(controller, evaluator=None) -> Dict[str, Any]:
        """Construit le contexte d'évaluation"""
        context = {
            'math': math,
            'np': np,
            'sqrt': math.sqrt,
            'pi': math.pi,
            'e': math.e,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'len': len,
        }
        
        if hasattr(controller.state, 'dynamic_vars'):
            for var_name, var_expr in controller.state.dynamic_vars.items():
                try:
                    if isinstance(var_expr, str) and evaluator is not None:
                        evaluator.allowed_names = context                  
                        context[var_name] = evaluator.eval_expression(var_expr, context)
                    else:
                        context[var_name] = var_expr
                except Exception as e:
                    print(f"Erreur lors de l'évaluation de la variable '{var_name}': {e}")
                    context[var_name] = var_expr
        
        return context
    
    @staticmethod
    def _create_item(target_type: str, template: dict, context: dict, evaluator, controller) -> Any:
        """Crée un item selon le type"""
        
        if target_type == "avatar":
            return ForLoopGenerator._create_avatar(template, context, evaluator, controller)
        elif target_type == "material":
            return ForLoopGenerator._create_material(template, context, evaluator)
        elif target_type == "model":
            return ForLoopGenerator._create_model(template, context, evaluator)
        elif target_type == "contact_law":
            return ForLoopGenerator._create_contact_law(template, context, evaluator)
        elif target_type == "visibility":
            return ForLoopGenerator._create_visibility(template, context, evaluator)
        elif target_type == "dof":
            return ForLoopGenerator._create_dof(template, context, evaluator)
        else:
            raise ValueError(f"Type non supporté: {target_type}")
    
    @staticmethod
    def _eval_field(field_value: str, context: dict, evaluator) -> Any:
        """Évalue un champ avec le contexte"""
        if not isinstance(field_value, str):
            return field_value
        
        try:
            return evaluator.eval_expression(field_value, context)
        except:
            return field_value
    
    @staticmethod
    def _create_avatar(template: dict, context: dict, evaluator, controller) -> Any:
        """Crée un avatar depuis le template"""
        from ..core.models import Avatar, AvatarType, AvatarOrigin
        
        center_expr = template.get('center', '[0, 0]')
        center = ForLoopGenerator._eval_field(center_expr, context, evaluator)
        if isinstance(center, str):
            center = eval(center, {"__builtins__": {}}, context)
        if not isinstance(center, list):
            center = list(center)
        
        avatar = Avatar(
            avatar_type=AvatarType(template['avatar_type']),
            center=center,
            material_name=str(ForLoopGenerator._eval_field(template['material_name'], context, evaluator)),
            model_name=str(ForLoopGenerator._eval_field(template['model_name'], context, evaluator)),
            color=str(ForLoopGenerator._eval_field(template.get('color', 'BLUEx'), context, evaluator)),
            origin=AvatarOrigin.LOOP
        )
        
        if 'radius' in template:
            avatar.radius = float(ForLoopGenerator._eval_field(template['radius'], context, evaluator))
        
        if 'axis' in template:
            axis = {}
            for k, v in template['axis'].items():
                axis[k] = float(ForLoopGenerator._eval_field(v, context, evaluator))
            avatar.axis = axis
        
        if 'nb_vertices' in template:
            avatar.nb_vertices = int(ForLoopGenerator._eval_field(template['nb_vertices'], context, evaluator))
        
        if 'generation_type' in template:
            avatar.generation_type = template['generation_type']
        
        if 'vertices' in template:
            vertices_expr = template['vertices']
            vertices = ForLoopGenerator._eval_field(vertices_expr, context, evaluator)
            if isinstance(vertices, str):
                vertices = eval(vertices, {"__builtins__": {}}, context)
            avatar.vertices = vertices
        
        if 'wall_params' in template:
            wall_params = {}
            for k, v in template['wall_params'].items():
                wall_params[k] = float(ForLoopGenerator._eval_field(v, context, evaluator))
            avatar.wall_params = wall_params
        
        if 'contactors' in template:
            avatar.contactors = template['contactors']
        
        if 'is_hollow' in template:
            avatar.is_hollow = template['is_hollow']
        
        return avatar
    
    @staticmethod
    def _create_material(template: dict, context: dict, evaluator) -> Any:
        """Crée un matériau depuis le template"""
        from ..core.models import Material, MaterialType
        
        name = str(ForLoopGenerator._eval_field(template['name'], context, evaluator))
        density = float(ForLoopGenerator._eval_field(template['density'], context, evaluator))
        
        props = {}
        if 'properties' in template:
            for k, v in template['properties'].items():
                props[k] = ForLoopGenerator._eval_field(v, context, evaluator)
        
        return Material(
            name=name,
            material_type=MaterialType(template['material_type']),
            density=density,
            properties=props
        )
    
    @staticmethod
    def _create_model(template: dict, context: dict, evaluator) -> Any:
        """Crée un modèle depuis le template"""
        from ..core.models import Model
        
        return Model(
            name=str(ForLoopGenerator._eval_field(template['name'], context, evaluator)),
            physics=template['physics'],
            element=template['element'],
            dimension=int(template['dimension']),
            options=template.get('options', {})
        )
    
    @staticmethod
    def _create_contact_law(template: dict, context: dict, evaluator) -> Any:
        """Crée une loi de contact depuis le template"""
        from ..core.models import ContactLaw, ContactLawType
        
        friction = None
        if 'friction' in template:
            friction = float(ForLoopGenerator._eval_field(template['friction'], context, evaluator))
        
        return ContactLaw(
            name=str(ForLoopGenerator._eval_field(template['name'], context, evaluator)),
            law_type=ContactLawType(template['law_type']),
            friction=friction,
            properties=template.get('properties', {})
        )
    
    @staticmethod
    def _create_visibility(template: dict, context: dict, evaluator) -> Any:
        """Crée une règle de visibilité depuis le template"""
        from ..core.models import VisibilityRule
        
        return VisibilityRule(
            candidate_body=template['candidate_body'],
            candidate_contactor=template['candidate_contactor'],
            candidate_color=str(ForLoopGenerator._eval_field(template['candidate_color'], context, evaluator)),
            antagonist_body=template['antagonist_body'],
            antagonist_contactor=template['antagonist_contactor'],
            antagonist_color=str(ForLoopGenerator._eval_field(template['antagonist_color'], context, evaluator)),
            behavior_name=template['behavior_name'],
            alert=float(ForLoopGenerator._eval_field(template.get('alert', 0.1), context, evaluator))
        )
    
    @staticmethod
    def _create_dof(template: dict, context: dict, evaluator) -> Any:
        """Crée une opération DOF depuis le template"""
        from ..core.models import DOFOperation
        
        params = {}
        if 'parameters' in template:
            for k, v in template['parameters'].items():
                params[k] = ForLoopGenerator._eval_field(v, context, evaluator)
        
        return DOFOperation(
            operation_type=template['operation_type'],
            target_type=template['target_type'],
            target_value=ForLoopGenerator._eval_field(template['target_value'], context, evaluator),
            parameters=params
        )

class GranuloGenerator:
    """Génère des distributions granulométriques via pylmgc90.pre"""

    @staticmethod
    def generate_radii(config: GranuloGeneration) -> np.ndarray:
        """Distribution de rayons seule (sans dépôt)."""
        from pylmgc90 import pre

        kwargs = {}
        if config.seed is not None:
            # certaines versions acceptent seed en 4e argument positionnel
            try:
                return _safe_copy_array(
                    pre.granulo_Random(
                        config.nb_particles,
                        config.radius_min,
                        config.radius_max,
                        config.seed,
                    )
                )
            except TypeError:
                pass

        return _safe_copy_array(
            pre.granulo_Random(
                config.nb_particles,
                config.radius_min,
                config.radius_max,
            )
        )

    @staticmethod
    def generate(config: GranuloGeneration) -> Tuple[int, np.ndarray, np.ndarray]:
        """
        Génère une distribution granulométrique avec dépôt pylmgc90.

        Returns
        -------
        (nb_particles, coordinates, radii)
            coordinates : shape (nb, 2), C-contiguous float64
            radii       : shape (nb,),   C-contiguous float64

        IMPORTANT
        ---------
        Doit être appelé depuis le **thread principal** uniquement
        (pylmgc90 / Fortran n'est pas thread-safe).
        """
        from pylmgc90 import pre

        if config.radius_min <= 0 or config.radius_max <= 0:
            raise ValueError("radius_min et radius_max doivent être > 0")
        if config.radius_min > config.radius_max:
            raise ValueError("radius_min doit être ≤ radius_max")
        if config.nb_particles <= 0:
            raise ValueError("nb_particles doit être > 0")

        # 1) Rayons
        radii = GranuloGenerator.generate_radii(config)

        # 2) Dépôt
        ctype = config.container_type
        params = config.container_params or {}

        if ctype == "Box2D":
            nb, coor, out_radii = _call_deposit(
                pre.depositInBox2D, radii, float(params["lx"]), float(params["ly"])
            )
        elif ctype == "Disk2D":
            nb, coor, out_radii = _call_deposit(
                pre.depositInDisk2D, radii, float(params["r"])
            )
        elif ctype == "Couette2D":
            nb, coor, out_radii = _call_deposit(
                pre.depositInCouette2D,
                radii,
                float(params["rint"]),
                float(params["rext"]),
            )
        elif ctype == "Drum2D":
            nb, coor, out_radii = _call_deposit(
                pre.depositInDrum2D, radii, float(params["r"])
            )
        else:
            raise ValueError(f"Type de conteneur inconnu: {ctype}")

        if nb == 0:
            raise ValueError(
                "Aucune particule n'a pu être déposée. "
                "Augmentez la taille du conteneur ou réduisez les rayons / le nombre."
            )

        return nb, coor, out_radii