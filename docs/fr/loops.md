# Génération paramétrique d'avatars (boucles)

L'onglet **Boucles** (`Ctrl+6`) permet de créer automatiquement des séries d'avatars selon des motifs géométriques ou des expressions Python. Il propose deux mécanismes complémentaires :

- **Boucles géométriques** : positionnement automatique d'un avatar modèle selon un motif (Cercle, Grille, Ligne, Spirale).
- **Boucles `for` génériques** : génération d'avatars, matériaux, modèles, lois de contact, tables de visibilité ou opérations DOF via des expressions Python évaluées à chaque itération.

Les boucles créées sont sauvegardées dans le projet et reconstituées lors du rechargement. Elles sont également exportées dans le script Python généré.

![](captures/boucle_disk_ligne.JPG)

---

## Partie 1 — Boucles géométriques

### Principe

Une boucle géométrique prend un **avatar modèle** déjà défini dans l'onglet Avatar, calcule une liste de positions selon le motif choisi, puis crée une copie identique de l'avatar à chaque position. Tous les attributs de l'avatar modèle sont copiés (type, matériau, modèle, rayon, couleur, etc.).

### Champs du formulaire

| Champ | Description |
|-------|-------------|
| **Avatar modèle** | Index de l'avatar dont les propriétés seront copiées à chaque position. Sélectionner dans la liste déroulante des avatars existants. |
| **Type de boucle** | Motif géométrique de placement. Voir les 4 types ci-dessous. |
| **Nombre d'éléments** | Nombre d'avatars à créer. |
| **Offset X** | Décalage du centre du motif en X (m). |
| **Offset Y** | Décalage du centre du motif en Y (m). |
| **Groupe** | Nom du groupe d'avatars dans lequel stocker les avatars générés. Laissé vide pour ne pas créer de groupe. |

---

### Types de boucles géométriques

#### Cercle

Répartit `count` avatars uniformément sur un cercle de rayon `radius`, centré en `(offset_x, offset_y)`.

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| **Rayon** | Rayon du cercle de placement (m). | — |
| **Offset X / Y** | Centre du cercle. | `0.0` |

**Usage typique :** particules en anneau, tambour rotatif, couronne de boulons, granulométrie circulaire.

---

#### Grille

Répartit `count` avatars sur une grille carrée de côté, avec un espacement `step` entre éléments.

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| **Pas (step)** | Distance entre deux avatars voisins sur la grille (m). | — |
| **Offset X / Y** | Coin inférieur gauche de la grille. | `0.0` |


> La grille est toujours carrée. Si `count` n'est pas un carré parfait, le nombre réel d'avatars créés est `n_side²`. Exemple : `count=10` → grille 4×4 = 16 avatars.

**Usage typique :** empilement régulier de particules, plaque perforée, réseau carré.

---

#### Ligne

Aligne `count` avatars en ligne droite, séparés d'un pas `step`, dans la direction X ou Y.

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| **Pas (step)** | Distance entre deux avatars consécutifs (m). | — |
| **Offset X / Y** | Position du premier avatar. | `0.0` |
| **Inverser l'axe** | Si coché, la ligne est orientée selon Y (verticale) au lieu de X (horizontale). | décoché |

**Usage typique :** rangée de poteaux, file de particules, mur simple.

![](captures/rendu_boucle_disk_ligne.JPG)

---

#### Spirale

Dispose `count` avatars sur une spirale d'Archimède, de rayon initial `radius` qui croît d'un facteur `spiral_factor` à chaque itération.

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| **Rayon initial** | Rayon de départ de la spirale (m). | — |
| **Facteur de spirale** | Incrément de rayon par élément (m). | — |
| **Offset X / Y** | Centre de la spirale. | `0.0` |

**Usage typique :** mélangeurs, dépôts en spirale, arrangements décoratifs.

---

### Gestion des boucles géométriques

#### Créer une boucle

