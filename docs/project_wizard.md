# Project Configuration Wizard

The **Project Configuration Wizard** guides you step by step through the creation of a complete LMGC90 project with all its essential elements: material, model, test avatar, contact law, and visibility table.

It is particularly useful for quickly starting a new project without having to configure each tab separately.

> **⏱️ Estimated time: 2 to 3 minutes**

---

## Launching the Wizard

Three ways to open the wizard:

| Method | Action |
|---------|--------|
| Menu | **File → Project Wizard…** or **Wizards → Project Configuration** |
| Toolbar | Dedicated button (depending on the toolbar configuration) |
| Keyboard shortcut | `Ctrl+Shift+N` |

![Opening the wizard](captures/projet_assistant.JPG)

> **Cancellation possible at any time**: clicking **❌ Cancel** at any step closes the wizard without modifying the project. The project state (name, dimension, path) is fully restored.

---

## Overview of Steps

The wizard consists of **9 pages** navigated sequentially. The **⬅️ Back** and **Next ➡️** buttons allow free navigation between pages.

| Step | Page | Description | Mandatory |
|-------|------|-------------|-------------|
| 0 | Introduction | Presentation of the wizard | — |
| 1 | Project Information | Name and description | ✅ Yes (name required) |
| 2 | Dimension | 2D or 3D | ✅ Yes |
| 3 | Material | Create or reuse a material | ✅ Yes |
| 4 | Model | Create or reuse a physical model | ✅ Yes |
| 5 | Avatar | Create a first test avatar | ⬜ Optional |
| 6 | Contact Law | Define the contact behavior | ⬜ Optional |
| 7 | Visibility Table | Define who interacts with whom | ⬜ Optional (requires steps 5 and 6) |
| 8 | Summary | Verification before creation | — |

---

## Page 0 — Introduction

Welcome page presenting the upcoming steps. No input required.

Click **Next ➡️** to begin.

---

## Page 1 — Project Information

![Project name page](captures/projet_assistant_nom.JPG)

| Field | Description | Constraints |
|-------|-------------|-------------|
| **Project name** | Project identifier. Used as the file name when saving. | **Required** — 50 characters maximum. The Next button is disabled as long as this field is empty. |
| **Description** | Free text describing the purpose or context of the project. | Optional |

> **Name required:** the Name field is marked with an asterisk (`*`) in the wizard — it is a mandatory field. The **Next ➡️** button remains grayed out as long as it is empty.

---

## Page 2 — Problem Dimension

![Dimension page](captures/projet_assistant_dimension.JPG)

Choose between two mutually exclusive options (radio buttons):

| Choice | Internal Code | Usage Examples |
|-------|-------------|------------------|
| **2D — Two-dimensional problem** | `dimension = 2` | Biaxial compression, oedometric test, 2D granular flow, 2D rotating drum |
| **3D — Three-dimensional problem** | `dimension = 3` | Triaxial compression, 3D hopper, cylindrical drum, 3D mixer |

The **2D** value is selected by default.

> **Effect on subsequent steps:** the dimension chosen here automatically determines:
> - The list of elements offered at the Model step (`Rxx2D` or `Rxx3D`)
> - The type of avatar offered at the Avatar step (`rigidDisk` or `rigidSphere`)
> - The body and contactor type in the visibility table (`RBDY2/DISKx` or `RBDY3/SPHER`)

---

## Page 3 — Material

![Material page](captures/projet_assistant_materiau.JPG)

This page offers two modes depending on the state of the project:

### Mode A — Use an Existing Material _(if the project already contains materials)_

A dropdown list displays all the materials already defined in the Material tab. Select one of them to associate it with the project without creating a new one.

### Mode B — Create a New Material _(automatically checked if no material exists)_

Check **Create a new material instead** to display the creation form:

| Field | Description | Default Value |
|-------|-------------|-------------------|
| **Name** | Material identifier. **5 characters maximum.** | `rockx` |
| **Type** | Type of mechanical behavior. | `RIGID` |
| **Density** | Density (kg/m³). | `2500 kg/m³` |

