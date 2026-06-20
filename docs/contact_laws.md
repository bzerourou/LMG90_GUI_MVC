# Contact Laws

The **Contact** tab (`Ctrl+9`) allows you to create, modify, and delete pylmgc90 **contact laws** (`tact_behav`). Each law defines the mechanical behavior at the boundary between two bodies in contact. A law must be created here **before** it can be referenced in a visibility table (Visibility tab).

---

## Operating Principle

A **contact law** (`ContactLaw`) is a pylmgc90 object created by `pre.tact_behav(name, law, ...)`. It is identified by a unique name within the project and characterizes the physics of the contact: friction, cohesion, stiffness, damage…

**Generated pylmgc90 call:**

```python
law_IQS_CLB = pre.tact_behav(
    name='IQS_CLB',
    law='IQS_CLB',
    fric=0.3
)
tacts.addBehav(law_IQS_CLB)
```

---

## Tab Interface

The tab consists of three areas:

- **List of laws** (top): a tree with columns Name, Type, Friction, Properties. Laws **referenced** by at least one visibility table appear in **green**. Right-click to Edit, Delete, or display Information.
- **Creation / editing form** (middle): fields that adapt automatically to the chosen type.
- **Contextual help** (bottom): description and list of parameters for the selected type.

### Buttons

| Button | Mode | Action |
|--------|------|--------|
| **✅ Create Law** | Creation | Validates the form and creates the law. |
| **💾 Save Changes** | Editing | Updates the selected law. |
| **❌ Cancel** | Editing | Returns to creation mode without saving. |
| **🔄 Reset** | All | Clears the form and restores default values. |
| **✏️ Edit Selection** | All | Loads the selected law into the form. |
| **🗑️ Delete Selection** | All | Deletes the law (with reference check). |

---

## Form Fields

| Field | Description |
|-------|-------------|
| **Name** | Unique identifier of the law (20 characters max). Used in visibility tables. Default: `law01`. |
| **Category** | Filters the Type combo box. See the 4 categories below. |
| **Type** | pylmgc90 law type. Specific fields are shown/hidden dynamically depending on the type. |

---

## The 4 Law Categories

### Category 1 — Rigid / Rigid

Laws applicable between two rigid bodies (`RBDY2` / `RBDY3`).

---

#### `IQS_CLB` — Quasi-Static Inequality Coulomb _(the most common)_

Standard Coulomb law. Unilateral contact with dry Coulomb friction. Non-smooth Quasi-Static Inequality (IQS) approach.

| Parameter | Interface Label | Description | Default |
|-----------|----------------|-------------|--------|
| `fric` | Friction coefficient | Coulomb coefficient μ. The tangential force cannot exceed μ × normal force. | `0.3` |

**Typical `fric` values:**

| Material | `fric` |
|----------|--------|
| Sand / glass beads | 0.3 – 0.5 |
| Concrete / rocks | 0.5 – 0.8 |
| Polished metals | 0.1 – 0.3 |
| Wood / plastic | 0.3 – 0.6 |
| Frictionless (sliding) | `0.0` |

**pylmgc90 call:**
```python
law = pre.tact_behav(name='loi1', law='IQS_CLB', fric=0.3)
```

---

#### `IQS_CLB_g0` — Coulomb with Initial Gap

Identical to `IQS_CLB` but initializes the initial geometric gap between contactors to `g0=0`. Useful when bodies are already in contact at `t = 0` (with no initial interpenetration).

| Parameter | Description | Default |
|-----------|-------------|--------|
| `fric` | Coulomb friction coefficient. | `0.3` |

**Applications:** pre-tightened mechanical assemblies, progressive compression, contacts with initial roughness.

---

#### `IQS_DS_CLB` — Coulomb with Static/Dynamic Stiffness

Discrete law with two distinct contact stiffnesses: a static stiffness (before sliding) and a dynamic one (during sliding).

| Parameter | Interface Label | Description | Default |
|-----------|----------------|-------------|--------|
| `fric` | Friction coefficient | Coulomb coefficient. | `0.3` |
| `stfr` | Static contact stiffness | Static normal stiffness (N/m). | `1e8` |
| `dyfr` | Dynamic contact stiffness | Dynamic normal stiffness (N/m). | `1e8` |

