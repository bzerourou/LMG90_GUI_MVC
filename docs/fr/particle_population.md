# ParticlePopulation — Architecture SoA des avatars de masse

> Complément au [guide développeur](dev.md) · introduit progressivement (étapes 1–7 du refactor) · stable depuis v0.4.8 pour granulo / boucles éligibles.

---

## 1. Pourquoi SoA ?

| Approche | Structure | Cas d’usage | Limite pratique |
|----------|-----------|-------------|-----------------|
| **AoS** (`List[Avatar]`) | Un objet Python par particule | Murs, avatars manuels, déformables, édition unitaire | ~1 500–3 000 avatars avant ralentissement UI |
| **SoA** (`ParticlePopulation`) | Arrays numpy homogènes | Granulo, boucles massives, factory | Dizaines / centaines de milliers de particules |

**AoS (Array of Structures)** = liste d’objets riches, chacun avec tous ses champs.  
**SoA (Structure of Arrays)** = une structure unique qui détient des colonnes numpy (`centers`, `radii`) pour toute la population.

`ParticlePopulation` **ne remplace pas** `Avatar` : les deux coexistent dans `ProjectState`.

```
ProjectState
├── avatars: List[Avatar]                    # AoS — édition fine
└── particle_populations: List[ParticlePopulation]  # SoA — volumes
```

---

## 2. Modèle de données

Fichier : `src/core/particle_population.py`

### 2.1 Champs

| Champ | Type | Rôle |
|-------|------|------|
| `population_id` | `str` | Identifiant stable (`pop_<uuid>`) — **une id par population**, jamais par particule |
| `avatar_type` | `AvatarType` | Homogène sur toute la population (`RIGID_DISK` ou `RIGID_SPHERE` pour l’instant) |
| `material_name` | `str` | Matériau unique |
| `model_name` | `str` | Modèle unique |
| `color` | `str` | Couleur LMGC90 (5 caractères) |
| `origin` | `AvatarOrigin` | `GRANULO`, `LOOP`, … |
| `dimension` | `int` | 2 ou 3 (dérivé de `centers.shape[1]`) |
| `centers` | `np.ndarray (N, dim) float64` | Positions |
| `radii` | `np.ndarray (N,) float64` | Rayons |
| `group_name` | `Optional[str]` | Groupe UI / script |

### 2.2 Construction validée

Toujours passer par `ParticlePopulation.create(...)` plutôt que le constructeur nu :

```python
from src.core.particle_population import ParticlePopulation
from src.core.models import AvatarType, AvatarOrigin
import numpy as np

pop = ParticlePopulation.create(
    avatar_type=AvatarType.RIGID_DISK,
    material_name="TDURx",
    model_name="rigid",
    color="BLUEx",
    origin=AvatarOrigin.GRANULO,
    centers=np.array([[0.0, 0.0], [0.2, 0.0]], dtype=np.float64),
    radii=np.array([0.05, 0.06], dtype=np.float64),
    group_name="depot_box2d",
)
```

Validations effectuées :
- `centers` 2D, dernière dimension ∈ {2, 3}
- `radii` 1D, même longueur que `centers`
- tous les rayons strictement positifs

### 2.3 Identifiants de particules

Les particules **n’ont pas** d’`avatar_id` stocké. Un id dérivé est calculé à la demande :

```python
pop.particle_avatar_id(i)           # → "pop_abc123:42"
pop.index_from_particle_avatar_id("pop_abc123:42")  # → 42
```

Compatible avec le système d’ids stables existant tant que la population n’est pas régénérée.

### 2.4 Vue individuelle à la demande

```python
avatar = pop.as_avatar_view(i)  # matérialise UN Avatar ponctuel
```

À utiliser uniquement pour édition / info UI / DOF ciblé. **Ne jamais** boucler `as_avatar_view` sur toute la population — c’est exactement ce que SoA évite.

### 2.5 Stats utiles

```python
len(pop)                 # N
pop.bounds()             # (min_xyz, max_xyz) — cadrage caméra viewer
pop.radius_stats()       # {"min", "max", "mean"}
```

---

## 3. Sérialisation à deux niveaux

Fichiers : `particle_population.py` + `particle_population_io.py` + `serializers.py`

### 3.1 Forme autonome (mémoire / tests / rétrocompat)

```python
d = pop.to_dict()                    # meta + centers/radii en listes Python
pop2 = ParticlePopulation.from_dict(d)
```

