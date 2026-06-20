# Deformable Body Wizard — FE Mesh

The **Deformable Body Wizard** guides you step by step through the creation of a deformable body meshed with finite elements in LMGC90_GUI. It automatically generates the mesh, creates the associated material and model, applies the boundary conditions, then stores the `MESH_DEFORMABLE`-type avatar directly in the project.

The mesh is built via the pylmgc90 functions `pre.buildMesh2D()` or `pre.buildMeshH8()` for structured geometries, and via **gmsh** for curved geometries (disk, sphere, cylinder). In all cases, the raw mesh is converted into a pylmgc90 avatar via `pre.buildMeshedAvatar()`, which produces a body of type **MAILx** (deformable mesh). Complex geometries can also be imported from an external file via `pre.readMesh()`.

---

## Launching the Wizard

| Method | Action |
|---------|--------|
| Menu | **Wizards → Deformable Wizard…** |
| Keyboard shortcut | `Ctrl+Shift+D` |

> **Cancellation:** clicking **❌ Cancel** at any step closes the wizard without modifying the project. The project state is fully restored.

---

## Overview of Steps

The wizard consists of **8 pages** navigated sequentially. The **⬅️ Back** and **Next ➡️** buttons allow free navigation.

| Page | Title | Description |
|------|-------|-------------|
| 0 | Introduction | Presentation of the wizard and the steps |
| 1 | Dimension | 2D or 3D |
| 2 | Material | Create or reuse an elastic material |
| 3 | FE Model | Create or reuse a finite element model |
| 4 | Geometry | Shape and dimensions of the body |
| 5 | Refinement | Mesh fineness |
| 6 | Boundary Conditions (DOF) | Dirichlet and loading conditions |
| 7 | Summary | Verification before generation |

---

## Page 0 — Introduction

Presentation of the 8 upcoming steps. No input required. Click **Next ➡️** to begin.

> The generated mesh is a `MESH_DEFORMABLE` avatar of color `CYANx`, automatically added to the project's avatar list. Its reconstruction parameters are saved in `mesh_params` to allow the project to be reloaded.

![](captures/assistant_defor_page1.JPG)

---

## Page 1 — Dimension

Choose between two mutually exclusive options:

| Choice | pylmgc90 Function Used | Available Geometries |
|-------|---------------------------|------------------------|
| **2D** | `pre.buildMesh2D()` + gmsh | Rectangle, Disk, External file |
| **3D** | `pre.buildMeshH8()` + gmsh | Box (H8), Sphere, Cylinder, External file |

The **2D** value is selected by default.

> **Effect on subsequent steps:** the dimension determines the element types available on the Model page, the shapes available on the Geometry page, the refinement parameters, and the surface groups (`down/up/left/right` in 2D, with `front/rear` added in 3D).

![](captures/assistant_defor_page2.JPG)

---

## Page 2 — Deformable Material

This page offers two modes:

### Mode A — Use an Existing Material _(if elastic materials exist in the project)_

Only materials of elastic types are listed: `ELAS`, `ELAS_DILA`, `VISCO_ELAS`, `ELAS_PLAS`, `THERMO_ELAS`, `PORO_ELAS`. `RIGID` materials are not offered since they are incompatible with a deformable body.

### Mode B — Create a New Material

Check **Create a new material instead** to display the form. Conditional fields appear or are hidden automatically depending on the chosen type.

#### Fields Common to All Elastic Types

| Field | Description | Default Value |
|-------|-------------|-------------------|
| **Name** | Material identifier. **5 characters maximum.** | `ELAS1` |
| **Type** | Type of mechanical behavior. See table below. | `ELAS` |
| **Density** | Density (kg/m³). Range: 10 to 25,000. | `2700 kg/m³` (aluminum) |
| **Young's modulus** | Stiffness of the material (Pa). Range: 10³ to 10¹². | `70 × 10⁹ Pa` |
| **Poisson's ratio (ν)** | Lateral compressibility (dimensionless). Range: 0 to 0.4999. | `0.3` |

#### Available Material Types and Conditional Fields

