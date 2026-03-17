# ============================================================================
# viewer_3d.py  —  Visualisation 3D des avatars LMGC90
# ============================================================================
"""
Viewer PyVista/Qt6 pour LMGC90_GUI.

Fonctionnalités actuelles
─────────────────────────
  Rendu         : avatars rigides, maillages déformables, murs, clusters
  Fichiers      : lecture directe .msh / .geo (gmsh) via pyvista.read()
  Navigation    : orbit, zoom, pan, vues XY / XZ / YZ / isométrique
  Arêtes        : toggle show_edges sur tous les acteurs
  Sélection     : clic gauche → highlight + signal avatar_clicked(index)
  Mesure        : mode Règle — clic A puis B → distance affichée + signal
  Groupes       : combo filtre visibilité par groupe d'avatars
  Statut        : barre d'état (nb avatars, résultat mesure, fichier chargé)

Plan des fonctionnalités futures
─────────────────────────────────
  COURT TERME
  ────────────
  [ ] Sélection multiple (Ctrl+clic) + signal list[int]
  [ ] Sélection par boîte rubber-band (enable_rubber_band_style)
  [ ] Annotation 3D sur les avatars sélectionnés (add_point_labels)
  [ ] Colorisation par propriété : matériau, modèle, groupe, type
  [ ] Réglage opacité global et par groupe (QSlider)
  [ ] Export PNG / SVG / VTK de la scène courante

"""

import math
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QCheckBox, QComboBox, QSizePolicy,
    QToolButton, QFrame, QButtonGroup,
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import Avatar, AvatarType


# ── Couleurs ──────────────────────────────────────────────────────────────────

_COLOR_MAP = {
    'BLUEx': '#3a7ec8', 'REDxx': '#d94040', 'VERTx': '#3aaa5a',
    'JAUNx': '#e8c020', 'GRAYx': '#909090', 'BLACx': '#202020',
    'WHITx': '#f5f5f5', 'ORANx': '#e87820', 'CYANx': '#20c8c8',
    'MAGEx': '#c030c0', 'VIOLx': '#8040c0', 'ROSEx': '#e880a0',
}
_DEFAULT_COLOR  = '#80b0e0'
_WALL_COLOR     = '#b0b0b0'
_MESH_COLOR     = '#40c8a0'
_SELECT_COLOR   = '#ffcc00'
_MEASURE_COLOR  = '#ff4444'
_EXTRUSION_H    = 0.04


def _lmgc_color(name: str) -> str:
    return _COLOR_MAP.get(name, _DEFAULT_COLOR)


def _as3(center, z: float = 0.0):
    if len(center) == 3:
        return list(center)
    return [center[0], center[1], z]


def _polygon_face(n_pts: int) -> list:
    return [n_pts] + list(range(n_pts))


def _extrude(poly: pv.PolyData, h: float) -> pv.PolyData:
    return poly.extrude((0, 0, h), capping=True)


def _ellipse_poly(cx, cy, cz, a, b, n=64) -> pv.PolyData:
    t   = np.linspace(0, 2 * math.pi, n, endpoint=False)
    pts = np.column_stack([cx + a * np.cos(t), cy + b * np.sin(t),
                           np.full(n, cz)])
    return pv.PolyData(pts, _polygon_face(n))


# ── Constructeurs de mesh ─────────────────────────────────────────────────────

def _mesh_rigid_disk(av: Avatar) -> pv.PolyData:
    c = _as3(av.center)
    r = av.radius or 0.1
    d = pv.Circle(radius=r, resolution=64)
    d.points += np.array(c)
    return _extrude(d, _EXTRUSION_H)


def _mesh_rigid_sphere(av: Avatar) -> pv.PolyData:
    return pv.Sphere(center=_as3(av.center), radius=av.radius or 0.1,
                     theta_resolution=24, phi_resolution=24)


def _mesh_rigid_disk_discrete(av: Avatar) -> pv.PolyData:
    return _mesh_rigid_disk(av)


def _mesh_rigid_jonc(av: Avatar) -> pv.PolyData:
    c  = _as3(av.center)
    ax = av.axis or {}
    a  = float(ax.get('axe1', av.radius or 0.2))
    b  = float(ax.get('axe2', (av.radius or 0.1) ))
    return _extrude(_ellipse_poly(c[0], c[1], c[2], a, b), _EXTRUSION_H)


def _mesh_rigid_polygon(av: Avatar) -> pv.PolyData:
    c     = _as3(av.center)
    verts = av.vertices
    if verts and len(verts) >= 3:
        pts   = np.array([_as3(v, c[2]) for v in verts])
        faces = _polygon_face(len(pts))
        poly  = pv.PolyData(pts, faces)
    else:
        n = av.nb_vertices or 6
        r = av.radius or 0.1
        t = np.linspace(0, 2 * math.pi, n, endpoint=False)
        pts = np.column_stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t),
                               np.full(n, c[2])])
        poly = pv.PolyData(pts, _polygon_face(n))
    return _extrude(poly, _EXTRUSION_H)


