# Computation

## Overview

The `calcul` (Computation) tab manages the configuration and launching of LMGC90 simulations. It automatically generates the DATBOX and the `command.py` script, then executes that script.
## Computation Parameters

![](captures/calcul.JPG)

| Parameter | UI Field | Default Value | Description |
|---|---|---|---|
| `dt` | Time step | `1e-3` | Time increment |
| `nb_steps` | Number of iterations | `1000` | Number of computation steps |
| `theta` | Integrator theta | `0.5` | Integration scheme parameter |
| `tol` | Tolerance | `1.666e-4` | Solver convergence tolerance |
| `relax` | Relaxation | `1.0` | Relaxation factor |
| `norm` | Norm | `Quad ` | Convergence norm (`Quad `, `QM   `, `Maxim`) |
| `gs_it1` | GS1 iterations | `50` | Number of Gauss-Seidel iterations (outer loop) |
| `gs_it2` | GS2 iterations | `100` | Number of Gauss-Seidel iterations (inner loop) |
| `solver_type` | Solver | `NLGS` | Solver type (`Stored_Delassus_Loops`, `Exchange_Local_Global`, `Exchange_Local_Global` ) |
| `freq_write` | Write frequency | `50` | Write results every N steps |
| `freq_display` | Display frequency | `50` | Update display every N steps |


## Files Generated When Launching a Computation

| File | Location | Description |
|---|---|---|
| `DATBOX/` | Project folder | LMGC90 input data |
| `command.py` | Project folder | chipy computation script |
| `OUTBOX/` | Project folder | Results (created by LMGC90) |
| `Display/` | Project folder | Display files |
| `Postpro/` | Project folder | Post-processing files |


### Configuring Your Computations
You can configure your computation scripts via the "Configure chipy routines" button. A dialog box will open in your interface.

![](captures/config_calculs.JPG)

#### 1. Model Tab
The first tab performs automatic detection based on your model's hypothesis, and loads all parameters according to your avatars.



|Plane stress (mhyp = 1)	|2D computation under plane stress conditions. Relevant for thin structures.
| --- | ------- |
|Plane strain (mhyp = 2)	|2D computation under plane strain conditions. Relevant for structures that are infinitely long in z.|
|Three-dimensional (mhyp = 3)	|Full 3D computation.|

##### Deformable Bodies
|Enable deformable bodies	|Generates ReadDatbox(deformable=True) in the script. Automatically enables mecaFEMx if the physics is MECAx.|
|----|--------|
|FEM Physics	|Determines the finite element solver used: MECAx (solid mechanics), THERx (thermal), HYDRx (hydraulic), or THMx (coupled thermo-hydro-mechanical).|
|Rloc_tol	|Tolerance on contact forces for Rloc recovery. Typical value: 5 × 10⁻². Used in chipy.SetRlocTol().|


#### 2. Routines
This tab selects the chipy routines to include in the computation loop. Each checkbox corresponds to a call from the NewStep / ComputeStep / WriteOut family in the generated script.

![](captures/config_calculs_routines.JPG)

**2D Rigid Bodies — RBDY2**

–	RBDY2 (NewStep / FreeVelocity / WriteOut) — checked by default. Mandatory routines for any 2D rigid body. Generates RBDY2_NewStep(), RBDY2_FreeVelocity(), RBDY2_WriteOut() in the loop.

**3D Rigid Bodies — RBDY3**

–	RBDY3 (NewStep / FreeVelocity / WriteOut) — triggers the equivalent 3D routines.

**2D Contact Detectors**

Each checkbox enables contact detection between a pair of contactor types. The script generates the corresponding XXX_SelectProxTactors() and XXX_RecupRloc() / XXX_StockRloc().
|Detector	|Description|
|---|-----|
|`DKDKx`	|Disk / Disk (checked by default) — 2D granulometry, granular media|
|`DKJCx`	|Disk / Jonc — particles with ellipses|
|`DKKDx`	|Disk / Polygon (Corde) — disk-to-polygonal-wall interaction|
|`PLPLx`	|Plane / Plane — flat walls against each other|
|`CLALp`	|Masonry line / line — interfaces between bricks (CLALp)|
|`ALpALp`	|ALp line / line — variant for polygonal contactors|

