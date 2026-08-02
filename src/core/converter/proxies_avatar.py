"""Proxies des avatars créés pendant l'exécution simulée du script."""
import math
from typing import Any, Dict, List, Optional

from .utils import _to_serial, _center, _name


class _NodeObj:
    """Proxy d'un noeud pylmgc90."""
    __slots__ = ('coor', 'number')

    def __init__(self, coor=None, number=1):
        self.coor   = list(coor) if coor is not None else [0., 0.]
        self.number = int(number)

    def __repr__(self):
        return f"Node(number={self.number}, coor={self.coor})"


class _BulkObj:
    """Proxy de rigid2d() / rigid3d() — aucune donnee utile pour la conversion."""
    def __init__(self, kind='rigid2d'):
        self._kind = kind

    def __repr__(self):
        return f"Bulk({self._kind})"


class _NodesMock:
    """Simule body.nodes[1].coor."""
    def __init__(self, center):
        self._c = list(center)

    def __getitem__(self, idx): return self

    @property
    def coor(self): return self._c


class _AvatarObj:
    """Proxy d'un avatar rigide cree directement (pre.rigidDisk, etc.)."""

    def __init__(self, avatar_type: str, kwargs: dict):
        self._type      = avatar_type
        self._kwargs    = kwargs
        self._dof_ops   = []
        self._loop_idx: Optional[int] = None
        self._masonry_idx: Optional[int] = None

    def translate(self, dx=0., dy=0., dz=0., **kw):
        self._dof_ops.append({'op': 'translate',
                              'params': {'dx': float(dx), 'dy': float(dy), 'dz': float(dz)}})
        c = self._kwargs.get('center', [0., 0.])
        if len(c) == 2:
            self._kwargs['center'] = [c[0]+float(dx), c[1]+float(dy)]
        else:
            self._kwargs['center'] = [c[0]+float(dx), c[1]+float(dy), c[2]+float(dz)]

    def rotate(self, description='Euler', phi=0., theta=0., psi=0.,
               alpha=0., axis=None, center=None, **kw):
        params = {'description': description}
        if description == 'Euler':
            params.update({'phi': float(phi), 'theta': float(theta), 'psi': float(psi)})
        else:
            params.update({'alpha': float(alpha),
                           'axis': list(axis) if axis is not None else [0., 0., 1.]})
        if center is not None:
            params['center'] = list(center)
        self._dof_ops.append({'op': 'rotate', 'params': params})

    def imposeDrivenDof(self, group='all', component=1, description='predefined',
                        dofty='vlocy', ct=0., amp=0., omega=0., phi=0.,
                        rampi=1., ramp=0., evolutionFile='', **kw):
        params = {'group': group, 'component': _to_serial(component),
                  'dofty': dofty, 'ct': float(ct)}
        if amp:         params['amp']           = float(amp)
        if omega:       params['omega']         = float(omega)
        if phi:         params['phi']           = float(phi)
        if rampi != 1.: params['rampi']         = float(rampi)
        if ramp:        params['ramp']          = float(ramp)
        if evolutionFile: params['evolutionFile'] = evolutionFile
        if description != 'predefined': params['description'] = description
        self._dof_ops.append({'op': 'imposeDrivenDof', 'params': params})

    def imposeInitValue(self, group='all', component=1, value=0., **kw):
        self._dof_ops.append({'op': 'imposeInitValue',
                              'params': {'group': group,
                                         'component': _to_serial(component),
                                         'value': float(value)}})

    @property
    def nodes(self):
        return _NodesMock(self._kwargs.get('center', [0., 0.]))

    def __repr__(self):
        return f"Avatar({self._type}, center={self._kwargs.get('center')})"


