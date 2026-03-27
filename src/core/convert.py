#!/usr/bin/env python3
# ============================================================================
# py2lmgc90.py  —  Convertisseur script pylmgc90 → projet .lmgc90 (GUI)
# ============================================================================
"""
Convertit un script Python de pré-traitement pylmgc90 en fichier de projet
.lmgc90 lisible par LMGC90_GUI.

Stratégie : exécution du script dans un environnement contrôlé où
pylmgc90.pre est remplacé par un module fantôme (MockPre) qui intercepte
tous les appels et construit la représentation du projet.

Usage :
    python py2lmgc90.py mon_script.py               → mon_script.lmgc90
    python py2lmgc90.py mon_script.py -o sortie.lmgc90
    python py2lmgc90.py mon_script.py --check        # vérif sans écrire

Éléments convertis :
    ✓ pre.material(...)           → matériaux
    ✓ pre.model(...)              → modèles
    ✓ pre.rigidDisk(...)          → avatar rigidDisk
    ✓ pre.rigidJonc(...)          → avatar rigidJonc
    ✓ pre.rigidPolygon(...)       → avatar rigidPolygon
    ✓ pre.rigidOvoidPolygon(...)  → avatar rigidOvoidPolygon
    ✓ pre.rigidDiscreteDisk(...)  → avatar rigidDiscreteDisk
    ✓ pre.rigidCluster(...)       → avatar rigidCluster
    ✓ pre.roughWall(...)          → avatar roughWall
    ✓ pre.fineWall(...)           → avatar fineWall
    ✓ pre.smoothWall(...)         → avatar smoothWall
    ✓ pre.granuloRoughWall(...)   → avatar granuloRoughWall
    ✓ pre.rigidSphere(...)        → avatar rigidSphere (3D)
    ✓ pre.rigidPlan(...)          → avatar rigidPlan  (3D)
    ✓ pre.rigidCylinder(...)      → avatar rigidCylinder (3D)
    ✓ pre.rigidPolyhedron(...)    → avatar rigidPolyhedron (3D)
    ✓ .translate(dx, dy, dz)     → DOFOperation translate
    ✓ .rotate(...)               → DOFOperation rotate
    ✓ .imposeDrivenDof(...)      → DOFOperation imposeDrivenDof
    ✓ .imposeInitValue(...)      → DOFOperation imposeInitValue
    ✓ bodies.addAvatar(av)       → enregistrement dans bodies
    ✓ bodies += av               → idem
    ✓ pre.tact_behav(...)        → loi de contact
    ✓ tacts.addBehav(law)        → enregistrement loi
    ✓ tacts += law               → idem
    ✓ pre.see_table(...)         → table de visibilité
    ✓ svs.addSeeTable(st)        → enregistrement visibilité
    ✓ svs += st                  → idem
    ✓ pre.postpro_command(...)   → commande postpro
    ✓ posts.addCommand(cmd)      → enregistrement postpro
    ✓ pre.granulo_Random(...)    → génération granulométrique
    ✓ pre.depositInBox2D(...)    → dépôt Box2D
    ✓ pre.depositInDisk2D(...)   → dépôt Disk2D
    ✓ pre.depositInCouette2D(...)→ dépôt Couette2D
    ✓ pre.depositInDrum2D(...)   → dépôt Drum2D
    ✓ pre.depositInBox3D(...)    → dépôt Box3D
    ✓ pre.depositInSphere3D(...) → dépôt Sphere3D
    ✓ pre.depositInCylinder3D(...)→ dépôt Cylinder3D
    ✓ dim = 2 / dim = 3          → dimension du projet

Limitations connues :
    • Les boucles for complexes avec conditions dépendant du résultat de
      fonctions pylmgc90 peuvent ne pas être tracées complètement.
    • Les fonctions de maillage déformable (buildMesh2D, buildMeshH8,
      buildMeshedAvatar) ne sont pas converties en avatars individuels
      mais signalées comme avertissements.
"""

import sys
import os
import json
import math
import copy
import argparse
import traceback
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# Objets proxy — représentation interne pendant l'exécution du script
# ============================================================================

