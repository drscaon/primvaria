# primvaria-contract

The [Primvaria](https://primvaria.com) OpenUSD contract, as code: what the four
generators of the suite ([Granulaire](https://github.com/drscaon/granulaire),
[Maillage](https://github.com/drscaon/maillage),
[Filaire](https://github.com/drscaon/filaire) and
[Quincaillerie](https://github.com/drscaon/quincaillerie)) write alike and how it is
checked. The contract itself is
[docs/contract.md](https://github.com/drscaon/primvaria/blob/main/docs/contract.md).

You rarely install it yourself: each generator depends on it and gives its modules
under its own name (`granulaire.contract`, `granulaire.pack`, `granulaire.ground`,
`python -m granulaire.conformance`), filled in with the generator's name and version.

| Module | What it holds |
|---|---|
| `primvaria_contract.contract` | asset identity, drawn and measured values, semantic labels, variant sets, MateFrames, engine layers, and the checks (`conformance`, `check`) |
| `primvaria_contract.pack` | the pack files, `instances.csv` and `manifest.json` (`write_pack`, `check_pack`) |
| `primvaria_contract.ground` | the shared ground and physics scene |
| `primvaria_contract.conformance` | the command line of the check |

Check files of any generator of the suite:

```bash
pip install primvaria-contract
python -m primvaria_contract.conformance output/
```

Writing takes the generator's name and version explicitly:

```python
from primvaria_contract import contract

contract.write_identity(
    prim,
    name="Grain_000",
    preset="beach_sand",
    seed=1,
    identifier="./file.usdc",
    generator="granulaire",
    version="0.6.0b1",
)
problems = contract.conformance(stage)  # any generator of the suite
problems = contract.conformance(stage, "granulaire", "0.6.0b1")  # and the assets name it
```

Released from the [primvaria](https://github.com/drscaon/primvaria) repository
(folder `contract/`, tags `contract-vX.Y.Z`), before the generators that need its new
version. MIT licence.
