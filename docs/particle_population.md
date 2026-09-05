# ParticlePopulation — SoA architecture for bulk avatars

> Companion to the [developer guide](fr/dev.md) · introduced stepwise (refactor stages 1–7) · stable since v0.4.8 for eligible granulo / loops.

French full version: [docs/fr/particle_population.md](fr/particle_population.md).

---

## Why SoA?

| Approach | Structure | Use case | Practical limit |
|----------|-----------|----------|-----------------|
| **AoS** (`List[Avatar]`) | One Python object per particle | Walls, manual avatars, deformables, per-item edit | ~1.5k–3k avatars before UI lag |
| **SoA** (`ParticlePopulation`) | Homogeneous numpy arrays | Granulo, mass loops, factory | Tens/hundreds of thousands of particles |

`ParticlePopulation` **complements** `Avatar`; both live in `ProjectState`:

```
ProjectState
├── avatars: List[Avatar]
└── particle_populations: List[ParticlePopulation]
```

---

## Core model (`src/core/particle_population.py`)

| Field | Type | Role |
|-------|------|------|
| `population_id` | `str` | Stable id (`pop_<uuid>`) — **per population**, never per particle |
| `avatar_type` | `AvatarType` | Homogeneous (`RIGID_DISK` / `RIGID_SPHERE` for now) |
| `material_name` / `model_name` / `color` | `str` | Shared by all particles |
| `centers` | `(N, dim) float64` | Positions |
| `radii` | `(N,) float64` | Radii |
| `group_name` | `Optional[str]` | UI / script group |

Always construct via `ParticlePopulation.create(...)` (validates shapes and positive radii).

Particle ids are **derived**: `pop.particle_avatar_id(i)` → `"pop_xxx:i"`.  
Per-particle `Avatar` only on demand: `pop.as_avatar_view(i)` — never in a full-population loop.

---

## Two-level serialization

| Form | API | Use |
|------|-----|-----|
| Autonomous | `to_dict()` / `from_dict()` | In-memory, tests, pre-sidecar projects |
| Sidecar | `to_meta_dict()` + `.populations.npz` | Project save/load |

Sidecar keys: `"<population_id>__centers"`, `"<population_id>__radii"`.  
Helpers: `sidecar_path_for`, `save_populations_sidecar`, `load_populations_sidecar` in `particle_population_io.py`.

---

## pylmgc90 bridge

```python
bodies = LMGC90Bridge.create_avatars_from_population(pop, model_obj, material_obj)
```

Supported types: **`RIGID_DISK`**, **`RIGID_SPHERE`**. Direct numpy access; still one `pre.rigid*` call per particle (API limit).

---

## UI entry points

- Granulometry tab / wizard — checkbox “Create as ParticlePopulation (SoA…)”
- Loop tab (avatar target) — same idea

Unchecked → classic AoS path.

---

## Contributor checklist

1. Mass generation path with `use_population` flag  
2. Eligibility: type ∈ {RIGID_DISK, RIGID_SPHERE}, single material/model  
3. `ParticlePopulation.create` only  
4. Update `state.particle_populations` + `populations_groups`  
5. Serializer writes/reads sidecar  
6. Viewer/tree handle `isinstance(..., ParticlePopulation)`  
7. Unit tests: create, dict round-trip, sidecar round-trip  

See the French page for full tables, flow diagrams and file map.
