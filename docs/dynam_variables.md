# Dynamic Variables
LMGC90_GUI's **dynamic variables** allow you to write Python expressions directly into the interface's input fields, using the project's data (avatars, materials, models, groups) as variables. They replace fixed numeric values with expressions computed on the fly, and propagate automatically across all tabs.

![](captures/variables.JPG)

---

## Accessing the Variable Manager

| Method | Action |
|---------|--------|
| **Tools → Dynamic Variables** menu | Opens the manager |
| Shortcut | `Ctrl+V` |

---

## The Dynamic Variables Manager

The manager (`DynamicVarsDialog`) uses `SafeEvaluator` with `build_eval_context()` to evaluate expressions safely. It displays a 4-column table: **Name**, **Expression**, **Evaluated Value**, **Type**. Each variable is a Python expression stored as a string and evaluated at the time it is used.

### Adding a Variable

1. Enter a **Name** — a valid Python identifier (`thickness`, `r_min`, `x_wall`).
2. Enter an **Expression** — see the possibilities below.
3. The **Preview** updates in real time: result shown in green if valid, error in red.
4. Click **Add / Update**.

### Editing a Variable

Click on the row in the table → the Name and Expression fields are filled in → edit → **Add / Update**.

### Deleting a Variable

Select the row and click **Delete**.

### Refreshing

Click **Refresh** to re-evaluate all variables against the current project state (useful after adding avatars).

> **Persistence:** variables are saved in the project's `.lmgc90` file (`state.dynamic_vars`). They are automatically reloaded when the project is opened.

---

## Supported Expression Types

### Numeric Constants

```python
thickness = 0.5
radius = 0.075
n_cols = 15
pi_val = 3.14159
```

### Mathematical Expressions

All numeric Python expressions are supported:

```python
diameter = 2 * radius
area = pi * radius**2
step = lx + joint
half = thickness / 2
diag = sqrt(lx**2 + ly**2)
clamp = max(0.0, min(1.0, ratio))
```

**Available mathematical functions:**

| Symbol | Description |
|---------|-------------|
| `pi` | π ≈ 3.14159… |
| `e` | e ≈ 2.71828… |
| `sqrt(x)` | Square root |
| `abs(x)` | Absolute value |
| `min(a, b)` | Minimum |
| `max(a, b)` | Maximum |
| `round(x, n)` | Rounded to n decimal places |
| `sum(list)` | Sum of a list |
| `len(object)` | Length |
| `math.sin(x)` | Sine (x in radians) |
| `math.cos(x)` | Cosine |
| `math.tan(x)` | Tangent |
| `math.log(x)` | Natural logarithm |
| `math.log10(x)` | Base-10 logarithm |
| `math.exp(x)` | Exponential |
| `math.floor(x)` | Floor (round down) |
| `math.ceil(x)` | Ceiling (round up) |
| `math.radians(deg)` | Degrees → radians |
| `math.degrees(rad)` | Radians → degrees |
| `np.array(list)` | numpy array |
| `np.linspace(a,b,n)` | Evenly spaced array |
etc.

### Variables Referencing Other Variables

Variables are evaluated in the order in which they are defined — a variable can reference previous ones:

```python
thickness = 0.05
radius = thickness * 3
step = radius + thickness
grid_size = step * 10
```

---

## Accessing Project Data

### Avatars — `avatar[i]`

Access to an avatar by its index (0-based). All properties are read-only.