def _mesh_rigid_ovoid(av: Avatar) -> pv.PolyData:
    c  = _as3(av.center)
    ax = av.axis or {}
    a  = float(ax.get('axe1', av.radius or 0.15))
    b  = float(ax.get('axe2', (av.radius or 0.15) * 0.6))
    return _extrude(_ellipse_poly(c[0], c[1], c[2], a, b, n=80), _EXTRUSION_H)


def _mesh_rigid_cluster(av: Avatar) -> pv.PolyData:
    meshes = []
    for cont in (av.contactors or []):
        shape = cont.get('shape', '').upper()
        if shape.startswith('DISK'):
            cc = _as3(cont.get('center', av.center))
            r  = cont.get('radius', av.radius or 0.05)
            d  = pv.Circle(radius=r, resolution=32)
            d.points += np.array(cc)
            meshes.append(_extrude(d, _EXTRUSION_H))
    if not meshes:
        return _mesh_rigid_disk(av)
    result = meshes[0]
    for m in meshes[1:]:
        result = result.merge(m)
    return result


def _mesh_rough_wall(av: Avatar) -> pv.PolyData:
    c     = _as3(av.center)
    verts = av.vertices
    if verts and len(verts) >= 2:
        pts = np.array([_as3(v, c[2]) for v in verts])
    else:
        half = av.radius or 1.0
        pts  = np.array([[c[0]-half, c[1], c[2]], [c[0]+half, c[1], c[2]]])
    return pv.Spline(pts, len(pts)).tube(
        radius=max(0.005, (av.radius or 0.05) * 0.05)
    )


def _mesh_fine_wall(av: Avatar) -> pv.PolyData:
    return _mesh_rough_wall(av)


def _mesh_smooth_wall(av: Avatar) -> pv.PolyData:
    c     = _as3(av.center)
    verts = av.vertices
    if verts and len(verts) >= 2:
        pts = np.array([_as3(v, c[2]) for v in verts])
    else:
        half = av.radius or 1.0
        pts  = np.array([[c[0]-half, c[1], c[2]], [c[0]+half, c[1], c[2]]])
    return pv.Spline(pts, max(10, len(pts))).tube(radius=0.008)


def _mesh_granulo_wall(av: Avatar) -> pv.PolyData:
    return _mesh_rough_wall(av)


def _mesh_rigid_plan(av: Avatar) -> pv.PolyData:
    c  = _as3(av.center)
    ax = av.axis or {}
    s  = float(ax.get('size', av.radius or 1.0))
    n  = ax.get('normal', (0, 1, 0))
    return pv.Plane(center=c, direction=n, i_size=s*2, j_size=s*2,
                    i_resolution=4, j_resolution=4)


def _mesh_rigid_cylinder(av: Avatar) -> pv.PolyData:
    c  = _as3(av.center)
    r  = av.radius or 0.1
    ax = av.axis or {}
    h  = float(ax.get('height', r * 2))
    return pv.Cylinder(center=c, radius=r, height=h, resolution=32, capping=True)


def _mesh_rigid_polyhedron(av: Avatar) -> pv.PolyData:
    c     = _as3(av.center)
    verts = av.vertices
    if verts and len(verts) >= 4:
        pts = np.array([_as3(v) for v in verts])
        try:
            return pv.wrap(pv.PolyData(pts).delaunay_3d().extract_surface())
        except Exception:
            pass
    return pv.Dodecahedron(radius=av.radius or 0.1, center=c)


def _mesh_rough_wall_3d(av: Avatar) -> pv.PolyData:
    c = _as3(av.center)
    s = av.radius or 1.0
    return pv.Box(bounds=[c[0]-s, c[0]+s, c[1]-s, c[1]+s, c[2]-0.02, c[2]+0.02])


def _mesh_granulo_rough_wall_3d(av: Avatar) -> pv.PolyData:
    return _mesh_rough_wall_3d(av)


