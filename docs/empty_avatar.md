# Empty Avatar (Advanced Customization)

**Empty Avatar tab** Allows you to create **avatars with custom contactors**: either an empty body (`emptyAvatar`) fully defined by its contactors, or the addition of contactors to an **existing deformable body** (FEM mesh).  
This is the most flexible tool in LMGC90_GUI for advanced cases that do not fit into the standard rigid avatar types.

![](captures/avatar_vide_2disques.JPG)

---

## Two Operating Modes

The **Mode** field at the top of the form switches between two distinct behaviors:

| Mode | Description |
|------|-------------|
| **Empty avatar (emptyAvatar)** | Creates a new pylmgc90 body fully assembled from its contactors. The body is rigid, but its geometry is defined manually. |
| **Existing deformable body** | Adds contact contactors to a deformable body (FEM mesh) already created via the mesh wizard. Calls `body.addContactors()` directly on the pylmgc90 object. |

---

## Mode 1 — Empty Avatar (emptyAvatar)

### Principle

An empty avatar is a rigid body whose geometry is not predefined. pylmgc90 assembles it in three steps:

1. Creation of an empty body `pre.avatar(dimension=…)`
2. Addition of a rigid bulk `pre.rigid2d()` or `pre.rigid3d()`
3. Addition of a main node and the **contactors** that define the shape

The inertial properties (mass, moment of inertia) are computed automatically from the contactors' geometry via `body.computeRigidProperties()`.

### Form Fields

| Field | Description |
|-------|-------------|
| **Dimension** | `2` or `3`. Determines the list of available contactor shapes and the format of the center. |
| **Center (x,y) or (x,y,z)** | Coordinates of the reference main node. Accepts Python expressions. |
| **Material** | `RIGID`-type material assigned to the body. |
| **Model** | Model with the `Rxx2D` (2D) or `Rxx3D` (3D) element. |
| **Color** | Color for LMGC90 interaction (5 characters); not very important. |

---

## Mode 2 — Existing Deformable Body

### Principle

This mode does not create a new avatar — it enriches a deformable body (FEM mesh) already present in the project by adding surface contactors to it. This is necessary so that the deformable body can interact with other bodies (rigid or deformable).

The function called on the pylmgc90 object is: `body.addContactors(shape=…, color=…, **params)`.

### Fields Specific to This Mode

| Field | Description |
|-------|-------------|
| **Deformable body** | Dropdown list of `MESH_DEFORMABLE`-type bodies present in the project. The displayed format is `#index — geometry (material/model)`. |
| **Group (group=)** | `group` parameter passed to `addContactors()`. Determines which node group of the mesh the contactor is applied to (e.g.: `102` for group index 102). Leave empty to apply to all nodes. |

> **Important:** the deformable body must have been created and rebuilt in memory (present in `_pylmgc_bodies`) before adding contactors. If the project was just loaded from a JSON file without rebuilding, the pylmgc90 body does not yet exist in memory and adding contactors will fail.

---

## Managing Contactors

Each row in the **Contactors to add** list corresponds to a `body.addContactors()` call. Click **➕ Add a contactor** to create a new row. Click **×** to delete a row.

### Columns of a Contactor Row

| Column | Description |
|---------|-------------|
| **Shape** | pylmgc90 contactor type. The list adapts to the mode (empty avatar or deformable) and the dimension. |
| **Color** | Contactor color (5-character LMGC90 code). Independent of the body's color, but very important for contact detection. |
| **Params** | Geometric parameters of the contactor in the format `key=value, key=value`. Automatically filled with a suggestion based on the chosen shape. |

---

## Available Contactor Shapes

### 2D Empty Avatar — `shapes_2d`

| Shape | Description | Parameters | Default Suggestion |
|-------|-------------|------------|-----------------------|
| `DISKx` | 2D disk | `byrd` = radius | `byrd=0.3` |
| `xKSID` | 2D discrete disk | `byrd` = radius | `byrd=0.3` |
| `JONCx` | 2D jonc / ellipse | `axe1` = long half-axis, `axe2` = short half-axis | `axe1=1.0, axe2=0.1` |
| `POLYG` | 2D polygon | `nb_vertices` = number of vertices, `vertices` = list `[[x,y],…]` | `nb_vertices=4, vertices=[[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]]` |
| `PT2Dx` | 2D point node (FEM) | none | *(empty)* |

### 3D Empty Avatar — `shapes_3d`

| Shape | Description | Parameters | Default Suggestion |
|-------|-------------|------------|-----------------------|
| `SPHER` | 3D sphere | `byrd` = radius | `byrd=0.3` |
| `PLANx` | 3D plane | `axe1`, `axe2`, `axe3` = axis dimensions | `axe1=1.0, axe2=1.0, axe3=0.1` |
| `CYLND` | 3D cylinder | `byrd` = radius, `High` = height | `byrd=0.5, High=1.0` |
| `DNLYC` | 3D hollow cylinder | `byrd` = radius, `High` = height | `byrd=0.5, High=1.0` |
| `POLYR` | 3D polyhedron | `nb_vertices` = number of vertices, `vertices` = list `[[x,y,z],…]` | `nb_vertices=8, vertices=[[−1,−1,−1],[1,−1,−1],…]` |
| `PT3Dx` | 3D point node (FEM) | none | *(empty)* |

### 2D Deformable Body — `mesh_shapes_2d`

These shapes are intended to be added to a 2D FEM mesh. They define surface contactors for rigid-deformable interactions.