**3D Contact Detectors**
|Detector	|Description|
|---|-----|
|SPSPx	|Sphere / Sphere — 3D granulometry|
|SPCDx	|Sphere / Cylinder|
|SPPLx	|Sphere / Plane|
|CDCDx	|Cylinder / Cylinder|
|CDPLx	|Cylinder / Plane|
|PRPRx	|Polyhedron / Polyhedron|

**Deformable Bodies — FEM Routines**

–	mecaFEMx — Solid mechanics: assembly, computation of internal forces (Fint), external forces (Fext), stiffness matrix (K), and resolution (ComputeDof).

–	therFEMx — Thermal: heat flux, thermal energy balance, ComputeDof resolution.

–	hydrFEMx — Hydraulic: hydraulic pressure, fluid flux, ComputeDof resolution.

**Mixed Contactors — Rigid / Deformable**

–	DKMECAx — Interaction between rigid disks (2D) and mechanical meshes (2D FEM MECAx).

–	ALpMECAx — Interaction between masonry interfaces (CLALp) and 2D FEM mechanical meshes. Useful for simulations
of masonry structures with deformable blocks.

–	SPMECAx — Interaction between rigid spheres (3D) and 3D FEM mechanical meshes.

**Special Routines**

–	PT2Dx — 2D point nodes: point/point interaction for cable elements (ELASTIC_WIRE) and elastic rods (ELASTIC_ROD).

–	PT3Dx — 3D equivalent of PT2Dx.

–	NODES — Coupled nodes: degree-of-freedom coupling routines (COUPLED_DOF, NORMAL_COUPLED_DOF).

–	UpdateBulkBehav — Bulk behavior laws: generates chipy.UpdateBulkBehav() for models with plasticity, damage, or history variables.

#### 3. Extraction
This tab configures all computation outputs: visualization files, avatar visibility, state vector extraction, contact forces, energy, and FEM fields.

![](captures/config_calculs_extraction.JPG)

**chipy Messages (logs)**

–	Disable chipy messages (utilities_DisableLogMes) — Generates chipy.utilities_DisableLogMes() immediately after chipy.Initialize(). Suppresses all progress messages in the console. Recommended for production or long-duration computations.

**Visualization (WriteDisplayFiles)**

Controls the writing of visualization files to the DISPLAY/ directory. Each checkbox corresponds to a family of avatars:
–	RBDY2_WriteDisplayFiles — 2D rigid bodies (checked by default).
–	RBDY3_WriteDisplayFiles — 3D rigid bodies.
–	mecaFEMx_WriteDisplayFiles — Mechanical deformable meshes.
–	therFEMx_WriteDisplayFiles — Thermal deformable meshes.
–	hydrFEMx_WriteDisplayFiles — Hydraulic deformable meshes.
–	Write display files in the loop — If checked, files are written at every step (or at the defined frequency). If unchecked, only a single file is written at the end of the computation.

**Avatar Visibility (SetVisible / SetInvisible)**

Allows you to show or hide avatars individually or by group at specific moments during the simulation. Each row in the list corresponds to a visibility rule.
To create a rule, click "+ Create a visibility". Each row contains:

|Action	|SetVisible or SetInvisible — makes the avatar visible or invisible in chipy.|
|---|-----|
|Dim.	|2D (RBDY2) or 3D (RBDY3) — determines the prefix of the generated function.|
|Avatar IDs	|Comma-separated list of identifiers (e.g.: 1, 3, 5). Takes priority over the group if both are filled in.|
|Group	|Name of an avatar group defined in the project. Resolved into a list of IDs at generation time.|
|Mode / Timing	|Determines when the call is generated (see timing modes table below).|

**Timing Modes**

Timing Modes

|Mode	|Generated Condition	|Typical Use|
|---|---|---|
|Every step	|No condition (direct call)	|Systematic extraction, continuous energy balance|
Every N steps	|if k % N == 0:	|Reduce write frequency to lighten outputs|
|At step k =	|if k == K:	|One-off event: change visibility at a specific step|
|After the loop	|Outside the loop (after for k ...)	|Final state only, post-processing at the end of the computation|

**RBDY2 State Vector Extraction (RBDY2_GetBodyVector)**

Generates calls to `chipy.RBDY2_GetBodyVector(vector, id)` in the computation loop. For each row added via "+ Add an RBDY2 extraction", configure:

|Vector	|Name of the state vector to extract (see full list below).|
|---|------|
|Avatar IDs	|Comma-separated list of IDs. If filled in, generates a for loop over these IDs.|
|Group	|Group of avatars to iterate over. Lower priority than IDs if both are filled in.|
|Mode / Timing	|One of the four timing modes described above.|

