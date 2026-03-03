# ============================================================================
# viewer_3d.py  —  Visualisation 3D des avatars LMGC90
# ============================================================================
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox
)
from PyQt6.QtCore import pyqtSignal

from ...core.models import Avatar, AvatarType


# ── Correspondance couleurs LMGC90 → PyVista ─────────────────────────────────
_COLOR_MAP = {
    'BLUEx': '#3a7ec8',
    'REDxx': '#d94040',
    'VERTx': '#3aaa5a',
    'JAUNx': '#e8c020',
    'GRAYx': '#909090',
    'BLACx': '#202020',
    'WHITx': '#f5f5f5',
    'ORANx': '#e87820',
    'CYANx': '#20c8c8',
    'MAGEx': '#c030c0',
    'VIOLx': '#8040c0',
    'ROSEx': '#e880a0',
}

_DEFAULT_COLOR  = '#80b0e0'
_WALL_COLOR     = '#b0b0b0'
_MESH_COLOR     = '#40c8a0'
_EXTRUSION_H    = 0.04   # épaisseur d'extrusion des formes 2D (en unités modèle)


def _lmgc_color(name: str) -> str:
    return _COLOR_MAP.get(name, _DEFAULT_COLOR)


# ── Helpers géométriques ──────────────────────────────────────────────────────

def _as3(center, z: float = 0.0):
    """Garantit un centre [x, y, z]."""
    if len(center) == 2:
        return [float(center[0]), float(center[1]), z]
    return [float(center[0]), float(center[1]), float(center[2])]


def _polygon_face(n_pts: int) -> list:
    """Retourne le tableau de connectivité d'un polygone pour pv.PolyData."""
    return [n_pts] + list(range(n_pts))


def _extrude(poly: pv.PolyData, h: float) -> pv.PolyData:
    return poly.extrude((0.0, 0.0, h), capping=True)


def _ellipse_poly(cx, cy, cz, a, b, n=64) -> pv.PolyData:
    """Crée un polygone elliptique fermé (n sommets) centré en (cx,cy,cz)."""
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pts = np.c_[
        cx + a * np.cos(theta),
        cy + b * np.sin(theta),
        np.full(n, cz)
    ]
    faces = _polygon_face(n)
    return pv.PolyData(pts, faces=faces)


# ── Constructeur de mesh par type ─────────────────────────────────────────────

def _mesh_rigid_disk(av: Avatar) -> pv.PolyData:
    c  = _as3(av.center)
    r  = av.radius or 0.1
    is2d = len(av.center) == 2
    if is2d:
        disk = pv.Disc(center=c, inner=0.0, outer=r, normal=(0, 0, 1), r_res=1, c_res=48)
        return _extrude(disk, _EXTRUSION_H)
    return pv.Sphere(center=c, radius=r, theta_resolution=32, phi_resolution=32)


def _mesh_rigid_sphere(av: Avatar) -> pv.PolyData:
    c = _as3(av.center)
    r = av.radius or 0.1
    return pv.Sphere(center=c, radius=r, theta_resolution=32, phi_resolution=32)


def _mesh_rigid_disk_discrete(av: Avatar) -> pv.PolyData:
    """RIGID_DISCRETE : disque discret — même rendu qu'un disque."""
    return _mesh_rigid_disk(av)


def _mesh_rigid_jonc(av: Avatar) -> pv.PolyData:
    """Jonc 2D = ellipse extrudée."""
    c   = _as3(av.center)
    a   = float((av.axis or {}).get('axe1', 0.2))
    b   = float((av.axis or {}).get('axe2', 0.1))
    poly = _ellipse_poly(c[0], c[1], c[2], a, b)
    return _extrude(poly, _EXTRUSION_H)