def _mesh_empty_avatar(av: Avatar) -> pv.PolyData:
    c  = _as3(av.center)
    wp = av.wall_params or {}

    # ── Brique maçonnerie (wall_params présent, contactors vides) ────────────
    # wall_params = {'l': lx, 'h': ly, 'brick_name': ..., 'lz': lz (opt)}
    if wp and not (av.contactors):
        lx = float(wp.get('l', 0.20))
        ly = float(wp.get('h', 0.065))
        lz = float(wp.get('lz', ly))   # 3D : lz = hauteur ; 2D : extrusion
        # Rectangle centré en c
        x0, y0 = c[0] - lx / 2, c[1] - ly / 2
        pts = np.array([
            [x0,      y0,      c[2]],
            [x0 + lx, y0,      c[2]],
            [x0 + lx, y0 + ly, c[2]],
            [x0,      y0 + ly, c[2]],
        ])
        poly = pv.PolyData(pts, [4, 0, 1, 2, 3])
        if len(c) == 3 and c[2] != 0:
            # Déjà 3D : extrusion dans z
            return poly.extrude((0, 0, lz), capping=True)
        else:
            return poly.extrude((0, 0, lz), capping=True)

    # ── Contacteurs explicites ────────────────────────────────────────────────
    meshes = []
    for cont in (av.contactors or []):
        shape = cont.get('shape', '').upper()
        cc    = _as3(cont.get('center', c))
        if shape.startswith('DISK') or shape.startswith('CLxx'):
            r = cont.get('radius', 0.05)
            d = pv.Circle(radius=r, resolution=32)
            d.points += np.array(cc)
            meshes.append(_extrude(d, _EXTRUSION_H))
        elif shape.startswith('POLYR') or shape.startswith('CLALp'):
            verts = cont.get('vertices', [])
            if len(verts) >= 3:
                pts  = np.array([_as3(v, cc[2]) for v in verts])
                poly = pv.PolyData(pts, _polygon_face(len(pts)))
                meshes.append(_extrude(poly, _EXTRUSION_H))
        elif shape.startswith('SPHER'):
            meshes.append(pv.Sphere(center=cc, radius=cont.get('radius', 0.05)))
        elif shape.startswith('CYLND'):
            r = cont.get('radius', 0.05)
            h = cont.get('height', r * 2)
            meshes.append(pv.Cylinder(center=cc, radius=r, height=h))
        elif shape.startswith('JONCx'):
            a = cont.get('axe1', 0.1)
            b = cont.get('axe2', 0.05)
            meshes.append(_extrude(
                _ellipse_poly(cc[0], cc[1], cc[2], a, b), _EXTRUSION_H
            ))
    if not meshes:
        # Fallback : petite boîte indicative (jamais une sphère)
        size = 0.02
        meshes.append(pv.Box(bounds=[
            c[0]-size, c[0]+size, c[1]-size, c[1]+size, c[2], c[2]+size
        ]))
    result = meshes[0]
    for m in meshes[1:]:
        result = result.merge(m)
    return result


def _mesh_deformable(av: Avatar) -> pv.PolyData | None:
    """
    Reconstruit la grille depuis mesh_params, ou lit directement le fichier
    .msh / .geo si la géométrie provient d'un fichier externe.
    """
    c      = _as3(av.center)
    mp     = av.mesh_params or {}
    source = mp.get('geom', mp.get('source', ''))

    try:
        # ── FICHIER EXTERNE .msh / .geo ───────────────────────────────────────
        if source in ('file2d', 'file3d', 'Fichier externe'):
            filepath = mp.get('filepath', '').strip()
            if filepath:
                return _read_mesh_file(filepath, center=c)
            size = 0.5
            return pv.Box(bounds=[c[0]-size, c[0]+size,
                                   c[1]-size, c[1]+size,
                                   c[2]-size, c[2]+size])

        # ── RECTANGLE 2D ──────────────────────────────────────────────────────
        if source in ('rect2d', 'Rectangle'):
            lx = mp.get('lx', 1.0)
            ly = mp.get('ly', 1.0)
            nx = max(2, mp.get('nx', 4))
            ny = max(2, mp.get('ny', 4))
            x0, y0 = c[0] - lx / 2, c[1] - ly / 2
            xs = np.linspace(x0, x0 + lx, nx + 1)
            ys = np.linspace(y0, y0 + ly, ny + 1)
            XX, YY = np.meshgrid(xs, ys)
            pts = np.column_stack([XX.ravel(), YY.ravel(), np.zeros(XX.size)])
            faces = []
            for j in range(ny):
                for i in range(nx):
                    a = j * (nx + 1) + i
                    faces += [4, a, a+1, a+nx+2, a+nx+1]
            mesh = pv.PolyData(pts, np.array(faces))
            return mesh.extrude((0, 0, max(lx, ly) * 0.02), capping=True)

        # ── BOÎTE H8 3D ───────────────────────────────────────────────────────
        if source in ('box3d', 'Boîte (H8)'):
            lx = mp.get('lx', 1.0)
            ly = mp.get('ly', 1.0)
            lz = mp.get('lz', 1.0)
            nx = max(2, mp.get('nx', 2))
            ny = max(2, mp.get('ny', 2))
            nz = max(2, mp.get('nz', 2))
            x0, y0, z0 = c[0]-lx/2, c[1]-ly/2, c[2]-lz/2
            xs = np.linspace(x0, x0+lx, nx+1)
            ys = np.linspace(y0, y0+ly, ny+1)
            zs = np.linspace(z0, z0+lz, nz+1)

            def _face_grid(u_arr, v_arr, w_val, perm):
                UU, VV = np.meshgrid(u_arr, v_arr)
                pts_f = np.zeros((UU.size, 3))
                pts_f[:, perm[0]] = UU.ravel()
                pts_f[:, perm[1]] = VV.ravel()
                pts_f[:, perm[2]] = w_val
                nu, nv = len(u_arr)-1, len(v_arr)-1
                faces_f = []
                for jj in range(nv):
                    for ii in range(nu):
                        a = jj*(nu+1)+ii
                        faces_f += [4, a, a+1, a+nu+2, a+nu+1]
                return pv.PolyData(pts_f, np.array(faces_f))

            meshes = [
                _face_grid(xs, ys, z0,      (0,1,2)),
                _face_grid(xs, ys, z0+lz,   (0,1,2)),
                _face_grid(xs, zs, y0,      (0,2,1)),
                _face_grid(xs, zs, y0+ly,   (0,2,1)),
                _face_grid(ys, zs, x0,      (1,2,0)),
                _face_grid(ys, zs, x0+lx,   (1,2,0)),
            ]
            result = meshes[0]
            for m in meshes[1:]:
                result = result.merge(m)
            return result

        # ── DISQUE ────────────────────────────────────────────────────────────
        if source in ('disk2d', 'Disque'):
            r = mp.get('r', 0.5)
            return pv.Disc(center=c, inner=0, outer=r,
                           r_res=mp.get('nr', 4), c_res=mp.get('ntheta', 24))

        # ── SPHÈRE ────────────────────────────────────────────────────────────
        if source in ('sphere3d', 'Sphère'):
            r = mp.get('r', 0.5)
            return pv.Sphere(center=c, radius=r,
                             theta_resolution=mp.get('ntheta', 16),
                             phi_resolution=mp.get('nphi', 16))

        # ── CYLINDRE ─────────────────────────────────────────────────────────
        if source in ('cylinder3d', 'Cylindre'):
            r = mp.get('r', 0.3)
            h = mp.get('h', 1.0)
            return pv.Cylinder(center=c, radius=r, height=h,
                               resolution=mp.get('ntheta', 24), capping=True)

    except Exception as e:
        print(f"⚠️ Viewer — maillage déformable ({source!r}) : {e}")

    # Fallback boîte
    size = 0.3
    return pv.Box(bounds=[c[0]-size, c[0]+size, c[1]-size, c[1]+size,
                           c[2]-size, c[2]+size])


