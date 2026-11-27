# SimReady

[SimReady Foundation](https://nvidia.github.io/simready-foundation/) is NVIDIA's open
specification of what a simulation-ready OpenUSD asset holds, organised in profiles. Its
validator runs on CPU without Omniverse or Kit:

```bash
pip install simready-validate simready-foundation-tier-core
simready-validate --profile Robotics-Prop --version 5.0.0 path/to/file.usdc
```

The profile that fits the suite is **Robotics-Prop**, a rigid object a robot handles. The
same rules are behind Isaac Sim's own asset validation, so passing them is a way to know a
file is ready for Isaac Sim without a GPU. `scripts/simready_check.py` runs the validator on a
sample of every generator's presets in CI and writes a report; it informs, it does not block.

## Where the files stand

Checked on 27 November 2026 with simready-validate 2026.10.0 and Robotics-Prop 5.0.0.

**Met.** Every Material says what it is made of (`semantics:labels:material`, contract,
section 5), the shared ground is rendered with its own material and labelled `ground`, assets
carry their class and instance labels, the physics is plain UsdPhysics, textures are wired as
UsdPreviewSurface expects. Payloads are not asked for.

**Not met, by design of the suite's packs:**

| Requirement | Why the files differ |
|---|---|
| One USD file per folder, the asset alone (`NP.005`) | a pack is a scene: `/World` with the ground and many assets, and its engine layers (`_physx`, `_newton`, `_omniphysics`) lie beside the file (contract, section 9), where the profile expects the runtimes as variant sets inside one file |
| A thumbnail per asset (`SR.002`), metadata (`SR.004`: author, licence, category, Wikidata code, mass, extents, date) | SimReady packaging, not written by the generators |
| An asset's forward direction (`AF.001`) | an attribute in NVIDIA's `simready:` namespace, not written in the base files |
| Every dependency inside the asset's folder (`AA.001`) | Quincaillerie's assets share one material library and its textures, one folder up |

These belong to a SimReady export, an option that writes each rigid asset in the layout the
profile asks for, leaving the default output as it is (backlog PRV-66).

**Not met, and staying so:**

| Requirement | Why |
|---|---|
| Normals on every mesh (`VG.027`) | the meshes without normals are colliders (purpose guide, never rendered) and Maillage's cloth, whose points change as it drapes: normals written once would be wrong as soon as it moves, so renderers compute them |
| Rigid bodies (`RB.001`) | Maillage's cloth is not a rigid prop; SimReady has no profile for deformables yet |