Available vectors:
|Name	|Description|
|---|----|
|Coor0	|Reference position (initial configuration)|
|Coor_	|Current position|
|Coorb	|Position at the previous step|
|Coorm	|Average position between two steps|
|X____	|Total accumulated displacement|
|V____	|Current velocity (linear and angular)|
|Vbeg_	|Velocity at the beginning of the step|
|Vfree	|Free velocity (before contact resolution)|
|Fext_	|Applied external forces and moments|
|Fint_	|Internal forces and moments|
|Reac_	|Resultant of contact reactions|
|Ireac	|Contact reaction impulses|

**Contact Forces and Reactions**

–	Nodal forces (inter_handler_Rnod) — Extracts nodal forces at contact points and writes them to POSTPRO/.
–	Local velocities (inter_handler_Vloc) — Extracts relative velocities in the local contact frame.
–	Local forces (inter_handler_Rloc) — Extracts impulses/forces in the local contact frame.

**Energy**

–	Global energy balance (ComputeEnergy + WriteEnergy) — Computes and writes the kinetic, potential, and friction-dissipated energy.
–	RBDY2 kinetic energy (RBDY2_KineticEnergy) — Writes the kinetic energy of each 2D rigid body separately.

**FEM Fields (stresses, strains, temperature…)**

–	Per-element fields (mecaFEMx_WriteBodies) — Writes per-element fields: stresses and strains (MECAx), temperature (THERx), pressure (HYDRx).
–	Internal variables (mecaFEMx_WriteInternalVariables) — Writes internal variables at Gauss points: plasticity, damage, history variables.

### 4. Control

This tab controls advanced functions of the computation workflow: resuming from a saved state, early stopping based on a convergence criterion, and multi-step sequencing.

![](captures/config_pilotage.JPG)

**Restart — Resuming a Computation**
Allows you to resume a computation from a state previously saved in the .dat.last files.

|Enable restart	|Generates chipy.ReadIni() then chipy.SetStep(restart_step) before the computation loop.|
|---|--------|
|Restart step	|Number of the time step from which to resume (integer, from 0 to 9,999,999).|

**Automatic Stopping Criterion**

Interrupts the computation loop before the planned number of steps is reached if a convergence criterion is satisfied.


|Enable a stopping criterion	|Enables the early stopping mechanism. Generates a break condition in the for k loop.|
|----|---------|
|Criterion type	|Three types available: energy residual (‖E_res‖ < threshold), maximum displacement (max|u| < threshold), force residual (‖F_res‖ < threshold).|
|Threshold	|Numerical value of the stopping criterion (from 10⁻¹⁶ to 1.0). Default value: 10⁻⁶.|
|Evaluation frequency	|Evaluate the criterion every N steps. Avoids computing the criterion at every iteration, which can be costly.|

**Multi-Step Sequence — Variable dt**

Allows you to define several computation phases with different time steps. Useful for computations with progressive loading or to refine the time step as a critical event approaches.

|Enable a multi-step sequence	|Generates an outer loop over the phases: for _dt in dt_sequence: chipy.TimeEvolution_SetTimeStep(_dt) + inner loop.|
|----|-------|
|Number of phases	|Between 2 and 20 phases. The total number of steps (nb_steps) is evenly distributed across the phases.|
|dt per phase	|Comma-separated list of dt values, one per phase (e.g.: 1e-3, 1e-4, 1e-5).|

### 5. 2D Inspection

This tab lets you add inspection calls on the model's 2D contactors. Each row corresponds to a chipy.XXXX_GetYYYY() call inserted in the computation loop or after it.

![](captures/config_inspect2D.JPG)

Click "+ Add a 2D inspection" to create a row. Each row contains five columns:

|chipy Function	|Selection from the dropdown list of functions available for 2D contactors. The description is displayed in the tooltip.|
|---|------|
|IDs (contactors)	|Comma-separated list of chipy identifiers. Left empty for GetNb... type functions that take no argument.|
|Group	|Name of an avatar group. Resolved into IDs at generation time if the IDs are empty.|
|Mode / Timing	|One of the four timing modes (Every step, Every N steps, At step k =, After the loop).|
|Python var.	|Name of the Python variable in which to store the result (e.g.: vel_disk). Left empty if the result is not reused.|

**Available Functions — 2D Contactors**

Functions are grouped by contactor type:

