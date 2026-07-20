# Assistant de maçonnerie

L'**Assistant de maçonnerie** guide pas à pas la création de structures maçonnerie dans LMGC90_GUI. Il génère automatiquement des empilements de briques rigides via l'API pylmgc90 (`brick2D`, `brick3D`, `paneresse_simple`, `paneresse_double`), en gérant les fonctions de générations, les joints, les transformations et les groupes d'avatars.

---

## Lancer l'assistant

| Méthode | Action |
|---------|--------|
| Menu | **Assistants → Assistant de maçonnerie…** |
| Raccourci clavier | `Ctrl+Shift+M` |

> **Annulation possible à tout moment** via le bouton **❌ Annuler**, sans modification du projet.

---

## Vue d'ensemble des étapes

L'assistant est composé de **8 pages** parcourues séquentiellement.

| Page | Titre | Description |
|------|-------|-------------|
| 0 | Introduction | Présentation des appareils et de l'API utilisée |
| 1 | Dimension | 2D (`brick2D`) ou 3D (`brick3D`) |
| 2 | Matériau | Créer ou réutiliser un matériau de type `RIGID` |
| 3 | Modèle | Créer ou réutiliser un modèle `Rxx2D` / `Rxx3D` |
| 4 | Dimensions de la brique | `lx`, `ly`, `lz` et nom de la brique |
| 5 | Appareil de maçonnerie | Type d'appareil, dimensions du mur, position, couleur, groupe |
| 6 | Transformations | Translation, rotation, copie décalée post-génération |
| 7 | Récapitulatif | Vérification avant génération 

![](../captures/assistant_maçon_page1.JPG)


**API pylmgc90 utilisée :**
- `pre.brick2D(name, lx, ly)` — brique 2D (longueur × hauteur)
- `pre.brick3D(name, lx, ly, lz)` — brique 3D (longueur × profondeur × hauteur)
- `brick.rigidBrick(center, model, material, color)` — avatar pylmgc90 depuis la brique
- `pre.paneresse_simple(brick_ref, disposition)` — mur simple épaisseur géré par pylmgc90
- `pre.paneresse_double(brick_ref, disposition)` — mur double épaisseur géré par pylmgc90

---

## Page 1 — Dimension

| Choix | API pylmgc90 | Description |
|-------|-------------|-------------|
| **2D** — Structure plane | `pre.brick2D(name, lx, ly)` | Murs plans, sections 2D. `ly` est la **hauteur** de la brique. |
| **3D** — Structure volumique | `pre.brick3D(name, lx, ly, lz)` | Murs 3D, voûtes. `ly` est la **profondeur**, `lz` est la **hauteur**. |

La valeur **2D** est sélectionnée par défaut.

![](../captures/assistant_maçon_page2.JPG)

> **Effet sur les étapes suivantes :** la dimension conditionne le label de `ly` (hauteur en 2D / profondeur en 3D), la visibilité de `lz` et de l'offset Z, l'élément du modèle (`Rxx2D` ou `Rxx3D`), et les axes disponibles pour la rotation.

---

## Page 2 — Matériau des briques

Deux modes disponibles :

### Mode A — Créer un nouveau matériau _(coché par défaut)_

| Champ | Description | Valeur par défaut |
|-------|-------------|-------------------|
| **Nom** | Identifiant du matériau. **5 caractères maximum** (contrainte LMGC90). | `brick` |
| **Densité** | Masse volumique (kg/m³). Plage : 100 à 20 000. | `1800 kg/m³` (maçonnerie typique) |

> Le type est toujours `RIGID` — les briques sont des corps rigides. Il n'est pas nécessaire de spécifier des propriétés élastiques.

### Mode B — Utiliser un matériau existant

Liste déroulante de tous les matériaux déjà définis dans l'onglet Matériau. Tous les types sont acceptés, mais `RIGID` est recommandé pour les briques.

![](../captures/assistant_granulo_page3.JPG)

> **Validation :** le bouton Suivant est bloqué si le nom est vide (mode A) ou si aucun matériau valide n'est disponible (mode B).

---

## Page 3 — Modèle physique

Deux modes disponibles :

### Mode A — Créer un nouveau modèle _(coché par défaut)_