class _AvatarObj:
    """Proxy d'un avatar pendant l'exécution du script."""

    def __init__(self, avatar_type: str, kwargs: dict):
        self._type     = avatar_type
        self._kwargs   = kwargs
        self._dof_ops  = []   # opérations DOF appliquées sur cet avatar

    # ── Transformations géométriques ─────────────────────────────────────────

    def translate(self, dx=0., dy=0., dz=0., **kw):
        self._dof_ops.append({
            'op': 'translate',
            'params': {'dx': float(dx), 'dy': float(dy), 'dz': float(dz)}
        })
        # Mettre à jour le centre stocké immédiatement
        c = self._kwargs.get('center', [0., 0.])
        if len(c) == 2:
            self._kwargs['center'] = [c[0] + float(dx), c[1] + float(dy)]
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

    # ── Conditions aux limites ───────────────────────────────────────────────

    def imposeDrivenDof(self, group='all', component=1, description='predefined',
                        dofty='vlocy', ct=0., amp=0., omega=0., phi=0.,
                        rampi=1., ramp=0., evolutionFile='', **kw):
        params = {'group': group, 'component': _to_serial(component),
                  'dofty': dofty, 'ct': float(ct)}
        if amp:   params['amp']   = float(amp)
        if omega: params['omega'] = float(omega)
        if phi:   params['phi']   = float(phi)
        if rampi != 1.: params['rampi'] = float(rampi)
        if ramp:  params['ramp']  = float(ramp)
        if evolutionFile: params['evolutionFile'] = evolutionFile
        if description != 'predefined': params['description'] = description
        self._dof_ops.append({'op': 'imposeDrivenDof', 'params': params})

    def imposeInitValue(self, group='all', component=1, value=0., **kw):
        params = {'group': group, 'component': _to_serial(component),
                  'value': float(value)}
        self._dof_ops.append({'op': 'imposeInitValue', 'params': params})

    # ── Accesseur pour les nœuds (lecture seule, compatibilité scripts) ──────

    @property
    def nodes(self):
        return _NodesMock(self._kwargs.get('center', [0., 0.]))

    def __repr__(self):
        return f"Avatar({self._type}, center={self._kwargs.get('center')})"


class _NodesMock:
    """Simule body.nodes[1].coor pour les scripts qui lisent le centre."""
    def __init__(self, center):
        self._c = list(center)

    def __getitem__(self, idx):
        return self

    @property
    def coor(self):
        return self._c


class _MaterialObj:
    def __init__(self, name, materialType='RIGID', density=1000., **props):
        self.name         = name
        self.material_type = materialType
        self.density      = float(density)
        self.props        = {k: v for k, v in props.items()}

    def __repr__(self):
        return f"Material({self.name})"


class _ModelObj:
    def __init__(self, name, physics='MECAx', element='Rxx2D', dimension=2, **opts):
        self.name      = name
        self.physics   = physics
        self.element   = element
        self.dimension = int(dimension)
        self.opts      = {k: v for k, v in opts.items()}

    def __repr__(self):
        return f"Model({self.name})"


class _TactBehavObj:
    def __init__(self, name, law, fric=None, **props):
        self.name  = name
        self.law   = law
        self.fric  = fric
        self.props = {k: v for k, v in props.items()}

    def __repr__(self):
        return f"TactBehav({self.name}, {self.law})"


class _SeeTableObj:
    def __init__(self, CorpsCandidat, candidat, colorCandidat,
                 CorpsAntagoniste, antagoniste, colorAntagoniste,
                 behav, alert=0.1, **kw):
        self.candidate_body      = CorpsCandidat
        self.candidate_contactor = candidat
        self.candidate_color     = colorCandidat
        self.antagonist_body     = CorpsAntagoniste
        self.antagonist_contactor = antagoniste
        self.antagonist_color    = colorAntagoniste
        self.behav_name          = (behav.name if isinstance(behav, _TactBehavObj)
                                    else str(behav))
        self.alert               = float(alert)


class _PostproCommandObj:
    def __init__(self, name, step=1, rigid_set=None, **kw):
        self.name      = name
        self.step      = int(step)
        self.rigid_set = rigid_set  # liste d'_AvatarObj ou None


class _GranuloRadii:
    """Tableau de rayons retourné par granulo_Random."""
    def __init__(self, nb, rmin, rmax, seed=None):
        self.nb   = nb
        self.rmin = rmin
        self.rmax = rmax
        self.seed = seed
        # Simuler le tableau numpy (shape compatible)
        rng = np.random.default_rng(seed)
        self._arr = rng.uniform(rmin, rmax, nb)

    def __len__(self):
        return len(self._arr)

    def __getitem__(self, idx):
        return self._arr[idx]

    def __setitem__(self, idx, v):
        self._arr[idx] = v

    @property
    def size(self):
        return self._arr.size


class _Container:
    """Conteneur générique (avatars, matériaux, modèles, lois, tables, posts)."""

    def __init__(self, kind=''):
        self._items: List[Any] = []
        self._kind = kind

    def _add(self, item):
        self._items.append(item)

    def addAvatar(self, item):   self._add(item)
    def addMaterial(self, *args):
        for a in args: self._add(a)
    def addModel(self, item):    self._add(item)
    def addBehav(self, item):    self._add(item)
    def addSeeTable(self, item): self._add(item)
    def addCommand(self, item):  self._add(item)

    def __iadd__(self, item):
        self._add(item)
        return self

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __repr__(self):
        return f"Container({self._kind}, {len(self._items)} items)"


# ============================================================================
# Module mock pylmgc90.pre
# ============================================================================

