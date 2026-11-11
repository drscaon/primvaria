# Primvaria OpenUSD contract

**Version 0** (draft). This document says what every file written by a
Primvaria generator has in common, so that an asset from one generator
composes with an asset from any other and behaves the same in every engine.

Each rule is marked:

- **in place**: all four generators already do it, and their tests check it;
- **v0**: new with this version, to be implemented in the four generators and
  enforced by the shared conformance test (`tests/test_contract.py`);
- **planned**: named here so the direction is fixed, specified in a later
  version.

A change to the file format changes this document first, in a pull request to
this repository. See [MISSION.md](../MISSION.md).

## 1. Terms

| Term | Meaning |
|---|---|
| Asset | One generated instance or prototype: a grain, a cloth piece, a cable, a socket, a fastener, a cell, a holder. |
| Asset root | The prim that holds one asset (table in section 4). |
| Scene | A stage that places assets on the shared ground. |
| Pack | The folder a generator writes for one preset or set: the OpenUSD files and their tables. |

## 2. Stage

| Rule | Status |
|---|---|
| `metersPerUnit = 1` | in place |
| `upAxis = Z` | in place |
| `kilogramsPerUnit = 1` | in place |
| `defaultPrim` is set | in place |
| Angular drives, where an asset has them, use UsdPhysics units (per degree) | in place |

## 3. Shared ground and physics scene

In place in all four generators, written and checked by `ground.py` (the same
file in each repository).

| Prim | Content |
|---|---|
| `/World/PhysicsScene` | gravity 9.81 m/s² along −Z |
| `/World/Ground` | a 2 cm collision box whose top face is z = 0 |
| `/World/GroundMaterial` | physics material: static friction 0.6, dynamic friction 0.5, restitution 0.1 |

An asset rests on z = 0. A standalone asset file (Quincaillerie's
`assets/*.usdc`) carries no ground: its underside is at z = 0 of the asset.

## 4. Model hierarchy and asset identity

**v0.** Every asset root is a model, so that tools can find, list and
instance assets without knowing the generator.

| Prim | `kind` |
|---|---|
| Asset root | `component` |
| `/World` in a scene | `assembly` |
| Scopes between `/World` and an asset root (`/World/Cables`, `/World/Cloths`, `/World/Grains`, …) | `group` |

Asset roots by generator:

| Generator | Asset root | Note |
|---|---|---|
| Granulaire | `/World/Prototypes/Grain_NNN` | each `/World/Grains/g_NNNN` references a prototype and inherits its kind and metadata |
| Maillage | `/World/Cloths/<piece>` | |
| Filaire | `/World/Cables/<cable>`, `/World/Sockets/<socket>` | |
| Quincaillerie | the root prim of each `assets/*` file | already sets `kind` |

Every asset root also carries `assetInfo`:

| Key | Value |
|---|---|
| `name` | the asset's name, as in the pack's table |
| `identifier` | the path of the file that defines the asset |
| `version` | the generator's version |

## 5. Ground truth: the `primvaria:` namespace

**v0.** Every asset root carries these attributes, with the same names and
types in every generator:

| Attribute | Type | Value |
|---|---|---|
| `primvaria:contract` | string | version of this document the file follows (`"0"`) |
| `primvaria:generator` | token | `granulaire`, `maillage`, `filaire` or `quincaillerie` |
| `primvaria:version` | string | version of the generator that wrote the file |
| `primvaria:preset` | string | preset or catalogue entry the asset was drawn from |
| `primvaria:seed` | int | seed that reproduces this asset with the same generator version |

Generator-specific attributes keep their own namespace (`granulaire:*`,
`maillage:*`, `filaire:*`, `quincaillerie:*`); those that duplicate the
attributes above (`filaire:seed`, `maillage:version`, …) stay until the next
breaking release.

**Planned**, reserved from now on:

- `primvaria:variation:*`: every value drawn for this instance, one random
  stream per aspect, after Quincaillerie's variation model (tolerance, defect,
  wear, physics);
- `primvaria:measured:*`: every property measured on the generated asset
  (mass, shape descriptors, stiffness).

## 6. Variant sets

In place, with the names used today:

| Variant set | Generator | Variants |
|---|---|---|
| `moisture` | Granulaire | `dry`, `damp`, `wet`, `saturated` |
| `finish` | Quincaillerie | one per library finish, plus `as_generated`, the instance's worn look |
| `end_a`, `end_b` | Filaire | one variant per end the cable can carry |

**v0** rules for any new variant set:

- names are lowercase `snake_case`;
- a name means the same thing in every generator: `finish` is always a
  surface state, `moisture` always a water content;
- a default selection is always authored;
- a variant never changes the asset's identity (section 5), only its state.

**Planned:** `state` for Maillage (`flat`, `draped`, `crumpled`, `folded`).

## 7. MateFrame

In place in Filaire and Quincaillerie: anything that connects (plug and
socket, screw and nut, cell and holder) carries an `Xform` named `MateFrame`,
or `MateFrame_<feature>` when a part has several (`MateFrame_thread`,
`MateFrame_drive`).

- Its origin is on the mating plane.
- **+Z is the insertion or screwing direction.**
- Two parts mate when their MateFrames coincide, within the clearance.

The attributes that describe the mate (role, gender, insertion depth,
clearance, keying) are generator-specific today (`filaire:role`,
`filaire:insertionDepth`, …). **Planned:** common `primvaria:mate:*`
attributes.

## 8. Engines

The base of every file is plain OpenUSD: `UsdGeom`, `UsdShade` with
`UsdPreviewSurface`, and the standard `UsdPhysics` schemas. It is what the
OpenUSD validators, Blender and the MuJoCo checks read.

Engine-specific data is an extra over that base:

| Extra | Where it is today |
|---|---|
| PhysX attributes (`physxCollision:*`, `physxRigidBody:*`) | inline, in Filaire and Quincaillerie |
| OmniPhysics deformables | Maillage: a separate layer over the main file (`*_omniphysics.usda`); Granulaire: inline, API schemas applied by name |
| MaterialX | Quincaillerie's material library, beside `UsdPreviewSurface` |

**v0** rule: removing every engine-specific attribute leaves an asset that is
still valid and still passes the base checks.

**Planned:** engine extras as overlay layers in all four generators, as
Maillage does.

## 9. Pack files

Today each generator names its tables its own way:

| Generator | Per-instance table | Summary |
|---|---|---|
| Granulaire | `instances.csv`, `prototype_metrics.csv` | `summary.json` |
| Maillage | `pieces.csv` | `summary.json` |
| Filaire | `cables.csv` | `summary.json` |
| Quincaillerie | `parts.csv` | `summary.json` |

**Planned:** one schema for every pack, `manifest.json` and `instances.csv`,
with common columns that mirror section 5 followed by the generator's own.

## 10. Conformance

| Check | Status |
|---|---|
| Every OpenUSD `UsdValidation` validator, on every file and every variant, in each generator's CI | in place |
| The shared ground and physics scene (section 3), by `ground.py` | in place |
| Sections 2, 4 and 5, by `tests/test_contract.py`, the same file in the four generators, on every preset | v0 |
| A job in this repository that fails when a shared file (`ground.py`, `tests/test_contract.py`) differs between generators | v0 |

## 11. Versioning

The contract has one integer version, written in `primvaria:contract`.
A file states the version it follows; a generator release states it in its
changelog. Adding an attribute or a variant set is a minor change recorded
here; renaming or removing one raises the version.
