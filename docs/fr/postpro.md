# Post-traitement (PostPro)

L'onglet **Post-Pro**  définit les **commandes de post-traitement** qui seront incluses dans la DATBOX et exécutées par LMGC90 pendant le calcul. Chaque commande demande à LMGC90 d'écrire des fichiers de sortie à une fréquence donnée, permettant ensuite l'analyse et la visualisation des résultats.

![](captures/postpro.JPG)

---

## Principe de fonctionnement

Une **commande PostPro** (`PostProCommand`) associe un **nom de commande** pylmgc90 à une **fréquence d'écriture** (`step`) et, optionnellement, à une **cible** (avatar unique ou groupe). L'appel pylmgc90 correspondant est :

```python
# Sans cible (commande globale) :
posts.addCommand(pre.postpro_command(name='SOLVER INFORMATIONS', step=1))

# Avec cible avatar :
posts.addCommand(pre.postpro_command(
    name='BODY TRACKING',
    step=10,
    rigid_set=[bodies[3]]
))

# Avec cible groupe :
posts.addCommand(pre.postpro_command(
    name='TORQUE EVOLUTION',
    step=5,
    rigid_set=[bodies[i] for i in group_granulo_box2d]
))
```

La structure `PostProCommand` dans le projet stocke trois champs : `name`, `step` et optionnellement `target_type` / `target_value`.

---

## Interface de l'onglet

L'onglet est organisé en deux zones :

- **Liste des commandes** (en haut) : tableau de toutes les commandes enregistrées. Chaque ligne affiche le nom de la commande, la fréquence (`step=N`) et la cible (`Global`, `Avatar #N` ou `Groupe: nom`). Double-clic pour éditer.
- **Formulaire de création / modification** (en bas) : trois champs simples.

---

## Champs du formulaire

| Champ | Description | Valeur par défaut |
|-------|-------------|-------------------|
| **Commande** | Nom de la commande de post-traitement pylmgc90. Sélectionner dans la liste déroulante. | `SOLVER INFORMATIONS` |
| **Fréquence (step)** | Écriture tous les `step` pas de calcul. `step=1` = écriture à chaque pas, `step=100` = tous les 100 pas. | `1` |
| **Cible** | `Global` (toute la simulation), `Avatar` (index numérique) ou `Groupe` (nom de groupe). | `Global` |

---

## Commandes disponibles

### Qualité numérique — pas de cible requise

Ces commandes sont **globales** et ne nécessitent pas de `rigid_set`. Elles s'appliquent à l'ensemble de la simulation.

| Commande | Description | Fichiers de sortie |
|----------|-------------|-------------------|
| **`SOLVER INFORMATIONS`** | Informations du solveur de contact à chaque pas : nombre d'itérations, résidu, temps de calcul. Indispensable pour vérifier la **convergence** du schéma de contact. | `OUTBOX/solver_informations.dat` |
| **`VIOLATION EVOLUTION`** | Évolution de la violation (interpénétration résiduelle) moyenne et maximale entre corps. Mesure l'**erreur** numérique de non-pénétration. | `OUTBOX/violation_evolution.dat` |
| **`KINETIC ENERGY`** | Énergie cinétique totale du système à chaque pas. Utile pour suivre la dissipation d'énergie et détecter les instabilités. | `OUTBOX/kinetic_energy.dat` |
| **`CONTACT ENERGY`** | Énergie dissipée par les contacts (frottement + restitution). | `OUTBOX/contact_energy.dat` |
| **`STRAIN ENERGY`** | Énergie de déformation stockée dans le système. Pour les corps déformables EF. | `OUTBOX/strain_energy.dat` |
etc,
---

### Suivi de corps — cible requise (`rigid_set`)

Ces commandes écrivent des informations sur un **corps spécifique** ou un **groupe d'avatars**. Une cible (`target_type` + `target_value`) est obligatoire.

| Commande | Description | Données extraites | Fichiers de sortie |
|----------|-------------|-------------------|--------------------|
| **`BODY TRACKING`** | Suivi complet de la position, vitesse et accélération d'un corps au cours du temps. La commande la plus utilisée pour analyser la trajectoire d'un avatar. | Position (x, y, z), vitesse (vx, vy, vz), accélération, angle et vitesse angulaire | `OUTBOX/body_tracking.dat` |
| **`TORQUE EVOLUTION`** | Évolution du moment (couple) appliqué sur le corps ou le groupe. | Composantes du couple selon X, Y, Z | `OUTBOX/torque_evolution.dat` |
| **`MOMENTUM EVOLUTION`** | Évolution de la quantité de mouvement du corps ou du groupe. | Quantité de mouvement (px, py, pz) | `OUTBOX/momentum_evolution.dat` |

