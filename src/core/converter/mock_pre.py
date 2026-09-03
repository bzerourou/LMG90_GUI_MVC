"""_MockPre — module fantôme remplaçant pylmgc90.pre pendant l'exécution simulée."""
from typing import TYPE_CHECKING

from .proxies_avatar import (
    _NodeObj, _BulkObj, _AvatarObj, _EmptyAvatarObj, _MeshAvatarObj,
)
from .proxies_data import (
    _MaterialObj, _ModelObj, _TactBehavObj, _SeeTableObj, _PostproCommandObj,
    _GranuloRadii,
)
from .proxies_masonry import _BrickObj, _WallObj
from .containers import _Container, _SilentModule
from .utils import _center, _name, _to_serial, _normalize_kwargs

if TYPE_CHECKING:
    # Import uniquement pour les vérificateurs de type (mypy/IDE) — évite
    # tout risque de cycle à l'exécution. _MockPre.__init__ reçoit un
    # Converter réel mais ne l'utilise que par son API (_cv.xxx), jamais
    # besoin de la classe elle-même au runtime.
    from .converter import Converter


class _MockPre:
    """
    Remplace pylmgc90.pre pendant l'execution du script.
    """

    def __init__(self, converter: "Converter"):
        self._cv = converter

    # ── Conteneurs vides ─────────────────────────────────────────────────────

    def avatars(self):          return _Container('avatars')
    def materials(self):        return _Container('materials')
    def models(self):           return _Container('models')
    def tact_behavs(self):      return _Container('tact_behavs')
    def see_tables(self):       return _Container('see_tables')
    def postpro_commands(self): return _Container('postpro_commands')

    # ── Materiaux ─────────────────────────────────────────────────────────────

    def material(self, name, materialType='RIGID', density=1000., **kw):
        obj = _MaterialObj(name, materialType, density, **kw)
        self._cv._materials[name] = obj
        return obj

    # ── Modeles ───────────────────────────────────────────────────────────────

    def model(self, name, physics='MECAx', element='Rxx2D', dimension=2, **kw):
        obj = _ModelObj(name, physics, element, dimension, **kw)
        self._cv._models[name] = obj
        return obj

    # ── Utilitaire interne ────────────────────────────────────────────────────

    def _make_avatar(self, avatar_type: str, **kw) -> _AvatarObj:
        kw  = _normalize_kwargs(kw)
        obj = _AvatarObj(avatar_type, kw)
        self._cv._avatar_pool.append(obj)
        return obj

    # ── Corps rigides 2D ─────────────────────────────────────────────────────

    def rigidDisk(self, r=0.1, center=None, model=None, material=None,
                  color='BLUEx', is_Hollow=False, **kw):
        av = self._make_avatar('rigidDisk', r=float(r),
                               center=_center(center), model=_name(model),
                               material=_name(material), color=color)
        if is_Hollow:
            av._kwargs['is_Hollow'] = True
        return av

    def rigidJonc(self, axe1=1., axe2=0.1, center=None, model=None,
                  material=None, color='BLUEx', **kw):
        return self._make_avatar('rigidJonc',
                                 axe1=float(axe1), axe2=float(axe2),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def rigidPolygon(self, model=None, material=None, center=None, color='BLUEx',
                     theta=0., radius=None, generation_type='regular',
                     nb_vertices=None, vertices=None, **kw):
        kw_av = dict(center=_center(center), model=_name(model),
                     material=_name(material), color=color,
                     generation_type=generation_type)
        if radius is not None:       kw_av['radius']      = float(radius)
        if theta:                    kw_av['theta']        = float(theta)
        if nb_vertices is not None:  kw_av['nb_vertices']  = int(nb_vertices)
        if vertices is not None:     kw_av['vertices']     = _to_serial(vertices)
        return self._make_avatar('rigidPolygon', **kw_av)

    def rigidOvoidPolygon(self, ra=1., rb=1., nb_vertices=8, center=None,
                          model=None, material=None, color='BLUEx', **kw):
        return self._make_avatar('rigidOvoidPolygon',
                                 ra=float(ra), rb=float(rb),
                                 nb_vertices=int(nb_vertices),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def rigidDiscreteDisk(self, r=0.1, center=None, model=None, material=None,
                          color='BLUEx', **kw):
        return self._make_avatar('rigidDiscreteDisk', r=float(r),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def rigidCluster(self, nb_disk=3, r=0.1, center=None, model=None,
                     material=None, color='BLUEx', **kw):
        return self._make_avatar('rigidCluster',
                                 nb_disk=int(nb_disk), r=float(r),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    # ── Murs 2D — signatures corrigees (l=longueur, r=rayon disques, h=hauteur) ──

    def roughWall(self, l=1., r=0.1, center=None, model=None,
                  material=None, color='BLUEx', nb_vertex=10, **kw):
        return self._make_avatar('roughWall',
                                 l=float(l), r=float(r), nb_vertex=int(nb_vertex),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def fineWall(self, l=1., r=0.1, center=None, model=None,
                 material=None, color='BLUEx', nb_vertex=10, **kw):
        return self._make_avatar('fineWall',
                                 l=float(l), r=float(r), nb_vertex=int(nb_vertex),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def smoothWall(self, l=1., h=0.1, center=None, model=None,
                   material=None, color='BLUEx', nb_polyg=10, **kw):
        return self._make_avatar('smoothWall',
                                 l=float(l), h=float(h), nb_polyg=int(nb_polyg),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    def granuloRoughWall(self, l=1., rmin=0.05, rmax=0.1, center=None,
                         model=None, material=None, color='BLUEx',
                         nb_vertex=10, **kw):
        return self._make_avatar('granuloRoughWall',
                                 l=float(l), rmin=float(rmin), rmax=float(rmax),
                                 nb_vertex=int(nb_vertex),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color)

    # ── Corps rigides 3D ─────────────────────────────────────────────────────

    def rigidSphere(self, r=0.1, center=None, model=None, material=None,
                    color='BLUEx', is_Hollow=False, **kw):
        if is_Hollow:
            kw['is_Hollow'] = True
        return self._make_avatar('rigidSphere', r=float(r),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color)

    def rigidPlan(self, center=None, axe1=1., axe2=1., axe3=0.05,
                  model=None, material=None, color='BLUEx', **kw):
        """Plan rigide 3D. axe1/axe2/axe3 = demi-dimensions du plan rectangulaire."""
        return self._make_avatar('rigidPlan',
                                 axe1=float(axe1), axe2=float(axe2), axe3=float(axe3),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color)

    def rigidCylinder(self, r=0.5, h=1., center=None, model=None,
                      material=None, color='BLUEx', is_Hollow=False, **kw):
        if is_Hollow:
            kw['is_Hollow'] = True
        return self._make_avatar('rigidCylinder',
                                 r=float(r), h=float(h),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color)

    def rigidPolyhedron(self, model=None, material=None, center=None,
                        color='BLUEx', vertices=None, faces=None,
                        nb_vertices=None, radius=None,
                        generation_type='regular', **kw):
        kw_av = dict(center=_center(center, dim=3), model=_name(model),
                     material=_name(material), color=color,
                     generation_type=generation_type)
        if vertices    is not None: kw_av['vertices']    = _to_serial(vertices)
        if faces       is not None: kw_av['faces']       = _to_serial(faces)
        if nb_vertices is not None: kw_av['nb_vertices'] = int(nb_vertices)
        if radius      is not None: kw_av['radius']      = float(radius)
        return self._make_avatar('rigidPolyhedron', **kw_av)

    def roughWall3D(self, lx=1., ly=1., r=0.05, center=None, model=None,
                    material=None, color='BLUEx', **kw):
        return self._make_avatar('roughWall3D',
                                 lx=float(lx), ly=float(ly), r=float(r),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color)

    def granuloRoughWall3D(self, lx=1., ly=1., rmin=0.02, rmax=0.05,
                           center=None, model=None, material=None,
                           color='BLUEx', **kw):
        return self._make_avatar('granuloRoughWall3D',
                                 lx=float(lx), ly=float(ly),
                                 rmin=float(rmin), rmax=float(rmax),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color)

    # ── Avatar vide (contacteurs manuels) ─────────────────────────────────────

    def avatar(self, dimension=2) -> _EmptyAvatarObj:
        obj = _EmptyAvatarObj(dimension=int(dimension))
        self._cv._avatar_pool.append(obj)
        return obj

    def node(self, coor=None, number=1) -> _NodeObj:
        return _NodeObj(coor=coor, number=number)

    def rigid2d(self) -> _BulkObj: return _BulkObj('rigid2d')
    def rigid3d(self) -> _BulkObj: return _BulkObj('rigid3d')

    # ── Maillages 2D ─────────────────────────────────────────────────────────

    def _make_mesh(self, source: str, params: dict) -> _MeshAvatarObj:
        obj = _MeshAvatarObj(source, params, self._cv)
        self._cv._avatar_pool.append(obj)
        return obj

    def buildMesh2D(self, mesh_type='T3xxx', x0=0., y0=0.,
                    lx=1., ly=1., nx=4, ny=4, **kw):
        """Maillage 2D structure (triangles ou quads)."""
        return self._make_mesh('buildMesh2D', {
            'source_type': 'built2D', 'mesh_type': mesh_type,
            'x0': float(x0), 'y0': float(y0),
            'lx': float(lx), 'ly': float(ly),
            'nx': int(nx),   'ny': int(ny),
            'center': [float(x0) + float(lx)/2., float(y0) + float(ly)/2.],
        })

    def buildMeshT3(self, x0=0., y0=0., lx=1., ly=1., nx=4, ny=4, **kw):
        return self.buildMesh2D('T3xxx', x0, y0, lx, ly, nx, ny)

    def buildMeshQ4(self, x0=0., y0=0., lx=1., ly=1., nx=4, ny=4, **kw):
        return self.buildMesh2D('Q4xxx', x0, y0, lx, ly, nx, ny)

    def buildMeshT6(self, x0=0., y0=0., lx=1., ly=1., nx=4, ny=4, **kw):
        return self.buildMesh2D('T6xxx', x0, y0, lx, ly, nx, ny)

    def buildMeshQ8(self, x0=0., y0=0., lx=1., ly=1., nx=4, ny=4, **kw):
        return self.buildMesh2D('Q8xxx', x0, y0, lx, ly, nx, ny)

    # ── Maillages 3D ─────────────────────────────────────────────────────────

    def buildMeshH8(self, x0=0., y0=0., z0=0.,
                    lx=1., ly=1., lz=1., nx=2, ny=2, nz=2, **kw):
        """Volume 3D en hexaedres H8."""
        return self._make_mesh('buildMeshH8', {
            'source_type': 'builtH8',
            'x0': float(x0), 'y0': float(y0), 'z0': float(z0),
            'lx': float(lx), 'ly': float(ly), 'lz': float(lz),
            'nx': int(nx),   'ny': int(ny),   'nz': int(nz),
            'center': [float(x0)+float(lx)/2.,
                       float(y0)+float(ly)/2.,
                       float(z0)+float(lz)/2.],
            'dim': 3,
        })

    # ── Lecture de maillages exterieurs ──────────────────────────────────────

    def readMesh(self, filename=None, dim=2, **kw):
        """Lit un maillage depuis un fichier (format LMGC90 natif)."""
        fname = str(filename) if filename is not None else ''
        return self._make_mesh('readMesh', {
            'source_type': 'file', 'mesh_file': fname,
            'dim': int(dim), 'format': 'lmgc90',
        })

    def readMeshGMSH(self, filename=None, dim=2, **kw):
        """Lit un maillage au format GMSH (.msh)."""
        fname = str(filename) if filename is not None else ''
        return self._make_mesh('readMeshGMSH', {
            'source_type': 'file', 'mesh_file': fname,
            'dim': int(dim), 'format': 'gmsh',
        })

    def readMeshVTK(self, filename=None, dim=2, **kw):
        """Lit un maillage au format VTK."""
        fname = str(filename) if filename is not None else ''
        return self._make_mesh('readMeshVTK', {
            'source_type': 'file', 'mesh_file': fname,
            'dim': int(dim), 'format': 'vtk',
        })

    # ── Construction de corps deformable ou rigide issu de maillage ───────────

    def buildMeshedAvatar(self, mesh=None, model=None, material=None,
                          color='BLUEx', **kw):
        """Corps deformable (FEM) construit depuis un objet maillage."""
        params: dict = {'source_type': 'meshed_avatar', 'deformable': True,
                        'color': color}
        if isinstance(mesh, _MeshAvatarObj):
            params['mesh_source']  = mesh._source
            params['mesh_params']  = dict(mesh._mesh_params)
            params['center']       = mesh._center
            params['dim']          = len(mesh._center)
        params['model']    = _name(model)
        params['material'] = _name(material)
        obj = _MeshAvatarObj('buildMeshedAvatar', params, self._cv)
        obj._model    = _name(model)
        obj._material = _name(material)
        obj._color    = color
        obj._kwargs.update({'model': obj._model, 'material': obj._material, 'color': color})
        if isinstance(mesh, _MeshAvatarObj):
            obj._center = mesh._center
            obj._kwargs['center'] = obj._center
        self._cv._avatar_pool.append(obj)
        return obj

    def surfacicMeshToRigid3D(self, mesh=None, model=None, material=None,
                               color='BLUEx', **kw):
        """Convertit un maillage surfacique en corps rigide 3D."""
        params: dict = {'source_type': 'surfacicToRigid3D', 'deformable': False,
                        'dim': 3, 'color': color}
        if isinstance(mesh, _MeshAvatarObj):
            params['mesh_source'] = mesh._source
            params['mesh_params'] = dict(mesh._mesh_params)
            params['center']      = mesh._center
        params['model']    = _name(model)
        params['material'] = _name(material)
        obj = _MeshAvatarObj('surfacicMeshToRigid3D', params, self._cv)
        obj._model    = _name(model)
        obj._material = _name(material)
        obj._color    = color
        obj._kwargs.update({'model': obj._model, 'material': obj._material, 'color': color})
        if isinstance(mesh, _MeshAvatarObj):
            obj._center = mesh._center
            obj._kwargs['center'] = obj._center
        self._cv._avatar_pool.append(obj)
        return obj

    def volumicMeshToRigid3D(self, mesh=None, model=None, material=None,
                              color='BLUEx', **kw):
        """Convertit un maillage volumique en corps rigide 3D."""
        params: dict = {'source_type': 'volumicToRigid3D', 'deformable': False,
                        'dim': 3, 'color': color}
        if isinstance(mesh, _MeshAvatarObj):
            params['mesh_source'] = mesh._source
            params['mesh_params'] = dict(mesh._mesh_params)
            params['center']      = mesh._center
        params['model']    = _name(model)
        params['material'] = _name(material)
        obj = _MeshAvatarObj('volumicMeshToRigid3D', params, self._cv)
        obj._model    = _name(model)
        obj._material = _name(material)
        obj._color    = color
        obj._kwargs.update({'model': obj._model, 'material': obj._material, 'color': color})
        if isinstance(mesh, _MeshAvatarObj):
            obj._center = mesh._center
            obj._kwargs['center'] = obj._center
        self._cv._avatar_pool.append(obj)
        return obj

    # ── Maconnerie ────────────────────────────────────────────────────────────

    def brick2D(self, name='brick', lx=0.2, ly=0.1, **kw):
        return _BrickObj('brick2D', name=name, lx=lx, ly=ly)

    def brick3D(self, name='brick', lx=0.2, ly=0.1, lz=0.05, **kw):
        return _BrickObj('brick3D', name=name, lx=lx, ly=ly, lz=lz)

    def paneresse_simple(self, brick=None, *a, **kw):
        return _WallObj('paneresse_simple', brick=brick, converter=self._cv)

    def paneresse_double(self, brick=None, *a, **kw):
        return _WallObj('paneresse_double', brick=brick, converter=self._cv)

    # ── Contact / Visibilite / Postpro ────────────────────────────────────────

    def tact_behav(self, name, law, fric=None, **kw):
        obj = _TactBehavObj(name, law, fric, **kw)
        self._cv._tact_behavs[name] = obj
        return obj

    def see_table(self, CorpsCandidat, candidat, colorCandidat,
                  CorpsAntagoniste, antagoniste, colorAntagoniste,
                  behav, alert=0.1, **kw):
        obj = _SeeTableObj(CorpsCandidat, candidat, colorCandidat,
                           CorpsAntagoniste, antagoniste, colorAntagoniste,
                           behav, alert)
        self._cv._see_tables.append(obj)
        return obj

    def postpro_command(self, name, step=1, rigid_set=None, **kw):
        obj = _PostproCommandObj(name, step, rigid_set)
        self._cv._postpro_cmds.append(obj)
        return obj

    # ── Granulometrie ─────────────────────────────────────────────────────────

    def granulo_Random(self, nb, rmin=None, rmax=None,
                       r_min=None, r_max=None, seed=None, **kw):
        rmin = rmin if rmin is not None else r_min
        rmax = rmax if rmax is not None else r_max
        obj  = _GranuloRadii(int(nb), float(rmin), float(rmax), seed)
        idx  = len(self._cv._granulo_pairs)
        obj._granulo_idx = idx
        self._cv._granulo_pairs.append({
            'nb': int(nb), 'rmin': float(rmin), 'rmax': float(rmax),
            'seed': seed, 'nb_particles': None,
            'container_type': None, 'container_params': {},
        })
        return obj

    def _deposit(self, container_type: str, radii, params: dict):
        import numpy as np
        nb  = len(radii) if hasattr(radii, '__len__') else int(radii.nb)
        rng = np.random.default_rng(None)
        coords = rng.uniform(0, 1, (nb, 2))
        idx = getattr(radii, '_granulo_idx', None)
        if idx is not None and idx < len(self._cv._granulo_pairs):
            self._cv._granulo_pairs[idx].update({
                'nb_particles': nb, 'container_type': container_type,
                'container_params': params,
            })
        else:
            self._cv._granulo_pairs.append({
                'nb': nb, 'rmin': 0., 'rmax': 0., 'seed': None,
                'nb_particles': nb, 'container_type': container_type,
                'container_params': params,
            })
        return nb, coords

    def depositInBox2D(self, radii=None, lx=4., ly=4., **kw):
        return self._deposit('Box2D', radii, {'lx': float(lx), 'ly': float(ly)})

    def depositInDisk2D(self, radii=None, r=2., **kw):
        return self._deposit('Disk2D', radii, {'r': float(r)})

    def depositInCouette2D(self, radii=None, rint=1., rext=3., **kw):
        return self._deposit('Couette2D', radii, {'rint': float(rint), 'rext': float(rext)})

    def depositInDrum2D(self, radii=None, r=2., **kw):
        return self._deposit('Drum2D', radii, {'r': float(r)})

    def depositInBox3D(self, radii=None, lx=4., ly=4., lz=4., **kw):
        return self._deposit('Box3D', radii,
                             {'lx': float(lx), 'ly': float(ly), 'lz': float(lz)})

    def depositInSphere3D(self, radii=None, r=2., **kw):
        return self._deposit('Sphere3D', radii, {'r': float(r)})

    def depositInCylinder3D(self, radii=None, r=2., **kw):
        return self._deposit('Cylinder3D', radii, {'r': float(r)})

    # ── writeDatbox — capture de la dimension ─────────────────────────────────

    def writeDatbox(self, dim=2, mats=None, mods=None, bodies=None,
                    tacts=None, sees=None, post=None, datbox_path='DATBOX', **kw):
        if isinstance(dim, int):
            self._cv._dimension = int(dim)

    # ── Divers ────────────────────────────────────────────────────────────────

    def visuAvatars(self, *a, **kw):      pass
    def saveAvatarSet(self, *a, **kw):    pass
    def loadAvatarSet(self, *a, **kw):    return _Container('avatars')
    def mzToolBox(self, *a, **kw):        return _SilentModule('mzToolBox')

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        def _stub(*a, **kw): return _SilentModule(name)
        return _stub