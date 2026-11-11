# Mission

**Physics-ready variability for Physical AI, in OpenUSD.**

Primvaria generates the objects robots struggle with most (grains, cloth,
cables and small mechanical parts) as OpenUSD assets that are variable,
measured and proven in real engines.

This file is the reference every change in the suite is checked against: the
Primvaria package and the four generators,
[Granulaire](https://github.com/drscaon/granulaire),
[Maillage](https://github.com/drscaon/maillage),
[Filaire](https://github.com/drscaon/filaire) and
[Quincaillerie](https://github.com/drscaon/quincaillerie).

## The three verbs

| Verb | What it means | How it shows |
|---|---|---|
| **Vary** | Distributions instead of one shape. No two generated instances are the same, and each aspect of the variation has its own seed. | Every draw is written into the asset and into the pack's tables as ground truth. |
| **Measure** | Outputs are measured on what was generated, not trusted from the inputs. | Mass, shape and stiffness measurements ship with the asset, so a training set can be filtered and stratified. |
| **Prove** | Each preset passes physical tests in named engines, from the OpenUSD file alone. | One engine matrix, and a Limits section in every README that says what was not tested. |

OpenUSD is the contract that carries all three: see
[docs/contract.md](docs/contract.md).

## Who it is for

Simulation tooling engineers in robot-learning teams who need asset diversity.
The main uses are robustness testing (the same policy against many variations
of the same object) and the simulation of real maintenance tasks, where parts
are worn, damaged or out of tolerance, not factory-new.

## The entry gate

A change enters a sprint, and a pull request is merged, only with a yes to
all five questions:

1. Does it strengthen at least one verb (Vary, Measure, Prove) on an asset
   that already exists, or does a user request justify the new asset?
2. Is the output still plain OpenUSD in its base layer, readable without any
   engine-specific overlay?
3. Does it run on CPU?
4. Does it have an acceptance criterion that CI can check?
5. Is the limit that remains written in the README?

The pull request template of each repository carries this checklist.

## Non-goals

- Common rigid household objects, which existing asset libraries cover well.
- One-off assets modelled by hand: everything here is generated and seeded.
- A mandatory GPU. Everything can run on CPU; engines that need a GPU are
  targets to test against, not requirements.
- Dependence on a single engine. Engine-specific attributes are extras over a
  base that every OpenUSD tool reads.
- Output formats other than OpenUSD as a primary output. Other formats are
  written only to run a check (a MuJoCo model, for example) or on request.

## Parked until triggered

These are in scope but wait for a trigger, so they do not displace quality
work on the existing assets:

| Parked | Comes back when |
|---|---|
| Isaac Sim / PhysX and OmniPhysics runs on a rented GPU | there is external engagement: a first outside issue or request |
| New presets, connectors and parts | someone asks, through a preset-request issue |
| CAD (STEP) and MJCF exports | someone outside the project asks |

## How the mission is kept

- **Contract first.** A change that touches the file format goes through
  [docs/contract.md](docs/contract.md) in this repository before it reaches a
  generator.
- **Quality before breadth.** Most of each sprint goes to the realism of what
  already exists; at most one breadth item (a new preset, connector or part)
  per sprint.
- **One release train.** At the end of a sprint the generators and the suite
  are released together and the engine matrix is updated.
