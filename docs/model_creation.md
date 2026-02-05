# Création d'un Modèle

Le modèle définit le type de physique de vos futurs modèles qui seront supportés par **LMGC90** 

## Interface
L'onglet **Modèle** vous permmetra de définir vos types de problème et modèles, cette interface comprend ces champs : 
  - Nom : qui est une suite maximum de cinq caractères
  - Physique : (seulement 'MECAx' qui est implémenté)
  - Élément : (type de formulation)
  - Dimension : (seulement en 2D)
  - Options : (kinematic, formulation, etc.) qui dépend de l'élément choisit


Les physiques en LMGC90 sont quatre : 

| Code | Nom complet | Physique |
|------|------------|----------|
| **MECAx** | Mécanique | Déformation, contrainte, dynamique |
| **THERx** | Thermique | Transfert de chaleur |
| **POROx** | Poromécanique | Milieux poreux saturés (Biot) |
| **MULTI** | Multiphasique | Écoulements multiphasiques |

_Remarque_ : "MECAx" mécanique est le seul implémenté dans LMGC90_GUI. Il traite les problèmes de déformation, contrainte et dynamique.

## Éléments disponibles
**LMGC90_GUI** supporte quelques éléments de base depuis la version v0.2.0
Le tableau suivant résume partiellement les éléments supportés dans LMGC90 :
### Classification par usage
| Usage | Dimension | Éléments recommandés | Ordre | Remarques |
|-------|-----------|---------------------|-------|-----------|
| **DEM 2D** | 0D | Rxx2D | - | Corps rigides plans |
| **DEM 3D** | 0D | Rxx3D | - | Corps rigides 3D |
| **Ressorts 2D** | 1D | SPRG2 | 1 | Éléments discrets |
| **Ressorts 3D** | 1D | SPRG3 | 1 | Éléments discrets |
| **Barres treillis** | 1D | BARxx | 1 | Traction/compression |
| **Conduction 1D** | 1D | S2xth | 1 | Thermique |
| **Structures 2D standard** | 2D | Q4xxx, Q8xxx | 1-2 | Quadrangles |
| **Structures 2D complexes** | 2D | T6xxx | 2 | Triangles auto |
| **Plaques minces** | 2D | DKTxx | 1 | Kirchhoff |
| **Pièces 3D simples** | 3D | H8xxx, H20xx | 1-2 | Maillage structuré |
| **Pièces 3D complexes** | 3D | TE10x | 2 | Maillage auto |
| **Géomécanique** | 3D | TE10x, H8xxx | 1-2 | Sol, roches |
| **Poromécanique 2D** | 2D | T33xx, Q44xx | 1 | Biot 2D |
| **Poromécanique 3D** | 3D | TE44x, H88xx, TE104 | 1-2 | Biot 3D |
| **Multiphasique** | 2D/3D | T33xx, T63xx, Q44xx, H8xxx, TE44x | 1-2 | Écoulements |

