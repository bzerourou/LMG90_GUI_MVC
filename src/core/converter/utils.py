"""Fonctions utilitaires de sérialisation partagées par tout le package convert."""
import math


def _center(c, dim=None):
    if c is None:
        return [0., 0.] if (dim or 2) == 2 else [0., 0., 0.]
    if hasattr(c, 'tolist'):
        return c.tolist()
    return [float(x) for x in c]


def _name(obj) -> str:
    from .proxies_data import _MaterialObj, _ModelObj
    if obj is None:
        return ''
    if isinstance(obj, (_MaterialObj, _ModelObj)):
        return obj.name
    return str(obj)


def _to_serial(obj):
    if obj is None:                                 return None
    if hasattr(obj, 'tolist'):                       return obj.tolist()
    if isinstance(obj, (list, tuple)):              return [_to_serial(x) for x in obj]
    if isinstance(obj, dict):                       return {k: _to_serial(v) for k, v in obj.items()}
    if isinstance(obj, (int, float, str, bool)):    return obj
    return str(obj)


def _normalize_kwargs(kw: dict) -> dict:
    return {k: _to_serial(v) for k, v in kw.items()}


def _rotate_vertices_2d(vertices, theta_deg: float):
    th = math.radians(theta_deg)
    ct, st = math.cos(th), math.sin(th)
    return [[ct*float(v[0]) - st*float(v[1]),
             st*float(v[0]) + ct*float(v[1])] for v in vertices]


def _default_preferences() -> dict:
    return {
        'default_project_path': None, 'unit_system': 'SI',
        'auto_save': True, 'auto_save_interval': 300,
        'backup_enabled': True, 'recent_projects': [],
        'max_recent_projects': 10, 'show_granulo_individually': True,
        'create_pylmgc_on_generate': True, 'script_use_loop': True,
    }