def _mesh_rigid_polygon(av: Avatar) -> pv.PolyData:
    """Polygone 2D extrudé."""
    c = _as3(av.center)
    if av.generation_type == "regular":
        n = av.nb_vertices or 6
        r = av.radius or 0.1
        theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
        pts = np.c_[
            c[0] + r * np.cos(theta),
            c[1] + r * np.sin(theta),
            np.full(n, c[2])
        ]
    else:
        if not av.vertices:
            return pv.Cube(center=c, x_length=0.1, y_length=0.1, z_length=_EXTRUSION_H)
        verts = np.array(av.vertices, dtype=float)
        pts = np.c_[
            c[0] + verts[:, 0],
            c[1] + verts[:, 1],
            np.full(len(verts), c[2])
        ]
    poly = pv.PolyData(pts, faces=_polygon_face(len(pts)))
    return _extrude(poly, _EXTRUSION_H)


def _mesh_rigid_ovoid(av: Avatar) -> pv.PolyData:
    """Ovoid = ellipse approximée par nb_vertices sommets, extrudée."""
    c  = _as3(av.center)
    wp = av.wall_params or {}
    ra = float(wp.get('ra', av.radius or 0.15))
    rb = float(wp.get('rb', ra * 0.6))
    n  = av.nb_vertices or 32
    poly = _ellipse_poly(c[0], c[1], c[2], ra, rb, n=n)
    return _extrude(poly, _EXTRUSION_H)


def _mesh_rigid_cluster(av: Avatar) -> pv.PolyData:
    """Cluster = ensemble de disques arrangés en cercle."""
    c      = _as3(av.center)
    r_body = av.radius or 0.1
    n_disk = av.nb_vertices or 4
    r_disk = r_body / (1 + n_disk / 2)

    meshes = []
    for i in range(n_disk):
        angle  = 2 * np.pi * i / n_disk
        offset = r_body - r_disk
        cx     = c[0] + offset * np.cos(angle)
        cy     = c[1] + offset * np.sin(angle)
        disk   = pv.Disc(center=[cx, cy, c[2]], inner=0.0, outer=r_disk,
                         normal=(0, 0, 1), r_res=1, c_res=24)
        meshes.append(_extrude(disk, _EXTRUSION_H))

    if not meshes:
        return pv.Sphere(center=c, radius=r_body)
    result = meshes[0]
    for m in meshes[1:]:
        result = result.merge(m)
    return result


def _mesh_rough_wall(av: Avatar) -> pv.PolyData:
    """Mur rugueux 2D : boîte allongée."""
    c  = _as3(av.center)
    wp = av.wall_params or {}
    l  = float(wp.get('l', 1.0))
    r  = float(wp.get('r', 0.05))
    return pv.Box(bounds=[
        c[0] - l / 2, c[0] + l / 2,
        c[1] - r,     c[1] + r,
        c[2],         c[2] + _EXTRUSION_H
    ])


def _mesh_fine_wall(av: Avatar) -> pv.PolyData:
    return _mesh_rough_wall(av)


def _mesh_smooth_wall(av: Avatar) -> pv.PolyData:
    """Mur lisse 2D : boîte avec hauteur h."""
    c  = _as3(av.center)
    wp = av.wall_params or {}
    l  = float(wp.get('l', 1.0))
    h  = float(wp.get('h', 0.1))
    return pv.Box(bounds=[
        c[0] - l / 2, c[0] + l / 2,
        c[1] - h / 2, c[1] + h / 2,
        c[2],         c[2] + _EXTRUSION_H
    ])


def _mesh_granulo_wall(av: Avatar) -> pv.PolyData:
    """Mur granulométrique 2D : similaire à rough_wall."""
    return _mesh_rough_wall(av)


