# Changelog

All notable changes to primvaria-contract are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/) with PEP 440 pre-release versions.

## [Unreleased]

## [0.1.0b1]

### Added

- The code of the Primvaria OpenUSD contract, version 0, that the four generators copied
  until now: `contract` (identity, variation, measurements, semantic labels, variant sets,
  MateFrames, engine layers, `conformance` and `check`), `pack` (`instances.csv`,
  `manifest.json`), `ground` (the shared ground and physics scene) and `conformance` (the
  command line, also `python -m primvaria_contract.conformance` for files of any generator).
- The generator that writes or checks is given explicitly: `write_identity(...,
  generator=, version=)`, `write_pack(..., generator=, version=)`, and `conformance(stage,
  generator, version)` and `check(path, generator, version)`, where leaving them out checks
  assets of any generator of the suite (what `own=False` did in the generators' copies).
- Tests of the checks on stages written by hand, moved from the generators' shared
  `tests/test_contract.py`.
