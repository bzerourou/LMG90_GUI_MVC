# Granulométrie et Dépôt

Cette section sert à la génération de dépôts granulaires.

## Paramètres
- Nombre de particules à générer
- Distribution aléatoire des rayons entre `rmin` et `rmax`
- [x]Seed (reproductibilité)
- Type de conteneur : Box2D, Disk2D, Couette2D, Drum2D
- Avatar modèle (sélectionné parmi les avatars manuels)
- Couleur des particules
- [x]Option : créer murs autour (Box2D) (non impl)
- Option : stocker dans groupe nommé

## Fonctionnement
1. Utilise la fonction `granulo_Random` pour la ditribution
2. Utilise les fonctions `depositInBox2D`, `depositInDisk2D`, `depositInCouette2D` et `depositInDrum2D`


## Exemple
Cet exemple n'est pas concret mais montre seulement les proprétés de vos granulométries
| Champ | Description | Exemple |
|-------|-------------|---------|
| **Nombre de particules** | Nombre total de particules à générer | `200` |
| **Rayon Min (rmin)** | Rayon minimum des particules | `0.05` |
| **Rayon Max (rmax)** | Rayon maximum des particules | `0.15` |


| Conteneur | Paramètres | Description |
|-----------|------------|-------------|
| dans mon cas **Box2D** | `lx`, `ly` | Boîte rectangulaire |    
| **Disk2D** | `r` | Disque circulaire |
| **Couette2D** | `rint`, `rext` | Anneau (cellule de Couette) |
| **Drum2D** | `r` | Tambour rotatif |

#### 3. Propriétés Physiques

| Champ | Description |
|-------|-------------|
| **Matériau** | Matériau à appliquer aux particules |
| **Modèle** | Modèle physique (généralement `Rxx2D`) |
| **Couleur** | Couleur des particules (`BLUEx`, `REDxx`, etc.) |
| **Type d'avatar** | Avatar modèle pour la forme des particules (rigidDisk)  |

IL ne vous reste de cliquer sur le bouton 'Générer de dépôt'

![](captures/depot_granulo_disk_jonc.JPG)

Le rendu de mon modèle, 

![](captures/rendu_depot_granulo_disk_jonc.JPG)

## Assistant de granulométrie 
Vous pouvez aussi utiliser l'assistant de granulométrie afin de générer facilement vos dépôts, cet assistant fait appel aux routines de LMGC90, cela pourra ralentir considérablement votre interface, il n'est pas idéal pour une génération de plus de 2000 avatars (particules).
Pour cela il vous suffit de cliquer sur le menu "Fichier" puis "Assistant de granulométrie " ou avec le raccourci clavier "ctr+ shift+ G". L'assistant s'ouvrira, cliquez sur le bouton "suivant"

![](captures/assistant_granulo_page1.JPG)

Choisissez la dimension de votre modèle numérique, dans mon cas je vais dire en 3D, puis cliqez sur "suivant"

![](captures/assistant_granulo_page2.JPG)

L'assistant vous propesera de créer un matériau simple de type rigide, j'opte pour les valeurs par défauts, ensuite sur "suivant"

![](captures/assistant_granulo_page3.JPG)

L'assistant vous propesera de créer un modèle rigide de type "Rxx2D"/"Rxx3D" pour la 2D/3D, je laisse tout par défaut, et cliquez sur "suivant", 
![](captures/assistant_granulo_page4.JPG)

On arrive maintenant au dialogue de génération, pour mon cas je vais générer 500 avatars, le rayon minimal et maximal respectivement à 0.05 et 0.06, puis cliquez sur "suivant", 

![](captures/assistant_granulo_page5.JPG)

Le type de dépôt est sur une Boxe3D, puis "suivant",

![](captures/assistant_granulo_page6.JPG)

Enfin on est arrivé au récapitulatif, on termine par cliquer sur le bouton "générer"

![](captures/assistant_granulo_page7.JPG)

## Génaration avec numpy
Il est possible d'utiliser un générateur d'avatars avec numpy, adapter pour les très grande génération, plus de 5000 avatars, pour cela cliquez sur le menu "fichier" -> "Génerateur granulométrie numpy...(bétâ)", 
![](captures/assistant_granulo_numpy.JPG)