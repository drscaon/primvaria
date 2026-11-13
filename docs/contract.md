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
types in every generator, and no other prim carries a `primvaria:*`
attribute:

| Attribute | Type | Value |
|---|---|---|
| `primvaria:contract` | string | version of this document the file follows (`"0"`) |
| `primvaria:generator` | token | `granulaire`, `maillage`, `filaire` or `quincaillerie` |
| `primvaria:version` | string | version of the generator that wrote the file |
| `primvaria:preset` | string | key of the preset or catalogue entry the asset was drawn from (`beach_sand`, `ISO4017_M8x30`) |
| `primvaria:seed` | int | seed of the run that drew the asset: with the asset's name and the same generator version, it reproduces it. `0` for an asset that is not drawn (Filaire's sockets, a Quincaillerie part written on its own) |

Generator-specific attributes keep their own namespace (`granulaire:*`,
`maillage:*`, `filaire:*`, `quincaillerie:*`) and never repeat the attributes
above or the drawn values of section 6: a generator's own preset, seed,
version or variation metadata is not written.

`primvaria:variation:*` holds what was drawn for the asset (section 6).

`primvaria:measured:<name>` holds what was measured on the asset once
generated, with the value types and the naming of the drawn values
(`snake_case`, the unit as a suffix):

| Generator | Measured |
|---|---|
| Granulaire | `mass_kg`, `mass_<state>_kg`, `volume_m3`, `area_m2`, the three axes, `elongation`, `flatness`, `sphericity`, `convexity`, `angularity_deg` |
| Maillage | `mass_kg`, `area_m2`, `perimeter_m`, `vertices`, `faces`, `edge_mean_mm`, `edge_cv`, `min_angle_deg`, `min_angle_p05_deg` |
| Filaire | `cable_mass_kg`, `end_a_mass_kg`, `end_b_mass_kg`, bending, torsional and axial stiffness, `segments`, `segment_length_m` |
| Quincaillerie | `mass_kg`, `colliders` |

## 6. Variation model

**v0.** The reference implementation is Quincaillerie's `variation.py`; the
four generators follow the same rules.

**Aspects.** A generator varies its assets along a fixed list of aspects,
each of which can be switched off:

| Generator | Aspects |
|---|---|
| Granulaire | `size`, `shape`, `roundness`, `mineralogy`, `orientation`, `moisture` |
| Maillage | `size`, `cut`, `corners`, `fabric`, `color` |
| Filaire | `length`, `layout`, `ends`, `color`, `stiffness`, `density` |
| Quincaillerie | `tolerance`, `defect`, `wear`, `physics` |

**Rules.**

1. *Reproducible.* The same generator version, preset, seed and options give
   the same assets.
2. *Independent aspects.* Switching an aspect off leaves every value drawn
   for the other aspects unchanged, so two runs with the same seed differ by
   that aspect alone. A generator gets there with one random stream per
   aspect, or by always drawing and then overriding.
3. *Nominal when off.* An aspect that is switched off takes its nominal value
   (the middle of its range, the first of its list), and that value is still
   recorded.
4. *Recorded.* Every drawn value is written on the asset root and in the
   pack's table, under the same name.

**Recording.**

| Attribute | Type | Value |
|---|---|---|
| `primvaria:variation:aspects` | string[] | the aspects that were switched on for the run; empty for an asset that is not drawn |
| `primvaria:variation:<name>` | bool, int, double, string, double[] or string[] | one drawn value |

Names are lowercase `snake_case` with the unit as a suffix when the value has
one (`diameter_m`, `clearance_mm`, `cut_skew_deg`, `youngs_modulus_pa`). The
pack's table has the same values in columns named `variation:<name>`. In
Granulaire the values are written on the prototype and inherited by the
grains; a grain adds its own drawn `moisture` state.

Each generator tests rules 1 to 3; the conformance check requires
`primvaria:variation:aspects` on every asset root and checks the names.

## 7. Variant sets

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

## 8. MateFrame

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

## 9. Engines

Every file is plain OpenUSD: `UsdGeom`, `UsdShade` with `UsdPreviewSurface`,
and the standard `UsdPhysics` schemas. It is what the OpenUSD validators,
Blender and the MuJoCo checks read, and it is complete on its own.

