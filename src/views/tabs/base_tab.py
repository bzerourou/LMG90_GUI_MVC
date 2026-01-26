from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import pyqtSignal
from ...controllers.project_controller import ProjectController
from ...utils.safe_eval import SafeEvaluator

import math
import numpy as np

class BaseTab(QWidget):
    """Classe de base pour les onglets avec évaluation sécurisée"""
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._evaluator = None
    
    def _get_evaluator(self) -> SafeEvaluator:
        """Retourne l'évaluateur avec contexte à jour"""
        if not self._evaluator:
            self._evaluator = SafeEvaluator()
        
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
        
        if hasattr(self.controller.state, 'dynamic_vars'):
            evaluated_vars = {}
            for var_name, var_expr in self.controller.state.dynamic_vars.items():
                try:
                    if isinstance(var_expr, str):
                        temp_context = {**context, **evaluated_vars}
                        temp_context['avatar'] = self._create_avatar_proxy()
                        temp_context['material'] = self._create_material_proxy()
                        temp_context['model'] = self._create_model_proxy()
                        evaluated_vars[var_name] = eval(var_expr, {"__builtins__": {}}, temp_context)
                    else:
                        evaluated_vars[var_name] = var_expr
                except:
                    evaluated_vars[var_name] = var_expr
            
            context.update(evaluated_vars)
        
        context['avatar'] = self._create_avatar_proxy()
        context['material'] = self._create_material_proxy()
        context['model'] = self._create_model_proxy()
        
        self._evaluator.allowed_names = context
        return self._evaluator
    
    def _create_material_proxy(self):
        """Crée un proxy pour accéder aux matériaux"""
        class MaterialProxy:
            def __init__(self, controller):
                self.controller = controller
            
            def __getitem__(self, name):
                mat = self.controller.get_material(name)
                if not mat:
                    raise KeyError(f"Matériau '{name}' introuvable")
                
                class MaterialDict(dict):
                    def __init__(self, m):
                        super().__init__()
                        self['name'] = m.name
                        self['density'] = m.density
                        self['material_type'] = m.material_type.value
                        self.update(m.properties)
                    
                    def __getattr__(self, name):
                        return self.get(name)
                
                return MaterialDict(mat)
        
        return MaterialProxy(self.controller)
    
    def _create_model_proxy(self):
        """Crée un proxy pour accéder aux modèles"""
        class ModelProxy:
            def __init__(self, controller):
                self.controller = controller
            
            def __getitem__(self, name):
                mod = self.controller.get_model(name)
                if not mod:
                    raise KeyError(f"Modèle '{name}' introuvable")
                
                class ModelDict(dict):
                    def __init__(self, m):
                        super().__init__()
                        self['name'] = m.name
                        self['physics'] = m.physics
                        self['element'] = m.element
                        self['dimension'] = m.dimension
                        self.update(m.options)
                    
                    def __getattr__(self, name):
                        return self.get(name)
                
                return ModelDict(mod)
        
        return ModelProxy(self.controller)
    
    def _create_avatar_proxy(self):
        """Crée un proxy pour accéder aux avatars avec nodes"""
        class AvatarProxy:
            def __init__(self, controller):
                self.controller = controller
            
            def __getitem__(self, index):
                avatars = self.controller.state.avatars
                if not isinstance(index, int) or index < 0 or index >= len(avatars):
                    raise IndexError(f"Avatar index {index} invalide (0-{len(avatars)-1})")
                return self._avatar_to_dict(avatars[index])
            
            def __len__(self):
                return len(self.controller.state.avatars)
            
            def _avatar_to_dict(self, avatar):
                """Convertit un avatar en dict accessible"""
                class NodeProxy(dict):
                    def __init__(self, coor):
                        super().__init__()
                        self['coor'] = coor
                    
                    def __getattr__(self, name):
                        return self.get(name)
                
                class AvatarDict(dict):
                    def __init__(self, av):
                        super().__init__()
                        self['center'] = av.center
                        self['radius'] = av.radius
                        self['color'] = av.color
                        self['material_name'] = av.material_name
                        self['model_name'] = av.model_name
                        self['avatar_type'] = av.avatar_type.value
                        self['axis'] = av.axis
                        self['vertices'] = av.vertices
                        self['nb_vertices'] = av.nb_vertices
                        self['wall_params'] = av.wall_params
                        
                        nodes = []
                        if av.vertices:
                            for vertex in av.vertices:
                                nodes.append(NodeProxy(vertex))
                        else:
                            nodes.append(NodeProxy(av.center))
                        self['nodes'] = nodes
                    
                    def __getattr__(self, name):
                        return self.get(name)
                
                return AvatarDict(avatar)
        
        return AvatarProxy(self.controller)
    
    def eval_float(self, text: str, default: float = 0.0, field_name: str = "") -> float:
        """Évalue une expression et retourne un float"""
        text = text.strip()
        if not text:
            return default
        
        try:
            evaluator = self._get_evaluator()
            result = evaluator.eval_expression(text)
            return float(result)
        except Exception as e:
            try:
                return float(text)
            except ValueError:
                self._show_eval_error(text, e, field_name)
                raise
    
    def eval_int(self, text: str, default: int = 0, field_name: str = "") -> int:
        """Évalue une expression et retourne un int"""
        text = text.strip()
        if not text:
            return default
        
        try:
            evaluator = self._get_evaluator()
            result = evaluator.eval_expression(text)
            return int(result)
        except Exception as e:
            try:
                return int(text)
            except ValueError:
                self._show_eval_error(text, e, field_name)
                raise
    
    def eval_list(self, text: str, expected_length: int = None, 
                  default: list = None, field_name: str = "") -> list:
        """Évalue une liste - supporte variables, listes littérales, et séparation par virgules"""
        text = text.strip()
        if not text:
            return default or []
        
        try:
            evaluator = self._get_evaluator()
            
            result = evaluator.eval_expression(text)
            
            if isinstance(result, list):
                if expected_length and len(result) != expected_length:
                    raise ValueError(f"Attendu {expected_length} éléments, reçu {len(result)}")
                return [float(x) for x in result]
            
            if isinstance(result, (int, float)):
                if expected_length and expected_length != 1:
                    raise ValueError(f"Attendu {expected_length} éléments, reçu 1")
                return [float(result)]
            
            if ',' in text:
                parts = [p.strip() for p in text.split(',')]
                
                if expected_length and len(parts) != expected_length:
                    raise ValueError(f"Attendu {expected_length} éléments, reçu {len(parts)}")
                
                result_list = []
                for part in parts:
                    val = evaluator.eval_expression(part)
                    result_list.append(float(val))
                
                return result_list
            
            raise ValueError(f"Impossible de convertir '{text}' en liste")
            
        except Exception as e:
            self._show_eval_error(text, e, field_name)
            raise
    
    def eval_dict(self, text: str, field_name: str = "") -> dict:
        """Évalue un dictionnaire de propriétés - Format: key1=val1, key2=val2"""
 
        if not text.strip():
            return {}
        
        try:
            evaluator = self._get_evaluator()
            props = {}
            
            # parser chaque paire individuellement
            current_key = None
            current_value = ""
            paren_depth = 0
            bracket_depth = 0
            in_quotes = False
            quote_char = None
            
            i = 0
            while i < len(text):
                char = text[i]
                
                # Gérer les guillemets
                if char in ('"', "'") and (i == 0 or text[i-1] != '\\'):
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                    elif char == quote_char:
                        in_quotes = False
                        quote_char = None
                
                # Si on est dans des guillemets, tout ajouter
                if in_quotes:
                    current_value += char
                    i += 1
                    continue
                
                # Compter les parenthèses et crochets
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                elif char == '[':
                    bracket_depth += 1
                elif char == ']':
                    bracket_depth -= 1
                
                # Si on trouve '=' et qu'on n'a pas de clé
                if char == '=' and current_key is None and paren_depth == 0 and bracket_depth == 0:
                    current_key = current_value.strip()
                    current_value = ""
                    i += 1
                    continue
                
                # Si on trouve ',' à la racine (pas dans [], ())
                if char == ',' and paren_depth == 0 and bracket_depth == 0 and current_key is not None:
                    # Évaluer la paire key=value
                    value_str = current_value.strip()
                    try:
                        props[current_key] = evaluator.eval_expression(value_str)
                    except:
                        # Si échec, garder comme string
                        props[current_key] = value_str
                    
                    # Reset
                    current_key = None
                    current_value = ""
                    i += 1
                    continue
                
                # Ajouter le caractère
                current_value += char
                i += 1
            
            # Traiter la dernière paire
            if current_key is not None:
                value_str = current_value.strip()
                try:
                    props[current_key] = evaluator.eval_expression(value_str)
                except:
                    props[current_key] = value_str
            
            return props
            
        except Exception as e:
            self._show_eval_error(text, e, field_name)
            raise
    
    def _show_eval_error(self, text: str, error: Exception, field_name: str = ""):
        """Affiche une erreur d'évaluation détaillée"""
        from PyQt6.QtWidgets import QMessageBox
        
        error_msg = "❌ Expression invalide"
        if field_name:
            error_msg += f" pour '{field_name}'"
        error_msg += f":\n\n'{text}'\n\n"
        error_msg += f"Erreur: {str(error)}\n\n"
        error_msg += "💡 Variables disponibles:\n"
        
        if hasattr(self.controller.state, 'dynamic_vars'):
            vars_list = list(self.controller.state.dynamic_vars.keys())
            if vars_list:
                error_msg += "  • " + "\n  • ".join(vars_list[:10])
                if len(vars_list) > 10:
                    error_msg += f"\n  ... et {len(vars_list)-10} autres"
            else:
                error_msg += "  (Aucune variable définie)\n"
                error_msg += "  Créez-les dans: Outils > Variables dynamiques"
        
        error_msg += "\n\n📌 Références internes:\n"
        error_msg += "  • avatar[i] - Accès à l'avatar i\n"
        error_msg += "    - avatar[0].center - Centre [x, y] ou [x, y, z]\n"
        error_msg += "    - avatar[0].center[0] - Coordonnée X\n"
        error_msg += "    - avatar[0].radius - Rayon\n"
        error_msg += "    - avatar[0].nodes[j].coor - Coordonnées du nœud j\n"
        error_msg += "    - avatar[0].nodes[1].coor[0] - X du nœud 1\n"
        error_msg += "    - avatar[0].vertices - Liste des sommets\n"
        error_msg += "  • material['NOM'] - Accès au matériau\n"
        error_msg += "    - material['TDURx'].density - Densité\n"
        error_msg += "  • model['NOM'] - Accès au modèle\n"
        error_msg += "    - model['rigid'].physics - Type physique\n"
        error_msg += "  • Fonctions math: math.pi, sqrt(x), abs(x), min(), max()\n"
        error_msg += "  • len(avatar) - Nombre total d'avatars"
        
        QMessageBox.critical(self, "Erreur d'Évaluation", error_msg)
    
    def add_expression_help_label(self, layout):
        """Ajoute un label d'aide pour les expressions"""
        help_label = QLabel(
            "💡 <b>Expressions supportées:</b><br>"
            "• Nombres: 0.5, 2*pi, sqrt(2)<br>"
            "• Variables dynamiques: thickness, radius<br>"
            "• Avatars: avatar[0].center[0], avatar[1].radius, avatar[2].nodes[1].coor<br>"
            "• Matériaux: material['TDURx'].density<br>"
            "• Modèles: model['rigid'].physics"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet(
            "color: #0066cc; font-size: 8pt; padding: 5px; "
            "background-color: #e3f2fd; border-radius: 3px;"
        )
        layout.addWidget(help_label)
    
    def _eval_expression(self, text: str, default=None, field_name=""):
        """Évalue une expression (supporte nombres, expressions, variables)"""
        text = text.strip()
        if not text:
            return default
        
        try:
            evaluator = self._get_evaluator()
            result = evaluator.eval_expression(text)
            return result
        except Exception as e:
            try:
                if '.' in text or 'e' in text.lower():
                    return float(text)
                return int(text)
            except ValueError:
                error_msg = f"Expression invalide"
                if field_name:
                    error_msg += f" pour '{field_name}'"
                error_msg += f": '{text}'\n\n"
                error_msg += f"Erreur: {e}\n\n"
                error_msg += "💡 Variables disponibles:\n"
                
                vars_list = list(self.controller.state.dynamic_vars.keys())
                if vars_list:
                    error_msg += "  • " + "\n  • ".join(vars_list[:5])
                    if len(vars_list) > 5:
                        error_msg += f"\n  ... et {len(vars_list)-5} autres"
                else:
                    error_msg += "  (Aucune - créez-les dans Outils > Variables dynamiques)"
                
                raise ValueError(error_msg)