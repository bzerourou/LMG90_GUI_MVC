# Variables dynamiques
Les **variables dynamiques** de LMGC90_GUI permettent d'écrire des expressions Python directement dans les champs de saisie de l'interface, en utilisant les données du projet (avatars, matériaux, modèles, groupes) comme des variables. Elles remplacent les valeurs numériques figées par des expressions calculées à la volée, et se propagent automatiquement dans tous les onglets.

![](captures/variables.JPG)

---

## Accès au gestionnaire de variables

| Méthode | Action |
|---------|--------|
| Menu **Outils → Variables dynamiques** | Ouvre le gestionnaire |
| Raccourci | `Ctrl+V` |

---

## Le gestionnaire de variables dynamiques

Le gestionnaire (`DynamicVarsDialog`) utilise `SafeEvaluator` avec `build_eval_context()` pour évaluer les expressions de façon sécurisée. Il affiche un tableau à 4 colonnes : **Nom**, **Expression**, **Valeur évaluée**, **Type**. Chaque variable est une expression Python stockée sous forme de chaîne et évaluée au moment de son utilisation.

### Ajouter une variable

1. Saisir un **Nom** — identifiant Python valide (`thickness`, `r_min`, `x_wall`).
2. Saisir une **Expression** — voir les possibilités ci-dessous.
3. L'**Aperçu** se met à jour en temps réel : résultat en vert si valide, erreur en rouge.
4. Cliquer sur **Ajouter / Modifier**.

### Modifier une variable

Cliquer sur la ligne dans le tableau → les champs Nom et Expression sont remplis → modifier → **Ajouter / Modifier**.

### Supprimer une variable

Sélectionner la ligne et cliquer sur **Supprimer**.

### Rafraîchir

Cliquer sur **Rafraîchir** pour réévaluer toutes les variables avec l'état courant du projet (utile après avoir ajouté des avatars).

> **Persistance :** les variables sont sauvegardées dans le fichier `.lmgc90` du projet (`state.dynamic_vars`). Elles sont rechargées automatiquement à l'ouverture.

---

## Types d'expressions supportées

### Constantes numériques

```python
thickness = 0.5
radius = 0.075
n_cols = 15
pi_val = 3.14159
```

### Expressions mathématiques

Toutes les expressions Python numériques sont supportées :

```python
diameter = 2 * radius
area = pi * radius**2
step = lx + joint
half = thickness / 2
diag = sqrt(lx**2 + ly**2)
clamp = max(0.0, min(1.0, ratio))
```

**Fonctions mathématiques disponibles :**

| Symbole | Description |
|---------|-------------|
| `pi` | π ≈ 3.14159… |
| `e` | e ≈ 2.71828… |
| `sqrt(x)` | Racine carrée |
| `abs(x)` | Valeur absolue |
| `min(a, b)` | Minimum |
| `max(a, b)` | Maximum |
| `round(x, n)` | Arrondi à n décimales |
| `sum(liste)` | Somme d'une liste |
| `len(objet)` | Longueur |
| `math.sin(x)` | Sinus (x en radians) |
| `math.cos(x)` | Cosinus |
| `math.tan(x)` | Tangente |
| `math.log(x)` | Logarithme naturel |
| `math.log10(x)` | Logarithme décimal |
| `math.exp(x)` | Exponentielle |
| `math.floor(x)` | Partie entière inférieure |
| `math.ceil(x)` | Partie entière supérieure |
| `math.radians(deg)` | Degrés → radians |
| `math.degrees(rad)` | Radians → degrés |
| `np.array(liste)` | Tableau numpy |
| `np.linspace(a,b,n)` | Tableau régulièrement espacé |
etc,

### Variables référençant d'autres variables

Les variables sont évaluées dans l'ordre de définition — une variable peut référencer les précédentes :

```python
thickness = 0.05
radius = thickness * 3
step = radius + thickness
grid_size = step * 10
```

---

## Accès aux données du projet