| Type | Additional Fields | Description |
|------|------------------------|-------------|
| `ELAS` | _(none)_ | Standard linear elasticity. |
| `ELAS_DILA` | `Thermal dilation` (K⁻¹, default `1e-5`), `T_ref_meca` (°C, default `20.0`) | Elasticity with one-sided thermal coupling. |
| `VISCO_ELAS` | `Viscous Young` (Pa, default `1.17 × 10⁹`), `Viscous Poisson` (default `0.35`) | Kelvin-Voigt visco-elasticity. |
| `ELAS_PLAS` | `Yield strength iso_hard` (Pa, default `4 × 10⁸`), `Hardening modulus isoh_coeff` (Pa, default `10⁸`) | J2 elasto-plasticity with linear isotropic hardening, Von-Mises criterion. |
| `THERMO_ELAS` | _(young and nu set to 0 — defined by the model)_ | Coupled thermo-elasticity. `conductivity='field'` and `specific_capacity='field'`. |
| `PORO_ELAS` | _(young and nu set to 0 — defined by the model)_ | Poro-elasticity following Biot's theory. `hydro_cpl=0.0` by default. |

> **Automatically generated properties:** `elas='standard'` and `anisotropy='isotropic'` are always added. For `ELAS_PLAS`, the criterion is always `Von-Mises`, the hardening is `isoh='linear'`, and the parameters `cinh='none'`, `visc='none'`.

![](captures/assistant_defor_page3.JPG)

---

## Page 3 — Finite Element Model

Same logic as the Material page: reuse an existing model compatible with the dimension, or create a new one.

### Mode A — Use an Existing Model

Only models whose dimension matches the one chosen on page 1 are listed.

### Mode B — Create a New Model

| Field | Description | Default Value |
|-------|-------------|-------------------|
| **Name** | Model identifier. **5 characters maximum.** | `femxx` |
| **Physics** | Physics being solved. | `MECAx`, `THERx`, or `HYDRx` |
| **Finite element** | Element type. Adapted automatically to the dimension. | See table below |
| **Anisotropy** | `iso__` (isotropic) or `ortho` (orthotropic). | `iso__` |
| **Kinematics** | `small` (small strains) or `large` (large strains). | `small` |
| **Formulation** | `UpdtL` (updated Lagrangian) or `TotaL` (total Lagrangian). | `UpdtL` |
| **Mass storage** | `lump_` (lumped mass) or `coher` (coherent mass). | `lump_` |

> A description of the selected element is displayed in italics below the dropdown list.

#### Available Elements by Dimension

**In 2D:**

| Element | Description |
|---------|-------------|
| `T3xxx` | 3-node linear triangle |
| `Q4xxx` | 4-node bilinear quadrangle |
| `T6xxx` | 6-node quadratic triangle |
| `Q8xxx` | 8-node serendipity quadrangle |
| `Q9xxx` | 9-node full biquadratic quadrangle |

**In 3D:**

| Element | Description |
|---------|-------------|
| `H8xxx` | 8-node trilinear hexahedron |
| `H20xx` | 20-node triquadratic hexahedron |
| `TE10x` | 10-node quadratic tetrahedron |
| `SHB8x` | 8-node SHB8 hexahedral solid-shell |
| `SHB6x` | 6-node SHB6 prismatic solid-shell |

> The options `material='elas_'` and `external_model='no___'` are automatically added to the model options during generation.

![](captures/assistant_defor_page4.JPG)

---

## Page 4 — Geometry

Defines the shape and dimensions of the body. The list of available shapes depends on the chosen dimension.

### 2D Shapes

#### Rectangle _(native pylmgc90 structured mesh)_

Generates a rectangular mesh via `pre.buildMesh2D()`.

| Field | Description | Default |
|-------|-------------|--------|
| **Center X, Y** | Position of the center of the rectangle (m). | `0.0, 0.0` |
| **Length X (lx)** | Horizontal dimension (m). | `1.0 m` |
| **Length Y (ly)** | Vertical dimension (m). | `1.0 m` |

> The bottom-left corner is calculated automatically: `x0 = cx − lx/2`, `y0 = cy − ly/2`.

#### Disk _(via gmsh)_

Generates a mesh of a full circular disk via **gmsh** (`addDisk`), Frontal-Delaunay algorithm, then imports the `.msh` v2.2 file.

| Field | Description | Default |
|-------|-------------|--------|
| **Center X, Y** | Position of the center of the disk (m). | `0.0, 0.0` |
| **Radius (r)** | Radius of the disk (m). | `0.5 m` |

