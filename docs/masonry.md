# Assistant Maçonnerie – Génération de structures en briques

L’assistant maçonnerie permet de créer rapidement des murs, panneaux ou structures maçonnées en briques rigides avec **LMGC90_GUI**.

Il génère automatiquement :
- les briques (rigidBrick2D ou rigidBrick3D)
- les groupes d’avatars pour un pilotage facile

L’assistant s’appuie sur les fonctions historiques de `pylmgc90.pre` (`brick2D`, `brick3D`, `paneresse_simple`,  `paneresse_simple`, etc.).

## Accès à l’assistant

Menu :  
**Fichier → Assistant maçonnerie**  
ou raccourci : **Ctrl + Shift + M**

## Étapes de l’assistant (pages du wizard)

### 1. Introduction
Première page de l'assistant est une brève présentation, cliquez sur le bouton "Suivant", 

![](captures/assistant_maçon_page1.JPG)

### 2. Dimensions de la brique de référence
La deuxième page est pour le choix de la dimension de votre modèle, je choisis la dimension 2D, puis sur le bouton "Suivant", 

![](captures/assistant_maçon_page2.JPG)
       |

### 3. Matériau, modèle 
La troisième page est consacrée aux : 

- **1.matériau**  : soit existant ou une nouvelle création (nom : TDURx, BRIQx, etc.)

![](captures/assistant_maçon_page3.JPG)

- **2.modèle** le modèle doit être rigide (Rxx2D / Rxx3D)

![](captures/assistant_maçon_page4.JPG)

### 4. Type de pose / disposition
Cette quatrième page est consacrée à la création de votre exemple de brique (nom, longueur et largeur )

| Paramètre              | Symbole | Valeur par défaut | Unité | Remarques                                      |
|------------------------|---------|-------------------|-------|------------------------------------------------|
| Longueur (paneresse)   | lx      | 0.20              | m     | Dimension selon l’axe principal                |
| Largeur / profondeur   | ly      | 0.10              | m     | Épaisseur de la brique                         |
| Hauteur (3D seulement) | lz      | 0.05              | m     | Seulement en 3D                                |
| Épaisseur joint        | ej      | 0.010             | m     | Espace entre briques (0 = pas de joint) 

![](captures/assistant_maçon_page5.JPG)

On arrive maintenant aux types de génération de votre mur, comme on le voit sur le type d'appareil, il existe plusieurs types de générations  : 
                       | 2D + 3D       |

### 2D/3D

| Disposition         | Description                               | Utilisation typique                     | Support 2D/3D |
|---------------------|-------------------------------------------|-----------------------------------------|---------------|
| Paneresse simple    | Briques posées à plat, alignées           | Murs simples, cloisons                  | 3D       |
| Boutisse            | Briques posées sur la tranche             | Renforts, murs porteurs                 | 2D + 3D       |
| Paneresse + boutisse| Alternance tous les rangs                 | Murs traditionnels en pierre/brique     | 2D + 3D       |
| Double paneresse    | Deux rangées parallèles + boutisses       | Murs épais (> 30 cm)                    | 3D     |
| Chant               | Briques debout sur la hauteur             | Bordures, appuis                        | 2D + 3D       |

![](captures/assistant_maçon_page6.JPG)

### Géomtérie
Ici vous introduisez la géométrie de votre mur,  

| Paramètre               | Symbole | Valeur par défaut | Remarques                                      |
|-------------------------|---------|-------------------|------------------------------------------------|
| Longueur totale         | L       | 4.00              | Longueur du mur (axe x)                        |
| Hauteur totale          | H       | 2.50              | Hauteur du mur                                 |
| Nombre de rangs         | nr      | auto              | Calculé automatiquement ou forcé               |
| Mode dimensionnement    | -       | Nombre de briques | Ou longueur/hauteur fixées                     |
| Sans demi-briques       | -       | décoché           | Évite les découpes (plus esthétique)           |
| Décalage rang suivant   | offset  | 0.5 × lx          | Décalage horizontal des rangs (en % de lx)     |




### 6. DOF
La page DOF vous permet de fixer des conditions aux limites pour vos éléments de maçonnerie, 
- translation
- rotation
- imposeDrivenDof
- imposeInitValue

![](captures/assistant_maçon_page7.JPG)


**Imortant**

L’assistant n'inclus pas encore l'ajout de lois de contact  :
- Afin d'en rajouter une loi il vous faut passer par l'onglet `DOF`