> **Wizard tip:** for simple granular simulations, use the `RIGID` type with a density of 2,500 kg/m³ (typical sand/gravel). Elastic properties are not configurable in the wizard — use the Material tab for the `ELAS`, `ELAS_PLAS`, etc. types.

---

## Page 4 — Physical Model

![Model page](captures/projet_assistant_modele.JPG)

Same logic as the Material page: reuse an existing model or create a new one.

### Mode A — Use an Existing Model

Dropdown list of models already defined in the Model tab.

### Mode B — Create a New Model

| Field | Description | Default Value |
|-------|-------------|-------------------|
| **Name** | Model identifier. **5 characters maximum.** | `rigid` |
| **Physics** | Physics family. | `MECAx` (only option in the wizard) |
| **Element** | Finite element type. Adapted automatically to the dimension. | `Rxx2D` (2D) or `Rxx3D` (3D) |

> **Wizard tip:** for rigid bodies (DEM), use `Rxx2D` in 2D or `Rxx3D` in 3D. These elements have no numerical options and are the simplest to configure. For deformable finite element models, create the model directly in the Model tab after finishing the wizard.

---

## Page 5 — First Avatar _(optional)_

![Avatar page](captures/projet_assistant_avatar.JPG)

This page is **optional**. It allows you to create a test avatar positioned at the origin (center = `[0, 0]` in 2D or `[0, 0, 0]` in 3D).

Check **Create a test avatar** to display the form:

| Field | Description | Default Value |
|-------|-------------|-------------------|
| **Type** | Avatar type. Adapted automatically to the dimension. | `rigidDisk` (2D) or `rigidSphere` (3D) |
| **Radius** | Radius of the disk or sphere (m). | `0.1 m` |
| **Color** | 5-character LMGC90 color code. | `BLUEx` |

> **Dependency:** the avatar automatically uses the material and model defined in the previous steps. If no valid material or model is available, the avatar will not be created even if the box is checked.

> **Position:** the avatar is created at the origin of the coordinate system. Modify its position after creation via the Avatar tab.

---

## Page 6 — Contact Law _(optional)_

![Contact law page](captures/projet_assistant_contact.JPG)

Defines the mechanical behavior during contacts between avatars. Check **Create a contact law** (checked by default) to display the form:

| Field | Description | Default Value |
|-------|-------------|-------------------|
| **Name** | Law identifier. Up to 20 characters. | `iqsc0` |
| **Law type** | Type of contact behavior. See table below. | `IQS_CLB` |
| **Friction coefficient** | Visible only for laws with Coulomb friction. | `0.3` |

### Available Law Types

| Type | Full Name | Friction | Description |
|------|-------------|----------|-------------|
| `IQS_CLB` | Quasi-Static Unilateral Contact + Coulomb | ✅ Yes | Standard non-smooth rigid law. The most common for DEM simulations. |
| `IQS_CLB_G0` | IQS_CLB with zero gap | ✅ Yes | Variant with zero initial gap. |
| `COUPLED_DOF` | Coupled degrees of freedom | ❌ No | Kinematic coupling between bodies. |
| `IQS_DS_CLB` | Discrete Rigid Contact + Coulomb | ❌ No | Discrete law with normal and tangential stiffnesses. |
| `IQS_MOHR_DS_CLB` | Discrete Mohr-Coulomb | ❌ No | Mohr-Coulomb criterion for joints or brittle interfaces. |
| `IQS_MAC_CZM` | Cohesive Zone | ❌ No | Cohesive zone law for cracking. |
| `ELASTIC_WIRE` | Elastic cable | ❌ No | Unilateral tension link (cable). |
| `BRITTLE_ELASTIC_WIRE` | Brittle elastic cable | ❌ No | Cable with brittle failure beyond a threshold. |
| `ELASTIC_ROD` | Elastic rod | ❌ No | Bilateral link in tension and compression (rod). |
| `ELASTIC_REPELL_CLB` | Elastic repulsion + Coulomb | ❌ No | Repulsive contact with friction. |