---

### Commandes additionnelles

| Commande | Description |
|----------|-------------|
| **`WORK EVOLUTION`** | Travail des forces extérieures appliquées au cours du temps. |
| **`DISSIPATED ENERGY`** | Énergie dissipée totale (contact + amortissement). |

---

## Cible des commandes

### Global _(pas de `rigid_set`)_

La commande s'applique à l'ensemble du système. Utiliser pour `SOLVER INFORMATIONS`, `VIOLATION EVOLUTION`, `KINETIC ENERGY`.

```python
pre.postpro_command(name='SOLVER INFORMATIONS', step=1)
```

### Avatar (index unique)

La commande surveille un corps spécifique identifié par son index dans la liste des avatars (0-based).

```python
pre.postpro_command(name='BODY TRACKING', step=10, rigid_set=[bodies[3]])
```

Dans l'interface : sélectionner **Avatar** comme type de cible, puis saisir l'index (ex : `3`).

### Groupe (ensemble d'avatars)

La commande surveille tous les corps d'un groupe nommé (boucle, granulométrie, maçonnerie…).

```python
pre.postpro_command(
    name='TORQUE EVOLUTION',
    step=5,
    rigid_set=[bodies[i] for i in group_granulo_box2d]
)
```

Dans l'interface : sélectionner **Groupe** comme type de cible, puis choisir le groupe dans la liste déroulante.

> Tous les groupes définis dans le projet (boucles, granulométrie, maçonnerie) apparaissent automatiquement dans la liste.

---

## Fréquence d'écriture (`step`)

Le paramètre `step` contrôle la fréquence d'écriture des fichiers de résultats.

| Valeur `step` | Comportement | Usage |
|---------------|-------------|-------|
| `1` | Écriture à chaque pas de calcul | Analyse fine, débogage, petits modèles |
| `10` | Écriture tous les 10 pas | Bon compromis précision / taille fichier |
| `100` | Écriture tous les 100 pas | Grandes simulations longues durées |
| `step_total / 1000` | ~1000 points dans le fichier | Règle empirique pour des courbes lisses |

> **Impact sur les performances :** un `step=1` avec `BODY TRACKING` sur un grand groupe peut générer des fichiers de plusieurs gigaoctets et ralentir le calcul. Adapter la fréquence à la durée et à la précision requise.

---

## Gestion des commandes

### Créer une commande

Remplir le formulaire et cliquer sur **✅ Ajouter la Commande**. La commande est créée via `add_postpro_command()` qui :

1. Résout la cible (`rigid_set`) en listes d'objets pylmgc90.
2. Crée l'objet `pre.postpro_command(name, step, rigid_set)`.
3. L'ajoute au conteneur `_postpro_container` via `addCommand()`.
4. Sauvegarde dans `state.postpro_commands`.
5. Émet le signal `command_added` → `_refresh_all()`.

### Modifier une commande

Double-cliquer dans la liste pour charger les valeurs dans le formulaire. Modifier et cliquer sur **💾 Mettre à jour**. `update_postpro_command()` reconstruit l'ensemble du conteneur postpro (même comportement que pour les visibilités — limitation pylmgc90).

### Supprimer une commande

Sélectionner et cliquer sur **🗑️ Supprimer**. La commande est retirée de `state.postpro_commands` via `remove_postpro_command()`. Le signal `command_deleted` est émis.

---

## Visualisation dans l'arbre du modèle

Les commandes postpro sont affichées dans l'arbre du modèle (panneau gauche) sous le nœud **Post-Processing**, avec pour chaque commande :

- Son nom (ex. `BODY TRACKING`)
- Sa fréquence (`step=10`)
- Sa cible (`Global`, `Avatar #3` ou `Groupe: granulo_box2d`)

Double-cliquer sur une commande dans l'arbre ouvre directement l'onglet PostPro en mode édition (`load_for_edit(postpro)`).

---

## Script Python généré

