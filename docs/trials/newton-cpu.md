# Trial: Newton on CPU as a second engine

PRV-30, 14 November 2026. One preset per generator, written by the releases of
13 November, opened in [Newton](https://github.com/newton-physics/newton) 1.8.0
on CPU (2 cores, no GPU) from the file alone, with the XPBD solver. The MuJoCo
Warp solver was left out on purpose: it is the algorithm the generators are
already checked with. The script is `scripts/newton_trial.py`.

This was a trial. Option 1 below was then taken (23 November 2026): Newton is
now a column of the engine matrix, checked in CI on every preset; see
[Outcome](#outcome-newton-in-ci) at the end.

## Answers

| Question | Answer |
|---|---|
| Do the files open unchanged? | Grains and fasteners: yes, with exact masses; they simulate correctly once the contact gap is set, which the PhysX layer already does. Cables: the file opens, but Newton locks every cable joint, so the cable is a rigid bar (finding 2). Cloth: not read (finding 3). |
| How long on CPU? | Seconds to about a minute per scene (table below), slower than MuJoCo but usable in CI. |
| How far from MuJoCo? | Grains and fasteners: same masses and same outcome (at rest on the ground, nothing through it), with higher residual speeds in XPBD. Cables and cloth: no comparison is possible yet. No preset was compared value by value. |

## What was run

| Generator | File | Newton sees | Mass, Newton / pack | Simulated | Wall time | Result |
|---|---|---|---|---|---|---|
| Granulaire | `granulaire_crushed_gravel.usdc`, 60 grains | 60 bodies, 121 shapes | 0.073164 / 0.073164 kg | 6 s | 24 s | at rest, none below the ground |
| Filaire | `filaire_usb_c_physx.usda` | 1014 bodies, 1014 joints with **0 degrees of freedom**, 2453 shapes | 0.266560 / 0.266561 kg | 2 s | 65 s | rests on the ground, but as rigid bars: not a cable test |
| Quincaillerie | `scene_physx.usda`, M10 screw, nut, washer and their assembly | 6 bodies, 2075 shapes | 0.081724 / 0.081724 kg | 1 s | 40 s | at rest, assembly in place |
| Maillage | `maillage_tea_towel_omniphysics.usda`, 12 pieces | no cloth (see below) | not read | not run | | import only |

Import takes 1 to 7 seconds. The first run also compiles Newton's kernels
(about a minute, cached afterwards). The MuJoCo pile test of the same gravel
takes 9 seconds for 6.2 simulated seconds.

Residual linear speed at the end: 3 to 9 mm/s in XPBD. The MuJoCo pile test
ends below 0.2 % of its reference speed, so XPBD is noisier at rest; a check
in Newton needs its own tolerance, not MuJoCo's.

## Findings

### 1. Newton's default contact gap is 0.1 m

A shape with no authored gap gets 0.1 m, a robot-scale default. For parts a
few millimetres across, every shape is then "near" every other one: the
fastener scene starts with 103 450 candidate contacts, which is exactly the
size of the contact buffer. Contacts are dropped, and the nut falls through
the ground; cable segments do the same, and one grain of the gravel got a
non-finite angular velocity.

With a gap suited to the parts, all three scenes are stable. Two ways, both
tested:

- open the PhysX engine layer with Newton's PhysX resolver
  (`--physx`): the layer's `physxCollision:contactOffset` becomes the gap.
  No change to the files. Contacts at start: 6 188 for the fasteners.
- set the gap in the script (`--gap 0.0005`), for files that have no PhysX
  layer (Granulaire).

The files are not at fault: OpenUSD has no standard attribute for a contact
gap. But it means "opens in Newton" is true and "simulates in Newton as it
is" is not, unless the gap is given.

### 2. Newton locks Filaire's cable joints

A Filaire cable is a chain of rigid segments. Each joint is a generic
`PhysicsJoint` whose three translations are locked (`LimitAPI`, low above
high) and whose three rotations are free and carry the bending and torsion
stiffness in a `DriveAPI`. In UsdPhysics an axis of a generic joint with no
limit is free.

Newton's importer builds the degrees of freedom of such a joint from its
limits only: an axis with no `LimitAPI` gets none. The 996 cable joints of the
USB-C file come out with 0 degrees of freedom, and the stiffness is not read.
The cable is then a set of rigid bars. It rests on the ground, which says
nothing about a cable.

Checked by adding, in memory, a wide rotation limit (±170°) to every cable
joint and nothing else: Newton then gives each joint 3 rotational degrees of
freedom and reads the stiffness exactly (0.0583 and 0.0835 N·m/rad for
0.0010176 and 0.0014567 N·m/deg in the file), and the cables stay stable for
1 s. So the limit is in Newton's reading of free axes, not in the values the
file holds. No sag, coil or insertion was run.

Separately, Isaac Sim's own Newton backend did not support cables or
deformables as of Isaac Sim 6.0.1 (NVIDIA's answer on its forum); that is
about Newton's rod model, which Filaire does not use.

### 3. The cloth layer uses names Newton does not read

Maillage's layer applies `OmniPhysicsDeformableBodyAPI` and
`OmniPhysicsSurfaceDeformableSimAPI`, with `omniphysics:` attributes. Newton
reads the names of the AOUSD proposal: `PhysicsDeformableBodyAPI`,
`PhysicsSurfaceDeformableSimAPI`, `physics:` attributes. With the layer as it
is, Newton sees no cloth.

A copy of the layer with only those names changed imports as 12 cloths,
18 728 particles, 0.799525 kg: the pack's mass exactly. Newton then warns
about three details: `restBendAnglesDefault` is `flatDefault` in the layer
(`flat` expected), thickness is expected on the geometry and not on the
material, and the shear stiffness is not used. No drape was simulated: on two
cores, 18 728 particles were out of this trial's budget.

### 4. Newton needs its own environment

`newton[sim]` installs MuJoCo 3.x, which replaces the MuJoCo 4.0.1 the
generators are checked with. `newton[importers]` alone is enough for this
trial, but it pins `usd-core` 26.8, below the 26.11 used here. A Newton check
therefore runs in a separate job with its own environment.

### 5. What matched without any work

Bodies, colliders, the ground, friction and the masses were all read from
plain `UsdPhysics`. The masses agree with `instances.csv` to the last digit in
the three rigid generators, which is an independent confirmation that the
files say what the pack says. Joints are the exception (finding 2).

## Not done

- No drape, sag, coil, plug or threading test: only settling at rest.
- Nothing about cable behaviour: with the joints locked there is no cable.
- Friction and thread contact were not examined: settling shows stability,
  not that contact behaves as in MuJoCo.
- No value-by-value comparison with MuJoCo.
- One preset per generator, one seed.
- The VBD solver was not tried.

## Options

1. **Add Newton as a third engine**, in its own CI job, for what it reads
   today: import and mass agreement for every preset of the four generators,
   settling for grains and fasteners. The matrix says, per generator, what
   Newton reads and what it does not, and that the two gaps (free joint axes,
   cloth schema names) are on Newton's side of the file.
2. **Add a Newton engine layer** to the contract (`<file>_newton.usda`) that
   authors the contact gap, wide limits on the cables' rotation axes, and for
   Maillage the proposal's schema names, so that the files simulate in Newton
   with no option. This is a feature and a contract change.
3. **Stop here**: the matrix says "Newton 1.8.0: tried on CPU, see the trial".

## Outcome: Newton in CI

23 November 2026, option 1. `scripts/newton_check.py` runs in Primvaria's CI
(job "Newton on CPU, every preset"): it writes a small pack of every preset of
the four generators, then opens each file in Newton 1.8.0 with XPBD on CPU, in
its own environment (finding 4). About 3 minutes to write the packs and 6 to
check them on two cores. What it checks:

| Generator | Files | Checked |
|---|---|---|
| Granulaire | 25 presets, 24 grains each, deformables off | mass equals the pack's; after 2 s every pose finite, no centre of mass below the ground, every grain below 5 cm/s. Contact gap: a quarter of the smallest grain, at most 0.5 mm (finding 1) |
| Quincaillerie | the 31 parts of the catalogue, each from its own PhysX layer | the same, after a 5 cm drop onto Newton's ground plane (an asset file has no ground) |
| Filaire | 20 presets, one cable each | mass equals the pack's; joints and degrees of freedom recorded, no settling (finding 2) |
| Maillage | 12 presets | what Newton reads, recorded (finding 3) |

All pass. The run found one more gap on Newton's side:

### 6. Newton refuses joints outside an articulation

The 10 battery holders carry a clip or a spring joint between two of their
bodies, with no `PhysicsArticulationRootAPI`: in UsdPhysics such a joint is
simulated as a constraint. Newton 1.8.0 refuses it when the model is
finalized ("joints not belonging to any articulation"). The check records the
refusal for these files instead of failing.

A check that passes says what is in the table above and no more: settling at
rest is stability, not contact behaving as in MuJoCo, and nothing here is a
cable or cloth test.

## Newton layers (24 November 2026)

The gaps above were on Newton's side, but every one of them can be met by the
file without breaking it. Each generator now writes a Newton layer beside each
file with physics, `<file>_newton.usda` (contract section 9, a new engine layer:
no new contract version, the files and the other layers unchanged), and
`generate --engines` chooses which layers are written:

| Finding | What the Newton layer adds |
|---|---|
| 1. contact gap | `newton:contactGap` on every collider: the asset's contact offset (Quincaillerie, Filaire), a quarter of the grain (Granulaire) |
| 2. free joint axes locked | a ±170° limit on each rotation between two cable segments, never reached |
| 3. OmniPhysics deformables not read | Maillage's cloth in the AOUSD proposal's schemas (`PhysicsSurfaceDeformableSimAPI` and the rest), the same values |
| 6. joints outside an articulation refused | `PhysicsArticulationRootAPI` on each battery holder |

`scripts/newton_check.py` now opens the Newton layers with Newton's own schema
resolver and sets nothing itself. 98 of 98 pass on CPU:

| Generator | Checked |
|---|---|
| Granulaire, 25 presets | mass as the pack; at rest on the ground after 2 s |
| Quincaillerie, 41 assets, holders included | mass as the pack; at rest after a 5 cm drop |
| Filaire, 20 presets | mass as the pack; hung from its first segment, the cable bends under its weight (a rigid one would not move) |
| Maillage, 12 presets | read as cloth, mass as the pack; raised 5 cm, at rest on the ground after 1 s |

What it does not say: a hung cable keeps swinging, because under XPBD the
drives' damping has almost no effect (100 times the damping changed the swing
speed by under 10 %); neither the cable's bend nor the cloth's drape is
compared with MuJoCo or with beam theory yet.