class _MockPre:
    """
    Remplace pylmgc90.pre pendant l'exécution du script.
    Intercepte toutes les fonctions de création d'objets.
    """

    def __init__(self, converter: 'Converter'):
        self._cv = converter

    # ── Conteneurs vides ─────────────────────────────────────────────────────

    def avatars(self):       return _Container('avatars')
    def materials(self):     return _Container('materials')
    def models(self):        return _Container('models')
    def tact_behavs(self):   return _Container('tact_behavs')
    def see_tables(self):    return _Container('see_tables')
    def postpro_commands(self): return _Container('postpro_commands')

    # ── Matériaux ─────────────────────────────────────────────────────────────

    def material(self, name, materialType='RIGID', density=1000., **kw):
        obj = _MaterialObj(name, materialType, density, **kw)
        self._cv._materials[name] = obj
        return obj

    # ── Modèles ───────────────────────────────────────────────────────────────

    def model(self, name, physics='MECAx', element='Rxx2D', dimension=2, **kw):
        obj = _ModelObj(name, physics, element, dimension, **kw)
        self._cv._models[name] = obj
        return obj

    # ── Avatars 2D ───────────────────────────────────────────────────────────

    def _make_avatar(self, avatar_type: str, **kw) -> _AvatarObj:
        kw = _normalize_kwargs(kw)
        obj = _AvatarObj(avatar_type, kw)
        self._cv._avatar_pool.append(obj)
        return obj

    def rigidDisk(self, r=0.1, center=None, model=None, material=None,
                  color='BLUEx', **kw):
        return self._make_avatar('rigidDisk', r=float(r),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color, **kw)

    def rigidJonc(self, axe1=1., axe2=0.1, center=None, model=None,
                  material=None, color='BLUEx', **kw):
        return self._make_avatar('rigidJonc', axe1=float(axe1), axe2=float(axe2),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color, **kw)

    def rigidPolygon(self, model=None, material=None, center=None, color='BLUEx',
                     theta=0., radius=1., generation_type='regular',
                     nb_vertices=None, vertices=None, **kw):
        kw_av = dict(center=_center(center), model=_name(model),
                     material=_name(material), color=color,
                     radius=float(radius), generation_type=generation_type)
        if theta:
            kw_av['theta'] = float(theta)
        if nb_vertices is not None:
            kw_av['nb_vertices'] = int(nb_vertices)
        if vertices is not None:
            kw_av['vertices'] = _to_serial(vertices)
        return self._make_avatar('rigidPolygon', **kw_av)

    def rigidOvoidPolygon(self, ra=1., rb=1., nb_vertices=8, center=None,
                          model=None, material=None, color='BLUEx', **kw):
        return self._make_avatar('rigidOvoidPolygon',
                                 ra=float(ra), rb=float(rb),
                                 nb_vertices=int(nb_vertices),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color, **kw)

    def rigidDiscreteDisk(self, r=0.1, center=None, model=None, material=None,
                          color='BLUEx', **kw):
        return self._make_avatar('rigidDiscreteDisk', r=float(r),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color, **kw)

    def rigidCluster(self, nb_disk=3, r=0.1, center=None, model=None,
                     material=None, color='BLUEx', **kw):
        return self._make_avatar('rigidCluster', nb_disk=int(nb_disk),
                                 r=float(r), center=_center(center),
                                 model=_name(model), material=_name(material),
                                 color=color, **kw)

    def roughWall(self, lx=1., ly=0.1, center=None, model=None,
                  material=None, color='BLUEx', **kw):
        return self._make_avatar('roughWall', lx=float(lx), ly=float(ly),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color, **kw)

    def fineWall(self, lx=1., ly=0.1, center=None, model=None,
                 material=None, color='BLUEx', **kw):
        return self._make_avatar('fineWall', lx=float(lx), ly=float(ly),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color, **kw)

    def smoothWall(self, lx=1., ly=0.1, center=None, model=None,
                   material=None, color='BLUEx', **kw):
        return self._make_avatar('smoothWall', lx=float(lx), ly=float(ly),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color, **kw)

    def granuloRoughWall(self, lx=1., ly=0.1, center=None, model=None,
                         material=None, color='BLUEx', **kw):
        return self._make_avatar('granuloRoughWall', lx=float(lx), ly=float(ly),
                                 center=_center(center), model=_name(model),
                                 material=_name(material), color=color, **kw)

    # ── Avatars 3D ───────────────────────────────────────────────────────────

    def rigidSphere(self, r=0.1, center=None, model=None, material=None,
                    color='BLUEx', **kw):
        return self._make_avatar('rigidSphere', r=float(r),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color, **kw)

    def rigidPlan(self, center=None, model=None, material=None,
                  color='BLUEx', **kw):
        return self._make_avatar('rigidPlan',
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color, **kw)

    def rigidCylinder(self, r=0.5, h=1., center=None, model=None,
                      material=None, color='BLUEx', **kw):
        return self._make_avatar('rigidCylinder', r=float(r), h=float(h),
                                 center=_center(center, dim=3),
                                 model=_name(model), material=_name(material),
                                 color=color, **kw)

    def rigidPolyhedron(self, model=None, material=None, center=None,
                        color='BLUEx', vertices=None, faces=None, **kw):
        kw_av = dict(center=_center(center, dim=3), model=_name(model),
                     material=_name(material), color=color)
        if vertices is not None:
            kw_av['vertices'] = _to_serial(vertices)
        if faces is not None:
            kw_av['faces'] = _to_serial(faces)
        return self._make_avatar('rigidPolyhedron', **kw_av)

    # ── Lois de contact ───────────────────────────────────────────────────────

    def tact_behav(self, name, law, fric=None, **kw):
        obj = _TactBehavObj(name, law, fric, **kw)
        self._cv._tact_behavs[name] = obj
        return obj

    # ── Tables de visibilité ──────────────────────────────────────────────────

    def see_table(self, CorpsCandidat, candidat, colorCandidat,
                  CorpsAntagoniste, antagoniste, colorAntagoniste,
                  behav, alert=0.1, **kw):
        obj = _SeeTableObj(CorpsCandidat, candidat, colorCandidat,
                           CorpsAntagoniste, antagoniste, colorAntagoniste,
                           behav, alert)
        self._cv._see_tables.append(obj)
        return obj

    # ── Commandes post-traitement ─────────────────────────────────────────────

    def postpro_command(self, name, step=1, rigid_set=None, **kw):
        obj = _PostproCommandObj(name, step, rigid_set)
        self._cv._postpro_cmds.append(obj)
        return obj

    # ── Granulométrie ─────────────────────────────────────────────────────────

    def granulo_Random(self, nb, rmin=None, rmax=None, r_min=None, r_max=None, seed=None, **kw):
        rmin = rmin if rmin is not None else r_min
        rmax = rmax if rmax is not None else r_max
        obj = _GranuloRadii(int(nb), float(rmin), float(rmax), seed)
        self._cv._last_granulo = {
            'nb': int(nb), 'rmin': float(rmin), 'rmax': float(rmax), 'seed': seed
        }
        return obj

    def _deposit(self, container_type: str, radii, params: dict):
        nb   = len(radii) if hasattr(radii, '__len__') else int(radii.nb)
        rng  = np.random.default_rng(None)
        coords = rng.uniform(0, 1, (nb, 2))
        self._cv._last_deposit = {
            'container_type': container_type,
            'container_params': params,
            'nb_particles': nb,
        }
        # Retourner un tuple (nb_remaining, coords) pour compatibilité
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
        return self._deposit('Box3D', radii, {'lx': float(lx), 'ly': float(ly), 'lz': float(lz)})

    def depositInSphere3D(self, radii=None, r=2., **kw):
        return self._deposit('Sphere3D', radii, {'r': float(r)})

    def depositInCylinder3D(self, radii=None, r=2., **kw):
        return self._deposit('Cylinder3D', radii, {'r': float(r)})

    # ── Maillage EF (stub — pas converti en avatars GUI) ─────────────────────

    def buildMesh2D(self, *a, **kw):
        self._cv._warnings.append(
            "buildMesh2D() détecté — utilisez l'assistant Corps Déformable dans LMGC90_GUI."
        )
        return _FakeMesh('buildMesh2D')

    def buildMeshH8(self, *a, **kw):
        self._cv._warnings.append(
            "buildMeshH8() détecté — utilisez l'assistant Corps Déformable dans LMGC90_GUI."
        )
        return _FakeMesh('buildMeshH8')

    def buildMeshedAvatar(self, *a, **kw):
        return _FakeMesh('buildMeshedAvatar')

    def readMesh(self, *a, **kw):
        return _FakeMesh('readMesh')

    # ── writeDatbox — intercepte la dimension ─────────────────────────────────

    def writeDatbox(self, dim=2, mats=None, mods=None, bodies=None,
                    tacts=None, sees=None, post=None, datbox_path='DATBOX', **kw):
        if isinstance(dim, int):
            self._cv._dimension = int(dim)

    # ── Visualisation / divers (ignorés silencieusement) ─────────────────────

    def visuAvatars(self, *a, **kw):       pass
    def saveAvatarSet(self, *a, **kw):     pass
    def loadAvatarSet(self, *a, **kw):     return _Container('avatars')
    def avatar(self, *a, **kw):            return _AvatarObj('emptyAvatar', {})

    # ── Bricks (maçonnerie) — stub ───────────────────────────────────────────

    def brick2D(self, *a, **kw):
        return _BrickObj('brick2D', *a, **kw)

    def brick3D(self, *a, **kw):
        return _BrickObj('brick3D', *a, **kw)

    def paneresse_simple(self, *a, **kw):
        return _WallObj('paneresse_simple')

    def paneresse_double(self, *a, **kw):
        return _WallObj('paneresse_double')


