# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/) with PEP 440
pre-release versions.

## [Unreleased]

### Added

- The website has one page per subject: a short home, the engine matrix, the
  contract and the mission, and for each generator its README and every page
  of its `docs/` folder, rendered from the repositories' Markdown files
  (`site/build.py`, `site/layout.html`, `site/style.css`, `site/pages/`). The
  build fails on a broken internal link and writes the sitemap.
- `.github/workflows/generator-checks.yml`, a reusable workflow with the checks
  every generator runs the same way (lint and format, tests on every Python
  and platform with a smoke test, oldest OpenUSD, package build): the four
  generators call it, so the ruff version and the test matrix are written
  once.
- `docs/engines.json`, the one source of the engine matrix, and
  `scripts/sync_engines.py`, which renders it into the README and the website
  and fills the generators' counts on the site from the installed packages; a
  test fails when either is out of date.
- `CONTRIBUTING.md`, issue templates (bug report, links to the generators for preset requests),
  `SECURITY.md` and `CITATION.cff`.
- `MISSION.md`: the mission, the three verbs (vary, measure, prove), the
  audience, the entry gate every change passes and the non-goals.
- `docs/contract.md`: version 0 of the OpenUSD contract shared by the four
  generators (stage, ground and physics scene, asset identity and the
  `primvaria:` namespace, variant sets, MateFrame, engine extras, pack files).
- Pull request template with the mission checklist, the same in the five
  repositories.
- `scripts/check_shared_files.py` and its CI job (on every change and weekly):
  fails when a file the four generators share (`ground.py`, `contract.py`,
  `conformance.py`, `tests/test_contract.py`) differs between them.
- Website footer: links to the mission and the OpenUSD contract.

### Changed

- `docs/contract.md`, section 9: engine data is no longer in the files. It is
  an engine layer beside each file (`<file>_physx`, `<file>_omniphysics`),
  in the four generators; a file holds no schema or attribute of an engine
  and is complete without its layers.

- `docs/contract.md`: the measured values (`primvaria:measured:*`, section 5)
  and the pack files (`instances.csv` and `manifest.json`, section 10) are part
  of version 0; the shared-files guard also covers `pack.py` and
  `tests/test_pack.py`.
- `docs/contract.md`, new section 6, the variation model: aspects per
  generator, the rules (reproducible, independent aspects, nominal when off,
  recorded) and the `primvaria:variation:*` attributes.
- `docs/contract.md`: a generator's own namespace never repeats the identity
  or the drawn values (the duplicates were removed from the four generators).
- `docs/contract.md`: `primvaria:seed` is the seed of the run (`0` for an asset
  that is not drawn), `primvaria:preset` the preset's key; conformance is
  checked by `python -m <generator>.conformance`.

## [0.2.0b1] - 2026-11-11 (beta)

Requires the generators' new releases (Granulaire 0.3.0b1, Maillage 0.2.0b1,
Filaire 0.3.0b1, Quincaillerie 0.2.0b1), which share one ground and physics scene.

### Breaking changes

- Python 3.11 or later (was 3.10): MuJoCo 4 requires it, and Python 3.10 reached
  its end of life in October 2026.
- Minimum generator versions raised to the releases that share the ground and
  physics scene and require Python 3.11, usd-core 26.5 and MuJoCo 4.

### Added

- One-minute demo video on the website (`site/demo.mp4`, section "See it in
  one minute") and a GIF of the terrain test at the top of the README: the
  generators' variations and their tests, simulated in MuJoCo and rendered in
  Blender.
- Website, [primvaria.com](https://primvaria.com): the four generators and the
  engine matrix, built from `site/` and deployed to GitHub Pages by the
  `pages.yml` workflow.
- README: engine matrix, PyPI and website badges.
- Logo: the mark (nine primitives, no two alike) and the wordmark, light and
  dark, the website's favicon and the GitHub social preview, drawn by
  `scripts/make_logo.py`.
- Social preview built from the four generators' renders (one tile each,
  named), by `scripts/make_social_preview.py`; also the website's link
  preview.

### Changed

- README: the ground and physics scene the four generators now share.
- `sim` extra: the MuJoCo checks of all four generators (Granulaire and Maillage have
  theirs now); new `blender` extra (Blender as a Python module, Python 3.13 only).
- Engine matrix: Filaire's bayonet-lock test in MuJoCo.
- Filaire: 20 presets and 24 connector families, with the BNC coaxial lead and its
  bayonet lock.
- Filaire on the website and in the README: 19 presets and 23 connector families,
  with the robot and drone leads (servo, battery, balance, jumper) and CAN bus.
- The project's homepage on PyPI is primvaria.com.
- Website search metadata: a title and description naming what the project is
  (OpenUSD asset generators for robot simulation), canonical URL, structured
  data (schema.org) for the suite and the four generators, `robots.txt` and
  `sitemap.xml`.

## [0.1.0b1] - 2026-10-29

### Added

- First beta of the suite package: `pip install primvaria` installs
  Granulaire, Maillage, Filaire and Quincaillerie.
- Extras `render`, `sim`, `materialx` and `all`, mapped to the generators'
  own extras.
- `primvaria` command line: `primvaria list` shows the generators and their
  installed versions; `primvaria <generator> ...` runs that generator's
  command line.
- CI on Python 3.10–3.13, and a release workflow publishing to PyPI through
  Trusted Publishing.
