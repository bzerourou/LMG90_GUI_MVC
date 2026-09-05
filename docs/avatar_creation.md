# Creating an Avatar (Simple Rigid Body)

**Avatar tab** — Create, edit and delete rigid bodies in the project: disks, spheres, joncs, polygons, walls, cylinders, polyhedra and more.  
Each avatar is defined by a **type**, a **centre**, a **material**, a **model** and **geometry parameters** specific to its type.

![](captures/avatar_disque.JPG)

---

## General layout

The tab is split into two areas:

- **Avatar list** (top): tree showing every avatar in the project with its index, type, colour and centre. Double-click a row to edit. Right-click for the context menu (Edit, Delete, Information).
- **Create / edit form** (bottom): fields that adapt to the selected avatar type.

## Avatars by dimension

### 2D avatars

| pylmgc90 type | Short description | Key parameters |
|---------------|-------------------|----------------|
| `rigidDisk` | Rigid disk | `r`, `is_hollow` |
| `rigidJonc` | Rigid ellipse | `axe1`, `axe2` |
| `rigidPolygon` | Rigid polygon | `generation_type`, `nb_vertices`, `radius` or `vertices` |
| `rigidOvoidPolygon` | Rigid ovoid | `ra`, `rb`, `nb_vertices` |
| `rigidDiscreteDisk` | Discrete disk | `r` |
| `rigidCluster` | Disk cluster | `r`, `nb_disk` |
| `roughWall` | Rough wall | `l`, `r`, `nb_vertex` |
| `fineWall` | Fine wall | `l`, `r`, `nb_vertex` |
| `smoothWall` | Smooth wall | `l`, `h`, `nb_polyg` |
| `granuloRoughWall` | Granular rough wall | `l`, `rmin`, `rmax`, `nb_vertex` |

### 3D avatars

| pylmgc90 type | Short description | Key parameters |
|---------------|-------------------|----------------|
| `rigidSphere` | Rigid sphere | `r`, `is_hollow` |
| `rigidPlan` | Rigid plane | `axe1`, `axe2`, `axe3` |
| `rigidCylinder` | Rigid cylinder | `r`, `h`, `is_hollow` |
| `rigidPolyhedron` | Rigid polyhedron | `generation_type`, `nb_vertices`, `radius` or `vertices` + `faces` |
| `roughWall3D` | Rough wall 3D | `lx`, `ly`, `r` |
| `granuloRoughWall3D` | Granular rough wall 3D | `lx`, `ly`, `rmin`, `rmax` |

### Fields common to all types

| Field | Description |
|-------|-------------|
| **Type** | pylmgc90 avatar type. Controls which extra fields are shown. |
| **Centre** | Reference centre coordinates. Format `x, y` in 2D or `x, y, z` in 3D. Accepts Python expressions (`avatar[0].x + 0.5`). |
| **Material** | Selection among materials defined in the Materials tab. |
| **Model** | Selection among models defined in the Models tab. |
| **Colour** | LMGC90 display colour code (5 characters). See the colour list below. |

### Available LMGC90 colours

Examples of colours you can use:

| Code | Colour |
|------|--------|
| `BLUEx` | Blue |
| `REDxx` | Red |
| `VERTx` | Green |
| `JAUNx` | Yellow |
| `GRAYx` | Grey |
| `BLACx` | Black |
| `WHITx` | White |
| `ORANx` | Orange |
| `CYANx` | Cyan |
| `MAGEx` | Magenta |
| `VIOLx` | Violet |
| `ROSEx` | Pink |

---

## 2D avatar types

### 1. rigidDisk — Rigid disk 2D

Circular rigid body in 2D. The most common type for granular simulations.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `r` (radius) | Disk radius (m). | `0.1` |
| `is_hollow` | If checked, creates a hollow disk (`is_Hollow=True`). Useful for rigid rings. | checkbox |

---

### rigidJonc — Rigid jonc / ellipse 2D

Elliptical rigid body in 2D. Defined by two semi-axes.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `axe1` | Major semi-axis (m) — length. | `0.15` |
| `axe2` | Minor semi-axis (m) — width. | `0.05` |

---

### rigidPolygon — Rigid polygon 2D

Polygonal rigid body in 2D. Three generation modes depending on `generation_type`.

| Parameter | Description | Values |
|-----------|-------------|--------|
| `generation_type` | Shape generation mode. | `regular` · `full` · `bevel` |
| `nb_vertices` | Number of vertices (for `regular` and `full`). | `3` to `20` |
| `radius` | Circumscribed circle radius (m) — used for `regular`. Not used for `full` and `bevel`. | `0.1` |
| `vertices` | Explicit vertex list `[[x1,y1],[x2,y2],…]` — used for `full` and `bevel`. | `[[-0.1,-0.1],[0.1,-0.1],[0.,0.1]]` |

**Generation modes:**

- **`regular`**: regular polygon (equal sides). Defined by `nb_vertices` and `radius` (circumscribed circle).
- **`full`**: arbitrary polygon from an explicit vertex list. Radius is not used.
- **`bevel`**: polygon with automatic corner chamfering to avoid contact singularities.

---

### rigidOvoidPolygon — Rigid ovoid 2D

Ovoid (polygonal ellipse) rigid body in 2D. Polygonal approximation of an ellipse.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `ra` | Major semi-axis (m). | `0.15` |
| `rb` | Minor semi-axis (m). | `0.08` |
| `nb_vertices` | Number of vertices of the polygonal approximation. | `20` |

---

### rigidDiscreteDisk — Discrete rigid disk 2D

