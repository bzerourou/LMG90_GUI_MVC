# Création d'un Modèle

Le modèle définit le **solveur éléments finis** qui sera utilisé pour les corps déformables du projet. Il associe une physique, un type d'élément fini, une dimension spatiale et des options numériques.

## Interface
L'onglet **Modèle** (`Ctrl+2`) est divisé en deux parties :
 
- **Liste des modèles** (en haut) : tableau affichant tous les modèles définis dans le projet avec leur nom, physique, élément et dimension. Les modèles utilisés par au moins un avatar sont affichés en vert.
- **Formulaire de création / modification** (en bas) : champs de saisie dont la section Options s'adapte automatiquement à l'élément sélectionné.

### Champs du formulaire
 
| Champ | Description |
|-------|-------------|
| **Nom** | Identifiant unique du modèle. **sur 5 caractères** (contrainte interne LMGC90). Exemples : `rigid`, `MECAx`, `elas2`, `ther3`. |
| **Physique** | Famille de physique résolue. Détermine la liste d'éléments disponibles. Voir section [Physiques disponibles](#physiques-disponibles). |
| **Dimension** | Dimension spatiale : `2` (2D) ou `3` (3D). La liste d'éléments se met à jour automatiquement. |
| **Élément** | Type d'élément fini. La liste dépend de la physique ET de la dimension sélectionnées. |
| **Options** | Paramètres numériques affichés automatiquement selon l'élément. Les éléments rigides (`Rxx2D`, `Rxx3D`) n'ont aucune option. |
 
> **Mise à jour automatique :** à chaque changement de physique ou de dimension, la liste d'éléments disponibles est rechargée. Si l'élément précédemment sélectionné existe dans la nouvelle liste, il est conservé.
 
---
 
## Physiques disponibles
 
Les quatre physiques sont toutes implémentées dans LMGC90_GUI.
 
| Code | Nom complet | Description | Matériaux compatibles |
|------|-------------|-------------|----------------------|
| `MECAx` | Mécanique des solides | Déformation, contrainte, dynamique. | `RIGID`, `ELAS`, `ELAS_DILA`, `VISCO_ELAS`, `ELAS_PLAS` |
| `THERx` | Thermique | Diffusion de chaleur, convection, rayonnement. | `THERMO_ELAS` |
| `POROx` | Poromécanique | Couplage solide / fluide selon la théorie de Biot. | `PORO_ELAS` |
| `MULTI` | Thermo-hydraulique-mécanique (THM) | Couplage complet mécanique + thermique + hydraulique. | `PORO_ELAS`, `THERMO_ELAS` |
 
---
 
## Éléments disponibles par physique
 
### MECAx — Éléments mécaniques 2D
 
| Élément | Géométrie | Nœuds | Ordre | Description |
|---------|-----------|-------|-------|-------------|
| `Rxx2D` | Point | 1 | — | Corps rigide 2D. Aucune option. |
| `T3xxx` | Triangle 3 nœuds | 3 | 1 | Triangle linéaire standard. |
| `T3Lxx` | Triangle 3 nœuds | 3 | 1 | Triangle linéaire enrichi (incompatible). |
| `T6xxx` | Triangle 6 nœuds | 6 | 2 | Triangle quadratique. |
| `DKTxx` | Triangle 3 nœuds | 3 | 1 | Triangle de Kirchhoff discret (plaques minces). |
| `Q4xxx` | Quadrangle 4 nœuds | 4 | 1 | Quadrangle bilinéaire standard. |
| `Q4P0x` | Quadrangle 4 nœuds | 4 | 1 | Quadrangle bilinéaire + pression constante (quasi-incompressible). |
| `Q8xxx` | Quadrangle 8 nœuds | 8 | 2 | Quadrangle sérendipité. |
| `Q8Rxx` | Quadrangle 8 nœuds | 8 | 2 | Quadrangle sérendipité à intégration réduite. |
| `Q9xxx` | Quadrangle 9 nœuds | 9 | 2 | Quadrangle Lagrange biquadratique. |
| `BARxx` | Segment 2 nœuds | 2 | 1 | Barre / treillis 1D. |
| `SPRG2` | Segment 2 nœuds | 2 | 1 | Ressort 2D (`discrete=yes__` ajouté automatiquement). |
 
