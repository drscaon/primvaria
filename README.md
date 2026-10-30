<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/drscaon/primvaria/main/docs/images/logo-dark.svg">
    <img alt="Primvaria" src="https://raw.githubusercontent.com/drscaon/primvaria/main/docs/images/logo.svg" width="420">
  </picture>
</h1>

<p align="center"><strong>Physics-ready variability for Physical AI, in OpenUSD.</strong></p>

<p align="center">
  <a href="https://github.com/drscaon/primvaria/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/drscaon/primvaria/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://pypi.org/project/primvaria/"><img alt="PyPI" src="https://img.shields.io/pypi/v/primvaria"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green">
  <a href="https://primvaria.com"><img alt="Website" src="https://img.shields.io/badge/web-primvaria.com-0f6e74"></a>
</p>

Primvaria is a suite of procedural asset generators for the objects robots
struggle with most: grains, cloth, cables and small mechanical parts. Every
generator follows the same approach: **distributions instead of one shape**
(no two generated instances are the same, and what was drawn is written down
as ground truth), **measured outputs** (mass, shape, stiffness are measured on
what was generated, not trusted from the inputs) and **honest limits** (each
asset is checked in real engines, and what was not tested is said).

Every output is **OpenUSD** with standard `UsdPhysics` schemas, plus PhysX
attributes for **NVIDIA Omniverse and Isaac Sim**: one file format for
Blender, usdview, Omniverse and the other OpenUSD-aware tools, read back into
MuJoCo for the checks. Each generator's README says in which engines its
assets have been tested so far. Everything can run on CPU.

The name comes from *primvar*, OpenUSD's primitive variable, and *varia*,
Latin for "diverse things".

## The generators

| | Generator | Assets | Physics |
|---|---|---|---|
| ![Granulaire](https://raw.githubusercontent.com/drscaon/granulaire/main/docs/images/moisture_gallery.png) | [**Granulaire**](https://github.com/drscaon/granulaire) | sand, gravel, pebbles, seeds, fruit, pellets, packing peanuts; measured shapes, masses and moisture | rigid bodies, pile test in Blender and MuJoCo; deformables for OmniPhysics |
| ![Maillage](https://raw.githubusercontent.com/drscaon/maillage/main/docs/images/blender_drape.jpg) | [**Maillage**](https://github.com/drscaon/maillage) | towels, napkins, tablecloths, sheets, scarves, flags; real sizes, fabrics and masses | cloth meshes with engine-neutral stiffness; drape test in Blender and MuJoCo; OmniPhysics surface deformables |
| ![Filaire](https://raw.githubusercontent.com/drscaon/filaire/main/docs/images/hero.jpg) | [**Filaire**](https://github.com/drscaon/filaire) | standard cables with male and female connectors and the receptacles they plug into | rigid-segment chains with joints; drop, sag and insertion tests in MuJoCo, drop in Blender |
| ![Quincaillerie](https://raw.githubusercontent.com/drscaon/quincaillerie/main/docs/images/fasteners.jpg) | [**Quincaillerie**](https://github.com/drscaon/quincaillerie) | metric screws, nuts and washers with modelled threads; battery cells and their holders | rigid bodies, springs and clips; drop, screwing and insertion tests in MuJoCo and Blender |

Each generator is its own package, released on its own schedule. Primvaria
installs them together and gives them one command line.

## Engine matrix

Where each generator stands in each engine (also on
[primvaria.com](https://primvaria.com/#engines)). Tests run in each project's
CI on every preset, from the OpenUSD file alone.

| | OpenUSD validators | Blender | MuJoCo | Isaac Sim · PhysX | OmniPhysics deformables |
|---|---|---|---|---|---|
| Granulaire | tested | tested: pile | tested: pile | not yet | exported, not run |
| Maillage | tested | tested: drape | tested: flex drape | n/a (cloth) | exported, structure checked, not run |
| Filaire | tested | tested: drop (add-on) | tested: drop, sag, coil, insertion | not yet | n/a |
| Quincaillerie | tested | tested: drop, assemblies (add-on) | tested: drop, screwing, jam, insertion | not yet | n/a |

Isaac Sim runs need an NVIDIA RTX GPU and have not been done yet: the files
follow the standard `UsdPhysics` schemas and carry PhysX attributes.

## Installation

```bash
pip install primvaria             # the four generators
pip install "primvaria[all]"      # + renders, MuJoCo checks, MaterialX
```

| Extra | Adds |
|---|---|
| `render` | previews and renders (matplotlib, Pillow) |
| `sim` | the MuJoCo checks of Filaire and Quincaillerie |
| `materialx` | MaterialX materials of Quincaillerie |
| `all` | all of the above |

Blender as a Python module is installed with `pip install "maillage[blender]"`
(Python 3.13 only, as the `bpy` wheels exist for one Python version). Only one
generator? Install it alone: `pip install granulaire`.

## Usage

```bash
primvaria list                                   # generators and installed versions
primvaria granulaire generate --preset beach_sand
primvaria maillage generate --preset tea_towel
primvaria filaire generate --preset usb_c --length 2
primvaria quincaillerie generate screw M10 --with nut,washer --count 10
```

`primvaria <generator> ...` runs that generator's own command line: it is the
same as typing `granulaire ...`, `maillage ...`, which keep working. From
Python, import the generators directly:

```python
from granulaire import generate_scene, write_outputs

write_outputs(generate_scene("beach_sand"), "output")
```

## Logo

`docs/images/`: the logo (`logo.svg`, `logo-dark.svg`), the mark alone
(`mark.svg`, `mark-dark.svg`, `mark.png`) and the social preview
(`social_preview.png`, 1280 × 640, to upload in Settings > General > Social
preview, also the website's link preview; `social_preview@2x.png`).
The mark is nine primitives, no two alike, the centre one in teal: the suite's
promise in one image. The wordmark is Familjen Grotesk Bold (SIL Open Font
License), drawn as outlines. Regenerate the logo and the website's favicon
with `python scripts/make_logo.py`, and the social preview, built from the four
generators' renders, with `python scripts/make_social_preview.py`.

## Website

[primvaria.com](https://primvaria.com) is built from `site/` by the `pages.yml`
workflow (GitHub Pages) on every change to `site/` and weekly, to pick up new
hero images from the four repositories. Preview it locally with
`python site/build.py --local ..` (sibling clones of the four repositories),
then `python -m http.server -d _site`.

## Development

The project follows **GitHub Flow**, like the four generators: `main` is
protected, every change goes through a pull request from a short-lived branch
(`feat/<name>`, `fix/<name>`, …), and CI must be green before merging.
Enable the pre-push hook once per clone with
`git config core.hooksPath .githooks`.

Releasing: on a `chore/release-X.Y.Z` branch, bump `version` in
`pyproject.toml` and move the `Unreleased` entries of `CHANGELOG.md` under
the new version; merge, then tag `vX.Y.Z` on `main`. The release workflow
tests, builds, creates the GitHub release and publishes the package on PyPI
through Trusted Publishing.

## License

[MIT](https://github.com/drscaon/primvaria/blob/main/LICENSE) © 2026 Daniel Régis Sarmento Caon
