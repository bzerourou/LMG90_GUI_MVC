# Tables de visibilité

L'onglet **Visibilité** (`Ctrl+9`) permet de définir les **tables de visibilité** (`see_table`) de pylmgc90 : chaque règle déclare quels contacteurs peuvent se détecter mutuellement et avec quelle loi de contact. C'est une étape **obligatoire** avant de générer la DATBOX — sans table de visibilité, aucune interaction de contact n'est calculée.

![](captures/table_visibilite.JPG)

---

## Principe de fonctionnement

Une **table de visibilité** (`see_table`) est le mécanisme par lequel pylmgc90 sait quels corps doivent être testés pour la détection de contact. Elle met en relation un **corps candidat** (peut être pénétré) et un **corps antagoniste** (jamais pénétré), en précisant pour chaque paire la couleur des contacteurs impliqués et la loi de contact à appliquer.

**Appel pylmgc90 généré :**

```python
see_0 = pre.see_table(
    CorpsCandidat='RBDY2',
    candidat='DISKx',
    colorCandidat='BLUEx',
    CorpsAntagoniste='RBDY2',
    antagoniste='DISKx',
    colorAntagoniste='BLUEx',
    behav=law_IQS_CLB,
    alert=0.1
)
sees.addSeeTable(see_0)
```

La structure `VisibilityRule` dans le projet stocke exactement ces 8 paramètres.

---

## Interface de l'onglet

L'onglet est divisé en deux zones :

- **Liste des règles** (en haut) : tableau de toutes les tables de visibilité définies dans le projet, avec corps candidat, contacteur, couleurs, corps antagoniste, loi et distance d'alerte. Double-clic pour éditer.
- **Formulaire de création / modification** (en bas) : 8 champs correspondant aux paramètres de `pre.see_table`.

---

## Champs du formulaire

### Corps candidat

| Champ | Description | Valeurs courantes |
|-------|-------------|-------------------|
| **Corps candidat** (`CorpsCandidat`) | Type du corps portant le contacteur candidat. | `RBDY2` (corps rigide 2D), `RBDY3` (corps rigide 3D), `MAILx` (corps déformable EF) |
| **Contacteur candidat** (`candidat`) | Forme du contacteur sur le corps candidat. Doit correspondre au shape déclaré dans l'onglet Avatar vide. | Voir tableau des contacteurs ci-dessous |
| **Couleur candidat** (`colorCandidat`) | Code couleur LMGC90 à 5 caractères du contacteur candidat. **Doit correspondre exactement** à la couleur du contacteur déclaré sur le corps. | `BLUEx`, `REDxx`, `VERTx`, `GRAYx`… |

### Corps antagoniste

| Champ | Description | Valeurs courantes |
|-------|-------------|-------------------|
| **Corps antagoniste** (`CorpsAntagoniste`) | Type du corps portant le contacteur antagoniste. | `RBDY2`, `RBDY3`, `MAILx` |
| **Contacteur antagoniste** (`antagoniste`) | Forme du contacteur antagoniste. | Voir tableau des contacteurs |
| **Couleur antagoniste** (`colorAntagoniste`) | Couleur du contacteur antagoniste. **Doit correspondre** à la couleur du contacteur déclaré sur le corps antagoniste. | `BLUEx`, `REDxx`… |

### Loi et alerte

| Champ | Description | Défaut |
|-------|-------------|--------|
| **Comportement** (`behav`) | Nom de la loi de contact à appliquer pour cette paire. Sélectionner dans la liste déroulante des lois définies dans l'onglet Contact. La loi doit exister avant de créer la règle. | _(première loi disponible)_ |
| **Distance d'alerte** (`alert`) | Distance de détection (m). Deux contacteurs distants de moins de `alert` sont considérés comme potentiellement en contact et sont testés. Plage : 0,001 à 10,0 m. | `0.1 m` |

---

## Types de corps disponibles

| Type | Description | Usage |
|------|-------------|-------|
| `RBDY2` | Corps rigide 2D (`rigidDisk`, `rigidJonc`, `rigidPolygon`…) | Simulations 2D — particules, maçonnerie, mécanismes |
| `RBDY3` | Corps rigide 3D (`rigidSphere`, `rigidPolyhedron`…) | Simulations 3D — sphères, polyèdres |
| `MAILx` | Corps déformable EF (`MESH_DEFORMABLE`) | Interactions rigide/déformable ou déformable/déformable |

