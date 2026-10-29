"""Primvaria: physics-ready variability for Physical AI, in OpenUSD."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("primvaria")
except PackageNotFoundError:  # running from a source tree without installing
    __version__ = "0.0.0+unknown"

from .suite import MEMBERS, Member, get_member

__all__ = ["MEMBERS", "Member", "get_member", "__version__"]
