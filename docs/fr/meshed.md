# Assistant Corps Déformable — Maillage EF

L'**Assistant Corps Déformable** guide pas à pas la création d'un corps déformable maillé par éléments finis dans LMGC90_GUI. Il génère automatiquement le maillage, crée le matériau et le modèle associés, applique les conditions aux limites, puis stocke l'avatar de type `MESH_DEFORMABLE` directement dans le projet.

Le maillage est construit via les fonctions pylmgc90 `pre.buildMesh2D()` ou `pre.buildMeshH8()` pour les géométries structurées, et via **gmsh** pour les géométries courbes (disque, sphère, cylindre). Dans tous les cas, le maillage brut est converti en avatar pylmgc90 via `pre.buildMeshedAvatar()`, qui produit un corps de type **MAILx** (maillage déformable). Les géométries complexes peuvent également être importées depuis un fichier externe via `pre.readMesh()`.

---

## Lancer l'assistant

| Méthode | Action |
|---------|--------|
| Menu | **Assistants → Assistant de déformable…** |
| Raccourci clavier | `Ctrl+Shift+D` |

> **Annulation :** cliquer sur **❌ Annuler** à n'importe quelle étape ferme l'assistant sans modifier le projet. L'état du projet est entièrement restauré.

---

## Vue d'ensemble des étapes

L'assistant est composé de **8 pages** parcourues séquentiellement. Les boutons **⬅️ Retour** et **Suivant ➡️** permettent de naviguer librement.

| Page | Titre | Description |
|------|-------|-------------|
| 0 | Introduction | Présentation de l'assistant et des étapes |
| 1 | Dimension | 2D ou 3D |
| 2 | Matériau | Créer ou réutiliser un matériau élastique |
| 3 | Modèle EF | Créer ou réutiliser un modèle éléments finis |
| 4 | Géométrie | Forme et dimensions du corps |
| 5 | Raffinement | Finesse du maillage |
| 6 | Conditions aux limites (DOF) | Conditions de Dirichlet et de chargement |
| 7 | Récapitulatif | Vérification avant génération |

---

## Page 0 — Introduction

Présentation des 8 étapes à venir. Aucune saisie requise. Cliquer sur **Suivant ➡️** pour commencer.

> Le maillage généré est un avatar `MESH_DEFORMABLE` de couleur `CYANx` ajouté automatiquement à la liste des avatars du projet. Ses paramètres de reconstruction sont sauvegardés dans `mesh_params` pour permettre le rechargement du projet.

![](../captures/assistant_defor_page1.JPG)

---

## Page 1 — Dimension

Choisir entre deux options exclusives :

| Choix | Fonction pylmgc90 utilisée | Géométries disponibles |
|-------|---------------------------|------------------------|
| **2D** | `pre.buildMesh2D()` + gmsh | Rectangle, Disque, Fichier externe |
| **3D** | `pre.buildMeshH8()` + gmsh | Boîte (H8), Sphère, Cylindre, Fichier externe |

La valeur **2D** est sélectionnée par défaut.

> **Effet sur les étapes suivantes :** la dimension conditionne les types d'éléments disponibles à la page Modèle, les formes disponibles à la page Géométrie, les paramètres de raffinement, et les groupes de surface (`down/up/left/right` en 2D, avec `front/rear` en plus en 3D).

![](../captures/assistant_defor_page2.JPG)

---

## Page 2 — Matériau déformable

Cette page propose deux modes :

### Mode A — Utiliser un matériau existant _(si des matériaux élastiques existent dans le projet)_

Seuls les matériaux de types élastiques sont listés : `ELAS`, `ELAS_DILA`, `VISCO_ELAS`, `ELAS_PLAS`, `THERMO_ELAS`, `PORO_ELAS`. Les matériaux `RIGID` ne sont pas proposés car incompatibles avec un corps déformable.

### Mode B — Créer un nouveau matériau

Cocher **Créer un nouveau matériau à la place** pour afficher le formulaire. Les champs conditionnels s'affichent ou se masquent automatiquement selon le type choisi.

