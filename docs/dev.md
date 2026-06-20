# LMGC90_GUI — Architecture & Contributor Guide

> Version 0.4.0 — Graphical interface for the LMGC90 mechanical simulation code. The current architecture will be replaced in version 0.5.0.

---

## Table of Contents

1. [Overview](#1-overview)
2. [File Structure](#2-file-structure)
3. [Core Layer (Model)](#3-core-layer-model)
4. [Controllers Layer](#4-controllers-layer)
5. [GUI / Views Layer](#5-gui--views-layer)
6. [Utils Layer](#6-utils-layer)
7. [Data Flow](#7-data-flow)
8. [Key Systems Explained](#8-key-systems-explained)
9. [Project Life Cycle](#9-project-life-cycle)
10. [Conventions and Patterns](#10-conventions-and-patterns)
11. [Contribution Guide](#11-contribution-guide)

---

## 1. Overview

LMGC90_GUI is a **PyQt6** desktop application following the **MVC** (Model-View-Controller) pattern. It allows you to create LMGC90 mechanical simulations through a graphical interface without manually writing Python code.

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
│         │           │  (LMGC90Bridge)  │    │  (external)    │   │
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

### Main Dependencies

| Dependency | Role |
|---|---|
| `PyQt6` | UI framework (widgets, signals/slots, threads) |
| `pylmgc90` | LMGC90 library (pre-processing, simulation) |
| `numpy` | Vectorized computations (granulometry, positions) |
| `pyvista` / `pyvistaqt` | 3D visualization of avatars |
| `gmsh` (optional) | Meshing of geometries for deformable bodies |

---

## 2. File Structure

```
lmgc90_gui/
│
├── main.py                          # Entry point, QApplication
│
├── src/
│   ├── core/                        # Model Layer (MVC)
│   │   ├── models.py                # Dataclasses: Material, Model, Avatar, ...
│   │   ├── validators.py            # Data validation
│   │   ├── generators.py            # LoopGenerator, GranuloGenerator
│   │   ├── serializers.py           # JSON save/load (.lmgc90)
│   │   ├── pylmgc_bridge.py         # Conversion of models → pylmgc90 objects
│   │   ├── particle_factory.py      # Progressive generation engine
│   │   ├── avatar_factory.py        # Predefined avatar templates
│   │   ├── app_logger.py            # Application logger
│   │   └── workers/
│   │       └── granulo_worker.py    # QThread for granulo generation
│   │
│   ├── controllers/
│   │   └── project_controller.py    # Central controller (business logic)
│   │
│   ├── views/                       # View Layer (MVC)
│   │   ├── main_window.py           # Main window (QMainWindow)
│   │   ├── tree_view.py             # Model tree (QTreeWidget)
│   │   └── tabs/                    # Working tabs
│   │       ├── base_tab.py          # Base class with safe_eval
│   │       ├── material_tab.py      # Material management
│   │       ├── model_tab.py         # FE model management
│   │       ├── avatar_tab.py        # Standard avatar management
│   │       ├── empty_avatar_tab.py  # Empty avatars (manual contactors)
│   │       ├── loop_tab.py          # Generation loops
│   │       ├── granulo_tab.py       # Granulometric generation
│   │       ├── dof_tab.py           # DOF boundary conditions
│   │       ├── contact_tab.py       # Contact laws
│   │       ├── visibility_tab.py    # Visibility tables
│   │       ├── postpro_tab.py       # Post-processing
│   │       ├── viewer_tab.py        # 3D visualization tab wrapper
│   │       └── ...
│   │
│   ├── gui/
│   │   └── dialogs/                 # Dialogs and wizards
│   │       ├── dialogs.py           # DynamicVarsDialog, PreferencesDialog, DuplicateDialog
│   │       ├── setup_wizard.py      # Project wizard
│   │       ├── factory_wizard.py    # Particle Factory wizard (+ FactoryTab)
│   │       ├── granulo_wizard.py    # Granulometry wizard
│   │       ├── mesh_wiz_def.py      # Deformable body wizard (FEM)
│   │       ├── masonery_wizard.py   # Masonry wizard
│   │       ├── fast_granulo_dialg.py # Fast numpy generation dialog
│   │       ├── viewer_3d.py         # PyVista widget (3D visualization)
│   │       ├── chipy_routines_dialog.py # chipy routine config
│   │       ├── app_log_dialog.py    # Log visualization
│   │       └── convert_dialog.py    # pylmgc90 script conversion
│   │
│   └── utils/
│       ├── safe_eval.py             # Secure evaluator + project context proxies
│       ├── script_generator.py      # pre.py script generation
│       ├── compute_script_generator.py # chipy script generation (command.py)
│       ├── fast_granulo_engin.py    # High-perf numpy granulo engine
│       └── convert.py              # pylmgc90 script → .lmgc90 converter
```

---

## 3. Core Layer (Model)

### 3.1 `models.py` — The Dataclasses

All project entities are **Python dataclasses**. They are the source of truth.

```python
# Model hierarchy
ProjectState
├── List[Material]          # Materials (RIGID, ELAS, ...)
├── List[Model]             # FE models (Rxx2D, T3xxx, ...)
├── List[Avatar]            # Rigid/deformable bodies
├── List[ContactLaw]        # Contact laws (IQS_CLB, ...)
├── List[VisibilityRule]    # Visibility tables
├── List[DOFOperation]      # Boundary conditions
├── List[Loop]              # Geometric loops (circle, grid...)
├── List[ForLoop]           # Generic for loops (JSON template)
├── List[GranuloGeneration] # Granulometric deposits
├── List[PostProCommand]    # Post-processing commands
├── Dict[str, List[int]]    # Avatar groups (name → indices)
├── Dict[str, Any]          # Dynamic variables (expressions)
├── List[dict]              # Factories (serialized FactoryConfig)
└── ProjectPreferences      # User preferences
```

**Each dataclass** exposes `to_dict()` and `from_dict()` for JSON serialization. Example:

```python
@dataclass
class Avatar:
    avatar_type: AvatarType       # Enum: rigidDisk, roughWall, ...
    center: List[float]
    material_name: str
    model_name: str
    color: str = "BLUEx"
    origin: AvatarOrigin = AvatarOrigin.MANUAL
    radius: Optional[float] = None
    # ... other type-specific fields
```

**Important Enums:**

| Enum | Notable Values |
|---|---|
| `AvatarType` | `RIGID_DISK`, `ROUGH_WALL`, `MESH_DEFORMABLE`, `EMPTY_AVATAR`, ... |
| `AvatarOrigin` | `MANUAL`, `LOOP`, `GRANULO` |
| `MaterialType` | `RIGID`, `ELAS`, `ELAS_PLAS`, ... |
| `ContactLawType` | `IQS_CLB`, `MAC_CZM`, `ELASTIC_WIRE`, ... |
| `UnitSystem` | `SI`, `CGS` |

---

### 3.2 `validators.py` — Validation

Each entity has its own validator:

```python
MaterialValidator.validate_or_raise(material)  # Name ≤ 5 chars, density > 0
ModelValidator.validate_or_raise(model)         # Element compatible with physics+dim
AvatarValidator.validate_or_raise(avatar, model) # Parameters based on type
ContactLawValidator.validate_or_raise(law)      # Required properties
```

The validators raise `ValidationError` (inherits from `Exception`), caught by the View to display a `QMessageBox`.

---

### 3.3 `pylmgc_bridge.py` — Bridge to pylmgc90

`LMGC90Bridge` is a **static** class that converts the dataclasses into `pylmgc90.pre` objects:

```python
LMGC90Bridge.create_material(material)       → pre.material(...)
LMGC90Bridge.create_model(model)             → pre.model(...)
LMGC90Bridge.create_avatar(avatar, mod, mat) → pre.rigidDisk(...) / pre.avatar(...)
LMGC90Bridge.create_contact_law(law)         → pre.tact_behav(...)
LMGC90Bridge.create_visibility_rule(rule, b) → pre.see_table(...)
LMGC90Bridge.apply_dof_operation(op, body)   → body.translate(...) / body.imposeDrivenDof(...)
```

**Complex Cases Handled:**
- Deformable bodies: `pre.buildMesh2D`, `pre.buildMeshH8`, `pre.readMesh` + `pre.buildMeshedAvatar`
- Masonry bricks: `pre.brick2D/3D` + `brick.rigidBrick(...)`
- Empty avatars with contactors: step-by-step creation via `pre.avatar()` → `addBulk` → `addNode` → `addContactors`

---

### 3.4 `generators.py` — Position Generation

```python
LoopGenerator.generate_positions(loop: Loop) → List[[x, y]]
# Dispatches to: generate_circle / generate_grid / generate_line / generate_spiral

GranuloGenerator.generate(config) → (nb_particles, coordinates_array, radii_array)
# Calls pre.granulo_Random then pre.depositInBox2D / depositInDisk2D / ...
```

---

### 3.5 `particle_factory.py` — Particle Factory

A **progressive** particle generation system (inspired by EDEM):

- `FactoryConfig`: complete dataclass (type, zone, schedule, container)
- `ParticleFactory`: engine (validates, assigns body indices, generates code)
- `PreCodeGenerator`: generates the `pre.py` block (invisible creation + schedule)
- `ChipyCodeGenerator`: generates the `chipy.py` block (wave activation)

---

### 3.6 `serializers.py`

```python
ProjectSerializer.save(state, filepath)   # JSON → .lmgc90 file
ProjectSerializer.load(filepath)          # .lmgc90 file → ProjectState
```

The `.lmgc90` format is **pure JSON**. Only avatars with `origin == MANUAL` are serialized; generated avatars (loops, granulo) are regenerated on loading.

---

## 4. Controllers Layer

### 4.1 `project_controller.py` — The Central Controller

`ProjectController(QObject)` is the **heart of the application**. It:

1. Maintains the project state (`self.state: ProjectState`)
2. Maintains the pylmgc90 objects in memory:
   ```python
   self._materials_container   # pre.materials()
   self._models_container      # pre.models()
   self._bodies_container      # pre.avatars()
   self._contact_laws_container # pre.tact_behavs()
   self._visibility_container  # pre.see_tables()
   self._postpro_container     # pre.postpro_commands()
   
   self._pylmgc_materials: Dict[str, Any]  # name → pylmgc90 object
   self._pylmgc_models: Dict[str, Any]
   self._pylmgc_bodies: List[Any]          # indexed like state.avatars
   self._pylmgc_laws: Dict[str, Any]
   ```
3. Emits `state_changed = pyqtSignal()` on every modification

**Fundamental invariant:** `self._pylmgc_bodies[i]` always corresponds to `self.state.avatars[i]`.

#### Controller API (main methods)

```python
# Project
controller.new_project(name)
controller.save_project(filepath?)
controller.load_project(filepath)        # → rebuilds everything via _rebuild_pylmgc_objects()

# Material CRUD
controller.add_material(material)        # validates + creates pylmgc object + state
controller.update_material(old_name, m)  # updates refs in avatars
controller.remove_material(name)

# Model CRUD (identical)
# Avatar CRUD
controller.add_avatar(avatar, create_pylmgc=True)  # create_pylmgc=False for performance
controller.update_avatar(index, avatar)
controller.remove_avatar(index)
controller.duplicate_avatar(index, n, offset, group?)
controller.duplicate_group(group_name, n, offset, prefix?)

# Generation
controller.generate_loop(loop)           # → creates avatars + adds to the group
controller.generate_granulo(config)      # → via GranuloGenerator
controller.generate_for_loop(for_loop)   # → generic for loop

# DATBOX
controller.generate_datbox(output_path) # → pre.writeDatbox(...)
```

#### `_rebuild_pylmgc_objects()` — Reconstruction on Loading

When loading a project, the order is **strict**:
1. Materials → models → MANUAL avatars → loops → granulo → For loops
2. Contact laws → visibility → DOF

If an error occurs (e.g.: missing material), it is stored in `state.load_warnings` and displayed in the UI.

#### Batch Mode

```python
self._batch_mode = True   # Disables state_changed.emit() during creation
# ... create N avatars ...
self._batch_mode = False
self.state_changed.emit()  # A single signal at the end
```

---

## 5. GUI / Views Layer

### 5.1 `main_window.py` — Main Window

`MainWindow(QMainWindow)` orchestrates everything:

```
MainWindow
├── MenuBar                # File, Wizards, Tools, Computation, Tabs, Help
├── ToolBar                # New, Open, Save, DATBOX, Script
├── DockWidget (left)
│   └── ModelTreeView      # QTreeWidget tree
└── Central (vertical QSplitter)
    ├── QTabWidget         # Working tabs (70%)
    │   ├── MaterialTab
    │   ├── ModelTab
    │   ├── AvatarTab
    │   └── ...
    └── QWidget (bottom 30%)  # LMGC90 Viz + ParaView buttons
```

**Tab management:** Tabs can be opened/closed dynamically. `material_tab` and `model_tab` are **essential** (cannot be closed). Each tab is instantiated only once and hidden/shown.

**Signal connections:**
```python
# Each tab emits signals → MainWindow._refresh_all()
self.material_tab.material_created.connect(self._refresh_all)
# _refresh_all() calls tree_view.refresh() + tab.refresh() on all tabs
```

---

### 5.2 `tree_view.py` — Model Tree

`ModelTreeView(QObject)` manages a `QTreeWidget` displaying the complete structure:

```
LMGC90 Model
├── Materials (N)
├── Models (N)
├── Avatars (N) [filtered according to the show_granulo_individually preference]
├── Avatar Groups
├── Contact Laws
├── Visibility Tables
├── DOF Operations
├── Loops
├── Granulo Deposits
└── Post-Processing
```

**Signal emitted:** `item_selected = pyqtSignal(str, object)` → element type + data. `MainWindow` receives this signal and loads the element into the appropriate tab.

**Context menu:** Right-click on Avatar → `DuplicateDialog`. Right-click on Group → duplication of the entire group.

---

### 5.3 `base_tab.py` — Base Tab Class

All tabs inherit from `BaseTab(QWidget)`. It provides:

```python
# Secure evaluation of expressions (uses SafeEvaluator)
self.eval_float(text, default, field_name)  # "0.5 * pi" → 1.5707...
self.eval_int(text, default, field_name)
self.eval_list(text, expected_length, field_name)  # "1.0, 2.0" → [1.0, 2.0]
self.eval_dict(text, field_name)    # "k=1, nu=0.3" → {"k": 1, "nu": 0.3}

# Contextual help label
self.add_expression_help_label(layout)
```

The evaluator gives access to the **full project context** in the form fields:
`avatar[0].x`, `group['mur'][0].radius`, `material['acier'].density`, etc.

---

### 5.4 The Tabs (tabs/)

Each tab follows the same **CRUD pattern**:

```
Tab
├── QTreeWidget        # List of existing elements
├── Buttons (✏️ Edit, 🗑️ Delete)
├── QFormLayout        # Creation/editing form
├── Buttons (✅ Create, 💾 Save, ❌ Cancel, 🔄 Reset)
└── Signals emitted    # element_created, element_updated, element_deleted
```

**Methods to implement in each tab:**

```python
def _setup_ui(self)              # Interface construction
def _connect_signals(self)       # Signal/slot connection
def _on_create(self)             # Create an element
def _on_edit_from_tree(self)     # Load for editing from the tree
def _on_update(self)             # Save the modifications
def _on_delete(self)             # Delete
def load_for_edit(self, ...)     # Fill the form from an object
def refresh(self)                # Refresh the display
```

#### `avatar_tab.py` — Avatar Tab

Manages 18+ types of 2D/3D avatars. The `_on_type_changed()` method dynamically shows/hides fields based on the selected type. `_build_avatar_from_form()` builds the `Avatar` object from the visible fields.

#### `model_tab.py` — Model Tab

Complex management of options depending on the physics (MECAx/THERx/POROx/MULTI) and the element. `_on_element_changed()` dynamically rebuilds the option combo boxes.

#### `granulo_tab.py` — Granulometric Generation

Uses a **QThread** (`GranuloWorker`) for the computations. Avatar creation is done in **progressive batches** via a `QTimer` so as not to block the UI:

```
_on_generate() → GranuloWorker.run() → data_ready signal
                                          ↓
                               _on_data_ready() → QTimer(0ms)
                                                     ↓
                               _create_next_avatar() × N [batches of 50-100]
                                                     ↓
                               _on_creation_completed()
```

---

### 5.5 `viewer_3d.py` — 3D Visualization

`Viewer3D(QWidget)` wrapping `pyvistaqt.QtInteractor`. **Never** refreshes automatically, to avoid freezes. The user clicks "🔄 Refresh the scene".

**Mesh construction:**
```python
build_avatar_mesh(avatar) → pv.PolyData
# Dispatches to _MESH_BUILDERS[avatar.avatar_type]
# E.g.: _mesh_rigid_disk → pv.Circle().extrude(h)
#       _mesh_rigid_polygon → pv.PolyData(vertices)
#       _mesh_deformable → rebuilt from mesh_params (geom)
```

**Color modes:** LMGC90 (by color code) | By type | By material | By origin  
**Interaction modes:** Navigation | Selection (avatar_clicked signal) | Ruler (distance measurement)

---

### 5.6 The Wizards (dialogs/)

Multi-page `QWizard` assistants for complex tasks:

| Wizard | Pages | Result |
|---|---|---|
| `ProjectSetupWizard` | Project → Dim → Mat → Mod → Avatar → Contact → Visibility → Summary | Fully initialized project |
| `GranuloWizard` | Distribution → Container → Properties → Summary | Generated granulo deposit |
| `MeshWizard` | Intro → Dim → Mat → Mod → Geom → Refinement → Boundary → Summary | FEM deformable body |
| `MasonryWizard` | Config → Model → Summary | Masonry wall |
| `FactoryWizard` | Intro → Zone → Particles → Container → Schedule → Summary | Configured factory |

---

## 6. Utils Layer

### 6.1 `safe_eval.py` — Secure Evaluation

**Problem solved:** Allow users to enter Python expressions (`avatar[0].x + 0.1`, `sqrt(2) * radius`) in the forms without security risk.

**Architecture:**

```python
# 1. SafeEvaluator — AST checking + isolated eval
ev = SafeEvaluator(allowed_names=context_dict)
result = ev.eval_expression("avatar[0].x * 2")

# 2. Proxies — access to project data
AvatarCollectionProxy  # avatar[i], len(avatar), list(avatar)
AvatarProxy            # .center, .x, .y, .z, .radius, .nodes[1].coor, ...
GroupProxy             # group['name'][0].center
MaterialProxy          # material['acier'].density
ModelProxy             # model['rigid'].physics

# 3. build_eval_context() — builds the full context
ctx = build_eval_context(controller)
# ctx contains: math, np, avatar, group, material, model,
#               avatars_by_color(), avatars_by_material(), ...
#               + all the project's dynamic variables
```

**Security:** `SafeEvaluator._check_safe()` walks the AST and rejects any disallowed node (import, exec, dangerous attributes, etc.).

---

### 6.2 `script_generator.py` — pre.py Script Generation

`ScriptGenerator(controller)` generates a Python script reproducing the project:

```
generate(output_path)
├── _write_header()           # Header comment
├── _write_imports()          # from pylmgc90 import pre, numpy, math
├── _write_dynamic_vars()     # Evaluation and injection of dynamic vars
├── _write_containers()       # mats, mods, bodies, tacts, sees, posts
├── _write_materials()        # mat_NAME = pre.material(...)
├── _write_models()           # mod_NAME = pre.model(...)
├── _write_avatars_manual()   # MANUAL avatars (with loop or individual option)
│   ├── _write_avatars_manual_loop()   # Loop mode (by groups)
│   │   ├── _write_masonry_group_loop()  # Masonry brick loops
│   │   └── _write_standard_group_loop() # for loop + list of centers
│   └── _write_single_avatar()          # Individual avatar
├── _write_for_loops()        # Generic For loops
├── _write_loops()            # Geometric loops (circle, grid...)
├── _write_granulo()          # pre.granulo_Random + depositIn*
├── _write_contact_laws()     # pre.tact_behav(...)
├── _write_visibility()       # pre.see_table(...)
├── _write_dof_operations()   # body.translate / imposeDrivenDof
├── _write_postpro()          # pre.postpro_command(...)
├── _write_factories()        # Particle Factories (pre-computed code)
└── _write_datbox()           # pre.writeDatbox(...)
```

**`script_use_loop` preference:** If enabled, avatars from the same homogeneous group are grouped into a `for _c in _centers_<group>:` loop for a more compact script.

---

### 6.3 `compute_script_generator.py` — chipy Script Generation

`ComputeScriptGenerator(controller)` generates `command.py` (simulation loop) according to the parameters configured in `ChipyRoutinesDialog`.

Generated sections:
1. chipy configuration (`SetDimension`, `ReadDatbox`, ...)
2. Initialization of the Particle Factories (invisibility + schedule)
3. Main loop `for k in range(nb_steps):`
   - FreeVelocity RBDY2/RBDY3/FEM
   - Contact detection (selected detectors)
   - NLGS resolution
   - Factory wave activation
   - ComputeDof + UpdateStep
   - Extraction (energy, GBV, inspection)
   - WriteOut + WriteDisplayFiles
4. Finalization

---

### 6.4 `fast_granulo_engin.py` — Numpy Granulometry

A **pylmgc90-free**, fully numpy engine, for generating thousands of particles without blocking the UI:

```python
GranuloFastEngine.generate(nb, rmin, rmax, container_type, ...)
# → Placement in batches (candidates → bbox filtering → vectorized collision filtering)
# → FastGranuloResult with List[FastParticle]

GranuloFileWriter.write(result, output_dir)
# → Writes DATBOX/BODIES.DAT directly (bypassing pylmgc90)

GranuloStateIntegrator.integrate(result, controller)
# → Adds the avatars in a single batch into controller.state
```

---

### 6.5 `convert.py` — Script Converter

Converts an existing `pre.py` script into a `.lmgc90` file by **executing the script** with a `_MockPre` module that intercepts all `pre.*` calls:

```python
class _MockPre:          # Replaces pylmgc90.pre during exec
class _AvatarObj         # Proxy of a rigid avatar
class _MeshAvatarObj     # Proxy of a deformable body
class _EmptyAvatarObj    # Proxy of an empty avatar
class _BrickObj          # Proxy of a masonry brick
class _WallObj           # Proxy of a masonry wall

class Converter:
    run()                # Executes the script with the mock
    to_lmgc90_dict()    # Builds the project JSON

# CLI:
# python convert.py my_script.py -o output.lmgc90
```

---

## 7. Data Flow

### 7.1 Creating an Avatar (complete example)

```
User fills in AvatarTab → clicks "✅ Create Avatar"
         ↓
AvatarTab._on_create()
  → _build_avatar_from_form()   # Values → Avatar dataclass
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
  → self.state_changed.emit()   # if not in batch_mode
         ↓
AvatarTab.avatar_created.emit()
         ↓
MainWindow._refresh_all()
  → tree_view.refresh()         # Tree updated
  → [all tabs].refresh() # Combos updated
```

### 7.2 Saving and Loading

```
Saving:
  ProjectController.save_project()
    → ProjectSerializer.save(state, filepath)
      → state.to_dict()            # Only MANUAL avatars
        → json.dump(data, file)   # .lmgc90 file

Loading:
  ProjectController.load_project(filepath)
    → ProjectSerializer.load(filepath)
      → ProjectState.from_dict(data)   # Dataclasses rebuilt
    → _rebuild_pylmgc_objects()        # Strict-order reconstruction
      1. Materials + Models           # pylmgc90 objects recreated
      2. MANUAL Avatars                # bridge.create_avatar()
      3. Loops → generate_loop()     # LOOP avatars recreated
      4. Granulo → generate_granulo()  # GRANULO avatars recreated
      5. For Loops → generate_for_loop()
      6. Laws + Visibility + DOF
```

---

## 8. Key Systems Explained

### 8.1 Avatar Indexing

The index of an avatar in `state.avatars` is its identifier everywhere:
- `state.avatar_groups["mur"] = [0, 1, 2, 3]` → indices in state.avatars
- `state.operations[0].target_value = 5` → avatar #5
- `self._pylmgc_bodies[5]` → pylmgc90 object of avatar #5

**⚠️ Caution when deleting:** `remove_avatar(index)` does a `pop(index)` which shifts all subsequent indices. Groups and operations referencing avatars with a higher index become invalid. This is a known limitation that will require a future redesign (stable IDs).

### 8.2 Dynamic Variables

Dynamic variables (`state.dynamic_vars`) are **Python expressions**:
```python
{"thickness": "0.5", "radius": "thickness * 2 + 0.1", "x_wall": "avatar[0].x"}
```

They are evaluated in definition order and injected into `SafeEvaluator`'s context. Thus, in a form, the user can write `radius` and get the computed value.

### 8.3 Preferences System

`ProjectPreferences` is stored in `state.preferences` and saved with the project. Important preferences:

| Preference | Impact |
|---|---|
| `show_granulo_individually` | Hides GRANULO avatars in the tree and tabs |
| `create_pylmgc_on_generate` | Disables pylmgc creation during massive generation |
| `script_use_loop` | Generates compact loops in the pre.py script |
| `auto_refresh_viewer` | (reserved) Automatic refresh of the 3D view |

### 8.4 Particle Factory

Factories are persisted as `List[dict]` in `state.factories`. On loading and when generating the script, `ParticleFactory.from_list_of_dicts()` rebuilds the engine, recomputes the body indices, and generates the code blocks.

---

## 9. Project Life Cycle

```
1. NEW PROJECT
   MainWindow._on_new_project()
   → controller.new_project(name)
   → _reset_containers() [empty pylmgc containers]
   → state = ProjectState(name)

2. CONFIGURATION
   Materials Tab → add_material()
   Models Tab   → add_model()
   Avatars Tab  → add_avatar()
   ... (laws, visibility, DOF, loops, granulo)

3. SAVING
   Ctrl+S → save_project()
   → state.to_dict() → JSON

4. DATBOX GENERATION
   Tools → DATBOX → controller.generate_datbox(path)
   → pre.writeDatbox(dim, mats, mods, bodies, tacts, sees, post)

5. PRE.PY SCRIPT GENERATION
   Tools → Python Script → ScriptGenerator.generate(path)

6. CHIPY SCRIPT GENERATION (command.py)
   Computation → Generate Script → ComputeScriptGenerator.generate(path, params)

7. COMPUTATION
   Computation → Run → compute_tab.run_computation()
   → Executes command.py in a subprocess
   → Displays the LMGC90 logs

8. LOADING
   File → Open → controller.load_project(path)
   → ProjectState.from_dict() + _rebuild_pylmgc_objects()
```

---

## 10. Conventions and Patterns

### Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Classes | PascalCase | `AvatarTab`, `LMGC90Bridge` |
| Methods | snake_case | `_on_create()`, `load_for_edit()` |
| Qt Slots | `_on_` prefix | `_on_type_changed()` |
| Qt Signals | Descriptive suffix | `avatar_created`, `state_changed` |
| Private methods | `_` prefix | `_build_avatar_from_form()` |
| pylmgc containers | `_pylmgc_` prefix | `_pylmgc_materials` |

### Signal/Slot Pattern

```python
# In a tab:
class AvatarTab(BaseTab):
    avatar_created = pyqtSignal()   # Declaration at class level

    def _on_create(self):
        ...
        self.avatar_created.emit()  # Emission after successful action

# In MainWindow:
self.avatar_tab.avatar_created.connect(self._refresh_all)
```

### Error Handling

```python
try:
    # Business logic
    avatar = self._build_avatar_from_form()
    self.controller.add_avatar(avatar)
    # Success
    QMessageBox.information(self, "Success", "✅ Avatar created")
except ValidationError as e:
    QMessageBox.warning(self, "Validation", str(e))
except ValueError as e:
    QMessageBox.critical(self, "Error", f"Invalid values:\n{e}")
except Exception as e:
    QMessageBox.critical(self, "Error", f"Creation failed:\n{e}")
```

---

## 11. Contribution Guide

### Adding a New Avatar Type

1. **`models.py`**: Add the value to `AvatarType`
2. **`validators.py`**: Add the validation in `AvatarValidator.validate()`
3. **`pylmgc_bridge.py`**: Add the case in `LMGC90Bridge.create_avatar()`
4. **`avatar_tab.py`**:
   - Add the type to `AVATAR_TYPES_2D` or `AVATAR_TYPES_3D`
   - Handle field display in `_on_type_changed()`
   - Build the avatar in `_build_avatar_from_form()`
5. **`viewer_3d.py`**: Add the mesh builder to `_MESH_BUILDERS`
6. **`script_generator.py`**: Handle the generation in `_write_single_avatar()`

### Adding a New Tab

1. Create `src/views/tabs/my_tab.py` inheriting from `BaseTab`
2. Implement the complete CRUD pattern
3. Declare the necessary signals
4. Import it in `src/views/tabs/__init__.py`
5. Instantiate it in `MainWindow._create_tabs()`
6. Add it to `MainWindow.all_tabs`
7. Connect the signals in `MainWindow._connect_signals()`

### Adding a New Contact Law

1. **`models.py`**: Add it to `ContactLawType` and the appropriate category in `CONTACT_LAW_CATEGORIES`
2. **`validators.py`**: Add the required properties to `ContactLawValidator._REQUIRED_PROPS`
3. **`pylmgc_bridge.py`**: Add the case in `create_contact_law()`
4. **`contact_tab.py`**: Add the UI fields in `_on_type_changed()` and `_build_law_from_form()`

### Adding a Preference Parameter

1. **`models.py`**: Add the field to `ProjectPreferences` with a default value
2. Add it to `to_dict()` and `from_dict()`
3. **`dialogs.py`**: Add the widget in `PreferencesDialog._build_perf_tab()` (or another tab)
4. Add it to `_load_preferences()` and `get_preferences()`
5. Use the preference via `getattr(self.controller.state.preferences, 'my_pref', default)`

### Testing and Debugging

- **Application logger**: `from src.core.app_logger import get_logger; _log = get_logger('my_module')`
- **Journal**: Computation → Application Journal (F7)
- **LMGC90 Logs**: Computation → View LMGC90 Logs (F6)
- **Dynamic Variables**: Tools → Dynamic Variables (Ctrl+V)

---

## Appendix — Quick Reference Files

| Need | File |
|---|---|
| Add/modify a data type | `src/core/models.py` |
| Modify validation | `src/core/validators.py` |
| Modify the pylmgc90 call | `src/core/pylmgc_bridge.py` |
| Add business logic | `src/controllers/project_controller.py` |
| Modify a tab's UI | `src/views/tabs/<name>_tab.py` |
| Modify the 3D view | `src/gui/dialogs/viewer_3d.py` |
| Modify the generated pre.py script | `src/utils/script_generator.py` |
| Modify the generated chipy script | `src/utils/compute_script_generator.py` |
| Modify expression evaluation | `src/utils/safe_eval.py` |
| Modify JSON serialization | `src/core/serializers.py` + `models.py` |
