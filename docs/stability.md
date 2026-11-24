# Stability and the road to 1.0

Primvaria is for evaluation: someone runs a robot against these assets and
draws a conclusion. That only holds if the asset is the same each time, says
what it really is, and says where it stops being credible. This page says
what the suite promises today, and what must be true before it leaves beta.

## Today: beta

All five packages are beta (`0.x.0bN`). The file format follows
[contract](contract.md) version 1, candidate: its rules are frozen and
breaking them follows the contract's section 12. Generated values are not
frozen yet: a release may still change the values drawn for a given preset
and seed, and says so in its changelog under *Changed values*.

## What 1.0 promises

From the 1.0 release of a generator on:

- **Same input, same asset.** The same generator version, preset, seed and
  options give the same file on Linux, macOS and Windows and on every
  supported Python.
- **Changed values are a major change.** A release that changes the drawn or
  measured values of an existing preset and seed raises the generator's
  major version.
- **The format changes only through the contract.** A breaking change to
  what a file holds raises the contract's version first (section 12), with a
  deprecation period.

## Exit criteria

The suite leaves beta when all of these hold, in all four generators. Each
one is checked in CI, except the last two, which are read by a person.

| # | Criterion | Backlog item |
|---|---|---|
| 1 | Reproducibility tests: stored reference values of several presets are compared on Linux, macOS and Windows and on every supported Python (before every release; on Linux and Python 3.12 on each commit). **Met** since 16 November for Python 3.11 to 3.13 (`tests/test_golden.py`); newer Pythons are not tested yet | PRV-32 |
| 2 | What is drawn follows what the preset declares, by a statistical test per generator. **Met** since 17 November (`tests/test_distributions.py` and `docs/variation.md` in each generator) | PRV-34 |
| 3 | The four generators agree on their shared behaviour: command line, pack columns, documentation pages. **Met** since 17 November (`scripts/check_consistency.py`, `tests/test_consistency.py`) | PRV-35 |
| 4 | Every contract rule is checked by a test, including those section 11 lists as not checked. **Met** since 17 November: sections 7 and 8 were the last (section 11) | PRV-35 |
| 5 | Every physical value of a preset names its source, or is marked as an estimate | PRV-33 |
| 6 | The engine matrix and every Limits section say, per engine, what was tested and what was not, and whose limit it is (the asset's or the engine's) | review |
| 7 | One full sprint with no breaking change to the contract or to the values of any generator | review |

## Not required for 1.0

These would add evidence, but 1.0 does not wait for them, and the
documentation must not suggest they were done:

- a run in Isaac Sim, PhysX or OmniPhysics (they need an RTX GPU);
- a check in Newton or against NVIDIA's SimReady profiles;
- calibration against measurements of real materials;
- outside users.
