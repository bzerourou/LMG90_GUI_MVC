# LMGC90_GUI — Architecture & Guide du Contributeur

> Version 0.5.0 — Interface graphique pour le code de simulation mécanique LMGC90
> **Cette révision ajoute la documentation du refactor "ParticlePopulation" (architecture SoA)**,
> voir §3.7, §3.8, §4.2, §5.7, §8.5 et l'annexe mises à jour.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Structure des fichiers](#2-structure-des-fichiers)
3. [Couche Core (Modèle)](#3-couche-core-modèle)
4. [Couche Controllers](#4-couche-controllers)
5. [Couche GUI / Views](#5-couche-gui--views)
6. [Couche Utils](#6-couche-utils)
7. [Flux de données](#7-flux-de-données)
8. [Systèmes clés expliqués](#8-systèmes-clés-expliqués)
9. [Cycle de vie d'un projet](#9-cycle-de-vie-dun-projet)
10. [Conventions et patterns](#10-conventions-et-patterns)
11. [Guide de contribution](#11-guide-de-contribution)

---

## 1. Vue d'ensemble

LMGC90_GUI est une application de bureau **PyQt6** suivant le pattern **MVC** (Model-View-Controller). Elle permet de créer des simulations mécaniques LMGC90 via une interface graphique sans écrire de code Python manuellement.

```
┌─────────────────────────────────────────────────────────────────┐
│                          LMGC90_GUI                             │
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │   GUI/Views  │───▶│   Controllers    │───▶│   Core/Model  │  │
│  │   (PyQt6)    │    │  (ProjectController)│   │  (dataclasses)│  │
│  └──────────────┘    └──────────────────┘    └───────────────┘  │
│         │                    │                       │           │
│         │                    ▼                       ▼           │
│         │           ┌──────────────────┐    ┌───────────────┐   │
│         │           │  pylmgc_bridge   │───▶│  pylmgc90.pre │   │
│         │           │  (LMGC90Bridge)  │    │  (externe)    │   │
│         │           └──────────────────┘    └───────────────┘   │
│         │                                                         │
│         ▼                                                         │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │                       Utils                              │   │
│   │  safe_eval | script_generator | compute_script_generator │   │
│   │  fast_granulo_engin | serializers | validators           │   │
│   └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Dépendances principales

| Dépendance | Rôle |
|---|---|
| `PyQt6` | Framework UI (widgets, signaux/slots, threads) |
| `pylmgc90` | Bibliothèque LMGC90 (pré-traitement, simulation) |
| `numpy` | Calculs vectorisés (granulométrie, positions, **populations SoA**) |
| `pyvista` / `pyvistaqt` | Visualisation 3D des avatars |
| `gmsh` (optionnel) | Maillage de géométries pour corps déformables |

---

## 2. Structure des fichiers

```
lmgc90_gui/
│
├── main.py                          # Point d'entrée, QApplication
│
├── src/
│   ├── core/                        # Couche Modèle (MVC)
│   │   ├── models.py                # Dataclasses : Material, Model, Avatar, ProjectState, ...
│   │   ├── particle_population.py   # ★ ParticlePopulation — modèle SoA (Structure of Arrays)
│   │   ├── particle_population_io.py# ★ Sidecar binaire .npz (arrays des populations)
│   │   ├── validators.py            # Validation des données
│   │   ├── generators.py            # LoopGenerator, GranuloGenerator
│   │   ├── serializers.py           # Sauvegarde/chargement JSON (.lmgc90) + sidecar .npz
│   │   ├── pylmgc_bridge.py         # Conversion modèles → objets pylmgc90
│   │   ├── particle_factory.py      # Moteur de génération progressive
│   │   ├── avatar_factory.py        # Templates d'avatars prédéfinis
│   │   ├── app_logger.py            # Logger applicatif
│   │   └── workers/
│   │       └── granulo_worker.py    # QThread pour génération granulo
│   │
│   ├── controllers/
│   │   ├── project_controller.py    # Contrôleur central (assemble tous les mixins)
│   │   ├── granulo_mixin.py         # CRUD granulo — chemin AoS (Avatar) ET chemin SoA (population)
│   │   ├── for_loops_mixin.py       # Boucles For génériques — chemin AoS ET chemin SoA
│   │   └── base_mixin.py            # _rebuild_pylmgc_objects (régénère aussi les populations)
│   │
│   ├── views/                       # Couche Vue (MVC)
│   │   ├── main_window.py           # Fenêtre principale (QMainWindow)
│   │   ├── tree_view.py             # Arbre du modèle (QTreeWidget)
│   │   └── tabs/                    # Onglets de travail
│   │       ├── base_tab.py          # Classe de base avec safe_eval
│   │       ├── material_tab.py      # Gestion matériaux
│   │       ├── model_tab.py         # Gestion modèles EF
│   │       ├── avatar_tab.py        # Gestion avatars standards
│   │       ├── empty_avatar_tab.py  # Avatars vides (contacteurs manuels)
│   │       ├── loop_tab.py          # Boucles de génération (case à cocher SoA)
│   │       ├── granulo_tab.py       # Génération granulométrique (case à cocher SoA)
│   │       ├── dof_tab.py           # Conditions aux limites DOF
│   │       ├── contact_tab.py       # Lois de contact
│   │       ├── visibility_tab.py    # Tables de visibilité
│   │       ├── postpro_tab.py       # Post-traitement
│   │       ├── viewer_tab.py        # Wrapper onglet visualisation 3D
│   │       └── ...
│   │
│   ├── gui/
│   │   └── dialogs/                 # Dialogues et assistants
│   │       ├── dialogs.py           # DynamicVarsDialog, PreferencesDialog, DuplicateDialog
│   │       ├── setup_wizard.py      # Assistant de projet
│   │       ├── factory_wizard.py    # Assistant Particle Factory (+ FactoryTab)
│   │       ├── granulo_wizard.py    # Assistant granulométrie (option SoA)
│   │       ├── mesh_wiz_def.py      # Assistant corps déformables (FEM)
│   │       ├── masonery_wizard.py   # Assistant maçonnerie
│   │       ├── fast_granulo_dialg.py # Dialog génération rapide numpy
│   │       ├── viewer_3d.py         # Widget PyVista (visualisation 3D, gère avatars + populations)
│   │       ├── chipy_routines_dialog.py # Config routines chipy
│   │       ├── app_log_dialog.py    # Visualisation des logs
│   │       └── convert_dialog.py    # Conversion scripts pylmgc90
│   │
│   └── utils/
│       ├── safe_eval.py             # Évaluateur sécurisé + proxies contexte projet
│       ├── script_generator.py      # Génération script pre.py
│       ├── compute_script_generator.py # Génération script chipy (command.py)
│       ├── fast_granulo_engin.py    # Moteur granulo numpy haute perf.
│       └── convert.py              # Convertisseur script pylmgc90 → .lmgc90
```

> ★ Fichiers introduits par le refactor "avatar_id stable" / architecture SoA — voir §3.7-3.8.

---

## 3. Couche Core (Modèle)

### 3.1 `models.py` — Les dataclasses

Toutes les entités du projet sont des **dataclasses Python**. Elles sont la source de vérité.

```python
# Hiérarchie des modèles
ProjectState
├── List[Material]              # Matériaux (RIGID, ELAS, ...)
├── List[Model]                 # Modèles EF (Rxx2D, T3xxx, ...)
├── List[Avatar]                # Corps rigides/déformables — modèle AoS (Array of Structures)
├── List[ParticlePopulation]    # ★ Populations de particules massives — modèle SoA
├── Dict[str, List[str]]        # ★ populations_groups : nom de groupe → population_id
├── List[ContactLaw]            # Lois de contact (IQS_CLB, ...)
├── List[VisibilityRule]        # Tables de visibilité
├── List[DOFOperation]          # Conditions aux limites
├── List[Loop]                  # Boucles géométriques (cercle, grille...)
├── List[ForLoop]               # Boucles for génériques (JSON template)
├── List[GranuloGeneration]     # Dépôts granulométriques (référence un population_id en mode SoA)
├── List[PostProCommand]        # Commandes post-traitement
├── Dict[str, List[str]]        # Groupes d'avatars (nom → avatar_id, stable — voir §8.2)
├── Dict[str, Any]              # Variables dynamiques (expressions)
├── List[dict]                  # Factories (FactoryConfig sérialisés)
└── ProjectPreferences          # Préférences utilisateur
```

**Chaque dataclass** expose `to_dict()` et `from_dict()` pour la sérialisation JSON. Exemple :

```python
@dataclass
class Avatar:
    avatar_type: AvatarType       # Enum : rigidDisk, roughWall, ...
    center: List[float]
    material_name: str
    model_name: str
    color: str = "BLUEx"
    origin: AvatarOrigin = AvatarOrigin.MANUAL
    avatar_id: str = field(default_factory=new_avatar_id)  # identité stable, jamais réassignée
    radius: Optional[float] = None
    # ... autres champs spécifiques au type
```

**Enums importants :**

| Enum | Valeurs notables |
|---|---|
| `AvatarType` | `RIGID_DISK`, `ROUGH_WALL`, `MESH_DEFORMABLE`, `EMPTY_AVATAR`, ... |
| `AvatarOrigin` | `MANUAL`, `LOOP`, `GRANULO`, `FACTORY` |
| `MaterialType` | `RIGID`, `ELAS`, `ELAS_PLAS`, ... |
| `ContactLawType` | `IQS_CLB`, `MAC_CZM`, `ELASTIC_WIRE`, ... |
| `UnitSystem` | `SI`, `CGS` |

**Champs `ProjectState` liés à la population SoA (nouveau) :**

```python
@dataclass
class ProjectState:
    ...
    avatars: List[Avatar] = field(default_factory=list)
    particle_populations: List[Any] = field(default_factory=list)   # List[ParticlePopulation]
    populations_groups: Dict[str, List[str]] = field(default_factory=dict)  # groupe → [population_id, ...]
    ...
```

`particle_populations` est typé `List[Any]` dans `models.py` pour éviter un import circulaire
(`particle_population.py` importe déjà `Avatar`/`AvatarType`/`AvatarOrigin` depuis `models.py`).
L'import réel de `ParticlePopulation` est fait localement dans
`ProjectState.from_dict()` au moment de la désérialisation.

---

### 3.2 `validators.py` — Validation

Chaque entité a son validateur :

```python
MaterialValidator.validate_or_raise(material)  # Nom ≤ 5 chars, densité > 0
ModelValidator.validate_or_raise(model)         # Élément compatible physique+dim
AvatarValidator.validate_or_raise(avatar, model) # Paramètres selon type
ContactLawValidator.validate_or_raise(law)      # Propriétés obligatoires
```

Les validateurs lèvent `ValidationError` (hérite de `Exception`) capturée par la Vue pour afficher un `QMessageBox`.

> **Note SoA :** `ParticlePopulation` ne passe **pas** par `AvatarValidator`. Sa propre
> validation est intégrée dans `ParticlePopulation.create()` (voir §3.7) : cohérence des
> formes `centers`/`radii`, dimension 2 ou 3, rayons strictement positifs. Un
> `ParticlePopulation` invalide lève directement `ValueError` à la construction, il n'existe
> jamais d'instance invalide en mémoire.

---

### 3.3 `pylmgc_bridge.py` — Pont vers pylmgc90

`LMGC90Bridge` est une classe **statique** qui convertit les dataclasses en objets `pylmgc90.pre` :

```python
LMGC90Bridge.create_material(material)       → pre.material(...)
LMGC90Bridge.create_model(model)             → pre.model(...)
LMGC90Bridge.create_avatar(avatar, mod, mat) → pre.rigidDisk(...) / pre.avatar(...)
LMGC90Bridge.create_contact_law(law)         → pre.tact_behav(...)
LMGC90Bridge.create_visibility_rule(rule, b) → pre.see_table(...)
LMGC90Bridge.apply_dof_operation(op, body)   → body.translate(...) / body.imposeDrivenDof(...)
```

**Cas complexes gérés :**
- Corps déformables : `pre.buildMesh2D`, `pre.buildMeshH8`, `pre.readMesh` + `pre.buildMeshedAvatar`
- Briques de maçonnerie : `pre.brick2D/3D` + `brick.rigidBrick(...)`
- Avatars vides avec contacteurs : création pas-à-pas via `pre.avatar()` → `addBulk` → `addNode` → `addContactors`

#### ★ `create_avatars_from_population()` — Création en masse (SoA)

Méthode statique dédiée, appelée uniquement pour un `ParticlePopulation` (jamais pour un
`Avatar` individuel) :

```python
@staticmethod
def create_avatars_from_population(
    population: "ParticlePopulation", model_obj: Any, material_obj: Any
) -> List[Any]:
    """
    Crée les objets pylmgc90 réels pour toute une population, en une seule passe.
    Reste un appel Fortran par particule côté pylmgc90 (granulo_Random/depositInXxx
    sont vectorisés, mais la création d'avatar elle-même ne l'est pas), mais élimine
    tout l'overhead Python côté GUI : pas d'objet Avatar/dataclass intermédiaire par
    particule, accès direct aux arrays numpy de la population.
    """
```

**Limitation assumée et documentée dans le code :** seuls les types
`AvatarType.RIGID_DISK` (→ `pre.rigidDisk`) et `AvatarType.RIGID_SPHERE`
(→ `pre.rigidSphere`) sont supportés — ce sont les deux seuls types produits
aujourd'hui par la génération granulométrique. Tout autre type lève `ValueError`.
C'est cette même liste (`_POPULATION_ELIGIBLE_TYPES` dans `for_loops_mixin.py`) qui
conditionne l'éligibilité d'une boucle For au chemin SoA (§4.2).

---

### 3.4 `generators.py` — Génération de positions

```python
LoopGenerator.generate_positions(loop: Loop) → List[[x, y]]
# Dispatche vers : generate_circle / generate_grid / generate_line / generate_spiral

GranuloGenerator.generate(config) → (nb_particles, coordinates_array, radii_array)
# Appelle pre.granulo_Random puis pre.depositInBox2D / depositInDisk2D / ...
```

`GranuloGenerator.generate()` est **agnostique** au chemin AoS/SoA : il retourne toujours
des arrays numpy bruts (`coordinates`, `radii`). C'est l'appelant (`GranuloMixin`, voir §4.2)
qui décide, selon `config.use_particle_population`, de matérialiser N `Avatar` individuels
ou un seul `ParticlePopulation`.

---

### 3.5 `particle_factory.py` — Particle Factory

Système de génération **progressive** de particules (inspiré d'EDEM) :

- `FactoryConfig` : dataclass complète (type, zone, planning, conteneur)
- `ParticleFactory` : moteur (valide, assigne les indices corps, génère le code)
- `PreCodeGenerator` : génère le bloc `pre.py` (création invisible + planning)
- `ChipyCodeGenerator` : génère le bloc `chipy.py` (activation par vagues)

> Les avatars issus d'une Factory restent des `Avatar` individuels (`AvatarOrigin.FACTORY`),
> chargés via `factory_mixin.py::load_factory_avatars_from_json()`. La Factory **ne produit
> pas** de `ParticlePopulation` — elle reste sur le modèle AoS car chaque particule y est
> potentiellement identifiée par nom (`factory_<name>_<type>_<i>`) pour le pilotage
> `SetVisible`/`SetInvisible` par vagues.

---

### 3.6 `serializers.py`

```python
ProjectSerializer.save(state, filepath)   # JSON → fichier .lmgc90 (+ sidecar .npz, voir §3.8)
ProjectSerializer.load(filepath)          # fichier .lmgc90 (+ sidecar) → ProjectState
```

Le format `.lmgc90` est du **JSON pur**. Seuls les avatars `origin == MANUAL` sont sérialisés ; les avatars générés (boucles, granulo) sont regénérés au chargement.

> **Impact du refactor SoA sur la sauvegarde :** les `ParticlePopulation` ne sont **jamais**
> écrites en JSON avec leurs arrays inline (ce serait rédhibitoire en taille pour des
> dizaines de milliers de particules). `ProjectSerializer.save()` délègue les arrays au
> sidecar binaire `.npz` (§3.8) et n'écrit dans le JSON qu'un champ
> `particle_populations_sidecar` (nom de fichier relatif) — voir §3.8 pour le détail complet
> du format à deux niveaux (métadonnées JSON / arrays npz).

---

### 3.7 ★ `particle_population.py` — Le modèle SoA

**Nouveau fichier** introduit pour supporter les volumes de particules qui feraient
s'effondrer une `List[Avatar]` (dizaines de milliers de particules et plus, génération
granulométrique massive, boucles For à grand nombre d'itérations).

#### Motivation

`Avatar` est un modèle **AoS** (Array of Structures) : chaque particule est un objet Python
complet (dataclass avec ~15 champs), et `state.avatars` est une liste Python de ces objets.
Ce modèle est adapté aux avatars **peu nombreux et individuellement édités** (murs, avatars
manuels, corps déformables) mais devient un goulot d'étranglement mémoire et CPU au-delà de
quelques milliers de particules homogènes (dépôt granulométrique, boucle For massive).

`ParticlePopulation` est le pendant **SoA** (Structure of Arrays) : une population entière de
particules **homogènes** (même type, même matériau, même modèle, même couleur) est stockée
comme **deux arrays numpy contigus** — centres et rayons — plutôt que N objets Python.

> **`ParticlePopulation` est complémentaire à `Avatar`, pas un remplacement.** `Avatar` reste
> la bonne structure pour tout ce qui est peu nombreux et édité individuellement.
> `ParticlePopulation` vise spécifiquement les volumes massifs et homogènes.

#### Structure

```python
@dataclass
class ParticlePopulation:
    population_id: str            # identifiant stable — jamais recalculé
    avatar_type: AvatarType       # UN SEUL type pour toute la population
    material_name: str            # UN SEUL matériau pour toute la population
    model_name: str               # UN SEUL modèle pour toute la population
    color: str                    # UNE SEULE couleur pour toute la population
    origin: AvatarOrigin          # typiquement GRANULO ou LOOP
    dimension: int                # 2 ou 3, déduit de centers.shape[1]

    centers: np.ndarray           # shape (N, dim), dtype float64
    radii: np.ndarray             # shape (N,),     dtype float64

    group_name: Optional[str] = None
```

Ce choix d'homogénéité forcée est **cohérent avec la façon dont granulo/factory génèrent
déjà aujourd'hui** via `GranuloTab` : un dépôt granulométrique ou une boucle For massive
produit toujours des particules d'un seul type/matériau/modèle/couleur.

#### Construction validée

```python
population = ParticlePopulation.create(
    avatar_type=AvatarType.RIGID_DISK,
    material_name="TDURx",
    model_name="rigid",
    color="BLUEx",
    origin=AvatarOrigin.GRANULO,
    centers=coordinates_array,     # (N, 2) ou (N, 3)
    radii=radii_array,             # (N,)
    group_name="depot_box",
    population_id=None,            # généré automatiquement si absent (uuid4 hex préfixé "pop_")
)
```

`create()` est le **point d'entrée validé** — à préférer systématiquement à l'appel direct
du constructeur `ParticlePopulation(...)`. Il vérifie : `centers` bien 2D avec
`centers.shape[1] ∈ {2, 3}`, `radii` bien 1D de même longueur que `centers`, et tous les
rayons strictement positifs (`np.any(radii <= 0)` → `ValueError`).

#### Identifiants de particules — dérivés, jamais stockés

Contrairement à `Avatar.avatar_id` (stocké, généré une fois), l'identifiant d'une particule
individuelle au sein d'une population est **calculé à la volée** :

```python
population.particle_avatar_id(i)              # → f"{population_id}:{i}"
population.index_from_particle_avatar_id(aid)  # inverse — utile pour sélection/DOF ciblé
```

Ce schéma reste valide **tant que la population n'est pas régénérée** (un rechargement de
projet régénère la population avec le même `population_id`, donc les mêmes id dérivés).

#### Matérialisation ponctuelle — `as_avatar_view()`

Pour un besoin ponctuel (édition individuelle dans l'UI, DOF ciblé sur une seule particule,
affichage d'info), une particule peut être matérialisée en `Avatar` complet à la demande :

```python
avatar = population.as_avatar_view(i)   # construit un Avatar(...) à la volée
```

⚠️ **Ne jamais appeler ceci en boucle sur toute la population** — c'est exactement l'usage
que `ParticlePopulation` est censé éviter. C'est le mécanisme utilisé par le viewer 3D pour
étendre les populations en avatars affichables (§5.7) et par `granulo_mixin.py` pour générer
les anciens indices `generated_ids` lors d'une migration.

#### Statistiques utiles (aperçu UI)

```python
population.bounds()         # → (min, max) par axe, pour cadrer la caméra du viewer
population.radius_stats()   # → {"min": ..., "max": ..., "mean": ...}
len(population)             # → nombre de particules (shape[0] de centers)
```

#### Sérialisation à deux niveaux

`ParticlePopulation` expose **deux paires** de méthodes de sérialisation, pour deux usages
distincts :

| Paire | Usage | Contenu |
|---|---|---|
| `to_dict()` / `from_dict()` | Mémoire (tests, duplication), rétrocompatibilité avec les anciens projets sauvegardés **avant** l'introduction du sidecar binaire | Forme **autonome** — arrays inclus, sérialisés en listes JSON |
| `to_meta_dict()` / `from_meta_and_arrays()` | Utilisé par `ProjectSerializer` en production | Métadonnées seules en JSON (population_id, type, matériau, modèle, couleur, origine, dimension, groupe, `n_particles`) ; les arrays viennent séparément du sidecar `.npz` |

`to_meta_dict()` inclut volontairement `n_particles` (redondant avec `len(centers)`) pour
permettre l'affichage/la validation sans devoir charger le fichier `.npz`.

---

### 3.8 ★ `particle_population_io.py` — Sidecar binaire `.npz`

**Nouveau fichier**, complémentaire à `particle_population.py` : gère la lecture/écriture du
fichier compagnon binaire regroupant **tous les arrays numpy** de toutes les
`ParticlePopulation` d'un projet, dans un seul fichier `.npz` compressé.

#### Convention de nommage du fichier

```python
sidecar_path_for(project_filepath: Path) -> Path
# <projet>.lmgc90  →  <projet>.populations.npz   (même dossier)
```

L'implémentation utilise deux appels successifs à `.with_suffix('')` puis
`.with_suffix('.populations.npz')` pour éviter un double-suffixe si le nom du projet
contient lui-même un point.

#### Format interne du `.npz`

Deux arrays par population, préfixés par son `population_id`, pour tout stocker dans un seul
fichier :

```
"<population_id>__centers" -> ndarray (N, dim) float64
"<population_id>__radii"   -> ndarray (N,)     float64
```

#### API

```python
save_populations_sidecar(populations: List[ParticlePopulation], npz_path: Path) -> None
# np.savez_compressed(npz_path, **arrays)
# Si `populations` est vide : AUCUN fichier n'est écrit, et un ancien sidecar
# orphelin existant est supprimé (évite une désynchronisation projet/sidecar).

load_populations_sidecar(npz_path: Path) -> Dict[str, Tuple[np.ndarray, np.ndarray]]
# → {population_id: (centers, radii)}
# Retourne un dict vide si le fichier n'existe pas — traité comme "aucune population
# chargeable", PAS comme une erreur fatale (voir gestion des load_warnings ci-dessous).
```

#### Intégration dans `ProjectSerializer` (chargement défensif)

Le chargement d'un sidecar corrompu ou d'une population manquante **ne fait jamais échouer
le chargement du reste du projet** :

```python
# serializers.py::ProjectSerializer.load()
if sidecar_name and raw_populations:
    npz_path = filepath.parent / sidecar_name
    sidecar_arrays = load_populations_sidecar(npz_path)
    for meta in raw_populations:
        pop_id = meta.get('population_id')
        if pop_id in sidecar_arrays:
            # fusionner centers/radii dans le dict avant ProjectState.from_dict()
            ...
        else:
            load_warnings.append(
                f"Population '{pop_id}' introuvable dans le sidecar "
                f"'{sidecar_name}' — population ignorée."
            )
```

Ce comportement suit exactement la même philosophie `load_warnings` déjà en place pour la
migration des anciennes références positionnelles (`ProjectState._migrate_legacy_avatar_refs`,
voir §8.2).

---

## 4. Couche Controllers

### 4.1 `project_controller.py` — Le contrôleur central

`ProjectController(QObject)` est le **cœur de l'application**. Il :

1. Maintient l'état du projet (`self.state: ProjectState`)
2. Maintient les objets pylmgc90 en mémoire :
   ```python
   self._materials_container   # pre.materials()
   self._models_container      # pre.models()
   self._bodies_container      # pre.avatars()
   self._contact_laws_container # pre.tact_behavs()
   self._visibility_container  # pre.see_tables()
   self._postpro_container     # pre.postpro_commands()

   self._pylmgc_materials: Dict[str, Any]  # nom → objet pylmgc90
   self._pylmgc_models: Dict[str, Any]
   self._pylmgc_bodies: List[Any]          # indexé comme state.avatars (AoS)
   self._pylmgc_laws: Dict[str, Any]
   self._pylmgc_population_bodies: Dict[str, List[Any]]  # ★ population_id → [bodies pylmgc90]
   ```
3. Émet `state_changed = pyqtSignal()` à chaque modification

**Invariant fondamental (AoS) :** `self._pylmgc_bodies[i]` correspond toujours à
`self.state.avatars[i]`.

**Invariant fondamental (SoA) :** `self._pylmgc_population_bodies[population_id]` est la
liste des objets pylmgc90 réels (un par particule) créés pour cette population, dans le
même ordre que `population.centers`/`population.radii`. Cette liste est indépendante de
`_pylmgc_bodies` — les particules d'une population ne sont **jamais** ajoutées à
`_pylmgc_bodies`, seulement à `_bodies_container` (le conteneur pylmgc90 partagé, utilisé
pour `writeDatbox`).

#### API du contrôleur (méthodes principales)

```python
# Projet
controller.new_project(name)
controller.save_project(filepath?)
controller.load_project(filepath)        # → reconstruit tout via _rebuild_pylmgc_objects()

# CRUD Matériaux
controller.add_material(material)        # valide + crée objet pylmgc + state
controller.update_material(old_name, m)  # met à jour refs dans avatars
controller.remove_material(name)

# CRUD Modèles (identique)
# CRUD Avatars (AoS)
controller.add_avatar(avatar, create_pylmgc=True)  # create_pylmgc=False pour perf
controller.update_avatar(index, avatar)
controller.remove_avatar(index)
controller.duplicate_avatar(index, n, offset, group?)
controller.duplicate_group(group_name, n, offset, prefix?)

# Génération (AoS, un Avatar par particule)
controller.generate_loop(loop)           # → crée avatars + ajoute au groupe
controller.generate_granulo(config)      # → via GranuloGenerator ; bascule en SoA si
                                          #    config.use_particle_population == True
controller.generate_for_loop(for_loop)   # → boucle for générique ; bascule en SoA si
                                          #    éligible ET template_config['_use_soa'] == True

# Génération (SoA — nouveau, voir §4.2)
controller.generate_granulo_population(config)              # → ParticlePopulation (variante explicite)
controller.create_granulo_population_from_arrays(config, centers, radii)  # arrays déjà calculés
controller.remove_particle_population(population_id)        # supprime population + bodies pylmgc90

# DATBOX
controller.generate_datbox(output_path) # → pre.writeDatbox(...)
```

#### `_rebuild_pylmgc_objects()` — Reconstruction au chargement

Au chargement d'un projet, l'ordre est **strict** :

1. Matériaux → modèles → avatars MANUAL
2. Nettoyage des groupes (préserve les avatar_id des factories en attente)
3. Régénération des boucles (`generate_loop`) → avatars AoS
4. Régénération de la granulométrie (`generate_granulo`) → avatars AoS **ou** SoA selon
   `GranuloGeneration.use_particle_population`
5. ★ **Régénération des populations SoA** (`state.particle_populations`) — étape dédiée,
   distincte de l'étape 4 : pour chaque `ParticlePopulation` déjà présente dans l'état
   chargé (populations qui n'ont pas de `GranuloGeneration` associée, ex. issues d'une
   boucle For SoA), les objets pylmgc90 sont recréés directement via
   `LMGC90Bridge.create_avatars_from_population(population, mod_obj, mat_obj)` et ajoutés à
   `_bodies_container` + `_pylmgc_population_bodies[population.population_id]`
6. Régénération des boucles For (`generate_for_loop`) → AoS **ou** SoA selon éligibilité
7. Lois de contact → visibilité → réapplication des opérations DOF

Si une erreur survient (ex : matériau manquant), elle est stockée dans `state.load_warnings`
et affichée dans l'UI — **y compris pour une population SoA** dont le matériau/modèle est
introuvable (`"Population de particules #{i+1} ({population.population_id}) : {e}"`).

#### Mode batch

```python
self._batch_mode = True   # Désactive state_changed.emit() pendant la création
# ... créer N avatars ...
self._batch_mode = False
self.state_changed.emit()  # Un seul signal à la fin
```

> Le chemin SoA n'a **pas besoin** du mode batch pour les performances : une population
> entière est créée en un seul appel `state_changed.emit()` de toute façon, puisqu'il n'y a
> qu'un seul objet `ParticlePopulation` ajouté à `state.particle_populations` (au lieu de N
> appels `add_avatar`). C'est précisément le gain principal du refactor SoA côté UI.

---

### 4.2 ★ Architecture SoA — intégration dans les mixins

Deux mixins possèdent désormais **deux chemins de génération parallèles** : le chemin
historique **AoS** (un `Avatar` par particule) et le chemin **SoA** (`ParticlePopulation`
unique). Le choix entre les deux est piloté explicitement par l'utilisateur (case à cocher
dans l'UI), jamais par un seuil automatique implicite.

#### `granulo_mixin.py` — `GranuloMixin`

```python
def generate_granulo(self, config: GranuloGeneration) -> List[int]:
    if config.use_particle_population:
        nb, coordinates, radii = GranuloGenerator.generate(config)
        self.create_granulo_population_from_arrays(config, coordinates, radii)
        return []   # aucun index Avatar — la génération vit dans state.particle_populations
    else:
        nb, coordinates, radii = GranuloGenerator.generate(config)
        # ... boucle Python, un Avatar par particule (chemin historique, inchangé)
```

`create_granulo_population_from_arrays(config, centers, radii)` :
1. Construit le `ParticlePopulation` via `ParticlePopulation.create(...)`
2. Réutilise `config.population_id` si déjà défini (mise à jour), sinon le fixe depuis le
   `population_id` généré
3. Résout `mat_obj`/`mod_obj` depuis `_pylmgc_materials`/`_pylmgc_models` — lève `ValueError`
   explicite si absents (même contrat que pour un `Avatar` classique)
4. Appelle `LMGC90Bridge.create_avatars_from_population(...)`, ajoute chaque body à
   `_bodies_container` **et** à `_pylmgc_bodies` (⚠️ **exception à l'invariant décrit en
   §4.1** — vérifier `_pylmgc_population_bodies` en parallèle pour la traçabilité), stocke
   la liste dans `_pylmgc_population_bodies[population.population_id]`
5. Ajoute `config` à `state.granulo_generations` et `population` à
   `state.particle_populations` (sauf si `self._is_loading`, pour éviter les doublons lors
   du rechargement)
6. Alimente `state.populations_groups[config.group_name]` avec le `population_id` (et non
   des avatar_id — les groupes de populations sont une structure distincte des groupes
   d'avatars, voir tableau ci-dessous)
7. Émet `state_changed`

`remove_particle_population(population_id)` : retire les bodies pylmgc90 correspondants de
`_bodies_container`, supprime l'entrée de `_pylmgc_population_bodies`, retire le
`ParticlePopulation` de `state.particle_populations`, nettoie
`state.populations_groups` (et supprime les groupes devenus vides).

**Distinction groupes d'avatars vs groupes de populations :**

| Structure | Clé → Valeur | Résolu par |
|---|---|---|
| `state.avatar_groups` | nom de groupe → `List[avatar_id]` (str) | `GroupProxy` (safe_eval), `LoopTab`, `DOFTab`, ... |
| `state.populations_groups` | nom de groupe → `List[population_id]` (str) | usage interne granulo/for_loop SoA uniquement, pas encore exposé dans `GroupProxy` |

#### `for_loops_mixin.py` — `ForLoopsMixin`

```python
_POPULATION_ELIGIBLE_TYPES = {'rigidDisk', 'rigidSphere'}   # même liste que LMGC90Bridge
_SOA_FLAG_KEY = '_use_soa'   # clé interne du template_config, posée par loop_tab.py
```

**Conditions d'éligibilité** (`_for_loop_eligible_for_population`) — **toutes** requises :

1. `template_config.get('_use_soa')` est vrai — **choix explicite de l'utilisateur**, coché
   dans `LoopTab` (case visible uniquement quand `target_type == "avatar"`)
2. `avatar_type ∈ {rigidDisk, rigidSphere}`
3. Le template ne contient **aucune** des clés incompatibles avec le SoA :
   `contactors`, `vertices`, `wall_params`, `is_hollow`, `generation_type`, `axis`,
   `nb_vertices` — ces avatars nécessitent un objet `Avatar` individuel même si
   l'utilisateur a coché la case (le chemin AoS classique est alors utilisé silencieusement)

**Chemin SoA** (`_generate_for_loop_avatar_population`) :

```python
for_loop → évalue center_expr/radius_expr à chaque itération de la boucle Python
         → accumule dans centers: List[List[float]], radii: List[float]
         → np.array(...) une fois la boucle terminée
         → ParticlePopulation.create(..., origin=AvatarOrigin.LOOP)
         → LMGC90Bridge.create_avatars_from_population(...)
         → state.particle_populations.append(population)
         → for_loop.template_config['_population_id'] = population.population_id  # traçabilité
         → for_loop.generated_refs = []   # AUCUN avatar_id : les particules ne sont PAS
                                           # dans state.avatars, donc rien à référencer côté AoS
```

**Limitation assumée et explicitée dans le tooltip UI** (`loop_tab.py`) : les avatars
produits par ce chemin ne sont **plus individuellement modifiables** via l'onglet Avatar
— cohérent avec le compromis déjà accepté pour la granulométrie SoA.

`remove_for_loop()` gère le nettoyage symétrique via
`_remove_for_loop_population(for_loop)` : lit `template_config['_population_id']` en
priorité (chemin direct), sinon retombe sur `for_loop.group_name` pour retrouver et
supprimer toutes les populations associées au groupe.

---

## 5. Couche GUI / Views

### 5.1 `main_window.py` — Fenêtre principale

`MainWindow(QMainWindow)` orchestre tout :

```
MainWindow
├── MenuBar                # Fichier, Assistants, Outils, Calcul, Onglets, Aide
├── ToolBar                # Nouveau, Ouvrir, Sauvegarder, DATBOX, Script
├── DockWidget (gauche)
│   └── ModelTreeView      # Arbre QTreeWidget
└── Central (QSplitter vertical)
    ├── QTabWidget         # Onglets de travail (70%)
    │   ├── MaterialTab
    │   ├── ModelTab
    │   ├── AvatarTab
    │   └── ...
    └── QWidget (bas 30%)  # Boutons LMGC90 Viz + ParaView
```

**Gestion des onglets :** Les onglets peuvent être ouverts/fermés dynamiquement. `material_tab` et `model_tab` sont **essentiels** (non fermables). Chaque onglet est instancié une seule fois et caché/montré.

**Connexion des signaux :**
```python
# Chaque onglet émet des signaux → MainWindow._refresh_all()
self.material_tab.material_created.connect(self._refresh_all)
# _refresh_all() appelle tree_view.refresh() + tab.refresh() sur tous les onglets
```

---

### 5.2 `tree_view.py` — Arbre du modèle

`ModelTreeView(QObject)` gère un `QTreeWidget` affichant la structure complète :

```
Modèle LMGC90
├── Matériaux (N)
├── Modèles (N)
├── Avatars (N) [filtrés selon préférence show_granulo_individually]
├── Groupes d'avatars
├── Lois de contact
├── Tables de visibilité
├── Opérations DOF
├── Boucles
├── Dépôts Granulo
└── Post-Processing
```

**Signal émis :** `item_selected = pyqtSignal(str, object)` → type d'élément + données. `MainWindow` reçoit ce signal et charge l'élément dans l'onglet approprié.

**Menu contextuel :** Clic droit sur Avatar → `DuplicateDialog`. Clic droit sur Groupe → duplication du groupe entier.

> **Note SoA :** l'arbre du modèle n'affiche **pas encore** de nœud dédié aux
> `ParticlePopulation` — seul le nœud "Dépôts Granulo" liste les `GranuloGeneration`
> (avec, pour celles en mode SoA, un nombre de particules affiché depuis
> `gen.nb_particles` plutôt que `len(gen.generated_ids)`, ce dernier restant vide en SoA).
> C'est une piste d'amélioration UI connue, pas une limitation technique.

---

### 5.3 `base_tab.py` — Classe de base des onglets

Tous les onglets héritent de `BaseTab(QWidget)`. Elle fournit :

```python
# Évaluation sécurisée d'expressions (utilise SafeEvaluator)
self.eval_float(text, default, field_name)  # "0.5 * pi" → 1.5707...
self.eval_int(text, default, field_name)
self.eval_list(text, expected_length, field_name)  # "1.0, 2.0" → [1.0, 2.0]
self.eval_dict(text, field_name)    # "k=1, nu=0.3" → {"k": 1, "nu": 0.3}

# Label d'aide contextuelle
self.add_expression_help_label(layout)
```

L'évaluateur donne accès au **contexte projet complet** dans les champs de formulaire :
`avatar[0].x`, `group['mur'][0].radius`, `material['acier'].density`, etc.

> **Note SoA :** `AvatarCollectionProxy`/`GroupProxy` (dans `safe_eval.py`) n'itèrent
> aujourd'hui que sur `state.avatars` — les particules d'une `ParticlePopulation` ne sont
> **pas** exposées dans les expressions `avatar[i]` ou `group['nom']`. C'est une conséquence
> directe du compromis SoA (pas d'objet `Avatar` individuel adressable) et non un oubli.

---

### 5.4 Les onglets (tabs/)

Chaque onglet suit le même **pattern CRUD** :

```
Tab
├── QTreeWidget        # Liste des éléments existants
├── Boutons (✏️ Modifier, 🗑️ Supprimer)
├── QFormLayout        # Formulaire de création/édition
├── Boutons (✅ Créer, 💾 Enregistrer, ❌ Annuler, 🔄 Réinitialiser)
└── Signaux émis       # element_created, element_updated, element_deleted
```

**Méthodes à implémenter dans chaque onglet :**

```python
def _setup_ui(self)              # Construction de l'interface
def _connect_signals(self)       # Connexion signaux/slots
def _on_create(self)             # Créer un élément
def _on_edit_from_tree(self)     # Charger pour édition depuis l'arbre
def _on_update(self)             # Enregistrer les modifications
def _on_delete(self)             # Supprimer
def load_for_edit(self, ...)     # Remplir le formulaire depuis un objet
def refresh(self)                # Rafraîchir l'affichage
```

#### `avatar_tab.py` — Onglet Avatar

Gère 18+ types d'avatars 2D/3D. La méthode `_on_type_changed()` affiche/masque dynamiquement les champs selon le type sélectionné. `_build_avatar_from_form()` construit l'objet `Avatar` depuis les champs visibles.

#### `model_tab.py` — Onglet Modèle

Gestion complexe des options selon la physique (MECAx/THERx/POROx/MULTI) et l'élément. `_on_element_changed()` reconstruit dynamiquement les combos d'options.

#### `granulo_tab.py` — Génération granulométrique

Utilise un **QThread** (`GranuloWorker`) pour les calculs. La création des avatars se fait par **batches progressifs** via un `QTimer` pour ne pas bloquer l'UI :

```
_on_generate() → GranuloWorker.run() → data_ready signal
                                          ↓
                               _on_data_ready() → QTimer(0ms)
                                                     ↓
                               _create_next_avatar() × N [batches de 50-100]
                                                     ↓
                               _on_creation_completed()
```

★ **Chemin SoA :** une case à cocher **"Créer comme ParticlePopulation (SoA, stockage
compact)"** (`self.use_population_check`) est disponible dans le formulaire. Quand cochée,
`config.use_particle_population = True` est posé sur le `GranuloGeneration` avant génération,
et `_on_data_ready()` **court-circuite entièrement le système de batches/QTimer** :

```python
if self.current_config and self.current_config.use_particle_population:
    self._create_particle_population_from_particles(particles_data)
    return
```

`_create_particle_population_from_particles()` reconstruit `centers`/`radii` en arrays numpy
depuis les données déjà calculées par le worker, puis appelle directement
`controller.create_granulo_population_from_arrays(...)` — un seul appel, sans QTimer ni
`_batch_mode`, car il n'y a qu'un seul objet à insérer dans `state.particle_populations`.

#### `loop_tab.py` — Boucles (For)

★ Pour `target_type == "avatar"` uniquement, une case à cocher **"Créer comme
ParticlePopulation (SoA, plus rapide pour les gros volumes)"**
(`self.use_soa_check`) est affichée. Son tooltip énonce explicitement les conditions
d'éligibilité (mêmes que §4.2) et la limitation (particules non éditables individuellement).
Le choix est propagé dans le JSON du template via la clé `_use_soa` :

```python
if target_type == "avatar" and self.use_soa_check.isChecked():
    template_config['_use_soa'] = True
```

Ce flag est ensuite lu par `ForLoopsMixin._for_loop_eligible_for_population()` (§4.2). Il
est également **restauré** en édition (`load_for_edit`) et **conservé au chargement** du
projet, car `template_config` fait partie intégrante du `ForLoop` sérialisé.

---

### 5.5 `viewer_3d.py` — Visualisation 3D

`Viewer3D(QWidget)` wrappant `pyvistaqt.QtInteractor`. Ne se rafraîchit **jamais automatiquement** pour éviter les freezes. L'utilisateur clique "🔄 Rafraîchir la scène".

**Construction des meshes :**
```python
build_avatar_mesh(avatar) → pv.PolyData
# Dispatche vers _MESH_BUILDERS[avatar.avatar_type]
# Ex: _mesh_rigid_disk → pv.Circle().extrude(h)
#     _mesh_rigid_polygon → pv.PolyData(vertices)
#     _mesh_deformable → reconstruit depuis mesh_params (geom)
```

**Modes couleur :** LMGC90 (par code couleur) | Par type | Par matériau | Par origine  
**Modes interaction :** Navigation | Sélection (avatar_clicked signal) | Règle (mesure distance)

---

### 5.6 `viewer_tab.py` — Wrapper d'intégration MainWindow

```python
renderables = [*self.controller.state.avatars, *self.controller.state.particle_populations]
self.viewer.update_avatars(renderables)
```

`renderables` est une liste **mixte** `Avatar` + `ParticlePopulation` — c'est
`_expand_renderables()` côté `viewer_3d.py` (§5.7) qui homogénéise le tout avant construction
des meshes. Le compteur affiché dans le bandeau supérieur (`ViewerTab.refresh()`) additionne
également les deux :

```python
n = sum(len(item) if isinstance(item, ParticlePopulation) else 1 for item in items)
```

(`len(population)` retourne le nombre de particules — voir §3.7 — d'où la distinction avec
`1` pour un `Avatar` scalaire.)

---

### 5.7 ★ Intégration SoA dans le viewer 3D

`viewer_3d.py::_expand_renderables()` est le point d'entrée qui **aplati** la liste mixte
`Avatar` + `ParticlePopulation` en une séquence homogène d'`Avatar` (réels ou vues) prête
pour `build_avatar_mesh()` :

```python
def _expand_renderables(renderables) -> List[Tuple[int, Avatar]]:
    expanded: List[Tuple[int, Avatar]] = []
    for item in renderables or []:
        if isinstance(item, ParticlePopulation):
            for i in range(len(item)):
                expanded.append((len(expanded), item.as_avatar_view(i)))
        elif isinstance(item, Avatar):
            expanded.append((len(expanded), item))
    return expanded
```

**Conséquence directe :** afficher une population de 50 000 particules matérialise
**50 000 objets `Avatar` temporaires** côté viewer (via `as_avatar_view(i)` en boucle,
l'exception délibérée à la règle "ne jamais boucler" énoncée en §3.7 — justifiée ici car le
viewer a de toute façon besoin d'un mesh PyVista par particule). C'est un point de vigilance
performance connu pour le mode paramétrique du viewer sur de très gros volumes SoA ; le mode
batch (`_BATCH_TYPES = {RIGID_DISK, RIGID_SPHERE}` dans `Viewer3D.update_avatars()`) fusionne
ensuite ces meshes individuels par lot de couleur identique pour limiter le nombre d'acteurs
VTK réellement créés — mais la matérialisation Python initiale reste, elle, en O(N).

Le mode **pylmgc90** du viewer (bouton 🔬, `_render_via_pylmgc90`) reçoit lui aussi la liste
aplatie via `[av for _, av in renderables]` — aucune adaptation spécifique nécessaire de ce
côté puisqu'il consomme déjà des `Avatar`.

---

## 6. Couche Utils

### 6.1 `safe_eval.py` — Évaluation sécurisée

**Problème résolu :** Permettre aux utilisateurs d'entrer des expressions Python (`avatar[0].x + 0.1`, `sqrt(2) * radius`) dans les formulaires sans risque de sécurité.

**Architecture :**

```python
# 1. SafeEvaluator — vérification AST + eval isolé
ev = SafeEvaluator(allowed_names=context_dict)
result = ev.eval_expression("avatar[0].x * 2")

# 2. Proxies — accès aux données du projet
AvatarCollectionProxy  # avatar[i], len(avatar), list(avatar) — state.avatars UNIQUEMENT (AoS)
AvatarProxy            # .center, .x, .y, .z, .radius, .nodes[1].coor, ...
GroupProxy             # group['nom'][0].center — résout state.avatar_groups (AoS) UNIQUEMENT
MaterialProxy          # material['acier'].density
ModelProxy             # model['rigid'].physics

# 3. build_eval_context() — construit le contexte complet
ctx = build_eval_context(controller)
# ctx contient: math, np, avatar, group, material, model,
#               avatars_by_color(), avatars_by_material(), ...
#               + toutes les variables dynamiques du projet
```

**Sécurité :** `SafeEvaluator._check_safe()` parcourt l'AST et rejette tout nœud non autorisé (import, exec, attributs dangereux, etc.).

> Voir §5.3 pour la portée volontairement limitée de `AvatarCollectionProxy`/`GroupProxy` vis-à-vis des populations SoA.

---

### 6.2 `script_generator.py` — Génération script pre.py

`ScriptGenerator(controller)` génère un script Python reproduisant le projet :

```
generate(output_path)
├── _write_header()           # Commentaire d'en-tête
├── _write_imports()          # from pylmgc90 import pre, numpy, math
├── _write_dynamic_vars()     # Évaluation et injection des vars dynamiques
├── _write_containers()       # mats, mods, bodies, tacts, sees, posts
├── _write_materials()        # mat_NOM = pre.material(...)
├── _write_models()           # mod_NOM = pre.model(...)
├── _write_avatars_manual()   # Avatars MANUAL (avec option boucle ou individuel)
│   ├── _write_avatars_manual_loop()   # Mode boucle (par groupes)
│   │   ├── _write_masonry_group_loop()  # Boucles briques de maçonnerie
│   │   └── _write_standard_group_loop() # Boucle for + liste de centers
│   └── _write_single_avatar()          # Avatar individuel
├── _write_for_loops()        # Boucles For génériques
├── _write_loops()            # Boucles géométriques (cercle, grille...)
├── _write_granulo()          # pre.granulo_Random + depositIn*
├── _write_contact_laws()     # pre.tact_behav(...)
├── _write_visibility()       # pre.see_table(...)
├── _write_dof_operations()   # body.translate / imposeDrivenDof
├── _write_postpro()          # pre.postpro_command(...)
├── _write_factories()        # Particle Factories (code pré-calculé)
└── _write_datbox()           # pre.writeDatbox(...)
```

> ⚠️ **Limitation SoA actuelle, non résolue :** `ScriptGenerator` ne parcourt que
> `self.state.avatars` (AoS) et `self.state.granulo_generations` en régénérant l'appel
> `pre.granulo_Random` + `depositInXxx` (ce qui reste valide, car indépendant du mode
> AoS/SoA côté génération pylmgc90 elle-même). En revanche, un `ParticlePopulation` créé via
> une **boucle For SoA** (§4.2) — c'est-à-dire sans `GranuloGeneration` associée — n'a
> aujourd'hui **aucun chemin d'écriture dédié** dans `_write_for_loops()`/`_write_loops()` :
> seul le template JSON de la boucle For est réécrit tel quel (avec sa clé `_use_soa`), le
> script généré recrée donc les avatars via le chemin AoS classique de `_write_for_avatar()}`.
> Point de vigilance pour toute contribution future touchant `for_loops_mixin.py` ou
> `script_generator.py`.

**Préférence `script_use_loop` :** Si activée, les avatars d'un même groupe homogène sont regroupés dans une boucle `for _c in _centers_<groupe>:` pour un script plus compact.

---

### 6.3 `compute_script_generator.py` — Génération script chipy

`ComputeScriptGenerator(controller)` génère `command.py` (boucle de simulation) selon les paramètres configurés dans `ChipyRoutinesDialog`.

Sections générées :
1. Configuration chipy (`SetDimension`, `ReadDatbox`, ...)
2. Initialisation des Particle Factories (invisibilité + planning)
3. Boucle principale `for k in range(nb_steps):`
   - FreeVelocity RBDY2/RBDY3/FEM
   - Détection contact (détecteurs sélectionnés)
   - Résolution NLGS
   - Activation des vagues de factory
   - ComputeDof + UpdateStep
   - Extraction (énergie, GBV, inspection)
   - WriteOut + WriteDisplayFiles
4. Finalisation

> Le calcul chipy lui-même (`command.py`) est **totalement agnostique** au mode AoS/SoA côté
> GUI : au moment du calcul, tous les corps (avatars individuels ou particules issues d'une
> population) sont déjà des corps `RBDY2`/`RBDY3` identiques dans le DATBOX généré par
> `pre.writeDatbox()`. La distinction AoS/SoA n'existe que côté Python GUI (édition,
> mémoire, sérialisation) — elle disparaît entièrement une fois la DATBOX écrite.

---

### 6.4 `fast_granulo_engin.py` — Granulométrie numpy

Moteur **sans pylmgc90**, entièrement numpy, pour générer des milliers de particules sans bloquer l'UI :

```python
GranuloFastEngine.generate(nb, rmin, rmax, container_type, ...)
# → Placement par batches (candidats → filtrage bbox → filtrage collisions vectorisé)
# → FastGranuloResult avec List[FastParticle]

GranuloFileWriter.write(result, output_dir)
# → Écrit DATBOX/BODIES.DAT directement (bypass pylmgc90)

GranuloStateIntegrator.integrate(result, controller)
# → Ajoute les avatars en batch unique dans controller.state (AoS)
```

> **Ce moteur reste 100% AoS** (`GranuloStateIntegrator.integrate()` construit un `Avatar`
> par particule dans une boucle, cf. `core/models.py::Avatar` et `add_avatar`). Il n'a **pas
> encore** de variante SoA — contrairement à `GranuloTab`/`GranuloMixin` (§4.2, §5.4). C'est
> une extension naturelle possible pour une future contribution, dans la mesure où
> `GranuloFastEngine.generate()` produit déjà des arrays numpy en interne
> (`FastGranuloResult.particles`) qu'il suffirait de convertir en `ParticlePopulation` via
> `ParticlePopulation.create()` plutôt que de les éclater en `Avatar` individuels.

---

### 6.5 `convert.py` — Convertisseur de scripts

Convertit un script `pre.py` existant en fichier `.lmgc90` en **exécutant le script** avec un module `_MockPre` qui intercepte tous les appels `pre.*` :

```python
class _MockPre:          # Remplace pylmgc90.pre pendant l'exec
class _AvatarObj         # Proxy d'un avatar rigide
class _MeshAvatarObj     # Proxy d'un corps déformable
class _EmptyAvatarObj    # Proxy d'un avatar vide
class _BrickObj          # Proxy d'une brique de maçonnerie
class _WallObj           # Proxy d'un mur de maçonnerie

class Converter:
    run()                # Exécute le script avec le mock
    to_lmgc90_dict()    # Construit le JSON projet

# CLI :
# python convert.py mon_script.py -o sortie.lmgc90
```

> Le convertisseur produit exclusivement des `avatars` AoS dans le JSON de sortie — il n'a
> aucune notion de `ParticlePopulation`. Un script source utilisant `pre.granulo_Random` +
> `depositInXxx` sera donc toujours importé comme un `GranuloGeneration` classique
> (`use_particle_population=False` par défaut), quelle que soit la taille du dépôt.

---

## 7. Flux de données

### 7.1 Création d'un avatar (exemple complet — chemin AoS)

```
Utilisateur remplit AvatarTab → clique "✅ Créer Avatar"
         ↓
AvatarTab._on_create()
  → _build_avatar_from_form()   # Valeurs → Avatar dataclass
  → controller.add_avatar(avatar)
         ↓
ProjectController.add_avatar()
  → AvatarValidator.validate_or_raise(avatar, model)  # Validation
  → mat_obj = self._pylmgc_materials[avatar.material_name]
  → mod_obj = self._pylmgc_models[avatar.model_name]
  → body_obj = LMGC90Bridge.create_avatar(avatar, mod_obj, mat_obj)
  → self._bodies_container.addAvatar(body_obj)
  → self._pylmgc_bodies.append(body_obj)
  → self.state.avatars.append(avatar)
  → self.state_changed.emit()   # si pas en batch_mode
         ↓
AvatarTab.avatar_created.emit()
         ↓
MainWindow._refresh_all()
  → tree_view.refresh()         # Arbre mis à jour
  → [tous les onglets].refresh() # Combos mis à jour
```

### 7.2 ★ Génération d'un dépôt granulométrique massif (chemin SoA)

```
Utilisateur coche "Créer comme ParticlePopulation" dans GranuloTab
         ↓ clique "✅ Générer le Dépôt"
GranuloTab._on_generate_optimized()
  → config = GranuloGeneration(..., use_particle_population=True)
  → GranuloGenerator.generate(config)   # thread principal : pre.granulo_Random + depositInBox2D
  → GranuloWorker (QThread)             # conversion arrays → dicts (léger, pas de natif)
         ↓ data_ready
GranuloTab._on_data_ready()
  → current_config.use_particle_population == True
  → _create_particle_population_from_particles(particles_data)   # PAS de QTimer/batches
         ↓
controller.create_granulo_population_from_arrays(config, centers, radii)
  → population = ParticlePopulation.create(...)
  → LMGC90Bridge.create_avatars_from_population(population, mod_obj, mat_obj)
  → _bodies_container.addAvatar(body) pour chaque particule  [reste O(N) côté pylmgc90]
  → _pylmgc_population_bodies[population.population_id] = bodies
  → state.granulo_generations.append(config)
  → state.particle_populations.append(population)             # UN SEUL objet Python ajouté
  → state.populations_groups[config.group_name].append(population.population_id)
  → state_changed.emit()                                       # UN SEUL signal
         ↓
MainWindow._refresh_all()
  → tree_view.refresh() (affiche le dépôt via GranuloGeneration, pas via un nœud population dédié)
```

**Différence structurante avec le flux AoS (§7.1) :** un seul appel `state_changed.emit()`
et un seul objet ajouté à une liste Python, quel que soit le nombre de particules — contre N
avatars/N entrées de liste en mode AoS (mitigé par le `_batch_mode` et les batches
`QTimer`, mais toujours O(N) côté structures Python).

### 7.3 Sauvegarde et chargement (avec populations SoA)

```
Sauvegarde :
  ProjectController.save_project()
    → ProjectSerializer.save(state, filepath)
      → state.to_dict()                     # avatars MANUAL (AoS) uniquement
      → save_populations_sidecar(state.particle_populations, sidecar_path)  # ★ arrays → .npz
      → data['particle_populations_sidecar'] = npz_path.name               # ★ référence JSON
      → json.dump(data, file)               # Fichier .lmgc90

Chargement :
  ProjectController.load_project(filepath)
    → ProjectSerializer.load(filepath)
      → load_populations_sidecar(npz_path)         # ★ arrays bruts depuis le .npz
      → fusion métadonnées JSON + arrays npz        # ★ avant ProjectState.from_dict()
      → ProjectState.from_dict(data)                # Dataclasses reconstruites,
                                                      #   y compris ParticlePopulation.from_dict()
    → _rebuild_pylmgc_objects()        # Reconstruction ordre strict (voir §4.1)
      1. Matériaux + Modèles
      2. Avatars MANUAL
      3. Boucles → generate_loop()
      4. Granulo → generate_granulo()             # AoS ou SoA selon use_particle_population
      5. ★ Populations SoA restantes (hors granulo) → create_avatars_from_population()
      6. Boucles For → generate_for_loop()         # AoS ou SoA selon _use_soa
      7. Lois + Visibilité + DOF
```

---

## 8. Systèmes clés expliqués

### 8.1 Indexation des avatars (AoS)

L'index d'un avatar dans `state.avatars` **n'est plus l'identifiant persistant** depuis le
refactor "avatar_id stable" : chaque `Avatar` porte un `avatar_id` (uuid hex) généré une
seule fois à la création et jamais réassigné, même si sa position dans `state.avatars`
change. C'est cet identifiant qui est utilisé dans `avatar_groups`, `DOFOperation.target_value`,
`PostProCommand.target_value`, `Loop.model_avatar_id`, etc. — voir `core/models.py` et la
migration `ProjectState._migrate_legacy_avatar_refs()` pour la compatibilité ascendante avec
les anciens fichiers `.lmgc90` (schéma v1, références positionnelles).

### 8.2 Identifiants de particules (SoA)

Symétriquement côté SoA, l'identité d'une particule au sein d'une `ParticlePopulation` est
**dérivée**, pas stockée : `f"{population_id}:{i}"` (voir §3.7). Le `population_id`
lui-même **est** stable (généré une fois, jamais recalculé), mais l'indice `i` d'une
particule donnée à l'intérieur de la population reste positionnel — acceptable car une
population entière est traitée comme un bloc atomique (jamais réordonnée partiellement, pas
de suppression individuelle d'une particule au sein d'une population).

### 8.3 Variables dynamiques

Les variables dynamiques (`state.dynamic_vars`) sont des **expressions Python** :
```python
{"thickness": "0.5", "radius": "thickness * 2 + 0.1", "x_wall": "avatar[0].x"}
```

Elles sont évaluées dans l'ordre de définition et injectées dans le contexte de `SafeEvaluator`. Ainsi, dans un formulaire, l'utilisateur peut écrire `radius` et obtenir la valeur calculée.

> Comme noté en §5.3, `avatar[i]` dans ces expressions ne référence que les avatars AoS —
> une particule issue d'une `ParticlePopulation` n'est pas adressable par ce mécanisme.

### 8.4 Système de préférences

`ProjectPreferences` est stocké dans `state.preferences` et sauvegardé avec le projet. Les préférences importantes :

| Préférence | Impact |
|---|---|
| `show_granulo_individually` | Masque les avatars GRANULO (**AoS uniquement**) dans l'arbre et les onglets ; n'a aucun effet sur une `ParticlePopulation`, qui n'apparaît de toute façon jamais individuellement dans l'arbre (voir §5.2) |
| `create_pylmgc_on_generate` | Désactive la création pylmgc pendant génération massive **AoS** |
| `script_use_loop` | Génère des boucles compactes dans le script pre.py (AoS) |
| `auto_refresh_viewer` | (réservé) Rafraîchissement auto de la vue 3D |

### 8.5 ★ Architecture SoA (ParticlePopulation) vs AoS (Avatar) — synthèse

| Critère | AoS — `Avatar` | SoA — `ParticlePopulation` |
|---|---|---|
| Stockage | 1 objet Python (dataclass) par particule dans `state.avatars` | 2 arrays numpy (`centers`, `radii`) partagés par toute la population, 1 seul objet Python dans `state.particle_populations` |
| Homogénéité | Aucune contrainte — chaque avatar peut différer en tout | **Un seul** type/matériau/modèle/couleur pour toute la population |
| Types supportés | Tous les `AvatarType` | Uniquement `RIGID_DISK` et `RIGID_SPHERE` (limite de `LMGC90Bridge.create_avatars_from_population`) |
| Édition individuelle | Oui — via `AvatarTab`, `avatar[i]` dans les expressions | Non — seule la population entière est manipulable |
| Identité | `avatar_id` stocké, stable | `population_id` stocké, stable ; id de particule dérivé `f"{population_id}:{i}"` |
| Sérialisation | JSON inline (`state.avatars`, uniquement `origin==MANUAL`) | Métadonnées JSON + arrays dans sidecar `.npz` compressé séparé |
| Génération | `add_avatar()` — un appel par particule (mitigé par `_batch_mode`) | `create_granulo_population_from_arrays()` / chemin SoA de `for_loops_mixin.py` — un seul appel pour toute la population |
| Activation | Chemin par défaut, toujours actif | **Opt-in explicite** : case à cocher dans `GranuloTab`/`LoopTab`, jamais de bascule automatique |
| Coût mémoire/CPU (GUI) | O(N) objets Python, O(N) appels `state_changed` potentiels | O(1) objet Python, O(1) appel `state_changed`, mais toujours O(N) côté création des bodies pylmgc90 (limite Fortran, non contournable) |
| Viewer 3D | `Avatar` directement | Aplatie via `as_avatar_view(i)` en boucle — voir §5.7, coût O(N) côté viewer uniquement |
| `safe_eval` (`avatar[i]`, `group[...]`) | Supporté | **Non supporté** — limitation connue |
| Script `pre.py` généré | Support complet | Support complet pour la granulométrie (indépendant du mode) ; **pas de chemin dédié** pour une boucle For SoA (voir §6.2) |

**Règle de décision pour choisir AoS vs SoA lors d'une contribution :** si le nouveau code
doit produire un grand nombre (typiquement > quelques milliers) de particules
**strictement homogènes** en type/matériau/modèle/couleur, et que ces particules n'ont pas
besoin d'édition individuelle après création, le chemin SoA est préférable. Dans tous les
autres cas (avatars variés, édition individuelle requise, petit nombre), rester sur le
chemin AoS historique.

---

## 9. Cycle de vie d'un projet

```
1. NOUVEAU PROJET
   MainWindow._on_new_project()
   → controller.new_project(name)
   → _reset_containers() [conteneurs pylmgc vides, y compris _pylmgc_population_bodies.clear()]
   → state = ProjectState(name)   # particle_populations = [] par défaut

2. CONFIGURATION
   Onglet Matériaux → add_material()
   Onglet Modèles   → add_model()
   Onglet Avatars   → add_avatar()
   ... (lois, visibilité, DOF, boucles, granulo — AoS ou SoA selon les cases à cocher)

3. SAUVEGARDE
   Ctrl+S → save_project()
   → state.to_dict() → JSON
   → save_populations_sidecar(...) → .populations.npz  [si des populations existent]

4. GÉNÉRATION DATBOX
   Outils → DATBOX → controller.generate_datbox(path)
   → pre.writeDatbox(dim, mats, mods, bodies, tacts, sees, post)
   # bodies contient indifféremment les corps AoS et SoA (tous dans _bodies_container)

5. GÉNÉRATION SCRIPT PRE.PY
   Outils → Script Python → ScriptGenerator.generate(path)
   # ⚠️ voir limitation §6.2 pour les populations issues d'une boucle For SoA

6. GÉNÉRATION SCRIPT CHIPY (command.py)
   Calcul → Générer Script → ComputeScriptGenerator.generate(path, params)
   # agnostique AoS/SoA — voir §6.3

7. CALCUL
   Calcul → Lancer → compute_tab.run_computation()
   → Exécute command.py dans un subprocess
   → Affiche les logs LMGC90

8. CHARGEMENT
   Fichier → Ouvrir → controller.load_project(path)
   → ProjectState.from_dict() + sidecar .npz (§7.3) + _rebuild_pylmgc_objects()
```

---

## 10. Conventions et patterns

### Conventions de nommage

| Élément | Convention | Exemple |
|---|---|---|
| Classes | PascalCase | `AvatarTab`, `LMGC90Bridge`, `ParticlePopulation` |
| Méthodes | snake_case | `_on_create()`, `load_for_edit()` |
| Slots Qt | Préfixe `_on_` | `_on_type_changed()` |
| Signaux Qt | Suffixe descriptif | `avatar_created`, `state_changed` |
| Méthodes privées | Préfixe `_` | `_build_avatar_from_form()` |
| Conteneurs pylmgc | Préfixe `_pylmgc_` | `_pylmgc_materials`, `_pylmgc_population_bodies` |
| Flags SoA internes | Préfixe `_` dans les dicts JSON | `_use_soa`, `_population_id` dans `template_config` |

### Pattern signal/slot

```python
# Dans un onglet :
class AvatarTab(BaseTab):
    avatar_created = pyqtSignal()   # Déclaration au niveau classe

    def _on_create(self):
        ...
        self.avatar_created.emit()  # Émission après action réussie

# Dans MainWindow :
self.avatar_tab.avatar_created.connect(self._refresh_all)
```

### Gestion des erreurs

```python
try:
    # Code métier
    avatar = self._build_avatar_from_form()
    self.controller.add_avatar(avatar)
    # Succès
    QMessageBox.information(self, "Succès", "✅ Avatar créé")
except ValidationError as e:
    QMessageBox.warning(self, "Validation", str(e))
except ValueError as e:
    QMessageBox.critical(self, "Erreur", f"Valeurs invalides :\n{e}")
except Exception as e:
    QMessageBox.critical(self, "Erreur", f"Création échouée :\n{e}")
```

---

## 11. Guide de contribution

### Ajouter un nouveau type d'avatar

1. **`models.py`** : Ajouter la valeur dans `AvatarType`
2. **`validators.py`** : Ajouter la validation dans `AvatarValidator.validate()`
3. **`pylmgc_bridge.py`** : Ajouter le cas dans `LMGC90Bridge.create_avatar()`
4. **`avatar_tab.py`** :
   - Ajouter le type dans `AVATAR_TYPES_2D` ou `AVATAR_TYPES_3D`
   - Gérer l'affichage des champs dans `_on_type_changed()`
   - Construire l'avatar dans `_build_avatar_from_form()`
5. **`viewer_3d.py`** : Ajouter le builder de mesh dans `_MESH_BUILDERS`
6. **`script_generator.py`** : Gérer la génération dans `_write_single_avatar()`
7. *(Optionnel, SoA)* Si ce type doit être éligible au chemin SoA, l'ajouter à
   `_POPULATION_ELIGIBLE_TYPES` (`for_loops_mixin.py`) **et** au dispatch de
   `LMGC90Bridge.create_avatars_from_population()` — les deux listes doivent rester
   synchronisées manuellement (pas de source unique de vérité aujourd'hui, point de
   vigilance pour toute contribution future).

### Ajouter un nouvel onglet

1. Créer `src/views/tabs/mon_tab.py` héritant de `BaseTab`
2. Implémenter le pattern CRUD complet
3. Déclarer les signaux nécessaires
4. Importer dans `src/views/tabs/__init__.py`
5. Instancier dans `MainWindow._create_tabs()`
6. Ajouter dans `MainWindow.all_tabs`
7. Connecter les signaux dans `MainWindow._connect_signals()`

### Ajouter une nouvelle loi de contact

1. **`models.py`** : Ajouter dans `ContactLawType` et la catégorie appropriée dans `CONTACT_LAW_CATEGORIES`
2. **`validators.py`** : Ajouter propriétés requises dans `ContactLawValidator._REQUIRED_PROPS`
3. **`pylmgc_bridge.py`** : Ajouter le cas dans `create_contact_law()`
4. **`contact_tab.py`** : Ajouter les champs UI dans `_on_type_changed()` et `_build_law_from_form()`

### Ajouter un paramètre de préférences

1. **`models.py`** : Ajouter le champ dans `ProjectPreferences` avec valeur par défaut
2. Ajouter dans `to_dict()` et `from_dict()`
3. **`dialogs.py`** : Ajouter le widget dans `PreferencesDialog._build_perf_tab()` (ou autre onglet)
4. Ajouter dans `_load_preferences()` et `get_preferences()`
5. Utiliser la préférence via `getattr(self.controller.state.preferences, 'ma_pref', default)`

### ★ Étendre le chemin SoA à un nouveau générateur (ex. Particle Factory, fast_granulo)

1. Vérifier que la sortie du générateur est déjà (ou peut être) exprimée comme deux arrays
   numpy `centers (N, dim)` et `radii (N,)` — c'est le cas de `GranuloFastEngine.generate()`
   par exemple (voir remarque §6.4).
2. Construire un `ParticlePopulation` via `ParticlePopulation.create(...)` (jamais le
   constructeur direct).
3. Créer les objets pylmgc90 via `LMGC90Bridge.create_avatars_from_population(...)` — si le
   type d'avatar cible n'est pas `rigidDisk`/`rigidSphere`, l'étendre d'abord (voir
   ci-dessus "Ajouter un nouveau type d'avatar").
4. Ajouter la population à `state.particle_populations` et, si un regroupement est
   pertinent, à `state.populations_groups`.
5. Exposer le choix AoS/SoA dans l'UI via une case à cocher **opt-in explicite** — ne jamais
   basculer automatiquement selon un seuil implicite (cohérent avec le choix de design
   documenté en §4.2).
6. Gérer la suppression symétrique (`remove_particle_population` ou équivalent) et la
   régénération au chargement (`_rebuild_pylmgc_objects`, étape 5, §4.1).
7. Documenter la limitation "non éditable individuellement" dans le tooltip UI correspondant.

### Tests et débogage

- **Logger applicatif** : `from src.core.app_logger import get_logger; _log = get_logger('mon_module')`
- **Journal** : Calcul → Journal de l'application (F7)
- **Logs LMGC90** : Calcul → Voir Logs LMGC90 (F6)
- **Variables dynamiques** : Outils → Variables dynamiques (Ctrl+V)

---

## Annexe — Fichiers de référence rapide

| Besoin | Fichier |
|---|---|
| Ajouter/modifier un type de données | `src/core/models.py` |
| ★ Modifier le modèle SoA (populations massives) | `src/core/particle_population.py` |
| ★ Modifier la sérialisation binaire des populations | `src/core/particle_population_io.py` |
| Modifier la validation | `src/core/validators.py` |
| Modifier l'appel pylmgc90 | `src/core/pylmgc_bridge.py` |
| Ajouter une logique métier | `src/controllers/project_controller.py` |
| ★ Modifier le chemin SoA de la granulométrie | `src/controllers/granulo_mixin.py` |
| ★ Modifier le chemin SoA des boucles For | `src/controllers/for_loops_mixin.py` |
| Modifier l'UI d'un onglet | `src/views/tabs/<nom>_tab.py` |
| ★ Modifier la case à cocher SoA granulo | `src/views/tabs/granulo_tab.py` |
| ★ Modifier la case à cocher SoA boucle For | `src/views/tabs/loop_tab.py` |
| Modifier la vue 3D | `src/gui/dialogs/viewer_3d.py` |
| Modifier le script pre.py généré | `src/utils/script_generator.py` |
| Modifier le script chipy généré | `src/utils/compute_script_generator.py` |
| Modifier l'évaluation des expressions | `src/utils/safe_eval.py` |
| Modifier la sérialisation JSON | `src/core/serializers.py` + `models.py` |