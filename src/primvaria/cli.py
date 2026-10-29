"""Command line of the suite.

``primvaria list`` shows the generators and their installed versions;
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
  <generator> [args]   run a generator's command line ({", ".join(m.name for m in MEMBERS)})

examples:
  primvaria list
  primvaria granulaire generate --preset beach_sand
  primvaria filaire --help
"""


def _list() -> int:
    width = max(len(m.name) for m in MEMBERS)
    for m in MEMBERS:
        installed = m.installed_version or "not installed"
        print(f"{m.name:<{width}}  {installed:<14}  {m.summary}")
    return 0


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
