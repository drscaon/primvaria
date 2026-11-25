"""Command line of the Primvaria contract check, shared by the four generators::

    python -m <generator>.conformance output/<preset>     # files or folders; exit 1 on any issue
    python -m primvaria_contract.conformance FILES...      # files of any generator of the suite

A folder is also searched for packs (a ``manifest.json``): their ``instances.csv`` must say
what their OpenUSD files say.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .contract import CONTRACT, check, usd_files
from .pack import MANIFEST, check_pack


def main(argv: list[str] | None = None, generator: str | None = None, version: str | None = None) -> int:
    """generator, version: the files were written by this generator (``<generator>.conformance``),
    so their assets must name it and this version; None: any generator of the suite."""
    paths = sys.argv[1:] if argv is None else argv
    if not paths:
        print(f"usage: python -m {generator or __package__}.conformance FILE_OR_FOLDER...", file=sys.stderr)
        return 2
    files, failed = usd_files(paths), 0
    for f in files:
        issues = check(f, generator, version)
        failed += bool(issues)
        for msg in issues:
            print(f"{f}: {msg}")
    packs = sorted({m.parent for p in map(Path, paths) if p.is_dir() for m in p.rglob(MANIFEST)})
    for folder in packs:
        issues = check_pack(folder)
        failed += bool(issues)
        for msg in issues:
            print(f"{folder}: {msg}")
    checked = f"{len(files)} OpenUSD files and {len(packs)} packs"
    print(f"{checked} checked against contract {CONTRACT}, {failed} with issues")
    return 1 if failed or not files else 0


if __name__ == "__main__":
    raise SystemExit(main())
