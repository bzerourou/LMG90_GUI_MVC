# LMGC90_GUI — Architecture & Guide du Contributeur

> Version 0.4.0 — Interface graphique pour le code de simulation mécanique LMGC90, l'architecture actuelle va être remplacée dans la version 0.5.1.

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
| `numpy` | Calculs vectorisés (granulométrie, positions) |
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
│   │   ├── models.py                # Dataclasses : Material, Model, Avatar, ...
│   │   ├── validators.py            # Validation des données
│   │   ├── generators.py            # LoopGenerator, GranuloGenerator
│   │   ├── serializers.py           # Sauvegarde/chargement JSON (.lmgc90)
│   │   ├── pylmgc_bridge.py         # Conversion modèles → objets pylmgc90
│   │   ├── particle_factory.py      # Moteur de génération progressive
│   │   ├── avatar_factory.py        # Templates d'avatars prédéfinis
│   │   ├── app_logger.py            # Logger applicatif
│   │   └── workers/
│   │       └── granulo_worker.py    # QThread pour génération granulo
│   │
│   ├── controllers/
│   │   └── project_controller.py    # Contrôleur central (logique métier)
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
│   │       ├── loop_tab.py          # Boucles de génération
│   │       ├── granulo_tab.py       # Génération granulométrique
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
│   │       ├── granulo_wizard.py    # Assistant granulométrie
│   │       ├── mesh_wiz_def.py      # Assistant corps déformables (FEM)
│   │       ├── masonery_wizard.py   # Assistant maçonnerie
│   │       ├── fast_granulo_dialg.py # Dialog génération rapide numpy
│   │       ├── viewer_3d.py         # Widget PyVista (visualisation 3D)
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

---

## 3. Couche Core (Modèle)

### 3.1 `models.py` — Les dataclasses

Toutes les entités du projet sont des **dataclasses Python**. Elles sont la source de vérité.

```python
# Hiérarchie des modèles
ProjectState
├── List[Material]          # Matériaux (RIGID, ELAS, ...)
├── List[Model]             # Modèles EF (Rxx2D, T3xxx, ...)
├── List[Avatar]            # Corps rigides/déformables
├── List[ContactLaw]        # Lois de contact (IQS_CLB, ...)
├── List[VisibilityRule]    # Tables de visibilité
├── List[DOFOperation]      # Conditions aux limites
├── List[Loop]              # Boucles géométriques (cercle, grille...)
├── List[ForLoop]           # Boucles for génériques (JSON template)
├── List[GranuloGeneration] # Dépôts granulométriques
├── List[PostProCommand]    # Commandes post-traitement
├── Dict[str, List[int]]    # Groupes d'avatars (nom → indices)
├── Dict[str, Any]          # Variables dynamiques (expressions)
├── List[dict]              # Factories (FactoryConfig sérialisés)
└── ProjectPreferences      # Préférences utilisateur
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
    radius: Optional[float] = None
    # ... autres champs spécifiques au type
```

**Enums importants :**

| Enum | Valeurs notables |
|---|---|
| `AvatarType` | `RIGID_DISK`, `ROUGH_WALL`, `MESH_DEFORMABLE`, `EMPTY_AVATAR`, ... |
| `AvatarOrigin` | `MANUAL`, `LOOP`, `GRANULO` |
| `MaterialType` | `RIGID`, `ELAS`, `ELAS_PLAS`, ... |
| `ContactLawType` | `IQS_CLB`, `MAC_CZM`, `ELASTIC_WIRE`, ... |
| `UnitSystem` | `SI`, `CGS` |

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

---

### 3.4 `generators.py` — Génération de positions

```python
LoopGenerator.generate_positions(loop: Loop) → List[[x, y]]
# Dispatche vers : generate_circle / generate_grid / generate_line / generate_spiral

GranuloGenerator.generate(config) → (nb_particles, coordinates_array, radii_array)
# Appelle pre.granulo_Random puis pre.depositInBox2D / depositInDisk2D / ...
```

---

### 3.5 `particle_factory.py` — Particle Factory