`DISKx — 2D Rigid Disks`
–	DISKx_GetNbDISKx — Total number of DISKx contactors (no ID required).
–	DISKx_GetBodyId(i) — ID of the RBDY2 body to which contactor i belongs.
–	DISKx_GetPtrDISKx2BDYTY(i) — Local index of the contactor within its RBDY2 body.
–	DISKx_GetPtrTactBehav(i) — Contact behavior law associated with contactor i.
–	DISKx_GetRadius(i) — Radius of disk i.
–	DISKx_GetCoor(i) — Coordinates of the center of disk i.
–	DISKx_GetVelocity(i) — Velocity of the center of disk i.

`JONCx — 2D Joncs / Ellipses`
–	JONCx_GetNbJONCx — Total number of JONCx contactors.
–	JONCx_GetBodyId(i), JONCx_GetPtrJONCx2BDYTY(i), JONCx_GetPtrTactBehav(i) — Identification.
–	JONCx_GetAxes(i) — Half-axes (a, b) of jonc i.
–	JONCx_GetCoor(i) — Coordinates of the center of jonc i.

`POLYR — 2D Rigid Polygons`
–	POLYR_GetNbPOLYR — Total number of POLYR contactors.
–	POLYR_GetBodyId(i), POLYR_GetPtrPOLYR2BDYTY(i), POLYR_GetPtrTactBehav(i) — Identification.
–	POLYR_GetNbVerti(i) — Number of vertices of polygon i.
–	POLYR_GetVerti(i) — Coordinates of all the vertices of polygon i.
–	POLYR_GetCoor(i) — Coordinates of the reference center of polygon i.

`xKSID — 2D Discrete Disk Clusters`
–	xKSID_GetNbxKSID, xKSID_GetBodyId(i), xKSID_GetPtrxKSID2BDYTY(i), xKSID_GetRadius(i).

`RBDY2 — 2D Rigid Bodies (summary)`
–	RBDY2_GetNbRBDY2 — Total number of 2D rigid bodies.
–	RBDY2_KineticEnergy — Total kinetic energy of all RBDY2 bodies.

`PT2Dx — 2D FEM Contactor Nodes`
–	PT2Dx_GetNbPT2Dx — Number of 2D FEM contactor nodes.
–	PT2Dx_GetBodyId(i) — ID of the parent FEM body.
–	PT2Dx_GetCoor(i) — Coordinates of contactor node i.

### 6. 3D Inspection

![](captures/config_inspect3D.JPG)

Works the same way as the 2D Inspection tab, but for 3D contactors. The available families are:

`SPHER — 3D Rigid Spheres`
–	SPHER_GetNbSPHER, SPHER_GetBodyId(i), SPHER_GetPtrSPHER2BDYTY(i), SPHER_GetPtrTactBehav(i).
–	SPHER_GetRadius(i) — Radius of sphere i.
–	SPHER_GetCoor(i), SPHER_GetVelocity(i) — Position and velocity.

`POLYH — 3D Rigid Polyhedra`
–	POLYH_GetNbPOLYH, POLYH_GetBodyId(i), POLYH_GetPtrPOLYH2BDYTY(i), POLYH_GetPtrTactBehav(i).
–	POLYH_GetNbFaces(i), POLYH_GetNbVerti(i), POLYH_GetVerti(i) — Geometry.
–	POLYH_GetCoor(i) — Coordinates of the reference center.

`CYLND — 3D Rigid Cylinders`
–	CYLND_GetNbCYLND, CYLND_GetBodyId(i), CYLND_GetPtrCYLND2BDYTY(i), CYLND_GetPtrTactBehav(i).
–	CYLND_GetRadius(i), CYLND_GetLength(i), CYLND_GetCoor(i).

`PLANE — 3D Rigid Planes`
–	PLANE_GetNbPLANE, PLANE_GetBodyId(i), PLANE_GetNormal(i), PLANE_GetCoor(i).

`RBDY3 and PT3Dx`
–	RBDY3_GetNbRBDY3 — Total number of 3D rigid bodies.
–	PT3Dx_GetNbPT3Dx, PT3Dx_GetBodyId(i), PT3Dx_GetCoor(i) — 3D FEM contactor nodes.

### 7. Interaction Inspection

This tab inspects the active contactor pairs (interactions currently occurring in the simulation). The ID used is the index of the pair in the chipy list (1-based numbering).