### Classification par dimension
| Dimension | Type géométrique | Code élément | Nœuds | Ordre | Nom complet | DDL MECAx | DDL THERx | DDL POROx | DDL MULTI |
|-----------|------------------|--------------|-------|-------|-------------|-----------|-----------|-----------|-----------|
| **0D** | **Point** | | | | | | | | |
| 0D | Point | **Rxx2D** | 1 | - | Corps rigide 2D | 3 | 1 | - | - |
| 0D | Point | **Rxx3D** | 1 | - | Corps rigide 3D | 6 | 1 | - | - |
| **1D** | **Segment** | | | | | | | | |
| 1D | S2xxx | **SPRG2** | 2 | 1 | Ressort 2D | 2 | 1 | - | - |
| 1D | S2xxx | **SPRG3** | 2 | 1 | Ressort 3D | 3 | 1 | - | - |
| 1D | S2xxx | **S2xth** | 2 | 1 | Segment thermique | - | 1 | - | - |
| 1D | S2xxx | **BARxx** | 2 | 1 | Barre 3D | 3 | - | - | - |
| 1D | S2xxx | **Beam** | 2-3 | 1-2 | Poutre (futur) | - | - | - | - |
| 1D | S2xxx | **Cable** | 2-3 | 1-2 | Câble (futur) | - | - | - | - |
| 1D | S3xxx | *(vide)* | 3 | 2 | Réservé | - | - | - | - |
| **2D** | **Triangle** | | | | | | | | |
| 2D | T3xxx | **T3xxx** | 3 | 1 | Triangle linéaire | 2 | 1 | - | - |
| 2D | T3xxx | **T3Lxx** | 3 | 1 | Triangle linéaire spécial | 2 | - | - | - |
| 2D | T3xxx | **DKTxx** | 3 | 1 | Triangle plaque DKT | 4 | 1 | - | - |
| 2D | T3xxx | **T33xx** | 3 | 1 | Triangle poromécanique | - | - | 3 | 4 |
| 2D | T6xxx | **T6xxx** | 6 | 2 | Triangle quadratique | 2 | 1 | - | - |
| 2D | T6xxx | **T63xx** | 6 | 2 | Triangle quadratique poro | - | - | 3 | 4 |
| **2D** | **Quadrangle** | | | | | | | | |
| 2D | Q4xxx | **Q4xxx** | 4 | 1 | Quadrangle bilinéaire | 2 | 1 | - | - |
| 2D | Q4xxx | **Q4P0x** | 4 | 1 | Quadrangle + pression | 2 | 1 | - | - |
| 2D | Q4xxx | **Q44xx** | 4 | 1 | Quadrangle poromécanique | - | - | 3 | 4 |
| 2D | Q8xxx | **Q8xxx** | 8 | 2 | Quadrangle sérendipité | 2 | 1 | - | - |
| 2D | Q8xxx | **Q8Rxx** | 8 | 2 | Quadrangle intégr. réduite | 2 | 1 | - | - |
| 2D | Q8xxx | **Q84xx** | 8 | 2 | Quadrangle sérendipité poro | - | - | 3 | 4 |
| 2D | Q9xxx | **Q9xxx** | 9 | 2 | Quadrangle Lagrange | 2 | - | - | - |
| **3D** | **Tétraèdre** | | | | | | | | |
| 3D | TE4xx | **TE4xx** | 4 | 1 | Tétraèdre linéaire | 3 | 1 | - | - |
| 3D | TE4xx | **TE4Lx** | 4 | 1 | Tétraèdre linéaire spécial | 3 | - | - | - |
| 3D | TE4xx | **TE44x** | 4 | 1 | Tétraèdre poromécanique | - | - | 4 | 5 |
| 3D | TE10x | **TE10x** | 10 | 2 | Tétraèdre quadratique | 3 | 1 | - | - |
| 3D | TE10x | **TE104** | 10 | 2 | Tétraèdre quadratique poro | - | - | 4 | 5 |
| **3D** | **Hexaèdre** | | | | | | | | |
| 3D | H8xxx | **H8xxx** | 8 | 1 | Hexaèdre trilinéaire | 3 | 1 | - | 5 |
| 3D | H8xxx | **H88xx** | 8 | 1 | Hexaèdre poromécanique | - | - | 4 | 4 |
| 3D | H8xxx | **SHB8x** | 8 | 1 | Hexaèdre SHB (futur) | 3 | - | - | - |
| 3D | H20xx | **H20xx** | 20 | 2 | Hexaèdre sérendipité | 3 | 1 | - | - |
| 3D | H20xx | **H20Rx** | 20 | 2 | Hexaèdre intégr. réduite | 3 | 1 | - | - |
| 3D | H20xx | **H208x** | 20 | 2 | Hexaèdre sérendipité poro | - | - | 4 | 5 |
| 3D | H20xx | **SHB20** | 20 | 2 | Hexaèdre SHB 20 (futur) | 3 | - | - | - |
| **3D** | **Prisme** | | | | | | | | |
| 3D | PRI6x | **PRI6x** | 6 | 1 | Prisme linéaire | 3 | 1 | - | - |
| 3D | PRI6x | **SHB6x** | 6 | 1 | Prisme SHB | 3 | - | - | - |
| 3D | PRI15 | **PRI15** | 15 | 2 | Prisme quadratique | 3 | 1 | - | - |
| 3D | PRI15 | **SHB15** | 15 | 2 | Prisme SHB 15 (futur) | 3 | - | - | - |



## Options du modèle "MECAx"
#### **kinematic** : Type de cinématique
Définit si les déformations sont petites ou grandes.
**Valeurs possibles** :
- **`small`** : Petites déformations (hypothèse HPP)
  - Déformations < 5-10%
  - Relation linéaire déplacement-déformation
  - Géométrie de référence = géométrie actuelle
- **`large`** : Grandes déformations
  - Déformations > 10%
  - Relation non-linéaire géométrique
  - Mise à jour de la configuration