| Expression | Description | Returned Type |
|------------|-------------|---------------|
| `avatar[i].center` | Full center `[x, y]` or `[x, y, z]` | `list` |
| `avatar[i].x` | X coordinate of the center | `float` |
| `avatar[i].y` | Y coordinate of the center | `float` |
| `avatar[i].z` | Z coordinate of the center (3D) | `float` or `None` |
| `avatar[i].radius` | Radius of the avatar | `float` or `None` |
| `avatar[i].color` | LMGC90 color (`'BLUEx'`) | `str` |
| `avatar[i].material_name` | Material name | `str` |
| `avatar[i].model_name` | Model name | `str` |
| `avatar[i].avatar_type` | pylmgc90 type (`'rigidDisk'`) | `str` |
| `avatar[i].origin` | Origin: `'manual'`, `'loop'`, `'granulo'` | `str` |
| `avatar[i].generation_type` | `'regular'`, `'full'`, `'bevel'` or `None` | `str` or `None` |
| `avatar[i].is_hollow` | Hollow disk | `bool` |
| `avatar[i].nb_vertices` | Number of vertices (polygon) | `int` or `None` |
| `avatar[i].vertices` | List of vertices | `list` or `None` |
| `avatar[i].axis` | Axes of the jonc `{axe1, axe2, axe3}` | `dict` or `None` |
| `avatar[i].contactors` | List of contactors | `list` |
| `avatar[i].wall_params` | Raw wall parameters | `dict` |
| `avatar[i].brick_lx` | Masonry brick length (`wall_params['l']`) | `float` or `None` |
| `avatar[i].brick_ly` | Brick height/depth (`wall_params['h']`) | `float` or `None` |
| `avatar[i].brick_lz` | 3D brick height (`wall_params['lz']`) | `float` or `None` |
| `avatar[i].mesh_params` | FE mesh parameters | `dict` or `None` |
| `avatar[i].index` | Index of the avatar in the list | `int` |

#### pylmgc90 Nodes — `avatar[i].nodes`

The `nodes` property simulates access to pylmgc90 nodes. The pylmgc90 convention numbers nodes starting from 1 — `nodes[1]` is the main node, identical to `nodes[0]` in Python.

| Expression | Description |
|------------|-------------|
| `avatar[i].nodes[1].coor` | Coordinates of the main node `[x, y]` or `[x, y, z]` |
| `avatar[i].nodes[1].coor[0]` | X coordinate of the node |
| `avatar[i].nodes[1].coor[1]` | Y coordinate of the node |
| `avatar[i].nodes[1].coor[2]` | Z coordinate of the node (3D) |
| `avatar[i].nodes[0].coor` | Identical to `nodes[1]` (Python convention) |
| `avatar[i].nodes[k].coor` | k-th vertex for polygons (k ≥ 1) |

> **Why `nodes[1]`?** pylmgc90 numbers nodes starting from 1. LMGC90_GUI supports both conventions: `nodes[0]` and `nodes[1]` both point to the main node.

#### Iterating Over Avatars

```python
nb = len(avatar)                    # Total number of avatars
liste = list(avatar)                # All avatars as a list of proxies
centres = [av.center for av in avatar]  # List of all centers
rayons  = [av.radius for av in avatar if av.radius is not None]
```

---

### Groups — `group['name']`

Access to a group of avatars by its name. Returns a list of `AvatarProxy`.

| Expression | Description |
|------------|-------------|
| `group['mur_briques']` | List of avatars in the group |
| `group['mur_briques'][0].center` | Center of the first avatar in the group |
| `group['mur_briques'][0].x` | X coordinate of the first avatar |
| `len(group['mur_briques'])` | Number of avatars in the group |
| `'mur_briques' in group` | Test for the group's existence (bool) |
| `list(group)` | List of all group names |

**Examples:**
```python
nb_briques  = len(group['mur_facade'])
premier_x   = group['mur_facade'][0].x
dernier_y   = group['mur_facade'][-1].y
all_centers = [av.center for av in group['granulo_box2d']]
```

---

### Materials — `material['name']`