**Applications:** braking systems (μ_static > μ_dynamic), tectonic plate sliding, mechanisms with self-induced vibrations.

---

#### `IQS_MOHR_DS_CLB` — Mohr-Coulomb with Cohesion

Mohr-Coulomb criterion including normal and tangential cohesion. Allows modeling materials with initial adhesion (cement, wet clay).

| Parameter | Interface Label | Description | Default |
|-----------|----------------|-------------|--------|
| `fric` | Friction coefficient | Coulomb coefficient μ. | `0.3` |
| `stfr` | Static stiffness | Stiffness before cohesion failure (N/m). | `1e8` |
| `dyfr` | Dynamic stiffness | Stiffness after failure (N/m). | `1e8` |
| `cohn` | Normal cohesion | Tensile adhesion force (Pa). | `0.0` |
| `coht` | Tangential cohesion | Additional tangential resistance (Pa). | `0.0` |

**Applications:** geomechanics (clays, cohesive soils), wet granular materials, powders with van der Waals forces.

---

#### `IQS_MAC_CZM` — MAC Cohesive Zone (rigid/rigid)

Mohr-Coulomb-Allix-Corigliano cohesive zone model. Simulates progressive failure and delamination between rigid bodies.

| Parameter | Interface Label | Description | Default |
|-----------|----------------|-------------|--------|
| `stfr` | Static stiffness | Tangential stiffness before damage (N/m). | `1e10` |
| `dyfr` | Dynamic stiffness | Normal stiffness before damage (N/m). | `1e10` |
| `cn` | Normal strength | Normal tensile strength (Pa). | `1e6` |
| `ct` | Tangential strength | Shear strength (Pa). | `1e6` |
| `b` | Mixing parameter | Mode I/II coupling (0 = pure mode I, 1 = equipartition). | `1.0` |
| `w` | Fracture energy | Critical fracture energy (J/m²). | `0.01` |

**Applications:** bond failure, cracking, composite delamination.

---

#### `RST_CLB` — Restitution + Coulomb

Contact with a restitution coefficient (elastic or partially elastic impacts) and Coulomb friction.

| Parameter | Description | Default |
|-----------|-------------|--------|
| `fric` | Coulomb friction coefficient. | `0.3` |

**Applications:** ball impacts, bouncing, mechanical shocks.

---

### Category 2 — Rigid / Deformable (or Def / Def)

Laws applicable between a rigid body (`RBDY2`/`RBDY3`) and a deformable FE body (`MAILx`), or between two deformable bodies.

---

#### `GAP_SGR_CLB` — Gap Contact + Coulomb (rigid/deformable)

Standard law for rigid/deformable contact. Manages the initial gap between the rigid surface and the FE mesh.

| Parameter | Description | Default |
|-----------|-------------|--------|
| `fric` | Coulomb friction coefficient. | `0.3` |

**Applications:** tool/workpiece contact, impact, indentation, FE compression.

---

#### `GAP_SGR_CLB_g0` — GAP with g0 Initialization

Identical to `GAP_SGR_CLB` with the gap initialized to zero. Use if the bodies are initially in tangential contact.

| Parameter | Description | Default |
|-----------|-------------|--------|
| `fric` | Coulomb friction coefficient. | `0.3` |

---

#### `GAP_MOHR_DS_CLB` — Mohr-Coulomb Gap (rigid/deformable)

Mohr-Coulomb criterion with gap management for rigid/deformable contact.

| Parameter | Description | Default |
|-----------|-------------|--------|
| `fric` | Coulomb coefficient. | `0.3` |
| `stfr` | Static stiffness (N/m). | `1e8` |
| `dyfr` | Dynamic stiffness (N/m). | `1e8` |
| `cohn` | Normal cohesion (Pa). | `0.0` |
| `coht` | Tangential cohesion (Pa). | `0.0` |

---

#### `MAC_CZM` — MAC Cohesive Zone (rigid/deformable or def/def)

MAC cohesive zone model applied to rigid/deformable interfaces. Same parameters as `IQS_MAC_CZM`.

