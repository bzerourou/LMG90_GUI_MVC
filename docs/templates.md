# Library — Preconfigured Avatars

The **Library** tab (`📚`) provides a catalog of preconfigured avatars, organized by category. It allows you to quickly insert common shapes into the project without having to manually enter the geometric parameters.

This tab **refreshes automatically** every time the dimension changes in the Model tab: the available templates adapt to the project's current dimension (2D or 3D).

![General view of the Library tab](captures/templates.JPG)

---

## Interface Organization

The tab is divided into two panels:

| Panel | Description |
|---------|-------------|
| **Left — Template tree** | Tree structure of available avatars, organized by category. Click on an entry to display its properties on the right. |
| **Right — Properties** | Displays the name, avatar type, description, and default parameters of the selected template. Also allows you to configure the center, material, model, and color before insertion. |

---

## Available Templates

Templates are organized by category. The list changes depending on whether the project's dimension is **2D** or **3D**.

### 2D Templates

#### Simple Particles

| Template | pylmgc90 Type | Default Parameters | Description |
|----------|--------------|----------------------|-------------|
| **Small Disk** | `rigidDisk` | `radius = 0.05 m` | Rigid disk with a small radius, typical of fine granular simulations. |
| **Medium Disk** | `rigidDisk` | `radius = 0.10 m` | Rigid disk with an intermediate radius. |
| **Large Disk** | `rigidDisk` | `radius = 0.20 m` | Rigid disk with a large radius, for sizable particles. |

#### Elongated Shapes

| Template | pylmgc90 Type | Default Parameters | Description |
|----------|--------------|----------------------|-------------|
| **Horizontal Cylinder** | `rigidJonc` | `axe1 = 2.0 m`, `axe2 = 0.1 m` | Elliptical jonc elongated horizontally, aspect ratio 2:1. |
| **Vertical Cylinder** | `rigidJonc` | `axe1 = 2.0 m`, `axe2 = 0.1 m` | Elliptical jonc elongated vertically. |

> `axe1` is the long half-axis, `axe2` the short half-axis (same parameters as `rigidJonc` in the Avatar tab).

#### Regular Polygons

| Template | pylmgc90 Type | Default Parameters | Description |
|----------|--------------|----------------------|-------------|
| **Triangle** | `rigidPolygon` | `generation_type='regular'`, `nb_vertices=3`, `radius=0.1 m` | Equilateral triangle inscribed in a circle of radius 0.1 m. |
| **Square** | `rigidPolygon` | `generation_type='regular'`, `nb_vertices=4`, `radius=0.1 m` | Regular square inscribed in a circle of radius 0.1 m. |
| **Pentagon** | `rigidPolygon` | `generation_type='regular'`, `nb_vertices=5`, `radius=0.1 m` | Regular pentagon. |
| **Hexagon** | `rigidPolygon` | `generation_type='regular'`, `nb_vertices=6`, `radius=0.1 m` | Regular hexagon — a shape widely used in DEM for compact assemblies. |
| **Rectangle** | `rigidPolygon` | `generation_type='full'`, vertices defined explicitly, `radius=0.15 m` | Rectangle 0.30 m × 0.10 m defined by a list of vertices. |

#### Walls

| Template | pylmgc90 Type | Default Parameters | Description |
|----------|--------------|----------------------|-------------|
| **Horizontal Wall** | `fineWall` | `l=2.0 m`, `r=0.1 m`, `nb_polyg=20` | Thin horizontal wall of length 2 m, made up of 20 polygonal segments. |

---

### 3D Templates

#### Simple Particles

| Template | pylmgc90 Type | Default Parameters | Description |
|----------|--------------|----------------------|-------------|
| **Small Sphere** | `rigidSphere` | `radius = 0.05 m` | Rigid sphere with a small radius. |
| **Medium Sphere** | `rigidSphere` | `radius = 0.10 m` | Rigid sphere with an intermediate radius. |
| **Large Sphere** | `rigidSphere` | `radius = 0.20 m` | Rigid sphere with a large radius. |

#### 3D Shapes

| Template | pylmgc90 Type | Default Parameters | Description |
|----------|--------------|----------------------|-------------|
| **3D Cylinder** | `rigidCylinder` | `radius=0.05 m`, `h=0.2 m` | Right cylinder of radius 0.05 m and height 0.2 m. |
| **Ground Plane** | `rigidPlan` | `axe1=2.0 m`, `axe2=2.0 m`, `axe3=0.1 m` | Rigid horizontal plane of 2 m × 2 m, used as a floor or ceiling. |

---

## Complex Assemblies