def _read_mesh_file(filepath: str, center=None) -> pv.PolyData:
    """
    Lit un fichier .msh, .geo, .vtk, .vtu, .stl… via pyvista.read().
    Pour .geo (script gmsh), génère d'abord le maillage via le module gmsh.
    Extrait la surface et la centre si demandé.
    """
    import os
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Fichier introuvable : {filepath}")

    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.geo':
        try:
            import gmsh, tempfile
            gmsh.initialize()
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.open(filepath)
            gmsh.model.mesh.generate(3)
            tmp = tempfile.mktemp(suffix='.msh')
            gmsh.write(tmp)
            gmsh.finalize()
            mesh = pv.read(tmp)
            os.unlink(tmp)
        except ImportError:
            raise ImportError(
                "Le module gmsh est requis pour lire les fichiers .geo. "
                "Installez-le avec : pip install gmsh"
            )
    else:
        mesh = pv.read(filepath)

    # Extraire la surface
    surface = mesh.extract_surface() if hasattr(mesh, 'extract_surface') else mesh

    # Centrer si demandé
    if center is not None:
        bb     = surface.bounds
        cx_m   = (bb[0] + bb[1]) / 2
        cy_m   = (bb[2] + bb[3]) / 2
        cz_m   = (bb[4] + bb[5]) / 2
        surface.points += np.array([center[0]-cx_m, center[1]-cy_m, center[2]-cz_m])

    return surface


# ── Table de dispatch ─────────────────────────────────────────────────────────

_MESH_BUILDERS = {
    AvatarType.RIGID_DISK:            _mesh_rigid_disk,
    AvatarType.RIGID_SPHERE:          _mesh_rigid_sphere,
    AvatarType.RIGID_DISCRETE:        _mesh_rigid_disk_discrete,
    AvatarType.RIGID_JONC:            _mesh_rigid_jonc,
    AvatarType.RIGID_POLYGON:         _mesh_rigid_polygon,
    AvatarType.RIGID_OVOID:           _mesh_rigid_ovoid,
    AvatarType.RIGID_CLUSTER:         _mesh_rigid_cluster,
    AvatarType.ROUGH_WALL:            _mesh_rough_wall,
    AvatarType.FINE_WALL:             _mesh_fine_wall,
    AvatarType.SMOOTH_WALL:           _mesh_smooth_wall,
    AvatarType.GRANULO_WALL:          _mesh_granulo_wall,
    AvatarType.RIGID_PLAN:            _mesh_rigid_plan,
    AvatarType.RIGID_CYLINDER:        _mesh_rigid_cylinder,
    AvatarType.RIGID_POLYHEDRON:      _mesh_rigid_polyhedron,
    AvatarType.ROUGH_WALL_3D:         _mesh_rough_wall_3d,
    AvatarType.GRANULO_ROUGH_WALL_3D: _mesh_granulo_rough_wall_3d,
    AvatarType.EMPTY_AVATAR:          _mesh_empty_avatar,
    AvatarType.MESH_DEFORMABLE:       _mesh_deformable,
}