def _mesh_rigid_plan(av: Avatar) -> pv.PolyData:
    """Plan 3D orienté selon axe1/axe2/axe3."""
    c    = _as3(av.center)
    axis = av.axis or {}
    # normal = axe3 si disponible, sinon Z
    if 'axe3' in axis:
        normal = [float(axis['axe3'][0]) if hasattr(axis['axe3'], '__len__') else 0,
                  float(axis['axe3'][1]) if hasattr(axis['axe3'], '__len__') else 0,
                  1.0]
    else:
        normal = (0, 0, 1)
    size = float(av.radius or 1.0)
    return pv.Plane(center=c, direction=normal, i_size=size * 2, j_size=size * 2,
                    i_resolution=4, j_resolution=4)


def _mesh_rigid_cylinder(av: Avatar) -> pv.PolyData:
    """Cylindre 3D."""
    c  = _as3(av.center)
    r  = av.radius or 0.1
    wp = av.wall_params or {}
    h  = float(wp.get('h', 0.2))
    return pv.Cylinder(center=c, direction=(0, 0, 1), radius=r, height=h,
                        resolution=32, capping=True)


def _mesh_rigid_polyhedron(av: Avatar) -> pv.PolyData:
    """Polyèdre 3D : convex hull des sommets ou sphère approximée."""
    c = _as3(av.center)
    if av.vertices and len(av.vertices) >= 4:
        try:
            verts = np.array(av.vertices, dtype=float)
            # Centrer sur le centre de l'avatar
            pts   = verts + np.array(c)
            cloud = pv.PolyData(pts)
            return cloud.delaunay_3d().extract_surface()
        except Exception:
            pass
    # Fallback : icosphère approximant le polyèdre
    r = av.radius or 0.1
    return pv.Sphere(center=c, radius=r, theta_resolution=16, phi_resolution=16)


def _mesh_rough_wall_3d(av: Avatar) -> pv.PolyData:
    """Mur rugueux 3D : boîte lx × ly × 2r."""
    c  = _as3(av.center)
    wp = av.wall_params or {}
    lx = float(wp.get('lx', 1.0))
    ly = float(wp.get('ly', 1.0))
    r  = av.radius or 0.05
    return pv.Box(bounds=[
        c[0] - lx / 2, c[0] + lx / 2,
        c[1] - ly / 2, c[1] + ly / 2,
        c[2] - r,      c[2] + r
    ])


def _mesh_granulo_rough_wall_3d(av: Avatar) -> pv.PolyData:
    return _mesh_rough_wall_3d(av)


def _mesh_empty_avatar(av: Avatar) -> pv.PolyData:
    """Avatar vide : rendu depuis ses contacteurs."""
    c = _as3(av.center)
    if not av.contactors:
        return pv.Sphere(center=c, radius=0.04)

    meshes = []
    is2d   = len(av.center) == 2

    for cont in av.contactors:
        shape  = cont.get('shape', '')
        params = cont.get('params', {})
        try:
            # ── 2D ────────────────────────────────────────────────────────────
            if shape in ('DISKx', 'xKSID'):
                r   = float(params.get('byrd', 0.1))
                inner = r * 0.6 if shape == 'xKSID' else 0.0
                disk = pv.Disc(center=c, inner=inner, outer=r,
                               normal=(0, 0, 1), r_res=1, c_res=40)
                meshes.append(_extrude(disk, _EXTRUSION_H))

            elif shape == 'JONCx':
                a   = float(params.get('axe1', 0.2))
                b   = float(params.get('axe2', 0.1))
                poly = _ellipse_poly(c[0], c[1], c[2], a, b)
                meshes.append(_extrude(poly, _EXTRUSION_H))

            elif shape == 'POLYG':
                vertices = params.get('vertices', [])
                if vertices:
                    verts = np.array(vertices, dtype=float)
                    pts   = np.c_[
                        c[0] + verts[:, 0],
                        c[1] + verts[:, 1],
                        np.full(len(verts), c[2])
                    ]
                    poly = pv.PolyData(pts, faces=_polygon_face(len(pts)))
                    meshes.append(_extrude(poly, _EXTRUSION_H))

            elif shape in ('PT2Dx',):
                meshes.append(pv.Sphere(center=c, radius=0.02))

            # ── 3D ────────────────────────────────────────────────────────────
            elif shape == 'SPHER':
                r = float(params.get('byrd', 0.1))
                meshes.append(pv.Sphere(center=c, radius=r,
                                         theta_resolution=24, phi_resolution=24))

            elif shape == 'PLANx':
                s = float(params.get('size', 1.0))
                meshes.append(pv.Plane(center=c, i_size=s, j_size=s))

            elif shape == 'CYLND':
                r = float(params.get('byrd', 0.1))
                h = float(params.get('height', 0.2))
                meshes.append(pv.Cylinder(center=c, radius=r, height=h,
                                           direction=(0, 0, 1), capping=True))

            elif shape in ('PT3Dx',):
                meshes.append(pv.Sphere(center=c, radius=0.02))

        except Exception as e:
            print(f"⚠️ Viewer — contacteur '{shape}' ignoré : {e}")

    if not meshes:
        return pv.Sphere(center=c, radius=0.04)
    result = meshes[0]
    for m in meshes[1:]:
        result = result.merge(m)
    return result


