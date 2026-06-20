# Lois de contact

L'onglet **Contact** (`Ctrl+9`) permet de créer, modifier et supprimer les **lois de contact** (`tact_behav`) de pylmgc90. Chaque loi définit le comportement mécanique à la frontière entre deux corps en contact. Une loi doit être créée ici **avant** de pouvoir être référencée dans une table de visibilité (onglet Visibilité).

---

## Principe de fonctionnement

Une **loi de contact** (`ContactLaw`) est un objet pylmgc90 créé par `pre.tact_behav(name, law, ...)`. Elle est identifiée par un nom unique dans le projet et caractérise la physique du contact : frottement, cohésion, rigidité, endommagement…

**Appel pylmgc90 généré :**

```python
law_IQS_CLB = pre.tact_behav(
    name='IQS_CLB',
    law='IQS_CLB',
    fric=0.3
)
tacts.addBehav(law_IQS_CLB)
```

---

## Interface de l'onglet

L'onglet comprend trois zones :

- **Liste des lois** (en haut) : arbre avec colonnes Nom, Type, Friction, Propriétés. Les lois **référencées** par au moins une table de visibilité apparaissent en **vert**. Clic droit pour Modifier, Supprimer ou afficher les Informations.
- **Formulaire de création / modification** (au milieu) : champs qui s'adaptent automatiquement au type choisi.
- **Aide contextuelle** (en bas) : description et liste des paramètres du type sélectionné.

### Boutons

| Bouton | Mode | Action |
|--------|------|--------|
| **✅ Créer Loi** | Création | Valide le formulaire et crée la loi. |
| **💾 Enregistrer Modifications** | Édition | Met à jour la loi sélectionnée. |
| **❌ Annuler** | Édition | Revient au mode création sans sauvegarder. |
| **🔄 Réinitialiser** | Tous | Vide le formulaire et remet les valeurs par défaut. |
| **✏️ Modifier Sélection** | Tous | Charge la loi sélectionnée dans le formulaire. |
| **🗑️ Supprimer Sélection** | Tous | Supprime la loi (avec vérification de référence). |

---

## Champs du formulaire

| Champ | Description |
|-------|-------------|
| **Nom** | Identifiant unique de la loi (20 caractères max). Utilisé dans les tables de visibilité. Défaut : `law01`. |
| **Catégorie** | Filtre le combo Type. Voir les 4 catégories ci-dessous. |
| **Type** | Type de loi pylmgc90. Les champs spécifiques s'affichent/masquent dynamiquement selon le type. |

---

## Les 4 catégories de lois

### Catégorie 1 — Rigide / Rigide

Lois applicables entre deux corps rigides (`RBDY2` / `RBDY3`).

---

#### `IQS_CLB` — Coulomb Inégalité Quasi-Statique _(la plus courante)_

Loi de Coulomb standard. Contact unilatéral avec frottement de Coulomb sec. Approche non-lisse Inégalité Quasi-Statique (IQS).

| Paramètre | Label interface | Description | Défaut |
|-----------|----------------|-------------|--------|
| `fric` | Coefficient de friction | Coefficient de Coulomb μ. La force tangentielle ne peut pas dépasser μ × force normale. | `0.3` |

**Valeurs typiques de `fric` :**

| Matériau | `fric` |
|----------|--------|
| Sable / billes de verre | 0,3 – 0,5 |
| Béton / roches | 0,5 – 0,8 |
| Métaux polis | 0,1 – 0,3 |
| Bois / plastique | 0,3 – 0,6 |
| Sans frottement (glissant) | `0.0` |

**Appel pylmgc90 :**
```python
law = pre.tact_behav(name='loi1', law='IQS_CLB', fric=0.3)
```

---

#### `IQS_CLB_g0` — Coulomb avec jeu initial

Identique à `IQS_CLB` mais initialise le jeu géométrique initial entre contacteurs à `g0=0`. Utile lorsque les corps sont déjà en contact dès `t = 0` (sans interpénétration initiale).

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `fric` | Coefficient de frottement de Coulomb. | `0.3` |

**Applications :** assemblages mécaniques pré-serrés, compression progressive, contacts avec rugosité initiale.

---

#### `IQS_DS_CLB` — Coulomb avec rigidités statique/dynamique

Loi discrète avec deux rigidités de contact distinctes : une rigidité statique (avant glissement) et une dynamique (en glissement).

| Paramètre | Label interface | Description | Défaut |
|-----------|----------------|-------------|--------|
| `fric` | Coefficient de friction | Coefficient de Coulomb. | `0.3` |
| `stfr` | Rigidité de contact statique | Rigidité normale statique (N/m). | `1e8` |
| `dyfr` | Rigidité de contact dynamique | Rigidité normale dynamique (N/m). | `1e8` |

