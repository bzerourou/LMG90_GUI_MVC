# ============================================================================
# viewer_3d.py  —  Visualisation 3D des avatars LMGC90
# ============================================================================
"""
Viewer PyVista/Qt6 v0.2 pour LMGC90_GUI.

Fonctionnalités
───────────────
  Rendu paramétrique : tous les avatars rigides 2D/3D, corps déformables,
                       murs, clusters, avatars vides / maçonnerie
  Rendu pylmgc90     : mode « 🔬 pylmgc90 » — utilise pre.visuAvatars() pour
                       un rendu haute fidélité quand la bibliothèque est installée
  Corps déformables  : handle des sources GUI (geom='Rectangle'…) et des sources
                       convert.py (source='buildMesh2D', source_type='built2D'…)
                       + affichage des groupes de contacteurs
  Modes couleur      : palette LMGC90 / par type / par matériau / par origine
  DOF visuels        : flèches indiquant les conditions aux limites imposées
  Navigation         : orbit, zoom, pan, vues XY/XZ/YZ/isométrique
  Arêtes             : toggle show_edges
  Sélection          : clic gauche → highlight + signal avatar_clicked(index)
  Mesure             : mode Règle — clic A puis B → distance + signal
  Groupes            : filtre visibilité par groupe d'avatars
  Export             : capture PNG de la scène
"""

import math
import os
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from typing import Dict, List, Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QCheckBox, QComboBox, QSizePolicy,
    QToolButton, QFrame, QButtonGroup, QFileDialog,
    QSlider,
)
from PyQt6.QtCore import pyqtSignal, Qt

from ...core.models import Avatar, AvatarType, AvatarOrigin
from ...core.particle_population import ParticlePopulation


# ============================================================================
# Couleurs et constantes
# ============================================================================

# Palette complète LMGC90 → HTML
_COLOR_MAP: Dict[str, str] = {
    'BLUEx': '#3a7ec8', 'REDxx': '#d94040', 'VERTx': '#3aaa5a',
    'GREEx': '#3aaa5a', 'JAUNx': '#e8c020', 'GRAYx': '#909090',
    'BLACx': '#202020', 'WHITx': '#f5f5f5', 'ORANx': '#e87820',
    'CYANx': '#20c8c8', 'MAGEx': '#c030c0', 'VIOLx': '#8040c0',
    'ROSEx': '#e880a0', 'BROWx': '#8b5e3c', 'GOLDx': '#d4a017',
    'SILVx': '#c0c0c0', 'TURQx': '#30d5c8',
}

# Couleurs par type d'avatar (mode "par type")
_TYPE_COLORS: Dict[AvatarType, str] = {
    AvatarType.RIGID_DISK:            '#3a7ec8',
    AvatarType.RIGID_SPHERE:          '#2a6eb8',
    AvatarType.RIGID_JONC:            '#5a9ee8',
    AvatarType.RIGID_POLYGON:         '#4a8ed8',
    AvatarType.RIGID_OVOID:           '#6aaee8',
    AvatarType.RIGID_DISCRETE:        '#3a7ec8',
    AvatarType.RIGID_CLUSTER:         '#7abef8',
    AvatarType.ROUGH_WALL:            '#b0b0b0',
    AvatarType.FINE_WALL:             '#c0c0c0',
    AvatarType.SMOOTH_WALL:           '#d0d0d0',
    AvatarType.GRANULO_WALL:          '#a0a0a0',
    AvatarType.RIGID_PLAN:            '#909090',
    AvatarType.RIGID_CYLINDER:        '#5a9ec8',
    AvatarType.RIGID_POLYHEDRON:      '#4a8ec8',
    AvatarType.ROUGH_WALL_3D:         '#b0b0b0',
    AvatarType.GRANULO_ROUGH_WALL_3D: '#a0a0a0',
    AvatarType.EMPTY_AVATAR:          '#e0c080',
    AvatarType.MESH_DEFORMABLE:       '#40c8a0',
}

# Couleurs par origine
_ORIGIN_COLORS: Dict[str, str] = {
    'manual':   '#3a7ec8',
    'loop':     '#3aaa5a',
    'granulo':  '#e87820',
    'masonry':  '#8b5e3c',
    'mesh':     '#40c8a0',
}

_DEFAULT_COLOR  = '#80b0e0'
_WALL_COLOR     = '#b0b0b0'
_MESH_COLOR     = '#40c8a0'
_SELECT_COLOR   = '#ffcc00'
_MEASURE_COLOR  = '#ff4444'
_DOF_COLOR      = '#ff8800'

# Opacité par catégorie
_OPACITY_RIGID    = 0.92
_OPACITY_WALL     = 0.80
_OPACITY_MESH     = 0.65   # déformable : semi-transparent pour voir la structure
_OPACITY_EMPTY    = 0.85
_OPACITY_BATCH    = 0.90   # granulo batch

# Hauteur d'extrusion 2D → 3D (en fraction du rayon/taille caractéristique)
_EXTRUDE_RATIO    = 0.12   # hauteur = max(lx,ly) * ratio
_EXTRUDE_MIN      = 0.005
_EXTRUDE_DEFAULT  = 0.04

# Résolutions
_CIRCLE_RES  = 64
_SPHERE_RES  = 24
_ELLIPSE_RES = 80

# Sources reconnues pour les corps déformables (GUI et convert.py)
_MESH_SRC_RECT   = {'rect2d', 'Rectangle',   'buildMesh2D', 'built2D'}
_MESH_SRC_BOX    = {'box3d',  'Boîte (H8)',  'buildMeshH8', 'builtH8'}
_MESH_SRC_DISK   = {'disk2d', 'Disque'}
_MESH_SRC_SPHERE = {'sphere3d', 'Sphère'}
_MESH_SRC_CYL    = {'cylinder3d', 'Cylindre'}
_MESH_SRC_FILE   = {'file2d', 'file3d', 'Fichier externe', 'file', 'readMesh'}


# ============================================================================
# Utilitaires géométriques
# ============================================================================

def _lmgc_color(name: str) -> str:
    """Retourne la couleur HTML correspondant au code LMGC90."""
    return _COLOR_MAP.get(name, _DEFAULT_COLOR)


def _as3(center, z: float = 0.0) -> List[float]:
    """Garantit un centre 3D [x, y, z]."""
    if len(center) == 3:
        return list(center)
    return [float(center[0]), float(center[1]), z]


def _polygon_face(n_pts: int) -> list:
    return [n_pts] + list(range(n_pts))


def _extrude_h(characteristic_size: float) -> float:
    """Hauteur d'extrusion adaptative."""
    return max(_EXTRUDE_MIN, characteristic_size * _EXTRUDE_RATIO)


def _extrude(poly: pv.PolyData, h: float) -> pv.PolyData:
    return poly.extrude((0, 0, h), capping=True)