class _FakeMesh:
    """Objet maillage factice pour ne pas bloquer l'exécution."""
    def __init__(self, src):
        self._src = src
        self.nodes = [_NodesMock([0., 0.])]
        self.bulks = []

    def addNode(self, *a): pass
    def addBulk(self, *a): pass
    def defineGroups(self):   pass
    def defineModel(self, *a, **kw): pass
    def defineMaterial(self, *a, **kw): pass
    def addContactors(self, *a, **kw): pass
    def computeRigidProperties(self): pass
    def imposeInitValue(self, *a, **kw): pass
    def imposeDrivenDof(self, *a, **kw): pass
    def translate(self, *a, **kw): pass
    def rotate(self, *a, **kw): pass


class _BrickObj:
    def __init__(self, kind, name=None, lx=None, ly=None, lz=None, **kw):
        self._kind = kind
        self._name = name
        self._lx = lx; self._ly = ly; self._lz = lz

    def rigidBrick(self, center=None, model=None, material=None, color='BLUEx', **kw):
        return _AvatarObj('emptyAvatar', dict(center=_center(center),
                          model=_name(model), material=_name(material), color=color))


class _WallObj:
    def __init__(self, kind):
        self._kind = kind

    def setNumberOfRows(self, n): pass
    def setJointThicknessBetweenRows(self, e): pass
    def computeHeight(self): pass
    def setFirstRowByNumberOfBricks(self, *a, **kw): pass
    def setFirstRowByLength(self, *a, **kw): pass
    def buildRigidWall(self, *a, **kw): return []
    def buildRigidWallWithoutHalfBricks(self, *a, **kw): return []


