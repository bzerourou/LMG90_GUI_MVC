from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import pyqtSignal
from ...controllers.project_controller import ProjectController
from ...utils.safe_eval import SafeEvaluator, build_eval_context

import math
import numpy as np

class BaseTab(QWidget):
    """Classe de base pour les onglets avec évaluation sécurisée"""
    
    def __init__(self, controller: ProjectController):
        super().__init__()
        self.controller = controller
        self._evaluator = None

    # =========================================================================
    # Evaluateur avec contexte projet complet
    # =========================================================================
    def _get_evaluator(self) -> SafeEvaluator:
        """Retourne l'évaluateur avec contexte à jour"""
        if self._evaluator is None:
            self._evaluator = SafeEvaluator()
        
        self._evaluator.allowed_names = build_eval_context(self.controller)
        return self._evaluator
    
    # =========================================================================
    # Methodes d'evaluation publiques
    # =========================================================================

    def eval_float(self, text: str, default: float = 0.0,
                   field_name: str = "") -> float:
        """Evalue une expression et retourne un float."""
        text = text.strip()
        if not text:
            return default
        try:
            return float(self._get_evaluator().eval_expression(text))
        except Exception as e:
            try:
                return float(text)
            except ValueError:
                self._show_eval_error(text, e, field_name)
                raise

    def eval_int(self, text: str, default: int = 0,
                 field_name: str = "") -> int:
        """Evalue une expression et retourne un int."""
        text = text.strip()
        if not text:
            return default
        try:
            return int(self._get_evaluator().eval_expression(text))
        except Exception as e:
            try:
                return int(text)
            except ValueError:
                self._show_eval_error(text, e, field_name)
                raise

    def eval_list(self, text: str, expected_length: int = None,
                  default: list = None, field_name: str = "") -> list:
        """
        Evalue une liste.
        Supporte les variables, listes litterales et separations par virgule.
        """
        text = text.strip()
        if not text:
            return default or []

        evaluator = self._get_evaluator()
        try:
            result = evaluator.eval_expression(text)

            if isinstance(result, list):
                if expected_length and len(result) != expected_length:
                    raise ValueError(
                        f"Attendu {expected_length} elements, recu {len(result)}"
                    )
                return [float(x) for x in result]

            if isinstance(result, (int, float)):
                if expected_length and expected_length != 1:
                    raise ValueError(
                        f"Attendu {expected_length} elements, recu 1"
                    )
                return [float(result)]

            if ',' in text:
                parts = [p.strip() for p in text.split(',')]
                if expected_length and len(parts) != expected_length:
                    raise ValueError(
                        f"Attendu {expected_length} elements, recu {len(parts)}"
                    )
                return [float(evaluator.eval_expression(p)) for p in parts]

            raise ValueError(f"Impossible de convertir '{text}' en liste")

        except Exception as e:
            self._show_eval_error(text, e, field_name)
            raise

    def eval_dict(self, text: str, field_name: str = "") -> dict:
        """
        Evalue un dictionnaire de proprietes.
        Format : key1=val1, key2=val2
        """
        if not text.strip():
            return {}

        evaluator = self._get_evaluator()
        try:
            props = {}
            current_key   = None
            current_value = ""
            paren_depth   = 0
            bracket_depth = 0
            in_quotes     = False
            quote_char    = None

            i = 0
            while i < len(text):
                char = text[i]

                if char in ('"', "'") and (i == 0 or text[i - 1] != '\\'):
                    if not in_quotes:
                        in_quotes  = True
                        quote_char = char
                    elif char == quote_char:
                        in_quotes  = False
                        quote_char = None

                if in_quotes:
                    current_value += char
                    i += 1
                    continue

                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                elif char == '[':
                    bracket_depth += 1
                elif char == ']':
                    bracket_depth -= 1

                if (char == '=' and current_key is None
                        and paren_depth == 0 and bracket_depth == 0):
                    current_key   = current_value.strip()
                    current_value = ""
                    i += 1
                    continue

                if (char == ',' and paren_depth == 0
                        and bracket_depth == 0 and current_key is not None):
                    value_str = current_value.strip()
                    try:
                        props[current_key] = evaluator.eval_expression(value_str)
                    except Exception:
                        props[current_key] = value_str
                    current_key   = None
                    current_value = ""
                    i += 1
                    continue

                current_value += char
                i += 1

            if current_key is not None:
                value_str = current_value.strip()
                try:
                    props[current_key] = evaluator.eval_expression(value_str)
                except Exception:
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
        error_msg += "💡 Variables dynamiques disponibles:\n"
        
        dyn = getattr(self.controller.state, 'dynamic_vars', {}) or {}
        if dyn:
            keys = list(dyn.keys())
            error_msg += "  " + "\n  ".join(keys[:10])
            if len(keys) > 10:
                error_msg += f"\n  ... et {len(keys) - 10} autres"
        else:
                error_msg += "  (Aucune variable définie)\n"
                error_msg += "  Créez-les dans: Outils > Variables dynamiques"
        
        error_msg += "\n\n📌 Références internes:\n"
        error_msg += "  avatar[i].center          Centre [x, y] ou [x, y, z]\n"
        error_msg += "  avatar[i].x / .y / .z     Coordonnees individuelles\n"
        error_msg += "  avatar[i].radius          Rayon\n"
        error_msg += "  avatar[i].nodes[1].coor   Noeud principal (pylmgc90)\n"
        error_msg += "  avatar[i].brick_lx/ly/lz  Dimensions brique maconnerie\n"
        error_msg += "  avatar[i].material_name   Nom du materiau\n"
        error_msg += "  avatar[i].origin          Origine (manual/loop/granulo)\n"
        error_msg += "  group['nom']              Avatars du groupe\n"
        error_msg += "  material['nom'].density   Densite du materiau\n"
        error_msg += "  model['nom'].physics      Type physique du modele\n"
        error_msg += "  avatars_by_color('BLUEx') Filtrer par couleur\n"
        error_msg += "  avatars_by_material(nom)  Filtrer par materiau\n"
        error_msg += "  avatars_by_type(typ)      Filtrer par type\n"
        error_msg += "  len(avatar)               Nombre total d'avatars\n"
        error_msg += "  math.pi, sqrt(x), abs(x), min(), max()"
        
        QMessageBox.critical(self, "Erreur d'Évaluation", error_msg)
    
    # =========================================================================
    # Label d'aide
    # =========================================================================

    def add_expression_help_label(self, layout):
        """Ajoute un label d'aide pour les expressions"""
        help_label = QLabel(
            "💡 <b>Expressions supportées:</b><br>"
            "• Nombres : <code>0.5, 2*pi, sqrt(2)</code><br>"
            "• Variables dynamiques : <code>thickness, radius</code><br>"
            "• Avatars : <code>avatar[0].x, avatar[1].radius, avatar[0].nodes[1].coor</code><br>"
            "• Groupes : <code>group['mur'][0].center</code><br>"
            "• Filtres : <code>avatars_by_color('BLUEx'), avatars_by_material('beton')</code><br>"
            "• Materiaux : <code>material['TDURx'].density</code><br>"
            "• Modeles : <code>model['rigid'].dimension</code>"

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