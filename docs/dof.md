# Boundary Conditions (DOFs)

The **DOF** tab (`Ctrl+5`) allows you to apply mechanical, thermal, or initial boundary conditions to the avatars of the project. Each operation is recorded in `state.operations`, applied immediately to the pylmgc90 objects, and exported in the generated Python script.

---

## Operating Principle

A **DOF operation** (`DOFOperation`) is made up of:

| Field | Description |
|-------|-------------|
| `operation_type` | Nature of the operation: `translate`, `rotate`, `imposeDrivenDof`, `imposeInitValue` |
| `target_type` | Target: `'avatar'` (single index) or `'group'` (group name) |
| `target_value` | Avatar index (int) or group name (str) |
| `parameters` | Dictionary of parameters passed directly to the pylmgc90 method |

---

## Tab Interface

The tab is organized into two areas:

- **Operations list** (top): a table of all recorded operations with their type, target, and main parameters. Double-click to edit. Right-click to access the context menu.
- **Creation / editing form** (bottom): fields that adapt dynamically to the chosen operation type.

### Target Selection

| Field | Description |
|-------|-------------|
| **Target type** | `Avatar` (numeric index) or `Group` (group name). |
| **Target** | If Avatar: index of the avatar in the list (0-based). If Group: dropdown list of all groups defined in the project (loops, granulometry, masonry, etc.). |

> All groups created in the Loops, Granulometry, and Masonry tabs automatically appear in the list of available groups.

---

## The Four Operations

---

### 1. `translate` — Rigid Displacement

Moves all the nodes of the avatar by a translation vector. A purely geometric operation — it does not impose a kinematic condition for the simulation.

**pylmgc90 signature:**
```python
avatar.translate(dx=0., dy=0., dz=0.)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|--------|-------------|
| `dx` | float | `0.0` | Translation along the X axis (m) |
| `dy` | float | `0.0` | Translation along the Y axis (m) |
| `dz` | float | `0.0` | Translation along the Z axis (m) — 3D only |

**Example:**
```python
bodies[0].translate(dx=0.5, dy=0.0)
```

> The avatar's position in `state.avatars` is automatically resynchronized after the translation (`_sync_avatar_position`). This updates the display in the model tree and the 3D viewer.

---

### 2. `rotate` — Rigid Rotation

Applies a rotation to the avatar about a given center. Two description modes are available: Euler angles or axis-angle.

**pylmgc90 signature:**
```python
avatar.rotate(
    description='Euler',   # or 'axis'
    phi=0., theta=0., psi=0.,   # Euler angles (rad) — Euler mode
    alpha=0.,                    # angle (rad) — axis mode
    axis=[0., 0., 1.],           # rotation axis — axis mode
    center=[0., 0., 0.]          # center of rotation (m)
)
```

**Common parameters:**

| Parameter | Type | Default | Description |
|-----------|------|--------|-------------|
| `description` | str | `'Euler'` | Mode: `'Euler'` or `'axis'` |
| `center` | list[3] | `[0., 0., 0.]` | Center of rotation in absolute coordinates (m) |

**`'Euler'` mode parameters:**

| Parameter | Type | Default | Description |
|-----------|------|--------|-------------|
| `phi` | float | `0.0` | 1st Euler angle — rotation about Z (rad) |
| `theta` | float | `0.0` | 2nd Euler angle — rotation about X (rad) |
| `psi` | float | `0.0` | 3rd Euler angle — rotation about Z (rad) |

The three rotations are applied successively: first `phi` about Z, then `theta` about X, then `psi` about Z.

**`'axis'` mode parameters:**

| Parameter | Type | Default | Description |
|-----------|------|--------|-------------|
| `alpha` | float | `0.0` | Rotation angle (rad) |
| `axis` | list[3] | `[0., 0., 1.]` | Direction vector of the rotation axis |

**Examples:**
```python
# 90° rotation about Z centered at the origin (axis mode)
bodies[0].rotate(description='axis', alpha=1.5708, axis=[0., 0., 1.], center=[0., 0., 0.])