**Applications :** systèmes de freinage (μ_statique > μ_dynamique), glissement de plaques tectoniques, mécanismes avec vibrations auto-induites.

---

#### `IQS_MOHR_DS_CLB` — Mohr-Coulomb avec cohésion

Critère de Mohr-Coulomb incluant une cohésion normale et tangentielle. Permet de modéliser des matériaux avec adhésion initiale (ciment, argile humide).

| Paramètre | Label interface | Description | Défaut |
|-----------|----------------|-------------|--------|
| `fric` | Coefficient de friction | Coefficient de Coulomb μ. | `0.3` |
| `stfr` | Rigidité statique | Rigidité avant rupture de cohésion (N/m). | `1e8` |
| `dyfr` | Rigidité dynamique | Rigidité après rupture (N/m). | `1e8` |
| `cohn` | Cohésion normale | Force d'adhésion en traction (Pa). | `0.0` |
| `coht` | Cohésion tangentielle | Résistance tangentielle additionnelle (Pa). | `0.0` |

**Applications :** géomécanique (argiles, sols cohésifs), matériaux granulaires humides, poudres avec forces de van der Waals.

---

#### `IQS_MAC_CZM` — Zone cohésive MAC (rigide/rigide)

Modèle de zone cohésive Mohr-Coulomb-Allix-Corigliano. Simule la rupture progressive et le délaminage entre corps rigides.

| Paramètre | Label interface | Description | Défaut |
|-----------|----------------|-------------|--------|
| `stfr` | Rigidité statique | Rigidité tangentielle avant endommagement (N/m). | `1e10` |
| `dyfr` | Rigidité dynamique | Rigidité normale avant endommagement (N/m). | `1e10` |
| `cn` | Résistance normale | Résistance à la traction normale (Pa). | `1e6` |
| `ct` | Résistance tangentielle | Résistance au cisaillement (Pa). | `1e6` |
| `b` | Paramètre de mélange | Couplage modes I/II (0 = pur mode I, 1 = équipartition). | `1.0` |
| `w` | Énergie de rupture | Énergie de fracture critique (J/m²). | `0.01` |

**Applications :** rupture de liaisons, fissuration, délaminage composite.

---

#### `RST_CLB` — Restitution + Coulomb

Contact avec coefficient de restitution (chocs élastiques ou partiellement élastiques) et friction de Coulomb.

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `fric` | Coefficient de frottement de Coulomb. | `0.3` |

**Applications :** impact de billes, rebonds, chocs mécaniques.

---

### Catégorie 2 — Rigide / Déformable (ou Déf / Déf)

Lois applicables entre un corps rigide (`RBDY2`/`RBDY3`) et un corps déformable EF (`MAILx`), ou entre deux corps déformables.

---

#### `GAP_SGR_CLB` — Contact jeu + Coulomb (rigide/déformable)

Loi standard pour contact rigide/déformable. Gère le jeu initial entre la surface rigide et le maillage EF.

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `fric` | Coefficient de frottement de Coulomb. | `0.3` |

**Applications :** contact outil/pièce, frappe, indentation, compression EF.

---

#### `GAP_SGR_CLB_g0` — GAP avec initialisation à g0

Identique à `GAP_SGR_CLB` avec initialisation du jeu à zéro. Utiliser si les corps sont initialement en contact tangent.

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `fric` | Coefficient de frottement de Coulomb. | `0.3` |

---

#### `GAP_MOHR_DS_CLB` — Mohr-Coulomb jeu (rigide/déformable)

Critère de Mohr-Coulomb avec gestion du jeu pour contact rigide/déformable.

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `fric` | Coefficient de Coulomb. | `0.3` |
| `stfr` | Rigidité statique (N/m). | `1e8` |
| `dyfr` | Rigidité dynamique (N/m). | `1e8` |
| `cohn` | Cohésion normale (Pa). | `0.0` |
| `coht` | Cohésion tangentielle (Pa). | `0.0` |

---

#### `MAC_CZM` — Zone cohésive MAC (rigide/déformable ou déf/déf)

Modèle de zone cohésive MAC appliqué aux interfaces rigide/déformable. Mêmes paramètres que `IQS_MAC_CZM`.

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `stfr`, `dyfr` | Rigidités (N/m). | `1e10` |
| `cn`, `ct` | Résistances normale et tangentielle (Pa). | `1e6` |
| `b` | Paramètre de mélange. | `1.0` |
| `w` | Énergie de rupture (J/m²). | `0.01` |