What only one engine reads is not in the file. It is an **engine layer**
beside it:

- named `<file stem>_<engine>.usda` (or `.usdc` when it holds large meshes);
- its only sublayer is the file, so opening the layer gives the file plus the
  engine's data, and the file alone never depends on it;
- it adds opinions to what the file defines. It defines prims of its own only
  where the engine needs geometry the file does not have (a simulation mesh,
  an engine material);
- an opinion on something that exists in one variant only is written inside
  that variant.

| Layer | Holds | Written by |
|---|---|---|
| `*_physx` | PhysX solver iterations and contact offsets (`PhysxRigidBodyAPI`, `PhysxCollisionAPI`) | Filaire and Quincaillerie, for every file with physics; a scene's layer references the layers of its parts |
| `*_omniphysics` | OmniPhysics deformable bodies: schemas, simulation mesh, deformable material | Maillage (surface deformables, every piece) and Granulaire (volume deformables, packing peanuts and cherry tomatoes: rigid bodies in the file) |

MaterialX is not an engine layer: Quincaillerie's material library offers it
beside `UsdPreviewSurface`, in the same file.

**v0** rules:

- a file holds no schema or attribute of an engine (`Physx*`, `OmniPhysics*`,
  `physx*:`, `omniphysics:`);
- a file is valid and passes its generator's checks without its layers;
- a generator says in its own namespace what an engine must know and cannot
  guess (for example `quincaillerie:contactOffset`, the distance from which a
  threaded part needs contacts), and the engine layer copies it.

Each generator checks the structure of its layers (`python -m
<generator>.physx`, `python -m <generator>.omniphysics`). No layer has been
simulated: both engines need Isaac Sim and an NVIDIA RTX GPU.

## 10. Pack files

**v0.** Every pack has the same two files, written by the same module
(`pack.py`) in the four generators.

`instances.csv` has one row per asset, read back from the OpenUSD files, so
the table and the files cannot disagree. An asset is listed from the file
that defines it; a scene or a layer that only references it does not list it
again. Columns, in this order:

| Columns | Content |
|---|---|
| `name`, `file`, `prim` | the asset root's name, its file (relative to the pack) and its path |
| `generator`, `version`, `preset`, `seed` | the identity of section 5 |
| `aspects` | the aspects that were switched on, separated by spaces |
| `variation:<name>` | every drawn value (section 6) |
| `measured:<name>` | every measured value (section 5) |
| the generator's own | Granulaire: `prototype`, `x_m`, `y_m`, `z_m`; Filaire: `jacket`; Quincaillerie: `kind`, `size`, `format`, `length_mm`, `family` |

Lists are separated by spaces, booleans are `true` and `false`, and a cell is
empty where an asset has no such value.

`manifest.json` says what the pack is: `contract`, `generator`, `version`,
`pack` (the preset or the set), `seed`, `aspects`, `assets` (the number of
rows), `table`, `files` (the pack's OpenUSD files) and `summary`, the
generator's own statistics.

A generator may write other files beside them (Granulaire's
`prototype_metrics.csv`, textures, previews, engine exports).

## 11. Conformance

| Check | Status |
|---|---|
| Every OpenUSD `UsdValidation` validator, on every file and every variant, in each generator's CI | in place |
| The shared ground and physics scene (section 3), by `ground.py` | in place |
| Sections 2, 4, 5 and the recording of section 6, by `python -m <generator>.conformance` on every preset in each generator's CI, and by `tests/test_contract.py` | v0 |
| Section 10: the same command checks every pack it finds, the table must say what the files say; `tests/test_pack.py` | v0 |
| The files the generators share are byte-identical: `ground.py`, `contract.py`, `conformance.py`, `pack.py`, `tests/test_contract.py` and `tests/test_pack.py`. `scripts/check_shared_files.py` in this repository fails when one differs, in CI and weekly | v0 |

## 12. Versioning

The contract has one integer version, written in `primvaria:contract`.
A file states the version it follows; a generator release states it in its
changelog. Adding an attribute or a variant set is a minor change recorded
here; renaming or removing one raises the version.