| Parameter | Description | Default |
|-----------|-------------|--------|
| `stfr`, `dyfr` | Stiffnesses (N/m). | `1e10` |
| `cn`, `ct` | Normal and tangential strengths (Pa). | `1e6` |
| `b` | Mixing parameter. | `1.0` |
| `w` | Fracture energy (J/m²). | `0.01` |

---

#### `MAL_CZM` — MAL Cohesive Zone (rigid/deformable or def/def)

Variant of the CZM model based on the MAL (Mixed Augmented Lagrangian) formulation. Same parameters as `MAC_CZM`.

---

### Category 3 — Point / Point

Laws applicable between point contactors (`PT2Dx`, `PT3Dx`, FE nodes). Model wire links or discrete rods.

---

#### `ELASTIC_WIRE` — Elastic Cable

Link active only in **tension** (cable inextensible in one direction). Simple cable model.

| Parameter | Interface Label | Description | Default |
|-----------|----------------|-------------|--------|
| `stiffness` | Axial stiffness | Cable stiffness EA (N). | `1e6` |
| `prestrain` | Pre-strain | Initial pre-tension (dimensionless, e.g. `0.01` = 1%). | `0.0` |

**Applications:** suspension cables, anchor tie rods, fiber reinforcements.

---

#### `BRITTLE_ELASTIC_WIRE` — Brittle Elastic Cable

Elastic cable that fails in a brittle manner (without plastic deformation) when the stress exceeds `sigc`.

| Parameter | Interface Label | Description | Default |
|-----------|----------------|-------------|--------|
| `stiffness` | Axial stiffness | Cable stiffness EA (N). | `1e6` |
| `prestrain` | Pre-strain | Initial pre-tension. | `0.0` |
| `sigc` | Failure strength | Maximum stress before brittle failure (Pa). | `1e6` |

**Applications:** brittle fibers, glass fibers, reinforcement failure.

---

#### `ELASTIC_ROD` — Elastic Rod

Rigid rod that can work in **both tension and compression** (unlike the cable). Linear rod model.

| Parameter | Description | Default |
|-----------|-------------|--------|
| `stiffness` | Axial stiffness EA (N). | `1e6` |
| `prestrain` | Initial pre-strain. | `0.0` |

**Applications:** truss structures, point-to-point rigid links, stiffeners.

---

#### `VOIGT_ROD` — Voigt Visco-Elastic Rod

Rod with visco-elastic behavior (spring + damper in parallel — Kelvin-Voigt model).

| Parameter | Interface Label | Description | Default |
|-----------|----------------|-------------|--------|
| `stiffness` | Axial stiffness | Spring stiffness EA (N). | `1e6` |
| `viscosity` | Viscosity | Viscous damping coefficient (N·s). | `1e3` |
| `prestrain` | Pre-strain | Initial pre-tension. | `0.0` |

**Applications:** dampers, structures with viscous dissipation, visco-elastic soil models.

---

### Category 4 — Any (any / any)

Universal laws applicable regardless of the contactor pair.

---

#### `COUPLED_DOF` — Degree-of-Freedom Coupling

Perfect coupling (zero velocity and displacement jump at the interface). Rigid kinematic link.

**No parameters required.**

**Applications:** perfect link between two bodies, DOF coupling in multi-body assemblies.

---

#### `NORMAL_COUPLED_DOF` — Normal Direction Coupling

Coupling only in the direction normal to the contact. Allows free tangential sliding.

**No parameters required.**

---

#### `ELASTIC_REPELL_CLB` — Elastic Repulsion + Coulomb

Soft contact via elastic penalization in the normal direction, with Coulomb friction. Regularization method (alternative to strict IQS laws).

| Parameter | Interface Label | Description | Default |
|-----------|----------------|-------------|--------|
| `fric` | Friction coefficient | Coulomb coefficient. | `0.3` |
| `Kn` | Normal stiffness | Normal penalty stiffness (N/m). | `1e8` |

**Applications:** soft contacts, gentle penalization, models with controlled interpenetration.

---

## Summary Table of the 18 Laws