#### Champs communs à tous les types élastiques

| Champ | Description | Valeur par défaut |
|-------|-------------|-------------------|
| **Nom** | Identifiant du matériau. **5 caractères maximum.** | `ELAS1` |
| **Type** | Type de comportement mécanique. Voir tableau ci-dessous. | `ELAS` |
| **Densité** | Masse volumique (kg/m³). Plage : 10 à 25 000. | `2700 kg/m³` (aluminium) |
| **Module de Young** | Rigidité du matériau (Pa). Plage : 10³ à 10¹². | `70 × 10⁹ Pa` |
| **Coefficient de Poisson (ν)** | Compressibilité latérale (sans dimension). Plage : 0 à 0,4999. | `0.3` |

#### Types de matériaux disponibles et champs conditionnels

| Type | Champs supplémentaires | Description |
|------|------------------------|-------------|
| `ELAS` | _(aucun)_ | Élasticité linéaire standard. |
| `ELAS_DILA` | `Dilatation thermique` (K⁻¹, défaut `1e-5`), `T_ref_meca` (°C, défaut `20.0`) | Élasticité avec couplage thermique unilatéral. |
| `VISCO_ELAS` | `Young visqueux` (Pa, défaut `1.17 × 10⁹`), `Poisson visqueux` (défaut `0.35`) | Visco-élasticité de Kelvin-Voigt. |
| `ELAS_PLAS` | `Limite élastique iso_hard` (Pa, défaut `4 × 10⁸`), `Module d'écrouissage isoh_coeff` (Pa, défaut `10⁸`) | Élasto-plasticité J2 avec écrouissage isotrope linéaire, critère Von-Mises. |
| `THERMO_ELAS` | _(young et nu mis à 0 — définis par le modèle)_ | Thermo-élasticité couplée. `conductivity='field'` et `specific_capacity='field'`. |
| `PORO_ELAS` | _(young et nu mis à 0 — définis par le modèle)_ | Poro-élasticité selon la théorie de Biot. `hydro_cpl=0.0` par défaut. |

> **Propriétés générées automatiquement :** `elas='standard'` et `anisotropy='isotropic'` sont toujours ajoutés. Pour `ELAS_PLAS`, le critère est toujours `Von-Mises`, l'écrouissage `isoh='linear'`, et les paramètres `cinh='none'`, `visc='none'`.

![](../captures/assistant_defor_page3.JPG)

---

## Page 3 — Modèle éléments finis

Même logique que la page Matériau : réutiliser un modèle existant compatible avec la dimension, ou en créer un nouveau.

### Mode A — Utiliser un modèle existant

Seuls les modèles dont la dimension correspond à celle choisie à la page 1 sont listés.

### Mode B — Créer un nouveau modèle

| Champ | Description | Valeur par défaut |
|-------|-------------|-------------------|
| **Nom** | Identifiant du modèle. **5 caractères maximum.** | `femxx` |
| **Physique** | Physique résolue. | `MECAx`, `THERx` ou `HYDRx` |
| **Élément fini** | Type d'élément. Adapté automatiquement à la dimension. | Voir tableau ci-dessous |
| **Anisotropie** | `iso__` (isotrope) ou `ortho` (orthotrope). | `iso__` |
| **Cinématique** | `small` (petites déformations) ou `large` (grandes déformations). | `small` |
| **Formulation** | `UpdtL` (lagrangien actualisé) ou `TotaL` (lagrangien total). | `UpdtL` |
| **Stockage masse** | `lump_` (masse concentrée) ou `coher` (masse cohérente). | `lump_` |

> Une description de l'élément sélectionné s'affiche en italique sous la liste déroulante.

#### Éléments disponibles par dimension

**En 2D :**

| Élément | Description |
|---------|-------------|
| `T3xxx` | Triangle linéaire à 3 nœuds |
| `Q4xxx` | Quadrangle bilinéaire à 4 nœuds |
| `T6xxx` | Triangle quadratique à 6 nœuds |
| `Q8xxx` | Quadrangle serendipity à 8 nœuds |
| `Q9xxx` | Quadrangle biquadratique complet à 9 nœuds |

