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


# adapter à la version pylmgc90
def _call_deposit(func, *args, **kwargs):
    """
    Appelle une fonction de dépôt pylmgc90 (depositInBox2D, depositInDisk2D, ...)
    en s'adaptant au nombre de valeurs retournées selon la version installée :
      - pylmgc90 (ancien, ~2023)  : (nb_remaining, coor)
      - pylmgc90 (récent, ~2025) : (nb_remaining, coor, <valeur additionnelle>)

    Retourne toujours (nb_remaining, coor, radii). Si la version installée ne
    renvoie pas de valeur supplémentaire, on réutilise les rayons fournis en entrée.
    """
    result = func(*args, **kwargs)

    if not isinstance(result, (tuple, list)):
        raise RuntimeError(
            f"{func.__name__} : retour inattendu ({type(result).__name__!r}), "
            f"une séquence était attendue. Vérifiez la version de pylmgc90 installée."
        )

    if len(result) < 2:
        raise RuntimeError(
            f"{func.__name__} : seulement {len(result)} valeur(s) retournée(s), "
            f"au moins 2 attendues (nb_remaining, coor)."
        )

    nb_remaining = result[0]
    coor = result[1]
    dradii = result[2] if len(result) > 2 else (args[0] if args else None)

    if len(result) > 2:
        try:
            from .app_logger import get_logger
            get_logger('generators').debug(
                f"{func.__name__} a retourné {len(result)} valeurs "
                f"(version pylmgc90 récente détectée) — "
                f"{len(result) - 2} valeur(s) additionnelle(s) ignorée(s)."
            )
        except Exception:
            pass  # le logging ne doit jamais faire échouer le dépôt

    return nb_remaining, coor, dradii

class LoopGenerator:
    """Génère des positions selon différents motifs"""
    
    @staticmethod
    def generate_circle(count: int, radius: float, offset_x: float = 0.0, 
                       offset_y: float = 0.0) -> List[List[float]]:
        """Génère des positions en cercle"""
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
        """Génère des positions en grille"""
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
        """Génère des positions en ligne"""
        centers = []
        for i in range(count):
            if invert_axis:
                x = offset_x
                y = offset_y + i * step
            else:
                x = offset_x + i * step
                y = offset_y
            centers.append([x, y])
        return centers
    
    @staticmethod
    def generate_spiral(count: int, radius: float, spiral_factor: float,
                       offset_x: float = 0.0, offset_y: float = 0.0) -> List[List[float]]:
        """Génère des positions en spirale"""
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
        """
        Génère les positions selon la configuration de la boucle.
        
        Args:
            loop: Configuration de la boucle
            
        Returns:
            Liste des centres [x, y]
        """
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
    """Génère des distributions granulométriques"""
    
    @staticmethod
    def generate_radii(config: GranuloGeneration) -> np.ndarray:
        """
        Génère uniquement la distribution de rayons sans dépôt (granulo_Random).

        Args:
            config: Configuration de la génération — seuls nb_particles,
                    radius_min, radius_max et seed sont utilisés.

        Returns:
            Array numpy de rayons de forme (nb_particles,).
        """
        from pylmgc90 import pre
        return pre.granulo_Random(
            config.nb_particles,
            config.radius_min,
            config.radius_max,
            config.seed
        )

    @staticmethod
    def generate(config: GranuloGeneration) -> Tuple[int, np.ndarray, np.ndarray]:
        """
        Génère une distribution granulométrique avec dépôt.
        
        Args:
            config: Configuration de la génération
            
        Returns:
            (nb_particles, coordinates, radii)
            - nb_particles: nombre de particules effectivement placées
            - coordinates: array de shape (nb_particles, 2) avec positions
            - radii: array de shape (nb_particles,) avec rayons
        
        Raises:
            ValueError: Si le conteneur est inconnu ou paramètres invalides
        """
        from pylmgc90 import pre
        
        # Génération des rayons
        radii = pre.granulo_Random(
            config.nb_particles, 
            config.radius_min, 
            config.radius_max,
            config.seed
        )
        
        # Dépôt selon le type de conteneur
        ctype = config.container_type
        params = config.container_params
        
        if ctype == "Box2D":
            nb_remaining, coor, dradii = _call_deposit(pre.depositInBox2D, radii, params['lx'], params['ly'])
        elif ctype == "Disk2D":
            nb_remaining, coor, dradii = _call_deposit(pre.depositInDisk2D, radii, params['r'])
        elif ctype == "Couette2D":
            nb_remaining, coor, dradii = _call_deposit(pre.depositInCouette2D, radii, params['rint'], params['rext'])
        elif ctype == "Drum2D":
            nb_remaining, coor, dradii = _call_deposit(pre.depositInDrum2D, radii, params['r'])
        else:
            raise ValueError(f"Type de conteneur inconnu: {ctype}")
        
        # Reshape coordinates
        #nb_remaining = np.shape(coor)[0] // 2
        coor.shape = [coor.size//2,2]
        
        # Tronquer les rayons au nombre effectif
        radii = dradii[:nb_remaining]
        
        return nb_remaining, coor, radii