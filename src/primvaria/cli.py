"""Command line of the suite.

``primvaria list`` shows the generators and their installed versions;
``primvaria compose`` writes one stage that references assets from the generators' outputs;
``primvaria <generator> ...`` runs that generator's own command line, so
``primvaria granulaire generate --preset beach_sand`` is the same as
``granulaire generate --preset beach_sand``.
"""

from __future__ import annotations

import sys

from . import __version__
from .suite import MEMBERS, get_member

USAGE = f"""\
usage: primvaria [--version] <command> [args...]

Physics-ready variability for Physical AI, in OpenUSD.

commands:
  list                 the generators of the suite and their installed versions
  compose OUT INPUT... one stage with the assets of generator outputs (folders or files)
                       on the shared ground (primvaria compose --help)
  <generator> [args]   run a generator's command line ({", ".join(m.name for m in MEMBERS)})

examples:
  primvaria list
  primvaria compose scene.usda output/crushed_gravel output/tea_towel output/usb_c
  primvaria granulaire generate --preset beach_sand
  primvaria filaire --help
"""


def _list() -> int:
    width = max(len(m.name) for m in MEMBERS)
    for m in MEMBERS:
        installed = m.installed_version or "not installed"
        print(f"{m.name:<{width}}  {installed:<14}  {m.summary}")
    return 0


def _compose(args: list[str]) -> int:
    import argparse

    from primvaria_contract.contract import engine_list

    from .compose import ENGINES, check, compose, layer_path

    ap = argparse.ArgumentParser(
        prog="primvaria compose",
        description="Write one OpenUSD stage that references the assets of generator outputs, side by "
        "side on the shared ground, and check it against the contract.",
    )
    ap.add_argument("out", help="the stage to write (.usda, .usdc or .usd)")
    ap.add_argument("inputs", nargs="+", help="generator output folders or OpenUSD files")
    ap.add_argument("--limit", type=int, help="at most this many assets from each file")
    ap.add_argument("--gap", type=float, default=0.05, help="space between assets, m (default: 0.05)")
    ap.add_argument("--width", type=float, default=2.0, help="width of a row of assets, m (default: 2)")
    ap.add_argument(
        "--engines",
        default=",".join(ENGINES),
        metavar="LIST",
        help="engine layers written beside the stage, from the assets' own, comma-separated, or none "
        f"(default: {','.join(ENGINES)})",
    )
    ap.add_argument("--no-check", action="store_true", help="do not check the stage against the contract")
    a = ap.parse_args(args)
    try:
        engines = engine_list(a.engines)
    except ValueError as e:
        ap.error(str(e))
    if a.limit is not None and a.limit < 1:
        ap.error("--limit must be at least 1")
    try:
        stage, assets = compose(a.out, a.inputs, limit=a.limit, gap=a.gap, width=a.width, engines=engines)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    by_generator = {}
    for asset in assets:
        by_generator[asset.generator] = by_generator.get(asset.generator, 0) + 1
    counts = ", ".join(f"{n} {g}" for g, n in by_generator.items())
    print(f"{a.out}: {len(assets)} assets ({counts})")
    for engine in engines:
        if layer_path(a.out, engine).exists():
            print(f"  {layer_path(a.out, engine)}: the {engine} layer")
    if a.no_check:
        return 0
    problems = check(stage)
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    print("conforms to the contract" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help", "help"):
        print(USAGE, end="")
        return 0
    command, rest = args[0], args[1:]
    if command in ("-V", "--version"):
        print(f"primvaria {__version__}")
        return 0
    if command == "list":
        return _list()
    if command == "compose":
        return _compose(rest)
    try:
        member = get_member(command)
    except KeyError as e:
        print(f"error: {e.args[0]}", file=sys.stderr)
        return 2
    if member.installed_version is None:
        print(f"error: {member.name} is not installed (pip install {member.name})", file=sys.stderr)
        return 2
    return member.cli_main()(rest) or 0


if __name__ == "__main__":
    raise SystemExit(main())
