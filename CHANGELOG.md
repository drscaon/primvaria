# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/) with PEP 440
pre-release versions.

## [Unreleased]

### Fixed

- Site: the engine matrix's header row is written from `docs/engines.json` with the rows; it
  was hand-written, so the Newton column had shifted every title after MuJoCo and left the
  last column without one.

### Added

- Site and README: a second video on the home page, the four generators on one workbench
  (`#bench`), with its own schema.org VideoObject and sitemap entry.
- Newton on CPU in the engine matrix (PRV-30): `scripts/newton_check.py` and a CI job open
  every preset of the four generators in Newton 1.8.0 (XPBD) and check mass against the pack,
  then settling for grains and parts. What Newton does not read is recorded as on Newton's side:
  free joint axes, joints outside an articulation, OmniPhysics deformable schemas.

### Changed

- Newton check: two comparisons, reported in its summary and not failed on. A USB-C sample
  held flat at one end drops 7.9 times more under XPBD than beam theory says; a napkin's
  drape coefficient with Newton's VBD solver is 0.61 times MuJoCo's. Engine matrix: Filaire
  and Maillage *differ* in Newton (a new status), with the numbers.
- Newton check (PRV-30): every file is opened from its Newton layer, `<file>_newton.usda`,
  which the four generators now write (contract section 9, a new engine layer), with Newton's
  own schema resolver; the script sets no contact gap of its own. Filaire's cables (hung from
  one end, they bend), Maillage's cloth (raised 5 cm, at rest) and Quincaillerie's battery
  holders are now checked too: 98 of 98 pass. Engine matrix: Newton *tested* for all four.
- Contract section 9: the `*_newton` layer, `Newton*` and `newton:` as engine data, and
  `generate --engines` to choose the layers. No new contract version: a new engine layer is
  an addition.
- Site: the Quincaillerie page no longer shows the plate under its header; it repeated the
  fasteners image that opens the README just after it.

## [0.4.0b1] - 2026-11-20 (beta)

Requires the generators' new releases: Granulaire 0.5.0b1, Maillage 0.4.0b1,
Filaire 0.5.0b1 and Quincaillerie 0.4.0b1.

### Breaking changes

- Minimum generator versions raised to `granulaire>=0.5.0b1`,
  `maillage>=0.4.0b1`, `filaire>=0.5.0b1` and `quincaillerie>=0.4.0b1`: each
  has breaking changes of its own, listed first in its changelog.

### Added

- Website indexing of images and video (PRV-41): `sitemap.xml` lists each page's
  images (Google's image extension) and the home page's demo video (video
  extension: thumbnail, title, description, file, duration, publication date);
  the home page carries a schema.org `VideoObject` with the same facts, its
  duration read from the MP4 file and its upload date from the file's last
  commit; the picture at the top of each generator page has alt text (it had
  none). Tests check all three.
- `primvaria compose OUT INPUT...` (PRV-14): one command builds a scene from
  the generators' outputs on the shared ground and physics scene, each asset
  referenced from its own file with a relative path, in a scope per
  generator; names made unique (instance labels follow); engine layers left
  out; the scene checked against the contract. `tests/test_composition.py`
  now runs on the stage this command writes.
- `tests/test_composition.py` (PRV-40): assets of the four generators, each
  referenced alone from the file its generator wrote, in one stage on the
  shared ground. It found that a Granulaire grain, a Maillage piece and a
  Filaire cable lost their materials when referenced alone (they lay in the
  file's `/World/Looks`): contract section 4 now says an asset is whole on
  its own, the generators' shared check enforces it, and the three
  generators moved their materials inside their assets.
  It also found Quincaillerie's screws and cells 1.6 to 17 mm below z = 0,
  against section 3; that generator now puts every part's underside at z = 0.
- Every rule of the contract is now checked by a test (PRV-35, exit
  criterion 4 of `docs/stability.md`). Sections 7 and 8, the last two, by
  the generators' shared conformance check and by a new
  `tests/test_mate_frames.py` in Filaire and Quincaillerie. Section 7 now
  says that its table is the list of variant sets per generator, and what
  identifies an asset across its variants; section 8, where the mating plane
  is and how deep the part that goes in reaches past it. Quincaillerie's
  drive, terminal and seat frames moved to follow it (a breaking change of
  that generator).
- `scripts/check_consistency.py` (in CI, on the generators' main branches) and
  `tests/test_consistency.py`: the four generators must have the same
  documentation pages, README documentation table, example scripts and
  changelog section, the same subcommands and `generate` options
  (`--seed`, `--out`, `--no-vary`, `--nominal`, `--count`, `--preset`), exit
  with 2 on an error, and write packs whose tables start with the same
  columns and whose manifests have the same keys. A difference fails unless
  it is listed as intended, with its reason (PRV-35).
- `docs/stability.md`, a page of the website: what the suite promises in beta,
  what 1.0 will promise, and the exit criteria for 1.0 (PRV-31).
- `docs/trials/newton-cpu.md` and `scripts/newton_trial.py`: a trial of Newton 1.8.0 on CPU as a
  second engine, one preset per generator (PRV-30). A report, not a check.

### Changed

- Website: each generator's picture on the home page links to its page, as its title
  does; hovering the picture highlights the title.
- The sitemap dates each page by the last commit of the file its content
  comes from, instead of the day of the build, which told search engines
  that every page changed on every deploy. A page whose history cannot be
  read gets no date. The website workflow clones the four generators with
  their history and builds from them.
- The consistency guard requires `docs/sources.md` in every generator, linked
  from its README's documentation table, now that the four have it (PRV-33).
- The stability page marks exit criteria 2 (distributions) and 3 (the
  generators agree) as met.
- The drift guard checks `tests/test_golden.py`, the reproducibility test the
  four generators share (PRV-32); the contract's section 11 and the stability
  page say so.
- The contract is version 1, candidate: every version 0 rule is in force and
  frozen; files keep writing `primvaria:contract = "0"` until 1.0. Section 12
  now says what is and is not a breaking change, how a name is deprecated,
  and how changed values are declared. Section 11 lists the two rules no
  shared test checks yet (PRV-31).

### Fixed

- `scripts/check_consistency.py` authenticates its GitHub API calls with the
  CI's token: anonymous calls hit the rate limit shared by the runners and
  failed the job on main.

## [0.3.0b1] - 2026-11-13 (beta)

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

- Requires the releases of 13 November: Granulaire 0.4.0b1, Maillage 0.3.0b1,
  Filaire 0.4.0b1 and Quincaillerie 0.3.0b1 (engine layers, semantic labels,
  thread fit classes, example scripts).
- README and website home: the summary of the contract names the semantic
  labels, the engine layers and the pack files.
- `docs/contract.md`, section 5: every asset carries OpenUSD semantic labels
  (`semantics:labels:class`, `semantics:labels:instance`); `instances.csv`
  gains a `classes` column and `manifest.json` lists the classes of the pack.
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
