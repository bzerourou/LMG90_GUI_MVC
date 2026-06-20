# Creating an Avatar (Simple Rigid Body)

**Avatar tab** Allows you to create, modify, and delete the rigid bodies of the project: disks, spheres, joncs, polygons, walls, cylinders, polyhedra, and more.  
Each avatar is defined by a **type**, a **center**, a **material**, a **model**, and **geometric parameters** specific to its type.

![](captures/avatar_disque.JPG)

---

## General Interface

The tab is divided into two areas:

- **Avatar list** (top): a tree displaying all the avatars in the project with their index, type, color, and center. Double-click on a row to edit it. Right-click to access the context menu (Edit, Delete, Information).
- **Creation / editing form** (bottom): fields adapted to the selected avatar type.

## List of Avatars by Dimension

### 2D Avatars

| pylmgc90 Type | Short Description | Key Parameters |
|---------------|--------------------|-----------------|
| `rigidDisk` | Rigid disk | `r`, `is_hollow` |
| `rigidJonc` | Rigid ellipse | `axe1`, `axe2` |
| `rigidPolygon` | Rigid polygon | `generation_type`, `nb_vertices`, `radius` or `vertices` |
| `rigidOvoidPolygon` | Rigid ovoid | `ra`, `rb`, `nb_vertices` |
| `rigidDiscreteDisk` | Discrete disk | `r` |
| `rigidCluster` | Disk cluster | `r`, `nb_disk` |
| `roughWall` | Rough wall | `l`, `r`, `nb_vertex` |
| `fineWall` | Fine wall | `l`, `r`, `nb_vertex` |
| `smoothWall` | Smooth wall | `l`, `h`, `nb_polyg` |
| `granuloRoughWall` | Granular wall | `l`, `rmin`, `rmax`, `nb_vertex` |

### 3D Avatars

| pylmgc90 Type | Short Description | Key Parameters |
|---------------|--------------------|-----------------|
| `rigidSphere` | Rigid sphere | `r` |
| `rigidPlan` | Rigid plane | `axe1`, `axe2`, `axe3` |
| `rigidCylinder` | Rigid cylinder | `r`, `h` |
| `rigidPolyhedron` | Rigid polyhedron | `generation_type`, `nb_vertices`, `radius` or `vertices` + `faces` |
| `roughWall3D` | 3D rough wall | `lx`, `ly`, `r` |
| `granuloRoughWall3D` | 3D granular wall | `lx`, `ly`, `rmin`, `rmax` |

### Fields Common to All Types

| Field | Description |
|-------|-------------|
| **Type** | pylmgc90 avatar type. Determines the additional fields displayed. |
| **Center** | Coordinates of the reference center. Format `x, y` in 2D or `x, y, z` in 3D. Accepts Python expressions (`avatar[0].x + 0.5`). |
| **Material** | Selection from the materials defined in the Materials tab. |
| **Model** | Selection from the models defined in the Models tab. |
| **Color** | LMGC90 display color in 5 characters. See the color list below. |


### Available LMGC90 Colors
Examples of colors you could use:

| Code | Color |
|------|---------|
| `BLUEx` | Blue |
| `REDxx` | Red |
| `VERTx` | Green |
| `JAUNx` | Yellow |
| `GRAYx` | Gray |
| `BLACx` | Black |
| `WHITx` | White |
| `ORANx` | Orange |
| `CYANx` | Cyan |
| `MAGEx` | Magenta |
| `VIOLx` | Purple |
| `ROSEx` | Pink |

---

## 2D Avatar Types

### 1. rigidDisk — 2D Rigid Disk

2D rigid circular body. This is the most common type for granular simulations.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `r` (radius) | Disk radius (m). | `0.1` |
| `is_hollow` | If checked, creates a hollow disk (`is_Hollow=True`). Useful for rigid rings. | checkbox |

---

### rigidJonc — 2D Rigid Jonc / Ellipse

2D rigid elliptical body. Defined by two half-axes.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `axe1` | Main half-axis (m) — length. | `0.15` |
| `axe2` | Secondary half-axis (m) — width. | `0.05` |


---

### rigidPolygon — 2D Rigid Polygon

2D rigid polygonal body. Three generation modes available depending on `generation_type`.

| Parameter | Description | Values |
|-----------|-------------|---------|
| `generation_type` | Shape generation mode. | `regular` · `full` · `bevel` |
| `nb_vertices` | Number of vertices (for `regular` and `full`). | `3` to `20` |
| `radius` | Radius of the circumscribed circle (m) — used for `regular`. Not used for `full` and `bevel`. | `0.1` |
| `vertices` | Explicit list of vertices `[[x1,y1],[x2,y2],…]` — used for `full` and `bevel`. | `[[-0.1,-0.1],[0.1,-0.1],[0.,0.1]]` |

**Generation modes:**

- **`regular`**: regular polygon (all sides equal). Defined by `nb_vertices` and `radius` (radius of the circumscribed circle).
- **`full`**: arbitrary polygon from an explicit list of vertices. The radius is not used.
- **`bevel`**: polygon with automatic beveling of corners to avoid contact singularities.

---

### rigidOvoidPolygon — 2D Rigid Ovoid

2D rigid ovoid body (polygonal ellipse). Polygonal approximation of an ellipse.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `ra` | Main half-axis (m). | `0.15` |
| `rb` | Secondary half-axis (m). | `0.08` |
| `nb_vertices` | Number of vertices of the polygonal approximation. | `20` |

---

### rigidDiscreteDisk — 2D Rigid Discrete Disk

