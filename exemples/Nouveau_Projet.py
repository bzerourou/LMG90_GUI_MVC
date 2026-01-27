"""
Script généré automatiquement par LMGC90_GUI
Projet: Nouveau_Projet
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
body = pre.rigidJonc(
    center=[0.0, 0.0],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='VERTx',
    r=None,
    axe1=2.0,
    axe2=0.05
)
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.rigidDisk(
    center=[0.0, 0.5],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    r=0.1
)
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.rigidDisk(
    center=[-2.5, 0.5],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    r=1.0,
    is_Hollow=True
)
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.rigidPolygon(
    center=[1.0, 1.0],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    r=1.0,
    generation_type='regular',
    nb_vertices=8
)
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.rigidPolygon(
    center=[-4.0, 4.0],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    r=1.0,
    generation_type='full',
    vertices=np.array([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]])
)
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.rigidOvoidPolygon(
    center=[-2.0, -2.0],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    ra=1.0,
    rb=0.5,
    r=None,
    nb_vertices=16
)
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.rigidDiscreteDisk(
    center=[-2.0, 2.0],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    r=0.5
)
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.roughWall(
    center=[1.0, -3.0],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    l=2.0,
    r=0.1,
    nb_vertex=0
)
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.fineWall(
    center=[0.0, -1.2],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    l=2.0,
    r=0.15,
    nb_vertex=0
)
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.smoothWall(
    center=[0.0, 5.0],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    l=2.0,
    h=0.15,
    nb_polyg=12,
    r=None
)
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.granuloRoughWall(
    center=[0.0, 3.5],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    l=2.0,
    rmin=0.1,
    rmax=0.2,
    nb_vertex=12,
    r=None
)
bodies.addAvatar(body)
bodies_list.append(body)

# Avatar vide avec contacteurs personnalisés
body = pre.avatar(dimension=2)
body.addBulk(pre.rigid2d())
body.addNode(pre.node(coor=np.array([4.0, 1.0]), number=1))
body.defineGroups()
body.defineModel(model=mods['rigid'])
body.defineMaterial(material=mats['TDURx'])
body.addContactors(shape='DISKx', color='BLUEx', byrd=0.3)
body.computeRigidProperties()
bodies.addAvatar(body)
bodies_list.append(body)

# Avatar vide avec contacteurs personnalisés
body = pre.avatar(dimension=2)
body.addBulk(pre.rigid2d())
body.addNode(pre.node(coor=np.array([4.0, 1.0]), number=1))
body.defineGroups()
body.defineModel(model=mods['rigid'])
body.defineMaterial(material=mats['TDURx'])
body.addContactors(shape='DISKx', color='BLUEx', byrd=0.3)
body.addContactors(shape='DISKx', color='BLUEx', byrd=0.15, shift=[-1, 1])
body.addContactors(shape='PT2Dx', color='BLUEx', shift=[0.5, 0.5])
body.computeRigidProperties()
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.rigidDisk(
    center=[-6.0, 0.0],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    r=0.05
)
bodies.addAvatar(body)
bodies_list.append(body)

body = pre.rigidJonc(
    center=[0.0, -7.0],
    model=mods['rigid'],
    material=mats['TDURx'],
    color='BLUEx',
    r=None,
    axe1=2,
    axe2=0.1
)
bodies.addAvatar(body)
bodies_list.append(body)


# Boucles
# Boucle 1: Cercle
for angle_idx in range(6):
    angle = 2 * math.pi * angle_idx / 6
    x = 4.0 + 0.0 + 1.0 * math.cos(angle)
    y = 1.0 + 0.0 + 1.0 * math.sin(angle)
    center = [x, y]
    av = pre.emptyAvatar(
        center=center,
        material=mat_TDURx,
        model=mod_rigid,
        color='BLUEx'
    )
    bodies.addAvatar(av)

# Boucle 2: Ligne
for idx in range(3):
    x = 0.0 + 0.0
    y = -7.0 + -3.0 + idx * 1.0
    center = [x, y]
    av = pre.rigidJonc(
        center=center,
        material=mat_TDURx,
        model=mod_rigid,
        color='BLUEx'
    )
    bodies.addAvatar(av)

# Génération granulométrique
# Dépôt granulo 1
nb_particles_0, coords_0, radii_0 = pre.Disk2D(
    nb=50,
    rmin=0.125,
    rmax=0.15,
    r=2.0
)

for j in range(nb_particles_0):
    av = pre.rigidDisk(
        center=coords_0[j].tolist(),
        material=mat_TDURx,
        model=mod_rigid,
        color='SPARx',
        r=float(radii_0[j])
    )
    bodies.addAvatar(av)

# Lois de contact
law_law01 = pre.tact_behav(
    name='law01',
    law='IQS_CLB',
    fric=0.3
)
tacts.addBehav(law_law01)

law_law02 = pre.tact_behav(
    name='law02',
    law='IQS_CLB_g0',
    fric=0.3
)
tacts.addBehav(law_law02)

law_law03 = pre.tact_behav(
    name='law03',
    law='COUPLED_DOF'
)
tacts.addBehav(law_law03)

law_law04 = pre.tact_behav(
    name='law04',
    law='IQS_DS_CLB',
    fric=0.3,
    stfr=100000000.0,
    dyfr=100000000.0
)
tacts.addBehav(law_law04)

law_law06 = pre.tact_behav(
    name='law06',
    law='ELASTIC_WIRE',
    stiffness=1000000.0,
    prestrain=0.2
)
tacts.addBehav(law_law06)

# Tables de visibilité
see_0 = pre.see_table(
    CorpsCandidat='RBDY2',
    candidat='DISKx',
    colorCandidat='BLUEx',
    CorpsAntagoniste='RBDY2',
    antagoniste='DISKx',
    colorAntagoniste='VERTx',
    behav=law_law01,
    alert=0.05
)
sees.addSeeTable(see_0)

see_1 = pre.see_table(
    CorpsCandidat='RBDY2',
    candidat='PT2Dx',
    colorCandidat='BLUEx',
    CorpsAntagoniste='RBDY2',
    antagoniste='PT2Dx',
    colorAntagoniste='VERTx',
    behav=law_law03,
    alert=0.1
)
sees.addSeeTable(see_1)

# Opérations DOF
# DOF sur groupe 'depot_granulo'
# for av in group_depot_granulo:
#     av.translate(dx=0.0, dy=-8.0)

# DOF sur groupe 'depot_granulo'
# for av in group_depot_granulo:
#     av.rotate(psi=-2.0943951023931953, center=[0, 0])

# Post-traitement
# Commande avec cible: avatar = 0
# rigid_set = [...]  # À définir selon la cible
# post_cmd_0 = pre.postpro_command(
#     name='NEW RIGID SETS',
#     step=10,
#     rigid_set=rigid_set
# )

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