| Expression | Description | Type |
|------------|-------------|------|
| `material['beton'].name` | Material name | `str` |
| `material['beton'].density` | Density (kg/m³) | `float` |
| `material['beton'].material_type` | Type (`'RIGID'`, `'ELAS'`…) | `str` |
| `material['beton']['young']` | Custom property (Young's modulus) | `float` |
| `material['beton']['nu']` | Custom property (Poisson's ratio) | `float` |
| `material['beton'].young` | Same, via attribute | `float` |

**Examples:**
```python
rho = material['granite'].density
E   = material['acier']['young']
nu  = material['acier'].nu
```

---

### Models — `model['name']`

| Expression | Description | Type |
|------------|-------------|------|
| `model['rigid'].name` | Model name | `str` |
| `model['rigid'].physics` | Physics (`'MECAx'`, `'THERx'`…) | `str` |
| `model['rigid'].element` | Finite element (`'Rxx2D'`, `'Q4xxx'`…) | `str` |
| `model['rigid'].dimension` | Dimension (2 or 3) | `int` |
| `model['femxx']['kinematic']` | Numeric option | depends on the option |

**Example:**
```python
dim = model['femxx'].dimension
phys = model['rigid'].physics
```

---

### Filtering Functions

Return a list of `AvatarProxy` filtered according to a criterion.

| Function | Description | Example |
|----------|-------------|---------|
| `avatars_by_color('BLUEx')` | All avatars of color `'BLUEx'` | `bleus = avatars_by_color('BLUEx')` |
| `avatars_by_material('beton')` | All avatars using this material | `corps = avatars_by_material('TDURx')` |
| `avatars_by_type('rigidDisk')` | All avatars of this pylmgc90 type | `disques = avatars_by_type('rigidDisk')` |
| `avatars_by_origin('manual')` | Manually created avatars | `manuels = avatars_by_origin('manual')` |
| `avatars_by_origin('loop')` | Avatars generated by a loop | |
| `avatars_by_origin('granulo')` | Granular avatars | |

**Advanced examples:**
```python
nb_bleus = len(avatars_by_color('BLUEx'))
nb_disques_rouges = len([av for av in avatars_by_color('REDxx') if av.avatar_type == 'rigidDisk'])
rayon_moyen = sum(av.radius for av in avatars_by_type('rigidDisk')) / len(avatars_by_type('rigidDisk'))
x_min = min(av.x for av in avatars_by_color('BLUEx'))
x_max = max(av.x for av in avatars_by_color('BLUEx'))
```

---

## Usage by Tab

Dynamic variables can be used in **every field** of LMGC90_GUI's tabs. Simply write the variable name (or a full expression) in place of the numeric value.

### Material Tab

| Field | Accepts Expressions |
|-------|------------------------|
| **Density** | ✅ — e.g.: `material['granite'].density * 0.9` |
| **Properties** (`key=val, key=val`) | ✅ — e.g.: `young=E, nu=nu_beton` |

**Examples:**
```
Density    : rho
Properties : young=E, nu=nu, elas='standard', anisotropy='isotropic'
```

### Empty Avatar Tab

| Field | Accepts Expressions |
|-------|------------------------|
| **Center** | ✅ — e.g.: `avatar[0].x + spacing, avatar[0].y` |
| **Contactor parameters** | ✅ — e.g.: `r=radius, axe1=lx/2, axe2=ly/2` |

**Examples:**
```
Center             : avatar[0].x + spacing, 0.0
Parameters (DISKx) : r=radius
Parameters (JONCx) : axe1=brick_lx/2, axe2=brick_ly/2
Parameters (POLYG) : nb_vertices=6, vertices=sommets
```

### Contact Tab

**All numeric parameters** of all contact laws accept expressions:

| Parameter | Example Expression |
|-----------|----------------------|
| `fric` | `mu` or `0.5 * material['beton'].density / 2500` |
| `stfr`, `dyfr` | `E * 1e3` |
| `cohn`, `coht` | `cohesion_sol` |
| `cn`, `ct` | `resistance_traction` |
| `stiffness` | `EA_cable` |

**Examples:**
```
fric       : mu
stiffness  : EA_cable
cn         : sigma_c
```

### Loops Tab — Generic `for` Loops

In generic `for` loops, **every expression in the template** has access to the dynamic variables. The bounds (`start`, `end`, `step`) and all template fields are evaluated with the full context:

```
Start : 0
End   : nb_cols
Step  : 1
center (avatar template) : [i * (lx + joint) + lx/2, offset_y]
radius (avatar template)  : r_min + i * (r_max - r_min) / nb_cols
name   (material template): 'mat' + str(i)
```

### Loops Tab — Geometric Loops

Geometric loop parameters (Circle, Grid, Line, Spiral) can use dynamic variables via the `for` loops form:

```
radius (Circle) : rayon_anneau
step   (Grid) : pas_grille
```

### Wizards — Deformable Wizard (DOF page)

In the Boundary Conditions page of the deformable wizard, the Parameters field uses `SafeEvaluator.eval_dict()`:

```
component=[1,2], dofty="vlocy", ct=vitesse_imposee
component=[2], ct=deplacement / duree_rampe
```

---

## Supported Advanced Expressions

### Operators

| Operator | Example |
|-----------|---------|
| `+`, `-`, `*`, `/` | `lx + joint` |
| `//` | Integer division |
| `%` | Modulo |
| `**` | Power: `radius**2` |
| `==`, `!=`, `<`, `<=`, `>`, `>=` | Comparisons |
| `and`, `or`, `not` | Logic |

### Ternary Expressions

```python
r = r_grand if grand else r_petit
val = x if x > 0 else 0.0
```

### List Comprehensions

```python
centres = [av.center for av in group['mur']]
rayons  = [av.radius for av in avatars_by_type('rigidDisk')]
xs      = [av.x for av in avatar]
```

### Lists and Tuples

```python
center_2d = [avatar[0].x, avatar[0].y]
center_3d = [0.0, 0.0, avatar[0].z + 0.5]
```

### numpy Expressions

```python
moyenne = np.array([av.x for av in avatar]).mean()
coords  = np.array([av.center for av in avatar])
```

---

## Comparison with an Equivalent Python Script

The following table shows the equivalence between a dynamic variable in the interface and its Python code in a pre-processing script.

| Dynamic Variable (interface) | Python Script Equivalent |
|-------------------------------|--------------------------|
| `r = avatar[0].radius` | `r = bodies[0].nodes[1].coor[...]` |
| `cx = avatar[0].x` | `cx = bodies[0].nodes[1].coor[0]` |
| `cy = avatar[1].center[1]` | `cy = bodies[1].nodes[1].coor[1]` |
| `cx = avatar[0].nodes[1].coor[0]` | `cx = bodies[0].nodes[1].coor[0]` |
| `rho = material['beton'].density` | `rho = mats['beton'].density` |
| `E = material['acier']['young']` | `E = mats['acier'].young` |
| `phys = model['rigid'].physics` | `phys = mods['rigid'].physics` |
| `nb = len(avatar)` | `nb = len(bodies)` |
| `nb_g = len(group['mur'])` | `nb_g = len(group_mur)` |
| `x0 = group['mur'][0].x` | `x0 = bodies[group_mur[0]].nodes[1].coor[0]` |
| `bleus = avatars_by_color('BLUEx')` | `bleus = [b for b in bodies_list if b.color == 'BLUEx']` |

### Complete Example

**Interface — Dynamic Variables:**
```
lx = 0.20
ly = 0.065
joint = 0.010
nb_cols = 15
nb_rows = 10
spacing = lx + joint
offset_x = 0.0
wall_width = nb_cols * spacing
```

**Equivalent pre-processing Python script:**
```python
lx = 0.20
ly = 0.065
joint = 0.010
nb_cols = 15
nb_rows = 10
spacing = lx + joint
offset_x = 0.0
wall_width = nb_cols * spacing

for row in range(nb_rows):
    for col in range(nb_cols):
        cx = offset_x + col * spacing + lx / 2.0
        cy = row * (ly + joint) + ly / 2.0
        body = pre.rigidDisk(center=[cx, cy], ...)
        bodies.addAvatar(body)
```

---

## `AvatarProxy` Object Properties — Complete Reference

The following table lists **all the properties** accessible via `avatar[i]` or within a group list.

| Property | Type | Notes |
|-----------|------|-------|
| `.center` | `list[float]` | `[x, y]` in 2D, `[x, y, z]` in 3D |
| `.x` | `float` | `center[0]` |
| `.y` | `float` | `center[1]` |
| `.z` | `float` or `None` | `center[2]` or `None` if 2D |
| `.radius` | `float` or `None` | Radius of the disk/sphere |
| `.color` | `str` | 5-character color code (`'BLUEx'`) |
| `.material_name` | `str` | Name of the associated material |
| `.model_name` | `str` | Name of the associated model |
| `.avatar_type` | `str` | Enum value: `'rigidDisk'`, `'rigidSphere'`, `'rigidJonc'`, `'emptyAvatar'`… |
| `.origin` | `str` | `'manual'`, `'loop'`, `'granulo'` |
| `.generation_type` | `str` or `None` | `'regular'`, `'full'`, `'bevel'` |
| `.is_hollow` | `bool` | Hollow disk if `True` |
| `.nb_vertices` | `int` or `None` | Number of vertices of the polygon |
| `.vertices` | `list` or `None` | Vertex coordinates `[[x1,y1], ...]` |
| `.axis` | `dict` or `None` | `{'axe1': v, 'axe2': v, 'axe3': v}` for joncs/planes |
| `.contactors` | `list[dict]` | Each dict: `{'shape', 'color', 'params'}` |
| `.wall_params` | `dict` | Masonry wall parameters |
| `.brick_lx` | `float` or `None` | Brick length (`wall_params['l']`) |
| `.brick_ly` | `float` or `None` | Brick height/depth (`wall_params['h']`) |
| `.brick_lz` | `float` or `None` | 3D brick height (`wall_params['lz']`) |
| `.mesh_params` | `dict` or `None` | FE mesh parameters |
| `.index` | `int` | Index in `state.avatars` |
| `.nodes[1].coor` | `list[float]` | Main node (pylmgc90 convention) |
| `.nodes[0].coor` | `list[float]` | Same (Python convention) |
| `.nodes[k].coor` | `list[float]` | k-th vertex (polygons) |

---

## Security — What Is Allowed and Forbidden

Expressions are parsed via `SafeEvaluator`, which inspects the Python AST before execution. No direct `eval()` is used.

### Allowed

- Arithmetic operations, comparisons, logic
- Calls to functions from the context (`sqrt`, `math.sin`, `len`, `list`…)
- List, tuple, and dict comprehensions
- Ternary expressions (`a if cond else b`)
- Attribute and index access
- Conversions: `int(x)`, `float(x)`, `str(x)`, `bool(x)`

### Forbidden (blocked by SafeEvaluator)

- `import`, `exec`, `eval`, `open`, `__import__`
- Any statement (assignment, `for`/`while` loop, `if` — only expressions are allowed)
- Calls to functions not declared in the context
- Access to `__builtins__`, `__class__`, `__dict__`

> If an expression attempts a forbidden operation, `SafeEvaluator` raises a `ValueError` with the message `"Opération non autorisée : <ASTNodeName>"` ("Operation not allowed").

---

## Error Messages and Debugging

When an expression fails in a tab, a detailed dialog box lists:
- The faulty expression
- The Python error message
- The dynamic variables currently defined
- The available references (`avatar[i].x`, `group['name']`, etc.)

**Common causes:**

| Error | Cause | Solution |
|--------|-------|---------|
| `NameError: 'thickness'` | Variable not yet defined | Create `thickness` in the manager |
| `IndexError: Avatar index 5 invalide` | There are fewer than 6 avatars | Check the index |
| `KeyError: Groupe 'mur' introuvable` | The group does not exist | Check the name in the Loops/Masonry tab |
| `Opération non autorisée : Import` | Attempted import | Use only the available functions |
| `Syntaxe invalide` | Unclosed parentheses | Check the Python syntax |

---

## Ready-to-Use Dynamic Variable Examples

### Masonry Wall Geometry

```python
lx = 0.20          # Brick length
ly = 0.065         # Brick height
lz = 0.10          # Brick depth (3D)
joint = 0.010      # Joint thickness
nb_cols = 15       # Number of columns
nb_rows = 10       # Number of rows
spacing_x = lx + joint
spacing_y = ly + joint
wall_width = nb_cols * spacing_x
wall_height = nb_rows * spacing_y
```

### Granular Parameters

```python
r_min = 0.05
r_max = 0.15
ratio = r_max / r_min
lx_box = 4.0
ly_box = 4.0
nb_particules = 200
```

### Coordinates Relative to an Existing Avatar

```python
x_ref = avatar[0].x
y_ref = avatar[0].y
x_cible = x_ref + 1.0
y_cible = y_ref + 0.5
dist = sqrt((avatar[1].x - avatar[0].x)**2 + (avatar[1].y - avatar[0].y)**2)
```

### Material Parameters

```python
rho = material['granite'].density
E = material['acier']['young']
nu = material['acier']['nu']
mu = 0.3                        # Coulomb coefficient
K = E / (3 * (1 - 2 * nu))     # Bulk modulus
G = E / (2 * (1 + nu))         # Shear modulus
```

### Avatar Statistics

```python
nb_total = len(avatar)
nb_granulo = len(avatars_by_origin('granulo'))
nb_manuels = len(avatars_by_origin('manual'))
rayon_moyen = sum(av.radius for av in avatars_by_type('rigidDisk')) / max(1, nb_total)
x_centre_masse = sum(av.x for av in avatar) / max(1, nb_total)
```