| Champ | Description | Valeur par défaut |
|-------|-------------|-------------------|
| **Nom** | Identifiant du modèle. **5 caractères maximum.** | `rigid` |
| **Physique** | Toujours `MECAx` pour les briques rigides. | `MECAx` (automatique) |
| **Élément** | Adapté automatiquement à la dimension. | `Rxx2D` (2D) ou `Rxx3D` (3D) |

### Mode B — Utiliser un modèle existant

Liste déroulante des modèles définis dans l'onglet Modèle.

![](../captures/assistant_maçon_page4.JPG)

> **Validation :** le bouton Suivant est bloqué si le nom est vide (mode A) ou si aucun modèle valide n'est disponible (mode B).

---

## Page 4 — Dimensions de la brique

Définit la géométrie de la brique de référence passée à `brick2D()` ou `brick3D()`.

| Champ | Description | 2D | 3D | Valeur par défaut |
|-------|-------------|----|----|-------------------|
| **Nom brique** | Identifiant interne pylmgc90 (8 caractères max). Utilisé comme premier argument de `brick2D` / `brick3D`. | ✅ | ✅ | `std` |
| **lx — longueur** | Longueur de la brique dans la direction X (m). | ✅ | ✅ | `0.200 m` |
| **ly — hauteur (2D)** | En 2D : hauteur de la brique. Argument `ly` de `brick2D`. | ✅ | — | `0.065 m` |
| **ly — profondeur (3D)** | En 3D : profondeur (épaisseur du mur). Argument `ly` de `brick3D`. | — | ✅ | `0.100 m` |
| **lz — hauteur (3D)** | En 3D uniquement : hauteur de la brique. Argument `lz` de `brick3D`. | — | ✅ | `0.065 m` |

> **Brique standard française :** lx = 0,20 m · ly = 0,10 m · lz = 0,065 m (format NF EN 771-1).  
> **Convention pylmgc90 :** `brick2D(name, lx, ly)` avec ly = hauteur. `brick3D(name, lx, ly, lz)` avec ly = profondeur, lz = hauteur.

![](../captures/assistant_maçon_page5.JPG)

---

## Page 5 — Appareil de maçonnerie

Page principale de configuration. Définit le type d'empilement, les dimensions du mur, la position, la couleur et le groupe d'avatars.

---

### Types d'appareils disponibles

#### Standard — Décalage demi-brique

Chaque rang impair est décalé d'une demi-brique (`lx/2`) par rapport au rang pair. Appareil le plus courant, très résistant aux efforts verticaux.

```
Rang 2 : [=====][=====][=====]
Rang 1 :   [=====][=====][=====]
Rang 0 : [=====][=====][=====]
```

**Calcul des centres :**
```
cx = offset_x + col × (lx + joint) + (lx/2 si rang impair) + lx/2
cy = offset_y + rang × (ly + joint) + ly/2
```

---

#### Running Bond — Décalage progressif d'un tiers

Le décalage augmente d'un tiers de brique (`lx/3`) à chaque rang, puis revient à zéro tous les trois rangs.

```
Rang 3 : [=====][=====][=====]
Rang 2 :     [=====][=====][=====]
Rang 1 :   [=====][=====][=====]
Rang 0 : [=====][=====][=====]
```

**Calcul des centres :**
```
cx = offset_x + col × (lx + joint) + (rang % 3) × (lx/3) + lx/2
```

---

#### Stack Bond — Joints alignés