# ============================================================================
# Convertisseur principal
# ============================================================================

class Converter:
    """
    Exécute un script pylmgc90 dans un environnement contrôlé
    et extrait les objets du projet.
    """

    def __init__(self, script_path: Path):
        self.script_path = script_path
        self.project_name = script_path.stem

        # État du projet
        self._dimension  = 2
        self._materials  : Dict[str, _MaterialObj]  = {}
        self._models     : Dict[str, _ModelObj]     = {}
        self._avatar_pool: List[_AvatarObj]          = []  # tous les avatars créés
        self._bodies     : List[_AvatarObj]          = []  # avatars dans bodies
        self._tact_behavs: Dict[str, _TactBehavObj] = {}
        self._see_tables : List[_SeeTableObj]        = []
        self._postpro_cmds: List[_PostproCommandObj] = []
        self._last_granulo: Optional[dict]           = None
        self._last_deposit: Optional[dict]           = None
        self._granulo_gens: List[dict]               = []

        self._warnings: List[str] = []

    # ── Exécution du script ───────────────────────────────────────────────────

    def run(self):
        """Exécute le script et capture les objets."""
        script_src = self.script_path.read_text(encoding='utf-8', errors='replace')
        pre  = _MockPre(self)
        mock_pylmgc90 = type(sys)('pylmgc90')
        mock_pylmgc90.pre = pre

        # Construire un bodies container qui intercepte les ajouts
        bodies_container = _TrackedContainer(self)
        tacts_container  = _Container('tacts')
        sees_container   = _Container('sees')
        posts_container  = _Container('posts')
        mats_container   = _Container('mats')
        mods_container   = _Container('mods')

        glob = {
            '__name__': '__main__',
            '__file__': str(self.script_path),
            'os': type(sys)('os'),
            'sys': sys,
            'math': math,
            'numpy': np,
            'np': np,
            'matplotlib': _SilentModule('matplotlib'),
            'plt': _SilentModule('plt'),
            'bodies': bodies_container,
            'mats':   mats_container,
            'mods':   mods_container,
            'tacts':  tacts_container,
            'svs':    sees_container,
            'sees':   sees_container,
            'post':   posts_container,
            'posts':  posts_container,
            'pre':    pre,
        }
        # Patch os.mkdir / os.path pour ne pas créer DATBOX
        import types
        fake_os = types.SimpleNamespace(
            path=types.SimpleNamespace(
                isdir=lambda p: True,
                exists=lambda p: True,
                join=os.path.join,
                dirname=os.path.dirname,
                basename=os.path.basename,
            ),
            mkdir=lambda *a, **kw: None,
            getcwd=os.getcwd,
        )
        glob['os'] = fake_os

        # Injecter pylmgc90 dans sys.modules pour les imports
        import importlib
        sys.modules['pylmgc90']     = mock_pylmgc90
        sys.modules['pylmgc90.pre'] = pre

        try:
            exec(compile(script_src, str(self.script_path), 'exec'), glob)
        except Exception as exc:
            tb = traceback.format_exc()
            self._warnings.append(f"⚠ Exécution partielle du script : {exc}\n{tb}")
        finally:
            sys.modules.pop('pylmgc90', None)
            sys.modules.pop('pylmgc90.pre', None)

        # Récupérer les avatars dans bodies depuis glob (au cas où le script
        # aurait réassigné bodies après import)
        if isinstance(glob.get('bodies'), _TrackedContainer):
            self._bodies = glob['bodies']._items
        elif isinstance(glob.get('bodies'), _Container):
            self._bodies = [x for x in glob['bodies']._items
                            if isinstance(x, _AvatarObj)]

        # Lois / tables depuis les conteneurs
        for t in tacts_container._items:
            if isinstance(t, _TactBehavObj):
                self._tact_behavs[t.name] = t
        for s in sees_container._items:
            if isinstance(s, _SeeTableObj):
                self._see_tables.append(s)
        for p in posts_container._items:
            if isinstance(p, _PostproCommandObj):
                self._postpro_cmds.append(p)

        # Granulo
        if self._last_deposit and self._last_granulo:
            g = {**self._last_granulo, **self._last_deposit}
            # Trouver le matériau et modèle utilisés pour les particules granulo
            # (heuristique : dernier matériau RIGID et dernier modèle Rxx)
            g['material_name'] = self._guess_granulo_material()
            g['model_name']    = self._guess_granulo_model()
            g['color']         = 'BLUEx'
            g['avatar_type']   = 'rigidSphere' if self._dimension == 3 else 'rigidDisk'
            g['seed']          = self._last_granulo.get('seed')
            g['group_name']    = f"granulo_{g['container_type'].lower()}"
            self._granulo_gens.append(g)

    def _guess_granulo_material(self) -> str:
        for name, m in reversed(list(self._materials.items())):
            if m.material_type == 'RIGID':
                return name
        return list(self._materials.keys())[-1] if self._materials else 'TDURx'

    def _guess_granulo_model(self) -> str:
        for name, m in reversed(list(self._models.items())):
            if 'Rxx' in m.element:
                return name
        return list(self._models.keys())[-1] if self._models else 'rigid'

    # ── Construction du JSON projet ───────────────────────────────────────────

    def to_lmgc90_dict(self) -> dict:
        """Construit le dictionnaire du projet au format .lmgc90."""

        # Index des avatars dans bodies (pour les DOF)
        avatar_index = {id(av): i for i, av in enumerate(self._bodies)}

        # ── Matériaux ─────────────────────────────────────────────────────────
        materials = []
        for name, m in self._materials.items():
            d = {'name': name, 'type': m.material_type,
                 'density': m.density, 'props': m.props}
            materials.append(d)

        # ── Modèles ───────────────────────────────────────────────────────────
        models = []
        for name, m in self._models.items():
            d = {'name': name, 'physics': m.physics,
                 'element': m.element, 'dimension': m.dimension}
            d.update(m.opts)
            models.append(d)

        # ── Avatars ───────────────────────────────────────────────────────────
        avatars = []
        for av in self._bodies:
            av_dict = self._avatar_to_dict(av)
            if av_dict:
                avatars.append(av_dict)

        # ── Lois de contact ───────────────────────────────────────────────────
        contact_laws = []
        for name, t in self._tact_behavs.items():
            d = {'name': name, 'law': t.law}
            if t.fric is not None:
                d['fric'] = float(t.fric)
            d.update({k: v for k, v in t.props.items()})
            contact_laws.append(d)

        # ── Tables de visibilité ──────────────────────────────────────────────
        visibility_rules = []
        for s in self._see_tables:
            visibility_rules.append({
                'CorpsCandidat':    s.candidate_body,
                'candidat':        s.candidate_contactor,
                'colorCandidat':   s.candidate_color,
                'CorpsAntagoniste': s.antagonist_body,
                'antagoniste':     s.antagonist_contactor,
                'colorAntagoniste': s.antagonist_color,
                'behav':           s.behav_name,
                'alert':           s.alert
            })

        # ── Opérations DOF ────────────────────────────────────────────────────
        operations = []
        for av in self._bodies:
            idx = avatar_index.get(id(av))
            if idx is None:
                continue
            for dof in av._dof_ops:
                op = dof['op']
                params = copy.deepcopy(dof['params'])
                # translate : retirer dz si 0 et 2D
                if op == 'translate' and self._dimension == 2:
                    params.pop('dz', None)
                operations.append({
                    'type':         op,
                    'target':       'avatar',
                    'target_value': idx,
                    'params':       params
                })

        # ── Postpro ───────────────────────────────────────────────────────────
        postpro_creations = []
        for p in self._postpro_cmds:
            d = {'name': p.name, 'step': p.step}
            if p.rigid_set:
                # Trouver les indices des corps dans rigid_set
                indices = []
                for body in p.rigid_set:
                    if isinstance(body, _AvatarObj):
                        idx = avatar_index.get(id(body))
                        if idx is not None:
                            indices.append(idx)
                if len(indices) == 1:
                    d['target_info'] = {'type': 'avatar', 'value': indices[0]}
                elif indices:
                    # Stocker comme liste (approximation)
                    d['target_info'] = {'type': 'avatar', 'value': indices[0]}
            postpro_creations.append(d)

        # ── Granulométrie ─────────────────────────────────────────────────────
        granulo_generations = []
        for g in self._granulo_gens:
            granulo_generations.append({
                'nb':    g['nb_particles'],
                'rmin':  g['rmin'],
                'rmax':  g['rmax'],
                'container_params': {
                    'type': g['container_type'],
                    **g['container_params']
                },
                'model':       g['model_name'],
                'material':    g['material_name'],
                'avatar_type': g['avatar_type'],
                'color':       g.get('color', 'BLUEx'),
                'seed':        g.get('seed'),
                'stored_in_group': g.get('group_name'),
                'avatar_indices': []
            })

        return {
            'project_name': self.project_name,
            'dimension':    self._dimension,
            'units':        'SI',
            'preferences':  _default_preferences(),
            'materials':    materials,
            'models':       models,
            'avatars':      avatars,
            'custom_templates': {},
            'contact_laws': contact_laws,
            'visibility_rules': visibility_rules,
            'operations':   operations,
            'loops':        [],
            'granulo_generations': granulo_generations,
            'postpro_creations': postpro_creations,
            'avatar_groups': {},
            'dynamic_vars': {},
            'masonry_patterns': {},
        }

    # ── Conversion d'un avatar en dict .lmgc90 ───────────────────────────────

    def _avatar_to_dict(self, av: _AvatarObj) -> Optional[dict]:
        kw = av._kwargs
        t  = av._type

        # Champs obligatoires
        center   = kw.get('center', [0., 0.])
        material = kw.get('material') or ''
        model    = kw.get('model') or ''
        color    = kw.get('color', 'BLUEx')

        # Valider que material et model existent (sinon avertissement)
        if material and material not in self._materials:
            self._warnings.append(
                f"Avatar {t}: matériau '{material}' non trouvé dans pre.material()."
            )
        if model and model not in self._models:
            self._warnings.append(
                f"Avatar {t}: modèle '{model}' non trouvé dans pre.model()."
            )

        d = {
            'type':     t,
            'center':   _to_serial(center),
            'material': material,
            'model':    model,
            'color':    color,
            '__origin': 'manual',
        }

        # Champs spécifiques par type
        if t == 'rigidDisk':
            d['r'] = float(kw.get('r', 0.1))
            if kw.get('is_Hollow') or kw.get('is_hollow'):
                d['is_Hollow'] = True

        elif t == 'rigidJonc':
            d['axe1'] = float(kw.get('axe1', 1.))
            d['axe2'] = float(kw.get('axe2', 0.1))
            if 'axe3' in kw:
                d['axe3'] = float(kw['axe3'])

        elif t == 'rigidPolygon':
            # radius → clé 'radius' pour les polygones (selon to_dict)
            if 'radius' in kw:
                d['radius'] = float(kw['radius'])
            gen = kw.get('generation_type', 'regular')
            if gen:
                d['gen_type'] = gen
            if kw.get('nb_vertices') is not None:
                d['nb_vertices'] = int(kw['nb_vertices'])
            if kw.get('vertices') is not None:
                d['vertices'] = _to_serial(kw['vertices'])
            # theta : pré-appliquer si vertices fournis et theta != 0
            theta = kw.get('theta', 0.)
            if theta and kw.get('vertices') is not None:
                d['vertices'] = _rotate_vertices_2d(d['vertices'], float(theta))
            elif theta and kw.get('vertices') is None:
                # Pas de vertices explicites — stocker theta comme info
                # (sera ignoré au rechargement car pas dans wall_keys)
                pass

        elif t == 'rigidOvoidPolygon':
            d['ra']          = float(kw.get('ra', 1.))
            d['rb']          = float(kw.get('rb', 1.))
            d['nb_vertices'] = int(kw.get('nb_vertices', 8))

        elif t == 'rigidDiscreteDisk':
            d['r'] = float(kw.get('r', 0.1))

        elif t == 'rigidCluster':
            d['nb_vertices'] = int(kw.get('nb_disk', kw.get('nb_vertices', 3)))
            d['r']           = float(kw.get('r', 0.1))

        elif t in ('roughWall', 'fineWall', 'smoothWall', 'granuloRoughWall'):
            d['lx'] = float(kw.get('lx', 1.))
            d['ly'] = float(kw.get('ly', 0.1))

        elif t == 'rigidSphere':
            d['r'] = float(kw.get('r', 0.1))

        elif t == 'rigidCylinder':
            d['r']  = float(kw.get('r', 0.5))
            d['lz'] = float(kw.get('h', 1.))

        elif t == 'rigidPolyhedron':
            if kw.get('vertices') is not None:
                d['vertices'] = _to_serial(kw['vertices'])
            if kw.get('faces') is not None:
                d['faces'] = _to_serial(kw['faces'])

        return d


