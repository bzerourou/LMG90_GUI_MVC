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
  PERIODIC      Injections périodiques à intervalle fixe → ligne de production

Chaque Factory produit :
  1. Un bloc de code pre.py   → création des avatars (à insérer avant writeDatbox)
  2. Un fichier body_collection.pkl → indices corps réels (pattern box_generation)
  3. Un bloc de code chipy.py → activation progressive via pickle (box_simulation)

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

# Nom du fichier pickle (indices corps réels) — cf. exemples/box_generation.py
BODY_COLLECTION_PICKLE = 'body_collection.pkl'


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

    # Indices figes : True dès que le DATBOX/pre.py a ete genere avec ces indices.
    # Tant que ce flag est False, l'UI peut recalculer librement (avant-projet
    # pas encore exporte). Une fois True, AUCUN recalcul ne doit ecraser les
    # indices, sous peine de desynchroniser command.py par rapport au DATBOX reel.
    indices_frozen:   bool      = False

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
        self._write_radii_block()
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

    def _write_radii_block(self):
        """
        Écrit le calcul des rayons selon c.distribution, choisi dans
        FactoryParticlesPage (Uniforme / Aléatoire / granulo_Random).

        Auparavant ce bloc utilisait toujours np.linspace(...), ignorant
        totalement le choix de l'utilisateur — corrigé ici pour respecter
        UNIFORM / RANDOM / GRANULO comme dans RadiusGenerator (utilisé pour
        la prévisualisation UI), afin que le script généré produise la même
        distribution que ce qui est montré dans l'interface.
        """
        c = self.cfg

        if c.distribution == SizeDistribution.UNIFORM.value or c.radius_min == c.radius_max:
            self._w(f"_factory_{c.name}_radii = np.full({c.nb_particles}, {(c.radius_min + c.radius_max) / 2.0})")
            return

        if c.distribution == SizeDistribution.GRANULO.value:
            # Utilise pre.granulo_Random si disponible (loi LMGC90 native) ;
            # repli silencieux sur une distribution uniforme numpy équivalente
            # si la fonction est absente de la version de pylmgc90 installée.
            self._w(f"try:")
            self._w(f"    _factory_{c.name}_radii = pre.granulo_Random(")
            self._w(f"        {c.nb_particles}, {c.radius_min}, {c.radius_max}, {c.seed!r})")
            self._w(f"except AttributeError:")
            self._w(f"    _factory_{c.name}_rng_radii = np.random.default_rng({c.seed!r})")
            self._w(f"    _factory_{c.name}_radii = _factory_{c.name}_rng_radii.uniform(")
            self._w(f"        {c.radius_min}, {c.radius_max}, {c.nb_particles})")
            return

        # SizeDistribution.RANDOM (par défaut) : uniforme sur [rmin, rmax]
        self._w(f"_factory_{c.name}_rng_radii = np.random.default_rng({c.seed!r})")
        self._w(f"_factory_{c.name}_radii = _factory_{c.name}_rng_radii.uniform(")
        self._w(f"    {c.radius_min}, {c.radius_max}, {c.nb_particles})")

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

        rbdy = f"RBDY{dim}"
        w("# ── Chargement pickle (indices corps réels) ───────────────────")
        w("import pickle")
        w("import os")
        w(f"_pkl_path = '{BODY_COLLECTION_PICKLE}'")
        w("if not os.path.isfile(_pkl_path):")
        w("    raise FileNotFoundError(")
        w(f"        f\"Fichier '{{_pkl_path}}' introuvable. \"")
        w("        \"Exécutez d'abord le script pre.py pour créer body_collection.pkl.\")")
        w("with open(_pkl_path, 'rb') as _pkl_f:")
        w("    body_collection = pickle.load(_pkl_f)")
        w("print('Chargé', _pkl_path, '—', body_collection.get('total_nb_bodies', '?'), 'corps')")
        w("")

        # Rendre toutes les particules invisibles au départ
        w("# ── Rendre toutes les particules de factory invisibles ─────────")
        w("for _fcfg in body_collection.get('factories', {}).values():")
        w("    if not _fcfg.get('enabled', True):")
        w("        continue")
        w(f"    for _bnum in _fcfg['body_numbers']:")
        w(f"        chipy.{rbdy}_SetInvisible(_bnum)")
        w("")

        # Planning sous forme de dict {step → [body_nums]}
        w("# ── Construire le planning d'activation ───────────────────────")
        w("_activation_schedule = {}  # {step: [body_nums]}")
        w("for _fname, _fcfg in body_collection.get('factories', {}).items():")
        w("    if not _fcfg.get('enabled', True):")
        w("        continue")
        w("    _nums = _fcfg['body_numbers']")
        w("    _bs   = _fcfg['batch_size']")
        w("    _ss   = _fcfg['start_step']")
        w("    _iv   = _fcfg['interval_steps']")
        w("    _nb   = (len(_nums) + _bs - 1) // _bs")
        w("    for _batch_i in range(_nb):")
        w("        _step = _ss + _batch_i * _iv")
        w("        _batch = _nums[_batch_i * _bs : (_batch_i + 1) * _bs]")
        w("        _activation_schedule.setdefault(_step, []).extend(_batch)")
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
        w(f"        for _bnum in _activation_schedule[step]:")
        w(f"            chipy.{rbdy}_SetVisible(_bnum)")
        w(f"        print(f'Step {{step}}: {{len(_activation_schedule[step])}} particule(s) activée(s)')")
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

        Recalcule les indices de corps depuis body_counter_start, SAUF pour
        les factories déjà figées (indices_frozen == True), dont les indices
        restent inchangés. Pour figer explicitement de nouveaux indices,
        appeler freeze_body_indices() avant generate_pre_code().
        """
        self.reset_body_counter(body_counter_start)
        for cfg in self.configs:
            self._assign_body_indices(cfg)

        blocks = []
        for cfg in self.configs:
            gen = PreCodeGenerator(cfg)
            blocks.append(gen.generate())

        return '\n'.join(blocks)

    def generate_pickle_code(self, dimension: int = 2) -> str:
        """
        Génère le code runtime qui sérialise les indices corps réels
        (avatar.number + 1) dans body_collection.pkl.

        Même principe que exemples/box_generation.py : les numéros sont
        lus après bodies.addAvatar(), donc toujours synchronisés avec le
        DATBOX effectivement écrit.
        """
        active = [c for c in self.configs if c.enabled]
        if not active:
            return ''

        lines: List[str] = []
        w = lines.append
        w('')
        w('# ============================================================')
        w('# Sérialisation pickle — indices corps réels')
        w('# (pattern exemples/box_generation.py → box_simulation.py)')
        w('# ============================================================')
        w('import pickle')
        w('')
        w('body_collection = {')
        w("    'total_nb_bodies': len(bodies),")
        w(f"    'dimension': {dimension},")
        w("    'factories': {},")
        w('}')
        w('')
        for cfg in active:
            vn = cfg.name
            w(f"body_collection['factories']['{vn}'] = {{")
            w(f"    'body_numbers': [_av.number + 1 for _av in factory_{vn}_bodies],")
            w(f"    'batch_size': {cfg.batch_size},")
            w(f"    'start_step': {cfg.start_step},")
            w(f"    'interval_steps': {cfg.interval_steps},")
            w(f"    'enabled': True,")
            w('}')
            w('')
        w(f"with open('{BODY_COLLECTION_PICKLE}', 'wb') as _pkl_f:")
        w('    pickle.dump(body_collection, _pkl_f)')
        w(f"print('Écrit {BODY_COLLECTION_PICKLE} —',")
        w("      len(body_collection['factories']), 'factory(s),',")
        w("      body_collection['total_nb_bodies'], 'corps au total')")
        w('')
        return '\n'.join(lines)

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

    def generate_bodies_list_code(self) -> str:
        """
        Génère le code pour ajouter les avatars de factory à `bodies_list`
        avec des noms intelligibles (ex: factory_factory1_disk_0, etc.).
        INCLUT AUSSI la génération et sauvegarde du JSON de métadonnées.
        
        À appeler APRÈS generate_pre_code() dans le script pre.py,
        mais AVANT pre.writeDatbox().
        """
        active = [c for c in self.configs if c.enabled]
        if not active:
            return ''
        
        lines: List[str] = []
        w = lines.append
        w('')
        w('# ============================================================')
        w('# Ajouter les avatars de factory à bodies_list')
        w('# (permet au GUI de les manipuler : CL, table de connectivité)')
        w('# ============================================================')
        w('')
        
        for cfg in active:
            vn = cfg.name
            particle_type_short = 'disk' if 'Disk' in cfg.particle_type else 'sphere' if 'Sphere' in cfg.particle_type else 'part'
            w(f'# Factory: {vn}')
            w(f'for _i, _av in enumerate(factory_{vn}_bodies):')
            w(f'    _name = f"factory_{vn}_{particle_type_short}_{{_i}}"')
            w(f'    try:')
            w(f'        _av.name = _name  # Assigner un nom intelligible (si supporte)')
            w(f'    except Exception:')
            w(f'        pass')
            w(f'    bodies_list.append(_av)')
            w('')
        
        # ── GÉNÉRER ET SAUVEGARDER LE JSON DE MÉTADONNÉES ───────────────
        w('# ============================================================')
        w('# Générer et sauvegarder les métadonnées JSON des avatars')
        w('# ============================================================')
        w('import json')
        w('')
        w('_factory_metadata = {"factories": {}}')
        w('')
        
        for cfg in active:
            vn = cfg.name
            particle_type_short = 'disk' if 'Disk' in cfg.particle_type else 'sphere' if 'Sphere' in cfg.particle_type else 'part'
            w(f'# Factory: {vn}')
            w(f'_factory_metadata["factories"]["{vn}"] = {{')
            w(f'    "particle_type": "{cfg.particle_type}",')
            w(f'    "nb_particles": {cfg.nb_particles},')
            w(f'    "color": "{cfg.color}",')
            w(f'    "avatars": []')
            w(f'}}')
            w(f'for _i, _av in enumerate(factory_{vn}_bodies):')
            w(f'    _avatar_info = {{')
            w(f'        "name": getattr(_av, "name", f"factory_{vn}_{particle_type_short}_{{_i}}"),')
            w(f'        # avatar_id déterministe : stable entre executions, ')
            w(f'        # permet à ProjectState de retrouver l\'avatar après reload')
            w(f'        "avatar_id": f"factory_{vn}_{particle_type_short}_{{_i}}",')
            w(f'        "body_index": _av.number + 1,  # 1-based')
            w(f'        "type": "{cfg.particle_type}",')
            w(f'        "center": list(_factory_{vn}_positions[_i]),')
            w(f'        "radius": float(_av.r) if hasattr(_av, "r") else {cfg.radius_max},')
            w(f'        "color": "{cfg.color}",')
            w(f'        "material": "{cfg.material_name}",')
            w(f'        "model": "{cfg.model_name}",')
            w(f'        "factory_name": "{vn}",')
            w(f'        "factory_type": "{cfg.factory_type}"')
            w(f'    }}')
            w(f'    _factory_metadata["factories"]["{vn}"]["avatars"].append(_avatar_info)')
            w('')
        
        w('# Sauvegarder le JSON')
        w('with open("factory_avatars_metadata.json", "w", encoding="utf-8") as _json_f:')
        w('    json.dump(_factory_metadata, _json_f, indent=2, ensure_ascii=False)')
        w('print("✓ Métadonnées factory sauvegardes dans factory_avatars_metadata.json")')
        w('')
        
        return '\n'.join(lines)

    def generate_avatar_metadata_json(self) -> dict:
        """
        Génère un dictionnaire de métadonnées des avatars de factory
        que l'interface peut charger pour recréer les entrées dans state.avatars.
        
        Returns:
            dict with structure: {
                'factories': {
                    'factory_name': {
                        'particle_type': 'rigidDisk',
                        'avatars': [
                            {
                                'name': 'factory_name_disk_0',
                                'body_index': 1,
                                'type': 'rigidDisk',
                                'radius': 0.01,
                                'color': 'BLUEx',
                                'center': [0.0, 0.0, 2.0]
                            },
                            ...
                        ]
                    }
                }
            }
        """
        metadata = {'factories': {}}
        
        for cfg in self.configs:
            if not cfg.enabled:
                continue
            
            vn = cfg.name
            particle_type_short = 'disk' if 'Disk' in cfg.particle_type else 'sphere' if 'Sphere' in cfg.particle_type else 'part'
            
            avatars_info = []
            # Générer les infos pour chaque avatar créé
            nb_created = cfg.nb_particles
            for i in range(nb_created):
                body_idx = cfg.body_index_start + i
                avatar_name = f"factory_{vn}_{particle_type_short}_{i}"
                
                avatars_info.append({
                    'name': avatar_name,
                    'body_index': body_idx,
                    'type': cfg.particle_type,
                    'radius': cfg.radius_max,  # Utiliser rmax pour la métadonnée (varie à l'exécution)
                    'color': cfg.color,
                    'material': cfg.material_name,
                    'model': cfg.model_name,
                    'factory_name': vn,
                    'factory_type': cfg.factory_type,
                })
            
            metadata['factories'][vn] = {
                'particle_type': cfg.particle_type,
                'nb_particles': cfg.nb_particles,
                'color': cfg.color,
                'avatars': avatars_info
            }
        
        return metadata

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

    def freeze_body_indices(self, body_counter_start: int = 1) -> None:
        """
        Calcule et FIGE définitivement les indices de corps de toutes les
        factories, dans l'ordre de self.configs, à partir de body_counter_start.

        À appeler UNIQUEMENT au moment où le DATBOX/pre.py réel est généré
        (bouton "Générer Script Python", "Générer DATBOX", ou équivalent).
        C'est ce moment qui détermine l'ordre réel des corps dans le DATBOX ;
        tout calcul ultérieur (UI, command.py) doit relire ces indices figés
        sans les recalculer, sous peine de désynchronisation.
        """
        self.reset_body_counter(body_counter_start)
        for cfg in self.configs:
            cfg.indices_frozen = False        # autoriser un nouveau calcul
            self._assign_body_indices(cfg, force=True)

    def refresh_unfrozen_indices(self, body_counter_start: int = 1) -> None:
        """
        Recalcule uniquement les indices des factories PAS encore figées
        (indices_frozen == False) — utile pour l'aperçu dans l'UI avant tout
        export. Les factories déjà figées (export déjà effectué) ne sont pas
        modifiées : leurs indices restent ceux du dernier DATBOX généré.
        """
        self.reset_body_counter(body_counter_start)
        for cfg in self.configs:
            self._assign_body_indices(cfg, force=False)

    def _assign_body_indices(self, config: FactoryConfig, force: bool = False):
        """
        Assigne les indices de corps LMGC90 (1-based) à la factory.
        Les parois sont comptées avant les particules.

        Si config.indices_frozen est True et force=False, ne fait RIEN :
        les indices ont déjà été figés lors d'une génération précédente du
        DATBOX/pre.py et ne doivent plus changer, sous peine de désynchroniser
        les scripts command.py qui s'appuient sur ces indices pour
        SetVisible/SetInvisible.

        Passer force=True uniquement au moment où l'on génère réellement le
        DATBOX/pre.py (c'est ce point qui doit figer les indices définitifs).
        """
        if config.indices_frozen and not force:
            # Ne pas toucher self._current_body_index : on doit tout de même
            # l'avancer pour que les factories suivantes restent cohérentes
            # entre elles dans cette même passe de calcul.
            nb_walls = _count_walls(config) if config.wall_index_start else 0
            if config.wall_index_end:
                self._current_body_index = max(
                    self._current_body_index, config.wall_index_end + 1
                )
            self._current_body_index = max(
                self._current_body_index, config.body_index_end + 1
            )
            return

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

        if force:
            config.indices_frozen = True


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
    
    Génère automatiquement :
    1. Code pre.py pour créer les avatars (factory_factory1_bodies, etc.)
    2. Code pour ajouter les avatars à bodies_list (avec noms intelligibles)
    3. Code pour générer factory_avatars_metadata.json dans le script pre.py
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
    
    # Ajouter les avatars de factory à bodies_list avec des noms intelligibles
    # ET générer le JSON de métadonnées
    f.write(engine.generate_bodies_list_code())


# ============================================================================
# Sérialisation pickle — avatars et indices corps
# ============================================================================

def save_bodies_to_pickle(bodies_container, pickle_path: str = BODY_COLLECTION_PICKLE) -> None:
    """
    Sérialise les avatars créés dans un fichier pickle.
    À appeler APRÈS bodies.addAvatar() et AVANT pre.writeDatbox().
    
    Args:
        bodies_container: conteneur pre.avatars() contenant tous les corps
        pickle_path: chemin du fichier pickle à créer
    
    Exemple:
        bodies = pre.avatars()
        # ... créer les avatars et les ajouter avec bodies.addAvatar()
        save_bodies_to_pickle(bodies, 'bodies_collection.pkl')
        pre.writeDatbox(mats=mats, mods=mods, bodies=bodies, ...)
    """
    import pickle
    
    bodies_data = {
        'total_nb_bodies': len(bodies_container),
        'bodies_info': []
    }
    
    # Parcourir tous les avatars dans le conteneur
    for avatar in bodies_container:
        # Récupérer les infos essentielles : numéro (1-based), type, position, rayon si applicable
        info = {
            'number': avatar.number + 1,  # 1-based indexing
            'name': getattr(avatar, 'name', 'unknown'),
            'type': type(avatar).__name__,  # rigidDisk, rigidSphere, rigidJonc, etc.
        }
        
        # Position du centre
        if hasattr(avatar, 'center'):
            info['center'] = list(avatar.center) if hasattr(avatar.center, '__iter__') else [avatar.center]
        
        # Rayon (pour disques/sphères)
        if hasattr(avatar, 'r'):
            info['radius'] = avatar.r
        
        # Couleur
        if hasattr(avatar, 'color'):
            info['color'] = avatar.color
        
        bodies_data['bodies_info'].append(info)
    
    # Écrire le pickle
    with open(pickle_path, 'wb') as f:
        pickle.dump(bodies_data, f)
    
    print(f'✓ Sérialisé {bodies_data["total_nb_bodies"]} corps dans {pickle_path}')


def load_bodies_from_pickle(pickle_path: str = BODY_COLLECTION_PICKLE) -> dict:
    """
    Charge les avatars sérialisés depuis un fichier pickle.
    À appeler dans le script de calcul (command.py / chipy.py).
    
    Returns:
        dict contenant 'total_nb_bodies' et 'bodies_info' (liste des infos corps)
    
    Exemple:
        bodies_data = load_bodies_from_pickle('bodies_collection.pkl')
        print(f"Total: {bodies_data['total_nb_bodies']} corps")
        for info in bodies_data['bodies_info']:
            print(f"  Corps {info['number']}: {info['type']} à {info['center']}")
    """
    import pickle
    import os
    
    if not os.path.isfile(pickle_path):
        raise FileNotFoundError(f"Fichier pickle non trouvé: {pickle_path}")
    
    with open(pickle_path, 'rb') as f:
        bodies_data = pickle.load(f)
    
    print(f'✓ Chargé {bodies_data["total_nb_bodies"]} corps depuis {pickle_path}')
    return bodies_data


def load_factory_avatars_from_json(json_path: str = 'factory_avatars_metadata.json') -> dict:
    """
    Charge les métadonnées des avatars de factory depuis le JSON généré.
    À utiliser par le GUI pour recréer les entrées Avatar dans state.avatars.
    
    Args:
        json_path: chemin du fichier JSON de métadonnées
    
    Returns:
        dict avec structure:
        {
            'factories': {
                'factory1': {
                    'particle_type': 'rigidDisk',
                    'nb_particles': 100,
                    'color': 'BLUEx',
                    'avatars': [
                        {'name': 'factory_factory1_disk_0', 'body_index': 1, ...},
                        {'name': 'factory_factory1_disk_1', 'body_index': 2, ...},
                        ...
                    ]
                }
            }
        }
    
    Exemple d'utilisation dans le GUI :
        metadata = load_factory_avatars_from_json()
        for factory_name, factory_data in metadata['factories'].items():
            print(f"Factory {factory_name}: {factory_data['nb_particles']} particles")
            for avatar_info in factory_data['avatars']:
                # Créer des Avatar objects et les ajouter à state.avatars
                avatar = Avatar(
                    avatar_type=AvatarType(...),
                    center=...,
                    material_name=avatar_info['material'],
                    model_name=avatar_info['model'],
                    color=avatar_info['color'],
                    origin=AvatarOrigin.LOOP,  # avatars générés
                    radius=avatar_info['radius']
                )
                controller.add_avatar(avatar)
    """
    import json
    import os
    
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"Fichier JSON non trouvé: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    nb_factories = len(metadata.get('factories', {}))
    nb_total = sum(
        len(factory['avatars']) 
        for factory in metadata.get('factories', {}).values()
    )
    
    print(f'✓ Chargé métadonnées : {nb_factories} factory(ies), {nb_total} avatar(s) total')
    return metadata


def create_avatars_from_factory_metadata(metadata: dict) -> list:
    """
    Crée des objets Avatar à partir des métadonnées JSON de factory.
    À appeler après load_factory_avatars_from_json().
    
    Args:
        metadata: dict retourné par load_factory_avatars_from_json()
    
    Returns:
        Liste d'Avatar objects prêts à être ajoutés au state via controller.add_avatar()
    
    Exemple:
        metadata = load_factory_avatars_from_json()
        avatars = create_avatars_from_factory_metadata(metadata)
        for avatar in avatars:
            controller.add_avatar(avatar)
    """
    from .models import Avatar, AvatarType, AvatarOrigin

    avatars = []

    for factory_name, factory_data in metadata.get('factories', {}).items():
        particle_type_short = (
            'disk'   if 'Disk'   in factory_data.get('particle_type', '') else
            'sphere' if 'Sphere' in factory_data.get('particle_type', '') else
            'part'
        )
        for i, avatar_info in enumerate(factory_data.get('avatars', [])):
            # Convertir le type de particule en AvatarType enum
            particle_type_str = avatar_info['type']
            try:
                avatar_type = AvatarType(particle_type_str)
            except ValueError:
                print(f"⚠ Type d'avatar non reconnu: {particle_type_str}, ignoré")
                continue

            # ── avatar_id déterministe ─────────────────────────────────────
            # Priorité 1 : champ "avatar_id" présent dans le JSON
            #              (généré par generate_bodies_list_code depuis v2)
            # Priorité 2 : schéma déterministe factory_name + index
            #              (rétro-compatibilité avec les JSON sans ce champ)
            # Dans les deux cas le même avatar_id est produit à chaque appel,
            # ce qui garantit la stabilité des avatar_groups après reload.
            deterministic_id = f"factory_{factory_name}_{particle_type_short}_{i}"
            stable_avatar_id = avatar_info.get('avatar_id') or deterministic_id

            # Créer l'objet Avatar avec l'id stable
            avatar = Avatar(
                avatar_id=stable_avatar_id,          # id stable, non aléatoire
                avatar_type=avatar_type,
                center=avatar_info.get('center', [0., 0., 0.]),
                material_name=avatar_info.get('material', 'default'),
                model_name=avatar_info.get('model', 'default'),
                color=avatar_info.get('color', 'BLUEx'),
                origin=AvatarOrigin.FACTORY,          # ← origine explicite
                radius=avatar_info.get('radius'),
            )

            avatars.append(avatar)

    print(f'✓ Créé {len(avatars)} Avatar objects à partir des métadonnées')
    return avatars