Tous les joints verticaux sont parfaitement alignés. Aucun décalage entre les rangs. Esthétique, mais mécaniquement moins résistant (absence d'accrochage entre rangs).

```
Rang 2 : [=====][=====][=====]
Rang 1 : [=====][=====][=====]
Rang 0 : [=====][=====][=====]
```

**Calcul des centres :**
```
cx = offset_x + col × (lx + joint) + lx/2
cy = offset_y + rang × (ly + joint) + ly/2
```

---

#### Flemish Bond — Panneresse / Boutisse alternées

Chaque rang alterne des briques en panneresse (longueur `lx`) et des briques en boutisse (longueur `lx/2`). Le motif s'inverse d'un rang à l'autre.

```
Rang 1 : [1/2][==lx==][1/2][==lx==]
Rang 0 : [==lx==][1/2][==lx==][1/2]
```

**Calcul :** si `(rang + col) % 2 == 0` → panneresse (`brick_lx = lx`), sinon boutisse (`brick_lx = lx/2`). La position X est calculée avec un curseur cumulatif.

---

### Fonctions seulement en 3D

#### Paneresse simple — `pre.paneresse_simple`

Mur de **simple épaisseur** généré par l'API pylmgc90 avec gestion automatique des demi-briques aux extrémités, des joints et de la hauteur.

**Options spécifiques à cet appareil :**

| Option | Description | Valeurs |
|--------|-------------|---------|
| **Disposition** | Orientation des briques dans le rang. | `paneresse` · `boutisse` · `chant` |
| **Première brique** | Type de brique en début de premier rang. | `1` · `1/2` · `1/4` · `3/4` |
| **Dimensionnement** | Méthode pour définir la largeur du mur. | Nombre de briques · Longueur totale (m) |
| **Longueur totale** | Visible uniquement si Dimensionnement = « Longueur totale ». Appelle `setFirstRowByLength()`. | Ex : `3.0 m` |
| **Sans demi-briques** | Si coché, appelle `buildRigidWallWithoutHalfBricks()` au lieu de `buildRigidWall()`. | case à cocher |

**Dispositions :**

| Disposition | Description |
|-------------|-------------|
| `paneresse` | Briques posées dans le sens de la longueur (face visible = grand côté). |
| `boutisse` | Briques posées en travers (face visible = petit côté, `lx/2`). |
| `chant` | Briques posées sur le chant (hauteur = largeur de la brique). |


---

#### Paneresse double — `pre.paneresse_double`

Mur de **double épaisseur** (deux rangées de briques côte à côte). Toutes les options de la paneresse simple sont disponibles. L'API pylmgc90 géré automatiquement le décalage entre les deux épaisseurs.

---

### Dimensions du mur

| Champ | Description | Défaut |
|-------|-------------|--------|
| **Nombre de rangs** | Hauteur du mur en nombre de rangées de briques. Plage : 1 à 200. | `10` |
| **Nombre de colonnes** | Largeur du mur en nombre de briques par rang. Plage : 1 à 200. | `15` |
| **Épaisseur du joint** | Épaisseur du mortier entre briques (m). Plage : 0 à 0,05. | `0.010 m` |

> **Estimation automatique** dans le récapitulatif :  
> Largeur du mur ≈ nb_colonnes × (lx + joint)  
> Hauteur du mur ≈ nb_rangs × (lz ou ly + joint)

> **Avertissement au-delà de 5 000 briques :** une boîte de confirmation demande validation avant de continuer, car la génération peut prendre plusieurs secondes.

---

### Position initiale

Coordonnées du **coin inférieur gauche** du mur (en mètres). Les centres des briques sont calculés depuis ce point.

| Champ | Description | Défaut |
|-------|-------------|--------|
| **Offset X** | Abscisse du coin inférieur gauche. | `0.0 m` |
| **Offset Y** | Ordonnée du coin inférieur gauche. | `0.0 m` |
| **Offset Z** | Cote Z du mur (3D uniquement). | `0.0 m` |

---

### Options

| Option | Description | Défaut |
|--------|-------------|--------|
| **Couleur LMGC90** | Code couleur à 5 caractères. | `BLUEx` |
| **Stocker dans un groupe** | Si coché, enregistre tous les avatars générés dans un groupe nommé (`state.avatar_groups`). Le groupe est aussi sauvegardé dans `masonry_patterns` pour la reconstruction du script. | coché |
| **Nom du groupe** | Identifiant du groupe d'avatars. | `mur_briques` |

![](../captures/assistant_maçon_page6.JPG)

---

## Page 6 — Transformations post-génération

Les transformations s'appliquent **après** la génération de toutes les briques, sur l'ensemble des corps pylmgc90 de la session courante. Elles correspondent aux appels pylmgc90 `bodies.translate()`, `bodies.rotate()` et `copy.deepcopy(bodies)`.

> Toutes les transformations sont **désactivées par défaut** (cases décochées). Les champs sont grisés tant que la case correspondante n'est pas cochée.

---

### Translation — `bodies.translate(dx, dy, dz)`

Déplace l'ensemble du mur d'un vecteur (dx, dy, dz).

| Champ | Description | Défaut |
|-------|-------------|--------|
| **Activer la translation** | case à cocher | non coché |
| **dx** | Déplacement en X (m). | `0.0 m` |
| **dy** | Déplacement en Y (m). | `0.0 m` |
| **dz** | Déplacement en Z (m). **3D uniquement.** | `0.0 m` |

**Appel pylmgc90 généré :**
```python
# En 2D
bodies.translate(dx=dx, dy=dy)
# En 3D
bodies.translate(dx=dx, dy=dy, dz=dz)
```

---

### Rotation — `bodies.rotate(description='axis', center, axis, alpha)`

Fait pivoter l'ensemble du mur autour d'un axe passant par un centre donné. L'angle est saisi en degrés et converti automatiquement en radians.

| Champ | Description | Valeurs | Défaut |
|-------|-------------|---------|--------|
| **Activer la rotation** | case à cocher | — | non coché |
| **Centre x** | Coordonnée X du centre de rotation (m). | — | `0.0 m` |
| **Centre y** | Coordonnée Y du centre de rotation (m). | — | `0.0 m` |
| **Centre z** | Coordonnée Z du centre de rotation (m). **3D uniquement.** | — | `0.0 m` |
| **Axe** | Axe de rotation. En 2D, seul Z est pertinent (fixé automatiquement). | `Z` · `X` · `Y` | `Z` |
| **Angle α** | Angle de rotation en degrés. Converti en radians avant l'appel pylmgc90. | −360° à +360° | `90.0°` |

**Appel pylmgc90 généré :**
```python
import math, numpy as np
alpha = math.radians(90.0)
axis  = [0., 0., 1.]            # axe Z
center = np.array([cx, cy, cz])
bodies.rotate(description='axis', center=center, axis=axis, alpha=alpha)
```

> **En 2D :** l'axe est toujours Z (rotation dans le plan XY). Le champ Axe est grisé et fixé à `Z`.

---

### Copie décalée — `copy.deepcopy(bodies) + translate`

Duplique le mur complet (après translation et rotation éventuelles) et lui applique un décalage. Crée ainsi un deuxième mur indépendant dans le projet.

| Champ | Description | Défaut |
|-------|-------------|--------|
| **Créer une copie décalée** | case à cocher | non coché |
| **Décalage dx** | Décalage X de la copie (m). | `0.0 m` |
| **Décalage dy** | Décalage Y de la copie (m). | `0.0 m` |
| **Décalage dz** | Décalage Z de la copie (m). **3D uniquement.** | `0.0 m` |

**Appel pylmgc90 généré :**
```python
import copy
bodies_copy = copy.deepcopy(bodies)
bodies_copy.translate(dx=dx_copy, dy=dy_copy)   # ou dz en 3D
```

> **Usage typique :** créer deux murs parallèles d'un seul coup (dx = épaisseur de la pièce), ou, combinée avec la rotation, créer l'angle d'un bâtiment.

![](../captures/assistant_maçon_page7.JPG)

---

## Page 7 — Récapitulatif

Affiche un tableau HTML complet avant génération, incluant :

| Section | Informations |
|---------|-------------|
| **Dimension** | 2D ou 3D |
| **API pylmgc90** | Appel `brick2D(...)` ou `brick3D(...)` avec les valeurs exactes |
| **Matériau** | Nom et densité (nouveau) ou nom existant |
| **Modèle** | Nom (nouveau) ou nom existant |
| **Dimensions brique** | lx, ly, lz |
| **Appareil** | Nom du pattern sélectionné |
| **Rangs × colonnes** | Nombre total estimé de briques |
| **Épaisseur joint** | Valeur en mètres |
| **Taille mur estimée** | Largeur × Hauteur calculées depuis les paramètres |
| **Position** | Offset X, Y (et Z en 3D) |
| **Couleur** | Code couleur LMGC90 |
| **Groupe** | Nom du groupe (si activé) |
| **Translation** | dx, dy, dz (si activée) |
| **Rotation** | Axe, angle α, centre (si activée) |
| **Copie décalée** | dx, dy, dz de la copie (si activée) |
| **Options paneresse** | Disposition, première brique, mode dimensionnement, sans demi-briques (si paneresse) |

> **Avertissement automatique :** si le nombre total de briques dépasse 1 000, un message orange signale que la génération peut être lente.

Cliquer sur **✅ Générer** pour créer la structure. Un message de confirmation indique le nombre de briques créées.

---

## Résultat de la génération

À la fin de l'assistant, les éléments suivants sont créés dans le projet :

| Élément | Description |
|---------|-------------|
| **Matériau** | Ajouté à l'onglet Matériau (si créé). Type `RIGID`, densité configurée. |
| **Modèle** | Ajouté à l'onglet Modèle (si créé). `MECAx` + `Rxx2D` ou `Rxx3D`. |
| **Avatars briques** | Un avatar `EMPTY_AVATAR` par brique, avec `wall_params` stockés pour reconstruction. Couleur configurée. |
| **Groupe** | Groupe nommé dans `state.avatar_groups` regroupant tous les indices des avatars générés (si l'option est activée). |
| **masonry_patterns** | Dictionnaire sauvegardé dans le state pour la reconstruction du script de génération par `ScriptGenerator`. |

> **Reconstruction du script :** les paramètres complets du pattern (appareil, dimensions, joints, transformations, etc.) sont sauvegardés dans `state.masonry_patterns[group_name]`. Le générateur de script (`script_generator.py`) utilise ces données pour reproduire fidèlement la génération pylmgc90 lors de l'export.

---

## Exemples d'usage

### Mur standard 2D simple

```
Dimension      : 2D
Matériau       : brick — RIGID — 1800 kg/m³
Modèle         : rigid — MECAx — Rxx2D
Brique         : std — lx=0.200 m, ly=0.065 m
Appareil       : Standard
Rangs × col.   : 10 × 15 (150 briques)
Joint          : 0.010 m
Position       : (0.0, 0.0)
Couleur        : BLUEx
Groupe         : mur_nord
Transformations: (aucune)
```

---

### Mur en paneresse simple avec longueur fixe

```
Dimension      : 3D
Matériau       : stone — RIGID — 2200 kg/m³
Modèle         : rigid — MECAx — Rxx3D
Brique         : std — lx=0.200 m, ly=0.100 m, lz=0.065 m
Appareil       : Paneresse simple (pylmgc90)
  Disposition     : paneresse
  Première brique : 1/2
  Dimensionnement : Longueur totale — 4.000 m
  Sans demi-briques : Non
Rangs          : 15
Joint          : 0.010 m
Groupe         : mur_facade
```

---

### Deux murs parallèles via copie décalée

```
Appareil       : Standard — 8 rangs × 12 colonnes
Translation    : désactivée
Rotation       : désactivée
Copie décalée  : activée — dx=0.0, dy=3.5 m (largeur de la pièce)
```

Résultat : deux murs identiques distants de 3,5 m, créés en une seule exécution de l'assistant.

---

## Remarques importantes

**Nom de brique limité à 8 caractères :** le champ Nom brique accepte jusqu'à 8 caractères, mais LMGC90 peut tronquer les identifiants. Utiliser des noms courts (`std`, `half`, `custom`).

**Performance :** au-delà de 5 000 briques, la génération et l'interface peuvent ralentir significativement. Pour les grands assemblages (> 10 000 briques), préférer la génération directe depuis un script Python.

**Couleur par défaut :** si le champ Couleur est laissé vide, la valeur `BLUEx` est utilisée automatiquement.

**Transformations et centres :** après une translation ou une rotation, les centres des avatars dans `state.avatars` sont mis à jour depuis les coordonnées réelles des nœuds pylmgc90 (`body.nodes[1].coor`). Les avatars de la copie décalée sont ajoutés à la suite avec leur propre centre calculé.

**Réutilisabilité :** l'assistant peut être lancé plusieurs fois sur le même projet. Chaque exécution ajoute un nouveau groupe de briques sans effacer les précédents, à condition d'utiliser des noms d'éléments et de groupes différents.