### Avatars — `avatar[i]`

Accès à un avatar par son index (0-based). Toutes les propriétés sont en lecture seule.

| Expression | Description | Type retourné |
|------------|-------------|---------------|
| `avatar[i].center` | Centre complet `[x, y]` ou `[x, y, z]` | `list` |
| `avatar[i].x` | Coordonnée X du centre | `float` |
| `avatar[i].y` | Coordonnée Y du centre | `float` |
| `avatar[i].z` | Coordonnée Z du centre (3D) | `float` ou `None` |
| `avatar[i].radius` | Rayon de l'avatar | `float` ou `None` |
| `avatar[i].color` | Couleur LMGC90 (`'BLUEx'`) | `str` |
| `avatar[i].material_name` | Nom du matériau | `str` |
| `avatar[i].model_name` | Nom du modèle | `str` |
| `avatar[i].avatar_type` | Type pylmgc90 (`'rigidDisk'`) | `str` |
| `avatar[i].origin` | Origine : `'manual'`, `'loop'`, `'granulo'` | `str` |
| `avatar[i].generation_type` | `'regular'`, `'full'`, `'bevel'` ou `None` | `str` ou `None` |
| `avatar[i].is_hollow` | Disque creux | `bool` |
| `avatar[i].nb_vertices` | Nombre de sommets (polygone) | `int` ou `None` |
| `avatar[i].vertices` | Liste des sommets | `list` ou `None` |
| `avatar[i].axis` | Axes du jonc `{axe1, axe2, axe3}` | `dict` ou `None` |
| `avatar[i].contactors` | Liste des contacteurs | `list` |
| `avatar[i].wall_params` | Paramètres bruts de mur | `dict` |
| `avatar[i].brick_lx` | Longueur brique maçonnerie (`wall_params['l']`) | `float` ou `None` |
| `avatar[i].brick_ly` | Hauteur/profondeur brique (`wall_params['h']`) | `float` ou `None` |
| `avatar[i].brick_lz` | Hauteur 3D brique (`wall_params['lz']`) | `float` ou `None` |
| `avatar[i].mesh_params` | Paramètres de maillage EF | `dict` ou `None` |
| `avatar[i].index` | Indice de l'avatar dans la liste | `int` |

#### Nœuds pylmgc90 — `avatar[i].nodes`

La propriété `nodes` simule l'accès aux nœuds pylmgc90. La convention pylmgc90 numérote les nœuds à partir de 1 — `nodes[1]` est le nœud principal, identique à `nodes[0]` en Python.

| Expression | Description |
|------------|-------------|
| `avatar[i].nodes[1].coor` | Coordonnées du nœud principal `[x, y]` ou `[x, y, z]` |
| `avatar[i].nodes[1].coor[0]` | Coordonnée X du nœud |
| `avatar[i].nodes[1].coor[1]` | Coordonnée Y du nœud |
| `avatar[i].nodes[1].coor[2]` | Coordonnée Z du nœud (3D) |
| `avatar[i].nodes[0].coor` | Identique à `nodes[1]` (convention Python) |
| `avatar[i].nodes[k].coor` | k-ième sommet pour les polygones (k ≥ 1) |

> **Pourquoi `nodes[1]` ?** pylmgc90 numérote les nœuds à partir de 1. LMGC90_GUI supporte les deux conventions : `nodes[0]` et `nodes[1]` pointent tous les deux vers le nœud principal.

#### Itération sur les avatars

```python
nb = len(avatar)                    # Nombre total d'avatars
liste = list(avatar)                # Tous les avatars comme liste de proxies
centres = [av.center for av in avatar]  # Liste de tous les centres
rayons  = [av.radius for av in avatar if av.radius is not None]
```

---

### Groupes — `group['nom']`

Accès à un groupe d'avatars par son nom. Retourne une liste d'`AvatarProxy`.