In addition to the individual templates, the library offers **assemblies of several avatars** generated in a single action. These assemblies create several coordinated bodies in the project.

### 2D Disk Cluster

Creates a 2D rigid body of type `rigidCluster` — an aggregation of rigidly linked disks, forming a non-convex particle.

| Parameter | Description | Default Value |
|-----------|-------------|-------------------|
| Center | Position of the cluster's reference center. | `[0.0, 0.0]` |
| Material | Material of type `RIGID`. | — |
| Model | Model with element `Rxx2D`. | — |
| Main radius | Radius of each disk making up the cluster (m). | `0.1 m` |
| Number of disks (`nb_disk`) | Number of disks in the cluster. | `5` |

---

### 2D Dumbbell

Creates an empty avatar (`emptyAvatar`) composed of three contactors: two disks (`DISKx`) at the ends and a jonc (`JONCx`) in the center, forming a dumbbell shape.

| Parameter | Description | Default Value |
|-----------|-------------|-------------------|
| Center | Position of the dumbbell's center. | `[0.0, 0.0]` |
| Total length | Distance between the centers of the two disks (m). | `0.3 m` |
| Disk radius | Radius of the two end pieces (m). | `0.05 m` |

**Automatically Generated Contactors:**

| Contactor | Shape | Parameters |
|------------|-------|------------|
| Left disk | `DISKx` | `byrd = radius`, positioned at `−length/2` |
| Right disk | `DISKx` | `byrd = radius`, positioned at `+length/2` |
| Central body | `JONCx` | `axe1 = length`, `axe2 = radius × 0.3` |

---

### 2D Rectangular Box (Box Container)

Creates a rectangular container open at the top, composed of **3 smooth walls** (`smoothWall`): a bottom wall and two side walls.

| Parameter | Description | Default Value |
|-----------|-------------|-------------------|
| Total width | Interior horizontal dimension of the box (m). | — |
| Height | Vertical dimension of the box (m). | — |
| Wall thickness | Thickness of each wall (m). | — |
| Center | Position of the center of the box. | — |

**Bodies Created:**

| Body | Type | Position |
|-------|------|----------|
| Bottom wall | `smoothWall` | `center_y − height/2` |
| Left wall | `smoothWall` | `center_x − width/2` |
| Right wall | `smoothWall` | `center_x + width/2` |

---

### 2D V-Hopper

Creates a conical hopper composed of **2 inclined walls** (`rigidPolygon` with `generation_type='full'`), forming a funnel open at the top and bottom.

| Parameter | Description |
|-----------|-------------|
| Top width | Upper opening of the hopper (m). |
| Bottom width | Lower opening of the hopper (m). |
| Height | Total height of the hopper (m). |
| Center | Position of the geometric center. |

**Bodies Created:** left wall and right wall, each defined by 4 vertices calculated automatically from the dimensions.

---

## Creating an Avatar from a Template

1. Select a template in the tree on the left — its properties are displayed in the panel on the right.
2. Configure the fields in the right panel:
   - **Center**: insertion coordinates (x, y) in 2D or (x, y, z) in 3D. Accepts Python expressions.
   - **Material**: select from the materials defined in the Material tab.
   - **Model**: select from the models defined in the Model tab.
   - **Color**: 5-character LMGC90 color code.
3. Click **✅ Create Avatar**.

The avatar is added to the project's list and appears in the model tree.

![Creating an avatar from a template](captures/templates_pt_avatar.JPG)

---

## Creating a New Template

It is possible to save an existing avatar as a new template to reuse it in other projects.

1. Click the **New template** button.
2. The template creation dialog box opens.
3. Enter the name and description of the template.
4. The geometric parameters of the selected avatar are picked up automatically.
5. Confirm to add the template to the library.

![Creating a new template](captures/templates_new.JPG)

---

## Important Notes

**Current dimension:** the list of templates automatically adapts to the project's dimension. If the dimension is changed in the Model tab, the Library tab refreshes and displays only the compatible templates (2D or 3D).

**Material and model required:** a material and a model must be defined in the project before an avatar can be created from a template. If no material or model is available, an error message is displayed.

**Default parameters:** templates use reasonable default values. These values must be adjusted according to the units and scale of the model. In particular, radii and lengths in meters must be consistent with the granulometry and dimensions of the scene.

**Assemblies:** complex assemblies (box, hopper, dumbbell) create several avatars simultaneously in the project. They all appear in the model tree and can be modified individually after their creation.

**Python expressions:** the Center field accepts Python expressions evaluated via `SafeEvaluator`, as in all other tabs of the interface: `avatar[0].x + 0.5`, `math.sqrt(2) * r`, etc.