> Requires that **gmsh** be installed and accessible in Python (`import gmsh`).

#### External File

Imports a mesh from an existing file via `pre.readMesh(filepath, 2)`.

| Field | Description |
|-------|-------------|
| **Mesh file** | Path to the file. Accepted formats: `.msh`, `.vtk`, `.mesh`. Use the 📁 Browse button to navigate. |

---

### 3D Shapes

#### Box (H8) _(native pylmgc90 structured mesh)_

Generates a hexahedral mesh via `pre.buildMeshH8()`.

| Field | Description | Default |
|-------|-------------|--------|
| **Center X, Y, Z** | Position of the center of the box (m). | `0.0, 0.0, 0.0` |
| **Length X (lx)** | Dimension along X (m). | `1.0 m` |
| **Length Y (ly)** | Dimension along Y (m). | `1.0 m` |
| **Length Z (lz)** | Dimension along Z (m). | `1.0 m` |

#### Sphere _(via gmsh)_

Generates a mesh of a full sphere via **gmsh** (`addSphere`), 3D Frontal algorithm.

| Field | Description | Default |
|-------|-------------|--------|
| **Center X, Y, Z** | Position of the center of the sphere (m). | `0.0, 0.0, 0.0` |
| **Radius (r)** | Radius of the sphere (m). | `0.5 m` |

#### Cylinder _(via gmsh)_

Generates a mesh of a full cylinder via **gmsh** (`addCylinder`), Z axis, centered at (cx, cy, cz).

| Field | Description | Default |
|-------|-------------|--------|
| **Center X, Y, Z** | Position of the geometric center of the cylinder (m). | `0.0, 0.0, 0.0` |
| **Radius (r)** | Radius of the cylinder (m). | `0.5 m` |
| **Height (h)** | Axial length of the cylinder (m). | `1.0 m` |

#### External File (3D)

Imports a 3D mesh via `pre.readMesh(filepath, 3)`. Accepted formats: `.msh`, `.vtk`, `.mesh`.

![](captures/assistant_defor_page5.JPG)

---

## Page 5 — Mesh Refinement

Defines the fineness of the mesh. The displayed parameters depend on the geometry selected on the previous page.

### Structured Mesh Type (Rectangle Only)

| Type | Description |
|------|-------------|
| `Q4` | 4-node bilinear quadrangles — fast and robust. **Recommended by default.** |
| `2T3` | 3-node triangles obtained by cutting each Q4 in 2. |
| `4T3` | 3-node triangles obtained by cutting each Q4 in 4. More isotropic mesh. |
| `Q8` | 8-node serendipity quadrangles. More accurate, more costly. |

### Refinement Parameters by Geometry

| Geometry | Parameters | Estimate |
|-----------|------------|------------|
| **Rectangle** | `nx` × `ny` (default 10 × 10) | nx × ny elements |
| **Disk** | `nr` (default 5) × `ntheta` (default 16) | nr × ntheta elements |
| **Box (H8)** | `nx` × `ny` × `nz` (default 10 × 10 × 5) | nx × ny × nz elements |
| **Sphere** | `nr` × `ntheta` × `nphi` (default 5 × 16 × 8) | nr × ntheta × nphi elements |
| **Cylinder** | `nr` × `ntheta` × `nz` (default 5 × 16 × 5) | nr × ntheta × nz elements |
| **External file** | _(no parameter — mesh defined in the file)_ | — |

> An estimated element counter updates in real time as the parameters are modified.

**Meaning of the gmsh Parameters:**

| Parameter | Meaning |
|-----------|--------------|
| `nr` | Number of layers of elements in the radial direction. |
| `ntheta` | Number of elements in the angular direction (circumference). |
| `nphi` | Number of elements in the polar direction (latitude, sphere only). |
| `nz` | Number of elements in the axial Z direction. |
| `nx`, `ny`, `nz` | Number of elements in the Cartesian X, Y, Z directions. |

![](captures/assistant_defor_page6.JPG)

> **Tip:** start with the default values to check the geometry, then increase `nx`/`ny`/`nr`/`ntheta` to improve the accuracy of the computation.

---

## Page 6 — Boundary Conditions (DOF)

Defines the mechanical boundary conditions applied to the mesh's **surface groups**. These groups are created automatically by `buildMesh2D` and `buildMeshH8`.

### Available Surface Groups