def _ellipse_poly(cx: float, cy: float, cz: float,
                  a: float, b: float, n: int = _ELLIPSE_RES) -> pv.PolyData:
    t   = np.linspace(0, 2 * math.pi, n, endpoint=False)
    pts = np.column_stack([cx + a * np.cos(t), cy + b * np.sin(t),
                           np.full(n, cz)])
    return pv.PolyData(pts, _polygon_face(n))


def _rect_poly(cx: float, cy: float, cz: float,
               lx: float, ly: float) -> pv.PolyData:
    """Rectangle centré en (cx, cy, cz)."""
    x0, y0 = cx - lx / 2, cy - ly / 2
    pts = np.array([
        [x0,      y0,      cz],
        [x0 + lx, y0,      cz],
        [x0 + lx, y0 + ly, cz],
        [x0,      y0 + ly, cz],
    ])
    return pv.PolyData(pts, [4, 0, 1, 2, 3])


def _arrow_mesh(origin, direction, scale: float = 0.05) -> pv.PolyData:
    """Petite flèche pour visualiser une contrainte DOF."""
    d = np.array(direction, dtype=float)
    n = np.linalg.norm(d)
    if n > 1e-10:
        d /= n
    return pv.Arrow(start=np.array(origin, dtype=float) - d * scale * 0.5,
                    direction=d, tip_length=0.4, tip_radius=0.2,
                    shaft_radius=0.08, scale=scale)


# ============================================================================
# Constructeurs de maillage par type d'avatar
# ============================================================================

def _mesh_rigid_disk(av: Avatar) -> pv.PolyData:
    c = _as3(av.center)
    r = av.radius or 0.1
    d = pv.Circle(radius=r, resolution=_CIRCLE_RES)
    d.points += np.array(c)
    return _extrude(d, _extrude_h(r))


def _mesh_rigid_sphere(av: Avatar) -> pv.PolyData:
    return pv.Sphere(center=_as3(av.center), radius=av.radius or 0.1,
                     theta_resolution=_SPHERE_RES, phi_resolution=_SPHERE_RES)


def _mesh_rigid_disk_discrete(av: Avatar) -> pv.PolyData:
    """rigidDiscreteDisk — rendu identique au disk avec indication discrète."""
    return _mesh_rigid_disk(av)


def _mesh_rigid_jonc(av: Avatar) -> pv.PolyData:
    c  = _as3(av.center)
    ax = av.axis or {}
    a  = float(ax.get('axe1', av.radius or 0.2))
    b  = float(ax.get('axe2', av.radius or 0.1))
    return _extrude(_ellipse_poly(c[0], c[1], c[2], a, b), _extrude_h(max(a, b)))


def _mesh_rigid_polygon(av: Avatar) -> pv.PolyData:
    c     = _as3(av.center)
    verts = av.vertices
    if verts and len(verts) >= 3:
        pts  = np.array([_as3(v, c[2]) for v in verts])
        poly = pv.PolyData(pts, _polygon_face(len(pts)))
    else:
        n = av.nb_vertices or 6
        r = av.radius or 0.1
        t = np.linspace(0, 2 * math.pi, n, endpoint=False)
        pts = np.column_stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t),
                               np.full(n, c[2])])
        poly = pv.PolyData(pts, _polygon_face(n))
    r_char = float(av.radius or 0.1)
    return _extrude(poly, _extrude_h(r_char))


def _mesh_rigid_ovoid(av: Avatar) -> pv.PolyData:
    """
    rigidOvoidPolygon : semi-axes ra / rb dans wall_params
    (axe1/axe2 dans av.axis pour compatibilité ancienne sérialisation).
    """
    c  = _as3(av.center)
    wp = av.wall_params or {}
    ax = av.axis or {}
    # Priorité : wall_params (ra, rb) > axis (axe1, axe2) > radius
    a  = float(wp.get('ra', ax.get('axe1', av.radius or 0.15)))
    b  = float(wp.get('rb', ax.get('axe2', (av.radius or 0.15) * 0.6)))
    return _extrude(_ellipse_poly(c[0], c[1], c[2], a, b, n=_ELLIPSE_RES),
                    _extrude_h(max(a, b)))


def _mesh_rigid_cluster(av: Avatar) -> pv.PolyData:
    """rigidCluster : disques individuels depuis contactors, ou disque unique."""
    meshes = []
    for cont in (av.contactors or []):
        shape = cont.get('shape', '').upper()
        if shape.startswith('DISK') or shape.startswith('CLxx'):
            cc = _as3(cont.get('center', av.center))
            r  = float(cont.get('radius', av.radius or 0.05))
            d  = pv.Circle(radius=r, resolution=32)
            d.points += np.array(cc)
            meshes.append(_extrude(d, _extrude_h(r)))
    if not meshes:
        # Fallback : cluster de nb_vertices disques en couronne
        n  = av.nb_vertices or 3
        r  = av.radius or 0.05
        c  = _as3(av.center)
        R  = r * 1.5
        for k in range(n):
            angle = 2 * math.pi * k / n
            cc    = [c[0] + R * math.cos(angle), c[1] + R * math.sin(angle), c[2]]
            d     = pv.Circle(radius=r, resolution=32)
            d.points += np.array(cc)
            meshes.append(_extrude(d, _extrude_h(r)))
    result = meshes[0]
    for m in meshes[1:]:
        result = result.merge(m)
    return result


# ── Murs 2D ──────────────────────────────────────────────────────────────────

def _wall_box_2d(av: Avatar) -> pv.PolyData:
    """
    Génère une boîte plate pour tous les murs 2D.
    Lit lx/ly (nouveau convert.py) avec repli sur l/r (ancienne API).
    """
    c  = _as3(av.center)
    wp = av.wall_params or {}
    # Longueur : lx (nouveau) | l (ancien) | radius | 1.0
    lx = float(wp.get('lx', wp.get('l', av.radius or 1.0)))
    # Épaisseur : ly (nouveau) | r (ancien roughWall) | h (smoothWall) | 0.05
    ly = float(wp.get('ly', wp.get('r', wp.get('h', 0.05))))
    poly = _rect_poly(c[0], c[1], c[2], lx, ly)
    return _extrude(poly, _extrude_h(lx))


def _mesh_rough_wall(av: Avatar) -> pv.PolyData:
    return _wall_box_2d(av)


def _mesh_fine_wall(av: Avatar) -> pv.PolyData:
    return _wall_box_2d(av)


def _mesh_smooth_wall(av: Avatar) -> pv.PolyData:
    """smoothWall : rendu légèrement plus fin pour le distinguer."""
    c  = _as3(av.center)
    wp = av.wall_params or {}
    lx = float(wp.get('lx', wp.get('l', av.radius or 1.0)))
    ly = float(wp.get('ly', wp.get('h', 0.05)))
    # Arrondir les angles en utilisant plus de segments sur la section
    pts = []
    segs = 3
    h_h  = ly / 2
    for k in range(segs + 1):
        xk = c[0] - lx / 2 + k * lx / segs
        pts += [[xk, c[1] - h_h, c[2]], [xk, c[1] + h_h, c[2]]]
    return pv.Spline(np.array([[c[0] - lx/2, c[1], c[2]],
                               [c[0] + lx/2, c[1], c[2]]]),
                     n_points=max(10, int(lx * 100))).tube(radius=max(0.003, h_h * 0.5))


