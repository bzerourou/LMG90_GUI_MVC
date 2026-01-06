# ============================================================================
# Générateurs (boucles, granulo)
# ============================================================================
"""
Générateurs pour avatars (boucles, granulométrie).
Logique pure sans dépendances GUI.
"""
import math
import numpy as np
from typing import List, Tuple, Dict, Any
from .models import Avatar, Loop, GranuloGeneration, AvatarType, AvatarOrigin


class LoopGenerator:
    """Génère des positions selon différents motifs"""
    
    @staticmethod
    def generate_circle(count: int, radius: float, offset_x: float = 0.0, 
                       offset_y: float = 0.0) -> List[List[float]]:
        """Génère des positions en cercle"""
        centers = []
        for i in range(count):
            angle = 2 * math.pi * i / count
            x = offset_x + radius * math.cos(angle)
            y = offset_y + radius * math.sin(angle)
            centers.append([x, y])
        return centers
    
    @staticmethod
    def generate_grid(count: int, step: float, offset_x: float = 0.0, 
                     offset_y: float = 0.0) -> List[List[float]]:
        """Génère des positions en grille"""
        side = int(math.ceil(math.sqrt(count)))
        centers = []
        for i in range(count):
            x = offset_x + (i % side) * step
            y = offset_y + (i // side) * step
            centers.append([x, y])
        return centers
    
    @staticmethod
    def generate_line(count: int, step: float, offset_x: float = 0.0, 
                     offset_y: float = 0.0, invert_axis: bool = False) -> List[List[float]]:
        """Génère des positions en ligne"""
        centers = []
        for i in range(count):
            if invert_axis:
                x = offset_x
                y = offset_y + i * step
            else:
                x = offset_x + i * step
                y = offset_y
            centers.append([x, y])
        return centers
    
    @staticmethod
    def generate_spiral(count: int, radius: float, spiral_factor: float,
                       offset_x: float = 0.0, offset_y: float = 0.0) -> List[List[float]]:
        """Génère des positions en spirale"""
        centers = []
        for i in range(count):
            angle = 2 * math.pi * i / max(1, count // 5)
            r = radius + i * spiral_factor
            x = offset_x + r * math.cos(angle)
            y = offset_y + r * math.sin(angle)
            centers.append([x, y])
        return centers
    
    @staticmethod
    def generate_positions(loop: Loop) -> List[List[float]]:
        """
        Génère les positions selon la configuration de la boucle.
        
        Args:
            loop: Configuration de la boucle
            
        Returns:
            Liste des centres [x, y]
        """
        if loop.loop_type == "Cercle":
            return LoopGenerator.generate_circle(
                loop.count, loop.radius, loop.offset_x, loop.offset_y
            )
        elif loop.loop_type == "Grille":
            return LoopGenerator.generate_grid(
                loop.count, loop.step, loop.offset_x, loop.offset_y
            )
        elif loop.loop_type == "Ligne":
            return LoopGenerator.generate_line(
                loop.count, loop.step, loop.offset_x, loop.offset_y, loop.invert_axis
            )
        elif loop.loop_type == "Spirale":
            return LoopGenerator.generate_spiral(
                loop.count, loop.radius, loop.spiral_factor, loop.offset_x, loop.offset_y
            )
        else:
            raise ValueError(f"Type de boucle inconnu: {loop.loop_type}")


class GranuloGenerator:
    """Génère des distributions granulométriques"""
    
    @staticmethod
    def generate(config: GranuloGeneration) -> Tuple[int, np.ndarray, np.ndarray]:
        """
        Génère une distribution granulométrique avec dépôt.
        
        Args:
            config: Configuration de la génération
            
        Returns:
            (nb_particles, coordinates, radii)
            - nb_particles: nombre de particules effectivement placées
            - coordinates: array de shape (nb_particles, 2) avec positions
            - radii: array de shape (nb_particles,) avec rayons
        
        Raises:
            ValueError: Si le conteneur est inconnu ou paramètres invalides
        """
        from pylmgc90 import pre
        
        # Génération des rayons
        radii = pre.granulo_Random(
            config.nb_particles, 
            config.radius_min, 
            config.radius_max,
            config.seed
        )
        
        # Dépôt selon le type de conteneur
        ctype = config.container_type
        params = config.container_params
        
        if ctype == "Box2D":
            nb_remaining, coor = pre.depositInBox2D(radii, params['lx'], params['ly'])
        elif ctype == "Disk2D":
            nb_remaining, coor = pre.depositInDisk2D(radii, params['r'])
        elif ctype == "Couette2D":
            nb_remaining, coor = pre.depositInCouette2D(radii, params['rint'], params['rext'])
        elif ctype == "Drum2D":
            nb_remaining, coor = pre.depositInDrum2D(radii, params['r'])
        else:
            raise ValueError(f"Type de conteneur inconnu: {ctype}")
        
        if coor is None:
            raise ValueError("Échec du dépôt. Réduisez le nombre de particules.")
        
        # Reshape coordinates
        nb_remaining = np.shape(coor)[0] // 2
        coor = np.reshape(coor, (nb_remaining, 2))
        
        # Tronquer les rayons au nombre effectif
        radii = radii[:nb_remaining]
        
        return nb_remaining, coor, radii