### MECAx — Éléments mécaniques 3D
 
| Élément | Géométrie | Nœuds | Ordre | Description |
|---------|-----------|-------|-------|-------------|
| `Rxx3D` | Point | 1 | — | Corps rigide 3D. Aucune option. |
| `TE4xx` | Tétraèdre 4 nœuds | 4 | 1 | Tétraèdre linéaire. |
| `TE4Lx` | Tétraèdre 4 nœuds | 4 | 1 | Tétraèdre linéaire enrichi (F-bar). |
| `TE10x` | Tétraèdre 10 nœuds | 10 | 2 | Tétraèdre quadratique. |
| `H8xxx` | Hexaèdre 8 nœuds | 8 | 1 | Hexaèdre trilinéaire. |
| `H20xx` | Hexaèdre 20 nœuds | 20 | 2 | Hexaèdre sérendipité. |
| `H20Rx` | Hexaèdre 20 nœuds | 20 | 2 | Hexaèdre sérendipité à intégration réduite. |
| `PRI6x` | Prisme 6 nœuds | 6 | 1 | Prisme linéaire. |
| `SHB6x` | Prisme 6 nœuds | 6 | 1 | Prisme solide-coque SHB6. |
| `PRI15` | Prisme 15 nœuds | 15 | 2 | Prisme quadratique. |
| `BARxx` | Segment 2 nœuds | 2 | 1 | Barre / treillis 1D. |
| `SPRG3` | Segment 2 nœuds | 2 | 1 | Ressort 3D (`discrete=yes__` ajouté automatiquement). |
 
### THERx — Éléments thermiques 2D
 
| Élément | Nœuds | Ordre | Options thermiques spécifiques |
|---------|-------|-------|-------------------------------|
| `Rxx2D` | 1 | — | aucune |
| `T3xxx` | 3 | 1 | `mass_storage`, `convection`, `radiation` |
| `T6xxx` | 6 | 2 | `mass_storage`, `convection`, `radiation` |
| `DKTxx` | 3 | 1 | `mass_storage`, `convection`, `radiation` |
| `Q4xxx` | 4 | 1 | `mass_storage`, `convection`, `radiation` |
| `Q4P0x` | 4 | 1 | `mass_storage`, `convection`, `radiation` |
| `Q8xxx` | 8 | 2 | `mass_storage`, `convection`, `radiation` |
| `Q8Rxx` | 8 | 2 | `mass_storage`, `convection`, `radiation` |
| `SPRG2` | 2 | 1 | `mass_storage` uniquement |
| `S2xth` | 2 | 1 | `mass_storage` uniquement — segment thermique 1D |
 
### THERx — Éléments thermiques 3D
 
| Élément | Nœuds | Ordre | Options thermiques spécifiques |
|---------|-------|-------|-------------------------------|
| `Rxx3D` | 1 | — | aucune |
| `TE4xx` | 4 | 1 | `mass_storage`, `convection`, `radiation` |
| `TE10x` | 10 | 2 | `mass_storage`, `convection`, `radiation` |
| `H8xxx` | 8 | 1 | `mass_storage`, `convection`, `radiation` |
| `H20xx` | 20 | 2 | `mass_storage`, `convection`, `radiation` |
| `H20Rx` | 20 | 2 | `mass_storage`, `convection`, `radiation` |
| `PRI6x` | 6 | 1 | `mass_storage`, `convection`, `radiation` |
| `PRI15` | 15 | 2 | `mass_storage`, `convection`, `radiation` |
| `SPRG3` | 2 | 1 | `mass_storage` uniquement |
 
### POROx — Éléments poromécaniques (éléments mixtes déplacement-pression)
 