Système de génération **progressive** de particules (inspiré d'EDEM) :

- `FactoryConfig` : dataclass complète (type, zone, planning, conteneur)
- `ParticleFactory` : moteur (valide, assigne les indices corps, génère le code)
- `PreCodeGenerator` : génère le bloc `pre.py` (création invisible + planning)
- `ChipyCodeGenerator` : génère le bloc `chipy.py` (activation par vagues)

---

### 3.6 `serializers.py`

```python
ProjectSerializer.save(state, filepath)   # JSON → fichier .lmgc90
ProjectSerializer.load(filepath)          # fichier .lmgc90 → ProjectState
```

Le format `.lmgc90` est du **JSON pur**. Seuls les avatars `origin == MANUAL` sont sérialisés ; les avatars générés (boucles, granulo) sont regénérés au chargement.

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
   self._pylmgc_bodies: List[Any]          # indexé comme state.avatars
   self._pylmgc_laws: Dict[str, Any]
   ```
3. Émet `state_changed = pyqtSignal()` à chaque modification

**Invariant fondamental :** `self._pylmgc_bodies[i]` correspond toujours à `self.state.avatars[i]`.

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
# CRUD Avatars
controller.add_avatar(avatar, create_pylmgc=True)  # create_pylmgc=False pour perf
controller.update_avatar(index, avatar)
controller.remove_avatar(index)
controller.duplicate_avatar(index, n, offset, group?)
controller.duplicate_group(group_name, n, offset, prefix?)

# Génération
controller.generate_loop(loop)           # → crée avatars + ajoute au groupe
controller.generate_granulo(config)      # → via GranuloGenerator
controller.generate_for_loop(for_loop)   # → boucle for générique

# DATBOX
controller.generate_datbox(output_path) # → pre.writeDatbox(...)
```

#### `_rebuild_pylmgc_objects()` — Reconstruction au chargement

Au chargement d'un projet, l'ordre est **strict** :
1. Matériaux → modèles → avatars MANUAL → boucles → granulo → boucles For
2. Lois de contact → visibilité → DOF

Si une erreur survient (ex : matériau manquant), elle est stockée dans `state.load_warnings` et affichée dans l'UI.

#### Mode batch

```python
self._batch_mode = True   # Désactive state_changed.emit() pendant la création
# ... créer N avatars ...
self._batch_mode = False
self.state_changed.emit()  # Un seul signal à la fin
```

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

### 5.6 Les Wizards (dialogs/)

Assistants `QWizard` multi-pages pour des tâches complexes :

| Wizard | Pages | Résultat |
|---|---|---|
| `ProjectSetupWizard` | Projet → Dim → Mat → Mod → Avatar → Contact → Visibilité → Résumé | Projet complet initialisé |
| `GranuloWizard` | Distribution → Conteneur → Propriétés → Résumé | Dépôt granulo généré |
| `MeshWizard` | Intro → Dim → Mat → Mod → Géom → Raffin → Boundary → Résumé | Corps déformable FEM |
| `MasonryWizard` | Config → Modèle → Résumé | Mur de maçonnerie |
| `FactoryWizard` | Intro → Zone → Particules → Conteneur → Planning → Résumé | Factory configurée |

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
AvatarCollectionProxy  # avatar[i], len(avatar), list(avatar)
AvatarProxy            # .center, .x, .y, .z, .radius, .nodes[1].coor, ...
GroupProxy             # group['nom'][0].center
MaterialProxy          # material['acier'].density
ModelProxy             # model['rigid'].physics

# 3. build_eval_context() — construit le contexte complet
ctx = build_eval_context(controller)
# ctx contient: math, np, avatar, group, material, model,
#               avatars_by_color(), avatars_by_material(), ...
#               + toutes les variables dynamiques du projet
```

**Sécurité :** `SafeEvaluator._check_safe()` parcourt l'AST et rejette tout nœud non autorisé (import, exec, attributs dangereux, etc.).

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
# → Ajoute les avatars en batch unique dans controller.state
```

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

---

## 7. Flux de données

### 7.1 Création d'un avatar (exemple complet)

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

### 7.2 Sauvegarde et chargement

```
Sauvegarde :
  ProjectController.save_project()
    → ProjectSerializer.save(state, filepath)
      → state.to_dict()            # Seulement avatars MANUAL
        → json.dump(data, file)   # Fichier .lmgc90

Chargement :
  ProjectController.load_project(filepath)
    → ProjectSerializer.load(filepath)
      → ProjectState.from_dict(data)   # Dataclasses reconstruites
    → _rebuild_pylmgc_objects()        # Reconstruction ordre strict
      1. Matériaux + Modèles           # Objets pylmgc90 recréés
      2. Avatars MANUAL                # bridge.create_avatar()
      3. Boucles → generate_loop()     # Avatars LOOP recréés
      4. Granulo → generate_granulo()  # Avatars GRANULO recréés
      5. Boucles For → generate_for_loop()
      6. Lois + Visibilité + DOF
```

---

## 8. Systèmes clés expliqués

### 8.1 Indexation des avatars

L'index d'un avatar dans `state.avatars` est son identifiant partout :
- `state.avatar_groups["mur"] = [0, 1, 2, 3]` → indices dans state.avatars
- `state.operations[0].target_value = 5` → avatar #5
- `self._pylmgc_bodies[5]` → objet pylmgc90 de l'avatar #5

**⚠️ Attention lors de la suppression :** `remove_avatar(index)` fait un `pop(index)` qui décale tous les indices suivants. Les groupes et opérations qui référencent des avatars d'index supérieur deviennent invalides. C'est une limitation connue qui nécessite une refonte future (IDs stables).

### 8.2 Variables dynamiques

Les variables dynamiques (`state.dynamic_vars`) sont des **expressions Python** :
```python
{"thickness": "0.5", "radius": "thickness * 2 + 0.1", "x_wall": "avatar[0].x"}
```

Elles sont évaluées dans l'ordre de définition et injectées dans le contexte de `SafeEvaluator`. Ainsi, dans un formulaire, l'utilisateur peut écrire `radius` et obtenir la valeur calculée.

### 8.3 Système de préférences

`ProjectPreferences` est stocké dans `state.preferences` et sauvegardé avec le projet. Les préférences importantes :

| Préférence | Impact |
|---|---|
| `show_granulo_individually` | Masque les avatars GRANULO dans l'arbre et les onglets |
| `create_pylmgc_on_generate` | Désactive la création pylmgc pendant génération massive |
| `script_use_loop` | Génère des boucles compactes dans le script pre.py |
| `auto_refresh_viewer` | (réservé) Rafraîchissement auto de la vue 3D |

### 8.4 Particle Factory

Les factories sont persistées comme `List[dict]` dans `state.factories`. Au chargement et à la génération du script, `ParticleFactory.from_list_of_dicts()` reconstruit l'engine, recalcule les indices bodies, et génère les blocs de code.

---

## 9. Cycle de vie d'un projet

```
1. NOUVEAU PROJET
   MainWindow._on_new_project()
   → controller.new_project(name)
   → _reset_containers() [conteneurs pylmgc vides]
   → state = ProjectState(name)

2. CONFIGURATION
   Onglet Matériaux → add_material()
   Onglet Modèles   → add_model()
   Onglet Avatars   → add_avatar()
   ... (lois, visibilité, DOF, boucles, granulo)

3. SAUVEGARDE
   Ctrl+S → save_project()
   → state.to_dict() → JSON

4. GÉNÉRATION DATBOX
   Outils → DATBOX → controller.generate_datbox(path)
   → pre.writeDatbox(dim, mats, mods, bodies, tacts, sees, post)

5. GÉNÉRATION SCRIPT PRE.PY
   Outils → Script Python → ScriptGenerator.generate(path)

6. GÉNÉRATION SCRIPT CHIPY (command.py)
   Calcul → Générer Script → ComputeScriptGenerator.generate(path, params)

7. CALCUL
   Calcul → Lancer → compute_tab.run_computation()
   → Exécute command.py dans un subprocess
   → Affiche les logs LMGC90

8. CHARGEMENT
   Fichier → Ouvrir → controller.load_project(path)
   → ProjectState.from_dict() + _rebuild_pylmgc_objects()
```

---

## 10. Conventions et patterns

### Conventions de nommage

| Élément | Convention | Exemple |
|---|---|---|
| Classes | PascalCase | `AvatarTab`, `LMGC90Bridge` |
| Méthodes | snake_case | `_on_create()`, `load_for_edit()` |
| Slots Qt | Préfixe `_on_` | `_on_type_changed()` |
| Signaux Qt | Suffixe descriptif | `avatar_created`, `state_changed` |
| Méthodes privées | Préfixe `_` | `_build_avatar_from_form()` |
| Conteneurs pylmgc | Préfixe `_pylmgc_` | `_pylmgc_materials` |

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
| Modifier la validation | `src/core/validators.py` |
| Modifier l'appel pylmgc90 | `src/core/pylmgc_bridge.py` |
| Ajouter une logique métier | `src/controllers/project_controller.py` |
| Modifier l'UI d'un onglet | `src/views/tabs/<nom>_tab.py` |
| Modifier la vue 3D | `src/gui/dialogs/viewer_3d.py` |
| Modifier le script pre.py généré | `src/utils/script_generator.py` |
| Modifier le script chipy généré | `src/utils/compute_script_generator.py` |
| Modifier l'évaluation des expressions | `src/utils/safe_eval.py` |
| Modifier la sérialisation JSON | `src/core/serializers.py` + `models.py` |