---

## Types de contacteurs disponibles

### Contacteurs 2D (pour `RBDY2`)

| Contacteur | Description | Paramètre pylmgc90 |
|------------|-------------|---------------------|
| `DISKx` | Disque circulaire | `r` (rayon) |
| `xKSID` | Disque orienté (anti-disque) | `r` |
| `JONCx` | Jonc elliptique / capsule | `axe1`, `axe2` |
| `POLYG` | Polygone convexe 2D | `nb_vertices`, `vertices` |
| `CLxxx` | Ligne de contact (maçonnerie) | longueur déterminée par la brique |
| `PT2Dx` | Point de contact 2D | — |

### Contacteurs 3D (pour `RBDY3`)

| Contacteur | Description | Paramètre pylmgc90 |
|------------|-------------|---------------------|
| `SPHER` | Sphère | `r` (rayon) |
| `PLANx` | Plan semi-infini | vecteur normal |
| `CYLND` | Cylindre | `r`, longueur |
| `DNLYC` | Demi-cylindre | `r`, longueur |
| `POLYR` | Polyèdre convexe 3D | `vertices` |
| `PT3Dx` | Point de contact 3D | — |

### Contacteurs pour corps déformables (pour `MAILx`)

| Contacteur | Description |
|------------|-------------|
| `CLxxx` | Ligne de contact sur arête EF (2D) |
| `ALpxx` | Ligne de polygone (interface EF 2D) |

---

## Couleurs et correspondance

La couleur (`colorCandidat`, `colorAntagoniste`) est le **critère de filtrage** principal. Seuls les contacteurs portant exactement la couleur déclarée dans la table de visibilité sont testés pour le contact. Cela permet de créer des règles sélectives :

- Faire interagir uniquement les particules bleues entre elles : `colorCandidat='BLUEx'`, `colorAntagoniste='BLUEx'`
- Faire interagir des particules rouges avec un mur gris : `colorCandidat='REDxx'`, `colorAntagoniste='GRAYx'`
- Contact entre disques et plan fixe : `RBDY2/DISKx/BLUEx` ↔ `RBDY3/PLANx/GRAYx`

> **Erreur courante :** si aucune interaction n'est détectée pendant le calcul, vérifier que les couleurs dans la table de visibilité correspondent **exactement** (5 caractères, sensibles à la casse) aux couleurs déclarées sur les contacteurs des avatars.

---

## Distance d'alerte (`alert`)

La distance `alert` détermine la zone de recherche de contact. Deux contacteurs sont mis en liste candidate pour le calcul si la distance entre eux est inférieure à `alert`.

| Situation | Valeur recommandée |
|-----------|-------------------|
| Particules granulaires (r ≈ 0,05 à 0,15 m) | `0.1` à `0.3 m` |
| Maçonnerie (briques standard) | `0.02` à `0.05 m` |
| Grandes structures | 5 à 10 % du rayon maximal |
| Corps déformables EF | Taille caractéristique d'un élément |

> **Trop petite :** certains contacts réels ne sont pas détectés → interpénétration non gérée (très minim ).  
> **Trop grande :** trop de paires candidates → calcul ralenti inutilement.

---

## Gestion des règles

### Créer une règle

Remplir le formulaire et cliquer sur **✅ Créer**. La règle sera créée  :
1. Vérifie que la loi de contact référencée existe dans `_pylmgc_laws`.
2. Crée l'objet `see_table` pylmgc90 via `LMGC90Bridge.create_visibility_rule()`.
3. L'ajoute au conteneur `_visibility_container` (collection `sees`).
4. Sauvegarde dans `state.visibility_rules`.
5. Émet le signal `rule_created` → `_refresh_all()`.

### Modifier une règle