Utilisée en tests, duplication en mémoire, et lecture des projets sauvegardés **avant** l’introduction du sidecar binaire.

### 3.2 Forme sidecar (projets `.lmgc90`)

| Fichier | Contenu |
|---------|---------|
| `projet.lmgc90` (JSON) | Métadonnées via `to_meta_dict()` (`population_id`, type, matériau, `n_particles`, …) — **sans** les arrays |
| `projet.populations.npz` | Arrays compressés : `"<population_id>__centers"`, `"<population_id>__radii"` |

```python
from src.core.particle_population_io import (
    sidecar_path_for, save_populations_sidecar, load_populations_sidecar,
)

npz_path = sidecar_path_for(Path("mon_projet.lmgc90"))
# → mon_projet.populations.npz

save_populations_sidecar(state.particle_populations, npz_path)
arrays_by_id = load_populations_sidecar(npz_path)
# { "pop_xxx": (centers, radii), ... }

pop = ParticlePopulation.from_meta_and_arrays(meta, centers, radii)
```

**Règles :**
- populations vides → aucun `.npz` écrit ; un ancien sidecar orphelin est **supprimé**
- sidecar absent au chargement → warning dans `state.load_warnings`, pas d’échec fatal du projet
- un seul `.npz` regroupe **toutes** les populations du projet

---

## 4. Pont pylmgc90

Fichier : `src/core/pylmgc_bridge.py`

```python
bodies = LMGC90Bridge.create_avatars_from_population(pop, model_obj, material_obj)
# → List[pre.rigidDisk | pre.rigidSphere]
```

- Accès **direct** aux arrays numpy (pas de dataclass `Avatar` intermédiaire)
- Un appel `pre.rigidDisk` / `pre.rigidSphere` par particule (limite structurelle de l’API pylmgc90)
- Types supportés aujourd’hui : **`RIGID_DISK`** et **`RIGID_SPHERE` uniquement**

Toute autre géométrie reste sur le chemin AoS (`create_avatar`).

---

## 5. Intégration contrôleur / UI

### 5.1 État projet

Dans `ProjectState` (`models.py`) :

```python
particle_populations: List[Any] = field(default_factory=list)  # List[ParticlePopulation]
populations_groups: Dict[str, List[str]] = field(default_factory=dict)
# group_name → list of population_ids
```

### 5.2 Chemins d’activation UI

| Point d’entrée | Case à cocher / option | Mixin / module |
|----------------|------------------------|----------------|
| Onglet Granulométrie | « Créer comme ParticlePopulation (SoA, stockage compact) » | `granulo_mixin.py` |
| Assistant granulométrie | idem | `granulo_wizard.py` |
| Boucles (target avatar) | « Créer comme ParticlePopulation (SoA, …) » | `for_loops_mixin.py` / `loop_tab.py` |

Si la case est décochée (ou absente) → chemin **AoS** classique (`List[Avatar]`).

### 5.3 Reconstruction au chargement

Dans `base_mixin` / rebuild projet :

1. Matériaux, modèles, avatars MANUAL, boucles AoS, granulo AoS…
2. **Régénération / rechargement des populations SoA** depuis JSON meta + sidecar `.npz`
3. Création des corps pylmgc90 via `create_avatars_from_population` quand nécessaire (DATBOX, calcul)

Les populations ne sont **pas** re-déposées physiquement au load si le sidecar est présent : on recharge les arrays tels quels.

### 5.4 Viewer 3D

`viewer_3d.py` / `viewer_tab.py` acceptent un mélange :

```python
items = [*state.avatars, *state.particle_populations]
for item in items:
    if isinstance(item, ParticlePopulation):
        for i in range(len(item)):
            # rendu depuis centers[i], radii[i]
    else:
        # Avatar classique
```

Le compteur d’éléments affiché somme `len(pop)` pour les populations.

---

## 6. Flux typique — granulo SoA

```
UI (granulo_tab / wizard)
  │ use_population = True
  ▼
GranuloGenerator.generate(config)
  → (nb, centers ndarray, radii ndarray)
  ▼
ParticlePopulation.create(..., centers, radii, origin=GRANULO)
  ▼
state.particle_populations.append(pop)
state.populations_groups[group] = [pop.population_id]
  ▼
(optionnel) LMGC90Bridge.create_avatars_from_population → _pylmgc_bodies
  ▼
Sauvegarde projet
  → meta dans .lmgc90
  → arrays dans .populations.npz
```

---

