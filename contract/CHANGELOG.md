# Changelog

All notable changes to primvaria-contract are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/) with PEP 440 pre-release versions.

## [Unreleased]

## [0.4.0b1]

### Added

- Material labels (contract, section 5): `contract.write_material_label(material, label)` writes `semantics:labels:material`, one word for what a Material is made of; `contract.label_materials(stage, label)` gives one label to every Material the edit target defines that has none (class prims included, not the copies that reference them); `contract.unlabelled_materials(stage)` lists those without one. Optional in contract 0, so not a conformance problem; `testing.contract` requires it of the generators' own files.
- The shared ground (`ground.ground`) is rendered with its own material: `/World/GroundMaterial` gains a grey UsdPreviewSurface (`GROUND_ROUGHNESS` 0.9) and is bound to the ground for every purpose as well as for physics; the material carries the material label `concrete` (`GROUND_MATERIAL_LABEL`) and the ground the class label `ground` (`GROUND_LABEL`). Its physics is unchanged.

## [0.3.0b1]

### Added

- `testing`: the tests the four generators kept as byte-identical copies, written once. `testing.contract` (the generated files follow the contract), `testing.pack` (the pack says what the files say) and `testing.golden` (the same values as the stored references, one test per case of the generator's `tests/golden/cases.json`). A generator's `tests/test_contract.py`, `test_pack.py` and `test_golden.py` are each one import of them; they take its files from its fixtures (`contract_files`, `pack_folder`) and find the generator as before, the package under `src/` with a `contract.py`. The tests are the same as before, one for one. They need pytest, which stays out of the package's dependencies.

## [0.2.0b1]

### Added

- `validate`: the OpenUSD validators shipped with OpenUSD (the UsdValidation registry), run on each file once per variant of every variant set, as the generators' `validate.py` did; also `python -m primvaria_contract.validate` for files of any generator. A path that does not exist is reported (`not found`) and fails the command, as Filaire's copy already did.

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