---

#### `MAL_CZM` — Zone cohésive MAL (rigide/déformable ou déf/déf)

Variante du modèle CZM basée sur la formulation MAL (Mixed Augmented Lagrangian). Mêmes paramètres que `MAC_CZM`.

---

### Catégorie 3 — Point / Point

Lois applicables entre contacteurs ponctuels (`PT2Dx`, `PT3Dx`, nœuds EF). Modélisent des liaisons filaires ou des barres discrètes.

---

#### `ELASTIC_WIRE` — Câble élastique

Lien actif uniquement en **traction** (câble inextensible dans un sens). Modèle de câble simple.

| Paramètre | Label interface | Description | Défaut |
|-----------|----------------|-------------|--------|
| `stiffness` | Rigidité axiale | Rigidité EA du câble (N). | `1e6` |
| `prestrain` | Pré-déformation | Pré-tension initiale (adimensionnel, ex. `0.01` = 1 %). | `0.0` |

**Applications :** câbles de suspension, tirants d'ancrage, renforts fibreux.

---

#### `BRITTLE_ELASTIC_WIRE` — Câble élastique fragile

Câble élastique qui se rompt de façon fragile (sans déformation plastique) lorsque la contrainte dépasse `sigc`.

| Paramètre | Label interface | Description | Défaut |
|-----------|----------------|-------------|--------|
| `stiffness` | Rigidité axiale | Rigidité EA du câble (N). | `1e6` |
| `prestrain` | Pré-déformation | Pré-tension initiale. | `0.0` |
| `sigc` | Résistance à la rupture | Contrainte maximale avant rupture fragile (Pa). | `1e6` |

**Applications :** fibres fragiles, fils de verre, rupture de renfort.

---

#### `ELASTIC_ROD` — Barre élastique

Barre rigide pouvant travailler en **traction et en compression** (contrairement au câble). Modèle de barre linéaire.

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `stiffness` | Rigidité axiale EA (N). | `1e6` |
| `prestrain` | Pré-déformation initiale. | `0.0` |

**Applications :** structures treillis, liaisons rigides point à point, raidisseurs.

---

#### `VOIGT_ROD` — Barre visco-élastique de Voigt

Barre avec comportement visco-élastique (ressort + amortisseur en parallèle — modèle de Kelvin-Voigt).

| Paramètre | Label interface | Description | Défaut |
|-----------|----------------|-------------|--------|
| `stiffness` | Rigidité axiale | Rigidité du ressort EA (N). | `1e6` |
| `viscosity` | Viscosité | Coefficient d'amortissement visqueux (N·s). | `1e3` |
| `prestrain` | Pré-déformation | Pré-tension initiale. | `0.0` |

**Applications :** amortisseurs, structures avec dissipation visqueuse, modèles de sol visco-élastique.

---

### Catégorie 4 — Toutes (any / any)

Lois universelles applicables quelle que soit la paire de contacteurs.

---

#### `COUPLED_DOF` — Couplage de degrés de liberté