class _EmptyAvatarObj:
    """
    Proxy d'un avatar vide cree par pre.avatar(dimension=2/3) suivi de
    addBulk / addNode / defineModel / defineMaterial / addContactors /
    computeRigidProperties.
    """

    def __init__(self, dimension: int = 2):
        self._type        = 'emptyAvatar'
        self.dimension    = int(dimension)
        self._model       = ''
        self._material    = ''
        self._color       = 'BLUEx'
        self._contactors: List[dict] = []
        self._dof_ops:    List[dict] = []
        self._loop_idx:   Optional[int] = None
        self._masonry_idx: Optional[int] = None
        self._center: List[float] = [0.] * self.dimension
        self._kwargs: dict = {'center': self._center}

    def addBulk(self, bulk=None): pass

    def addNode(self, node=None):
        if isinstance(node, _NodeObj) and node.coor:
            self._center = list(node.coor)
            self._kwargs['center'] = self._center

    def defineGroups(self, *a, **kw): pass

    def defineModel(self, model=None, **kw):
        if model is not None:
            self._model = _name(model)
            self._kwargs['model'] = self._model

    def defineMaterial(self, material=None, **kw):
        if material is not None:
            self._material = _name(material)
            self._kwargs['material'] = self._material

    def addContactors(self, shape='DISKx', color='BLUEx', group='all', **params):
        self._color = color
        self._kwargs['color'] = color
        self._contactors.append({
            'shape': shape,
            'color': color,
            'group': group,
            'params': {k: _to_serial(v) for k, v in params.items()},
        })

    def computeRigidProperties(self, *a, **kw): pass

    def translate(self, dx=0., dy=0., dz=0., **kw):
        self._dof_ops.append({'op': 'translate',
                              'params': {'dx': float(dx), 'dy': float(dy), 'dz': float(dz)}})
        c = self._center
        if len(c) == 2:
            self._center = [c[0]+float(dx), c[1]+float(dy)]
        else:
            self._center = [c[0]+float(dx), c[1]+float(dy), c[2]+float(dz)]
        self._kwargs['center'] = self._center

    def rotate(self, description='Euler', phi=0., theta=0., psi=0.,
               alpha=0., axis=None, center=None, **kw):
        params = {'description': description}
        if description == 'Euler':
            params.update({'phi': float(phi), 'theta': float(theta), 'psi': float(psi)})
        else:
            params.update({'alpha': float(alpha),
                           'axis': list(axis) if axis is not None else [0., 0., 1.]})
        if center is not None:
            params['center'] = list(center)
        self._dof_ops.append({'op': 'rotate', 'params': params})

    def imposeDrivenDof(self, group='all', component=1, description='predefined',
                        dofty='vlocy', ct=0., amp=0., omega=0., phi=0.,
                        rampi=1., ramp=0., evolutionFile='', **kw):
        params = {'group': group, 'component': _to_serial(component),
                  'dofty': dofty, 'ct': float(ct)}
        if amp:         params['amp']   = float(amp)
        if omega:       params['omega'] = float(omega)
        if phi:         params['phi']   = float(phi)
        if rampi != 1.: params['rampi'] = float(rampi)
        if ramp:        params['ramp']  = float(ramp)
        if evolutionFile: params['evolutionFile'] = evolutionFile
        if description != 'predefined': params['description'] = description
        self._dof_ops.append({'op': 'imposeDrivenDof', 'params': params})

    def imposeInitValue(self, group='all', component=1, value=0., **kw):
        self._dof_ops.append({'op': 'imposeInitValue',
                              'params': {'group': group,
                                         'component': _to_serial(component),
                                         'value': float(value)}})

    @property
    def nodes(self):
        return _NodesMock(self._center)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return lambda *a, **kw: None

    def __repr__(self):
        return f"EmptyAvatar(dim={self.dimension}, center={self._center}, contactors={len(self._contactors)})"