def _mesh_granulo_wall(av: Avatar) -> pv.PolyData:
    return _wall_box_2d(av)


# ── Avatars 3D ────────────────────────────────────────────────────────────────

def _mesh_rigid_plan(av: Avatar) -> pv.PolyData:
    """
    rigidPlan 3D : plan rectangulaire.
    Dimensions depuis av.axis (axe1, axe2, axe3 = demi-côtés).
    La normale est déduite de axe3 (vecteur hors plan).
    """
    c  = _as3(av.center)
    ax = av.axis or {}
    wp = av.wall_params or {}
    # Demi-côtés (axe1/axe2 = dimensions du plan, axe3 = épaisseur)
    a1 = float(ax.get('axe1', wp.get('lx', av.radius or 0.5)))
    a2 = float(ax.get('axe2', wp.get('ly', av.radius or 0.5)))
    a3 = float(ax.get('axe3', 0.02))
    lx, ly, lz = 2 * a1, 2 * a2, max(0.005, 2 * a3)
    # Plan ≈ boîte très plate
    return pv.Box(bounds=[
        c[0] - lx/2, c[0] + lx/2,
        c[1] - ly/2, c[1] + ly/2,
        c[2] - lz/2, c[2] + lz/2,
    ])


def _mesh_rigid_sphere(av: Avatar) -> pv.PolyData:
    return pv.Sphere(center=_as3(av.center), radius=av.radius or 0.1,
                     theta_resolution=_SPHERE_RES, phi_resolution=_SPHERE_RES)


def _mesh_rigid_cylinder(av: Avatar) -> pv.PolyData:
    """
    rigidCylinder 3D.
    h depuis wall_params['h'] ou wall_params['lz'] (au lieu de axis['height']).
    """
    c  = _as3(av.center)
    r  = av.radius or 0.1
    wp = av.wall_params or {}
    h  = float(wp.get('h', wp.get('lz', r * 2)))
    return pv.Cylinder(center=c, radius=r, height=h,
                       direction=(0, 0, 1), resolution=32, capping=True)


