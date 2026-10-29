# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project uses [Semantic Versioning](https://semver.org/) with PEP 440
pre-release versions.

## [Unreleased]

### Added

- Website, [primvaria.com](https://primvaria.com): the four generators and the
  engine matrix, built from `site/` and deployed to GitHub Pages by the
  `pages.yml` workflow.
- README: engine matrix, PyPI and website badges.
- Logo: the mark (nine primitives, no two alike) and the wordmark, light and
  dark, the website's favicon and the GitHub social preview, drawn by
  `scripts/make_logo.py`.

### Changed

- The project's homepage on PyPI is primvaria.com.

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
