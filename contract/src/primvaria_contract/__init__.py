"""The Primvaria OpenUSD contract, shared by the four generators of the suite.

Granulaire, Maillage, Filaire and Quincaillerie write their OpenUSD files to the same contract
(https://github.com/drscaon/primvaria/blob/main/docs/contract.md). This package holds the code
they share for it, which each generator binds to its own name and version:

* ``primvaria_contract.contract``: identity, variation, measurements, semantic labels and
  the checks of the contract (``conformance``, ``check``), engine layers;
* ``primvaria_contract.pack``: the pack of a generator (``instances.csv``, ``manifest.json``);
* ``primvaria_contract.ground``: the shared ground and physics scene;
* ``primvaria_contract.conformance``: the command line of the check.

Use it through a generator (``granulaire.contract``, ``granulaire.pack`` ...), which fills in
the generator's name and version, or directly to check files of any generator::

    python -m primvaria_contract.conformance output/
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("primvaria-contract")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0+unknown"
