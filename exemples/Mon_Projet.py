"""
Script généré automatiquement par LMGC90_GUI
Projet: Mon_Projet
Dimension: 2D
"""

from pylmgc90 import pre
import numpy as np
import math

# Conteneurs
mats = pre.materials()
mods = pre.models()
bodies = pre.avatars()
tacts = pre.tact_behavs()
sees = pre.see_tables()
post = pre.postpro_commands()

bodies_list = []

# Matériaux
mat_TDURx = pre.material(
    name='TDURx',
    materialType='RIGID',
    density=2800.0
)
mats.addMaterial(mat_TDURx)

# Modèles
mod_rigid = pre.model(
    name='rigid',
    physics='MECAx',
    element='Rxx2D',
    dimension=2
)
mods.addModel(mod_rigid)

# Avatars manuels
body = pre.rigidDisk(
    center=[0.0, 0.0],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    r=0.1
)
bodies.addAvatar(body)
bodies_list.append(body)


# Boucles
# Boucle 1: Cercle
for angle_idx in range(10):
    angle = 2 * math.pi * angle_idx / 10
    x = 0.0 + 0.0 + 2.0 * math.cos(angle)
    y = 0.0 + 0.0 + 2.0 * math.sin(angle)
    center = [x, y]
    av = pre.rigidDisk(
        center=center,
        material=mat_TDURx,
        model=mod_rigid,
        color='BLUEx',
        r=0.1
    )
    bodies.addAvatar(av)

# Opérations DOF
# DOF sur groupe 'circle_10disks'
# for av in group_circle_10disks:
#     av.translate(dx=0.0, dy=2.0)

# Génération DATBOX
pre.writeDatbox(
    dim=2,
    mats=mats,
    mods=mods,
    bodies=bodies,
    tacts=tacts,
    sees=sees,
    post=post,
    datbox_path='DATBOX'
)

print('DATBOX généré avec succès!')