| Expression | Description |
|------------|-------------|
| `group['mur_briques']` | Liste des avatars du groupe |
| `group['mur_briques'][0].center` | Centre du premier avatar du groupe |
| `group['mur_briques'][0].x` | Coordonnée X du premier avatar |
| `len(group['mur_briques'])` | Nombre d'avatars dans le groupe |
| `'mur_briques' in group` | Test d'existence du groupe (bool) |
| `list(group)` | Liste de tous les noms de groupes |

**Exemples :**
```python
nb_briques  = len(group['mur_facade'])
premier_x   = group['mur_facade'][0].x
dernier_y   = group['mur_facade'][-1].y
all_centers = [av.center for av in group['granulo_box2d']]
```

---

### Matériaux — `material['nom']`

| Expression | Description | Type |
|------------|-------------|------|
| `material['beton'].name` | Nom du matériau | `str` |
| `material['beton'].density` | Densité (kg/m³) | `float` |
| `material['beton'].material_type` | Type (`'RIGID'`, `'ELAS'`…) | `str` |
| `material['beton']['young']` | Propriété personnalisée (module de Young) | `float` |
| `material['beton']['nu']` | Propriété personnalisée (coefficient de Poisson) | `float` |
| `material['beton'].young` | Idem via attribut | `float` |

**Exemples :**
```python
rho = material['granite'].density
E   = material['acier']['young']
nu  = material['acier'].nu
```

---

### Modèles — `model['nom']`

| Expression | Description | Type |
|------------|-------------|------|
| `model['rigid'].name` | Nom du modèle | `str` |
| `model['rigid'].physics` | Physique (`'MECAx'`, `'THERx'`…) | `str` |
| `model['rigid'].element` | Élément fini (`'Rxx2D'`, `'Q4xxx'`…) | `str` |
| `model['rigid'].dimension` | Dimension (2 ou 3) | `int` |
| `model['femxx']['kinematic']` | Option numérique | dépend de l'option |

**Exemple :**
```python
dim = model['femxx'].dimension
phys = model['rigid'].physics
```

---

### Fonctions de filtrage

Retournent une liste d'`AvatarProxy` filtrée selon un critère.

| Fonction | Description | Exemple |
|----------|-------------|---------|
| `avatars_by_color('BLUEx')` | Tous les avatars de couleur `'BLUEx'` | `bleus = avatars_by_color('BLUEx')` |
| `avatars_by_material('beton')` | Tous les avatars utilisant ce matériau | `corps = avatars_by_material('TDURx')` |
| `avatars_by_type('rigidDisk')` | Tous les avatars de ce type pylmgc90 | `disques = avatars_by_type('rigidDisk')` |
| `avatars_by_origin('manual')` | Avatars créés manuellement | `manuels = avatars_by_origin('manual')` |
| `avatars_by_origin('loop')` | Avatars générés par boucle | |
| `avatars_by_origin('granulo')` | Avatars granulaires | |

**Exemples avancés :**
```python
nb_bleus = len(avatars_by_color('BLUEx'))
nb_disques_rouges = len([av for av in avatars_by_color('REDxx') if av.avatar_type == 'rigidDisk'])
rayon_moyen = sum(av.radius for av in avatars_by_type('rigidDisk')) / len(avatars_by_type('rigidDisk'))
x_min = min(av.x for av in avatars_by_color('BLUEx'))
x_max = max(av.x for av in avatars_by_color('BLUEx'))
```

---

## Utilisation par onglet

Les variables dynamiques peuvent être utilisées dans **tous les champs ** des onglets de *LMGC90_GUI*. Il suffit d'écrire le nom de la variable (ou une expression complète) à la place de la valeur numérique.

### Onglet Matériau

| Champ | Accepte des expressions |
|-------|------------------------|
| **Densité** | ✅ — ex : `material['granite'].density * 0.9` |
| **Propriétés** (`key=val, key=val`) | ✅ — ex : `young=E, nu=nu_beton` |

**Exemples :**
```
Densité    : rho
Propriétés : young=E, nu=nu, elas='standard', anisotropy='isotropic'
```