| Élément | Dim. | Géométrie | Nœuds | Ordre | Description |
|---------|------|-----------|-------|-------|-------------|
| `T33xx` | 2D | Triangle | 3 | 1 | Triangle mixte P1/P1. |
| `T63xx` | 2D | Triangle | 6 | 2 | Triangle mixte P2/P1 — satisfait la condition LBB. |
| `Q44xx` | 2D | Quadrangle | 4 | 1 | Quadrangle mixte Q1/Q1. |
| `Q84xx` | 2D | Quadrangle | 8 | 2 | Quadrangle mixte Q2/Q1 — satisfait la condition LBB. |
| `TE44x` | 3D | Tétraèdre | 4 | 1 | Tétraèdre mixte P1/P1. |
| `TE104` | 3D | Tétraèdre | 10 | 2 | Tétraèdre mixte P2/P1 — satisfait la condition LBB. |
| `H88xx` | 3D | Hexaèdre | 8 | 1 | Hexaèdre mixte Q1/Q1. |
| `H208x` | 3D | Hexaèdre | 20 | 2 | Hexaèdre mixte Q2/Q1 — satisfait la condition LBB. |
 
### MULTI — Éléments THM 2D et 3D
 
Mêmes éléments mixtes que POROx, avec en plus `H8xxx` en 3D pour l'interpolation uniforme des trois champs couplés.
 
| Élément | Dim. | Description |
|---------|------|-------------|
| `T33xx` | 2D | Triangle mixte P1/P1. |
| `T63xx` | 2D | Triangle mixte P2/P1. |
| `Q44xx` | 2D | Quadrangle mixte Q1/Q1. |
| `Q84xx` | 2D | Quadrangle mixte Q2/Q1. |
| `TE44x` | 3D | Tétraèdre mixte P1/P1. |
| `TE104` | 3D | Tétraèdre mixte P2/P1. |
| `H8xxx` | 3D | Hexaèdre trilinéaire (interpolation uniforme THM). |
| `H88xx` | 3D | Hexaèdre mixte Q1/Q1. |
| `H208x` | 3D | Hexaèdre mixte Q2/Q1. |
 
---
 
## Tableau récapitulatif par usage
 
| Usage | Dimension | Éléments recommandés | Remarque |
|-------|-----------|---------------------|----------|
| Corps rigides 2D (DEM) | 2D | `Rxx2D` | Aucune option |
| Corps rigides 3D (DEM) | 3D | `Rxx3D` | Aucune option |
| Ressorts / barres 2D | 2D | `SPRG2`, `BARxx` | `discrete=yes__` auto |
| Ressorts / barres 3D | 3D | `SPRG3`, `BARxx` | `discrete=yes__` auto |
| Structures 2D — précision standard | 2D | `Q4xxx`, `T3xxx` | Rapide, adapté aux maillages structurés |
| Structures 2D — géométrie complexe | 2D | `T6xxx`, `Q8xxx` | Maillages automatiques non structurés |
| Plaques minces 2D | 2D | `DKTxx` | Formulation Kirchhoff |
| Quasi-incompressibilité 2D | 2D | `Q4P0x` | Pression constante par élément |
| Structures 3D — maillage structuré | 3D | `H8xxx`, `H20xx` | Hexaèdres recommandés |
| Structures 3D — maillage automatique | 3D | `TE10x`, `TE4xx` | Tétraèdres adaptatifs |
| Coques épaisses 3D | 3D | `SHB6x`, `PRI6x` | Solidescoques |
| Thermique 2D | 2D | `Q4xxx`, `T3xxx` | Physique THERx |
| Thermique 3D | 3D | `H8xxx`, `TE4xx` | Physique THERx |
| Segment thermique 1D | 2D / 3D | `S2xth` | Physique THERx uniquement |
| Poro-mécanique 2D (Biot) | 2D | `T63xx`, `Q84xx` | LBB satisfaite — recommandé |
| Poro-mécanique 3D (Biot) | 3D | `TE104`, `H208x` | LBB satisfaite — recommandé |
| THM couplé 3D | 3D | `H8xxx`, `TE104` | Physique MULTI |
 
---
 
## Options du modèle
 
### Options MECAx — spécifiques à l'élément
 
Ces trois options s'affichent pour tous les éléments MECAx non rigides.
 
#### `kinematic` — Hypothèse cinématique
 
| Valeur | Description | Cas d'usage |
|--------|-------------|-------------|
| `small` | Petites déformations (HPP). Relation linéaire déplacement-déformation. Géométrie de référence supposée constante. | Béton, acier en élasticité, la plupart des structures du génie civil. |
| `large` | Grandes déformations. Relation non linéaire géométrique. Mise à jour de la configuration à chaque pas. | Caoutchouc, matériaux souples, formage, impact, crash. |
 
