"""Every pack has the same two files, and they say what the OpenUSD files say.

Collected in each generator by ``tests/test_pack.py``, which imports this module. The
``pack_folder`` fixture (the generator's ``conftest.py``) gives a pack freshly written by the
generator.
"""

import shutil
from pathlib import Path

import pytest
from pxr import Usd

from ._fixtures import generator  # noqa: F401 (a fixture, collected where this module is imported)


@pytest.fixture
def copy(pack_folder, tmp_path):
    """A copy of the pack that a test may damage."""
    return Path(shutil.copytree(pack_folder, tmp_path / "pack"))


def test_the_pack_agrees_with_its_files(generator, pack_folder):
    assert generator.pack.check_pack(pack_folder) == []


def test_manifest(generator, pack_folder):
    manifest = generator.pack.read_manifest(pack_folder)
    assert manifest["contract"] == generator.contract.CONTRACT
    assert manifest["generator"] == generator.name and manifest["version"] == generator.package.__version__
    assert manifest["pack"] and isinstance(manifest["seed"], int) and isinstance(manifest["aspects"], list)
    assert (
        manifest["table"] == generator.pack.TABLE
        and manifest["assets"] == len(generator.pack.read_table(pack_folder)) > 0
    )
    classes = {c for row in generator.pack.read_table(pack_folder) for c in row["classes"].split()}
    assert manifest["classes"] == sorted(classes) and classes  # the semantic classes of the pack
    assert all((pack_folder / f).exists() for f in manifest["files"])


def test_one_row_per_asset_with_the_common_columns_first(generator, pack_folder):
    table = generator.pack.read_table(pack_folder)
    assert tuple(table[0])[: len(generator.pack.FIRST)] == generator.pack.FIRST
    assert len({(r["file"], r["prim"]) for r in table}) == len(table)
    for row in table:
        stage = Usd.Stage.Open(str(pack_folder / row["file"]))
        prim = stage.GetPrimAtPath(row["prim"])
        assert prim.GetName() == row["name"]
        assert row["generator"] == generator.name and row["version"] == generator.package.__version__
        assert row["seed"] == str(prim.GetAttribute("primvaria:seed").Get())
        assert (
            row["classes"] == generator.pack.cell(generator.contract.labels(prim))
            and row["preset"] in row["classes"].split()
        )
        for key, value in generator.contract.variation(prim).items():
            assert row["aspects" if key == "aspects" else f"variation:{key}"] == generator.pack.cell(value)
        for key, value in generator.contract.measured(prim).items():
            assert row[f"measured:{key}"] == generator.pack.cell(value)


def test_assets_carry_measurements(generator, pack_folder):
    table = generator.pack.read_table(pack_folder)
    assert any(key.startswith("measured:") for key in table[0])


def test_a_table_that_disagrees_is_reported(generator, copy):
    table = generator.pack.read_table(copy)
    lines = (copy / generator.pack.TABLE).read_text(encoding="utf-8").splitlines()
    seed = list(table[0]).index("seed")
    cells = lines[1].split(",")
    cells[seed] = str(int(cells[seed]) + 1)
    changed = "\n".join([lines[0], ",".join(cells), *lines[2:]]) + "\n"
    (copy / generator.pack.TABLE).write_text(changed, encoding="utf-8")
    assert any("seed is" in p for p in generator.pack.check_pack(copy))


def test_a_missing_row_and_a_missing_file_are_reported(generator, copy):
    lines = (copy / generator.pack.TABLE).read_text(encoding="utf-8").splitlines()
    (copy / generator.pack.TABLE).write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    problems = generator.pack.check_pack(copy)
    assert any("no row for" in p for p in problems) and any("rows in" in p for p in problems)
    (copy / generator.pack.read_manifest(copy)["files"][0]).unlink()
    assert any("missing file" in p for p in generator.pack.check_pack(copy))
    (copy / generator.pack.MANIFEST).unlink()
    assert generator.pack.check_pack(copy) == [f"no {generator.pack.MANIFEST} or no {generator.pack.TABLE}"]


@pytest.mark.slow
def test_command_line_checks_packs(generator, pack_folder, copy, capsys):
    assert generator.conformance.main([str(pack_folder)]) == 0
    assert "1 packs checked" in capsys.readouterr().out
    (copy / generator.pack.TABLE).write_text("name\n", encoding="utf-8")
    assert generator.conformance.main([str(copy)]) == 1