Double-cliquer dans la liste ou sélectionner et cliquer sur **✏️ Modifier**. Après confirmation, `update_visibility_rule()` :
1. Reconstruit **entièrement** le conteneur `_visibility_container` (limitation pylmgc90 — pas de modification in-place d'une see_table existante).
2. Réinsère toutes les règles avec les nouvelles valeurs.
3. Émet le signal `rule_updated` → `_refresh_all()`.

### Supprimer une règle

Sélectionner et cliquer sur **🗑️ Supprimer**. La règle est retirée de `state.visibility_rules` via `remove_visibility_rule()`. Le signal `rule_deleted` est émis.

> **Mise à jour en cascade :** renommer une loi de contact dans l'onglet Contact met à jour automatiquement le champ `behavior_name` de toutes les règles de visibilité qui y font référence.

---

## Règles courantes par type de simulation

### Granulométrie 2D — disques rigides

```
CorpsCandidat    : RBDY2   candidat    : DISKx   colorCandidat    : BLUEx
CorpsAntagoniste : RBDY2   antagoniste : DISKx   colorAntagoniste : BLUEx
behav : IQS_CLB   alert : 0.1
```

### Maçonnerie 2D — briques rigides

```
CorpsCandidat    : RBDY2   candidat    : CLxxx   colorCandidat    : BLUEx
CorpsAntagoniste : RBDY2   antagoniste : CLxxx   colorAntagoniste : BLUEx
behav : IQS_CLB   alert : 0.02
```

### Granulométrie 3D — sphères rigides

```
CorpsCandidat    : RBDY3   candidat    : SPHER   colorCandidat    : BLUEx
CorpsAntagoniste : RBDY3   antagoniste : SPHER   colorAntagoniste : BLUEx
behav : IQS_CLB   alert : 0.1
```

### Rigide / déformable — disque sur maillage EF

```
CorpsCandidat    : RBDY2   candidat    : DISKx   colorCandidat    : BLUEx
CorpsAntagoniste : MAILx   antagoniste : CLxxx   colorAntagoniste : VERTx
behav : GAP_SGR_CLB   alert : 0.05
```

### Corps de types différents — disques et joncs

```
CorpsCandidat    : RBDY2   candidat    : DISKx   colorCandidat    : BLUEx
CorpsAntagoniste : RBDY2   antagoniste : JONCx   colorAntagoniste : REDxx
behav : IQS_CLB   alert : 0.15
```
---

## Lien avec l'assistant de projet

L'**Assistant de projet** (`Ctrl+Shift+N`) propose une page **Visibilité** qui pré-remplit automatiquement la table de visibilité en fonction des choix effectués aux étapes précédentes :

- **Corps** : `RBDY2` (2D) ou `RBDY3` (3D) selon la dimension du projet.
- **Contacteur** : `DISKx` (2D) ou `SPHER` (3D).
- **Couleurs** : synchronisées automatiquement avec la couleur de l'avatar créé à l'étape Avatar.
- **Loi** : la loi créée à l'étape Contact.

Pour des configurations plus complexes (plusieurs types de contacteurs, plusieurs lois), utiliser directement l'onglet Visibilité après la fin de l'assistant.

---

## Remarques importantes

**La loi doit exister avant la règle :** `add_visibility_rule()` vérifie que la loi référencée est présente dans `_pylmgc_laws`. Si la loi est supprimée de l'onglet Contact après la création de la règle, la règle devient invalide et la génération du script échouera. L'onglet Contact avertit si l'on tente de supprimer une loi utilisée par une règle de visibilité.

**Reconstruction complète lors de la modification :** pylmgc90 ne permet pas de modifier une `see_table` existante. La moindre modification d'une règle entraîne la reconstruction complète du conteneur `sees` avec toutes les règles. Ce comportement est transparent pour l'utilisateur mais peut être lent si le projet contient de nombreuses règles.

**Multiplicité des règles :** un projet peut avoir autant de règles de visibilité que nécessaire. Pour un assemblage avec plusieurs populations de particules de couleurs différentes (ex. bleu, rouge, vert), créer une règle par paire de couleurs qui doit interagir. Des populations de couleurs différentes sans règle commune ne se voient pas.

**Détecteur de contact vs table de visibilité :** la table de visibilité déclare *qui* peut interagir. L'onglet Calcul (`Ctrl+8`) configure les *détecteurs de contact* (`DKDKx`, `SPSPx`…) qui déterminent *comment* le contact est résolu. Les deux doivent être cohérents — si une règle déclare `DISKx/DISKx`, le détecteur `DKDKx` doit être activé dans l'onglet Calcul.