| Group | Description | Available |
|--------|-------------|-----------|
| `down` | Bottom edge (y = y_min or z = z_min) | 2D and 3D |
| `up` | Top edge (y = y_max or z = z_max) | 2D and 3D |
| `left` | Left edge (x = x_min) | 2D and 3D |
| `right` | Right edge (x = x_max) | 2D and 3D |
| `front` | Front face (z = z_min) | 3D only |
| `rear` | Rear face (z = z_max) | 3D only |

> **Note:** for curved geometries (disk, sphere, cylinder) imported from gmsh, the surface groups depend on the physical entities defined in the `.msh` file. The names may differ from those above.

### Creating a DOF Condition

Click **+ Add a DOF condition** to create a row. Each row contains three columns:

| Column | Description | Values |
|---------|-------------|---------|
| **DOF type** | Nature of the condition. | `imposeDrivenDof` or `imposeInitValue` |
| **Group** | Surface group on which to apply the condition. | `down`, `up`, `left`, `right`, `front`, `rear` |
| **Parameters** | pylmgc90 arguments in the format `key=value, key=value`. Accepts Python expressions. | See examples below |

### Types of DOF Conditions

| Type | Description |
|------|-------------|
| `imposeDrivenDof` | Driven degree of freedom: imposes a displacement or velocity for the duration of the computation. |
| `imposeInitValue` | Initial value: imposes a position or velocity only at time t = 0. |

### Parameter Examples

| Usage | Parameters |
|-------|------------|
| Locking translation (2D) | `component=[1,2], dofty="vlocy"` |
| Locking translation (3D) | `component=[1,2,3], dofty="vlocy"` |
| Imposed displacement in Y | `component=[2], ct=0.001` |
| Zero initial value | `component=[1,2], value=0.0` |
| Locking X only | `component=[1], dofty="vlocy"` |

![](captures/assistant_defor_page7.JPG)

> **Parameter processing:** the Parameters field is parsed via `SafeEvaluator.eval_dict()` — simple Python expressions are allowed (`[1,2]`, `0.001`, `"vlocy"`). Each condition is converted into a `DOFOperation` and passed to `controller.add_dof_operation()`, which applies the condition AND saves it in `state.operations` (visible in the DOF tab for later editing).

> To delete a row, click the **x** button to the right of the row.


---

## Page 7 — Summary

Displays a complete summary of the configuration before generation.

| Section | Information Displayed |
|---------|------------------------|
| **Geometry** | Shape, structured mesh type (2D), dimensions, center |
| **Refinement** | Discretization parameters, estimated number of elements |
| **Material** | Name, type, density, Young, ν — or existing material |
| **FE Model** | Name, physics, element, anisotropy, kinematics, formulation, mass storage |
| **DOF Conditions** | List of conditions: type, group, parameters |

![](captures/assistant_defor_page8.JPG)

Click **✅ Generate the mesh** to launch generation. A confirmation message indicates the number of nodes and elements created.

> **In case of error:** the project state is fully restored. The error message details the cause (material not found, missing file, invalid parameter, gmsh not available, etc.).

---

## Generation Result

At the end of the wizard, the following elements are created in the project:

| Element | Description |
|---------|-------------|
| **Material** | Added to the Material tab (if created). |
| **FE Model** | Added to the Model tab (if created). |
| **MESH_DEFORMABLE Avatar** | Deformable body of color `CYANx`, added to the avatar list. |
| **DOF Conditions** | Saved in `state.operations`, visible in the DOF tab. |

The deformable body can then be enriched via the **Empty Avatar** tab (mode "Existing deformable body") to add surface contactors enabling interactions with rigid bodies.

![](captures/assistant_defor_page9.JPG)

---

## Important Notes

**External files:** the `.msh` (gmsh v2), `.vtk`, and `.mesh` formats are accepted by `pre.readMesh()`. The file must be compatible with the chosen dimension (2D or 3D). For gmsh files, make sure the physical entities are defined (surfaces in 2D, volumes in 3D).

**DOF conditions:** the boundary conditions created in the wizard are saved and visible in the DOF tab. They can be modified or deleted after generation without having to relaunch the wizard.

**Estimated number of elements:** the counter on the Refinement page is an **estimate** based on the product of the discretization parameters. The actual number may differ slightly for curved geometries generated by gmsh.