# 45° Euler rotation in the XY plane
bodies[2].rotate(description='Euler', phi=0.7854, theta=0., psi=0., center=[1.0, 0.5, 0.])
```

> **Tip:** for masonry walls, `'axis'` rotation with `axis=[0,0,1]` allows you to create building corners. The angle is entered in degrees in the interface and automatically converted to radians.

---

### 3. `imposeDrivenDof` — Driven DOF

Imposes a **driven** degree of freedom on the nodes of a group of the avatar. The imposed value can be constant, sinusoidal with a ramp, or defined by a time-evolution file.

**pylmgc90 signature:**
```python
avatar.imposeDrivenDof(
    group='all',
    component=1,
    description='predefined',
    dofty='vlocy',
    ct=0.,
    amp=0.,
    omega=0.,
    phi=0.,
    rampi=1.,
    ramp=0.,
    evolutionFile=''
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|--------|-------------|
| `group` | str | `'all'` | Node group of the avatar. `'all'` = all nodes. For deformable bodies: `'down'`, `'up'`, `'left'`, `'right'`, `'front'`, `'rear'`. |
| `component` | int or list | `1` | DOF component(s). See table below. |
| `description` | str | `'predefined'` | Time mode: `'predefined'` (analytical formula) or `'evolution'` (file). |
| `dofty` | str | `'vlocy'` | DOF type. See table below. |
| `ct` | float | `0.0` | Constant value. |
| `amp` | float | `0.0` | Cosine amplitude. |
| `omega` | float | `0.0` | Angular frequency (rad/s). |
| `phi` | float | `0.0` | Cosine phase (rad). |
| `rampi` | float | `1.0` | Initial value of the multiplicative ramp. |
| `ramp` | float | `0.0` | Ramp slope (s⁻¹). |
| `evolutionFile` | str | `''` | Path to a time-evolution file (`*.evol`). Used if `description='evolution'`. |

#### Components (`component`)

| Value | Meaning |
|--------|--------------|
| `1` | Translation along X (or DOF 1) |
| `2` | Translation along Y (or DOF 2) |
| `3` | Translation along Z (or DOF 3) — 3D only |
| `[1, 2]` | X and Y simultaneously (locks the horizontal plane) |
| `[1, 2, 3]` | Full 3D locking |

#### DOF Types (`dofty`)

| Physics | `dofty` | Description |
|----------|---------|-------------|
| **MECAx** | `'vlocy'` | Imposed velocity (m/s) |
| **MECAx** | `'force'` | Imposed force (N) |
| **THERx** | `'temp'` | Imposed temperature (K or °C depending on convention) |
| **THERx** | `'flux'` | Imposed thermal flux (W/m²) |
| **POROx** | `'vlocy'` | Filtration velocity (m/s) |
| **POROx** | `'force'` | Imposed pressure |
| **MULTI** | `'prim_'` | Primal variable (pressure, temperature…) |
| **MULTI** | `'dual_'` | Dual variable (flux, force…) |

#### General Formula (`'predefined'` mode)

The value imposed at time `t` is:

```
f(t) = [ct + amp × cos(ω × t + φ)] × clamp(rampi + ramp × t)
```

where `clamp(x) = sign(x) × min(|x|, 1)` — the ramp is bounded to 1 to avoid non-physical amplifications.

| Scenario | Parameters | Behavior |
|----------|------------|--------------|
| Locked (zero velocity) | `ct=0`, `dofty='vlocy'` | Fixed nodes throughout the simulation |
| Constant displacement | `ct=v0`, `dofty='vlocy'` | Constant velocity `v0` m/s |
| Sinusoidal oscillation | `amp=A`, `omega=ω`, `phi=φ` | v(t) = A × cos(ωt + φ) |
| Gradual startup | `ct=v0`, `rampi=0`, `ramp=1/t_ramp` | Linear rise from 0 to `v0` over `t_ramp` seconds |
| Arbitrary evolution | `description='evolution'`, `evolutionFile='myfile.evol'` | Value interpolated from the file |

#### Examples

```python
# Lock the base of an FE mesh (zero velocity in X and Y)
mesh.imposeDrivenDof(group='down', component=[1, 2], dofty='vlocy', ct=0.)

# Impose a constant vertical displacement of 0.001 m/s
bodies[3].imposeDrivenDof(group='all', component=2, dofty='vlocy', ct=0.001)

# Sinusoidal oscillation in X, frequency 5 Hz, amplitude 0.01 m/s
bodies[5].imposeDrivenDof(
    group='all', component=1, dofty='vlocy',
    ct=0., amp=0.01, omega=31.416, phi=0.
)

# Thermal loading from an evolution file
mesh.imposeDrivenDof(
    group='up', component=1, dofty='temp',
    description='evolution', evolutionFile='temperature.evol'
)
```

---

### 4. `imposeInitValue` — Initial Value

Imposes an **initial condition** (position or velocity) on the nodes of a group, only at time `t = 0`. Does not impose any constraint during the computation.

**pylmgc90 signature:**
```python
avatar.imposeInitValue(
    group='all',
    component=1,
    value=0.
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|--------|-------------|
| `group` | str | `'all'` | Node group. |
| `component` | int or list | `1` | DOF component(s) (same convention as `imposeDrivenDof`). |
| `value` | float | `0.0` | Initial value to impose (m/s, m, K depending on the type). |


> **Difference from `imposeDrivenDof`:** `imposeInitValue` is only active at `t = 0`. The avatar is then free to move afterward. `imposeDrivenDof` maintains the constraint throughout the simulation.

---

## Managing Operations

### Creating an Operation

Fill in the form and click **✅ Apply**. The operation is applied immediately to the pylmgc90 objects and saved in `state.operations`. The `operation_applied` signal is emitted, triggering a full refresh of the interface and the 3D viewer.

### Editing an Operation

Double-click on an operation in the list, or select it and click **✏️ Edit**. The form is loaded with the operation's values. Modify it and click **💾 Save** to update it (`update_dof_operation`). The operation is reapplied.

### Deleting an Operation

Select it and click **🗑️ Delete**. The operation is removed from `state.operations` (`remove_dof_operation`). The `operation_deleted` signal is emitted.

> **Warning:** deleting an operation does not undo its effect on the avatars (translations and rotations already applied remain in place). To undo a translation, create an inverse translation.

---

## Group Support

The group dropdown list automatically includes all groups defined in the project:

| Source | Example Names |
|--------|----------------|
| Geometric loops | `ma_ligne`, `anneau_particules` |
| `for` loops | name entered in the loop form |
| Granulometry | `granulo_box2d`, `granulo_couette2d` |
| Masonry | `mur_briques`, `mur_facade` |
| FE mesh DOF groups | `down`, `up`, `left`, `right`, `front`, `rear` |

Applying an operation to a group executes the same operation on every avatar in the group:

```python
# Example generated script for a group:
for av in group_granulo_box2d:
    av.imposeDrivenDof(group='all', component=1, dofty='vlocy', ct=0.0)
```

---


## Example — Slider-Crank (`slider_crank.lmgc90`)

The example provided among the project examples illustrates the application of four boundary conditions to the avatars of the slider-crank mechanism:

![Slider_crank example](captures/exemple_slider_crank.JPG)

| Operation | Type | Target | Typical Parameters |
|-----------|------|-------|---------------------|
| Crank rotation | `imposeDrivenDof` | Crank avatar | `component=3, dofty='vlocy', ct=ω` |
| Slider locking | `imposeDrivenDof` | Slider avatar | `component=2, dofty='vlocy', ct=0.` |
| Crank-rod pivot | `imposeInitValue` | Rod avatar | `component=[1,2], value=0.` |
| Initial position | `translate` | Crank avatar | `dx=x0, dy=y0` |

![](captures/exemple_slider_crank.JPG)

---

## Important Notes

**Order of operations:** operations are applied in the order in which they are created. A translation followed by a rotation gives a different result than a rotation followed by the translation. The order in `state.operations` is respected both when applying the operations and in the generated script.

**No undo:** `translate` and `rotate` modify the physical coordinates of the pylmgc90 nodes. There is no Undo button — to reverse an operation, create an opposite one (inverse translation, rotation of opposite sign).

**`imposeDrivenDof` vs `imposeInitValue`:** use `imposeDrivenDof` with `ct=0` and `dofty='vlocy'` to **lock** a DOF throughout the simulation. Use `imposeInitValue` only to define an **initial condition** with no constraint over time.

**Evolution files:** the `.evol` file must be placed in the project's `DATBOX/` directory. It contains two columns: time (s) and value, separated by spaces or tabs. The number of lines must cover the entire simulation duration.

**Components for deformable bodies:** for FE meshes, `component` directly accepts the integers 1, 2, 3 (nodal displacement DOFs). For rigid bodies, `component=1` corresponds to translation in X, `component=2` in Y, `component=3` in Z. The rotation component is `component=4` (2D) or 4-6 (3D) depending on the physics.