Remplir le formulaire et cliquer sur **✅ Générer la boucle**. Les avatars sont créés immédiatement dans le projet.

#### Modifier une boucle

Sélectionner une boucle dans la liste, modifier les paramètres et cliquer sur **💾 Mettre à jour**. Les anciens avatars sont supprimés et recréés avec les nouveaux paramètres.

#### Supprimer une boucle

Sélectionner une boucle dans la liste et cliquer sur **🗑️ Supprimer**. Tous les avatars générés par cette boucle sont supprimés automatiquement.

> **Suppression en cascade :** la suppression d'une boucle supprime **tous** les avatars qu'elle a générés (indices enregistrés dans `loop.generated_indices`), dans l'ordre inverse pour ne pas décaler les autres indices.

---

## Partie 2 — Boucles `for` génériques

### Principe

Les boucles `for` génériques permettent de créer des séries d'éléments en faisant varier une **variable de boucle** sur un intervalle défini par des expressions Python. Le **type d'élément** à créer est choisi parmi : avatar, matériau, modèle, loi de contact, table de visibilité, ou opération DOF.

![](captures/for_generique.JPG)

À chaque itération, le **template de configuration** est évalué avec la variable de boucle injectée dans le contexte d'évaluation.

### Champs du formulaire

| Champ | Description | Exemple |
|-------|-------------|---------|
| **Variable de boucle** | Nom de la variable Python disponible dans le template. | `i`, `k`, `n` |
| **Début** | Expression Python pour la valeur de départ. | `0`, `1`, `n_start` |
| **Fin** | Expression Python pour la valeur de fin (exclue). | `10`, `count`, `n_start + 5` |
| **Pas** | Expression Python pour l'incrément. | `1`, `2`, `-1` |
| **Type d'élément** | Type de l'objet à créer à chaque itération. | voir tableau ci-dessous |
| **Template** | Configuration de l'élément, avec la variable de boucle utilisable dans les valeurs. | voir sections par type |
| **Groupe** | Nom du groupe d'avatars (avatars uniquement). | `ma_ligne` |

### Contexte d'évaluation disponible

Les expressions dans le template et les bornes de la boucle ont accès aux éléments suivants :

| Symbole | Description |
|---------|-------------|
| `i` (ou la variable de boucle) | Valeur courante de l'itération |
| `math` | Module `math` Python complet |
| `sqrt`, `pi`, `e` | Raccourcis math |
| `abs`, `min`, `max`, `sum`, `len` | Fonctions Python standard |
| `str`, `int`, `float` | Conversions de type |
| Variables dynamiques | Toutes les variables définies dans le menu **Outils → Variables dynamiques** |

---

### Types d'éléments disponibles

#### Type `avatar` — Création d'avatars

Crée un avatar à chaque itération. Tous les paramètres de l'onglet Avatar sont disponibles dans le template.

**Paramètres du template :**