### Onglet Avatar vide (Empty Avatar)

| Champ | Accepte des expressions |
|-------|------------------------|
| **Centre** | ✅ — ex : `avatar[0].x + spacing, avatar[0].y` |
| **Paramètres des contacteurs** | ✅ — ex : `r=radius, axe1=lx/2, axe2=ly/2` |

**Exemples :**
```
Centre             : avatar[0].x + spacing, 0.0
Paramètres (DISKx) : r=radius
Paramètres (JONCx) : axe1=brick_lx/2, axe2=brick_ly/2
Paramètres (POLYG) : nb_vertices=6, vertices=sommets
```

### Onglet Contact

**Tous les paramètres numériques** de toutes les lois de contact acceptent des expressions :

| Paramètre | Exemple d'expression |
|-----------|----------------------|
| `fric` | `mu` ou `0.5 * material['beton'].density / 2500` |
| `stfr`, `dyfr` | `E * 1e3` |
| `cohn`, `coht` | `cohesion_sol` |
| `cn`, `ct` | `resistance_traction` |
| `stiffness` | `EA_cable` |

**Exemples :**
```
fric       : mu
stiffness  : EA_cable
cn         : sigma_c
```

### Onglet Boucles — Boucles `for` génériques

Dans les boucles `for` génériques, **toutes les expressions du template** ont accès aux variables dynamiques. Les bornes (`début`, `fin`, `pas`) et tous les champs du template sont évalués avec le contexte complet :

```
Début : 0
Fin   : nb_cols
Pas   : 1
center (template avatar) : [i * (lx + joint) + lx/2, offset_y]
radius (template avatar)  : r_min + i * (r_max - r_min) / nb_cols
name   (template matériau): 'mat' + str(i)
```

### Onglet Boucles — Boucles géométriques

Les paramètres des boucles géométriques (Cercle, Grille, Ligne, Spirale) peuvent utiliser les variables dynamiques via le formulaire des boucles `for` :

```
radius (Cercle) : rayon_anneau
step   (Grille) : pas_grille
```

### Assistants — Wizard déformable (page DOF)

Dans la page Conditions aux Limites de l'assistant déformable, le champ Paramètres utilise `SafeEvaluator.eval_dict()` :

```
component=[1,2], dofty="vlocy", ct=vitesse_imposee
component=[2], ct=deplacement / duree_rampe
```

---

## Expressions avancées supportées

### Opérateurs

| Opérateur | Exemple |
|-----------|---------|
| `+`, `-`, `*`, `/` | `lx + joint` |
| `//` | Division entière |
| `%` | Modulo |
| `**` | Puissance : `radius**2` |
| `==`, `!=`, `<`, `<=`, `>`, `>=` | Comparaisons |
| `and`, `or`, `not` | Logique |

### Expressions ternaires

```python
r = r_grand if grand else r_petit
val = x if x > 0 else 0.0
```

### Compréhensions de listes

```python
centres = [av.center for av in group['mur']]
rayons  = [av.radius for av in avatars_by_type('rigidDisk')]
xs      = [av.x for av in avatar]
```

### Listes et tuples

```python
center_2d = [avatar[0].x, avatar[0].y]
center_3d = [0.0, 0.0, avatar[0].z + 0.5]
```

### Expressions numpy

```python
moyenne = np.array([av.x for av in avatar]).mean()
coords  = np.array([av.center for av in avatar])
```

---

## Comparaison avec un script Python équivalent

Le tableau suivant montre l'équivalence entre une variable dynamique dans l'interface et son code Python en script de pré-traitement.