## 7. Comparaison AoS vs SoA (implémentation)

| Critère | AoS `Avatar` | SoA `ParticlePopulation` |
|---------|--------------|---------------------------|
| Stockage mémoire | 1 objet Python + refs par particule | 2 arrays contigus + meta |
| Création GUI | `add_avatar` × N → N signaux si pas batch | 1 objet, 1 signal |
| Édition unitaire | Native | Via `as_avatar_view(i)` uniquement |
| Sérialisation JSON | Liste d’objets | Meta JSON + sidecar `.npz` |
| Types supportés | Tous les `AvatarType` | `RIGID_DISK`, `RIGID_SPHERE` |
| Viewer | 1 actor / avatar (coûteux) | Itération array (plus léger) |
| DOF / postpro ciblé particule | Index avatar | `population_id:i` |

---

## 8. Pièges et conventions

1. **Homogénéité** — une population = un type, un matériau, un modèle, une couleur. Pas de mélange.
2. **Ne pas matérialiser en masse** — interdiction de `for i in range(len(pop)): as_avatar_view(i)` hors cas ponctuel.
3. **Sidecar synchronisé** — toujours écrire le `.npz` en même temps que le `.lmgc90` ; supprimer le sidecar si plus aucune population.
4. **Régénération** — changer les paramètres granulo / boucle SoA régénère une **nouvelle** population (nouvel `population_id`) ; les anciens `pop_xxx:i` deviennent invalides.
5. **Maçonnerie « fast mode »** — ce n’est **pas** du SoA : les briques restent des `Avatar` individuels ; seul le chemin de génération est accéléré.
6. **Extension future** — pour ajouter un type (ex. `RIGID_JONC`), étendre `create_avatars_from_population` et les validateurs d’éligibilité UI (cases à cocher).

---

## 9. Checklist contributeur

- [ ] Nouvelle génération de masse : prévoir un flag `use_population` (défaut raisonnable selon le volume)
- [ ] Éligibilité : type ∈ {RIGID_DISK, RIGID_SPHERE}, matériau/modèle uniques
- [ ] Création uniquement via `ParticlePopulation.create`
- [ ] Append dans `state.particle_populations` + mise à jour `populations_groups`
- [ ] Sauvegarde : `ProjectSerializer` doit appeler `save_populations_sidecar`
- [ ] Chargement : `from_meta_and_arrays` + warning si sidecar manquant
- [ ] Viewer / arbre : gérer `isinstance(..., ParticlePopulation)`
- [ ] Tests unitaires : `create`, `to_dict`/`from_dict`, `to_meta` + sidecar round-trip
- [ ] Documenter le nouveau chemin dans ce fichier et dans `granulometry.md` / `loops.md` si impact utilisateur

---

## 10. Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `src/core/particle_population.py` | Dataclass SoA, validation, vues, sérialisation meta/autonome |
| `src/core/particle_population_io.py` | Sidecar `.populations.npz` |
| `src/core/models.py` | `particle_populations`, `populations_groups` dans `ProjectState` |
| `src/core/serializers.py` | Save/load JSON + sidecar |
| `src/core/pylmgc_bridge.py` | `create_avatars_from_population` |
| `src/controllers/granulo_mixin.py` | Création granulo SoA |
| `src/controllers/for_loops_mixin.py` | Boucles SoA |
| `src/controllers/base_mixin.py` | Rebuild populations au load |
| `src/views/tabs/granulo_tab.py` | Case à cocher SoA |
| `src/views/tabs/loop_tab.py` | Case à cocher SoA |
| `src/gui/dialogs/granulo_wizard.py` | Case à cocher SoA |
| `src/gui/dialogs/viewer_3d.py` | Rendu des populations |
| `src/views/tabs/viewer_tab.py` | Comptage / liste renderables |

---

## 11. Étapes du refactor (référence)

| Étape | Contenu | Statut typique |
|-------|---------|----------------|
| 1 | Structure isolée (`create`, validation, `as_avatar_view`, stats) | Fait |
| 2 | Champs `ProjectState` | Fait |
| 3 | Sidecar `.npz` + meta JSON | Fait |
| 4 | Pont pylmgc90 masse | Fait (DISK/SPHERE) |
| 5 | Granulo UI + mixin | Fait |
| 6 | Boucles / for-loop UI | Fait (éligibilité) |
| 7 | Viewer, arbre, polish, perf | En cours / itératif |

Mettre à jour ce tableau au fil des PR.
