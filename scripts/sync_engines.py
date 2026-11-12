"""Keep the engine matrix and the generators' counts the same everywhere.

docs/engines.json is the one place the engine matrix is written. This renders it into
README.md and site/index.html, and fills each generator's facts line on the site (number of
presets, fabrics, connector families, catalogue assets) from the installed packages::

    python scripts/sync_engines.py           # rewrite README.md and site/index.html
    python scripts/sync_engines.py --check   # exit 1 if either is out of date (CI)
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "docs" / "engines.json"
README = ROOT / "README.md"
PAGE = ROOT / "site" / "index.html"
CSS = {"tested": "ok", "not yet": "warn", "exported": "warn", "n/a": "na"}
START, END = "<!-- engines:start -->", "<!-- engines:end -->"


def counts() -> dict[str, dict[str, int]]:
    """What each installed generator offers, for the facts lines."""
    import filaire
    import filaire.connectors
    import granulaire.presets
    import maillage.fabrics
    import maillage.presets
    from quincaillerie.generator import catalog_parts

    return {
        "granulaire": {"presets": len(granulaire.presets.PRESETS)},
        "maillage": {"presets": len(maillage.presets.PRESETS), "fabrics": len(maillage.fabrics.FABRICS)},
        "filaire": {"presets": len(filaire.PRESETS), "connectors": len(filaire.connectors.CONNECTORS)},
        "quincaillerie": {"assets": len(catalog_parts())},
    }


def readme_table(data: dict) -> str:
    engines = data["engines"]
    lines = [
        "| | " + " | ".join(e["title"] for e in engines) + " |",
        "|---|" + "---|" * len(engines),
    ]
    for name, cells in data["generators"].items():
        lines.append(
            f"| {name.capitalize()} | " + " | ".join(cells[e["key"]]["readme"] for e in engines) + " |"
        )
    return "\n".join(lines)


def page_rows(data: dict) -> str:
    rows = []
    for name, cells in data["generators"].items():
        tds = []
        for e in data["engines"]:
            cell = cells[e["key"]]
            note = f"<small>{html.escape(cell['site'])}</small>" if cell["site"] else ""
            tds.append(
                f'        <td><span class="st {CSS[cell["status"]]}">{cell["status"]}</span>{note}</td>'
            )
        rows.append(f'      <tr><th scope="row">{name.capitalize()}</th>\n' + "\n".join(tds) + "</tr>")
    return "\n".join(rows)


def between(text: str, new: str, where: str) -> str:
    """Replace what stands between the two markers."""
    if text.count(START) != 1 or text.count(END) != 1:
        raise SystemExit(f"{where}: expected one {START} and one {END}")
    head, rest = text.split(START)
    return head + START + "\n" + new + "\n" + rest[rest.index(END) - _indent(rest) :]


def _indent(rest: str) -> int:
    """Width of the whitespace that stands before the end marker on its line."""
    before = rest[: rest.index(END)]
    return len(before) - len(before.rstrip(" "))


def render(data: dict, numbers: dict) -> dict[Path, str]:
    readme = between(README.read_text(encoding="utf-8"), readme_table(data), "README.md")
    page = between(PAGE.read_text(encoding="utf-8"), page_rows(data), "site/index.html")
    page, n = re.subn(
        r"(Where each generator stands in each engine, on )[^.]*\.", rf"\g<1>{data['updated']}.", page
    )
    if n != 1:
        raise SystemExit("site/index.html: no 'Where each generator stands in each engine, on …' sentence")
    for name, cells in data["generators"].items():
        facts = html.escape(cells["facts"].format(**numbers[name]))
        pattern = rf'(<h3>{name.capitalize()}</h3>.*?<span class="num">)[^<]*(</span>)'
        page, n = re.subn(pattern, rf"\g<1>{facts}\g<2>", page, count=1, flags=re.S)
        if n != 1:
            raise SystemExit(f"site/index.html: no facts line for {name}")
    return {README: readme, PAGE: page}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="change nothing; exit 1 if a file is out of date"
    )
    args = parser.parse_args(argv)
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    stale = []
    for path, text in render(data, counts()).items():
        if path.read_text(encoding="utf-8") != text:
            stale.append(path.relative_to(ROOT).as_posix())
            if not args.check:
                path.write_text(text, encoding="utf-8")
    if stale:
        verb = "out of date (run python scripts/sync_engines.py)" if args.check else "updated"
        print(f"{', '.join(stale)}: {verb}")
        return 1 if args.check else 0
    print("README.md and site/index.html agree with docs/engines.json and the installed generators")
    return 0


if __name__ == "__main__":
    sys.exit(main())