# ── Conteneur qui intercept les ajouts à bodies ──────────────────────────────

class _TrackedContainer(_Container):
    def __init__(self, converter: Converter):
        super().__init__('bodies')
        self._cv = converter

    def addAvatar(self, item):
        if isinstance(item, _AvatarObj):
            self._items.append(item)
        elif hasattr(item, 'nodes'):   # _FakeMesh ou autre
            pass

    def __iadd__(self, item):
        self.addAvatar(item)
        return self


# ── Module silencieux pour matplotlib ────────────────────────────────────────

class _SilentModule:
    def __init__(self, name): self._name = name
    def __getattr__(self, k): return _SilentModule(f"{self._name}.{k}")
    def __call__(self, *a, **kw): return _SilentModule(f"{self._name}()")
    def __iadd__(self, o): return self
    def show(self, *a, **kw): pass
    def savefig(self, *a, **kw): pass


# ============================================================================
# Utilitaires
# ============================================================================

def _center(c, dim=None):
    """Normalise un centre en liste Python."""
    if c is None:
        return [0., 0.] if (dim or 2) == 2 else [0., 0., 0.]
    if hasattr(c, 'tolist'):
        return c.tolist()
    return list(float(x) for x in c)


def _name(obj) -> str:
    """Extrait le nom d'un objet Material ou Model, ou retourne la chaîne."""
    if obj is None:
        return ''
    if isinstance(obj, (_MaterialObj, _ModelObj)):
        return obj.name
    return str(obj)