def build_avatar_mesh(avatar: Avatar) -> pv.PolyData | None:
    """Construit le mesh PyVista d'un avatar. Retourne None si type inconnu."""
    builder = _MESH_BUILDERS.get(avatar.avatar_type)
    if builder is None:
        print(f"⚠️ Viewer — type non supporté : {avatar.avatar_type}")
        return None
    try:
        return builder(avatar)
    except Exception as e:
        print(f"⚠️ Viewer — erreur rendu {avatar.avatar_type.value} : {e}")
        return None


# ── Modes interactifs ─────────────────────────────────────────────────────────

class _Mode:
    NAVIGATE = "navigate"
    SELECT   = "select"
    MEASURE  = "measure"


# ── Helpers UI ────────────────────────────────────────────────────────────────

def _tool_btn(label: str, tip: str) -> QToolButton:
    b = QToolButton()
    b.setText(label)
    b.setToolTip(tip)
    b.setCheckable(True)
    b.setAutoExclusive(True)
    b.setFixedHeight(24)
    return b


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFrameShadow(QFrame.Shadow.Sunken)
    f.setFixedWidth(1)
    return f


def _hex_to_rgb_float(hex_color: str):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def _rgb_float_to_hex(r: float, g: float, b: float) -> str:
    return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))


# ── Widget de visualisation ───────────────────────────────────────────────────

