
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal

from ...core.models import Avatar, AvatarType


class Viewer3D(QWidget):
    """Widget de visualisation 3D des avatars"""
    
    avatar_clicked = pyqtSignal(int)  # Index de l'avatar cliqué
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.avatars_data = []
        self.actors = {}
        self.controller = controller
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # Barre d'outils
        toolbar = QHBoxLayout()
        
        self.info_label = QLabel("0 avatars")
        toolbar.addWidget(self.info_label)
        
        toolbar.addStretch()
        
        reset_btn = QPushButton("🔄 Réinitialiser Vue")
        reset_btn.clicked.connect(self.reset_camera)
        toolbar.addWidget(reset_btn)
        
        clear_btn = QPushButton("🗑️ Effacer")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)
        
        layout.addLayout(toolbar)
        
        # Viewer PyVista
        self.plotter = QtInteractor(self)
        self.plotter.set_background('white')
        layout.addWidget(self.plotter.interactor)
        
        self.setLayout(layout)
        
        # Ajouter axes
        self._add_axes()
    
    def _add_axes(self):
        """Ajoute les axes de référence"""
        # Axes XYZ
        self.plotter.add_axes(
            xlabel='X', ylabel='Y', zlabel='Z',
            line_width=3, color='black'
        )
        
        # Grille au sol (plan XY)
        grid = pv.Plane(
            center=(0, 0, 0),
            direction=(0, 0, 1),
            i_size=5, j_size=5
        )
        self.plotter.add_mesh(
            grid, color='lightgray', opacity=0.3,
            show_edges=True, edge_color='gray'
        )
    
    def add_avatar(self, avatar: Avatar, index: int):
        """Ajoute un avatar à la scène"""
        mesh = self._create_mesh_from_avatar(avatar)
        
        if mesh is None:
            return
        
        # Couleur selon le nom de couleur LMGC90
        color = self._get_color(avatar.color)
        
        # Ajouter à la scène
        actor = self.plotter.add_mesh(
            mesh,
            color=color,
            show_edges=True,
            edge_color='black',
            opacity=0.9,
            pickable=True
        )
        
        self.actors[index] = actor
        self.avatars_data.append((index, avatar))
        
        self._update_info()

    def _create_mesh_from_avatar(self, avatar: Avatar) -> pv.PolyData:
        """Crée un mesh PyVista depuis un Avatar"""
        center = avatar.center
        atype = avatar.avatar_type
        
        # Avatars 2D → extrudés en 3D
        if len(center) == 2:
            center = [center[0], center[1], 0.0]
            extrusion = 0.05
        else:
            extrusion = None
        
        # DISQUE / SPHERE
        if atype in [AvatarType.RIGID_DISK, AvatarType.RIGID_SPHERE]:
            if len(avatar.center) == 2:
                mesh = pv.Cylinder(
                    center=center,
                    direction=(0, 0, 1),
                    radius=avatar.radius,
                    height=extrusion
                )
            else:
                mesh = pv.Sphere(center=center, radius=avatar.radius)
            return mesh
        
        # JONC (ellipse)
        elif atype == AvatarType.RIGID_JONC:
            if not avatar.axis or 'axe1' not in avatar.axis or 'axe2' not in avatar.axis:
                # Fallback: petit cylindre
                return pv.Cylinder(center=center, radius=0.1, height=extrusion or 0.1)
            
            theta = np.linspace(0, 2*np.pi, 50)
            
            try:
                a = float(avatar.axis['axe1'])
                b = float(avatar.axis['axe2'])
            except (ValueError, TypeError):
                # Fallback si conversion échoue
                return pv.Cylinder(center=center, radius=0.1, height=extrusion or 0.1)
            
            x = center[0] + a * np.cos(theta)
            y = center[1] + b * np.sin(theta)
            z = np.full_like(x, center[2])
            
            points = np.c_[x, y, z]
            
            poly = pv.PolyData(points)
            poly.lines = np.hstack([[len(points)] + list(range(len(points))) + [0]])
            
            mesh = poly.extrude((0, 0, extrusion), capping=True)
            return mesh
        
        # POLYGONE
        elif atype == AvatarType.RIGID_POLYGON:
            if avatar.generation_type == "regular":
                n = avatar.nb_vertices
                theta = np.linspace(0, 2*np.pi, n, endpoint=False)
                r = avatar.radius
                
                x = center[0] + r * np.cos(theta)
                y = center[1] + r * np.sin(theta)
                z = np.full(n, center[2])
            else:
                verts = np.array(avatar.vertices)
                x = center[0] + verts[:, 0]
                y = center[1] + verts[:, 1]
                z = np.full(len(verts), center[2])
            
            points = np.c_[x, y, z]
            
            faces = [len(points)] + list(range(len(points)))
            mesh = pv.PolyData(points, faces=faces)
            
            if extrusion:
                mesh = mesh.extrude((0, 0, extrusion), capping=True)
            
            return mesh
        
        # CYLINDRE 3D
        elif atype == AvatarType.RIGID_CYLINDER:
            h = avatar.wall_params.get('h', 0.2) if avatar.wall_params else 0.2
            mesh = pv.Cylinder(
                center=center,
                direction=(0, 0, 1),
                radius=avatar.radius,
                height=h
            )
            return mesh
        
        # PLAN
        elif atype == AvatarType.RIGID_PLAN:
            mesh = pv.Plane(
                center=center,
                direction=(0, 0, 1),
                i_size=2, j_size=2
            )
            return mesh
        
        # MUR
        elif atype in [AvatarType.SMOOTH_WALL, AvatarType.ROUGH_WALL, AvatarType.FINE_WALL]:
            if avatar.wall_params:
                l = avatar.wall_params.get('l', 1.0)
                h = avatar.wall_params.get('h', 0.1)
                
                mesh = pv.Box(
                    bounds=[
                        center[0] - l/2, center[0] + l/2,
                        center[1] - h/2, center[1] + h/2,
                        center[2] - extrusion/2, center[2] + extrusion/2
                    ]
                )
                return mesh
        
        # AVATAR VIDE avec contacteurs
        elif atype == AvatarType.EMPTY_AVATAR:
            if not avatar.contactors:
                # Pas de contacteurs → petit cube
                return pv.Cube(center=center, x_length=0.05, y_length=0.05, z_length=0.05)
            
            # Créer un mesh composite depuis les contacteurs
            meshes = []
            
            for contactor in avatar.contactors:
                shape = contactor.get('shape', '')
                params = contactor.get('params', {})
                
                try:
                    # PT2Dx / PT3Dx → petit point (sphère)
                    if shape in ['PT2Dx', 'PT3Dx']:
                        meshes.append(pv.Sphere(center=center, radius=0.02))
                    
                    # DISKx
                    elif shape == 'DISKx':
                        r = float(params.get('byrd', 0.1))
                        meshes.append(pv.Cylinder(
                            center=center,
                            direction=(0, 0, 1),
                            radius=r,
                            height=extrusion or 0.05
                        ))
                    
                    # xKSID (disque hollow)
                    elif shape == 'xKSID':
                        r = float(params.get('byrd', 0.1))
                        # Anneau (torus plat)
                        meshes.append(pv.Cylinder(
                            center=center,
                            direction=(0, 0, 1),
                            radius=r,
                            height=extrusion or 0.05
                        ))
                    
                    # JONCx
                    elif shape == 'JONCx':
                        a = float(params.get('axe1', 0.2))
                        b = float(params.get('axe2', 0.1))
                        
                        theta = np.linspace(0, 2*np.pi, 100)
                        x = center[0] + a * np.cos(theta)
                        y = center[1] + b * np.sin(theta)
                        z = np.full_like(x, center[2])
                        
                        points = np.c_[x, y, z]
                        poly = pv.PolyData(points)
                        poly.lines = np.hstack([[len(points)] + list(range(len(points))) + [0]])
                        meshes.append(poly.extrude((0, 0, extrusion or 0.05), capping=True))
                    
                    # POLYG
                    elif shape == 'POLYG':
                        vertices = params.get('vertices', [])
                        if vertices:
                            verts = np.array(vertices)
                            x = center[0] + verts[:, 0]
                            y = center[1] + verts[:, 1]
                            z = np.full(len(verts), center[2])
                            
                            points = np.c_[x, y, z]
                            faces = [len(points)] + list(range(len(points)))
                            mesh = pv.PolyData(points, faces=faces)
                            meshes.append(mesh.extrude((0, 0, extrusion or 0.05), capping=True))
                    
                    # SPHER (3D)
                    elif shape == 'SPHER':
                        r = float(params.get('byrd', 0.1))
                        meshes.append(pv.Sphere(center=center, radius=r))
                    
                    # PLANx (3D)
                    elif shape == 'PLANx':
                        meshes.append(pv.Plane(center=center, i_size=1, j_size=1))
                    
                    # CYLND (3D)
                    elif shape == 'CYLND':
                        r = float(params.get('byrd', 0.1))
                        h = float(params.get('height', 0.2))
                        meshes.append(pv.Cylinder(center=center, radius=r, height=h))
                
                except Exception as e:
                    print(f"⚠️ Erreur création contacteur {shape}: {e}")
                    continue
            
            # Combiner tous les meshes
            if meshes:
                combined = meshes[0]
                for mesh in meshes[1:]:
                    combined = combined + mesh
                return combined
            else:
                # Fallback
                return pv.Cube(center=center, x_length=0.05, y_length=0.05, z_length=0.05)
        
        # Par défaut : petit cube
        return pv.Cube(center=center, x_length=0.1, y_length=0.1, z_length=0.1)

    def _get_color(self, color_name: str) -> str:
        """Convertit nom de couleur LMGC90 en couleur PyVista"""
        color_map = {
            'BLUEx': 'blue',
            'REDxx': 'red',
            'VERTx': 'green',
            'JAUNx': 'yellow',
            'GRAYx': 'gray',
            'BLACx': 'black',
            'WHITx': 'white',
            'ORANx': 'orange',
            'CYANx': 'cyan',
            'MAGEx': 'magenta'
        }
        return color_map.get(color_name, 'lightblue')
    
    def clear(self):
        """Efface tous les avatars"""
        self.plotter.clear()
        self.actors.clear()
        self.avatars_data.clear()
        self._add_axes()
        self._update_info()
    
    def reset_camera(self, dimension ):
        """Réinitialise la caméra"""
        if dimension == 2:
            # Vue orthogonale 2D : plan XY de face, sans perspective
            self.plotter.view_xy()                           
            self.plotter.camera.parallel_projection = True   
            self.plotter.camera.zoom(1.2)                    
            self.plotter.reset_camera()
        else : 
            self.plotter.reset_camera()
            self.plotter.view_isometric()
    
    def update_avatars(self, avatars):
        """Met à jour tous les avatars"""
        self.clear()
        
        for i, avatar in enumerate(avatars):
            self.add_avatar(avatar, i)
        if not  avatars:
            return
        dimension  = self.controller.state.dimension
        self.reset_camera(dimension)
    
    def _update_info(self):
        """Met à jour le label d'info"""
        self.info_label.setText(f"{len(self.avatars_data)} avatar(s)")