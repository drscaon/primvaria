"""Fail when the four generators stop looking like one suite (PRV-35).

What a user meets the same way in Granulaire, Maillage, Filaire and Quincaillerie, checked on
their repositories: the documentation pages, the README's documentation table, the example
scripts and the changelog. Their command lines and pack files are checked by
tests/test_consistency.py, with the generators installed. A difference fails unless INTENDED
below says why it is there::

    python scripts/check_consistency.py              # the main branches on GitHub
    python scripts/check_consistency.py --local ..   # sibling clones of the four repositories
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

GENERATORS = ("granulaire", "maillage", "filaire", "quincaillerie")
# every generator has these pages, and links each from its README's documentation table
PAGES = ("usage", "openusd", "physics", "variation", "limits", "development")
# example scripts every generator has, by the start of their name
EXAMPLES = ("01_first_pack", "02_one_aspect_at_a_time", "03_read_the_usd_file", "04_")
# differences that are meant: (generator, what) -> why
INTENDED = {
    ("filaire", "docs/connectors.md"): "the connector families, a table only Filaire has",
    ("quincaillerie", "docs/jam-rate.md"): "the defect rate to jam rate experiment (QUI-05)",
    # PRV-33, one generator at a time: once the four have it, sources joins PAGES and this goes
    ("quincaillerie", "docs/sources.md"): "the sources of the physical values: the first generator with them",
    ("filaire", "docs/sources.md"): "the sources of the physical values: the second generator with them",
    ("maillage", "docs/sources.md"): "the sources of the physical values: the third generator with them",
}
RAW = "https://raw.githubusercontent.com/drscaon/{name}/{ref}/{path}"
TREE = "https://api.github.com/repos/drscaon/{name}/git/trees/{ref}?recursive=1"


class Repo:
    """A generator's files, from a local clone or from GitHub."""

    def __init__(self, name: str, local: Path | None, ref: str):
        self.name, self.local, self.ref = name, local, ref
        if local is not None:
            root = local / name
            self.paths = {p.relative_to(root).as_posix() for p in root.rglob("*") if ".git" not in p.parts}
        else:
            # authenticated when a token is given (CI): GitHub limits anonymous API calls per address
            request = urllib.request.Request(TREE.format(name=name, ref=ref))
            if os.environ.get("GITHUB_TOKEN"):
                # not sent on along a redirect: urllib forwards ordinary headers to any host
                request.add_unredirected_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
            with urllib.request.urlopen(request, timeout=30) as r:
                self.paths = {e["path"] for e in json.load(r)["tree"] if e["type"] == "blob"}

    def text(self, path: str) -> str | None:
        if path not in self.paths:
            return None
        if self.local is not None:
            return (self.local / self.name / path).read_text(encoding="utf-8")
        try:
            with urllib.request.urlopen(RAW.format(name=self.name, ref=self.ref, path=path), timeout=30) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError:
            return None


def problems(repo: Repo) -> list[str]:
    found = []
    pages = {p for p in repo.paths if re.fullmatch(r"docs/[^/]+\.md", p)}
    for page in PAGES:
        if f"docs/{page}.md" not in pages:
            found.append(f"docs/{page}.md is missing")
    for extra in sorted(pages - {f"docs/{p}.md" for p in PAGES}):
        if (repo.name, extra) not in INTENDED:
            found.append(
                f"{extra} is a page the other generators do not have (add it to INTENDED, or rename it)"
            )
    readme = repo.text("README.md") or ""
    table = (
        readme.split("## Documentation", 1)[1].split("\n## ", 1)[0] if "## Documentation" in readme else ""
    )
    if not table:
        found.append("README.md has no Documentation section")
    for page in sorted(pages):
        if page.split("/", 1)[1] not in table:
            found.append(f"README.md's Documentation table does not link {page}")
    examples = sorted(p.split("/", 1)[1] for p in repo.paths if re.fullmatch(r"examples/[^/]+\.py", p))
    for start in EXAMPLES:
        if not any(e.startswith(start) for e in examples):
            found.append(f"no example named {start}*.py")
    changelog = repo.text("CHANGELOG.md") or ""
    if "## [Unreleased]" not in changelog:
        found.append("CHANGELOG.md has no [Unreleased] section")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--local", type=Path, help="folder holding clones of the four repositories")
    parser.add_argument("--ref", default="main", help="branch or tag to read on GitHub (default: main)")
    args = parser.parse_args(argv)
    failed = 0
    for name in GENERATORS:
        found = problems(Repo(name, args.local, args.ref))
        failed += bool(found)
        print(f"{name}: " + ("; ".join(found) if found else "consistent with the suite"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
