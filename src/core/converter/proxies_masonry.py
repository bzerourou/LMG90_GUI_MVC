"""Proxies pour la maçonnerie : briques (brick2D/3D) et murs (paneresse_simple/double)."""
from typing import List, Optional

from .proxies_avatar import _AvatarObj
from .utils import _center, _name


class _BrickObj:
    def __init__(self, kind: str, name: str = 'brick',
                 lx: float = 0.2, ly: float = 0.1, lz: float = 0.05, **kw):
        self._kind = kind
        self._name = str(name or 'brick')
        self._lx   = float(lx) if lx is not None else 0.2
        self._ly   = float(ly) if ly is not None else 0.1
        self._lz   = float(lz) if lz is not None else 0.05

    def rigidBrick(self, center=None, model=None, material=None,
                   color='BLUEx', theta=0., **kw) -> _AvatarObj:
        if self._kind == 'brick2D':
            av = _AvatarObj('rigidPolygon', dict(
                center          = _center(center),
                model           = _name(model),
                material        = _name(material),
                color           = color,
                generation_type = 'regular',
                nb_vertices     = 4,
                lx              = self._lx,
                ly              = self._ly,
                brick_name      = self._name,
            ))
            if theta:
                av._dof_ops.append({'op': 'rotate',
                                    'params': {'description': 'Euler',
                                               'phi': 0., 'theta': float(theta), 'psi': 0.}})
        else:
            av = _AvatarObj('rigidPolyhedron', dict(
                center     = _center(center, dim=3),
                model      = _name(model),
                material   = _name(material),
                color      = color,
                lx         = self._lx,
                ly         = self._ly,
                lz         = self._lz,
                brick_name = self._name,
            ))
        return av

    def rigidBrick3D(self, *a, **kw):
        return self.rigidBrick(*a, **kw)


class _WallObj:
    def __init__(self, kind: str, brick: Optional['_BrickObj'] = None,
                 converter=None):
        self._kind    = kind
        self._brick   = brick
        self._cv      = converter
        self._nb_rows = 1
        self._joint_h = 0.01
        self._joint_v = 0.01
        self._nb_bricks: Optional[int]   = None
        self._row_length: Optional[float] = None

    def setNumberOfRows(self, n: int):           self._nb_rows   = int(n)
    def setJointThicknessBetweenRows(self, e: float): self._joint_h = float(e)
    def setJointThicknessInRows(self, e: float = None, **kw):
        if e is not None: self._joint_v = float(e)

    def computeHeight(self) -> float:
        by = self._brick._ly if self._brick else 0.1
        return self._nb_rows * (by + self._joint_h)

    def getHeight(self) -> float:    return self.computeHeight()

    def getWidth(self) -> float:
        nb = self._nb_bricks or 5
        bx = self._brick._lx if self._brick else 0.2
        return nb * bx + (nb - 1) * self._joint_v

    def setFirstRowByNumberOfBricks(self, nb: int = 5, **kw):
        self._nb_bricks = int(nb)

    def setFirstRowByLength(self, L: float = 1.0, **kw):
        self._row_length = float(L)
        if self._brick:
            self._nb_bricks = max(1, int(round(float(L) / (self._brick._lx + self._joint_v))))

    def _brick_centers(self, wall_center, offset_rows: bool) -> List[List[float]]:
        nb  = self._nb_bricks or 5
        bx  = self._brick._lx if self._brick else 0.2
        by  = self._brick._ly if self._brick else 0.1
        jv  = self._joint_v
        jh  = self._joint_h
        cx0 = float(wall_center[0])
        cy0 = float(wall_center[1])
        total_w = nb * bx + (nb - 1) * jv
        x0 = cx0 - total_w / 2. + bx / 2.
        y0 = cy0 + by / 2.
        centers = []
        for row in range(self._nb_rows):
            ry     = y0 + row * (by + jh)
            offset = ((bx + jv) / 2.) if (offset_rows and row % 2 == 1) else 0.
            for col in range(nb):
                rx = x0 + col * (bx + jv) + offset
                centers.append([rx, ry])
        return centers

    def _build(self, center, model, material, color: str,
               offset_rows: bool) -> List[_AvatarObj]:
        c       = list(center) if center is not None else [0., 0.]
        centers = self._brick_centers(c, offset_rows)
        avatars = []
        for pos in centers:
            if self._brick:
                av = self._brick.rigidBrick(center=pos, model=model,
                                            material=material, color=color)
            else:
                av = _AvatarObj('rigidPolygon', dict(
                    center=pos, model=_name(model),
                    material=_name(material), color=color,
                    generation_type='regular', nb_vertices=4,
                ))
            avatars.append(av)
        if self._cv is not None:
            pattern_idx = len(self._cv._masonry_patterns)
            self._cv._masonry_patterns.append({
                'pattern_idx':        pattern_idx,
                'kind':               self._kind,
                'brick_name':         self._brick._name if self._brick else '',
                'lx':                 self._brick._lx   if self._brick else 0.2,
                'ly':                 self._brick._ly   if self._brick else 0.1,
                'lz':                 self._brick._lz   if self._brick else 0.05,
                'nb_rows':            self._nb_rows,
                'nb_bricks_per_row':  self._nb_bricks or 5,
                'joint_h':            self._joint_h,
                'joint_v':            self._joint_v,
                'center':             c,
                'model':              _name(model),
                'material':           _name(material),
                'color':              color,
                'avatar_indices':     [],
            })
            for av in avatars:
                av._masonry_idx = pattern_idx
        return avatars

    def buildRigidWall(self, center=None, model=None, material=None,
                       color='BLUEx', **kw) -> List[_AvatarObj]:
        return self._build(center, model, material, color,
                           offset_rows=(self._kind == 'paneresse_double'))

    def buildRigidWallWithoutHalfBricks(self, center=None, model=None,
                                         material=None, color='BLUEx',
                                         **kw) -> List[_AvatarObj]:
        return self._build(center, model, material, color, offset_rows=False)