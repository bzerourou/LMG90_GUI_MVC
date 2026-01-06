# ============================================================================
# Évaluation sécurisée d'expressions
# ============================================================================
"""
Utilitaires pour évaluer des expressions de manière sécurisée.
Remplace les eval() dangereux.
"""
import ast
import math
import numpy as np
from typing import Dict, Any


class SafeEvaluator:
    """Évaluateur sécurisé d'expressions Python"""
    
    def __init__(self, allowed_names: Dict[str, Any] = None):
        """
        Initialise l'évaluateur.
        
        Args:
            allowed_names: Variables autorisées (ex: {'pi': 3.14})
        """
        self.allowed_names = allowed_names or {}
        
        # Modules/fonctions autorisés
        self.allowed_names.update({
            'math': math,
            'np': np,
            'pi': math.pi,
            'e': math.e,
        })
    
    def eval_dict(self, expression: str) -> Dict[str, Any]:
        """
        Évalue une expression sous forme de dictionnaire.
        
        Args:
            expression: Chaîne à évaluer (ex: "a=1, b=2.5")
            
        Returns:
            Dictionnaire {clé: valeur}
            
        Raises:
            ValueError: Si l'expression est invalide
            
        Example:
            >>> evaluator = SafeEvaluator()
            >>> evaluator.eval_dict("young=1e9, nu=0.3")
            {'young': 1000000000.0, 'nu': 0.3}
        """
        if not expression.strip():
            return {}
        
        try:
            # Transformer "a=1, b=2" en "dict(a=1, b=2)"
            dict_expr = f"dict({expression})"
            
            # Parser l'AST
            tree = ast.parse(dict_expr, mode='eval')
            
            # Vérifier la sécurité
            self._check_safe(tree)
            
            # Évaluer
            result = eval(
                compile(tree, '<string>', 'eval'),
                {"__builtins__": {}},
                self.allowed_names
            )
            
            return result
            
        except SyntaxError as e:
            raise ValueError(f"Syntaxe invalide: {e}")
        except Exception as e:
            raise ValueError(f"Erreur d'évaluation: {e}")
    
    def eval_expression(self, expression: str) -> Any:
        """
        Évalue une expression simple.
        
        Args:
            expression: Expression à évaluer
            
        Returns:
            Résultat de l'évaluation
        """
        try:
            tree = ast.parse(expression, mode='eval')
            self._check_safe(tree)
            
            return eval(
                compile(tree, '<string>', 'eval'),
                {"__builtins__": {}},
                self.allowed_names
            )
        except Exception as e:
            raise ValueError(f"Erreur d'évaluation: {e}")
    
    def _check_safe(self, node: ast.AST) -> None:
        """
        Vérifie qu'un nœud AST est sûr.
        
        Raises:
            ValueError: Si le nœud contient des opérations dangereuses
        """
        # Nœuds autorisés
        safe_nodes = (
            ast.Expression, ast.Constant, ast.Name, ast.Load,
            ast.BinOp, ast.UnaryOp, ast.Compare,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
            ast.USub, ast.UAdd,
            ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
            ast.List, ast.Tuple, ast.Dict,
            ast.Call, ast.Attribute, ast.keyword,
            ast.Subscript, ast.Index, ast.Slice
        )
        
        for node in ast.walk(node):
            if not isinstance(node, safe_nodes):
                raise ValueError(
                    f"Opération non autorisée: {node.__class__.__name__}"
                )
            
            # Vérifier les appels de fonctions
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name not in self.allowed_names:
                        raise ValueError(f"Fonction non autorisée: {func_name}")