Circular rigid body in 2D with discrete kinematics. Same geometry as `rigidDisk`, but with an `xKSID` contactor (discrete disk). Used in some advanced discrete models.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `r` (radius) | Disk radius (m). | `0.1` |

---

### rigidCluster — Rigid disk cluster 2D

Rigid body in 2D made of several disks rigidly linked. Allows non-convex complex shapes.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `r` | Radius of each disk in the cluster (m). | `0.05` |
| `nb_vertices` (nb_disk) | Number of disks in the cluster. | `4` |

> The parameter is named `nb_disk` in the generated pylmgc90 script (not `nb_vertices`).

---

### roughWall — Rough wall 2D

Rough 2D wall made of aligned disks. Used for confining walls with geometric roughness.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `l` | Total wall length (m). | `2.0` |
| `r` | Radius of the disks forming the roughness (m). | `0.05` |
| `nb_vertex` | Number of disks along the wall. Default: `10`. | `20` |

---

### fineWall — Fine wall 2D

Fine 2D wall made of very small disks. Same parameters as `roughWall` but with finer roughness.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `l` | Total wall length (m). | `2.0` |
| `r` | Disk radius (m). Typically very small (0.001 to 0.01). | `0.005` |
| `nb_vertex` | Number of disks. Default: `10`. | `50` |

---

### smoothWall — Smooth wall 2D

Smooth 2D wall defined by a half-length and a height. Contactor `CLxxx` (continuous surface).

| Parameter | Description | Example |
|-----------|-------------|---------|
| `l` | Wall half-length (m) — total length is `2 × l`. | `1.0` |
| `h` | Half-height (thickness) of the wall (m). | `0.01` |
| `nb_polyg` | Number of polygonal segments. Default: `10`. | `20` |

---

### granuloRoughWall — Granular rough wall 2D

2D wall with random roughness generated from a granulometric distribution of disks.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `l` | Total wall length (m). | `2.0` |
| `rmin` | Minimum disk radius (m). | `0.01` |
| `rmax` | Maximum disk radius (m). | `0.05` |
| `nb_vertex` | Number of disks. Default: `10`. | `30` |

---

## 3D avatar types

### rigidSphere — Rigid sphere 3D

Spherical rigid body in 3D. 3D equivalent of `rigidDisk`.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `r` (radius) | Sphere radius (m). | `0.1` |
| `is_hollow` | If checked, creates a hollow sphere (`is_Hollow=True`). | checkbox |

---

### rigidPlan — Rigid plane 3D

Rigid planar surface in 3D. Defined by three direction vectors forming a local frame.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `axe1` | First plane axis vector (local X). | `[1.0, 0.0, 0.0]` |
| `axe2` | Second plane axis vector (local Y). | `[0.0, 1.0, 0.0]` |
| `axe3` | Plane normal (local Z). | `[0.0, 0.0, 1.0]` |

> The three vectors must form a direct orthonormal basis.

---

### rigidCylinder — Rigid cylinder 3D

Cylindrical rigid body in 3D.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `r` (radius) | Cylinder radius (m). | `0.1` |
| `h` | Height (axial length) of the cylinder (m). Default: `1.0` if omitted. | `0.5` |
| `is_hollow` | If checked, creates a hollow cylinder (`is_Hollow=True`). | checkbox |

---

### rigidPolyhedron — Rigid polyhedron 3D

Polyhedral rigid body in 3D. Two generation modes depending on `generation_type`.

| Parameter | Description | Values |
|-----------|-------------|--------|
| `generation_type` | Generation mode. | `regular` · `vertices` |
| `nb_vertices` | Number of vertices (for `regular`). | `8` (cube), `12` (icosahedron)… |
| `radius` | Regular polyhedron radius (m) — for `regular`. | `0.1` |
| `vertices` | Explicit 3D vertex list `[[x,y,z],…]` — for `vertices`. | `[[−1,−1,−1],[1,−1,−1],…]` |
| `faces` | Face connectivity `[[i,j,k],…]` (in `wall_params`) — for `vertices`. | `[[0,1,2],[2,3,0],…]` |

**Generation modes:**

- **`regular`**: regular polyhedron (similar to a polygonal sphere). Defined by `nb_vertices` and `radius`.
- **`vertices`**: arbitrary polyhedron defined by an explicit vertex list and face connectivity.

---

### roughWall3D — Rough wall 3D

Rough 3D wall made of spheres aligned on a rectangular surface.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `lx` | Wall dimension in X (m). | `2.0` |
| `ly` | Wall dimension in Y (m). | `2.0` |
| `r` | Roughness sphere radius (m). | `0.05` |

---

### granuloRoughWall3D — Granular rough wall 3D

Rough 3D wall with randomly sized spheres.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `lx` | Dimension in X (m). | `2.0` |
| `ly` | Dimension in Y (m). | `2.0` |
| `rmin` | Minimum sphere radius (m). | `0.01` |
| `rmax` | Maximum sphere radius (m). | `0.05` |

---

## General remarks

**Python expressions in numeric fields:** all numeric fields (centre, radius, dimensions) accept Python expressions evaluated via `SafeEvaluator`. Examples: `avatar[0].radius * 2`, `thickness + 0.1`, `math.sqrt(2) * r_base`.

**RIGID material:** rigid avatars must use a material of type `RIGID`. An elastic material can technically be assigned, but has no mechanical effect on a rigid body.

**Rxx model:** rigid avatars use a model with element `Rxx2D` (2D) or `Rxx3D` (3D). These elements have no numerical options.

**Unused avatars:** avatars whose material or model has been deleted remain in the list but raise an error at script generation. Validation is performed before generation.
