# Creating a Material

The **Material** tab explains how to create/edit/delete and configure a material in LMGC90_GUI.


[![Introduction LMGC90_GUI](https://img.youtube.com/vi/6OiwBiSzL_E/0.jpg)](https://www.youtube.com/watch?v=6OiwBiSzL_E)


## Interface
The **Material** tab is divided into two parts:
- **List of materials** (top): a table displaying all the materials defined in the project with their name, type, density, and a preview of the properties. Materials used by at least one avatar are displayed in green.
- **Creation / editing form** (bottom): input fields adapted to the selected type.



### Form Fields
 
| Field | Description |
|-------|-------------|
| **Name** | Unique identifier of the material. **5 characters maximum** (internal LMGC90 constraint). Examples: `TDURx`, `ROCKx`, `steel`, `BEton`. |
| **Type** | Dropdown list of supported material types. Determines the expected properties in the next field. |
| **Density** | Density in kg/m³ (SI system). Default value: `2800`. |
| **Properties** | Free-text field for type-specific parameters, in the format `key=value, key=value`. Automatically filled with a consistent suggestion each time the type is changed. |
 
> **Automatic suggestion:** each time a new type is selected, the Properties field and the name are automatically filled with typical values. These values serve as a starting point and must be adapted to the actual material.

---
 
## Available Material Types
 
LMGC90_GUI offers **10 types** of materials, corresponding to the types accepted by `pre.material(materialType=…)` in pylmgc90.
 
> **Note:** types marked _(advanced)_ — `DISCRETE`, `USER_MAT`, `EXTERNAL` — do not have automatic suggestions in the interface. Their parameters must be entered manually.
 
### Parameters Table
 
| Type | Full Name | Main Parameters | Compatible Physics |
|------|-------------|-----------------------|---------------------|
| `RIGID` | Rigid body | _(none)_ | MECAx |
| `ELAS` | Linear elastic | `elas`, `young`, `nu`, `anisotropy` | MECAx |
| `ELAS_DILA` | Elastic with thermal dilation | `elas`, `young`, `nu`, `anisotropy`, `dilatation`, `T_ref_meca` | MECAx, THERx |
| `VISCO_ELAS` | Visco-elastic | `elas`, `young`, `nu`, `anisotropy`, `viscous_model`, `viscous_young`, `viscous_nu` | MECAx |
| `ELAS_PLAS` | Elasto-plastic | `elas`, `young`, `nu`, `anisotropy`, `critere`, `isoh`, `iso_hard`, `isoh_coeff`, `cinh`, `visc` | MECAx |
| `THERMO_ELAS` | Coupled thermo-elastic | `elas`, `young`, `nu`, `anisotropy`, `dilatation`, `T_ref_meca`, `conductivity`, `specific_capacity` | THERx, THMx |
| `PORO_ELAS` | Poro-elastic (Biot) | `elas`, `young`, `nu`, `anisotropy`, `hydro_cpl`, `conductivity`, `specific_capacity` | POROx, THMx |
| `DISCRETE` _(advanced)_ | Discrete elements (mass-spring) | `masses`, `stiffnesses`, `viscosities` | MECAx |
| `USER_MAT` _(advanced)_ | Custom constitutive law | `density`, `file_mat` | MECAx |
| `EXTERNAL` _(advanced)_ | Interface with external code | _(defined by the external code)_ | MECAx |
 
### Table of Typical Uses
 
| Type | Typical Applications | Concrete Examples | Fields |
|------|-----------------------|-------------------|----------|
| `RIGID` | Discrete Element Method (DEM) | Grain stacks, granular flows, particle assemblies | Civil engineering, pharmaceuticals, food industry |
| `ELAS` | Structures in the elastic regime | Buildings, bridges, mechanical parts, metal structures | Civil engineering, mechanics |
| `ELAS_DILA` | One-sided thermal stresses | Structures subject to temperature variations, differential dilation | Construction, mechanics, electronics |
| `VISCO_ELAS` | Materials with viscous behavior | Polymers, asphalt, damping materials, seals | Roads, automotive, aerospace |
| `ELAS_PLAS` | Permanent plastic deformations | Metal forming, impact, damage, machining | Metallurgy, automotive, aerospace |
| `THERMO_ELAS` | Full thermo-mechanical coupling | Thermal dissipation, thermal shocks, braking | Electronics, automotive, nuclear |
| `PORO_ELAS` | Saturated porous media | Soil consolidation, oil reservoirs, aquifers, CO₂ storage | Geotechnics, hydrogeology, oil |
| `DISCRETE` | Mass-spring-damper systems | Seismic isolators, suspensions, discrete elastic links | Earthquake engineering, automotive |
| `USER_MAT` | Custom constitutive laws | Specific materials, experience-derived laws | Research, innovative materials |
| `EXTERNAL` | Coupling with an external code | Interface with other simulation software | Multi-physics simulation |
 
---
## Detailed Properties by Type
 
### RIGID — Rigid Body
 
No property parameter is required. The Properties field must remain empty.
 
```
Name      : BRIQx
Type      : RIGID
Density   : 2000
Properties: (empty)
```
 
---
 
### ELAS — Linear Elastic
 
```
elas='standard', young=2.1e11, nu=0.3, anisotropy='isotropic'
```
 
| Parameter | Description | Typical Value |
|-----------|-------------|----------------|
| `elas` | Elastic formulation: always `'standard'`. | `'standard'` |
| `young` | Young's modulus (Pa). | Steel: `2.1e11` · Concrete: `3e10` · Rock: `5e10` |
| `nu` | Poisson's ratio (dimensionless). | `0.2` to `0.35` |
| `anisotropy` | Type of anisotropy: `'isotropic'` or `'orthotropic'`. | `'isotropic'` |
| `G`| Shear modulus (Pa) | Steel: `8.1e10`|     
 
---
 
### ELAS_DILA — Elastic with Thermal Dilation
 
```
elas='standard', young=3e10, nu=0.2, anisotropy='isotropic', dilatation=1.2e-5, T_ref_meca=20.0
```
 
| Parameter | Description | Typical Value |
|-----------|-------------|----------------|
| `elas` | Elastic formulation. | `'standard'` |
| `young` | Young's modulus (Pa). | `3e10` |
| `nu` | Poisson's ratio. | `0.2` |
| `anisotropy` | Anisotropy. | `'isotropic'` |
| `dilatation` | Linear thermal expansion coefficient (K⁻¹). | `1e-5` to `2e-5` |
| `T_ref_meca` | Mechanical reference temperature (°C or K) — zero thermal strain at this value. | `20.0` |
 
---
 
### VISCO_ELAS — Visco-Elastic
 
```
elas='standard', anisotropy='isotropic', young=1.17e11, nu=0.35,
viscous_model='KelvinVoigt', viscous_young=1.17e9, viscous_nu=0.35
```
 
| Parameter | Description | Values |
|-----------|-------------|---------|
| `elas` | Elastic formulation. | `'standard'` |
| `young` | Young's modulus of the elastic branch (Pa). | `1.17e11` |
| `nu` | Elastic Poisson's ratio. | `0.35` |
| `anisotropy` | Anisotropy. | `'isotropic'` |
| `viscous_model` | Rheological model. `KelvinVoigt` = spring and damper in parallel (reversible creep). | `'KelvinVoigt'` · `'none'` |
| `viscous_young` | Young's modulus of the viscous branch (Pa). | `1.17e9` |
| `viscous_nu` | Poisson's ratio of the viscous branch. | `0.35` |
 
---
 
### ELAS_PLAS — Elasto-Plastic
 
```
elas='standard', anisotropy='isotropic', young=2.1e11, nu=0.3,
critere='Von-Mises', isoh='linear', iso_hard=2.5e8, isoh_coeff=1e9,
cinh='none', visc='none'
```
 
| Parameter | Description | Values |
|-----------|-------------|---------|
| `elas` | Elastic formulation. | `'standard'` |
| `young` | Young's modulus (Pa). | `2.1e11` |
| `nu` | Poisson's ratio. | `0.3` |
| `anisotropy` | Anisotropy. | `'isotropic'` . `'orthotropic'`  |
| `critere` | Plasticity criterion. | `'Von-Mises'` · `'none'` |
| `isoh` | Type of isotropic hardening. | `'none'`, `'linear'`   |
| `iso_hard` | Initial yield strength σ₀ (Pa). | `2.5e8` |
| `isoh_coeff` | Isotropic hardening modulus H (Pa). | `1e9` |
| `cinh` | Kinematic hardening. | `'none'` |
| `visc` | Viscoplasticity. | `'none'` |
 
---
 
### THERMO_ELAS — Coupled Thermo-Elastic
 
```
elas='standard', young=3e10, nu=0.2, anisotropy='isotropic',
dilatation=1.2e-5, T_ref_meca=20.0, conductivity=1.8, specific_capacity=880.0
```
 
| Parameter | Description | Typical Value |
|-----------|-------------|----------------|
| `elas` | Elastic formulation. | `'standard'` |
| `young` | Young's modulus (Pa). | `3e10` |
| `nu` | Poisson's ratio. | `0.2` |
| `anisotropy` | Anisotropy. | `'isotropic'` |
| `dilatation` | Thermal expansion coefficient (K⁻¹). | `1.2e-5` |
| `T_ref_meca` | Mechanical reference temperature. | `20.0` |
| `conductivity` | Thermal conductivity (W/m/K) or `'field'` |
| `specific_capacity` | Specific heat capacity (J/kg/K) or `'field'`|
 
---
 
### PORO_ELAS — Poro-Elastic (Biot)
 
```
elas='standard', young=5e7, nu=0.3, anisotropy='isotropic',
hydro_cpl=0.8, conductivity=1e-8, specific_capacity=1e-10
```
 
| Parameter | Description | Typical Value |
|-----------|-------------|----------------|
| `elas` | Elastic formulation. | `'standard'` |
| `young` | Young's modulus of the solid skeleton (Pa). | `5e7` |
| `nu` | Poisson's ratio of the skeleton. | `0.3` |
| `anisotropy` | Anisotropy. | `'isotropic'` |
| `hydro_cpl` | Biot coupling coefficient (0 to 1). | `0.8` |
| `conductivity` | Hydraulic conductivity (m/s) or `'field'` |
| `specific_capacity` | Hydraulic storage capacity (Pa⁻¹) or `'field'`|
 
---
 
## Creation Example — Elastic Steel
 
1. Open the **Material** tab (`Ctrl+1`).
2. Select the **ELAS** type from the dropdown list — the Properties field fills in automatically.
3. Modify the values in the Properties field:
 
```
elas='standard', young=2.1e11, nu=0.3, anisotropy='isotropic'
```
 
4. Set the density to `7850` kg/m³.
5. Enter a name: `steel` or `ACIEx`.
6. Click **✅ Create Material**.
 
![Creating a steel material](captures/materiau_steel.JPG)
 
---
 
## Editing and Deletion
 
In the materials list table, select the material to edit, then click the **✏️ Edit Selection** button. All the material's data is loaded into the form in **Edit** mode.
 
- Make your changes in the fields.
- Click **💾 Save Changes** to confirm.
- Click **❌ Cancel** to discard the changes and return to normal mode.
 
![Editing a material](captures/materiau_steel_modification.JPG)
 
> **Deletion:** a material used by at least one avatar cannot be deleted directly. A warning message indicates the affected avatars. You must first reassign these avatars to another material, or delete them.
 
---
 
## Dynamic Variables
 
Dynamic variables allow you to define reusable values or expressions in all the numeric fields of the interface, including the material Properties field.
 
Open the dialog box via **Tools → Dynamic Variables** or the shortcut `Ctrl+V`.
 
![Dynamic variables](captures/variables.JPG)
 
### How to Create a Variable
 
1. In the dialog box, click on one of the examples to load it as a base (optional).
2. Enter the variable's **name** (e.g.: `young_ref`).
3. Enter the **value or expression** (e.g.: `2.1e11`).
4. Click **Add or edit**.
5. Click **OK** to close.
 
The dynamic variables can now be used in any field of the application by simply typing its name. See [Dynamic Variables](dynam_variables.md).
 
### Expression Examples
 
| Entered Expression | Result | Usage |
|-------------------|----------|-------|
| `young_ref = 2.1e11` | Numeric constant | `young=young_ref` in the properties |
| `young_beton = young_ref / 7` | Computed expression | Concrete/steel stiffness ratio |
| `nu_courant = 0.3` | Constant | Default Poisson's ratio |
| `radius = avatar[0].radius * 2` | Property of an existing avatar | Radius derived from another avatar |
 
> **Note:** expressions are evaluated via `SafeEvaluator`, which allows standard Python mathematical operations (`+`, `-`, `*`, `/`, `**`, `math.sqrt(…)`, etc.) as well as access to the properties of the project's avatars and materials.
 
---
 
## Tips
 
- **Name limited to 5 characters**: names in LMGC90 are limited to five characters. Prefer short codes such as `steel`, `BEton`, `GRAN1`.
- **RIGID material with no properties**: for rigid bodies, the Properties field must remain empty. Only the density is used to compute the mass and moment of inertia.
- **`'field'` value**: for `conductivity` and `specific_capacity` in the `THERMO_ELAS` and `PORO_ELAS` types, the value `'field'` indicates that this parameter is defined by the finite element model rather than by a scalar constant.
- **Material / model consistency**: the material type must be compatible with the physics of the model associated with the avatar. For example, a `PORO_ELAS` material must be associated with a model of `POROx` or `MULTI` physics.
- **Dynamic variables**: use `Ctrl+V` to quickly access variables and avoid repetitive entry in the Properties fields.