**En 3D :**

| Élément | Description |
|---------|-------------|
| `H8xxx` | Hexaèdre trilinéaire à 8 nœuds |
| `H20xx` | Hexaèdre triquadratique à 20 nœuds |
| `TE10x` | Tétraèdre quadratique à 10 nœuds |
| `SHB8x` | Solide-coque hexaédrique SHB8 à 8 nœuds |
| `SHB6x` | Solide-coque prismatique SHB6 à 6 nœuds |

> Les options `material='elas_'` et `external_model='no___'` sont ajoutées automatiquement dans les options du modèle lors de la génération.

![](../captures/assistant_defor_page4.JPG)

---

## Page 4 — Géométrie

Définit la forme et les dimensions du corps. La liste des formes disponibles dépend de la dimension choisie.

### Formes 2D

#### Rectangle _(maillage structuré natif pylmgc90)_

Génère un maillage rectangulaire via `pre.buildMesh2D()`.

| Champ | Description | Défaut |
|-------|-------------|--------|
| **Centre X, Y** | Position du centre du rectangle (m). | `0.0, 0.0` |
| **Longueur X (lx)** | Dimension horizontale (m). | `1.0 m` |
| **Longueur Y (ly)** | Dimension verticale (m). | `1.0 m` |

> Le coin inférieur gauche est calculé automatiquement : `x0 = cx − lx/2`, `y0 = cy − ly/2`.

#### Disque _(via gmsh)_

Génère un maillage de disque circulaire plein via **gmsh** (`addDisk`), algorithme Frontal-Delaunay, puis importe le fichier `.msh` v2.2.

| Champ | Description | Défaut |
|-------|-------------|--------|
| **Centre X, Y** | Position du centre du disque (m). | `0.0, 0.0` |
| **Rayon (r)** | Rayon du disque (m). | `0.5 m` |

> Nécessite que **gmsh** soit installé et accessible en Python (`import gmsh`).

#### Fichier externe

Importe un maillage depuis un fichier existant via `pre.readMesh(filepath, 2)`.

| Champ | Description |
|-------|-------------|
| **Fichier maillage** | Chemin vers le fichier. Formats acceptés : `.msh`, `.vtk`, `.mesh`. Utiliser le bouton 📁 Parcourir pour naviguer. |

---

### Formes 3D

#### Boîte (H8) _(maillage structuré natif pylmgc90)_

Génère un maillage hexaédrique via `pre.buildMeshH8()`.

| Champ | Description | Défaut |
|-------|-------------|--------|
| **Centre X, Y, Z** | Position du centre de la boîte (m). | `0.0, 0.0, 0.0` |
| **Longueur X (lx)** | Dimension en X (m). | `1.0 m` |
| **Longueur Y (ly)** | Dimension en Y (m). | `1.0 m` |
| **Longueur Z (lz)** | Dimension en Z (m). | `1.0 m` |

#### Sphère _(via gmsh)_

Génère un maillage de sphère pleine via **gmsh** (`addSphere`), algorithme Frontal 3D.

| Champ | Description | Défaut |
|-------|-------------|--------|
| **Centre X, Y, Z** | Position du centre de la sphère (m). | `0.0, 0.0, 0.0` |
| **Rayon (r)** | Rayon de la sphère (m). | `0.5 m` |

#### Cylindre _(via gmsh)_

Génère un maillage de cylindre plein via **gmsh** (`addCylinder`), d'axe Z, centré en (cx, cy, cz).

| Champ | Description | Défaut |
|-------|-------------|--------|
| **Centre X, Y, Z** | Position du centre géométrique du cylindre (m). | `0.0, 0.0, 0.0` |
| **Rayon (r)** | Rayon du cylindre (m). | `0.5 m` |
| **Hauteur (h)** | Longueur axiale du cylindre (m). | `1.0 m` |

#### Fichier externe (3D)

Importe un maillage 3D via `pre.readMesh(filepath, 3)`. Formats acceptés : `.msh`, `.vtk`, `.mesh`.