| Clé | Description | Exemple |
|-----|-------------|---------|
| `avatar_type` | Type pylmgc90 de l'avatar. | `"rigidDisk"` |
| `center` | Expression Python retournant une liste `[x, y]` ou `[x, y, z]`. La variable de boucle peut être utilisée. | `[i * 0.1, 0.0]` |
| `material_name` | Nom du matériau (chaîne). | `"TDURx"` |
| `model_name` | Nom du modèle (chaîne). | `"rigid"` |
| `color` | Code couleur LMGC90 (5 caractères). | `"BLUEx"` |
| `radius` | Expression Python pour le rayon (m). | `"0.05 + i * 0.01"` |
| `axis` | Dict `{axe1: expr, axe2: expr}` pour les joncs / plans. | `{"axe1": "1.0", "axe2": "0.1"}` |
| `nb_vertices` | Expression pour le nombre de sommets (polygones). | `"6"` |
| `generation_type` | `"regular"`, `"full"` ou `"bevel"`. | `"regular"` |
| `vertices` | Expression Python retournant la liste des sommets. | `"[[-0.1,-0.1],[0.1,-0.1],[0.1,0.1],[-0.1,0.1]]"` |
| `wall_params` | Dict des paramètres de mur. | `{"l": "2.0", "r": "0.05"}` |
| `contactors` | Liste de contacteurs (format identique à l'onglet Avatar vide). | |
| `is_hollow` | Booléen — crée un disque creux. | `false` |

**Script généré :**
```python
for i in range(0, 10, 1):
    center = [i * 0.1, 0.0]
    body = pre.rigidDisk(
        center=center,
        model=mods['rigid'],
        material=mats['TDURx'],
        color='BLUEx',
        r=0.05 + i * 0.01
    )
    bodies.addAvatar(body)
    bodies_list.append(body)
```

**Usage typique :** ligne de disques avec rayons croissants, grille d'avatars hétérogènes, série de corps avec des paramètres qui varient.

---

#### Type `material` — Création de matériaux

Crée un matériau à chaque itération. Utile pour générer une famille de matériaux avec des propriétés graduées.

**Paramètres du template :**

| Clé | Description | Exemple |
|-----|-------------|---------|
| `name` | Expression Python pour le nom (chaîne, 5 car. max). | `"str('mat') + str(i)"` |
| `material_type` | Type de matériau LMGC90. | `"RIGID"` |
| `density` | Expression Python pour la densité (kg/m³). | `"2800 + i * 100"` |
| `properties` | Dict de propriétés supplémentaires. | `{"young": "1e9 + i * 1e8"}` |

**Script généré :**
```python
for i in range(0, 5, 1):
    mat_name = str('mat') + str(i)
    density_val = 2800 + i * 100
    mats[mat_name] = pre.material(
        name=mat_name,
        materialType='RIGID',
        density=density_val
    )
    materials.addMaterial(mats[mat_name])
```

---

#### Type `model` — Création de modèles

Crée un modèle éléments finis à chaque itération.

**Paramètres du template :**

| Clé | Description | Exemple |
|-----|-------------|---------|
| `name` | Expression Python pour le nom. | `"'mod' + str(i)"` |
| `physics` | Physique. | `"MECAx"` |
| `element` | Élément fini. | `"Rxx2D"` |
| `dimension` | Dimension (2 ou 3). | `2` |
| `options` | Dict des options numériques. | `{}` |

---

#### Type `contact_law` — Création de lois de contact

Crée une loi de contact à chaque itération. Utile pour générer des lois avec des coefficients de friction différents.

**Paramètres du template :**

| Clé | Description | Exemple |
|-----|-------------|---------|
| `name` | Expression Python pour le nom. | `"'law' + str(i)"` |
| `law_type` | Type de loi (`IQS_CLB`, etc.). | `"IQS_CLB"` |
| `friction` | Expression Python pour le coefficient de friction. | `"0.1 + i * 0.05"` |

**Script généré :**
```python
for i in range(0, 5, 1):
    law_name = 'law' + str(i)
    laws[law_name] = pre.tact_behav(
        name=law_name,
        law='IQS_CLB',
        fric=0.1 + i * 0.05
    )
    tacts.addBehav(laws[law_name])
```

---

#### Type `visibility` — Création de tables de visibilité

Crée une règle de visibilité (table de détection de contact) à chaque itération.

**Paramètres du template :**

| Clé | Description | Exemple |
|-----|-------------|---------|
| `candidate_body` | Corps candidat (`RBDY2`, `RBDY3`). | `"RBDY2"` |
| `candidate_contactor` | Contacteur candidat (`DISKx`, etc.). | `"DISKx"` |
| `candidate_color` | Expression pour la couleur candidat. | `"'BLUEx'"` |
| `antagonist_body` | Corps antagoniste. | `"RBDY2"` |
| `antagonist_contactor` | Contacteur antagoniste. | `"DISKx"` |
| `antagonist_color` | Expression pour la couleur antagoniste. | `"'REDxx'"` |
| `behavior_name` | Nom de la loi de contact associée. | `"'law' + str(i)"` |
| `alert` | Distance d'alerte (m). | `"0.05 + i * 0.01"` |

---

#### Type `dof` — Opérations DOF

Applique une condition aux limites (degré de liberté imposé) à un ou plusieurs avatars à chaque itération.

**Paramètres du template :**

| Clé | Description | Exemple |
|-----|-------------|---------|
| `operation_type` | Type d'opération pylmgc90. | `"imposeDrivenDof"` |
| `target_type` | Toujours `"avatar"`. | `"avatar"` |
| `target_value` | Expression Python pour l'index de l'avatar cible. | `"i"`, `"i + 10"` |
| `parameters` | Dict des kwargs pylmgc90. | `{"component": "[1,2]", "dofty": "\"vlocy\""}` |

**Script généré :**
```python
for i in range(0, 5, 1):
    bodies_list[i].imposeDrivenDof(component=[1,2], dofty="vlocy")
```

---

### Gestion des boucles `for`

Les boucles `for` sont listées séparément des boucles géométriques. Les mêmes opérations sont disponibles : créer, modifier (régénère les éléments), supprimer (supprime les éléments générés).

---

## Groupes d'avatars

Les deux types de boucles peuvent stocker les avatars générés dans un **groupe nommé**. Un groupe est une liste d'indices d'avatars accessible dans tout le projet sous le nom donné.

Les groupes permettent :
- d'appliquer une condition DOF à tous les avatars d'un groupe d'un seul coup
- de cibler un ensemble d'avatars dans les tables de visibilité
- de distinguer plusieurs populations d'avatars pour l'extraction de données (chipy `GetBodyVector`)

> Si le champ Groupe est laissé vide, aucun groupe n'est créé et les avatars sont simplement ajoutés à la liste globale.

---

## Récapitulatif des paramètres par type de boucle géométrique

| Type | Paramètres requis | Paramètre optionnel | Formule |
|------|-------------------|---------------------|---------|
| **Cercle** | `count`, `radius` | `offset_x`, `offset_y` | `x = offset_x + radius × cos(2πi/count)` |
| **Grille** | `count`, `step` | `offset_x`, `offset_y` | `x = offset_x + (i % n_side) × step` |
| **Ligne** | `count`, `step` | `offset_x`, `offset_y`, `invert_axis` | `x = offset_x + i × step` (ou Y si inversé) |
| **Spirale** | `count`, `radius`, `spiral_factor` | `offset_x`, `offset_y` | `r = radius + i × spiral_factor` |


---

## Remarques importantes

**Avatar modèle non supprimable :** un avatar utilisé comme modèle par une boucle géométrique ne peut pas être supprimé tant que la boucle existe. Un message d'avertissement est affiché.

**Mise à jour en cascade :** modifier une boucle (géométrique ou `for`) supprime et recrée tous ses avatars. Si d'autres éléments du projet référencent ces avatars (conditions DOF, tables de visibilité), ils peuvent être invalidés.

**Expressions Python :** dans les boucles `for`, les expressions sont évaluées via `SafeEvaluator`. Les expressions malformées génèrent un message d'erreur sans bloquer le projet. Les variables dynamiques définies dans **Outils → Variables dynamiques** (`Ctrl+V`) sont accessibles dans toutes les expressions.

**Dimension 3D :** les boucles géométriques génèrent des centres 2D `[x, y]` ou 3D `[x, y, z]` selon la dimension du projet. Les avatars 3D (sphères, polyèdres) peuvent être générés en boucle `for` avec des centres explicitement 3D dans le template.

**Nombre d'éléments et performance :** créer plus de quelques milliers d'avatars via une boucle peut ralentir l'interface. Pour les grands assemblages (> 5 000 avatars), utiliser le générateur de granulométrie ou les assistants dédiés.