#### `formulation` — Formulation lagrangienne
 
Pertinent uniquement pour `kinematic=large`.
 
| Valeur | Description |
|--------|-------------|
| `UpdtL` | **Lagrangien actualisé.** La configuration de référence est mise à jour à chaque pas. Contraintes de Cauchy. Recommandé pour les grandes déformations continues (métaux). |
| `TotaL` | **Lagrangien total.** La configuration de référence reste la configuration initiale. Contraintes de Piola-Kirchhoff. Recommandé pour les grandes déformations réversibles (élastomères). |
 
#### `mass_storage` — Stockage de la matrice de masse
 
| Valeur | Description | Cas d'usage |
|--------|-------------|-------------|
| `lump_` | **Masse concentrée.** Matrice diagonale. Inversion immédiate. Moins précis sur les hautes fréquences. | Dynamique explicite, schémas à pas de temps petit. |
| `coher` | **Masse cohérente.** Matrice pleine intégrée. Plus précis. Plus coûteux à inverser. | Dynamique implicite, analyse modale, hautes fréquences. |
 
---
 
### Options MECAx — communes à tous les éléments (hors rigides)
 
Ces trois options s'affichent en complément des options spécifiques à l'élément.
 
#### `material` — Loi de comportement locale
 
| Valeur | Comportement | Matériaux associés |
|--------|-------------|-------------------|
| `elas_` | Élasticité linéaire standard | `ELAS`, `ELAS_DILA`, `RIGID` |
| `elasd` | Élasticité endommageable | `ELAS_PLAS` (avec variable d'endommagement) |
| `J2iso` | Plasticité J2 isotrope | `ELAS_PLAS` (`isoh='linear'` ou `'nonlinear'`) |
| `J2mix` | Plasticité J2 mixte (isotrope + cinématique) | `ELAS_PLAS` (`isoh` et `cinh` tous les deux actifs) |
| `kvisc` | Visco-élasticité de Kelvin-Voigt | `VISCO_ELAS` |
 
#### `anisotropy` — Anisotropie
 
| Valeur | Description |
|--------|-------------|
| `iso__` | **Isotrope.** Propriétés identiques dans toutes les directions. 2 paramètres : E (Young), ν (Poisson). |
| `ortho` | **Orthotrope.** Propriétés différentes selon 3 directions principales. Nécessite les 9 constantes d'élasticité (Ex, Ey, Ez, νxy, νyz, νxz, Gxy, Gyz, Gxz). Adapté aux composites, au bois, aux matériaux stratifiés. |
 
#### `external_model` — Modèle externe
 
| Valeur | Description |
|--------|-------------|
| `MatL_` | Loi interne LMGC90 (comportement standard). Valeur par défaut. |
| `Demfi` | Interface DemFi — couplage avec un modèle DEM externe. |
| `Umat_` | Interface UMAT — routine utilisateur de type ABAQUS (Fortran / C). |
| `no___` | Désactivé. |
| `yes__` | Activé (selon le contexte de l'option). |
 
---
 
### Options THERx
 
Ces options s'affichent pour tous les éléments thermiques non rigides.
 
| Option | Valeurs | Description |
|--------|---------|-------------|
| `mass_storage` | `lump_` · `coher` | Stockage de la matrice de capacité thermique. Même signification qu'en MECAx. |
| `convection` | `no___` · `yes__` | Active les termes de convection thermique en surface. |
| `radiation` | `no___` · `yes__` | Active les termes de rayonnement thermique en surface (loi de Stefan-Boltzmann). |
| `anisotropy` | `iso__` · `ortho` | Anisotropie de la conductivité thermique. |
| `external_model` | `MatL_` · `Demfi` · `Umat_` · `no___` · `yes__` | Interface avec un modèle thermique externe. |
 
> **Note :** `SPRG2`, `SPRG3` et `S2xth` n'ont que l'option `mass_storage`. Les options `convection` et `radiation` ne s'affichent pas pour ces éléments 1D.
 
---
 
## Exemple de création — corps rigide 2D
 
1. Ouvrir l'onglet **Modèle** (`Ctrl+2`).
2. Saisir le nom : `rigid`.
3. Sélectionner la physique : `MECAx`.
4. Sélectionner la dimension : `2`.
5. Sélectionner l'élément : `Rxx2D` — la section Options disparaît (aucune option pour les éléments rigides).
6. Cliquer sur **✅ Créer Modèle**.
 
![Création d'un modèle rigide 2D](captures/modele_rigid.JPG)
 
---
 
## Exemple de création — mécanique 2D élastique
 
1. Nom : `elas2`.
2. Physique : `MECAx` · Dimension : `2` · Élément : `Q4xxx`.
3. Options affichées automatiquement :
   - `kinematic` → `small`
   - `formulation` → `UpdtL`
   - `mass_storage` → `lump_`
   - `material` → `elas_`
   - `anisotropy` → `iso__`
   - `external_model` → `MatL_`
4. Cliquer sur **✅ Créer Modèle**.
 
---
 
## Modification et suppression
 
Sélectionnez un modèle dans la liste puis cliquez sur **✏️ Modifier Sélection** pour le charger en mode **Édition**. Apportez vos modifications puis cliquez sur **💾 Enregistrer Modifications**, ou sur **❌ Annuler** pour ignorer les changements.
 
> **Suppression :** un modèle utilisé par au moins un avatar ne peut pas être supprimé directement. La boîte de dialogue d'avertissement liste les avatars concernés.
 
---
 
## Tableau de compatibilité matériau / physique
 
| Matériau | MECAx | THERx | POROx | MULTI |
|----------|-------|-------|-------|-------|
| `RIGID` | ✅ | ❌ | ❌ | ❌ |
| `ELAS` | ✅ | ✅ | ❌ | ❌ |
| `ELAS_DILA` | ✅ | ✅ | ❌ | ❌ |
| `VISCO_ELAS` | ✅ | ❌ | ❌ | ❌ |
| `ELAS_PLAS` | ✅ | ❌ | ❌ | ❌ |
| `THERMO_ELAS` | ✅ | ✅ | ❌ | ✅ |
| `PORO_ELAS` | ❌ | ❌ | ✅ | ✅ |
| `DISCRETE` | ✅ | ❌ | ❌ | ❌ |
| `USER_MAT` | ✅ | ❌ | ❌ | ❌ |
| `EXTERNAL` | ✅ | ❌ | ❌ | ❌ |
 
---
 
## Tableau de compatibilité matériau / option `material`
 
| Matériau | `elas_` | `elasd` | `J2iso` | `J2mix` | `kvisc` |
|----------|---------|---------|---------|---------|---------|
| `RIGID` | ✅ | — | — | — | — |
| `ELAS` | ✅ | — | — | — | — |
| `ELAS_DILA` | ✅ | ✅ | — | — | — |
| `VISCO_ELAS` | — | — | — | — | ✅ |
| `ELAS_PLAS` | — | ✅ | ✅ | ✅ | — |
| `THERMO_ELAS` | ✅ | ✅ | — | — | — |
 
---
 
## Astuces
 
- **Nom limité à 5 caractères** : LMGC90 ignore silencieusement les caractères supplémentaires. Préférez `rigid`, `elas2`, `ther3`, `poro2`.
- **Élément Rxx** : les corps rigides utilisent exclusivement `Rxx2D` (2D) ou `Rxx3D` (3D). Ces éléments n'ont aucune option numérique.
- **Ressorts** : pour `SPRG2` et `SPRG3`, l'option `discrete=yes__` est ajoutée automatiquement à la création — il n'est pas nécessaire de la saisir manuellement.
- **LBB en poromécanique** : pour les calculs de consolidation ou de diffusion de pression, privilégiez les éléments d'ordre supérieur (`T63xx`, `Q84xx`, `TE104`, `H208x`) qui satisfont la condition de Ladyzhenskaya-Babuška-Brezzi et évitent les oscillations parasites de pression.
- **`kinematic=large` avec `formulation`** : le champ `formulation` n'a d'effet que si `kinematic=large`. En petites déformations, la valeur de `formulation` est ignorée par le solveur.
- **Modèles non utilisés** : les modèles non associés à un avatar apparaissent en noir dans la liste. Ils n'ont aucun effet sur le calcul.