![](../captures/assistant_defor_page5.JPG)

---

## Page 5 — Raffinement du maillage

Définit la finesse du maillage. Les paramètres affichés dépendent de la géométrie sélectionnée à la page précédente.

### Type de maillage structuré (Rectangle uniquement)

| Type | Description |
|------|-------------|
| `Q4` | Quadrangles bilinéaires à 4 nœuds — rapide et robuste. **Recommandé par défaut.** |
| `2T3` | Triangles à 3 nœuds obtenus en coupant chaque Q4 en 2. |
| `4T3` | Triangles à 3 nœuds obtenus en coupant chaque Q4 en 4. Maillage plus isotrope. |
| `Q8` | Quadrangles serendipity à 8 nœuds. Plus précis, plus coûteux. |

### Paramètres de raffinement par géométrie

| Géométrie | Paramètres | Estimation |
|-----------|------------|------------|
| **Rectangle** | `nx` × `ny` (défaut 10 × 10) | nx × ny éléments |
| **Disque** | `nr` (défaut 5) × `ntheta` (défaut 16) | nr × ntheta éléments |
| **Boîte (H8)** | `nx` × `ny` × `nz` (défaut 10 × 10 × 5) | nx × ny × nz éléments |
| **Sphère** | `nr` × `ntheta` × `nphi` (défaut 5 × 16 × 8) | nr × ntheta × nphi éléments |
| **Cylindre** | `nr` × `ntheta` × `nz` (défaut 5 × 16 × 5) | nr × ntheta × nz éléments |
| **Fichier externe** | _(pas de paramètre — maillage défini dans le fichier)_ | — |

> Un compteur d'éléments estimés se met à jour en temps réel lors de la modification des paramètres.

**Signification des paramètres gmsh :**

| Paramètre | Signification |
|-----------|--------------|
| `nr` | Nombre de couches d'éléments dans la direction radiale. |
| `ntheta` | Nombre d'éléments dans la direction angulaire (circonférence). |
| `nphi` | Nombre d'éléments dans la direction polaire (latitude, sphère uniquement). |
| `nz` | Nombre d'éléments dans la direction axiale Z. |
| `nx`, `ny`, `nz` | Nombre d'éléments dans les directions cartésiennes X, Y, Z. |

![](../captures/assistant_defor_page6.JPG)

> **Conseil :** commencer avec les valeurs par défaut pour vérifier la géométrie, puis augmenter `nx`/`ny`/`nr`/`ntheta` pour améliorer la précision du calcul.

---

## Page 6 — Conditions aux limites (DOF)

Définit les conditions aux limites mécaniques appliquées sur les **groupes de surface** du maillage. Ces groupes sont créés automatiquement par `buildMesh2D` et `buildMeshH8`.

### Groupes de surface disponibles

| Groupe | Description | Disponible |
|--------|-------------|-----------|
| `down` | Bord inférieur (y = y_min ou z = z_min) | 2D et 3D |
| `up` | Bord supérieur (y = y_max ou z = z_max) | 2D et 3D |
| `left` | Bord gauche (x = x_min) | 2D et 3D |
| `right` | Bord droit (x = x_max) | 2D et 3D |
| `front` | Face avant (z = z_min) | 3D uniquement |
| `rear` | Face arrière (z = z_max) | 3D uniquement |

> **Note :** pour les géométries courbes (disque, sphère, cylindre) importées depuis gmsh, les groupes de surface dépendent des entités physiques définies dans le fichier `.msh`. Les noms peuvent différer de ceux ci-dessus.

### Créer une condition DOF

Cliquer sur **+ Ajouter une condition DOF** pour créer une ligne. Chaque ligne contient trois colonnes :

| Colonne | Description | Valeurs |
|---------|-------------|---------|
| **Type DOF** | Nature de la condition. | `imposeDrivenDof` ou `imposeInitValue` |
| **Groupe** | Groupe de surface sur lequel appliquer la condition. | `down`, `up`, `left`, `right`, `front`, `rear` |
| **Paramètres** | Arguments pylmgc90 au format `cle=valeur, cle=valeur`. Accepte les expressions Python. | Voir exemples ci-dessous |

