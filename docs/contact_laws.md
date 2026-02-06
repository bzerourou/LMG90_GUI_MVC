# Lois de Contact

Définition des interactions entre vos avatars.

## Lois disponibles
Liste de types d'interactions qui sont implémentées : 

## Interactions (rigid/rigid)
### Frottement sec classique
- IQS_CLB : Loi de Coulomb (Inequal Quasi-Static)

Paramètre : `fric` (coefficient de frottement constant)

**Paramètres typiques** :
- `fric = 0.3-0.5` : Matériaux granulaires (sable, billes de verre)
- `fric = 0.5-0.8` : Matériaux rugueux (béton, roches)
- `fric = 0.1-0.3` : Surfaces lisses (métaux polis)

- IQS_CLB_g0 : Prise en compte d'un jeu initial entre particules, simulations avec pré-positionnement.

Paramètre : `fric`

**Applications** :
- Assemblages mécaniques avec jeu
- Simulation de compression progressive
- Contacts avec rugosité initiale

- IQS_DS_CLB : Loi de Coulomb avec frottement dynamique/statique

Paramètres : `dyfr` (frottement dynamique, glissement), `stfr` (frottement statique, adhérence)

**Cas pratiques** :

- Systèmes de freinage (μ_statique > μ_dynamique)
- Glissement de plaques tectoniques
- Mécanismes avec vibrations auto-induites

- COUPLED_DOF (liaison parfaite)

### Lois cohésives               
   
- IQS_MOHR_DS_CLB : Loi de Mohr-Coulomb, matériaux avec forces d'adhésion (sols humides, matériaux cimentés).

Paramètres : `cohn`, `coht`, `dyfr`, `stfr `  

**Applications** :
- Géomécanique : argiles, sols cohésifs
- Matériaux granulaires humides
- Poudres avec forces de van der Waals

### Modèles de zones cohésives (CZM)
- IQS_MAC_CZM : Modèle cohésif de Mohr-Coulomb-Allix-Corigliano, rupture progressive, délaminage, fissuration.

Paramètres : `dyfr`, `stfr`, `cn`, `ct`, `b`, `w`         
                cn : Rigidité normale (N/m³)
                ct : Rigidité tangentielle
                b  : Paramètre d'endommagement
                w  : Ouverture critique (m)  

### Câbles élastiques
- ELASTIC_WIRE : Câble élastique simple, en traction seulement.
Paramètres : `stiffness`, `prestrain`  

                stiffness : Rigidité EA (N)
                prestrain : Précontrainte 1%

- ELASTIC_REPELL_CLB : Barre élastique, contacts mous, pénalisation douce.

Paramètres : `stiffness`, `fric`  

### Interactions Universelles (any/any)
#### Couplages cinématiques
- COUPLED_DOF : Couplage parfait (saut de vitesse nul)
Aucun paramètre

#### Lois de répulsion élastique
- ELASTIC_REPELL_CLB : Répulsion élastique de type Coulomb
Paramètres : `stiffness`, `fric`


## Exemple 
On va créer une loi de Coulomb avec un frottement de 0.3, pour cela il faut se rendre dans l'onglet "Contact", il faut ensuite choisir une parmi les lois disponible dans mon cas "IQS_CLB" et de renseigner la valeur de 0.3 pour le frottement, on termine par cliquer sur le bouton "Créer Loi"

![](captures/contact_law.JPG)



