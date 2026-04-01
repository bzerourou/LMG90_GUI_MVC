# ============================================================================
# particle_factory.py  —  Moteur de génération progressive de particules
# ============================================================================
"""
Système de Factory pour LMGC90_GUI, 

Concept
───────
Pré-créer toutes vos particules dans le DATBOX en les rendant
initialement invisibles (chipy.RBDY2/3_SetInvisible), puis les activer par
vagues à des pas de temps planifiés (chipy.RBDY2/3_SetVisible).

Types de Factory disponibles
──────────────────────────────
  RAIN          Pluie de particules tombant d'une zone horizontale → dépôt de poudre
  JET           Injection directionnelle avec vitesse initiale → spray, injection forcée
  SILO_FILL     Remplissage d'un silo par le dessus → stockage, tassement
  SURFACE       Dépôt progressif en couches sur une surface → enrobage, sédimentation
  PERIODIC      Injections périodiques à intervalle fixe → ligne de production

Chaque Factory produit :
  1. Un bloc de code pre.py   → création des avatars (à insérer avant writeDatbox)
  2. Un bloc de code chipy.py → activation progressive (à insérer dans la boucle chipy)

API pylmgc90 utilisée (vérifiée)
──────────────────────────────────
  pre.rigidSphere, pre.rigidDisk, pre.rigidJonc, pre.roughWall
  pre.rigidPlan, pre.granulo_Random, pre.depositInBox2D/3D
  chipy.RBDY2_SetInvisible / SetVisible  (dimension 2)
  chipy.RBDY3_SetInvisible / SetVisible  (dimension 3)
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class FactoryType(Enum):
    PERIODIC = "periodic"  # Injection périodique


class ZoneShape(Enum):
    BOX        = "box"        # Parallélépipède (3D) / Rectangle (2D)
    CYLINDER   = "cylinder"   # Cylindre (3D) / Disque (2D)
    RECTANGLE  = "rectangle"  # Rectangle 2D
    DISK       = "disk"       # Disque 2D


class ContainerShape(Enum):
    NONE        = "none"
    BOX_OPEN    = "box_open"      # Boîte ouverte (sans couvercle)
    BOX_CLOSED  = "box_closed"    # Boîte fermée
    SILO_BOX    = "silo_box"      # Silo rectangulaire (col étroit + corps)
    SILO_CYL    = "silo_cyl"      # Silo cylindrique
    HOPPER      = "hopper"        # Trémie (entonnoir)
    COUETTE     = "couette"       # Anneau Couette 2D


class SizeDistribution(Enum):
    UNIFORM     = "uniform"       # Rayon fixe
    RANDOM      = "random"        # Uniforme aléatoire [rmin, rmax]
    GRANULO     = "granulo"       # pre.granulo_Random (log-uniforme LMGC90)


# ============================================================================
# Modèles de données (sérialisables JSON)
# ============================================================================

@dataclass
class FactoryBatch:
    """
    Une vague d'activation dans le planning.
    body_start et body_end sont les indices (1-based) des corps LMGC90
    correspondant à cette vague.
    """
    step:        int             # Pas de simulation où activer
    body_start:  int  = 0        # Indice début (1-based, dans bodies)
    body_end:    int  = 0        # Indice fin   (1-based, inclus)
    nb_active:   int  = 0        # Nombre de corps activés dans cette vague

    def to_dict(self) -> dict:
        return {'step': self.step, 'body_start': self.body_start,
                'body_end': self.body_end, 'nb_active': self.nb_active}

    @classmethod
    def from_dict(cls, d: dict) -> 'FactoryBatch':
        return cls(**d)


@dataclass
class FactoryConfig:
    """
    Configuration complète d'une Factory.
    Entièrement sérialisable (intégration ProjectState).
    """

    # ── Identité ──────────────────────────────────────────────────────────────
    name:           str
    factory_type:   str         = FactoryType.PERIODIC.value
    dimension:      int         = 2
    enabled:        bool        = True

    # ── Particules ────────────────────────────────────────────────────────────
    particle_type:   str        = 'rigidDisk'   # rigidSphere | rigidDisk
    distribution:    str        = SizeDistribution.RANDOM.value
    radius_min:      float      = 0.01
    radius_max:      float      = 0.02
    nb_particles:    int        = 1000
    model_name:      str        = ''
    material_name:   str        = ''
    color:           str        = 'BLUEx'
    seed:            Optional[int] = None

    # ── Zone d'injection ─────────────────────────────────────────────────────
    zone_shape:      str        = ZoneShape.BOX.value
    zone_center:     List[float] = field(default_factory=lambda: [0., 0., 2.])
    zone_lx:         float      = 1.0    # Largeur X  (box) ou rayon (cylindre)
    zone_ly:         float      = 1.0    # Largeur Y
    zone_lz:         float      = 0.5    # Hauteur Z (épaisseur de la zone)

    # ── Vitesse initiale ──────────────────────────────────────────────────────
    velocity:        List[float] = field(default_factory=lambda: [0., 0., 0.])
    velocity_random: float      = 0.0    # Amplitude du bruit aléatoire sur v

    # ── Planning d'activation ─────────────────────────────────────────────────
    batch_size:      int        = 10     # Particules par vague
    start_step:      int        = 1      # Pas de la première vague
    interval_steps:  int        = 50     # Pas entre deux vagues
    # nb_batches calculé depuis nb_particles et batch_size

    # ── Conteneur (parois) ────────────────────────────────────────────────────
    container_shape:  str       = ContainerShape.NONE.value
    container_lx:     float     = 2.0
    container_ly:     float     = 2.0
    container_lz:     float     = 3.0
    container_wall_r: float     = 0.01   # Rayon/épaisseur des parois
    container_center: List[float] = field(default_factory=lambda: [0., 0., 0.])

    # ── Résultats (renseignés après génération) ────────────────────────────────
    body_index_start: int       = 0      # Premier indice dans bodies (1-based)
    body_index_end:   int       = 0      # Dernier indice dans bodies (1-based)
    batches:          List[dict] = field(default_factory=list)   # FactoryBatch sérialisés
    wall_index_start: int       = 0      # Premier indice des parois dans bodies
    wall_index_end:   int       = 0

    @property
    def nb_batches(self) -> int:
        return math.ceil(self.nb_particles / max(1, self.batch_size))

    @property
    def last_activation_step(self) -> int:
        return self.start_step + (self.nb_batches - 1) * self.interval_steps

    @property
    def is_3d(self) -> bool:
        return self.dimension == 3

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'FactoryConfig':
        data = dict(d)
        # Compatibilité: batches est une liste de dicts
        if 'batches' in data and data['batches']:
            pass  # déjà des dicts
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})


# ============================================================================
# Générateur de positions
# ============================================================================

class PositionGenerator:
    """
    Génère des positions de particules dans une zone d'injection.
    Utilise un empilement léger sans chevauchement (réseau + perturbation).
    """

    @staticmethod
    def generate(config: FactoryConfig, nb: int,
                 rng: Optional[np.random.Generator] = None) -> np.ndarray:
        """
        Retourne un tableau (nb, 2 ou 3) de positions dans la zone d'injection.
        Les positions sont espacées pour éviter les chevauchements à l'init.
        """
        if rng is None:
            rng = np.random.default_rng(config.seed)

        dim    = config.dimension
        center = np.array(config.zone_center[:dim])
        r_max  = config.radius_max
        # Espacement minimal = 2.2 * r_max pour éviter les chevauchements
        spacing = 2.2 * r_max

        if dim == 3:
            return PositionGenerator._grid_3d(center, config.zone_lx,
                                              config.zone_ly, config.zone_lz,
                                              spacing, nb, rng)
        else:
            return PositionGenerator._grid_2d(center, config.zone_lx,
                                              config.zone_ly,
                                              spacing, nb, rng)

    @staticmethod
    def _grid_3d(center, lx, ly, lz, spacing, nb, rng) -> np.ndarray:
        """Réseau cubique avec perturbation aléatoire dans la zone."""
        nx = max(1, int(lx / spacing))
        ny = max(1, int(ly / spacing))
        nz = max(1, int(lz / spacing))
        positions = []

        x0 = center[0] - lx / 2 + spacing / 2
        y0 = center[1] - ly / 2 + spacing / 2
        z0 = center[2] - lz / 2 + spacing / 2

        for ix in range(nx):
            for iy in range(ny):
                for iz in range(nz):
                    if len(positions) >= nb:
                        break
                    # Perturbation 20 % de l'espacement
                    noise = rng.uniform(-0.2, 0.2, 3) * spacing
                    x = x0 + ix * spacing + noise[0]
                    y = y0 + iy * spacing + noise[1]
                    z = z0 + iz * spacing + noise[2]
                    # Rester dans la zone
                    x = np.clip(x, center[0] - lx/2, center[0] + lx/2)
                    y = np.clip(y, center[1] - ly/2, center[1] + ly/2)
                    z = np.clip(z, center[2] - lz/2, center[2] + lz/2)
                    positions.append([x, y, z])

        # Compléter avec aléatoire si pas assez de points dans la grille
        while len(positions) < nb:
            x = rng.uniform(center[0] - lx/2, center[0] + lx/2)
            y = rng.uniform(center[1] - ly/2, center[1] + ly/2)
            z = rng.uniform(center[2] - lz/2, center[2] + lz/2)
            positions.append([x, y, z])

        return np.array(positions[:nb])

    @staticmethod
    def _grid_2d(center, lx, ly, spacing, nb, rng) -> np.ndarray:
        """Réseau carré avec perturbation aléatoire."""
        nx = max(1, int(lx / spacing))
        ny = max(1, int(ly / spacing))
        positions = []

        x0 = center[0] - lx / 2 + spacing / 2
        y0 = center[1] - ly / 2 + spacing / 2

        for ix in range(nx):
            for iy in range(ny):
                if len(positions) >= nb:
                    break
                noise = rng.uniform(-0.2, 0.2, 2) * spacing
                x = np.clip(x0 + ix * spacing + noise[0],
                             center[0] - lx/2, center[0] + lx/2)
                y = np.clip(y0 + iy * spacing + noise[1],
                             center[1] - ly/2, center[1] + ly/2)
                positions.append([x, y])

        while len(positions) < nb:
            x = rng.uniform(center[0] - lx/2, center[0] + lx/2)
            y = rng.uniform(center[1] - ly/2, center[1] + ly/2)
            positions.append([x, y])

        return np.array(positions[:nb])


# ============================================================================
# Générateur de rayons
# ============================================================================

class RadiusGenerator:
    """Génère les rayons des particules selon la distribution choisie."""

    @staticmethod
    def generate(config: FactoryConfig, nb: int,
                 rng: Optional[np.random.Generator] = None) -> np.ndarray:
        if rng is None:
            rng = np.random.default_rng(config.seed)

        dist = config.distribution
        rmin = config.radius_min
        rmax = config.radius_max

        if dist == SizeDistribution.UNIFORM.value or rmin == rmax:
            return np.full(nb, (rmin + rmax) / 2)

        if dist in (SizeDistribution.RANDOM.value, SizeDistribution.GRANULO.value):
            # Distribution uniforme sur [rmin, rmax]
            # pre.granulo_Random utilise une loi proche — on simule ici
            return rng.uniform(rmin, rmax, nb)

        return rng.uniform(rmin, rmax, nb)


# ============================================================================
# Générateur de code pre.py
# ============================================================================

class PreCodeGenerator:
    """
    Génère le bloc de code pré-traitement (pre.py) pour une Factory.
    Ce code est à insérer dans le script avant pre.writeDatbox().
    """

    def __init__(self, config: FactoryConfig):
        self.cfg = config
        self.lines: List[str] = []

    def generate(self) -> str:
        """Retourne le code complet du bloc pre."""
        c = self.cfg
        self.lines.clear()

        self._comment_header()
        self._write_container_walls()
        self._write_particle_positions()
        self._write_particle_creation()
        self._write_footer()

        return '\n'.join(self.lines)

    # ── En-tête ───────────────────────────────────────────────────────────────

    def _comment_header(self):
        c = self.cfg
        self._w(f"# {'=' * 70}")
        self._w(f"# FACTORY : {c.name}  ({c.factory_type.upper()})")
        self._w(f"# {c.nb_particles} particules de type {c.particle_type}")
        self._w(f"# {c.nb_batches} vague(s) de {c.batch_size}, toutes les "
                f"{c.interval_steps} pas à partir du pas {c.start_step}")
        self._w(f"# {'=' * 70}")
        self._w(f"# Indices bodies réservés : {c.body_index_start}..{c.body_index_end}")
        self._w("")

    # ── Parois du conteneur ───────────────────────────────────────────────────

    def _write_container_walls(self):
        c = self.cfg
        shape = c.container_shape

        if shape == ContainerShape.NONE.value:
            return

        self._w(f"# ── Parois du conteneur ({shape}) ──────────────────────────")

        if c.dimension == 2:
            self._write_container_2d(shape)
        else:
            self._write_container_3d(shape)

        self._w("")

    def _write_container_2d(self, shape: str):
        """Parois 2D avec pre.roughWall / pre.rigidJonc."""
        c   = self.cfg
        cx  = c.container_center[0]
        cy  = c.container_center[1] if len(c.container_center) > 1 else 0.
        lx  = c.container_lx
        ly  = c.container_ly
        r   = c.container_wall_r
        mat = f"mat_{c.material_name}"
        mod = f"mod_{c.model_name}"

        # Sol
        self._w(f"# Sol")
        self._w(f"wall_factory_{c.name}_floor = pre.roughWall(")
        self._w(f"    l={lx}, r={r},")
        self._w(f"    center=[{cx}, {cy}],")
        self._w(f"    model={mod}, material={mat}, color='GRAYx')")
        self._w(f"bodies.addAvatar(wall_factory_{c.name}_floor)")
        self._w(f"wall_factory_{c.name}_floor.imposeDrivenDof(")
        self._w(f"    component=[1,2,3], dofty='vlocy')")
        self._w("")

        # Paroi gauche
        self._w(f"# Paroi gauche")
        self._w(f"wall_factory_{c.name}_left = pre.roughWall(")
        self._w(f"    l={ly}, r={r},")
        self._w(f"    center=[{cx - lx/2}, {cy + ly/2}],")
        self._w(f"    model={mod}, material={mat}, color='GRAYx')")
        self._w(f"wall_factory_{c.name}_left.rotate(")
        self._w(f"    description='axis', alpha=1.5707963, axis=[0.,0.,1.],")
        self._w(f"    center=[{cx - lx/2}, {cy + ly/2}])")
        self._w(f"bodies.addAvatar(wall_factory_{c.name}_left)")
        self._w(f"wall_factory_{c.name}_left.imposeDrivenDof(")
        self._w(f"    component=[1,2,3], dofty='vlocy')")
        self._w("")

        # Paroi droite
        self._w(f"# Paroi droite")
        self._w(f"wall_factory_{c.name}_right = pre.roughWall(")
        self._w(f"    l={ly}, r={r},")
        self._w(f"    center=[{cx + lx/2}, {cy + ly/2}],")
        self._w(f"    model={mod}, material={mat}, color='GRAYx')")
        self._w(f"wall_factory_{c.name}_right.rotate(")
        self._w(f"    description='axis', alpha=1.5707963, axis=[0.,0.,1.],")
        self._w(f"    center=[{cx + lx/2}, {cy + ly/2}])")
        self._w(f"bodies.addAvatar(wall_factory_{c.name}_right)")
        self._w(f"wall_factory_{c.name}_right.imposeDrivenDof(")
        self._w(f"    component=[1,2,3], dofty='vlocy')")
        self._w("")

    def _write_container_3d(self, shape: str):
        """Parois 3D avec pre.rigidPlan (axe1/axe2 = demi-côtés du plan)."""
        c   = self.cfg
        cx, cy, cz = (c.container_center + [0., 0., 0.])[:3]
        lx  = c.container_lx
        ly  = c.container_ly
        lz  = c.container_lz
        e   = c.container_wall_r    # épaisseur des parois
        mat = f"mat_{c.material_name}"
        mod = f"mod_{c.model_name}"

        walls_3d = {
            'floor': {
                'center': f"[{cx}, {cy}, {cz}]",
                'axe1': lx/2, 'axe2': ly/2, 'axe3': e,
                'comment': 'Sol (Z-)'
            },
            'left': {
                'center': f"[{cx - lx/2}, {cy}, {cz + lz/2}]",
                'axe1': e, 'axe2': ly/2, 'axe3': lz/2,
                'comment': 'Paroi gauche (X-)'
            },
            'right': {
                'center': f"[{cx + lx/2}, {cy}, {cz + lz/2}]",
                'axe1': e, 'axe2': ly/2, 'axe3': lz/2,
                'comment': 'Paroi droite (X+)'
            },
            'front': {
                'center': f"[{cx}, {cy - ly/2}, {cz + lz/2}]",
                'axe1': lx/2, 'axe2': e, 'axe3': lz/2,
                'comment': 'Paroi avant (Y-)'
            },
            'back': {
                'center': f"[{cx}, {cy + ly/2}, {cz + lz/2}]",
                'axe1': lx/2, 'axe2': e, 'axe3': lz/2,
                'comment': 'Paroi arrière (Y+)'
            },
        }

        if shape == ContainerShape.BOX_CLOSED.value:
            walls_3d['lid'] = {
                'center': f"[{cx}, {cy}, {cz + lz}]",
                'axe1': lx/2, 'axe2': ly/2, 'axe3': e,
                'comment': 'Couvercle (Z+)'
            }

        for wname, wp in walls_3d.items():
            self._w(f"# {wp['comment']}")
            self._w(f"wall_factory_{c.name}_{wname} = pre.rigidPlan(")
            self._w(f"    center={wp['center']},")
            self._w(f"    axe1={wp['axe1']}, axe2={wp['axe2']}, axe3={wp['axe3']},")
            self._w(f"    model={mod}, material={mat}, color='GRAYx')")
            self._w(f"bodies.addAvatar(wall_factory_{c.name}_{wname})")
            self._w(f"wall_factory_{c.name}_{wname}.imposeDrivenDof(")
            self._w(f"    component=[1,2,3,4,5,6], dofty='vlocy')")
            self._w("")

    # ── Positions ─────────────────────────────────────────────────────────────

    def _write_particle_positions(self):
        c = self.cfg
        self._w(f"# ── Positions de la zone d'injection : {c.name} ─────────────")
        self._w(f"_factory_{c.name}_radii = np.linspace(")
        self._w(f"    {c.radius_min}, {c.radius_max}, {c.nb_particles})")
        self._w("")
        # Grille de positions
        self._w(f"_factory_{c.name}_rng = np.random.default_rng({c.seed!r})")
        self._w(f"_factory_{c.name}_spacing = 2.2 * {c.radius_max}")
        self._w(f"_factory_{c.name}_center = {c.zone_center[:c.dimension]}")
        self._w(f"_factory_{c.name}_positions = []")
        self._w("")

        if c.dimension == 3:
            self._w(f"# Réseau 3D avec perturbation")
            self._w(f"_nx = max(1, int({c.zone_lx} / _factory_{c.name}_spacing))")
            self._w(f"_ny = max(1, int({c.zone_ly} / _factory_{c.name}_spacing))")
            self._w(f"_nz = max(1, int({c.zone_lz} / _factory_{c.name}_spacing))")
            self._w(f"_x0 = {c.zone_center[0]} - {c.zone_lx}/2 + _factory_{c.name}_spacing/2")
            self._w(f"_y0 = {c.zone_center[1]} - {c.zone_ly}/2 + _factory_{c.name}_spacing/2")
            self._w(f"_z0 = {c.zone_center[2]} - {c.zone_lz}/2 + _factory_{c.name}_spacing/2")
            self._w(f"for _ix in range(_nx):")
            self._w(f"    for _iy in range(_ny):")
            self._w(f"        for _iz in range(_nz):")
            self._w(f"            if len(_factory_{c.name}_positions) >= {c.nb_particles}: break")
            self._w(f"            _noise = _factory_{c.name}_rng.uniform(-0.2, 0.2, 3) * _factory_{c.name}_spacing")
            self._w(f"            _factory_{c.name}_positions.append([")
            self._w(f"                _x0 + _ix * _factory_{c.name}_spacing + _noise[0],")
            self._w(f"                _y0 + _iy * _factory_{c.name}_spacing + _noise[1],")
            self._w(f"                _z0 + _iz * _factory_{c.name}_spacing + _noise[2]])")
        else:
            self._w(f"# Réseau 2D avec perturbation")
            self._w(f"_nx = max(1, int({c.zone_lx} / _factory_{c.name}_spacing))")
            self._w(f"_ny = max(1, int({c.zone_ly} / _factory_{c.name}_spacing))")
            self._w(f"_x0 = {c.zone_center[0]} - {c.zone_lx}/2 + _factory_{c.name}_spacing/2")
            self._w(f"_y0 = {c.zone_center[1]} - {c.zone_ly}/2 + _factory_{c.name}_spacing/2")
            self._w(f"for _ix in range(_nx):")
            self._w(f"    for _iy in range(_ny):")
            self._w(f"        if len(_factory_{c.name}_positions) >= {c.nb_particles}: break")
            self._w(f"        _noise = _factory_{c.name}_rng.uniform(-0.2, 0.2, 2) * _factory_{c.name}_spacing")
            self._w(f"        _factory_{c.name}_positions.append([")
            self._w(f"            _x0 + _ix * _factory_{c.name}_spacing + _noise[0],")
            self._w(f"            _y0 + _iy * _factory_{c.name}_spacing + _noise[1]])")

        self._w(f"# Compléter avec aléatoire si grille insuffisante")
        self._w(f"while len(_factory_{c.name}_positions) < {c.nb_particles}:")
        if c.dimension == 3:
            self._w(f"    _factory_{c.name}_positions.append([")
            self._w(f"        _factory_{c.name}_rng.uniform({c.zone_center[0]}-{c.zone_lx/2}, {c.zone_center[0]+c.zone_lx/2}),")
            self._w(f"        _factory_{c.name}_rng.uniform({c.zone_center[1]}-{c.zone_ly/2}, {c.zone_center[1]+c.zone_ly/2}),")
            self._w(f"        _factory_{c.name}_rng.uniform({c.zone_center[2]}-{c.zone_lz/2}, {c.zone_center[2]+c.zone_lz/2})])")
        else:
            self._w(f"    _factory_{c.name}_positions.append([")
            self._w(f"        _factory_{c.name}_rng.uniform({c.zone_center[0]}-{c.zone_lx/2}, {c.zone_center[0]+c.zone_lx/2}),")
            self._w(f"        _factory_{c.name}_rng.uniform({c.zone_center[1]}-{c.zone_ly/2}, {c.zone_center[1]+c.zone_ly/2})])")
        self._w("")

    # ── Création des avatars ──────────────────────────────────────────────────

    def _write_particle_creation(self):
        c   = self.cfg
        mat = f"mat_{c.material_name}"
        mod = f"mod_{c.model_name}"

        self._w(f"# ── Création des avatars — Factory {c.name} ──────────────────")
        self._w(f"factory_{c.name}_bodies = []   # Liste pour indexation chipy")
        self._w(f"for _j, _pos in enumerate(_factory_{c.name}_positions[:{c.nb_particles}]):")

        if c.particle_type == 'rigidSphere':
            self._w(f"    _av = pre.rigidSphere(")
        else:
            self._w(f"    _av = pre.rigidDisk(")

        self._w(f"        r=float(_factory_{c.name}_radii[_j]),")
        self._w(f"        center=list(_pos),")
        self._w(f"        model={mod},")
        self._w(f"        material={mat},")
        self._w(f"        color='{c.color}')")

        # Vitesse initiale si non nulle
        if any(v != 0. for v in c.velocity):
            vx, vy = c.velocity[0], c.velocity[1]
            vz = c.velocity[2] if c.dimension == 3 else 0.
            if c.dimension == 3:
                comps = [1, 2, 3] if vx != 0. or vy != 0. or vz != 0. else []
                if vx != 0.:
                    self._w(f"    _av.imposeInitValue(component=1, value={vx})")
                if vy != 0.:
                    self._w(f"    _av.imposeInitValue(component=2, value={vy})")
                if vz != 0.:
                    self._w(f"    _av.imposeInitValue(component=3, value={vz})")
            else:
                if vx != 0.:
                    self._w(f"    _av.imposeInitValue(component=1, value={vx})")
                if vy != 0.:
                    self._w(f"    _av.imposeInitValue(component=2, value={vy})")

        self._w(f"    bodies.addAvatar(_av)")
        self._w(f"    factory_{c.name}_bodies.append(_av)")
        self._w("")

    # ── Footer ────────────────────────────────────────────────────────────────

    def _write_footer(self):
        c = self.cfg
        self._w(f"# Planning de la factory {c.name} :")
        self._w(f"# Vague 0 → pas {c.start_step}  |  "
                f"Dernière vague → pas {c.last_activation_step}")
        self._w(f"# Toutes les particules activées au pas {c.last_activation_step}")
        self._w("")

    # ── Utilitaire ────────────────────────────────────────────────────────────

    def _w(self, line: str):
        self.lines.append(line)


# ============================================================================
# Générateur de code chipy.py
# ============================================================================

class ChipyCodeGenerator:
    """
    Génère le bloc de code boucle de simulation (chipy.py) pour l'ensemble
    des factories d'un projet.

    Ce code s'insère dans la boucle for step in range(nb_steps).
    """

    def __init__(self, factories: List[FactoryConfig],
                 nb_steps: int = 1000,
                 freq_write: int = 100,
                 dimension: int = 3):
        self.factories   = factories
        self.nb_steps    = nb_steps
        self.freq_write  = freq_write
        self.dimension   = dimension

    def generate(self) -> str:
        lines: List[str] = []
        w = lines.append
        dim = self.dimension

        # En-tête
        w("# ============================================================")
        w("# Code généré par LMGC90_GUI — Particle Factory")
        w("# À copier/coller dans votre script chipy.py")
        w("# ============================================================")
        w("from pylmgc90 import chipy")
        w("import numpy as np")
        w("")
        w("chipy.Initialize()")
        w("chipy.checkDirectories()")
        w("chipy.loadBehaviours()")
        w("chipy.loadModels()")
        w("chipy.loadBodies()")
        w("chipy.loadTactors()")
        w("")

        # Index des corps par factory (on connaît les indices après writeDatbox)
        w("# ── Indices des corps par factory ──────────────────────────────")
        for fc in self.factories:
            if fc.body_index_start > 0 and fc.body_index_end > 0:
                w(f"# Factory '{fc.name}' : corps {fc.body_index_start}..{fc.body_index_end}")
                w(f"_factory_{fc.name}_range = list(range(")
                w(f"    {fc.body_index_start}, {fc.body_index_end + 1}))")
            else:
                w(f"# Factory '{fc.name}' : indices à renseigner après writeDatbox")
                w(f"# (cf. _factory_{fc.name}_bodies dans le script pre.py)")
                w(f"_factory_{fc.name}_range = []  # À compléter")
        w("")

        # Rendre toutes les particules invisibles au départ
        rbdy = f"RBDY{dim}"
        w("# ── Rendre toutes les particules de factory invisibles ─────────")
        for fc in self.factories:
            w(f"for _bnum in _factory_{fc.name}_range:")
            w(f"    chipy.{rbdy}_SetInvisible(_bnum)")
        w("")

        # Planning sous forme de dict {step → [(factory_name, batch_indices)]}
        w("# ── Construire le planning d'activation ───────────────────────")
        w("_activation_schedule = {}  # {step: [(factory_name, [body_nums])]}")
        for fc in self.factories:
            w(f"# Factory {fc.name} : {fc.nb_batches} vague(s)")
            w(f"for _batch_i in range({fc.nb_batches}):")
            w(f"    _step = {fc.start_step} + _batch_i * {fc.interval_steps}")
            w(f"    _bstart = _batch_i * {fc.batch_size}")
            w(f"    _bend   = min(_bstart + {fc.batch_size}, len(_factory_{fc.name}_range))")
            w(f"    _nums   = _factory_{fc.name}_range[_bstart:_bend]")
            w(f"    _activation_schedule.setdefault(_step, []).append(('{fc.name}', _nums))")
        w("")

        # Réglages simulation
        w("# ── Réglages simulation ────────────────────────────────────────")
        w(f"nb_steps    = {self.nb_steps}")
        w(f"freq_write  = {self.freq_write}")
        w("chipy.TimeEvolution_SetNbSteps(nb_steps)")
        w("chipy.TimeEvolution_SetDisplayPeriod(freq_write)")
        w("")

        # Boucle principale
        w("# ── Boucle de simulation ───────────────────────────────────────")
        w("for step in range(1, nb_steps + 1):")
        w("")
        w("    # Activation des particules planifiées")
        w("    if step in _activation_schedule:")
        w("        for _factory_name, _body_nums in _activation_schedule[step]:")
        w(f"            for _bnum in _body_nums:")
        w(f"                chipy.{rbdy}_SetVisible(_bnum)")
        w(f"            print(f'Step {{step}}: Factory {{_factory_name}} — "
          f"{{len(_body_nums)}} particule(s) activée(s)')")
        w("")
        w("    # ── Boucle DEM standard ────────────────────────────────────")
        w("    chipy.IncrementStep()")
        w("    chipy.ComputeFext()")
        w("    chipy.ComputeBulk()")
        w("    chipy.ComputeFreeVelocity()")
        w("    chipy.SelectProxTactors()")
        w("    chipy.RecupRloc()")
        w("    chipy.ExSolver('NLGS', 'Stored_Delassus_Loops  ', 1.0e-4, 10, 100)")
        w("    chipy.StockRloc()")
        w("    chipy.ComputeDof()")
        w("    chipy.ComputeField()")
        w("    chipy.UpdateStep()")
        w("    chipy.WriteOut(freq_write)")
        w("    chipy.WriteDisplayFiles(freq_write)")
        w("")
        w("chipy.Finalize()")

        return '\n'.join(lines)


# ============================================================================
# Moteur principal
# ============================================================================

class ParticleFactory:
    """
    Moteur central du système de Factory.

    Rôle :
        - Valider les FactoryConfig
        - Calculer les indices de corps dans le conteneur bodies
        - Générer le code pre.py et chipy.py
        - Exposer une API simple pour le contrôleur GUI

    Usage type :
        factory = ParticleFactory()
        factory.add(FactoryConfig(...))
        pre_code   = factory.generate_pre_code()
        chipy_code = factory.generate_chipy_code(nb_steps=5000)
    """

    def __init__(self):
        self.configs: List[FactoryConfig] = []
        self._current_body_index = 1   # Prochain indice bodies disponible

    def reset_body_counter(self, start: int = 1):
        """Réinitialise le compteur de corps (à appeler avant la génération)."""
        self._current_body_index = start

    def add(self, config: FactoryConfig) -> FactoryConfig:
        """Ajoute une factory et calcule ses indices de corps."""
        self._assign_body_indices(config)
        self.configs.append(config)
        return config

    def remove(self, name: str) -> bool:
        before = len(self.configs)
        self.configs = [c for c in self.configs if c.name != name]
        return len(self.configs) < before

    def get(self, name: str) -> Optional[FactoryConfig]:
        return next((c for c in self.configs if c.name == name), None)

    def validate(self, config: FactoryConfig) -> Tuple[bool, List[str]]:
        """Valide une configuration. Retourne (ok, liste d'erreurs)."""
        errors: List[str] = []

        if not config.name or not config.name.isidentifier():
            errors.append("Le nom doit être un identifiant Python valide (pas d'espaces).")
        if any(c.name == config.name for c in self.configs):
            errors.append(f"Une factory '{config.name}' existe déjà.")
        if config.nb_particles <= 0:
            errors.append("Le nombre de particules doit être > 0.")
        if config.radius_min <= 0:
            errors.append("radius_min doit être > 0.")
        if config.radius_max < config.radius_min:
            errors.append("radius_max doit être >= radius_min.")
        if config.batch_size <= 0:
            errors.append("batch_size doit être > 0.")
        if config.start_step < 0:
            errors.append("start_step doit être >= 0.")
        if config.interval_steps <= 0:
            errors.append("interval_steps doit être > 0.")
        if not config.model_name:
            errors.append("Un modèle doit être sélectionné.")
        if not config.material_name:
            errors.append("Un matériau doit être sélectionné.")
        if config.dimension not in (2, 3):
            errors.append("La dimension doit être 2 ou 3.")

        return len(errors) == 0, errors

    def generate_pre_code(self, body_counter_start: int = 1) -> str:
        """
        Génère le code pre.py complet pour toutes les factories.
        Recalcule les indices de corps depuis body_counter_start.
        """
        self.reset_body_counter(body_counter_start)
        for cfg in self.configs:
            self._assign_body_indices(cfg)

        blocks = []
        for cfg in self.configs:
            gen = PreCodeGenerator(cfg)
            blocks.append(gen.generate())

        return '\n'.join(blocks)

    def generate_chipy_code(self, nb_steps: int = 1000,
                             freq_write: int = 100,
                             dimension: int = 3) -> str:
        """Génère le code chipy.py complet pour toutes les factories."""
        gen = ChipyCodeGenerator(
            [c for c in self.configs if c.enabled],
            nb_steps=nb_steps,
            freq_write=freq_write,
            dimension=dimension,
        )
        return gen.generate()

    def summary(self) -> str:
        """Retourne un résumé lisible de toutes les factories."""
        if not self.configs:
            return "Aucune factory configurée."
        lines = ["Factories configurées :", ""]
        for i, c in enumerate(self.configs, 1):
            status = "✓" if c.enabled else "✗"
            lines.append(
                f"  [{status}] {i}. {c.name} ({c.factory_type}) "
                f"— {c.nb_particles} × {c.particle_type} "
                f"— {c.nb_batches} vague(s) de {c.batch_size} "
                f"dès le pas {c.start_step}"
            )
            if c.body_index_start > 0:
                lines.append(f"       Indices corps : {c.body_index_start}..{c.body_index_end}")
        return '\n'.join(lines)

    def to_list_of_dicts(self) -> List[dict]:
        return [c.to_dict() for c in self.configs]

    @classmethod
    def from_list_of_dicts(cls, data: List[dict]) -> 'ParticleFactory':
        factory = cls()
        for d in data:
            cfg = FactoryConfig.from_dict(d)
            factory.configs.append(cfg)
        return factory

    # ── Utilitaire interne ────────────────────────────────────────────────────

    def _assign_body_indices(self, config: FactoryConfig):
        """
        Assigne les indices de corps LMGC90 (1-based) à la factory.
        Les parois sont comptées avant les particules.
        """
        # Compter les parois selon le type de conteneur
        nb_walls = _count_walls(config)
        if nb_walls > 0:
            config.wall_index_start = self._current_body_index
            config.wall_index_end   = self._current_body_index + nb_walls - 1
            self._current_body_index += nb_walls

        # Particules
        config.body_index_start = self._current_body_index
        config.body_index_end   = self._current_body_index + config.nb_particles - 1
        self._current_body_index += config.nb_particles

        # Construire le planning des vagues
        config.batches.clear()
        for i in range(config.nb_batches):
            b_start = config.body_index_start + i * config.batch_size
            b_end   = min(b_start + config.batch_size - 1, config.body_index_end)
            nb_act  = b_end - b_start + 1
            step    = config.start_step + i * config.interval_steps
            config.batches.append(FactoryBatch(
                step=step, body_start=b_start,
                body_end=b_end, nb_active=nb_act
            ).to_dict())


def _count_walls(config: FactoryConfig) -> int:
    """Retourne le nombre de parois générées pour le conteneur."""
    shape = config.container_shape
    if shape == ContainerShape.NONE.value:
        return 0
    if config.dimension == 2:
        # Sol + 2 parois = 3 (conteneur ouvert)
        return 3
    # 3D
    if shape == ContainerShape.BOX_CLOSED.value:
        return 6  # 5 faces + couvercle
    if shape in (ContainerShape.BOX_OPEN.value, ContainerShape.SILO_BOX.value):
        return 5  # 5 faces sans couvercle
    return 0


# ============================================================================
# Intégration ScriptGenerator — méthode additionnelle
# ============================================================================

def write_factories(f, factories: List[FactoryConfig], dimension: int = 3):
    """
    Méthode complémentaire pour ScriptGenerator._write_factories().
    Écrit le bloc de code pré-traitement de toutes les factories dans le
    fichier ouvert `f`.
    Appeler depuis ScriptGenerator.generate() après _write_datbox().
    """
    active = [c for c in factories if c.enabled]
    if not active:
        return

    engine = ParticleFactory()
    for cfg in active:
        engine.configs.append(cfg)

    f.write('\n\n')
    f.write('# ============================================================\n')
    f.write('# PARTICLE FACTORIES  — code généré par LMGC90_GUI\n')
    f.write('# ============================================================\n')
    f.write(engine.generate_pre_code())
    f.write('\n')