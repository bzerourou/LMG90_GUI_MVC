# Creating a Model

The model defines the **finite element solver** that will be used for the deformable bodies of the project. It associates a physics, a finite element type, a spatial dimension, and numerical options.

## Interface
The **Model** tab (`Ctrl+2`) is divided into two parts:
 
- **List of models** (top): a table displaying all the models defined in the project with their name, physics, element, and dimension. Models used by at least one avatar are displayed in green.
- **Creation / editing form** (bottom): input fields whose Options section adapts automatically to the selected element.

### Form Fields
 
| Field | Description |
|-------|-------------|
| **Name** | Unique identifier of the model. **5 characters** (internal LMGC90 constraint). Examples: `rigid`, `MECAx`, `elas2`, `ther3`. |
| **Physics** | Family of physics being solved. Determines the list of available elements. See section [Available Physics](#available-physics). |
| **Dimension** | Spatial dimension: `2` (2D) or `3` (3D). The list of elements updates automatically. |
| **Element** | Finite element type. The list depends on BOTH the selected physics and dimension. |
| **Options** | Numerical parameters automatically displayed depending on the element. Rigid elements (`Rxx2D`, `Rxx3D`) have no options. |
 
> **Automatic update:** each time the physics or dimension changes, the list of available elements is reloaded. If the previously selected element exists in the new list, it is kept.
 
---
 
## Available Physics
 
All four physics types are implemented in LMGC90_GUI.
 
| Code | Full Name | Description | Compatible Materials |
|------|-------------|-------------|----------------------|
| `MECAx` | Solid mechanics | Deformation, stress, dynamics. | `RIGID`, `ELAS`, `ELAS_DILA`, `VISCO_ELAS`, `ELAS_PLAS` |
| `THERx` | Thermal | Heat diffusion, convection, radiation. | `THERMO_ELAS` |
| `POROx` | Poromechanics | Solid / fluid coupling following Biot's theory. | `PORO_ELAS` |
| `MULTI` | Thermo-hydro-mechanical (THM) | Full mechanical + thermal + hydraulic coupling. | `PORO_ELAS`, `THERMO_ELAS` |
 
---
 
## Available Elements by Physics
 
### MECAx — 2D Mechanical Elements
 
| Element | Geometry | Nodes | Order | Description |
|---------|-----------|-------|-------|-------------|
| `Rxx2D` | Point | 1 | — | 2D rigid body. No options. |
| `T3xxx` | 3-node triangle | 3 | 1 | Standard linear triangle. |
| `T3Lxx` | 3-node triangle | 3 | 1 | Enriched linear triangle (incompatible modes). |
| `T6xxx` | 6-node triangle | 6 | 2 | Quadratic triangle. |
| `DKTxx` | 3-node triangle | 3 | 1 | Discrete Kirchhoff triangle (thin plates). |
| `Q4xxx` | 4-node quadrangle | 4 | 1 | Standard bilinear quadrangle. |
| `Q4P0x` | 4-node quadrangle | 4 | 1 | Bilinear quadrangle + constant pressure (quasi-incompressible). |
| `Q8xxx` | 8-node quadrangle | 8 | 2 | Serendipity quadrangle. |
| `Q8Rxx` | 8-node quadrangle | 8 | 2 | Serendipity quadrangle with reduced integration. |
| `Q9xxx` | 9-node quadrangle | 9 | 2 | Biquadratic Lagrange quadrangle. |
| `BARxx` | 2-node segment | 2 | 1 | 1D bar / truss. |
| `SPRG2` | 2-node segment | 2 | 1 | 2D spring (`discrete=yes__` added automatically). |
 
### MECAx — 3D Mechanical Elements
 
| Element | Geometry | Nodes | Order | Description |
|---------|-----------|-------|-------|-------------|
| `Rxx3D` | Point | 1 | — | 3D rigid body. No options. |
| `TE4xx` | 4-node tetrahedron | 4 | 1 | Linear tetrahedron. |
| `TE4Lx` | 4-node tetrahedron | 4 | 1 | Enriched linear tetrahedron (F-bar). |
| `TE10x` | 10-node tetrahedron | 10 | 2 | Quadratic tetrahedron. |
| `H8xxx` | 8-node hexahedron | 8 | 1 | Trilinear hexahedron. |
| `H20xx` | 20-node hexahedron | 20 | 2 | Serendipity hexahedron. |
| `H20Rx` | 20-node hexahedron | 20 | 2 | Serendipity hexahedron with reduced integration. |
| `PRI6x` | 6-node prism | 6 | 1 | Linear prism. |
| `SHB6x` | 6-node prism | 6 | 1 | SHB6 solid-shell prism. |
| `PRI15` | 15-node prism | 15 | 2 | Quadratic prism. |
| `BARxx` | 2-node segment | 2 | 1 | 1D bar / truss. |
| `SPRG3` | 2-node segment | 2 | 1 | 3D spring (`discrete=yes__` added automatically). |
 
### THERx — 2D Thermal Elements
 
| Element | Nodes | Order | Specific Thermal Options |
|---------|-------|-------|-------------------------------|
| `Rxx2D` | 1 | — | none |
| `T3xxx` | 3 | 1 | `mass_storage`, `convection`, `radiation` |
| `T6xxx` | 6 | 2 | `mass_storage`, `convection`, `radiation` |
| `DKTxx` | 3 | 1 | `mass_storage`, `convection`, `radiation` |
| `Q4xxx` | 4 | 1 | `mass_storage`, `convection`, `radiation` |
| `Q4P0x` | 4 | 1 | `mass_storage`, `convection`, `radiation` |
| `Q8xxx` | 8 | 2 | `mass_storage`, `convection`, `radiation` |
| `Q8Rxx` | 8 | 2 | `mass_storage`, `convection`, `radiation` |
| `SPRG2` | 2 | 1 | `mass_storage` only |
| `S2xth` | 2 | 1 | `mass_storage` only — 1D thermal segment |
 
### THERx — 3D Thermal Elements
 
| Element | Nodes | Order | Specific Thermal Options |
|---------|-------|-------|-------------------------------|
| `Rxx3D` | 1 | — | none |
| `TE4xx` | 4 | 1 | `mass_storage`, `convection`, `radiation` |
| `TE10x` | 10 | 2 | `mass_storage`, `convection`, `radiation` |
| `H8xxx` | 8 | 1 | `mass_storage`, `convection`, `radiation` |
| `H20xx` | 20 | 2 | `mass_storage`, `convection`, `radiation` |
| `H20Rx` | 20 | 2 | `mass_storage`, `convection`, `radiation` |
| `PRI6x` | 6 | 1 | `mass_storage`, `convection`, `radiation` |
| `PRI15` | 15 | 2 | `mass_storage`, `convection`, `radiation` |
| `SPRG3` | 2 | 1 | `mass_storage` only |
 
### POROx — Poromechanical Elements (mixed displacement-pressure elements)
 
| Element | Dim. | Geometry | Nodes | Order | Description |
|---------|------|-----------|-------|-------|-------------|
| `T33xx` | 2D | Triangle | 3 | 1 | Mixed P1/P1 triangle. |
| `T63xx` | 2D | Triangle | 6 | 2 | Mixed P2/P1 triangle — satisfies the LBB condition. |
| `Q44xx` | 2D | Quadrangle | 4 | 1 | Mixed Q1/Q1 quadrangle. |
| `Q84xx` | 2D | Quadrangle | 8 | 2 | Mixed Q2/Q1 quadrangle — satisfies the LBB condition. |
| `TE44x` | 3D | Tetrahedron | 4 | 1 | Mixed P1/P1 tetrahedron. |
| `TE104` | 3D | Tetrahedron | 10 | 2 | Mixed P2/P1 tetrahedron — satisfies the LBB condition. |
| `H88xx` | 3D | Hexahedron | 8 | 1 | Mixed Q1/Q1 hexahedron. |
| `H208x` | 3D | Hexahedron | 20 | 2 | Mixed Q2/Q1 hexahedron — satisfies the LBB condition. |
 
### MULTI — 2D and 3D THM Elements
 
Same mixed elements as POROx, plus `H8xxx` in 3D for uniform interpolation of the three coupled fields.
 
| Element | Dim. | Description |
|---------|------|-------------|
| `T33xx` | 2D | Mixed P1/P1 triangle. |
| `T63xx` | 2D | Mixed P2/P1 triangle. |
| `Q44xx` | 2D | Mixed Q1/Q1 quadrangle. |
| `Q84xx` | 2D | Mixed Q2/Q1 quadrangle. |
| `TE44x` | 3D | Mixed P1/P1 tetrahedron. |
| `TE104` | 3D | Mixed P2/P1 tetrahedron. |
| `H8xxx` | 3D | Trilinear hexahedron (uniform THM interpolation). |
| `H88xx` | 3D | Mixed Q1/Q1 hexahedron. |
| `H208x` | 3D | Mixed Q2/Q1 hexahedron. |
 
---
 
## Summary Table by Use Case
 
| Use Case | Dimension | Recommended Elements | Note |
|-------|-----------|---------------------|----------|
| 2D rigid bodies (DEM) | 2D | `Rxx2D` | No options |
| 3D rigid bodies (DEM) | 3D | `Rxx3D` | No options |
| 2D springs / bars | 2D | `SPRG2`, `BARxx` | `discrete=yes__` auto |
| 3D springs / bars | 3D | `SPRG3`, `BARxx` | `discrete=yes__` auto |
| 2D structures — standard accuracy | 2D | `Q4xxx`, `T3xxx` | Fast, suited to structured meshes |
| 2D structures — complex geometry | 2D | `T6xxx`, `Q8xxx` | Unstructured automatic meshes |
| 2D thin plates | 2D | `DKTxx` | Kirchhoff formulation |
| 2D quasi-incompressibility | 2D | `Q4P0x` | Constant pressure per element |
| 3D structures — structured mesh | 3D | `H8xxx`, `H20xx` | Hexahedra recommended |
| 3D structures — automatic mesh | 3D | `TE10x`, `TE4xx` | Adaptive tetrahedra |
| 3D thick shells | 3D | `SHB6x`, `PRI6x` | Solid-shells |
| 2D thermal | 2D | `Q4xxx`, `T3xxx` | THERx physics |
| 3D thermal | 3D | `H8xxx`, `TE4xx` | THERx physics |
| 1D thermal segment | 2D / 3D | `S2xth` | THERx physics only |
| 2D poromechanics (Biot) | 2D | `T63xx`, `Q84xx` | LBB satisfied — recommended |
| 3D poromechanics (Biot) | 3D | `TE104`, `H208x` | LBB satisfied — recommended |
| 3D coupled THM | 3D | `H8xxx`, `TE104` | MULTI physics |
 
---
 
## Model Options
 
### MECAx Options — Element-Specific
 
These three options are displayed for all non-rigid MECAx elements.
 
#### `kinematic` — Kinematic Assumption
 
| Value | Description | Use Case |
|--------|-------------|-------------|
| `small` | Small strains (HPP). Linear displacement-strain relationship. Reference geometry assumed constant. | Concrete, elastic steel, most civil engineering structures. |
| `large` | Large strains. Geometrically nonlinear relationship. Configuration updated at each step. | Rubber, soft materials, forming, impact, crash. |
 
#### `formulation` — Lagrangian Formulation
 
Relevant only for `kinematic=large`.
 
| Value | Description |
|--------|-------------|
| `UpdtL` | **Updated Lagrangian.** The reference configuration is updated at each step. Cauchy stresses. Recommended for continuous large strains (metals). |
| `TotaL` | **Total Lagrangian.** The reference configuration remains the initial configuration. Piola-Kirchhoff stresses. Recommended for reversible large strains (elastomers). |
 
#### `mass_storage` — Mass Matrix Storage
 
| Value | Description | Use Case |
|--------|-------------|-------------|
| `lump_` | **Lumped mass.** Diagonal matrix. Immediate inversion. Less accurate at high frequencies. | Explicit dynamics, small time-step schemes. |
| `coher` | **Coherent mass.** Full integrated matrix. More accurate. More costly to invert. | Implicit dynamics, modal analysis, high frequencies. |
 
---
 
### MECAx Options — Common to All Elements (except rigid)
 
These three options are displayed in addition to the element-specific options.
 
#### `material` — Local Constitutive Law
 
| Value | Behavior | Associated Materials |
|--------|-------------|-------------------|
| `elas_` | Standard linear elasticity | `ELAS`, `ELAS_DILA`, `RIGID` |
| `elasd` | Damageable elasticity | `ELAS_PLAS` (with damage variable) |
| `J2iso` | Isotropic J2 plasticity | `ELAS_PLAS` (`isoh='linear'` or `'nonlinear'`) |
| `J2mix` | Mixed J2 plasticity (isotropic + kinematic) | `ELAS_PLAS` (`isoh` and `cinh` both active) |
| `kvisc` | Kelvin-Voigt visco-elasticity | `VISCO_ELAS` |
 
#### `anisotropy` — Anisotropy
 
| Value | Description |
|--------|-------------|
| `iso__` | **Isotropic.** Identical properties in all directions. 2 parameters: E (Young), ν (Poisson). |
| `ortho` | **Orthotropic.** Different properties along 3 principal directions. Requires the 9 elastic constants (Ex, Ey, Ez, νxy, νyz, νxz, Gxy, Gyz, Gxz). Suited to composites, wood, laminated materials. |
 
#### `external_model` — External Model
 
| Value | Description |
|--------|-------------|
| `MatL_` | Internal LMGC90 law (standard behavior). Default value. |
| `Demfi` | DemFi interface — coupling with an external DEM model. |
| `Umat_` | UMAT interface — ABAQUS-type user routine (Fortran / C). |
| `no___` | Disabled. |
| `yes__` | Enabled (depending on the option's context). |
 
---
 
### THERx Options
 
These options are displayed for all non-rigid thermal elements.
 
| Option | Values | Description |
|--------|---------|-------------|
| `mass_storage` | `lump_` · `coher` | Storage of the thermal capacity matrix. Same meaning as in MECAx. |
| `convection` | `no___` · `yes__` | Enables surface thermal convection terms. |
| `radiation` | `no___` · `yes__` | Enables surface thermal radiation terms (Stefan-Boltzmann law). |
| `anisotropy` | `iso__` · `ortho` | Anisotropy of thermal conductivity. |
| `external_model` | `MatL_` · `Demfi` · `Umat_` · `no___` · `yes__` | Interface with an external thermal model. |
 
> **Note:** `SPRG2`, `SPRG3`, and `S2xth` only have the `mass_storage` option. The `convection` and `radiation` options are not displayed for these 1D elements.
 
---
 
## Creation Example — 2D Rigid Body
 
1. Open the **Model** tab (`Ctrl+2`).
2. Enter the name: `rigid`.
3. Select the physics: `MECAx`.
4. Select the dimension: `2`.
5. Select the element: `Rxx2D` — the Options section disappears (no options for rigid elements).
6. Click **✅ Create Model**.
 
![Creating a 2D rigid model](captures/modele_rigid.JPG)
 
---
 
## Creation Example — 2D Elastic Mechanics
 
1. Name: `elas2`.
2. Physics: `MECAx` · Dimension: `2` · Element: `Q4xxx`.
3. Options displayed automatically:
   - `kinematic` → `small`
   - `formulation` → `UpdtL`
   - `mass_storage` → `lump_`
   - `material` → `elas_`
   - `anisotropy` → `iso__`
   - `external_model` → `MatL_`
4. Click **✅ Create Model**.
 
---
 
## Editing and Deletion
 
Select a model in the list, then click **✏️ Edit Selection** to load it in **Edit** mode. Make your changes, then click **💾 Save Changes**, or **❌ Cancel** to discard the changes.
 
> **Deletion:** a model used by at least one avatar cannot be deleted directly. The warning dialog box lists the affected avatars.
 
---
 
## Material / Physics Compatibility Table
 
| Material | MECAx | THERx | POROx | MULTI |
|----------|-------|-------|-------|-------|
| `RIGID` | ✅ | ❌ | ❌ | ❌ |
| `ELAS` | ✅ | ✅ | ❌ | ❌ |
| `ELAS_DILA` | ✅ | ✅ | ❌ | ❌ |
| `VISCO_ELAS` | ✅ | ❌ | ❌ | ❌ |
| `ELAS_PLAS` | ✅ | ❌ | ❌ | ❌ |
| `THERMO_ELAS` | ✅ | ✅ | ❌ | ✅ |
| `PORO_ELAS` | ❌ | ❌ | ✅ | ✅ |
| `DISCRETE` | ✅ | ❌ | ❌ | ❌ |
| `USER_MAT` | ✅ | ❌ | ❌ | ❌ |
| `EXTERNAL` | ✅ | ❌ | ❌ | ❌ |
 
---
 
## Material / `material` Option Compatibility Table
 
| Material | `elas_` | `elasd` | `J2iso` | `J2mix` | `kvisc` |
|----------|---------|---------|---------|---------|---------|
| `RIGID` | ✅ | — | — | — | — |
| `ELAS` | ✅ | — | — | — | — |
| `ELAS_DILA` | ✅ | ✅ | — | — | — |
| `VISCO_ELAS` | — | — | — | — | ✅ |
| `ELAS_PLAS` | — | ✅ | ✅ | ✅ | — |
| `THERMO_ELAS` | ✅ | ✅ | — | — | — |
 
---
 
## Tips
 
- **Name limited to 5 characters**: LMGC90 silently ignores additional characters. Prefer `rigid`, `elas2`, `ther3`, `poro2`.
- **Rxx element**: rigid bodies exclusively use `Rxx2D` (2D) or `Rxx3D` (3D). These elements have no numerical options.
- **Springs**: for `SPRG2` and `SPRG3`, the option `discrete=yes__` is added automatically at creation — there is no need to enter it manually.
- **LBB in poromechanics**: for consolidation or pressure diffusion computations, prefer higher-order elements (`T63xx`, `Q84xx`, `TE104`, `H208x`) which satisfy the Ladyzhenskaya-Babuška-Brezzi condition and avoid spurious pressure oscillations.
- **`kinematic=large` with `formulation`**: the `formulation` field only has an effect if `kinematic=large`. In small strains, the value of `formulation` is ignored by the solver.
- **Unused models**: models not associated with an avatar appear in black in the list. They have no effect on the computation.