| Shape | Description | Usage |
|-------|-------------|-------|
| `ALpxx` | Line contactor for 2D FEM masonry | `ALpMECAx` interactions (CLALp / MECAx) |
| `CLxx` | 2D continuous line contactor | `DKMECAx` interactions (disk / MECAx) |
| `DISKL` | Disk on a 2D FEM node | Disk-disk interaction on a mesh |
| `PT2TL` | 2D transmission point | FEM node-to-node coupling |

### 3D Deformable Body — `mesh_shapes_3d`

| Shape | Description | Usage |
|-------|-------------|-------|
| `ASpxx` | Surface contactor for 3D FEM spheres | `SPMECAx` interactions (sphere / 3D MECAx) |
| `CSpxx` | 3D continuous surface contactor | Generic 3D rigid-deformable interactions |
| `PT3Dx` | 3D FEM point node | 3D FEM node-to-node coupling |

---

## Parameter Details by Shape

### DISKx / xKSID / SPHER — Disk, Discrete Disk, Sphere

```
byrd=0.3
```

| Parameter | Description |
|-----------|-------------|
| `byrd` | Radius of the contactor (m). Corresponds to the contact radius used in the detectors. |

---

### JONCx — 2D Jonc / Ellipse

```
axe1=1.0, axe2=0.1
```

| Parameter | Description |
|-----------|-------------|
| `axe1` | Main half-axis (m) — long axis of the ellipse. |
| `axe2` | Secondary half-axis (m) — short axis of the ellipse. |

---

### POLYG — 2D Polygon

```
nb_vertices=4, vertices=[[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]]
```

| Parameter | Description |
|-----------|-------------|
| `nb_vertices` | Number of vertices of the polygon. |
| `vertices` | List of local vertex coordinates `[[x1,y1],[x2,y2],…]`. The coordinates are relative to the center of the body. The vertices must be in trigonometric (counter-clockwise) order. |

---

### PLANx — 3D Plane

```
axe1=1.0, axe2=1.0, axe3=0.1
```

| Parameter | Description |
|-----------|-------------|
| `axe1` | Dimension along the first axis of the plane (m). |
| `axe2` | Dimension along the second axis of the plane (m). |
| `axe3` | Thickness of the plane (m) — used for computing the inertial properties. |

---

### CYLND / DNLYC — 3D Cylinder

```
byrd=0.5, High=1.0
```

| Parameter | Description |
|-----------|-------------|
| `byrd` | Radius of the cylinder (m). |
| `High` | Height (axial length) of the cylinder (m). Note the capital letter. |

---

### POLYR — 3D Polyhedron

```
nb_vertices=8, vertices=[[-1.,-1.,-1.],[1.,-1.,-1.],[1.,1.,-1.],[-1.,1.,-1.],
                          [-1.,-1.,1.],[1.,-1.,1.],[1.,1.,1.],[-1.,1.,1.]]
```

| Parameter | Description |
|-----------|-------------|
| `nb_vertices` | Number of vertices of the polyhedron. |
| `vertices` | List of 3D coordinates for each vertex `[[x,y,z],…]`. Local coordinates relative to the center. |

> For a convex polyhedron, the vertices can be provided in any order — pylmgc90 computes the convex hull. For a non-convex polyhedron, the order of the faces must be consistent.

---

### PT2Dx / PT3Dx — Point Nodes

No parameters. These contactors represent a contact point at a node.

```
(Params field empty)
```

---

## Complete Examples

### 2D Empty Avatar — 6-Vertex Polygonal Body

```
Mode      : Empty avatar (emptyAvatar)
Dimension : 2
Center    : 0.0, 0.5
Material  : BRIQx
Model     : rigid
Color     : REDxx

Contactor 1 :
  Shape  : POLYG
  Color  : REDxx
  Params : nb_vertices=6, vertices=[[-0.1,-0.05],[0.1,-0.05],[0.15,0.0],
                                    [0.1,0.05],[-0.1,0.05],[-0.15,0.0]]
```

---

### 3D Empty Avatar — Body with a Sphere and a Cylinder

```
Mode      : Empty avatar (emptyAvatar)
Dimension : 3
Center    : 0.0, 0.0, 0.5
Material  : ACIER
Model     : rig3D
Color     : CYANx

Contactor 1 :
  Shape  : SPHER
  Color  : CYANx
  Params : byrd=0.2

Contactor 2 :
  Shape  : CYLND
  Color  : GRAYx
  Params : byrd=0.05, High=0.8
```

---

### Adding Contactors to a Deformable Body

```
Mode             : Existing deformable body
Deformable body  : #3 — Rectangle (beton/MECAx)
Group (group=)   : 102

Contactor 1 :
  Shape  : CLxx
  Color  : BLUEx
  Params : (empty)
```

---

## Interface — List of Empty Avatars

The list at the top of the tab displays only avatars of type `EMPTY_AVATAR`. The columns are:

| Column | Description |
|---------|-------------|
| `#` | Index of the avatar in the project's overall avatar list. |
| `Color` | LMGC90 color code of the body. |
| `Center` | Coordinates of the reference center, rounded to 2 decimal places. |
| `Contactors` | Number of contactors defined on this body. |

**Context menu (right-click):**
- **✏️ Edit** — loads the avatar into the form for editing.
- **🗑️ Delete** — deletes the avatar after confirmation. Refused if the avatar is referenced by a loop or a group.
- **ℹ️ Information** — displays a dialog box with the details of all contactors.

---

## Important Notes

**An empty avatar requires at least one contactor.** Creation is refused if the contactor list is empty.

**Multiple contactors.** An empty avatar can have as many contactors as needed, of different shapes. Each contactor generates a distinct `body.addContactors(…)` line in the script.