| Variable dynamique (interface) | Équivalent script Python |
|-------------------------------|--------------------------|
| `r = avatar[0].radius` | `r = bodies[0].nodes[1].coor[...]` |
| `cx = avatar[0].x` | `cx = bodies[0].nodes[1].coor[0]` |
| `cy = avatar[1].center[1]` | `cy = bodies[1].nodes[1].coor[1]` |
| `cx = avatar[0].nodes[1].coor[0]` | `cx = bodies[0].nodes[1].coor[0]` |
| `rho = material['beton'].density` | `rho = mats['beton'].density` |
| `E = material['acier']['young']` | `E = mats['acier'].young` |
| `phys = model['rigid'].physics` | `phys = mods['rigid'].physics` |
| `nb = len(avatar)` | `nb = len(bodies)` |
| `nb_g = len(group['mur'])` | `nb_g = len(group_mur)` |
| `x0 = group['mur'][0].x` | `x0 = bodies[group_mur[0]].nodes[1].coor[0]` |
| `bleus = avatars_by_color('BLUEx')` | `bleus = [b for b in bodies_list if b.color == 'BLUEx']` |

### Exemple complet

**Interface — Variables dynamiques :**
```
lx = 0.20
ly = 0.065
joint = 0.010
nb_cols = 15
nb_rows = 10
spacing = lx + joint
offset_x = 0.0
wall_width = nb_cols * spacing
```

**Équivalent script Python pré-traitement :**
```python
lx = 0.20
ly = 0.065
joint = 0.010
nb_cols = 15
nb_rows = 10
spacing = lx + joint
offset_x = 0.0
wall_width = nb_cols * spacing

for row in range(nb_rows):
    for col in range(nb_cols):
        cx = offset_x + col * spacing + lx / 2.0
        cy = row * (ly + joint) + ly / 2.0
        body = pre.rigidDisk(center=[cx, cy], ...)
        bodies.addAvatar(body)
```

---

## Propriétés de l'objet `AvatarProxy` — référence complète

Le tableau suivant liste **toutes les propriétés** accessibles via `avatar[i]` ou dans une liste de groupe.

| Propriété | Type | Notes |
|-----------|------|-------|
| `.center` | `list[float]` | `[x, y]` en 2D, `[x, y, z]` en 3D |
| `.x` | `float` | `center[0]` |
| `.y` | `float` | `center[1]` |
| `.z` | `float` ou `None` | `center[2]` ou `None` si 2D |
| `.radius` | `float` ou `None` | Rayon du disque/sphère |
| `.color` | `str` | Code couleur 5 car. (`'BLUEx'`) |
| `.material_name` | `str` | Nom du matériau associé |
| `.model_name` | `str` | Nom du modèle associé |
| `.avatar_type` | `str` | Valeur enum : `'rigidDisk'`, `'rigidSphere'`, `'rigidJonc'`, `'emptyAvatar'`… |
| `.origin` | `str` | `'manual'`, `'loop'`, `'granulo'` |
| `.generation_type` | `str` ou `None` | `'regular'`, `'full'`, `'bevel'` |
| `.is_hollow` | `bool` | Disque creux si `True` |
| `.nb_vertices` | `int` ou `None` | Nombre de sommets du polygone |
| `.vertices` | `list` ou `None` | Coordonnées des sommets `[[x1,y1], ...]` |
| `.axis` | `dict` ou `None` | `{'axe1': v, 'axe2': v, 'axe3': v}` pour joncs/plans |
| `.contactors` | `list[dict]` | Chaque dict : `{'shape', 'color', 'params'}` |
| `.wall_params` | `dict` | Paramètres de mur maçonnerie |
| `.brick_lx` | `float` ou `None` | Longueur brique (`wall_params['l']`) |
| `.brick_ly` | `float` ou `None` | Hauteur/profondeur brique (`wall_params['h']`) |
| `.brick_lz` | `float` ou `None` | Hauteur 3D brique (`wall_params['lz']`) |
| `.mesh_params` | `dict` ou `None` | Paramètres maillage EF |
| `.index` | `int` | Index dans `state.avatars` |
| `.nodes[1].coor` | `list[float]` | Nœud principal (convention pylmgc90) |
| `.nodes[0].coor` | `list[float]` | Idem (convention Python) |
| `.nodes[k].coor` | `list[float]` | k-ième sommet (polygones) |

