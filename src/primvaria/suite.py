"""The generators of the Primvaria suite and how to reach them."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version


@dataclass(frozen=True)
class Member:
    """One generator of the suite: a separate package with its own command line."""

    name: str
    summary: str
    repository: str

    @property
    def installed_version(self) -> str | None:
        """Installed version of the package, or None when it is not installed."""
        try:
            return version(self.name)
        except PackageNotFoundError:
            return None

    def cli_main(self) -> Callable[[list[str] | None], int]:
        """The member's command-line entry point, ``<name>.cli:main``."""
        return importlib.import_module(f"{self.name}.cli").main


MEMBERS: tuple[Member, ...] = (
    Member(
        "granulaire",
        "granular assets: sand, gravel, pebbles, seeds, pellets",
        "https://github.com/drscaon/granulaire",
    ),
    Member(
        "maillage",
        "textile assets: towels, napkins, tablecloths, sheets, flags",
        "https://github.com/drscaon/maillage",
    ),
    Member(
        "filaire",
        "cable assets: standard cables with mating connectors",
        "https://github.com/drscaon/filaire",
    ),
    Member(
        "quincaillerie",
        "hardware assets: threaded fasteners, battery cells and holders",
        "https://github.com/drscaon/quincaillerie",
    ),
)

_BY_NAME = {m.name: m for m in MEMBERS}


def get_member(name: str) -> Member:
    """Look a member up by name; raises KeyError with the known names."""
    try:
        return _BY_NAME[name]
    except KeyError:
        known = ", ".join(_BY_NAME)
        raise KeyError(f"unknown generator {name!r} (known: {known})") from None