![](captures/config_interac.JPG)

Functions are grouped by interaction type:

``DKDKx — Disk / Disk``
–	DKDKx_GetNbDKDKx — Number of active pairs.
–	DKDKx_GetBodyIds(i) — RBDY2 IDs of the two bodies in pair i.
–	DKDKx_GetTactors(i) — IDs of the two DISKx contactors in pair i.
–	DKDKx_GetGapTT(i) — Gap of pair i.
–	DKDKx_GetStatusTT(i) — Contact status: 0 = no contact, 1 = active contact.
–	DKDKx_GetRlocTT(i) — Local reaction (Rn, Rt) in the local contact frame.
–	DKDKx_GetVlocTT(i) — Relative local velocity (Vn, Vt).

``DKJCx — Disk / Jonc``
–	DKJCx_GetNbDKJCx, DKJCx_GetBodyIds(i), DKJCx_GetTactors(i), DKJCx_GetGapTT(i), DKJCx_GetStatusTT(i), DKJCx_GetRlocTT(i).

``DKKDx — Disk / Corde (Polygon)``
–	DKKDx_GetNbDKKDx, DKKDx_GetBodyIds(i), DKKDx_GetGapTT(i), DKKDx_GetRlocTT(i).

``PLPLx — Polygon / Polygon``
–	PLPLx_GetNbPLPLx, PLPLx_GetBodyIds(i), PLPLx_GetTactors(i), PLPLx_GetGapTT(i), PLPLx_GetStatusTT(i), PLPLx_GetRlocTT(i), PLPLx_GetVlocTT(i).

``CLALp — Brick / Brick (masonry)``
–	CLALp_GetNbCLALp, CLALp_GetBodyIds(i), CLALp_GetGapTT(i), CLALp_GetStatusTT(i), CLALp_GetRlocTT(i).
●  Use CLALp with "Every step" mode to track the evolution of contact forces in masonry joints throughout the simulation.

``ALpALp — ALp / ALp``
–	ALpALp_GetNbALpALp, ALpALp_GetBodyIds(i), ALpALp_GetGapTT(i), ALpALp_GetRlocTT(i).

``SPSPx — Sphere / Sphere (3D)``
–	SPSPx_GetNbSPSPx, SPSPx_GetBodyIds(i), SPSPx_GetTactors(i), SPSPx_GetGapTT(i), SPSPx_GetStatusTT(i), SPSPx_GetRlocTT(i) (Rn, Rt, Rs), SPSPx_GetVlocTT(i) (Vn, Vt, Vs).

``SPCDx — Sphere / Cylinder (3D)``
–	SPCDx_GetNbSPCDx, SPCDx_GetBodyIds(i), SPCDx_GetTactors(i), SPCDx_GetGapTT(i), SPCDx_GetRlocTT(i).

``SPPLx — Sphere / Plane (3D)``
–	SPPLx_GetNbSPPLx, SPPLx_GetBodyIds(i), SPPLx_GetGapTT(i), SPPLx_GetRlocTT(i).

``CDCDx — Cylinder / Cylinder (3D)``
–	CDCDx_GetNbCDCDx, CDCDx_GetBodyIds(i), CDCDx_GetGapTT(i), CDCDx_GetRlocTT(i).
CDPLx — Cylinder / Plane (3D)
–	CDPLx_GetNbCDPLx, CDPLx_GetBodyIds(i), CDPLx_GetGapTT(i), CDPLx_GetRlocTT(i).

``PRPRx — Polyhedron / Polyhedron (3D)``
–	PRPRx_GetNbPRPRx, PRPRx_GetBodyIds(i), PRPRx_GetTactors(i), PRPRx_GetGapTT(i), PRPRx_GetStatusTT(i), PRPRx_GetRlocTT(i) (Rn, Rt, Rs).

``Mixed Contactors — Rigid / Deformable``
–	DKMECAx_GetNbDKMECAx, DKMECAx_GetBodyIds(i), DKMECAx_GetGapTT(i), DKMECAx_GetRlocTT(i) — Disk / 2D FEM MECAx.
–	ALpMECAx_GetNbALpMECAx, ALpMECAx_GetBodyIds(i), ALpMECAx_GetRlocTT(i) — ALp / 2D FEM MECAx.
–	SPMECAx_GetNbSPMECAx, SPMECAx_GetBodyIds(i), SPMECAx_GetRlocTT(i) — Sphere / 3D FEM MECAx.