def _mesh_rigid_polyhedron(av: Avatar) -> pv.PolyData:
    """
    rigidPolyhedron 3D : vertices + faces explicites, ou génération régulière.
    """
    c     = _as3(av.center)
    verts = av.vertices
    wp    = av.wall_params or {}
    faces_data = wp.get('faces')

    if verts and len(verts) >= 4 and faces_data:
        # Polyèdre avec connectivité explicite
        try:
            pts   = np.array([_as3(v) for v in verts], dtype=float)
            faces = []
            for f in faces_data:
                if isinstance(f, (list, tuple)):
                    faces += [len(f)] + list(f)
                else:
                    faces.append(int(f))
            return pv.PolyData(pts, np.array(faces))
        except Exception:
            pass

    if verts and len(verts) >= 4:
        # Enveloppe convexe
        try:
            pts = np.array([_as3(v) for v in verts], dtype=float)
            cloud = pv.PolyData(pts)
            hull  = cloud.delaunay_3d()
            return hull.extract_surface()
        except Exception:
            pass

    # Génération régulière : icosphère / dodécaèdre
    r = av.radius or 0.1
    n = av.nb_vertices or 8
    if n <= 6:
        return pv.PlatonicSolid('octahedron').scale(r).translate(c)
    if n <= 12:
        return pv.PlatonicSolid('dodecahedron').scale(r * 0.6).translate(c)
    return pv.Sphere(center=c, radius=r,
                     theta_resolution=max(4, n // 2),
                     phi_resolution=max(4, n // 2))


def _mesh_rough_wall_3d(av: Avatar) -> pv.PolyData:
    """
    roughWall3D : dalle plane 3D.
    Dimensions depuis wall_params['lx'] / wall_params['ly'], épaisseur = radius.
    """
    c  = _as3(av.center)
    wp = av.wall_params or {}
    lx = float(wp.get('lx', av.radius or 1.0))
    ly = float(wp.get('ly', av.radius or 1.0))
    r  = av.radius or 0.05
    return pv.Box(bounds=[
        c[0] - lx/2, c[0] + lx/2,
        c[1] - ly/2, c[1] + ly/2,
        c[2] - r,    c[2] + r,
    ])


def _mesh_granulo_rough_wall_3d(av: Avatar) -> pv.PolyData:
    return _mesh_rough_wall_3d(av)


# ── Avatar vide / maçonnerie ──────────────────────────────────────────────────

def _mesh_empty_avatar(av: Avatar) -> pv.PolyData:
    """
    emptyAvatar :
    • Si wall_params présent (brique maçonnerie) → boîte aux bonnes dimensions.
    • Si contactors présent → rendu de chaque contacteur.
    • Fallback → petite boîte indicative.

    Gère les deux nomenclatures :
      - Ancienne sérialisation :  l / h / r
      - Nouvelle (convert.py) :  lx / ly / lz
    """
    c  = _as3(av.center)
    wp = av.wall_params or {}

    # ── Brique maçonnerie ────────────────────────────────────────────────────
    if wp and 'brick_name' in wp or (wp and not av.contactors):
        lx = float(wp.get('lx', wp.get('l', 0.20)))
        ly = float(wp.get('ly', wp.get('h', 0.065)))
        lz = float(wp.get('lz', ly))
        # Petite encoche sur la face avant pour distinguer l'orientation
        box = pv.Box(bounds=[
            c[0] - lx/2, c[0] + lx/2,
            c[1] - ly/2, c[1] + ly/2,
            c[2],        c[2] + lz,
        ])
        return box

    # ── Contacteurs explicites ────────────────────────────────────────────────
    meshes = []
    for cont in (av.contactors or []):
        shape = cont.get('shape', '').upper()
        cc    = _as3(cont.get('center', c))

        if shape.startswith('DISK') or shape.startswith('CLxx'):
            r = float(cont.get('radius', 0.05))
            d = pv.Circle(radius=r, resolution=32)
            d.points += np.array(cc)
            meshes.append(_extrude(d, _extrude_h(r)))

        elif shape.startswith('POLYR') or shape.startswith('CLALp') or shape.startswith('POLYG'):
            verts = cont.get('vertices', [])
            if len(verts) >= 3:
                pts  = np.array([_as3(v, cc[2]) for v in verts])
                poly = pv.PolyData(pts, _polygon_face(len(pts)))
                meshes.append(_extrude(poly, _extrude_h(0.1)))

        elif shape.startswith('SPHER'):
            r = float(cont.get('radius', 0.05))
            meshes.append(pv.Sphere(center=cc, radius=r,
                                    theta_resolution=16, phi_resolution=16))

        elif shape.startswith('CYLND'):
            r = float(cont.get('radius', 0.05))
            h = float(cont.get('height', r * 2))
            meshes.append(pv.Cylinder(center=cc, radius=r, height=h,
                                      direction=(0, 0, 1)))

        elif shape.startswith('JONCx') or shape.startswith('JONC'):
            a = float(cont.get('axe1', 0.1))
            b = float(cont.get('axe2', 0.05))
            meshes.append(_extrude(_ellipse_poly(cc[0], cc[1], cc[2], a, b),
                                   _extrude_h(max(a, b))))

        elif shape.startswith('PT2D') or shape.startswith('PT3D') or shape.startswith('NODE'):
            # Point contacteur : petite sphère
            meshes.append(pv.Sphere(center=cc, radius=0.01))

    if not meshes:
        # Fallback : petite boîte indicative centrée
        s = 0.02
        meshes.append(pv.Box(bounds=[c[0]-s, c[0]+s, c[1]-s, c[1]+s, c[2], c[2]+s]))

    result = meshes[0]
    for m in meshes[1:]:
        result = result.merge(m)
    return result


# ── Corps déformables (maillés) ───────────────────────────────────────────────

def _mesh_deformable(av: Avatar) -> Optional[pv.PolyData]:
    """
    Reconstruit la grille d'un corps déformable.

    Gère deux formats de mesh_params.

    """
    c   = _as3(av.center)
    mp  = av.mesh_params or {}

    # Résoudre la source depuis l'un ou l'autre format
    geom        = mp.get('geom', '')
    source      = mp.get('source', '')
    source_type = mp.get('source_type', '')

    # Résolution unifiée de la source
    effective_src = geom or source or source_type

    try:
        # ── Fichier externe ──────────────────────────────────────────────────
        if effective_src in _MESH_SRC_FILE or mp.get('filepath') or mp.get('mesh_file'):
            filepath = (mp.get('mesh_file') or mp.get('filepath') or '').strip()
            if filepath and os.path.isfile(filepath):
                return _read_mesh_file(filepath, center=c)
            # Fichier absent → boîte placeholder avec indicateur
            size = 0.5
            return pv.Box(bounds=[c[0]-size, c[0]+size,
                                   c[1]-size, c[1]+size,
                                   c[2]-size, c[2]+size])

        # ── Maillage buildMeshedAvatar : déléguer à la source interne ────────
        if source == 'buildMeshedAvatar' or source_type == 'meshed_avatar':
            inner_src  = mp.get('mesh_source', 'buildMesh2D')
            inner_type = mp.get('mesh_source_type', 'built2D')
            effective_src = inner_src or inner_type

        # ── Rectangle 2D (GUI rect2d / convert.py buildMesh2D) ──────────────
        if effective_src in _MESH_SRC_RECT:
            lx = float(mp.get('lx', 1.0))
            ly = float(mp.get('ly', 1.0))
            # GUI: nx/ny  |  convert.py: nb_elem_x/nb_elem_y
            nx = max(2, int(mp.get('nx', mp.get('nb_elem_x', 4))))
            ny = max(2, int(mp.get('ny', mp.get('nb_elem_y', 4))))
            x0, y0 = c[0] - lx / 2, c[1] - ly / 2
            xs = np.linspace(x0, x0 + lx, nx + 1)
            ys = np.linspace(y0, y0 + ly, ny + 1)
            XX, YY = np.meshgrid(xs, ys)
            pts    = np.column_stack([XX.ravel(), YY.ravel(),
                                      np.full(XX.size, c[2])])
            faces  = []
            for j in range(ny):
                for i in range(nx):
                    a = j * (nx + 1) + i
                    faces += [4, a, a + 1, a + nx + 2, a + nx + 1]
            mesh = pv.PolyData(pts, np.array(faces))
            return mesh

        # ── Boîte H8 3D (GUI box3d / convert.py buildMeshH8) ────────────────
        if effective_src in _MESH_SRC_BOX:
            lx = float(mp.get('lx', 1.0))
            ly = float(mp.get('ly', 1.0))
            lz = float(mp.get('lz', 1.0))
            nx = max(2, int(mp.get('nx', mp.get('nb_elem_x', 2))))
            ny = max(2, int(mp.get('ny', mp.get('nb_elem_y', 2))))
            nz = max(2, int(mp.get('nz', mp.get('nb_elem_z', 2))))
            x0, y0, z0 = c[0] - lx/2, c[1] - ly/2, c[2] - lz/2
            xs = np.linspace(x0, x0 + lx, nx + 1)
            ys = np.linspace(y0, y0 + ly, ny + 1)
            zs = np.linspace(z0, z0 + lz, nz + 1)

            def _face_grid(u_arr, v_arr, w_val, perm):
                UU, VV = np.meshgrid(u_arr, v_arr)
                pts_f  = np.zeros((UU.size, 3))
                pts_f[:, perm[0]] = UU.ravel()
                pts_f[:, perm[1]] = VV.ravel()
                pts_f[:, perm[2]] = w_val
                nu, nv  = len(u_arr) - 1, len(v_arr) - 1
                faces_f = []
                for jj in range(nv):
                    for ii in range(nu):
                        a = jj * (nu + 1) + ii
                        faces_f += [4, a, a + 1, a + nu + 2, a + nu + 1]
                return pv.PolyData(pts_f, np.array(faces_f))

            sides = [
                _face_grid(xs, ys, z0,      (0, 1, 2)),
                _face_grid(xs, ys, z0 + lz, (0, 1, 2)),
                _face_grid(xs, zs, y0,      (0, 2, 1)),
                _face_grid(xs, zs, y0 + ly, (0, 2, 1)),
                _face_grid(ys, zs, x0,      (1, 2, 0)),
                _face_grid(ys, zs, x0 + lx, (1, 2, 0)),
            ]
            result = sides[0]
            for s in sides[1:]:
                result = result.merge(s)
            return result

        # ── Disque 2D ────────────────────────────────────────────────────────
        if effective_src in _MESH_SRC_DISK:
            r = float(mp.get('r', 0.5))
            return pv.Disc(center=c, inner=0.0, outer=r,
                           r_res=max(2, mp.get('nr', 4)),
                           c_res=max(8, mp.get('ntheta', 24)))

        # ── Sphère 3D ────────────────────────────────────────────────────────
        if effective_src in _MESH_SRC_SPHERE:
            r = float(mp.get('r', 0.5))
            return pv.Sphere(center=c, radius=r,
                             theta_resolution=max(6, mp.get('ntheta', 16)),
                             phi_resolution  =max(6, mp.get('nphi',   16)))

        # ── Cylindre 3D ──────────────────────────────────────────────────────
        if effective_src in _MESH_SRC_CYL:
            r = float(mp.get('r', 0.3))
            h = float(mp.get('h', 1.0))
            return pv.Cylinder(center=c, radius=r, height=h,
                               resolution=max(8, mp.get('ntheta', 24)),
                               capping=True)

    except Exception as e:
        print(f"⚠️ Viewer — maillage déformable ({effective_src!r}) : {e}")

    # Fallback : boîte avec annotations de taille
    size = max(0.2, float(mp.get('lx', mp.get('r', 0.3))))
    return pv.Box(bounds=[c[0]-size, c[0]+size,
                           c[1]-size, c[1]+size,
                           c[2]-size, c[2]+size])


# ============================================================================
# Lecture de fichier maillage externe
# ============================================================================

def _read_mesh_file(filepath: str, center=None) -> pv.PolyData:
    """
    Lit un fichier .msh, .geo, .vtk, .vtu, .vtp, .stl… via pyvista.read().
    Pour .geo (script gmsh), génère d'abord le maillage via le module gmsh.
    Centre le résultat si demandé.
    """
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

    surface = mesh.extract_surface() if hasattr(mesh, 'extract_surface') else mesh

    if center is not None:
        bb   = surface.bounds
        cx_m = (bb[0] + bb[1]) / 2
        cy_m = (bb[2] + bb[3]) / 2
        cz_m = (bb[4] + bb[5]) / 2
        surface.points += np.array([center[0] - cx_m,
                                     center[1] - cy_m,
                                     center[2] - cz_m])
    return surface


# ============================================================================
# Intégration pre.visuAvatars()
# ============================================================================

def _render_via_pylmgc90(avatars: List[Avatar], controller) -> Optional[pv.MultiBlock]:
    """
    Génère les meshes via le pipeline pylmgc90 :
      1. Crée les objets pylmgc90 (LMGC90Bridge)
      2. Appelle pre.visuAvatars() dans un répertoire temporaire
      3. Charge et retourne les fichiers VTP générés

    Retourne None si pylmgc90 n'est pas installé ou si la génération échoue.
    La valeur retournée est un pv.MultiBlock avec un bloc par fichier VTP.
    """
    import tempfile, shutil
    try:
        from pylmgc90 import pre as pylmgc_pre
        from ...core.pylmgc_bridge import LMGC90Bridge

        state = controller.state
        mats  = {m.name: m for m in state.materials}
        mods  = {m.name: m for m in state.models}

        bodies_container = pylmgc_pre.avatars()
        n_ok = 0

        for av in avatars:
            mat = mats.get(av.material_name)
            mod = mods.get(av.model_name)
            if mat is None or mod is None:
                continue
            try:
                mat_obj = LMGC90Bridge.create_material(mat)
                mod_obj = LMGC90Bridge.create_model(mod)
                av_obj  = LMGC90Bridge.create_avatar(av, mod_obj, mat_obj)
                for op in getattr(state, 'operations', []) or []:
                    applies = op.operation_type == 'rotate' and (
                        op.target_type == 'avatar' and op.target_value == av.avatar_id
                        or op.target_type == 'group'
                        and av.avatar_id in state.avatar_groups.get(
                            op.target_value, []
                        )
                    )
                    if applies:
                        LMGC90Bridge.apply_dof_operation(op, av_obj)
                bodies_container += av_obj
                n_ok += 1
            except Exception:
                pass

        if n_ok == 0:
            return None

        tmpdir      = tempfile.mkdtemp()
        display_dir = os.path.join(tmpdir, 'DISPLAY')
        os.makedirs(display_dir, exist_ok=True)

        try:
            pylmgc_pre.visuAvatars(bodies=bodies_container, pathToFile=tmpdir)
        except Exception as e:
            print(f"⚠️ visuAvatars : {e}")
            shutil.rmtree(tmpdir, ignore_errors=True)
            return None

        # Collecter les fichiers générés
        vtp_files = []
        for root, _, files in os.walk(tmpdir):
            for f in files:
                if f.endswith(('.vtp', '.vtk', '.vtu')):
                    vtp_files.append(os.path.join(root, f))

        if not vtp_files:
            shutil.rmtree(tmpdir, ignore_errors=True)
            return None

        result = pv.MultiBlock()
        for vtp in vtp_files:
            try:
                block = pv.read(vtp)
                name  = os.path.splitext(os.path.basename(vtp))[0]
                result.append(block, name)
            except Exception:
                pass

        shutil.rmtree(tmpdir, ignore_errors=True)
        return result if result.n_blocks > 0 else None

    except ImportError:
        return None
    except Exception as e:
        print(f"⚠️ Viewer — pipeline pylmgc90 : {e}")
        return None


# ============================================================================
# Table de dispatch
# ============================================================================

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

_WALL_TYPES = {
    AvatarType.ROUGH_WALL, AvatarType.FINE_WALL,
    AvatarType.SMOOTH_WALL, AvatarType.GRANULO_WALL,
    AvatarType.ROUGH_WALL_3D, AvatarType.GRANULO_ROUGH_WALL_3D,
    AvatarType.RIGID_PLAN,
}


def build_avatar_mesh(avatar: Avatar) -> Optional[pv.PolyData]:
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


def _apply_avatar_rotations(mesh: pv.PolyData, avatar: Avatar, controller) -> pv.PolyData:
    """Rejoue les rotations DOF sur le mesh paramétrique de l'avatar."""
    state = getattr(controller, 'state', None)
    operations = getattr(state, 'operations', []) if state is not None else []
    for operation in operations or []:
        targets_avatar = (
            operation.target_type == 'avatar'
            and operation.target_value == avatar.avatar_id
        )
        targets_group = (
            operation.target_type == 'group'
            and avatar.avatar_id in state.avatar_groups.get(
                operation.target_value, []
            )
        ) if state is not None else False
        if operation.operation_type != 'rotate' or not (targets_avatar or targets_group):
            continue

        parameters = operation.parameters
        if parameters.get('description') != 'axis':
            continue
        axis = parameters.get('axis')
        alpha = parameters.get('alpha')
        if axis is None or alpha is None:
            continue
        mesh.rotate_vector(axis, np.degrees(float(alpha)), point=_as3(avatar.center), inplace=True)
    return mesh


def _expand_renderables(renderables) -> List[Tuple[int, Avatar]]:
    """Transforme les avatars et les populations en une séquence d'avatars rendables."""
    expanded: List[Tuple[int, Avatar]] = []
    for item in renderables or []:
        if isinstance(item, ParticlePopulation):
            for i in range(len(item)):
                expanded.append((len(expanded), item.as_avatar_view(i)))
        elif isinstance(item, Avatar):
            expanded.append((len(expanded), item))
    return expanded


# ============================================================================
# Utilitaires couleur et style
# ============================================================================

def _color_for_avatar(av: Avatar, mode: str) -> str:
    """Retourne la couleur hexadécimale selon le mode actif."""
    if mode == 'type':
        return _TYPE_COLORS.get(av.avatar_type, _DEFAULT_COLOR)
    if mode == 'origin':
        return _ORIGIN_COLORS.get(av.origin.value, _DEFAULT_COLOR)
    if mode == 'material':
        # Hachage stable du nom → couleur
        h   = hash(av.material_name) & 0xFFFFFF
        return '#{:06x}'.format(h | 0x404040)
    # Mode 'lmgc90' (défaut)
    if av.avatar_type == AvatarType.MESH_DEFORMABLE:
        return _MESH_COLOR
    if av.avatar_type in _WALL_TYPES:
        return _WALL_COLOR
    return _lmgc_color(av.color)


def _opacity_for_avatar(av: Avatar) -> float:
    """Opacité selon le type."""
    if av.avatar_type == AvatarType.MESH_DEFORMABLE:
        return _OPACITY_MESH
    if av.avatar_type in _WALL_TYPES:
        return _OPACITY_WALL
    if av.avatar_type == AvatarType.EMPTY_AVATAR:
        return _OPACITY_EMPTY
    return _OPACITY_RIGID


def _show_edges_for_avatar(av: Avatar, global_edges: bool) -> bool:
    """Les corps déformables affichent toujours les arêtes (structure du maillage)."""
    if av.avatar_type == AvatarType.MESH_DEFORMABLE:
        return True
    return global_edges


def _hex_to_rgb_float(hex_color: str) -> Tuple[float, float, float]:
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def _rgb_float_to_hex(r: float, g: float, b: float) -> str:
    return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))


# ============================================================================
# Modes interactifs
# ============================================================================

class _Mode:
    NAVIGATE = "navigate"
    SELECT   = "select"
    MEASURE  = "measure"


# ============================================================================
# Helpers UI
# ============================================================================

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


# ============================================================================
# Widget principal
# ============================================================================

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
        self.avatars_data    = []          # [(index, Avatar), …]
        self.actors          = {}          # index → vtkActor
        self._selected_idx   = None
        self._orig_colors    = {}          # index → couleur hex d'origine
        self._mode           = _Mode.NAVIGATE
        self._measure_pts    = []
        self._measure_actors = []
        self._dof_actors     = []          # flèches DOF
        self._color_mode     = 'lmgc90'   # lmgc90 | type | material | origin
        self._pylmgc90_mode  = False       # True = rendu via visuAvatars
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

        # Modes navigation / sélection / mesure
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

        # Vues caméra
        for label, tip, fn in [
            ("XY",  "Vue orthogonale plan XY (2D)", self._view_xy),
            ("XZ",  "Vue plan XZ",                  self._view_xz),
            #("YZ",  "Vue plan YZ",                  self._view_yz),
            ("Iso", "Vue isométrique",               self._view_iso),
        ]:
            btn = QPushButton(label)
            btn.setToolTip(tip)
            btn.setFixedWidth(36)
            btn.clicked.connect(fn)
            tb.addWidget(btn)

        tb.addWidget(_sep())

        # Arêtes
        self._edges_check = QCheckBox("Arêtes")
        self._edges_check.setChecked(True)
        self._edges_check.toggled.connect(self._toggle_edges)
        tb.addWidget(self._edges_check)

        # Conditions aux limites
        self._dof_check = QCheckBox("DOF")
        self._dof_check.setChecked(False)
        self._dof_check.setToolTip("Afficher les flèches de conditions aux limites")
        self._dof_check.toggled.connect(self._toggle_dof)
        tb.addWidget(self._dof_check)

        tb.addWidget(_sep())

        # Mode couleur
        #tb.addWidget(QLabel("Couleur :"))
        self._color_combo = QComboBox()
        self._color_combo.setToolTip("Mode de colorisation des avatars")
        self._color_combo.addItems(["LMGC90", "Par type", "Par matériau", "Par origine"])
        self._color_combo.setFixedWidth(90)
        self._color_combo.currentIndexChanged.connect(self._on_color_mode_changed)
        tb.addWidget(self._color_combo)

        tb.addWidget(_sep())

        # Opacité globale
        #tb.addWidget(QLabel("Opacité :"))
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(20, 100)
        self._opacity_slider.setValue(92)
        self._opacity_slider.setFixedWidth(50)
        self._opacity_slider.setToolTip("Opacité globale des avatars")
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        tb.addWidget(self._opacity_slider)

        tb.addWidget(_sep())

        # Bouton pylmgc90
        self._pylmgc90_btn = QPushButton("🔬")
        self._pylmgc90_btn.setCheckable(True)
        self._pylmgc90_btn.setToolTip(
            "Rendu haute fidélité via pre.visuAvatars() de pylmgc90.\n"
            "Requiert pylmgc90 installé. Désactive la sélection individuelle."
        )
        self._pylmgc90_btn.setFixedWidth(50)
        self._pylmgc90_btn.toggled.connect(self._on_pylmgc90_toggled)
        tb.addWidget(self._pylmgc90_btn)

        tb.addWidget(_sep())

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

        exp = QPushButton("📷")
        exp.setToolTip("Exporter la scène en PNG")
        exp.setFixedWidth(28)
        exp.clicked.connect(self._export_png)
        tb.addWidget(exp)

        tb.addStretch()

        # Filtre groupe
        #tb.addWidget(QLabel("Groupe :"))
        self._group_combo = QComboBox()
        self._group_combo.setToolTip("Afficher seulement les avatars de ce groupe")
        self._group_combo.setMinimumWidth(100)
        self._group_combo.addItem("Tous les groupes")
        self._group_combo.currentTextChanged.connect(self._on_group_filter)
        tb.addWidget(self._group_combo)

        root.addLayout(tb)

        # ── Plotter PyVista ───────────────────────────────────────────────────
        self.plotter = QtInteractor(self)
        self.plotter.set_background("#cadbddca")
        self.plotter.enable_anti_aliasing()
        root.addWidget(self.plotter.interactor, stretch=1)

        # ── Barre d'état ───────────────────────────────────────────────────
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
            line_width=2, color='white',
        )
        grid = pv.Plane(
            center=(0, 0, 0), direction=(0, 0, 1),
            i_size=10, j_size=10, i_resolution=10, j_resolution=10,
        )
        self.plotter.add_mesh(
            grid, color="#80a6ac", opacity=0.5,
            show_edges=True, edge_color="#4f4f80", pickable=False,
        )

    # =========================================================================
    # Modes interactifs
    # =========================================================================

    def _set_mode(self, mode: str):
        self._mode = mode
        if mode != _Mode.MEASURE:
            self._cancel_measure()

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
                self.plotter.iren.add_observer(
                    'LeftButtonPressEvent', self._on_vtk_click_select
                )
            self._status("Mode sélection — cliquez sur un avatar")

        elif mode == _Mode.MEASURE:
            try:
                iren = self.plotter.iren.interactor
                iren.RemoveObservers('LeftButtonPressEvent')
                iren.AddObserver('LeftButtonPressEvent', self._on_vtk_click_measure)
            except Exception:
                try:
                    self.plotter.enable_point_picking(
                        callback=self._on_measure_pick,
                        show_message=False, show_point=False, picker='point',
                    )
                except Exception as e:
                    self._status(f"Règle indisponible : {e}")
                    return
            self._status("Mode mesure — cliquez sur le point A")

        else:
            try:
                iren = self.plotter.iren.interactor
                iren.RemoveObservers('LeftButtonPressEvent')
            except Exception:
                pass
            self._status("Navigation")

    def _on_vtk_click_select(self, obj, event):
        try:
            picker = self.plotter.renderer.GetPickProp()
            if picker:
                self._on_pick(picker)
        except Exception:
            pass

    def _on_vtk_click_measure(self, obj, event):
        try:
            iren  = self.plotter.iren.interactor
            x, y  = iren.GetEventPosition()
            picker = self.plotter.renderer._prop_picker
            if picker is None:
                import vtk
                picker = vtk.vtkCellPicker()
                picker.SetTolerance(0.005)
            picker.Pick(x, y, 0, self.plotter.renderer)
            pos = picker.GetPickPosition()
            if picker.GetCellId() < 0:
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
                f"  matériau={av.material_name}  modèle={av.model_name}"
            )
        self.avatar_clicked.emit(index)

    # ── Mesure ────────────────────────────────────────────────────────────────

    def _on_measure_pick(self, point):
        if point is None:
            return
        self._measure_pts.append(np.array(point))
        sphere = self.plotter.add_mesh(
            pv.Sphere(center=point, radius=0.015),
            color=_MEASURE_COLOR, pickable=False,
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
            line_a = self.plotter.add_mesh(
                pv.Line(A, B), color=_MEASURE_COLOR, line_width=2, pickable=False,
            )
            self._measure_actors.append(line_a)
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
    # Rendu DOF
    # =========================================================================

    def _draw_dof_hints(self, avatars: List[Avatar]):
        """Ajoute des flèches colorées pour les avatars avec conditions aux limites."""
        self._clear_dof_actors()
        if not self._dof_check.isChecked():
            return

        state  = self.controller.state
        ops    = getattr(state, 'operations', []) or []
        bodies = avatars

        for op in ops:
            if op.operation_type not in ('imposeDrivenDof', 'imposeInitValue'):
                continue

            if op.target_type == 'avatar':
                target = op.target_value
                if isinstance(target, int):
                    target_avatars = [
                        bodies[target]
                    ] if 0 <= target < len(bodies) else []
                else:
                    target_avatars = [
                        av for av in bodies if av.avatar_id == target
                    ]
            elif op.target_type == 'group':
                group_ids = state.avatar_groups.get(op.target_value, [])
                target_avatars = [
                    av for av in bodies if av.avatar_id in group_ids
                ]
            else:
                target_avatars = []

            for av in target_avatars:
                c = _as3(av.center)

                comp = op.parameters.get('component', 1)
                # Composante → direction de la flèche
                if isinstance(comp, list):
                    dirs = [d for d in comp if d != 0]
                    comp = dirs[0] if dirs else 1

                if comp == 1:
                    direction = (1, 0, 0)
                elif comp == 2:
                    direction = (0, 1, 0)
                elif comp == 3:
                    direction = (0, 0, 1)
                else:
                    direction = (1, 0, 0)

                scale = max(0.04, (av.radius or 0.1) * 0.8)
                arrow = _arrow_mesh(c, direction, scale=scale)
                actor = self.plotter.add_mesh(
                    arrow, color=_DOF_COLOR,
                    opacity=0.9, pickable=False,
                )
                self._dof_actors.append(actor)

        self.plotter.render()

    def _clear_dof_actors(self):
        for actor in self._dof_actors:
            try:
                self.plotter.remove_actor(actor)
            except Exception:
                pass
        self._dof_actors.clear()

    def _toggle_dof(self, show: bool):
        if show:
            self._draw_dof_hints(
                [av for _, av in self.avatars_data]
            )
        else:
            self._clear_dof_actors()
        self.plotter.render()

    # =========================================================================
    # API publique
    # =========================================================================

    def add_avatar(self, avatar: Avatar, index: int):
        """Ajoute un avatar individuel à la scène."""
        mesh = build_avatar_mesh(avatar)
        if mesh is None:
            return
        mesh = _apply_avatar_rotations(mesh, avatar, self.controller)

        color   = _color_for_avatar(avatar, self._color_mode)
        opacity = _opacity_for_avatar(avatar)
        edges   = _show_edges_for_avatar(avatar, self._edges_check.isChecked())

        # Corps déformables : rendu fil-de-fer par-dessus la surface
        if avatar.avatar_type == AvatarType.MESH_DEFORMABLE:
            # Surface semi-transparente
            surf_actor = self.plotter.add_mesh(
                mesh, color=color, show_edges=True,
                edge_color='#004444', opacity=opacity,
                pickable=True, smooth_shading=False,
            )
            self.actors[index]       = surf_actor
            self._orig_colors[index] = color

            # Afficher les groupes de contacteurs si disponibles
            mp = avatar.mesh_params or {}
            for cont in mp.get('contactors', []):
                cont_color = _lmgc_color(cont.get('color', 'GREEx'))
                try:
                    # Sélectionner les faces de bord
                    edges_mesh = mesh.extract_feature_edges(
                        feature_angle=30, boundary_edges=True,
                        non_manifold_edges=False, feature_edges=False,
                    )
                    self.plotter.add_mesh(
                        edges_mesh, color=cont_color,
                        line_width=2, pickable=False, opacity=0.9,
                    )
                except Exception:
                    pass
        else:
            actor = self.plotter.add_mesh(
                mesh,
                color=color,
                show_edges=edges,
                edge_color='#000000',
                opacity=opacity,
                pickable=True,
                smooth_shading=True,
            )
            self.actors[index]       = actor
            self._orig_colors[index] = color

        self.avatars_data.append((index, avatar))
        self._update_info()

    def update_avatars(self, avatars: List[Avatar]):
        """
        Recharge tous les avatars.

        Stratégie :
        • Mode pylmgc90 ON  → appel pre.visuAvatars() + chargement VTP
        • Mode pylmgc90 OFF → rendu paramétrique avec batch pour les granulo
        """
        self.clear()
        if not avatars:
            return

        renderables = _expand_renderables(avatars)

        # ── Mode pylmgc90 : rendu via visuAvatars ────────────────────────────
        if self._pylmgc90_mode:
            self._render_with_pylmgc90([av for _, av in renderables])
            return

        # ── Mode paramétrique ────────────────────────────────────────────────
        _BATCH_TYPES = {AvatarType.RIGID_DISK, AvatarType.RIGID_SPHERE}
        batches: Dict = {}
        singles = []

        for i, av in renderables:
            if av.avatar_type in _BATCH_TYPES:
                color = _color_for_avatar(av, self._color_mode)
                key   = (av.avatar_type, color)
                batches.setdefault(key, []).append((i, av))
            else:
                singles.append((i, av))

        for i, av in singles:
            self.add_avatar(av, i)

        for (av_type, color), group in batches.items():
            if len(group) == 1:
                i, av = group[0]
                self.add_avatar(av, i)
                continue

            parts = [build_avatar_mesh(av) for _, av in group]
            parts = [m for m in parts if m is not None]
            if not parts:
                continue

            merged = parts[0]
            for p in parts[1:]:
                merged = merged.merge(p)

            opacity = _OPACITY_BATCH * (self._opacity_slider.value() / 100)
            actor = self.plotter.add_mesh(
                merged, color=color,
                show_edges=False,
                opacity=opacity,
                pickable=False,
                smooth_shading=True,
            )
            first_i = group[0][0]
            self.actors[first_i]       = actor
            self._orig_colors[first_i] = color
            for i, av in group:
                self.avatars_data.append((i, av))

        # DOF hints si activés
        if self._dof_check.isChecked():
            self._draw_dof_hints([av for _, av in renderables])

        self._refresh_group_combo()
        self._update_info()
        self._reset_camera()

    def _render_with_pylmgc90(self, avatars: List[Avatar]):
        """Rendu haute fidélité via pre.visuAvatars()."""
        self._status("🔬 Rendu pylmgc90 en cours…")
        result = _render_via_pylmgc90(avatars, self.controller)

        if result is None:
            self._status(
                "⚠️ pylmgc90 indisponible ou rendu échoué — "
                "basculement en mode paramétrique"
            )
            self._pylmgc90_mode = False
            self._pylmgc90_btn.setChecked(False)
            self.update_avatars(avatars)
            return

        # Afficher chaque bloc (un par type de corps : RBDY2, MAILx…)
        for i in range(result.n_blocks):
            block = result[i]
            name  = result.get_block_name(i) or f"block_{i}"
            if block is None:
                continue
            try:
                surf = block.extract_surface() if hasattr(block, 'extract_surface') else block
                color = {'RBDY2': _DEFAULT_COLOR, 'RBDY3': '#5a9ec8',
                         'MAILx': _MESH_COLOR}.get(name, _DEFAULT_COLOR)
                actor = self.plotter.add_mesh(
                    surf, color=color,
                    show_edges=self._edges_check.isChecked(),
                    edge_color='#000000',
                    opacity=0.9, pickable=False,
                    smooth_shading=True,
                )
                self.actors[i]       = actor
                self._orig_colors[i] = color
            except Exception as e:
                print(f"⚠️ Viewer pylmgc90 block {name} : {e}")

        # Enregistrer les données pour la barre de statut
        for i, av in enumerate(avatars):
            self.avatars_data.append((i, av))

        self._status(
            f"🔬 Rendu pylmgc90 — {result.n_blocks} bloc(s), "
            f"{len(avatars)} avatar(s)"
        )
        self._update_info()
        self._refresh_group_combo()
        self._reset_camera()

    def clear(self):
        self.plotter.clear()
        self.actors.clear()
        self.avatars_data.clear()
        self._orig_colors.clear()
        self._selected_idx   = None
        self._dof_actors.clear()
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
            mesh   = _read_mesh_file(filepath)
            actor  = self.plotter.add_mesh(
                mesh, color=_MESH_COLOR,
                show_edges=self._edges_check.isChecked(),
                edge_color='#004444', opacity=0.9, pickable=False,
            )
            self.plotter.reset_camera()
            ext    = filepath.rsplit('.', 1)[-1].upper()
            self._status(
                f"Fichier {ext} : {mesh.n_points} nœuds, "
                f"{mesh.n_cells} cellules — {filepath}"
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
    # Arêtes et opacité
    # =========================================================================

    def _toggle_edges(self, show: bool):
        for idx, actor in self.actors.items():
            try:
                av = next((a for i, a in self.avatars_data if i == idx), None)
                # Corps déformables : arêtes toujours visibles
                if av and av.avatar_type == AvatarType.MESH_DEFORMABLE:
                    continue
                actor.GetProperty().SetEdgeVisibility(int(show))
            except Exception:
                pass
        self.plotter.render()

    def _on_opacity_changed(self, value: int):
        """Applique l'opacité globale à tous les acteurs (sauf déformables)."""
        opacity = value / 100.0
        for idx, actor in self.actors.items():
            try:
                av = next((a for i, a in self.avatars_data if i == idx), None)
                if av and av.avatar_type == AvatarType.MESH_DEFORMABLE:
                    continue
                actor.GetProperty().SetOpacity(opacity)
            except Exception:
                pass
        self.plotter.render()

    # =========================================================================
    # Modes couleur et pylmgc90
    # =========================================================================

    def _on_color_mode_changed(self, idx: int):
        modes = ['lmgc90', 'type', 'material', 'origin']
        self._color_mode = modes[idx] if idx < len(modes) else 'lmgc90'
        # Mettre à jour la couleur de chaque acteur existant
        for av_idx, actor in self.actors.items():
            av = next((a for i, a in self.avatars_data if i == av_idx), None)
            if av is None:
                continue
            new_color = _color_for_avatar(av, self._color_mode)
            try:
                actor.GetProperty().SetColor(*_hex_to_rgb_float(new_color))
                self._orig_colors[av_idx] = new_color
            except Exception:
                pass
        self.plotter.render()

    def _on_pylmgc90_toggled(self, checked: bool):
        self._pylmgc90_mode = checked
        if checked:
            self._status(
                "🔬 Mode pylmgc90 activé — cliquez sur « Rafraîchir » dans l'onglet "
                "pour déclencher le rendu via pre.visuAvatars()"
            )
        else:
            self._status("Mode paramétrique — cliquez sur « Rafraîchir » pour recharger")

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
        groups  = getattr(self.controller.state, 'avatar_groups', {}) or {}
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
            f"Groupe « {text} » : {n} avatar{'s' if n != 1 else ''}"
            if text != "Tous les groupes"
            else f"{len(self.avatars_data)} avatar(s) visibles"
        )

    # =========================================================================
    # Export PNG
    # =========================================================================

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter la scène", "scene.png",
            "Images PNG (*.png);;Tous les fichiers (*)"
        )
        if path:
            try:
                self.plotter.screenshot(path)
                self._status(f"📷 Scène exportée : {path}")
            except Exception as e:
                self._status(f"❌ Erreur export : {e}")

    # =========================================================================
    # Utilitaires internes
    # =========================================================================

    def _update_info(self):
        n   = len(self.avatars_data)
        mode_label = " [pylmgc90]" if self._pylmgc90_mode else ""
        self.info_label.setText(f"{n} avatar{'s' if n != 1 else ''}{mode_label}")

    def _status(self, msg: str):
        self._status_label.setText(msg)