"""Fail when a file the four generators share has drifted between them.

The Primvaria contract (docs/contract.md) relies on a few files being byte-identical in
Granulaire, Maillage, Filaire and Quincaillerie. This compares them::

    python scripts/check_shared_files.py              # the main branches on GitHub
    python scripts/check_shared_files.py --local ..   # sibling clones of the four repositories
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

GENERATORS = ("granulaire", "maillage", "filaire", "quincaillerie")
# paths in each repository; {name} is the generator's package name
SHARED = (
    "src/{name}/ground.py",
    "src/{name}/contract.py",
    "src/{name}/conformance.py",
    "src/{name}/pack.py",
    "tests/test_contract.py",
    "tests/test_pack.py",
)
RAW = "https://raw.githubusercontent.com/drscaon/{name}/{ref}/{path}"


def read(name: str, path: str, local: Path | None, ref: str) -> bytes | None:
    """Content of a generator's file, or None when it does not exist."""
    if local is not None:
        f = local / name / path
        return f.read_bytes() if f.exists() else None
    try:
        with urllib.request.urlopen(RAW.format(name=name, ref=ref, path=path), timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def drift(contents: dict[str, bytes | None]) -> list[str]:
    """Problems of one shared file, given its content in each generator (empty: identical)."""
    missing = [name for name, data in contents.items() if data is None]
    if missing:
        return [f"missing in {', '.join(missing)}"]
    # line endings aside: a checkout on Windows must not look like drift
    digests = {
        name: hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()[:12] for name, data in contents.items()
    }
    if len(set(digests.values())) > 1:
        return ["differs: " + ", ".join(f"{name} {d}" for name, d in digests.items())]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--local", type=Path, help="folder holding clones of the four repositories")
    parser.add_argument("--ref", default="main", help="branch or tag to read on GitHub (default: main)")
    args = parser.parse_args(argv)
    failed = 0
    for pattern in SHARED:
        contents = {g: read(g, pattern.format(name=g), args.local, args.ref) for g in GENERATORS}
        problems = drift(contents)
        failed += bool(problems)
        print(f"{pattern}: {'; '.join(problems) if problems else 'identical in the four generators'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