2D rigid circular body with discrete kinematics. Same geometry as a `rigidDisk`, but with a `xKSID`-type contactor (discrete disk). Used in some advanced discrete models.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `r` (radius) | Disk radius (m). | `0.1` |

---

### rigidCluster — 2D Rigid Disk Cluster

2D rigid body composed of several disks rigidly linked together. Allows the creation of complex non-convex shapes.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `r` | Radius of each disk in the cluster (m). | `0.05` |
| `nb_vertices` (nb_disk) | Number of disks in the cluster. | `4` |

> The parameter is named `nb_disk` in the generated pylmgc90 script (not `nb_vertices`).

---

### roughWall — 2D Rough Wall

2D rough wall made up of aligned disks. Used for confining walls with geometric roughness.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `l` | Total length of the wall (m). | `2.0` |
| `r` | Radius of the disks forming the roughness (m). | `0.05` |
| `nb_vertex` | Number of disks along the wall. Default: `10`. | `20` |

---

### fineWall — 2D Fine Wall

2D fine wall made up of very small disks. Same parameters as `roughWall` but with finer roughness.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `l` | Total length of the wall (m). | `2.0` |
| `r` | Radius of the disks (m). Typically very small (0.001 to 0.01). | `0.005` |
| `nb_vertex` | Number of disks. Default: `10`. | `50` |

---

### smoothWall — 2D Smooth Wall

2D smooth wall defined by a half-length and a height. `CLxxx` contactor (continuous surface).

| Parameter | Description | Example |
|-----------|-------------|---------|
| `l` | Half-length of the wall (m) — the total length is `2 × l`. | `1.0` |
| `h` | Half-height (thickness) of the wall (m). | `0.01` |
| `nb_polyg` | Number of polygonal segments. Default: `10`. | `20` |

---

### granuloRoughWall — 2D Granular Rough Wall

2D wall with random roughness generated by a granulometric distribution of disks.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `l` | Total length of the wall (m). | `2.0` |
| `rmin` | Minimum radius of the disks (m). | `0.01` |
| `rmax` | Maximum radius of the disks (m). | `0.05` |
| `nb_vertex` | Number of disks. Default: `10`. | `30` |

---

## 3D Avatar Types

### rigidSphere — 3D Rigid Sphere

3D rigid spherical body. 3D equivalent of `rigidDisk`.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `r` (radius) | Sphere radius (m). | `0.1` |

---

### rigidPlan — 3D Rigid Plane

3D rigid flat surface. Defined by three direction vectors forming a local frame.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `axe1` | Vector of the plane's first axis (local X direction). | `[1.0, 0.0, 0.0]` |
| `axe2` | Vector of the plane's second axis (local Y direction). | `[0.0, 1.0, 0.0]` |
| `axe3` | Normal to the plane (local Z direction). | `[0.0, 0.0, 1.0]` |

> The three vectors must form a direct orthonormal basis.

---

### rigidCylinder — 3D Rigid Cylinder

3D rigid cylindrical body.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `r` (radius) | Cylinder radius (m). | `0.1` |
| `h` | Height (axial length) of the cylinder (m). Default: `1.0` if absent. | `0.5` |

---

### rigidPolyhedron — 3D Rigid Polyhedron

3D rigid polyhedral body. Two generation modes available depending on `generation_type`.

| Parameter | Description | Values |
|-----------|-------------|---------|
| `generation_type` | Generation mode. | `regular` · `vertices` |
| `nb_vertices` | Number of vertices (for `regular`). | `8` (cube), `12` (icosahedron)… |
| `radius` | Radius of the regular polyhedron (m) — for `regular`. | `0.1` |
| `vertices` | Explicit list of 3D vertices `[[x,y,z],…]` — for `vertices`. | `[[−1,−1,−1],[1,−1,−1],…]` |
| `faces` | Face connectivity `[[i,j,k],…]` (in `wall_params`) — for `vertices`. | `[[0,1,2],[2,3,0],…]` |

**Generation modes:**

- **`regular`**: regular polyhedron (similar to a polygonal sphere). Defined by `nb_vertices` and `radius`.
- **`vertices`**: arbitrary polyhedron defined by an explicit list of vertices and face connectivity.

---

### roughWall3D — 3D Rough Wall

3D rough wall made up of spheres aligned on a rectangular surface.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `lx` | Wall dimension in X (m). | `2.0` |
| `ly` | Wall dimension in Y (m). | `2.0` |
| `r` | Radius of the roughness spheres (m). | `0.05` |

---

### granuloRoughWall3D — 3D Granular Rough Wall

3D rough wall with randomly sized spheres.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `lx` | Dimension in X (m). | `2.0` |
| `ly` | Dimension in Y (m). | `2.0` |
| `rmin` | Minimum radius of the spheres (m). | `0.01` |
| `rmax` | Maximum radius of the spheres (m). | `0.05` |

---


## General Notes

**Python expressions in numeric fields:** all numeric fields (center, radius, dimensions) accept Python expressions evaluated via `SafeEvaluator`. Examples: `avatar[0].radius * 2`, `thickness + 0.1`, `math.sqrt(2) * r_base`.

**RIGID material:** rigid avatars must use a material of type `RIGID`. An elastic material can technically be assigned, but has no mechanical effect on a rigid body.

**Rxx model:** rigid avatars use a model with the `Rxx2D` (2D) or `Rxx3D` (3D) element. These elements have no numerical options.

**Unused avatars:** avatars whose material or model has been deleted remain in the list but generate an error when the script is created. Validation is performed before generation.