---

## Sécurité — ce qui est autorisé et interdit

Les expressions sont analysées via `SafeEvaluator` qui inspecte l'AST Python avant exécution. Aucun `eval()` direct n'est utilisé.

### Autorisé

- Opérations arithmétiques, comparaisons, logique
- Appels de fonctions du contexte (`sqrt`, `math.sin`, `len`, `list`…)
- Compréhensions de listes, tuples, dicts
- Expressions ternaires (`a if cond else b`)
- Accès aux attributs et index
- Conversions : `int(x)`, `float(x)`, `str(x)`, `bool(x)`

### Interdit (bloqué par SafeEvaluator)

- `import`, `exec`, `eval`, `open`, `__import__`
- Toute instruction (assignment, boucle `for`/`while`, `if` — seules les expressions sont autorisées)
- Appels de fonctions non déclarées dans le contexte
- Accès à `__builtins__`, `__class__`, `__dict__`

> Si une expression tente une opération interdite, `SafeEvaluator` lève une `ValueError` avec le message `"Opération non autorisée : <NomDuNœudAST>"`.

---

## Messages d'erreur et débogage

Lorsqu'une expression échoue dans un onglet, une boîte de dialogue détaillée liste :
- L'expression fautive
- Le message d'erreur Python
- Les variables dynamiques actuellement définies
- Les références disponibles (`avatar[i].x`, `group['nom']`, etc.)

**Causes fréquentes :**

| Erreur | Cause | Solution |
|--------|-------|---------|
| `NameError: 'thickness'` | Variable pas encore définie | Créer `thickness` dans le gestionnaire |
| `IndexError: Avatar index 5 invalide` | Il y a moins de 6 avatars | Vérifier l'index |
| `KeyError: Groupe 'mur' introuvable` | Le groupe n'existe pas | Vérifier le nom dans l'onglet Boucles/Maçonnerie |
| `Opération non autorisée : Import` | Tentative d'import | Utiliser uniquement les fonctions disponibles |
| `Syntaxe invalide` | Parenthèses mal fermées | Vérifier la syntaxe Python |

---

## Exemples de variables dynamiques prêtes à l'emploi

### Géométrie de mur maçonné

```python
lx = 0.20          # Longueur brique
ly = 0.065         # Hauteur brique
lz = 0.10          # Profondeur brique (3D)
joint = 0.010      # Épaisseur joint
nb_cols = 15       # Nombre de colonnes
nb_rows = 10       # Nombre de rangs
spacing_x = lx + joint
spacing_y = ly + joint
wall_width = nb_cols * spacing_x
wall_height = nb_rows * spacing_y
```

### Paramètres granulaires

```python
r_min = 0.05
r_max = 0.15
ratio = r_max / r_min
lx_box = 4.0
ly_box = 4.0
nb_particules = 200
```

### Coordonnées relatives à un avatar existant

```python
x_ref = avatar[0].x
y_ref = avatar[0].y
x_cible = x_ref + 1.0
y_cible = y_ref + 0.5
dist = sqrt((avatar[1].x - avatar[0].x)**2 + (avatar[1].y - avatar[0].y)**2)
```

### Paramètres matériaux

```python
rho = material['granite'].density
E = material['acier']['young']
nu = material['acier']['nu']
mu = 0.3                        # Coefficient de Coulomb
K = E / (3 * (1 - 2 * nu))     # Module de compressibilité
G = E / (2 * (1 + nu))         # Module de cisaillement
```

### Statistiques sur les avatars

```python
nb_total = len(avatar)
nb_granulo = len(avatars_by_origin('granulo'))
nb_manuels = len(avatars_by_origin('manual'))
rayon_moyen = sum(av.radius for av in avatars_by_type('rigidDisk')) / max(1, nb_total)
x_centre_masse = sum(av.x for av in avatar) / max(1, nb_total)
```