def _to_serial(obj):
    """Rend un objet JSON-sérialisable."""
    if obj is None:
        return None
    if hasattr(obj, 'tolist'):
        return obj.tolist()
    if isinstance(obj, (list, tuple)):
        return [_to_serial(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_serial(v) for k, v in obj.items()}
    if isinstance(obj, (int, float, str, bool)):
        return obj
    return str(obj)


def _normalize_kwargs(kw: dict) -> dict:
    """Convertit les numpy arrays en listes dans les kwargs."""
    return {k: _to_serial(v) for k, v in kw.items()}


def _rotate_vertices_2d(vertices, theta_deg: float):
    """Applique une rotation 2D (degrés) aux vertices."""
    import math
    th = math.radians(theta_deg)
    cos_t, sin_t = math.cos(th), math.sin(th)
    result = []
    for v in vertices:
        x, y = float(v[0]), float(v[1])
        result.append([cos_t * x - sin_t * y, sin_t * x + cos_t * y])
    return result


def _default_preferences() -> dict:
    return {
        'default_project_path': None,
        'unit_system': 'SI',
        'auto_save': True,
        'auto_save_interval': 300,
        'backup_enabled': True,
        'recent_projects': [],
        'max_recent_projects': 10,
        'show_granulo_individually': True,
        'create_pylmgc_on_generate': True,
        'script_use_loop': True,
    }


# ============================================================================
# Interface en ligne de commande
# ============================================================================

def convert(script_path: Path, output_path: Path, verbose: bool = True) -> bool:
    """
    Convertit un script Python en fichier .lmgc90.
    Retourne True si la conversion a réussi (avec ou sans avertissements).
    """
    if not script_path.exists():
        print(f"❌ Fichier introuvable : {script_path}", file=sys.stderr)
        return False

    if verbose:
        print(f"🔄 Conversion de : {script_path}")
        print(f"   Destination   : {output_path}")

    cv = Converter(script_path)
    cv.run()

    project = cv.to_lmgc90_dict()

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(project, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f"\n📋 Résumé :")
        print(f"   Dimension    : {project['dimension']}D")
        print(f"   Matériaux    : {len(project['materials'])}")
        print(f"   Modèles      : {len(project['models'])}")
        print(f"   Avatars      : {len(project['avatars'])}")
        print(f"   Lois contact : {len(project['contact_laws'])}")
        print(f"   Visibilités  : {len(project['visibility_rules'])}")
        print(f"   Opérations   : {len(project['operations'])}")
        print(f"   Granulo      : {len(project['granulo_generations'])}")
        print(f"   PostPro      : {len(project['postpro_creations'])}")

        for av in project['avatars']:
            print(f"     • {av['type']:22s} center={av['center']}")

        if cv._warnings:
            print(f"\n⚠️  Avertissements ({len(cv._warnings)}) :")
            for w in cv._warnings:
                first_line = w.split('\n')[0]
                print(f"   • {first_line}")

        print(f"\n✅ Fichier écrit : {output_path}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Convertit un script pylmgc90 en projet .lmgc90 pour LMGC90_GUI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('script', type=Path,
                        help='Fichier Python source (.py)')
    parser.add_argument('-o', '--output', type=Path, default=None,
                        help='Fichier de sortie (.lmgc90). Défaut : même nom que script.')
    parser.add_argument('--check', action='store_true',
                        help="Vérifie la conversion sans écrire le fichier.")
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Sortie minimale.')

    args = parser.parse_args()

    script  = args.script.resolve()
    output  = args.output or script.with_suffix('.lmgc90')

    if args.check:
        cv = Converter(script)
        cv.run()
        project = cv.to_lmgc90_dict()
        print(json.dumps(project, indent=2, ensure_ascii=False))
        return

    ok = convert(script, output, verbose=not args.quiet)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()