**Choix pratique** :
- `small` : Béton, acier en élasticité, la plupart des structures
- `large` : Caoutchouc, matériaux mous, formage, crash

#### **formulation** : Formulation lagrangienne

⚠️ **Requis uniquement pour `kinematic='large'`**

**Valeurs possibles** :
- **`TotaL`** : Lagrangien Total
  - Toutes les quantités référencées à la configuration initiale
  - Tenseur de déformation : Green-Lagrange
  - Tenseur de contrainte : 2ème Piola-Kirchhoff
  
- **`UpdtL`** : Lagrangien Actualisé (Updated Lagrangian)
  - Quantités référencées à la configuration actuelle
  - Mise à jour incrémentale de la géométrie

#### **mass_storage** : Stockage de la matrice de masse

Définit comment la matrice de masse est calculée et stockée.

**Valeurs possibles** :
- **`lump_`** : Masse concentrée (lumped mass)
  - Matrice diagonale
  - Inversion triviale
  - Plus rapide, moins précis
  
- **`coher`** : Masse cohérente (consistent mass)
  - Matrice pleine
  - Plus coûteux, plus précis
  - Meilleure pour hautes fréquences

#### **material** : Type de comportement mécanique

Définit la classe de comportement du matériau.

**Valeurs possibles** :

| Code | Comportement | Matériaux typiques |
|------|-------------|-------------------|
| **`elas_`** | Élastique linéaire | Acier, béton (faibles charges), verre |
| **`elasd`** | Élastique avec dilatation | Matériaux thermo-élastiques |
| **`neoh_`** | Néo-Hookéen | Caoutchouc, élastomères |
| **`hyper`** | Hyperélastique général | Polymères, tissus biologiques |
| **`hyp_d`** | Hyperélastique avec dilatation | Hyperélasticité + thermique |
| **`J2iso`** | Plasticité J2 isotrope | Métaux (acier, alu) en plasticité |
| **`J2mix`** | Plasticité J2 mixte | Plasticité avec écrouissage mixte |
| **`kvisc`** | Visco-élastique | Polymères visqueux, asphalte |

**Compatibilité** :

kinematic='small' : elas_, elasd, kvisc, J2iso, J2mix
kinematic='large' + formulation='TotaL' : neoh_, hyper, hyp_d, kvisc, J2iso

#### **anisotropy** : Anisotropie du matériau

**Valeurs possibles** :
- **`iso__`** : Isotrope
  - Propriétés identiques dans toutes les directions
  - 2 paramètres : E (Young), ν (Poisson)
  
- **`ortho`** : Orthotrope
  - Propriétés différentes selon 3 directions principales
  - Nécessite : Ex, Ey, Ez, νxy, νyz, νxz, Gxy, Gyz, Gxz
  - Matériaux : composites, bois, matériaux stratifiés

#### **external_model** : Modèle utilisateur externe

Permet d'utiliser une loi de comportement définie par l'utilisateur.

**Valeurs possibles** :
- **`no___`** : Pas de modèle externe (défaut)
- **`MatL_`** : Utilise une bibliothèque MFront/MaterialLaw
- **`Demfi`** : Interface Demfi
- **`Umat_`** : Interface UMAT (type Abaqus)

#### **discrete** : Éléments discrets

Active les éléments de type ressort/amortisseur.

**Valeurs possibles** :
- **`yes__`** : Active les éléments discrets
- **`no___`** : Désactive (défaut)

## Exemple
Dans l'onglet 'Modèle' choisissez : 
1. Nom : `rigid`
2. Élément : `Rxx2D`
3. Dimension : `2`
4. Cliquez ensuise sur le bouton *Créer Modèle*

![modele](captures/modele_rigid.JPG)

**Important** :

Ce tableau résume la compatibilité entre matériau et modèle dans LMGC90: 
| Matériau | MECAx (elas_) | MECAx (neoh_) | MECAx (hyper) | MECAx (kvisc) | MECAx (J2iso) | MECAx (J2mix) | MECAx (elasd) | MECAx (hyp_d) | THERx | POROx | MULTI |
|----------|---------------|---------------|---------------|---------------|---------------|---------------|---------------|---------------|-------|-------|-------|
| **RIGID** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **THERMO_RIGID** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **DISCRETE** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **USER_MAT** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **EXTERNAL** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **ELAS** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **VISCO_ELAS** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **ELAS_PLAS** | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **ELAS_DILA** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **THERMO_ELAS** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **PORO_ELAS** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |