"""The tests that the four generators of the suite run on their own files, written once.

Each generator's test file is one import, so pytest collects these tests there::

    # tests/test_contract.py
    from primvaria_contract.testing.contract import *  # noqa: F403

    # tests/test_pack.py
    from primvaria_contract.testing.pack import *  # noqa: F403

    # tests/test_golden.py
    from primvaria_contract.testing.golden import *  # noqa: F403

What they test comes from the generator, through fixtures:

- ``contract_files`` (``conftest.py``): OpenUSD files freshly written by the generator, one folder;
- ``pack_folder`` (``conftest.py``): a pack freshly written by the generator;
- the golden cases: ``tests/golden/cases.json`` beside the test file, and one reference
  ``tests/golden/<case>.json`` per case.

The generator itself is found as today: the package under ``src/`` that has a ``contract.py``
(``generator`` fixture). These modules need pytest, which is not a dependency of
primvaria-contract: a generator has it among its test dependencies.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace


def find_generator(test_file: str | Path) -> SimpleNamespace:
    """The generator whose tests are in ``test_file`` (``<repo>/tests/test_*.py``): its name and
    its modules ``package``, ``contract``, ``conformance`` and ``pack``."""
    src = Path(test_file).resolve().parents[1] / "src"
    names = sorted(p.name for p in src.iterdir() if (p / "contract.py").exists()) if src.is_dir() else []
    if len(names) != 1:
        raise LookupError(f"no single generator package with a contract.py under {src}: {names}")
    name = names[0]
    modules = {m: importlib.import_module(f"{name}.{m}") for m in ("contract", "conformance", "pack")}
    return SimpleNamespace(name=name, package=importlib.import_module(name), **modules)
