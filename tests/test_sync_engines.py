"""The engine matrix has one source, docs/engines.json; the README and the site follow it."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("sync_engines", ROOT / "scripts" / "sync_engines.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)
DATA = json.loads(sync.SOURCE.read_text(encoding="utf-8"))


def test_readme_and_site_are_up_to_date(capsys):
    assert sync.main(["--check"]) == 0, capsys.readouterr().out


def test_every_generator_has_every_engine():
    keys = [e["key"] for e in DATA["engines"]]
    assert list(DATA["generators"]) == ["granulaire", "maillage", "filaire", "quincaillerie"]
    for cells in DATA["generators"].values():
        assert all(cells[k]["status"] in sync.CSS and cells[k]["readme"] for k in keys)


def test_counts_come_from_the_installed_generators():
    numbers = sync.counts()
    page = sync.render(DATA, numbers)[sync.HOME]
    for name, cells in DATA["generators"].items():
        assert all(n > 0 for n in numbers[name].values())
        assert cells["facts"].format(**numbers[name]) in page


def test_a_stale_table_is_rewritten():
    stale = sync.README.read_text(encoding="utf-8").replace("tested: pile", "tested: heap")
    assert (
        sync.between(stale, sync.readme_table(DATA), "README.md")
        == sync.render(DATA, sync.counts())[sync.README]
    )
