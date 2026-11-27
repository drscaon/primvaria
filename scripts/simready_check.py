"""How the suite's files fare against NVIDIA's SimReady profile for props, on CPU.

SimReady Foundation (https://nvidia.github.io/simready-foundation/) is a set of profiles that
say what a simulation-ready OpenUSD asset holds. Its validator runs without Omniverse, Kit or
a GPU (``pip install simready-validate simready-foundation-tier-core``). This runs it on every
main file under the given folders (engine layers and material libraries left out, since the
validator opens a file with all it composes) and writes a report: which requirements each
generator meets and which it does not, with the validator's own reason.

The report is information, not a gate: the suite's packs are scenes (/World with a ground and
many assets) with their engine layers beside them, where the profile describes one prop per
folder with its runtimes as variant sets. What does not pass, and why, is in docs/simready.md::

    python scripts/simready_check.py packs                    # report on packs/
    python scripts/simready_check.py packs --validator .simready/bin/simready-validate
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from pxr import Usd

PROFILE = "Robotics-Prop"
VERSION = "5.0.0"
ENGINE_LAYERS = ("_physx", "_omniphysics", "_newton")


def main_files(folders: list[Path]) -> list[Path]:
    """Every OpenUSD file under the folders but engine layers and material libraries."""
    found = []
    for folder in folders:
        for f in sorted(folder.rglob("*.usd[ac]")):
            if f.stem.endswith(ENGINE_LAYERS) or "materials" in f.parts:
                continue
            found.append(f)
    return found


def generator_of(path: Path) -> str:
    """The generator that wrote a file, from its assets (primvaria:generator), or '?'."""
    stage = Usd.Stage.Open(str(path))
    for prim in stage.Traverse():
        attr = prim.GetAttribute("primvaria:generator")
        if attr and attr.Get():
            return str(attr.Get())
    return "?"


def validate(path: Path, validator: str, profile: str, version: str) -> dict:
    """The validator's features summary for one file: {feature: {...}}; {} when it gave none."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "result.json"
        cmd = [validator, "--profile", profile, "--version", version, str(path), "--output", str(out)]
        subprocess.run(cmd, capture_output=True, text=True)  # exit 1 when the profile is not met
        if not out.exists():
            return {}
        data = json.loads(out.read_text(encoding="utf-8"))
    entry = next(iter(data.values()), {}) if data else {}
    return entry.get("features_summary", {})


def blocking(summary: dict) -> dict[str, str]:
    """{requirement id: first message} of the requirements that make the profile fail."""
    found = {}
    for feature in summary.values():
        if not feature.get("blocking_failure"):
            continue
        ids = ast.literal_eval(feature.get("failing requirements", "[]") or "[]")
        messages = json.loads(feature.get("requirement_messages", "{}") or "{}")
        for rid in ids:
            text = (messages.get(rid) or [""])[0]
            found.setdefault(rid, text.split(". ")[0][:160])
    return found


def report(results: dict[str, list[tuple[Path, dict[str, str]]]], profile: str, version: str) -> str:
    lines = [f"# SimReady {profile} {version}", ""]
    lines += ["Not met is expected for now: see docs/simready.md in primvaria. One row per requirement", ""]
    for gen in sorted(results):
        files = results[gen]
        passed = sum(1 for _, b in files if not b)
        lines += [f"## {gen}: {passed} of {len(files)} files meet the profile", ""]
        count, text = defaultdict(int), {}
        for _, found in files:
            for rid, msg in found.items():
                count[rid] += 1
                text.setdefault(rid, msg)
        if count:
            lines += ["| Requirement | Files | Reason (the validator's words) |", "|---|---|---|"]
            for rid in sorted(count):
                lines.append(f"| `{rid}` | {count[rid]} | {text[rid].replace('|', '/')} |")
            lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--validator", default="simready-validate", help="the simready-validate command")
    parser.add_argument("--profile", default=PROFILE)
    parser.add_argument("--version", default=VERSION)
    parser.add_argument("--report", type=Path, help="markdown report (default: <first folder>/simready.md)")
    args = parser.parse_args(argv)
    results: dict[str, list] = defaultdict(list)
    for f in main_files(args.folders):
        summary = validate(f, args.validator, args.profile, args.version)
        if not summary:
            print(f"{f}: no result from the validator", file=sys.stderr)
            continue
        results[generator_of(f)].append((f, blocking(summary)))
    text = report(results, args.profile, args.version)
    target = args.report or args.folders[0] / "simready.md"
    target.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