| Law | Category | Parameters | Main Use |
|-----|-----------|-----------|-----------------|
| `IQS_CLB` | Rig/Rig | `fric` | Standard granular contact |
| `IQS_CLB_g0` | Rig/Rig | `fric` | Contact with zero initial gap |
| `IQS_DS_CLB` | Rig/Rig | `fric`, `stfr`, `dyfr` | Static/dynamic friction |
| `IQS_MOHR_DS_CLB` | Rig/Rig | `fric`, `stfr`, `dyfr`, `cohn`, `coht` | Cohesive materials |
| `IQS_MAC_CZM` | Rig/Rig | `stfr`, `dyfr`, `cn`, `ct`, `b`, `w` | Failure, delamination |
| `RST_CLB` | Rig/Rig | `fric` | Impacts with restitution |
| `GAP_SGR_CLB` | Rig/Def | `fric` | FE tool/workpiece contact |
| `GAP_SGR_CLB_g0` | Rig/Def | `fric` | FE contact with zero gap |
| `GAP_MOHR_DS_CLB` | Rig/Def | `fric`, `stfr`, `dyfr`, `cohn`, `coht` | FE cohesive interface |
| `MAC_CZM` | Rig/Def | `stfr`, `dyfr`, `cn`, `ct`, `b`, `w` | FE cohesive zone |
| `MAL_CZM` | Rig/Def | `stfr`, `dyfr`, `cn`, `ct`, `b`, `w` | MAL cohesive zone |
| `ELASTIC_WIRE` | Pt/Pt | `stiffness`, `prestrain` | Cable (tension only) |
| `BRITTLE_ELASTIC_WIRE` | Pt/Pt | `stiffness`, `prestrain`, `sigc` | Brittle cable |
| `ELASTIC_ROD` | Pt/Pt | `stiffness`, `prestrain` | Elastic rod |
| `VOIGT_ROD` | Pt/Pt | `stiffness`, `viscosity`, `prestrain` | Visco-elastic rod |
| `COUPLED_DOF` | Any/Any | _(none)_ | Perfect rigid link |
| `NORMAL_COUPLED_DOF` | Any/Any | _(none)_ | Normal coupling only |
| `ELASTIC_REPELL_CLB` | Any/Any | `fric`, `Kn` | Soft penalty contact |

---

## Managing Laws

### Creating a Law

Fill in the form and click **✅ Create Law**. The law is created via `add_contact_law()`, which calls `LMGC90Bridge.create_contact_law()` → `pre.tact_behav(...)` → `tacts.addBehav(...)`. The `law_created` signal is emitted → `_refresh_all()`. Created laws are stored in `state.contact_laws` (a list of `ContactLaw`) and classified by `ContactLawType` (enum) and `CONTACT_LAW_CATEGORIES` (category → laws dict).

### Editing a Law

Double-click in the list or click **✏️ Edit Selection**. The form switches to edit mode (the ✅ button is replaced by 💾). Modify the values and click **💾 Save Changes** (`update_contact_law()`). Press **❌ Cancel** to return to creation mode without saving.

> **Renaming:** renaming a law automatically updates the `behavior_name` field of all visibility tables that reference it.

### Deleting a Law

Select it and click **🗑️ Delete Selection** (`remove_contact_law()`). If the law is referenced by one or more visibility tables, a warning lists the references and blocks the deletion. Delete the relevant visibility tables first.

### Law Information

Right-click → **ℹ️ Information** displays a dialog box with the type, all the parameters, and the list of visibility tables that use it.

---

## Visual Indicator in the List

| Name Color | Meaning |
|----------------|--------------|
| **Green** | Law referenced by at least one visibility table |
| Black (normal) | Law not yet referenced |

---

## Important Notes

**Consistency with the visibility table:** the chosen law must be compatible with the body/contactor types of the visibility table. A `GAP_SGR_CLB` law will not work with an `RBDY2/DISKx — RBDY2/DISKx` (rigid/rigid) pair — use `IQS_CLB` in that case.

**Consistency with the contact detector:** the law type must match the detector enabled in the Computation tab. For example, `ELASTIC_WIRE` requires the `PT2Lx` (point/line) detector or similar.

**Numerical values:** the fields accept Python scientific notation (`1e8`, `1e-3`, `3.14e6`). Values are evaluated at the time the law is created.

**Protected deletion:** a law used by at least one visibility table cannot be deleted directly. This protection prevents reference errors in the project.