def _mesh_deformable(av: Avatar) -> pv.PolyData:
    """
    Corps déformable maillé (MESH_DEFORMABLE).
    Reconstruit la grille structurée depuis mesh_params pour afficher
    les éléments finis réels (arêtes des éléments visibles).

    Sources :
      rect2d  → plaque 2D maillée (nx × ny quad/tri), fine épaisseur
      box3d   → volume 3D maillé (nx × ny × nz hex), arêtes internes visibles
      file2d/3d → boîte englobante indicative (fichier non rechargé ici)
      None/inconnu → fallback boîte grise avec label
    """
    mp = av.mesh_params or {}
    source = mp.get('source', '')
    c = _as3(av.center)

    try:
        # ── RECT 2D ───────────────────────────────────────────────────────────
        if source == 'rect2d':
            lx   = float(mp.get('lx', 1.0))
            ly   = float(mp.get('ly', 1.0))
            x0   = float(mp.get('x0', c[0] - lx / 2))
            y0   = float(mp.get('y0', c[1] - ly / 2))
            nx   = int(mp.get('nx', 4))
            ny   = int(mp.get('ny', 4))
            zval = float(c[2])

            # Nœuds de la grille 2D
            xs = np.linspace(x0, x0 + lx, nx + 1)
            ys = np.linspace(y0, y0 + ly, ny + 1)
            XX, YY = np.meshgrid(xs, ys)
            pts = np.c_[XX.ravel(), YY.ravel(), np.full(XX.size, zval)]

            # Faces quad (4 sommets par élément)
            faces = []
            for j in range(ny):
                for i in range(nx):
                    bl = j * (nx + 1) + i
                    faces += [4, bl, bl + 1, bl + (nx + 1) + 1, bl + (nx + 1)]

            mesh = pv.PolyData(pts, np.array(faces))
            # Épaisseur très fine pour rester "plat" tout en étant visible
            return mesh.extrude((0.0, 0.0, max(lx, ly) * 0.02), capping=True)

        # ── BOX 3D ────────────────────────────────────────────────────────────
        elif source == 'box3d':
            lx = float(mp.get('lx', 1.0))
            ly = float(mp.get('ly', 1.0))
            lz = float(mp.get('lz', 1.0))
            x0 = float(mp.get('x0', c[0] - lx / 2))
            y0 = float(mp.get('y0', c[1] - ly / 2))
            z0 = float(mp.get('z0', c[2] - lz / 2))
            nx = int(mp.get('nx', 2))
            ny = int(mp.get('ny', 2))
            nz = int(mp.get('nz', 2))

            # Grille structurée 3D complète — on extrait les 6 faces
            # AVEC les arêtes internes grâce à la résolution nx/ny/nz
            xs = np.linspace(x0, x0 + lx, nx + 1)
            ys = np.linspace(y0, y0 + ly, ny + 1)
            zs = np.linspace(z0, z0 + lz, nz + 1)

            # Construire les faces des 6 faces du volume, avec maillage interne
            meshes = []

            def _face_grid(u_arr, v_arr, w_val, perm):
                """Construit une face maillée dans le plan (u,v) à w=w_val.
                perm = (iu, iv, iw) — indices pour permuter vers XYZ."""
                UU, VV = np.meshgrid(u_arr, v_arr)
                raw = np.zeros((UU.size, 3))
                raw[:, perm[0]] = UU.ravel()
                raw[:, perm[1]] = VV.ravel()
                raw[:, perm[2]] = w_val
                nu = len(u_arr) - 1
                nv = len(v_arr) - 1
                fcs = []
                for jj in range(nv):
                    for ii in range(nu):
                        bl = jj * (nu + 1) + ii
                        fcs += [4, bl, bl + 1, bl + (nu + 1) + 1, bl + (nu + 1)]
                return pv.PolyData(raw, np.array(fcs))

            # Face -Z et +Z
            meshes.append(_face_grid(xs, ys, z0,       (0, 1, 2)))
            meshes.append(_face_grid(xs, ys, z0 + lz,  (0, 1, 2)))
            # Face -Y et +Y
            meshes.append(_face_grid(xs, zs, y0,       (0, 2, 1)))
            meshes.append(_face_grid(xs, zs, y0 + ly,  (0, 2, 1)))
            # Face -X et +X
            meshes.append(_face_grid(ys, zs, x0,       (1, 2, 0)))
            meshes.append(_face_grid(ys, zs, x0 + lx,  (1, 2, 0)))

            result = meshes[0]
            for m in meshes[1:]:
                result = result.merge(m)
            return result

        # ── FICHIER EXTERNE ───────────────────────────────────────────────────
        elif source in ('file2d', 'file3d'):
            # On ne peut pas relire le fichier ici → boîte englobante indicative
            label = mp.get('filepath', 'fichier externe')
            print(f"ℹ️ Viewer — déformable fichier : {label!r} → boîte indicative")
            dim = 3 if source == 'file3d' else 2
            size = 0.5
            if dim == 2:
                poly = pv.Rectangle([
                    [c[0] - size, c[1] - size, c[2]],
                    [c[0] + size, c[1] - size, c[2]],
                    [c[0] + size, c[1] + size, c[2]],
                    [c[0] - size, c[1] + size, c[2]],
                ])
                return poly.extrude((0, 0, size * 0.04), capping=True)
            else:
                return pv.Box(bounds=[
                    c[0] - size, c[0] + size,
                    c[1] - size, c[1] + size,
                    c[2] - size, c[2] + size,
                ])

    except Exception as e:
        print(f"⚠️ Viewer — maillage déformable ({source!r}) : {e}")

    # ── FALLBACK (mesh_params absent = projet ancien) ─────────────────────────
    # On affiche une boîte semi-transparente avec les dimensions du center
    print(f"⚠️ Viewer — MESH_DEFORMABLE sans mesh_params, fallback boîte")
    size = 0.3
    return pv.Box(bounds=[
        c[0] - size, c[0] + size,
        c[1] - size, c[1] + size,
        c[2] - size, c[2] + size,
    ])


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


