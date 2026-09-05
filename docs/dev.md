# LMGC90_GUI — Architecture & Contributor Guide

> Version 0.5.0 — Graphical interface for the LMGC90 mechanical simulation code  
> **This revision adds documentation for the “ParticlePopulation” refactor (SoA architecture)**,  
> see §3.7, §3.8, §4.2, §5.7, §8.5 and the updated appendix.

---

## Table of contents

1. [Overview](#1-overview)
2. [File structure](#2-file-structure)
3. [Core layer (Model)](#3-core-layer-model)
4. [Controllers layer](#4-controllers-layer)
5. [GUI / Views layer](#5-gui--views-layer)
6. [Utils layer](#6-utils-layer)
7. [Data flows](#7-data-flows)
8. [Key systems explained](#8-key-systems-explained)
9. [Project lifecycle](#9-project-lifecycle)
10. [Conventions and patterns](#10-conventions-and-patterns)
11. [Contribution guide](#11-contribution-guide)

---

## 1. Overview

LMGC90_GUI is a **PyQt6** desktop application following the **MVC** (Model-View-Controller) pattern. It lets users build LMGC90 mechanical simulations through a graphical interface without writing Python by hand.

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
│         │           │  (LMGC90Bridge)  │    │  (external)   │   │
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

### Main dependencies

| Dependency | Role |
|---|---|
| `PyQt6` | UI framework (widgets, signals/slots, threads) |
| `pylmgc90` | LMGC90 library (preprocessing, simulation) |
| `numpy` | Vectorised computation (granulometry, positions, **SoA populations**) |
| `pyvista` / `pyvistaqt` | 3D visualisation of avatars |
| `gmsh` (optional) | Geometry meshing for deformable bodies |

---

## 2. File structure

```
lmgc90_gui/
│
├── main.py                          # Entry point, QApplication
│
├── src/
│   ├── core/                        # Model layer (MVC)
│   │   ├── models.py                # Dataclasses: Material, Model, Avatar, ProjectState, ...
│   │   ├── particle_population.py   # ★ ParticlePopulation — SoA model (Structure of Arrays)
│   │   ├── particle_population_io.py# ★ Binary .npz sidecar (population arrays)
│   │   ├── validators.py            # Data validation
│   │   ├── generators.py            # LoopGenerator, GranuloGenerator
│   │   ├── serializers.py           # JSON save/load (.lmgc90) + .npz sidecar
│   │   ├── pylmgc_bridge.py         # Model → pylmgc90 object conversion
│   │   ├── particle_factory.py      # Progressive generation engine
│   │   ├── avatar_factory.py        # Predefined avatar templates
│   │   ├── app_logger.py            # Application logger
│   │   └── workers/
│   │       └── granulo_worker.py    # QThread for granulo generation
│   │
│   ├── controllers/
│   │   ├── project_controller.py    # Central controller (assembles all mixins)
│   │   ├── granulo_mixin.py         # Granulo CRUD — AoS (Avatar) AND SoA (population) paths
│   │   ├── for_loops_mixin.py       # Generic For loops — AoS AND SoA paths
│   │   └── base_mixin.py            # _rebuild_pylmgc_objects (also regenerates populations)
│   │
│   ├── views/                       # View layer (MVC)
│   │   ├── main_window.py           # Main window (QMainWindow)
│   │   ├── tree_view.py             # Model tree (QTreeWidget)
│   │   └── tabs/                    # Work tabs
│   │       ├── base_tab.py          # Base class with safe_eval
│   │       ├── material_tab.py      # Materials management
│   │       ├── model_tab.py         # FE models management
│   │       ├── avatar_tab.py        # Standard avatars
│   │       ├── empty_avatar_tab.py  # Empty avatars (manual contactors)
│   │       ├── loop_tab.py          # Generation loops (SoA checkbox)
│   │       ├── granulo_tab.py       # Granulometric generation (SoA checkbox)
│   │       ├── dof_tab.py           # DOF boundary conditions
│   │       ├── contact_tab.py       # Contact laws
│   │       ├── visibility_tab.py    # Visibility tables
│   │       ├── postpro_tab.py       # Post-processing
│   │       ├── viewer_tab.py        # 3D visualisation tab wrapper
│   │       └── ...
│   │
│   ├── gui/
│   │   └── dialogs/                 # Dialogs and assistants
│   │       ├── dialogs.py           # DynamicVarsDialog, PreferencesDialog, DuplicateDialog
│   │       ├── setup_wizard.py      # Project assistant
│   │       ├── factory_wizard.py    # Particle Factory assistant (+ FactoryTab)
│   │       ├── granulo_wizard.py    # Granulometry assistant (SoA option)
│   │       ├── mesh_wiz_def.py      # Deformable bodies assistant (FEM)
│   │       ├── masonery_wizard.py   # Masonry assistant
│   │       ├── fast_granulo_dialg.py # Fast numpy generation dialog
│   │       ├── viewer_3d.py         # PyVista widget (avatars + populations)
│   │       ├── chipy_routines_dialog.py # chipy routines config
│   │       ├── app_log_dialog.py    # Log viewer
│   │       └── convert_dialog.py    # pylmgc90 script conversion
│   │
│   └── utils/
│       ├── safe_eval.py             # Safe evaluator + project context proxies
│       ├── script_generator.py      # pre.py script generation
│       ├── compute_script_generator.py # chipy script generation (command.py)
│       ├── fast_granulo_engin.py    # High-performance numpy granulo engine
│       └── convert.py              # pylmgc90 script → .lmgc90 converter
```

> ★ Files introduced by the “stable avatar_id” / SoA architecture refactor — see §3.7–3.8.

---

## 3. Core layer (Model)

### 3.1 `models.py` — Dataclasses

All project entities are **Python dataclasses**. They are the source of truth.

```python
# Model hierarchy
ProjectState
├── List[Material]              # Materials (RIGID, ELAS, ...)
├── List[Model]                 # FE models (Rxx2D, T3xxx, ...)
├── List[Avatar]                # Rigid/deformable bodies — AoS model (Array of Structures)
├── List[ParticlePopulation]    # ★ Massive particle populations — SoA model
├── Dict[str, List[str]]        # ★ populations_groups: group name → population_id
├── List[ContactLaw]            # Contact laws (IQS_CLB, ...)
├── List[VisibilityRule]        # Visibility tables
├── List[DOFOperation]          # Boundary conditions
├── List[Loop]                  # Geometric loops (circle, grid...)
├── List[ForLoop]               # Generic for-loops (JSON template)
├── List[GranuloGeneration]     # Granulometric deposits (references a population_id in SoA mode)
├── List[PostProCommand]        # Post-processing commands
├── Dict[str, List[str]]        # Avatar groups (name → avatar_id, stable — see §8.2)
├── Dict[str, Any]              # Dynamic variables (expressions)
├── List[dict]                  # Factories (serialised FactoryConfig)
└── ProjectPreferences          # User preferences
```

**Each dataclass** exposes `to_dict()` and `from_dict()` for JSON serialisation. Example:

```python
@dataclass
class Avatar:
    avatar_type: AvatarType       # Enum: rigidDisk, roughWall, ...
    center: List[float]
    material_name: str
    model_name: str
    color: str = "BLUEx"
    origin: AvatarOrigin = AvatarOrigin.MANUAL
    avatar_id: str = field(default_factory=new_avatar_id)  # stable identity, never reassigned
    radius: Optional[float] = None
    # ... other type-specific fields
```

**Important enums:**

| Enum | Notable values |
|---|---|
| `AvatarType` | `RIGID_DISK`, `ROUGH_WALL`, `MESH_DEFORMABLE`, `EMPTY_AVATAR`, ... |
| `AvatarOrigin` | `MANUAL`, `LOOP`, `GRANULO`, `FACTORY` |
| `MaterialType` | `RIGID`, `ELAS`, `ELAS_PLAS`, ... |
| `ContactLawType` | `IQS_CLB`, `MAC_CZM`, `ELASTIC_WIRE`, ... |
| `UnitSystem` | `SI`, `CGS` |

**`ProjectState` fields related to SoA populations (new):**

```python
@dataclass
class ProjectState:
    ...
    avatars: List[Avatar] = field(default_factory=list)
    particle_populations: List[Any] = field(default_factory=list)   # List[ParticlePopulation]
    populations_groups: Dict[str, List[str]] = field(default_factory=dict)  # group → [population_id, ...]
    ...
```

`particle_populations` is typed as `List[Any]` in `models.py` to avoid a circular import
(`particle_population.py` already imports `Avatar` / `AvatarType` / `AvatarOrigin` from `models.py`).
The real import of `ParticlePopulation` is done locally in `ProjectState.from_dict()` at
deserialisation time.

---

### 3.2 `validators.py` — Validation

Each entity has its validator:

```python
MaterialValidator.validate_or_raise(material)  # Name ≤ 5 chars, density > 0
ModelValidator.validate_or_raise(model)         # Element compatible with physics+dim
AvatarValidator.validate_or_raise(avatar, model) # Parameters by type
ContactLawValidator.validate_or_raise(law)      # Required properties
```

Validators raise `ValidationError` (inherits `Exception`), caught by the View to show a `QMessageBox`.

> **SoA note:** `ParticlePopulation` does **not** go through `AvatarValidator`. Its own
> validation is built into `ParticlePopulation.create()` (see §3.7): consistency of
> `centers` / `radii` shapes, dimension 2 or 3, strictly positive radii. An invalid
> `ParticlePopulation` raises `ValueError` at construction; no invalid instance ever exists
> in memory.

---

### 3.3 `pylmgc_bridge.py` — Bridge to pylmgc90

`LMGC90Bridge` is a **static** class that converts dataclasses into `pylmgc90.pre` objects:

```python
LMGC90Bridge.create_material(material)       → pre.material(...)
LMGC90Bridge.create_model(model)             → pre.model(...)
LMGC90Bridge.create_avatar(avatar, mod, mat) → pre.rigidDisk(...) / pre.avatar(...)
LMGC90Bridge.create_contact_law(law)         → pre.tact_behav(...)
LMGC90Bridge.create_visibility_rule(rule, b) → pre.see_table(...)
LMGC90Bridge.apply_dof_operation(op, body)   → body.translate(...) / body.imposeDrivenDof(...)
```

**Complex cases handled:**
- Deformable bodies: `pre.buildMesh2D`, `pre.buildMeshH8`, `pre.readMesh` + `pre.buildMeshedAvatar`
- Masonry bricks: `pre.brick2D/3D` + `brick.rigidBrick(...)`
- Empty avatars with contactors: step-by-step via `pre.avatar()` → `addBulk` → `addNode` → `addContactors`

#### ★ `create_avatars_from_population()` — Bulk creation (SoA)

Dedicated static method, called only for a `ParticlePopulation` (never for an individual
`Avatar`):

```python
@staticmethod
def create_avatars_from_population(
    population: "ParticlePopulation", model_obj: Any, material_obj: Any
) -> List[Any]:
    """
    Creates real pylmgc90 objects for an entire population in one pass.
    Still one Fortran call per particle on the pylmgc90 side (granulo_Random /
    depositInXxx are vectorised, but avatar creation itself is not), but removes
    all Python GUI overhead: no intermediate Avatar/dataclass per particle,
    direct access to the population's numpy arrays.
    """
```

**Assumed limitation documented in the code:** only types
`AvatarType.RIGID_DISK` (→ `pre.rigidDisk`) and `AvatarType.RIGID_SPHERE`
(→ `pre.rigidSphere`) are supported — the only two types produced today by
granulometric generation. Any other type raises `ValueError`.
The same list (`_POPULATION_ELIGIBLE_TYPES` in `for_loops_mixin.py`) gates
For-loop eligibility for the SoA path (§4.2).

---

### 3.4 `generators.py` — Position generation

```python
LoopGenerator.generate_positions(loop: Loop) → List[[x, y]]
# Dispatches to: generate_circle / generate_grid / generate_line / generate_spiral

GranuloGenerator.generate(config) → (nb_particles, coordinates_array, radii_array)
# Calls pre.granulo_Random then pre.depositInBox2D / depositInDisk2D / ...
```

`GranuloGenerator.generate()` is **agnostic** to the AoS/SoA path: it always returns raw
numpy arrays (`coordinates`, `radii`). The caller (`GranuloMixin`, see §4.2) decides,
based on `config.use_particle_population`, whether to materialise N individual `Avatar`
objects or a single `ParticlePopulation`.

---

### 3.5 `particle_factory.py` — Particle Factory

**Progressive** particle generation system (EDEM-inspired):

- `FactoryConfig`: full dataclass (type, zone, schedule, container)
- `ParticleFactory`: engine (validates, assigns body indices, generates code)
- `PreCodeGenerator`: generates the `pre.py` block (invisible creation + schedule)
- `ChipyCodeGenerator`: generates the `chipy.py` block (wave activation)

> Avatars from a Factory remain individual `Avatar` objects (`AvatarOrigin.FACTORY`),
> loaded via `factory_mixin.py::load_factory_avatars_from_json()`. The Factory **does not
> produce** a `ParticlePopulation` — it stays on the AoS model because each particle may
> be identified by name (`factory_<name>_<type>_<i>`) for `SetVisible` / `SetInvisible`
> wave control.

---

### 3.6 `serializers.py`

```python
ProjectSerializer.save(state, filepath)   # JSON → .lmgc90 file (+ .npz sidecar, see §3.8)
ProjectSerializer.load(filepath)          # .lmgc90 file (+ sidecar) → ProjectState
```

The `.lmgc90` format is **pure JSON**. Only avatars with `origin == MANUAL` are serialised;
generated avatars (loops, granulo) are regenerated on load.

> **Impact of the SoA refactor on save:** `ParticlePopulation` objects are **never**
> written into JSON with their arrays inline (that would be prohibitive for tens of
> thousands of particles). `ProjectSerializer.save()` delegates arrays to the binary
> `.npz` sidecar (§3.8) and only writes a `particle_populations_sidecar` field (relative
> file name) into the JSON — see §3.8 for the full two-level format (JSON metadata / npz
> arrays).

---

### 3.7 ★ `particle_population.py` — The SoA model

**New file** introduced to support particle volumes that would collapse a `List[Avatar]`
(tens of thousands of particles and more, massive granulometric generation, large For
loops).

#### Motivation

`Avatar` is an **AoS** (Array of Structures) model: each particle is a full Python object
(dataclass with ~15 fields), and `state.avatars` is a Python list of those objects.
This model fits **few, individually edited** avatars (walls, manual avatars, deformable
bodies) but becomes a memory and CPU bottleneck beyond a few thousand homogeneous particles
(granulometric deposit, massive For loop).

`ParticlePopulation` is the **SoA** (Structure of Arrays) counterpart: an entire population
of **homogeneous** particles (same type, material, model, colour) is stored as **two
contiguous numpy arrays** — centres and radii — rather than N Python objects.

> **`ParticlePopulation` complements `Avatar`; it does not replace it.** `Avatar` remains
> the right structure for anything few and individually edited.
> `ParticlePopulation` specifically targets large homogeneous volumes.

#### Structure

```python
@dataclass
class ParticlePopulation:
    population_id: str            # stable identifier — never recomputed
    avatar_type: AvatarType       # ONE type for the whole population
    material_name: str            # ONE material for the whole population
    model_name: str               # ONE model for the whole population
    color: str                    # ONE colour for the whole population
    origin: AvatarOrigin          # typically GRANULO or LOOP
    dimension: int                # 2 or 3, derived from centers.shape[1]

    centers: np.ndarray           # shape (N, dim), dtype float64
    radii: np.ndarray             # shape (N,),     dtype float64

    group_name: Optional[str] = None
```

This forced homogeneity is **consistent with how granulo/factory already generate** via
`GranuloTab`: a granulometric deposit or massive For loop always produces particles of a
single type/material/model/colour.

#### Validated construction

```python
population = ParticlePopulation.create(
    avatar_type=AvatarType.RIGID_DISK,
    material_name="TDURx",
    model_name="rigid",
    color="BLUEx",
    origin=AvatarOrigin.GRANULO,
    centers=coordinates_array,     # (N, 2) or (N, 3)
    radii=radii_array,             # (N,)
    group_name="depot_box",
    population_id=None,            # auto-generated if missing (uuid4 hex prefixed "pop_")
)
```

`create()` is the **validated entry point** — always prefer it over calling the
`ParticlePopulation(...)` constructor directly. It checks: `centers` is 2D with
`centers.shape[1] ∈ {2, 3}`, `radii` is 1D of the same length as `centers`, and all radii
are strictly positive (`np.any(radii <= 0)` → `ValueError`).

#### Particle identifiers — derived, never stored

Unlike `Avatar.avatar_id` (stored, generated once), the identifier of an individual particle
within a population is **computed on the fly**:

```python
population.particle_avatar_id(i)              # → f"{population_id}:{i}"
population.index_from_particle_avatar_id(aid)  # inverse — useful for selection / targeted DOF
```

This scheme remains valid **as long as the population is not regenerated** (reloading a
project regenerates the population with the same `population_id`, hence the same derived
ids).

#### On-demand materialisation — `as_avatar_view()`

For a one-off need (individual UI edit, DOF on a single particle, info display), a particle
can be materialised as a full `Avatar` on demand:

```python
avatar = population.as_avatar_view(i)   # builds an Avatar(...) on the fly
```

⚠️ **Never call this in a loop over the whole population** — that is exactly the usage
`ParticlePopulation` is meant to avoid. This is the mechanism used by the 3D viewer to
expand populations into displayable avatars (§5.7) and by `granulo_mixin.py` to generate
legacy `generated_ids` during migration.

#### Useful statistics (UI overview)

```python
population.bounds()         # → (min, max) per axis, to frame the viewer camera
population.radius_stats()   # → {"min": ..., "max": ..., "mean": ...}
len(population)             # → particle count (centers.shape[0])
```

#### Two-level serialisation

`ParticlePopulation` exposes **two pairs** of serialisation methods for two distinct uses:

| Pair | Use | Content |
|---|---|---|
| `to_dict()` / `from_dict()` | In-memory (tests, duplication), backward compatibility with projects saved **before** the binary sidecar | **Autonomous** form — arrays included, serialised as JSON lists |
| `to_meta_dict()` / `from_meta_and_arrays()` | Used by `ProjectSerializer` in production | Metadata only in JSON (population_id, type, material, model, colour, origin, dimension, group, `n_particles`); arrays come separately from the `.npz` sidecar |

`to_meta_dict()` deliberately includes `n_particles` (redundant with `len(centers)`) so
display/validation can proceed without loading the `.npz` file.

---

### 3.8 ★ `particle_population_io.py` — Binary `.npz` sidecar

**New file**, complementary to `particle_population.py`: handles read/write of the companion
binary file that groups **all numpy arrays** of all `ParticlePopulation` objects in a
project into a single compressed `.npz` file.

#### File naming convention

```python
sidecar_path_for(project_filepath: Path) → Path
# <project>.lmgc90  →  <project>.populations.npz   (same folder)
```

#### Internal `.npz` format

```
"<population_id>__centers" → (N, dim) float64
"<population_id>__radii"   → (N,)     float64
```

One pair of keys per population; all populations of the project share a single file.

#### API

```python
save_populations_sidecar(populations, npz_path)
# np.savez_compressed(npz_path, **arrays)
# If `populations` is empty: NO file is written, and any existing orphan sidecar
# is deleted (avoids project/sidecar desynchronisation).

load_populations_sidecar(npz_path)
# → {population_id: (centers, radii)}
# Returns an empty dict if the file does not exist — treated as “no loadable
# population”, NOT as a fatal error (see load_warnings handling below).
```

#### Integration in `ProjectSerializer` (defensive loading)

On load, missing arrays for a meta entry produce a `load_warning` rather than failing the
whole project. On save, the relative sidecar name is stored in
`particle_populations_sidecar` inside the JSON.

---

## 4. Controllers layer

### 4.1 `project_controller.py` — Central controller

`ProjectController(QObject)` is the **heart of the application**. It:

1. Holds project state (`self.state: ProjectState`)
2. Holds in-memory pylmgc90 objects:
   ```python
   self._materials_container   # pre.materials()
   self._models_container      # pre.models()
   self._bodies_container      # pre.avatars()
   self._contact_laws_container # pre.tact_behavs()
   self._visibility_container  # pre.see_tables()
   self._postpro_container     # pre.postpro_commands()

   self._pylmgc_materials: Dict[str, Any]  # name → pylmgc90 object
   self._pylmgc_models: Dict[str, Any]
   self._pylmgc_bodies: List[Any]          # indexed like state.avatars (AoS)
   self._pylmgc_laws: Dict[str, Any]
   self._pylmgc_population_bodies: Dict[str, List[Any]]  # ★ population_id → [pylmgc90 bodies]
   ```
3. Emits `state_changed = pyqtSignal()` on every change

**Fundamental invariant (AoS):** `self._pylmgc_bodies[i]` always matches
`self.state.avatars[i]`.

**Fundamental invariant (SoA):** `self._pylmgc_population_bodies[population_id]` is the
list of real pylmgc90 objects (one per particle) created for that population, in the same
order as `population.centers` / `population.radii`. This list is independent of
`_pylmgc_bodies` — population particles are **never** added to `_pylmgc_bodies`, only to
`_bodies_container` (the shared pylmgc90 container used for `writeDatbox`).

#### Controller API (main methods)

```python
# Project
controller.new_project(name)
controller.save_project(filepath?)
controller.load_project(filepath)        # → full rebuild via _rebuild_pylmgc_objects()

# Material CRUD
controller.add_material(material)        # validate + create pylmgc object + state
controller.update_material(old_name, m)  # update refs in avatars
controller.remove_material(name)

# Model CRUD (same pattern)
# Avatar CRUD (AoS)
controller.add_avatar(avatar, create_pylmgc=True)  # create_pylmgc=False for perf
controller.update_avatar(index, avatar)
controller.remove_avatar(index)
controller.duplicate_avatar(index, n, offset, group?)
controller.duplicate_group(group_name, n, offset, prefix?)

# Generation (AoS, one Avatar per particle)
controller.generate_loop(loop)           # → create avatars + add to group
controller.generate_granulo(config)      # → via GranuloGenerator; switches to SoA if
                                          #    config.use_particle_population == True
controller.generate_for_loop(for_loop)   # → generic for-loop; switches to SoA if
                                          #    eligible AND template_config['_use_soa'] == True

# Generation (SoA — new, see §4.2)
controller.create_granulo_population_from_arrays(config, centers, radii)
controller.remove_particle_population(population_id)

# DATBOX
controller.generate_datbox(output_path) # → pre.writeDatbox(...)
```

#### `_rebuild_pylmgc_objects()` — Rebuild on load

On project load, order is **strict**:

1. Materials → models → MANUAL avatars → loops → granulo → For loops  
2. Contact laws → visibility → DOF  

SoA-specific steps:

4. Granulo → `generate_granulo()` (AoS or SoA depending on `use_particle_population`)  
5. ★ Remaining SoA populations (non-granulo) → `create_avatars_from_population()`  
6. For loops → `generate_for_loop()` (AoS or SoA depending on `_use_soa`)  

If an error occurs (e.g. missing material), it is stored in `state.load_warnings` and shown
in the UI.

#### Batch mode

```python
self._batch_mode = True   # Disables state_changed.emit() during creation
# ... create N avatars ...
self._batch_mode = False
self.state_changed.emit()  # Single signal at the end
```

---

### 4.2 ★ SoA architecture — integration in mixins

#### `granulo_mixin.py` — `GranuloMixin`

Two paths:

| Path | Condition | Result |
|------|-----------|--------|
| AoS | `config.use_particle_population == False` (default) | N `Avatar` objects via `add_avatar` (batch mode) |
| SoA | `config.use_particle_population == True` | One `ParticlePopulation` via `create_granulo_population_from_arrays` |

SoA path:

1. `ParticlePopulation.create(...)`
2. `LMGC90Bridge.create_avatars_from_population(...)`
3. Bodies added to `_bodies_container` and `_pylmgc_population_bodies[population_id]`
4. Append to `state.particle_populations` and `state.populations_groups`
5. Single `state_changed.emit()`

#### `for_loops_mixin.py` — For loops

SoA eligibility (`_for_loop_eligible_for_population` / `_POPULATION_ELIGIBLE_TYPES`):

- Target type is avatar
- Template type ∈ {`RIGID_DISK`, `RIGID_SPHERE`}
- Explicit `_use_soa` flag in `template_config`

If eligible and flag set → build centres/radii arrays, then same population creation path
as granulo.

---

## 5. GUI / Views layer

### 5.1 `main_window.py` — Main window

`MainWindow(QMainWindow)` orchestrates menus, toolbar, tree dock, central tabs, and the
bottom render area. Tabs can be opened/closed dynamically; material and model tabs are
essential (non-closable). Every tab signal ends up in `_refresh_all()`.

### 5.2 `tree_view.py` — Model tree

Displays materials, models, avatars (filtered by preferences), groups, contact laws,
visibility, DOF, loops, granulo deposits, post-processing. Granulo SoA deposits appear via
their `GranuloGeneration` entry, not as individual particle nodes.

### 5.3 `base_tab.py` — Tab base class

Provides `eval_float` / `eval_int` / `eval_list` / `eval_dict` via `SafeEvaluator` with full
project context (`avatar[i]`, groups, materials…). Note: `avatar[i]` addresses **AoS only** —
population particles are not addressable this way.

### 5.4 Granulo / loop tabs — SoA checkboxes

**`granulo_tab.py`:** checkbox *“Create as ParticlePopulation (SoA, compact storage)”*.
When checked, `_on_data_ready()` bypasses the QTimer batch path and calls
`controller.create_granulo_population_from_arrays(...)` once.

**`loop_tab.py`:** for `target_type == "avatar"`, checkbox *“Create as ParticlePopulation
(SoA, faster for large volumes)”*. Choice stored as `template_config['_use_soa']`, restored
on edit and persisted with the `ForLoop`.

### 5.5–5.6 Viewer

`viewer_3d.py` wraps `pyvistaqt.QtInteractor`. Scene never auto-refreshes (manual refresh
button). Mesh builders are dispatched by `AvatarType`.

### 5.7 ★ SoA integration in the 3D viewer

Renderables may mix `Avatar` and `ParticlePopulation`. Populations are expanded via
`as_avatar_view(i)` for display only (O(N) on the viewer side). Element counts sum
`len(population)` for populations.

---

## 6. Utils layer

### 6.1 `safe_eval.py` — Safe evaluation

AST-checked evaluation plus project proxies (`avatar`, `group`, `material`, …). Dynamic
variables are injected into the evaluation context. Population particles are **not**
exposed as `avatar[i]`.

### 6.2 `script_generator.py` — pre.py generation

Full support for AoS avatars and granulometry (including deposits that live as populations
in the GUI — the exported pre.py still emits standard `rigidDisk`/`rigidSphere` creation).
**No dedicated path** yet for a For-loop that only exists as SoA in the GUI (limitation
documented for contributors).

### 6.3 `compute_script_generator.py` — chipy script

Agnostic to AoS/SoA: once bodies are in the DATBOX / body containers, chipy does not see
the GUI storage model.

### 6.4 `fast_granulo_engin.py` — Numpy granulometry

Fully numpy engine without pylmgc90 for large deposits without blocking the UI. **Still
100% AoS** when integrating into `controller.state`. A natural future extension is to feed
`ParticlePopulation.create()` from the internal numpy arrays instead of exploding them into
individual `Avatar` objects.

### 6.5 `convert.py` — Script converter

Executes a `pre.py` under a mock `pre` module and builds a `.lmgc90` dict. Output is
**AoS-only**; large `granulo_Random` deposits become classical `GranuloGeneration` with
`use_particle_population=False`.

---

## 7. Data flows

### 7.1 Creating an avatar (full example — AoS path)

```
User fills AvatarTab → clicks "✅ Create Avatar"
         ↓
AvatarTab._on_create()
  → _build_avatar_from_form()
  → controller.add_avatar(avatar)
         ↓
ProjectController.add_avatar()
  → validate → create pylmgc body → containers + state.avatars
  → state_changed.emit()
         ↓
MainWindow._refresh_all()
```

### 7.2 ★ Massive granulometric deposit (SoA path)

```
User checks “Create as ParticlePopulation” in GranuloTab
         ↓ Generate
GranuloGenerator.generate(config) → centers, radii
         ↓
controller.create_granulo_population_from_arrays(...)
  → ParticlePopulation.create(...)
  → create_avatars_from_population(...)
  → state.particle_populations.append(pop)   # ONE Python object
  → state_changed.emit()                     # ONE signal
```

**Structural difference vs AoS:** one `state_changed` and one list append regardless of
particle count — vs N avatars / N list entries (mitigated by `_batch_mode` and QTimer
batches, but still O(N) on Python structures).

### 7.3 Save and load (with SoA populations)

```
Save:
  state.to_dict()  → MANUAL avatars only in JSON
  save_populations_sidecar(...) → .populations.npz
  particle_populations_sidecar = npz file name

Load:
  load_populations_sidecar → merge meta + arrays
  ProjectState.from_dict()
  _rebuild_pylmgc_objects() (strict order, §4.1)
```

---

## 8. Key systems explained

### 8.1 Avatar indexing (AoS)

Since the “stable avatar_id” refactor, list position is no longer the persistent identity.
Each `Avatar` carries an `avatar_id` (hex uuid) generated once and never reassigned. Groups,
DOF, postpro, and loops reference that id. Legacy positional references are migrated via
`ProjectState._migrate_legacy_avatar_refs()`.

### 8.2 Particle identifiers (SoA)

Symmetrically, particle identity inside a `ParticlePopulation` is **derived**, not stored:
`f"{population_id}:{i}"`. The `population_id` is stable; index `i` is positional — acceptable
because a population is treated as an atomic block (no partial reorder, no single-particle
delete).

### 8.3 Dynamic variables

Expressions in `state.dynamic_vars`, evaluated in definition order and injected into
`SafeEvaluator`. `avatar[i]` only addresses AoS avatars.

### 8.4 Preferences system

| Preference | Impact |
|---|---|
| `show_granulo_individually` | Hides GRANULO avatars (**AoS only**) in tree/tabs; no effect on `ParticlePopulation` |
| `create_pylmgc_on_generate` | Disables pylmgc creation during massive **AoS** generation |
| `script_use_loop` | Emits compact loops in pre.py (AoS) |
| `auto_refresh_viewer` | (reserved) Auto 3D refresh |

### 8.5 ★ SoA (`ParticlePopulation`) vs AoS (`Avatar`) — summary

| Criterion | AoS — `Avatar` | SoA — `ParticlePopulation` |
|---|---|---|
| Storage | 1 Python object per particle in `state.avatars` | 2 numpy arrays + 1 Python object in `state.particle_populations` |
| Homogeneity | No constraint | **Single** type/material/model/colour for the whole population |
| Supported types | All `AvatarType` | Only `RIGID_DISK` and `RIGID_SPHERE` |
| Individual edit | Yes | No — whole population only |
| Identity | Stored stable `avatar_id` | Stable `population_id`; particle id `f"{population_id}:{i}"` |
| Serialisation | Inline JSON (MANUAL only) | JSON metadata + compressed `.npz` sidecar |
| Generation | `add_avatar()` per particle (batch-mitigated) | One call for the whole population |
| Activation | Default path | **Explicit opt-in** checkbox — never automatic |
| GUI memory/CPU | O(N) objects / potential signals | O(1) object / signal; still O(N) pylmgc90 body creation |
| 3D viewer | Direct `Avatar` | Flattened via `as_avatar_view(i)` — O(N) on viewer only |
| `safe_eval` | Supported | **Not supported** for population particles |
| Generated `pre.py` | Full support | Full support for granulometry; **no dedicated path** for SoA For-loops yet |

**Decision rule for contributions:** if new code must produce a large number (typically
more than a few thousand) of particles that are **strictly homogeneous** and do not need
individual editing after creation, prefer SoA. Otherwise stay on the historical AoS path.

---

## 9. Project lifecycle

```
1. NEW PROJECT
   → controller.new_project(name)
   → empty containers, including _pylmgc_population_bodies.clear()
   → state.particle_populations = []

2. CONFIGURATION
   Materials, models, avatars, laws, visibility, DOF, loops, granulo (AoS or SoA)

3. SAVE
   JSON + optional .populations.npz

4. DATBOX GENERATION
   pre.writeDatbox(...) — bodies include both AoS and SoA bodies from _bodies_container

5. PRE.PY SCRIPT
   ScriptGenerator — see §6.2 limitation for SoA For-loops

6. CHIPY SCRIPT
   ComputeScriptGenerator — AoS/SoA agnostic

7. COMPUTATION
   Subprocess running command.py + LMGC90 logs

8. LOAD
   JSON + sidecar + _rebuild_pylmgc_objects()
```

---

## 10. Conventions and patterns

### Naming conventions

| Element | Convention | Example |
|---|---|---|
| Classes | PascalCase | `AvatarTab`, `LMGC90Bridge`, `ParticlePopulation` |
| Methods | snake_case | `_on_create()`, `load_for_edit()` |
| Qt slots | `_on_` prefix | `_on_type_changed()` |
| Qt signals | descriptive suffix | `avatar_created`, `state_changed` |
| Private methods | `_` prefix | `_build_avatar_from_form()` |
| pylmgc containers | `_pylmgc_` prefix | `_pylmgc_materials`, `_pylmgc_population_bodies` |
| Internal SoA flags | `_` prefix in JSON dicts | `_use_soa`, `_population_id` in `template_config` |

### Signal/slot pattern

```python
class AvatarTab(BaseTab):
    avatar_created = pyqtSignal()

    def _on_create(self):
        ...
        self.avatar_created.emit()

# In MainWindow:
self.avatar_tab.avatar_created.connect(self._refresh_all)
```

### Error handling

```python
try:
    avatar = self._build_avatar_from_form()
    self.controller.add_avatar(avatar)
    QMessageBox.information(self, "Success", "✅ Avatar created")
except ValidationError as e:
    QMessageBox.warning(self, "Validation", str(e))
except ValueError as e:
    QMessageBox.critical(self, "Error", f"Invalid values:\n{e}")
except Exception as e:
    QMessageBox.critical(self, "Error", f"Creation failed:\n{e}")
```

---

## 11. Contribution guide

### Adding a new avatar type

1. **`models.py`**: add value to `AvatarType`
2. **`validators.py`**: validation in `AvatarValidator.validate()`
3. **`pylmgc_bridge.py`**: case in `create_avatar()`
4. **`avatar_tab.py`**: type list, `_on_type_changed()`, `_build_avatar_from_form()`
5. **`viewer_3d.py`**: mesh builder in `_MESH_BUILDERS`
6. **`script_generator.py`**: `_write_single_avatar()`
7. *(Optional, SoA)* If the type should be SoA-eligible, add it to
   `_POPULATION_ELIGIBLE_TYPES` (`for_loops_mixin.py`) **and** to the dispatch in
   `LMGC90Bridge.create_avatars_from_population()` — both lists must stay manually in sync
   (no single source of truth today).

### Adding a new tab

1. Create `src/views/tabs/my_tab.py` inheriting `BaseTab`
2. Implement full CRUD pattern
3. Declare signals
4. Export in `src/views/tabs/__init__.py`
5. Instantiate in `MainWindow._create_tabs()`
6. Add to `MainWindow.all_tabs`
7. Connect signals in `MainWindow._connect_signals()`

### Adding a contact law

1. **`models.py`**: `ContactLawType` + category
2. **`validators.py`**: required properties
3. **`pylmgc_bridge.py`**: `create_contact_law()` case
4. **`contact_tab.py`**: UI fields and form builder

### Adding a preference

1. Field on `ProjectPreferences` with default
2. `to_dict()` / `from_dict()`
3. Widget in `PreferencesDialog`
4. Read via `getattr(self.controller.state.preferences, 'my_pref', default)`

### ★ Extending the SoA path to a new generator (e.g. Particle Factory, fast_granulo)

1. Ensure the generator can expose `centers (N, dim)` and `radii (N,)` numpy arrays
2. Build a `ParticlePopulation` via `ParticlePopulation.create(...)` (never the raw constructor)
3. Create pylmgc90 bodies via `create_avatars_from_population(...)` (extend type support first if needed)
4. Append to `state.particle_populations` and optionally `state.populations_groups`
5. Expose AoS/SoA choice with an **explicit opt-in** checkbox — never switch automatically on a hidden threshold
6. Handle symmetric removal and load-time regeneration (`_rebuild_pylmgc_objects`, step 5)
7. Document the “not individually editable” limitation in the UI tooltip

### Testing and debugging

- Application logger: `from src.core.app_logger import get_logger; _log = get_logger('my_module')`
- Application journal: Computation → Application journal (F7)
- LMGC90 logs: Computation → View LMGC90 logs (F6)
- Dynamic variables: Tools → Dynamic variables (Ctrl+V)

---

## Appendix — Quick file reference

| Need | File |
|---|---|
| Add/change a data type | `src/core/models.py` |
| ★ Change the SoA model (mass populations) | `src/core/particle_population.py` |
| ★ Change binary population serialisation | `src/core/particle_population_io.py` |
| Change validation | `src/core/validators.py` |
| Change pylmgc90 calls | `src/core/pylmgc_bridge.py` |
| Add business logic | `src/controllers/project_controller.py` |
| ★ Change granulo SoA path | `src/controllers/granulo_mixin.py` |
| ★ Change For-loop SoA path | `src/controllers/for_loops_mixin.py` |
| Change a tab UI | `src/views/tabs/<name>_tab.py` |
| ★ Change granulo SoA checkbox | `src/views/tabs/granulo_tab.py` |
| ★ Change For-loop SoA checkbox | `src/views/tabs/loop_tab.py` |
| Change 3D view | `src/gui/dialogs/viewer_3d.py` |
| Change generated pre.py | `src/utils/script_generator.py` |
| Change generated chipy script | `src/utils/compute_script_generator.py` |
| Change expression evaluation | `src/utils/safe_eval.py` |
| Change JSON serialisation | `src/core/serializers.py` + `models.py` |