**Typical Friction Values:**

| Material | Friction Coefficient |
|----------|------------------------|
| Smooth surfaces | 0.1 |
| Fine sand | 0.3 |
| Gravel | 0.5 |
| Rough concrete | 0.6–0.8 |

> Friction is only configurable for the `IQS_CLB` and `IQS_CLB_G0` laws. For other types, the field is automatically hidden.

---

## Page 7 — Visibility Table _(optional)_

![Visibility page](captures/projet_assistant_visibilite.JPG)

The visibility table defines **which contactors can detect each other** and with which contact law. Check **Create a visibility table** (checked by default) to display the form:

| Field | Description | Default Value |
|-------|-------------|-------------------|
| **Candidate color** | Color of the candidate contactors (active body). | `BLUEx` (synchronized with the avatar's color if step 5 is active) |
| **Antagonist color** | Color of the antagonist contactors (passive body). | `BLUEx` |
| **Alert distance** | Maximum contact detection distance (m). Beyond this, two bodies are not considered to be in potential contact. | `0.1 m` |

**Automatic Configuration Based on Dimension:**

| Parameter | 2D | 3D |
|-----------|----|----|
| Body type | `RBDY2` | `RBDY3` |
| Contactor type | `DISKx` | `SPHER` |
| Contact law | The one created at step 6 | The one created at step 6 |

> **Dependency:** the visibility table is only created if a contact law was defined at the previous step **and** an avatar was created at step 5. If either of these conditions is not met, the table is ignored even if the box is checked.

> **Color synchronization:** if an avatar was created at step 5, the candidate and antagonist colors are automatically pre-filled with that avatar's color.

---

## Page 8 — Summary

![Summary page](captures/projet_assistant_recap.JPG)

The last page displays a complete summary of all the elements that will be created. Review the information before validating.

### Summary Content

| Section | Information Displayed |
|---------|------------------------|
| **Project** | Project name, dimension (2D/3D) |
| **Material** | Name, type, density — or selected existing material |
| **Model** | Name, physics, element — or selected existing model |
| **Avatar** | Type, radius — or "No avatar created" |
| **Contact Law** | Name, type, friction coefficient — or "No law created" |
| **Visibility Table** | Body, contactor, colors, applied law, alert distance — or "No table created" |

Click **✅ Create the Project** to finalize. All elements are created simultaneously and immediately appear in the model tree and the corresponding tabs.

> **In case of error:** if creation fails (duplicate material name, invalid parameter, etc.), an error box is displayed with details of the problem. The project state is fully restored to what it was before the wizard was opened.

---

## After Creation

Once the wizard is finished, all generated elements can be freely modified via their respective tabs:

| Created Element | Tab to Edit |
|-------------|---------------------|
| Material | **Material** (`Ctrl+1`) — select from the list and click ✏️ Edit |
| Model | **Model** (`Ctrl+2`) |
| Avatar | **Avatar** (`Ctrl+3`) |
| Contact Law | **Contact** (`Ctrl+9`) |
| Visibility Table | **Visibility** |

---

## Shortcuts Summary

| Action | Shortcut |
|--------|-----------|
| Open the wizard | `Ctrl+Shift+N` |
| Next page | `Enter` or **Next ➡️** |
| Previous page | **⬅️ Back** |
| Cancel | **❌ Cancel** (restores the previous state) |
| Create the project | **✅ Create the Project** (last page) |

---

## Usage Tips

**Start simple:** for a first 2D LMGC90_GUI project, use the `RIGID` type for the material, `Rxx2D` for the model, create a test disk, and the `IQS_CLB` law with a friction of 0.3. The project will be functional in under 2 minutes.

**Reuse existing elements:** if a material or model has already been created in the current project, the wizard automatically offers it as the first option. There is no need to create a new one every time.

**Complete afterward:** the wizard creates basic elements. For your advanced configurations (deformable finite elements, plastic laws, boundary conditions, granular loops), use the specialized tabs directly after finishing the wizard.