class Viewer3D(QWidget):
    """
    Widget de visualisation 3D PyVista pour LMGC90.

    Signaux
    ───────
    avatar_clicked(int)     : index de l'avatar cliqué (mode SELECT)
    measurement_done(float) : distance mesurée en mètres (mode MEASURE)
    """

    avatar_clicked   = pyqtSignal(int)
    measurement_done = pyqtSignal(float)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller      = controller
        self.avatars_data    = []   # [(index, Avatar), …]
        self.actors          = {}   # index → vtkActor
        self._selected_idx   = None
        self._orig_colors    = {}   # index → couleur hex d'origine
        self._mode           = _Mode.NAVIGATE
        self._measure_pts    = []   # 0, 1 ou 2 points 3D
        self._measure_actors = []   # acteurs temporaires (sphères + ligne + label)
        self._setup_ui()

    # =========================================================================
    # Interface
    # =========================================================================

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(2)

        # ── Barre d'outils ────────────────────────────────────────────────────
        tb = QHBoxLayout()
        tb.setSpacing(4)

        self.info_label = QLabel("0 avatar(s)")
        self.info_label.setStyleSheet("color:#aaa; font-size:9pt;")
        tb.addWidget(self.info_label)
        tb.addWidget(_sep())

        # Modes
        self._btn_nav     = _tool_btn("🖱️ Nav.",    "Navigation (orbit / zoom / pan)")
        self._btn_select  = _tool_btn("👆 Sélect.", "Cliquer sur un avatar pour le sélectionner")
        self._btn_measure = _tool_btn("📏 Règle",   "Mesurer la distance entre deux points")
        self._btn_nav.setChecked(True)
        mode_grp = QButtonGroup(self)
        for b in (self._btn_nav, self._btn_select, self._btn_measure):
            mode_grp.addButton(b)
            tb.addWidget(b)
        self._btn_nav.clicked.connect(lambda: self._set_mode(_Mode.NAVIGATE))
        self._btn_select.clicked.connect(lambda: self._set_mode(_Mode.SELECT))
        self._btn_measure.clicked.connect(lambda: self._set_mode(_Mode.MEASURE))

        tb.addWidget(_sep())

        # Vues
        for label, tip, fn in [
            ("XY",  "Vue orthogonale plan XY (2D)", self._view_xy),
            ("XZ",  "Vue plan XZ",                  self._view_xz),
            ("YZ",  "Vue plan YZ",                  self._view_yz),
            ("Iso", "Vue isométrique",               self._view_iso),
        ]:
            btn = QPushButton(label)
            btn.setToolTip(tip)
            btn.setFixedWidth(36)
            btn.clicked.connect(fn)
            tb.addWidget(btn)

        tb.addWidget(_sep())

        self._edges_check = QCheckBox("Arêtes")
        self._edges_check.setChecked(True)
        self._edges_check.toggled.connect(self._toggle_edges)
        tb.addWidget(self._edges_check)

        rst = QPushButton("🔄")
        rst.setToolTip("Réinitialiser la caméra")
        rst.setFixedWidth(28)
        rst.clicked.connect(self._reset_camera)
        tb.addWidget(rst)

        clr = QPushButton("🗑️")
        clr.setToolTip("Effacer la scène")
        clr.setFixedWidth(28)
        clr.clicked.connect(self.clear)
        tb.addWidget(clr)

        tb.addStretch()

        # Filtre groupe
        tb.addWidget(QLabel("Groupe :"))
        self._group_combo = QComboBox()
        self._group_combo.setToolTip("Afficher seulement les avatars de ce groupe")
        self._group_combo.setMinimumWidth(130)
        self._group_combo.addItem("Tous les groupes")
        self._group_combo.currentTextChanged.connect(self._on_group_filter)
        tb.addWidget(self._group_combo)

        root.addLayout(tb)

        # ── Plotter PyVista ───────────────────────────────────────────────────
        self.plotter = QtInteractor(self)
        self.plotter.set_background("#91919c")
        self.plotter.enable_anti_aliasing()
        root.addWidget(self.plotter.interactor, stretch=1)

        # ── Barre de statut ───────────────────────────────────────────────────
        self._status_label = QLabel("Prêt")
        self._status_label.setStyleSheet(
            "color:#ccc; font-size:8pt; padding:1px 4px;"
            "background:#111122; border-top:1px solid #333;"
        )
        self._status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        root.addWidget(self._status_label)

        self._add_scene_helpers()

    def _add_scene_helpers(self):
        self.plotter.add_axes(
            xlabel='X', ylabel='Y', zlabel='Z',
            line_width=2, color='white'
        )
        grid = pv.Plane(
            center=(0,0,0), direction=(0,0,1),
            i_size=10, j_size=10, i_resolution=10, j_resolution=10
        )
        self.plotter.add_mesh(
            grid, color='#2a2a4a', opacity=0.5,
            show_edges=True, edge_color="#5A5A74", pickable=False
        )

    # =========================================================================
    # Modes interactifs
    # =========================================================================

    def _set_mode(self, mode: str):
        self._mode = mode
        if mode != _Mode.MEASURE:
            self._cancel_measure()

        # Toujours revenir en trackball d'abord pour éviter les conflits
        try:
            self.plotter.enable_trackball_style()
        except Exception:
            pass

        if mode == _Mode.SELECT:
            try:
                self.plotter.enable_element_picking(
                    callback=self._on_pick,
                    mode='cell',
                    show_message=False,
                    pickable_window=False,
                )
            except Exception:
                # Fallback : observer clic gauche
                self.plotter.iren.add_observer(
                    'LeftButtonPressEvent', self._on_vtk_click_select
                )
            self._status("Mode sélection — cliquez sur un avatar")

        elif mode == _Mode.MEASURE:
            # Approche robuste : observer VTK direct
            # (enable_point_picking instable selon version PyVistaQt)
            try:
                iren = self.plotter.iren.interactor
                iren.RemoveObservers('LeftButtonPressEvent')
                iren.AddObserver('LeftButtonPressEvent', self._on_vtk_click_measure)
            except Exception:
                # Fallback enable_point_picking
                try:
                    self.plotter.enable_point_picking(
                        callback=self._on_measure_pick,
                        show_message=False,
                        show_point=False,
                        picker='point',
                    )
                except Exception as e:
                    self._status(f"Règle indisponible : {e}")
                    return
            self._status("Mode mesure — cliquez sur le point A")

        else:
            # Navigation : retirer les observeurs mesure/sélection
            try:
                iren = self.plotter.iren.interactor
                iren.RemoveObservers('LeftButtonPressEvent')
            except Exception:
                pass
            self._status("Navigation")

    def _on_vtk_click_select(self, obj, event):
        """Observeur VTK pour la sélection (fallback)."""
        try:
            x, y = self.plotter.iren.interactor.GetEventPosition()
            picker = self.plotter.renderer.GetPickProp()
            if picker:
                self._on_pick(picker)
        except Exception:
            pass

    def _on_vtk_click_measure(self, obj, event):
        """
        Observeur VTK robuste pour la règle de mesure.
        Utilise pick() pour obtenir les coordonnées 3D du point cliqué.
        """
        try:
            iren = self.plotter.iren.interactor
            x, y = iren.GetEventPosition()
            # Picker de cellule pour obtenir la position 3D sur la surface
            picker = self.plotter.renderer._prop_picker
            if picker is None:
                import vtk
                picker = vtk.vtkCellPicker()
                picker.SetTolerance(0.005)
            picker.Pick(x, y, 0, self.plotter.renderer)
            pos = picker.GetPickPosition()
            # Vérifier que le pick a touché quelque chose (pos != origine)
            if picker.GetCellId() < 0:
                # Rien touché — essayer un picker de points
                import vtk
                pt_picker = vtk.vtkPointPicker()
                pt_picker.SetTolerance(0.01)
                pt_picker.Pick(x, y, 0, self.plotter.renderer)
                pos = pt_picker.GetPickPosition()
                if all(p == 0.0 for p in pos):
                    self._status("Aucune surface touchée — cliquez sur un objet")
                    return
            self._on_measure_pick(pos)
        except Exception as e:
            self._status(f"Erreur mesure : {e}")

    # ── Sélection ─────────────────────────────────────────────────────────────

    def _on_pick(self, picked):
        if picked is None:
            return
        for idx, actor in self.actors.items():
            try:
                if (actor == picked or
                        (hasattr(picked, 'GetMapper') and
                         hasattr(actor, 'GetMapper') and
                         actor.GetMapper() == picked.GetMapper())):
                    self._select_avatar(idx)
                    return
            except Exception:
                pass

    def _select_avatar(self, index: int):
        # Désélectionner le précédent
        if self._selected_idx is not None and self._selected_idx in self.actors:
            orig = self._orig_colors.get(self._selected_idx, _DEFAULT_COLOR)
            try:
                self.actors[self._selected_idx].GetProperty().SetColor(
                    *_hex_to_rgb_float(orig)
                )
            except Exception:
                pass

        self._selected_idx = index
        actor = self.actors.get(index)
        if actor:
            try:
                prop = actor.GetProperty()
                r, g, b = prop.GetColor()
                self._orig_colors[index] = _rgb_float_to_hex(r, g, b)
                prop.SetColor(*_hex_to_rgb_float(_SELECT_COLOR))
            except Exception:
                pass
            self.plotter.render()

        av = next((a for i, a in self.avatars_data if i == index), None)
        if av:
            c = av.center
            self._status(
                f"Sélectionné : avatar #{index} — {av.avatar_type.value} "
                f"@ ({', '.join(f'{x:.4f}' for x in c)})"
            )
        self.avatar_clicked.emit(index)

    # ── Mesure ────────────────────────────────────────────────────────────────

    def _on_measure_pick(self, point):
        if point is None:
            return
        self._measure_pts.append(np.array(point))
        sphere = self.plotter.add_mesh(
            pv.Sphere(center=point, radius=0.015),
            color=_MEASURE_COLOR, pickable=False
        )
        self._measure_actors.append(sphere)

        if len(self._measure_pts) == 1:
            p = self._measure_pts[0]
            self._status(
                f"Point A : ({p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f}) — cliquez sur B"
            )
        elif len(self._measure_pts) == 2:
            A, B = self._measure_pts
            dist = float(np.linalg.norm(B - A))
            # Ligne A→B
            line_a = self.plotter.add_mesh(
                pv.Line(A, B), color=_MEASURE_COLOR, line_width=2, pickable=False
            )
            self._measure_actors.append(line_a)
            # Label au milieu
            mid = (A + B) / 2
            lbl = self.plotter.add_point_labels(
                [mid], [f"  {dist:.4f} m"],
                font_size=12, text_color='white',
                point_color=_MEASURE_COLOR, point_size=0,
                always_visible=True, shadow=True,
            )
            self._measure_actors.append(lbl)
            self._status(f"Distance A→B : {dist:.6f} m")
            self.measurement_done.emit(dist)
            # Réinitialiser pour la prochaine mesure
            self._measure_pts.clear()

    def _cancel_measure(self):
        for actor in self._measure_actors:
            try:
                self.plotter.remove_actor(actor)
            except Exception:
                pass
        self._measure_actors.clear()
        self._measure_pts.clear()

    # =========================================================================
    # API publique
    # =========================================================================

    def add_avatar(self, avatar: Avatar, index: int):
        mesh = build_avatar_mesh(avatar)
        if mesh is None:
            return

        if avatar.avatar_type == AvatarType.MESH_DEFORMABLE:
            color = _MESH_COLOR
        elif avatar.avatar_type in (
            AvatarType.ROUGH_WALL, AvatarType.FINE_WALL,
            AvatarType.SMOOTH_WALL, AvatarType.GRANULO_WALL,
            AvatarType.ROUGH_WALL_3D, AvatarType.GRANULO_ROUGH_WALL_3D,
        ):
            color = _WALL_COLOR
        else:
            color = _lmgc_color(avatar.color)

        actor = self.plotter.add_mesh(
            mesh,
            color=color,
            show_edges=self._edges_check.isChecked(),
            edge_color='#000000',
            opacity=0.88,
            pickable=True,
            smooth_shading=True,
        )
        self.actors[index]       = actor
        self._orig_colors[index] = color
        self.avatars_data.append((index, avatar))
        self._update_info()

    def update_avatars(self, avatars):
        """
        Recharge tous les avatars.
        Pour les grandes scènes (granulo), les disques/sphères identiques
        sont fusionnés en un seul acteur par couleur pour éviter le crash VTK.
        """
        self.clear()
        if not avatars:
            return

        # Séparer les avatars "simples répétitifs" (granulo) des autres
        _BATCH_TYPES = {AvatarType.RIGID_DISK, AvatarType.RIGID_SPHERE}
        batches: dict = {}   # (avatar_type, color_hex) → [(index, mesh), …]
        singles = []

        for i, av in enumerate(avatars):
            if av.avatar_type in _BATCH_TYPES:
                color = _lmgc_color(av.color)
                key   = (av.avatar_type, color)
                batches.setdefault(key, []).append((i, av))
            else:
                singles.append((i, av))

        # Avatars singles : un acteur par avatar (comportement normal)
        for i, av in singles:
            self.add_avatar(av, i)

        # Avatars batched : fusionner en un seul mesh par groupe couleur
        for (av_type, color), group in batches.items():
            if len(group) == 1:
                # Un seul → comportement normal
                i, av = group[0]
                self.add_avatar(av, i)
                continue

            # Construire tous les meshes puis les fusionner
            parts = []
            for i, av in group:
                m = build_avatar_mesh(av)
                if m is not None:
                    parts.append(m)

            if not parts:
                continue

            merged = parts[0]
            for p in parts[1:]:
                merged = merged.merge(p)

            actor = self.plotter.add_mesh(
                merged,
                color=color,
                show_edges=False,   # arêtes désactivées sur les grands batches
                opacity=0.88,
                pickable=False,     # sélection individuelle non supportée en batch
                smooth_shading=True,
            )
            # Stocker l'acteur sur le premier index du groupe
            first_i = group[0][0]
            self.actors[first_i]       = actor
            self._orig_colors[first_i] = color
            for i, av in group:
                self.avatars_data.append((i, av))

        self._refresh_group_combo()
        self._update_info()
        self._reset_camera()

    def clear(self):
        self.plotter.clear()
        self.actors.clear()
        self.avatars_data.clear()
        self._orig_colors.clear()
        self._selected_idx   = None
        self._measure_pts.clear()
        self._measure_actors.clear()
        self._add_scene_helpers()
        self._update_info()

    def load_mesh_file(self, filepath: str):
        """
        Charge et affiche directement un fichier de maillage (.msh, .geo,
        .vtk, .vtu, .stl…) indépendamment du projet courant.
        """
        try:
            mesh = _read_mesh_file(filepath)
            self.plotter.add_mesh(
                mesh,
                color=_MESH_COLOR,
                show_edges=self._edges_check.isChecked(),
                edge_color='#004444',
                opacity=0.9,
                pickable=False,
            )
            self.plotter.reset_camera()
            ext    = filepath.rsplit('.', 1)[-1].upper()
            n_pts  = mesh.n_points
            n_cell = mesh.n_cells
            self._status(
                f"Fichier {ext} : {n_pts} nœuds, {n_cell} cellules — {filepath}"
            )
        except Exception as e:
            self._status(f"❌ Erreur chargement : {e}")

    # =========================================================================
    # Caméra
    # =========================================================================

    def _reset_camera(self):
        dim = getattr(self.controller.state, 'dimension', 3)
        if dim == 2:
            self._view_xy()
        else:
            self.plotter.reset_camera()
            self.plotter.view_isometric()

    def reset_camera(self, dimension: int = 3):
        """Compatible avec l'ancienne signature."""
        if dimension == 2:
            self._view_xy()
        else:
            self.plotter.reset_camera()
            self.plotter.view_isometric()

    def _view_xy(self):
        self.plotter.view_xy()
        self.plotter.camera.parallel_projection = True
        self.plotter.reset_camera()

    def _view_xz(self):
        self.plotter.view_xz()
        self.plotter.camera.parallel_projection = False
        self.plotter.reset_camera()

    def _view_yz(self):
        self.plotter.view_yz()
        self.plotter.camera.parallel_projection = False
        self.plotter.reset_camera()

    def _view_iso(self):
        self.plotter.view_isometric()
        self.plotter.camera.parallel_projection = False
        self.plotter.reset_camera()

    # =========================================================================
    # Arêtes
    # =========================================================================

    def _toggle_edges(self, show: bool):
        for actor in self.actors.values():
            try:
                actor.GetProperty().SetEdgeVisibility(int(show))
            except Exception:
                pass
        self.plotter.render()

    # =========================================================================
    # Filtrage par groupe
    # =========================================================================

    def _refresh_group_combo(self):
        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        self._group_combo.addItem("Tous les groupes")
        groups = getattr(self.controller.state, 'avatar_groups', {}) or {}
        for g in sorted(groups.keys()):
            self._group_combo.addItem(g)
        self._group_combo.blockSignals(False)

    def _on_group_filter(self, text: str):
        groups = getattr(self.controller.state, 'avatar_groups', {}) or {}
        visible = (
            {i for i, _ in self.avatars_data}
            if text == "Tous les groupes"
            else set(groups.get(text, []))
        )
        for idx, actor in self.actors.items():
            try:
                actor.SetVisibility(int(idx in visible))
            except Exception:
                pass
        self.plotter.render()
        n = len(visible)
        self._status(
            f"Groupe « {text} » : {n} avatar{'s' if n != 1 else ''} visible{'s' if n != 1 else ''}"
            if text != "Tous les groupes"
            else f"{len(self.avatars_data)} avatar(s) visibles"
        )

    # =========================================================================
    # Utilitaires internes
    # =========================================================================

    def _update_info(self):
        n = len(self.avatars_data)
        self.info_label.setText(f"{n} avatar{'s' if n != 1 else ''}")

    def _status(self, msg: str):
        self._status_label.setText(msg)