# ── Widget de visualisation ───────────────────────────────────────────────────

class Viewer3D(QWidget):
    """Widget de visualisation 3D des avatars LMGC90."""

    avatar_clicked = pyqtSignal(int)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller   = controller
        self.avatars_data = []   # liste de (index, Avatar)
        self.actors       = {}   # index → acteur PyVista
        self._setup_ui()

    # ── Interface ─────────────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Barre d'outils
        toolbar = QHBoxLayout()

        self.info_label = QLabel("0 avatar(s)")
        toolbar.addWidget(self.info_label)
        toolbar.addStretch()

        self._edges_check = QCheckBox("Arêtes")
        self._edges_check.setChecked(True)
        self._edges_check.toggled.connect(self._toggle_edges)
        toolbar.addWidget(self._edges_check)

        reset_btn = QPushButton("🔄 Réinitialiser vue")
        reset_btn.clicked.connect(self._reset_camera)
        toolbar.addWidget(reset_btn)

        xy_btn = QPushButton("Vue XY")
        xy_btn.setToolTip("Vue orthogonale 2D (axe Z)")
        xy_btn.clicked.connect(self._view_xy)
        toolbar.addWidget(xy_btn)

        clear_btn = QPushButton("🗑️ Effacer")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        # Plotter PyVista
        self.plotter = QtInteractor(self)
        self.plotter.set_background('#1a1a2e')   # fond sombre, contraste propre
        self.plotter.enable_anti_aliasing()
        layout.addWidget(self.plotter.interactor)

        self._add_scene_helpers()

    def _add_scene_helpers(self):
        """Ajoute axes et grille."""
        self.plotter.add_axes(
            xlabel='X', ylabel='Y', zlabel='Z',
            line_width=2, color='white'
        )
        grid = pv.Plane(
            center=(0, 0, 0), direction=(0, 0, 1),
            i_size=10, j_size=10, i_resolution=10, j_resolution=10
        )
        self.plotter.add_mesh(
            grid, color='#2a2a4a', opacity=0.4,
            show_edges=True, edge_color='#404060'
        )

    # ── API publique ──────────────────────────────────────────────────────────
    def add_avatar(self, avatar: Avatar, index: int):
        """Ajoute un avatar à la scène."""
        mesh = build_avatar_mesh(avatar)
        if mesh is None:
            return

        # Couleur : déformables en vert-cyan, murs en gris, reste selon color
        if avatar.avatar_type == AvatarType.MESH_DEFORMABLE:
            color = _MESH_COLOR
        elif avatar.avatar_type in (AvatarType.ROUGH_WALL, AvatarType.FINE_WALL,
                                    AvatarType.SMOOTH_WALL, AvatarType.GRANULO_WALL,
                                    AvatarType.ROUGH_WALL_3D,
                                    AvatarType.GRANULO_ROUGH_WALL_3D):
            color = _WALL_COLOR
        else:
            color = _lmgc_color(avatar.color)

        show_edges = self._edges_check.isChecked()

        actor = self.plotter.add_mesh(
            mesh,
            color=color,
            show_edges=show_edges,
            edge_color='#000000',
            opacity=0.85,
            pickable=True,
            smooth_shading=True
        )

        self.actors[index] = actor
        self.avatars_data.append((index, avatar))
        self._update_info()

    def update_avatars(self, avatars):
        """Recharge tous les avatars dans la scène."""
        self.clear()
        for i, av in enumerate(avatars):
            self.add_avatar(av, i)
        if avatars:
            self._reset_camera()

    def clear(self):
        """Efface tous les avatars."""
        self.plotter.clear()
        self.actors.clear()
        self.avatars_data.clear()
        self._add_scene_helpers()
        self._update_info()

    # ── Caméra ────────────────────────────────────────────────────────────────
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
        """Vue orthogonale 2D (plan XY, axe Z vers l'observateur)."""
        self.plotter.view_xy()
        self.plotter.camera.parallel_projection = True
        self.plotter.reset_camera()

    # ── Arêtes ────────────────────────────────────────────────────────────────
    def _toggle_edges(self, show: bool):
        """Active/désactive les arêtes sur tous les acteurs."""
        for actor in self.actors.values():
            try:
                prop = actor.GetProperty()
                prop.SetEdgeVisibility(int(show))
            except Exception:
                pass
        self.plotter.render()

    # ── Info ──────────────────────────────────────────────────────────────────
    def _update_info(self):
        n = len(self.avatars_data)
        self.info_label.setText(f"{n} avatar{'s' if n > 1 else ''}")