class _MeshAvatarObj:
    """
    Proxy d'un corps deformable ou rigide issu de maillage.

    Sources supportees : buildMesh2D, buildMeshH8, buildMeshT3, buildMeshQ4,
    buildMeshT6, buildMeshQ8, readMesh, readMeshGMSH, readMeshVTK,
    buildMeshedAvatar, surfacicMeshToRigid3D, volumicMeshToRigid3D
    """

    def __init__(self, source: str, params: dict, converter: 'Converter'):
        self._type          = 'mesh'
        self._source        = source
        self._mesh_params   = dict(params)
        self._cv            = converter
        self._model         = params.get('model', '')
        self._material      = params.get('material', '')
        self._color         = params.get('color', 'BLUEx')
        self._groups:      List[str]  = []
        self._contactors:  List[dict] = []
        self._dof_ops:     List[dict] = []
        self._loop_idx:    Optional[int] = None
        self._masonry_idx: Optional[int] = None
        dim = 3 if source in ('buildMeshH8', 'surfacicMeshToRigid3D',
                               'volumicMeshToRigid3D', 'readMesh3D',
                               'readMeshGMSH', 'readMeshVTK') else 2
        self._center: List[float] = _center(params.get('center'), dim=dim)
        self._kwargs = {
            'center':   self._center,
            'model':    self._model,
            'material': self._material,
            'color':    self._color,
        }

    def defineGroups(self, *groups, **kw):
        for g in groups:
            if isinstance(g, str):
                self._groups.append(g)

    def defineModel(self, model=None, **kw):
        if model is not None:
            self._model = _name(model)
            self._kwargs['model'] = self._model
            self._mesh_params['model'] = self._model

    def defineMaterial(self, material=None, **kw):
        if material is not None:
            self._material = _name(material)
            self._kwargs['material'] = self._material
            self._mesh_params['material'] = self._material

    def addContactors(self, group='all', contactor='ALpxx',
                      shape=None, color='BLUEx', **kw):
        self._color = color
        self._kwargs['color'] = color
        self._contactors.append({
            'group':      group,
            'contactor':  contactor or shape or 'ALpxx',
            'color':      color,
            'extra':      {k: _to_serial(v) for k, v in kw.items()},
        })

    def computeRigidProperties(self, *a, **kw): pass
    def setModel(self, *a, **kw):                pass
    def setMaterial(self, *a, **kw):             pass

    def translate(self, dx=0., dy=0., dz=0., **kw):
        self._dof_ops.append({'op': 'translate',
                              'params': {'dx': float(dx), 'dy': float(dy), 'dz': float(dz)}})
        c = self._center
        if len(c) == 2:
            self._center = [c[0]+float(dx), c[1]+float(dy)]
        else:
            self._center = [c[0]+float(dx), c[1]+float(dy), c[2]+float(dz)]
        self._kwargs['center'] = self._center

    def rotate(self, description='Euler', phi=0., theta=0., psi=0.,
               alpha=0., axis=None, center=None, **kw):
        params = {'description': description}
        if description == 'Euler':
            params.update({'phi': float(phi), 'theta': float(theta), 'psi': float(psi)})
        else:
            params.update({'alpha': float(alpha),
                           'axis': list(axis) if axis is not None else [0., 0., 1.]})
        if center is not None:
            params['center'] = list(center)
        self._dof_ops.append({'op': 'rotate', 'params': params})

    def imposeDrivenDof(self, group='all', component=1, description='predefined',
                        dofty='vlocy', ct=0., amp=0., omega=0., phi=0.,
                        rampi=1., ramp=0., evolutionFile='', **kw):
        params = {'group': group, 'component': _to_serial(component),
                  'dofty': dofty, 'ct': float(ct)}
        if amp:         params['amp']   = float(amp)
        if omega:       params['omega'] = float(omega)
        if phi:         params['phi']   = float(phi)
        if rampi != 1.: params['rampi'] = float(rampi)
        if ramp:        params['ramp']  = float(ramp)
        if evolutionFile: params['evolutionFile'] = evolutionFile
        if description != 'predefined': params['description'] = description
        self._dof_ops.append({'op': 'imposeDrivenDof', 'params': params})

    def imposeInitValue(self, group='all', component=1, value=0., **kw):
        self._dof_ops.append({'op': 'imposeInitValue',
                              'params': {'group': group,
                                         'component': _to_serial(component),
                                         'value': float(value)}})

    @property
    def nodes(self):
        return _NodesMock(self._center)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return lambda *a, **kw: None

    def __repr__(self):
        return f"MeshAvatar({self._source}, center={self._center})"