```python
# Post-traitement

# Commande globale
post_cmd_0 = pre.postpro_command(
    name='SOLVER INFORMATIONS',
    step=1
)
posts.addCommand(post_cmd_0)

# Commande avec cible avatar
post_cmd_1 = pre.postpro_command(
    name='BODY TRACKING',
    step=10,
    rigid_set=[bodies[3]]
)
posts.addCommand(post_cmd_1)

# Commande avec cible groupe
post_cmd_2 = pre.postpro_command(
    name='TORQUE EVOLUTION',
    step=5,
    rigid_set=[bodies[i] for i in group_granulo_box2d]
)
posts.addCommand(post_cmd_2)
```

Le conteneur `posts` est passé à `pre.writeDatbox(post=posts, ...)` lors de la génération de la DATBOX.

---

## Lecture des résultats

Les fichiers de sortie sont écrits dans le répertoire `OUTBOX/` du projet LMGC90 pendant le calcul. Chaque fichier est un fichier texte (colonnes séparées par des espaces) dont le format dépend de la commande :

| Commande | Format typique | Colonnes |
|----------|---------------|---------|
| `BODY TRACKING` | Texte, N colonnes | `t`, `x`, `y`, `z`, `vx`, `vy`, `vz`, `theta`, `omega` |
| `SOLVER INFORMATIONS` | Texte | `t`, `iter`, `residual`, `cpu_time` |
| `VIOLATION EVOLUTION` | Texte | `t`, `mean_violation`, `max_violation` |
| `KINETIC ENERGY` | Texte | `t`, `Ec` |
| `TORQUE EVOLUTION` | Texte | `t`, `Mx`, `My`, `Mz` |

Ces fichiers peuvent être lus et tracés directement avec Python (numpy, matplotlib) ou avec l'outil de visualisation intégré de LMGC90.

---

## Exemple d'utilisation — bielle-manivelle

Pour une simulation de bielle-manivelle, configurer les commandes suivantes :

| # | Commande | Step | Cible | Objectif |
|---|----------|------|-------|---------|
| 0 | `SOLVER INFORMATIONS` | `1` | Global | Vérifier la convergence |
| 1 | `VIOLATION EVOLUTION` | `1` | Global | Contrôler l'interpénétration |
| 2 | `BODY TRACKING` | `10` | Avatar #0 (manivelle) | Trajectoire angulaire |
| 3 | `BODY TRACKING` | `10` | Avatar #2 (coulisseau) | Déplacement linéaire |
| 4 | `KINETIC ENERGY` | `1` | Global | Bilan énergétique |

![Exemple onglet PostPro](captures/postpro.JPG)

---


## Remarques importantes

**Reconstruction lors de la modification :** comme pour les tables de visibilité, toute modification d'une commande entraîne la reconstruction complète du conteneur `_postpro_container`. Ceci est transparent pour l'utilisateur.

**Les fichiers de sortie ne sont écrits que pendant le calcul.** La génération de la DATBOX et du script Python n'écrit pas de résultats — le calcul doit être lancé depuis l'onglet Calcul (`F5`) pour que les fichiers `OUTBOX/` soient créés.

**Step et durée de simulation :** s'assurer que `step` est inférieur au nombre total de pas de calcul. Une commande avec `step=100` dans une simulation de 50 pas ne produira aucune sortie.

**Cohérence des indices d'avatars :** les indices dans `target_value` référencent la position dans `state.avatars` au moment de la création. Si des avatars sont supprimés ou réordonnés après la création d'une commande, les indices peuvent devenir incorrects. Préférer les groupes nommés pour les commandes sur plusieurs corps.





# Post-traitement

Définition des sorties pour LMGC90 qui vont à extraire et analyser vos calculs.

## Commandes disponibles
### 1.Vérifier la qualité numérique 
- SOLVER INFORMATIONS : pour s'assurer la convergence
- VIOLATION EVOLUTION : mesure "l'erreur" d'interpénétration moyenne
- TORQUE EVOLUTION (sur avatar/groupe) : 
- BODY TRACKING (suivi de corps)
- KINETIC ENERGY, etc.

## Fonctionnalités
-  step : étape 
-  rigid_set : avatar ou groupr d'avatars

## Exemple : 
Pour rajouter une commande du postpro, il faut se rendre dans l'onglet "PostPro", puis de choisir la commande voulue dans mon cas "BODY TRACKING", puis de renseigner l'étape, et de cliquer sur le bouton **"Ajouter la Commande"** 
![](captures/postpro.JPG)