### Types de conditions DOF

| Type | Description |
|------|-------------|
| `imposeDrivenDof` | Degré de liberté piloté : impose un déplacement ou une vitesse sur la durée du calcul. |
| `imposeInitValue` | Valeur initiale : impose une position ou une vitesse à l'instant t = 0 uniquement. |

### Exemples de paramètres

| Usage | Paramètres |
|-------|------------|
| Blocage de la translation (2D) | `component=[1,2], dofty="vlocy"` |
| Blocage de la translation (3D) | `component=[1,2,3], dofty="vlocy"` |
| Déplacement imposé en Y | `component=[2], ct=0.001` |
| Valeur initiale nulle | `component=[1,2], value=0.0` |
| Blocage en X uniquement | `component=[1], dofty="vlocy"` |

![](../captures/assistant_defor_page7.JPG)

> **Traitement des paramètres :** le champ Paramètres est analysé via `SafeEvaluator.eval_dict()` — les expressions Python simples sont autorisées (`[1,2]`, `0.001`, `"vlocy"`). Chaque condition est convertie en `DOFOperation` et transmise à `controller.add_dof_operation()`, qui applique la condition ET la sauvegarde dans `state.operations` (visible dans l'onglet DOF pour modification ultérieure).

> Pour supprimer une ligne, cliquer sur le bouton **x** à droite de la ligne.


---

## Page 7 — Récapitulatif

Affiche un résumé complet de la configuration avant génération.

| Section | Informations affichées |
|---------|------------------------|
| **Géométrie** | Forme, type de maillage structuré (2D), dimensions, centre |
| **Raffinement** | Paramètres de discrétisation, nombre d'éléments estimé |
| **Matériau** | Nom, type, densité, Young, ν — ou matériau existant |
| **Modèle EF** | Nom, physique, élément, anisotropie, cinématique, formulation, stockage masse |
| **Conditions DOF** | Liste des conditions : type, groupe, paramètres |

![](../captures/assistant_defor_page8.JPG)

Cliquer sur **✅ Générer le maillage** pour lancer la génération. Un message de confirmation indique le nombre de nœuds et d'éléments créés.

> **En cas d'erreur :** l'état du projet est entièrement restauré. Le message d'erreur détaille la cause (matériau introuvable, fichier manquant, paramètre invalide, gmsh non disponible, etc.).

---

## Résultat de la génération

À la fin de l'assistant, les éléments suivants sont créés dans le projet :

| Élément | Description |
|---------|-------------|
| **Matériau** | Ajouté à l'onglet Matériau (si créé). |
| **Modèle EF** | Ajouté à l'onglet Modèle (si créé). |
| **Avatar MESH_DEFORMABLE** | Corps déformable de couleur `CYANx`, ajouté à la liste des avatars. |
| **Conditions DOF** | Sauvegardées dans `state.operations`, visibles dans l'onglet DOF. |

Le corps déformable peut ensuite être enrichi via l'onglet **Avatar vide** (mode « Corps déformable existant ») pour y ajouter des contacteurs de surface permettant les interactions avec des corps rigides.

![](../captures/assistant_defor_page9.JPG)

---

## Remarques importantes

**Fichiers externes** : les formats `.msh` (gmsh v2), `.vtk` et `.mesh` sont acceptés par `pre.readMesh()`. Le fichier doit être compatible avec la dimension choisie (2D ou 3D). Pour les fichiers gmsh, s'assurer que les entités physiques sont définies (surfaces en 2D, volumes en 3D).

**Conditions DOF** : les conditions aux limites créées dans l'assistant sont sauvegardées et visibles dans l'onglet DOF. Elles peuvent être modifiées ou supprimées après la génération sans avoir à relancer l'assistant.

**Estimation du nombre d'éléments** : le compteur à la page Raffinement est une **estimation** basée sur le produit des paramètres de discrétisation. Le nombre réel peut différer légèrement pour les géométries courbes générées par gmsh.