Couplage parfait (saut de vitesse et de déplacement nul à l'interface). Liaison cinématique rigide.

**Aucun paramètre requis.**

**Applications :** liaison parfaite entre deux corps, couplage de DDL dans les assemblages multi-corps.

---

#### `NORMAL_COUPLED_DOF` — Couplage en direction normale

Couplage uniquement dans la direction normale au contact. Permet un glissement tangentiel libre.

**Aucun paramètre requis.**

---

#### `ELASTIC_REPELL_CLB` — Répulsion élastique + Coulomb

Contact mou par pénalisation élastique en direction normale, avec frottement de Coulomb. Méthode de régularisation (alternative aux lois IQS strictes).

| Paramètre | Label interface | Description | Défaut |
|-----------|----------------|-------------|--------|
| `fric` | Coefficient de friction | Coefficient de Coulomb. | `0.3` |
| `Kn` | Rigidité normale | Rigidité de pénalité normale (N/m). | `1e8` |

**Applications :** contacts mous, pénalisation douce, modèles avec interpénétration contrôlée.

---

## Tableau récapitulatif des 18 lois

| Loi | Catégorie | Paramètres | Usage principal |
|-----|-----------|-----------|-----------------|
| `IQS_CLB` | Rig/Rig | `fric` | Contact granulaire standard |
| `IQS_CLB_g0` | Rig/Rig | `fric` | Contact avec jeu initial nul |
| `IQS_DS_CLB` | Rig/Rig | `fric`, `stfr`, `dyfr` | Frottement statique/dynamique |
| `IQS_MOHR_DS_CLB` | Rig/Rig | `fric`, `stfr`, `dyfr`, `cohn`, `coht` | Matériaux cohésifs |
| `IQS_MAC_CZM` | Rig/Rig | `stfr`, `dyfr`, `cn`, `ct`, `b`, `w` | Rupture, délaminage |
| `RST_CLB` | Rig/Rig | `fric` | Chocs avec restitution |
| `GAP_SGR_CLB` | Rig/Déf | `fric` | Contact outil/pièce EF |
| `GAP_SGR_CLB_g0` | Rig/Déf | `fric` | Contact EF avec jeu nul |
| `GAP_MOHR_DS_CLB` | Rig/Déf | `fric`, `stfr`, `dyfr`, `cohn`, `coht` | Interface cohésive EF |
| `MAC_CZM` | Rig/Déf | `stfr`, `dyfr`, `cn`, `ct`, `b`, `w` | Zone cohésive EF |
| `MAL_CZM` | Rig/Déf | `stfr`, `dyfr`, `cn`, `ct`, `b`, `w` | Zone cohésive MAL |
| `ELASTIC_WIRE` | Pt/Pt | `stiffness`, `prestrain` | Câble (traction seule) |
| `BRITTLE_ELASTIC_WIRE` | Pt/Pt | `stiffness`, `prestrain`, `sigc` | Câble fragile |
| `ELASTIC_ROD` | Pt/Pt | `stiffness`, `prestrain` | Barre élastique |
| `VOIGT_ROD` | Pt/Pt | `stiffness`, `viscosity`, `prestrain` | Barre visco-élastique |
| `COUPLED_DOF` | Any/Any | _(aucun)_ | Liaison rigide parfaite |
| `NORMAL_COUPLED_DOF` | Any/Any | _(aucun)_ | Couplage normal seul |
| `ELASTIC_REPELL_CLB` | Any/Any | `fric`, `Kn` | Contact mou par pénalité |

---

## Gestion des lois

### Créer une loi

Remplir le formulaire et cliquer sur **✅ Créer Loi**. La loi est créée via `add_contact_law()` qui appelle `LMGC90Bridge.create_contact_law()` → `pre.tact_behav(...)` → `tacts.addBehav(...)`. Le signal `law_created` est émis → `_refresh_all()`. Les lois créées sont stockées dans `state.contact_laws` (liste de `ContactLaw`) et classifiées par `ContactLawType` (enum) et `CONTACT_LAW_CATEGORIES` (dict catégorie → lois).

### Modifier une loi

Double-cliquer dans la liste ou cliquer sur **✏️ Modifier Sélection**. Le formulaire passe en mode édition (bouton ✅ remplacé par 💾). Modifier les valeurs et cliquer sur **💾 Enregistrer Modifications** (`update_contact_law()`). Appuyer sur **❌ Annuler** pour revenir au mode création sans sauvegarder.

> **Renommage :** renommer une loi met automatiquement à jour le champ `behavior_name` de toutes les tables de visibilité qui y font référence.

### Supprimer une loi

Sélectionner et cliquer sur **🗑️ Supprimer Sélection** (`remove_contact_law()`). Si la loi est référencée par une ou plusieurs tables de visibilité, un avertissement liste les références et bloque la suppression. Supprimer d'abord les tables de visibilité concernées.

### Informations sur une loi

Clic droit → **ℹ️ Informations** affiche une boîte de dialogue avec le type, tous les paramètres et la liste des tables de visibilité qui l'utilisent.

---

## Indicateur visuel dans la liste

| Couleur du nom | Signification |
|----------------|--------------|
| **Vert** | Loi référencée par au moins une table de visibilité |
| Noir (normal) | Loi non encore référencée |

---

## Remarques importantes

**Cohérence avec la table de visibilité :** la loi choisie doit être compatible avec les types de corps/contacteurs de la table de visibilité. Une loi `GAP_SGR_CLB` ne fonctionnera pas avec une paire `RBDY2/DISKx — RBDY2/DISKx` (rigide/rigide) — utiliser `IQS_CLB` dans ce cas.

**Cohérence avec le détecteur de contact :** le type de loi doit correspondre au détecteur activé dans l'onglet Calcul. Par exemple, `ELASTIC_WIRE` nécessite le détecteur `PT2Lx` (point/ligne) ou similaire.

**Valeurs numériques :** les champs acceptent la notation scientifique Python (`1e8`, `1e-3`, `3.14e6`). Les valeurs sont évaluées au moment de la création de la loi.

**Suppression protégée :** une loi utilisée par au moins une table de visibilité ne peut pas être supprimée directement. Cette protection évite les erreurs de référence dans le projet.
