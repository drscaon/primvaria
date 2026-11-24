"""`primvaria compose` (PRV-14): what it finds in the generators' outputs, how it names and places
the assets, and its command line. That the stage it writes conforms, validates and settles in MuJoCo
is tests/test_composition.py."""

import shutil
from pathlib import Path

import pytest
from pxr import Usd, UsdSemantics

granulaire = pytest.importorskip("granulaire")
filaire = pytest.importorskip("filaire")
quincaillerie = pytest.importorskip("quincaillerie")

from granulaire import contract  # noqa: E402

from primvaria.cli import main  # noqa: E402
from primvaria.compose import check, compose, find_assets, layout  # noqa: E402


@pytest.fixture(scope="module")
def outputs(tmp_path_factory):
    """Two Granulaire packs (their grains are named alike), a Filaire pack and a Quincaillerie
    output folder (its scene.usda references the files of its assets/ folder)."""
    out = tmp_path_factory.mktemp("outputs")
    gravel = granulaire.write_outputs(granulaire.generate_scene("crushed_gravel", shapes=2, copies=1), out)
    pebbles = granulaire.write_outputs(granulaire.generate_scene("beach_pebbles", shapes=2, copies=1), out)
    cables = filaire.write_outputs(filaire.generate_scene("usb_c", count=2, seed=1), out)
    parts = quincaillerie.generate(
        quincaillerie.resolve("screw", "M6", 12, ["nut"]), str(out / "q"), "q", count=2, seed=1, detail="low"
    )
    return {"gravel": gravel, "pebbles": pebbles, "cables": cables, "parts": Path(parts.out_dir)}


def test_a_folder_gives_each_asset_once_and_no_engine_layer(outputs):
    assets = find_assets([outputs["parts"]])
    names = [a.name for a in assets]
    assert sorted(names) == sorted(set(names))  # not again through scene.usda
    assert len(assets) == 4  # two screws, two nuts
    assert all(a.file.parent.name == "assets" for a in assets)
    assert not any(contract.is_engine_layer(a.file) for a in find_assets([outputs["cables"]]))


def test_assets_named_alike_take_their_preset_and_their_label_follows(outputs, tmp_path):
    stage, assets = compose(tmp_path / "s.usda", [outputs["gravel"], outputs["pebbles"]])
    names = [a.name for a in assets]
    assert len(names) == len(set(names))
    assert {"crushed_gravel_g_0000", "beach_pebbles_g_0000"} <= set(names)
    query = UsdSemantics.LabelsQuery("instance", Usd.TimeCode.Default())
    for root in contract.asset_roots(stage):
        assert list(query.ComputeUniqueDirectLabels(root)) == [root.GetName()]
    assert check(stage) == []


def test_assets_stand_apart_in_rows(outputs):
    assets = find_assets([outputs["gravel"], outputs["cables"], outputs["parts"]])
    offsets = layout(assets, gap=0.05, width=0.5)
    boxes = [
        (a.lo[0] + dx, a.lo[1] + dy, a.hi[0] + dx, a.hi[1] + dy)
        for a, (dx, dy) in zip(assets, offsets, strict=True)
    ]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            apart = a[2] + 0.05 <= b[0] + 1e-9 or b[2] + 0.05 <= a[0] + 1e-9
            apart = apart or a[3] + 0.05 <= b[1] + 1e-9 or b[3] + 0.05 <= a[1] + 1e-9
            assert apart, (a, b)
    assert len({round(y, 6) for _, y, _, _ in boxes}) > 1  # 0.5 m is too narrow for one row


def test_each_asset_keeps_its_height(outputs, tmp_path):
    """Placing slides an asset along x and y only: it rests where its file has it (contract, section 3)."""
    stage, _ = compose(tmp_path / "s.usda", [outputs["parts"]])
    for root in contract.asset_roots(stage):
        place = root.GetParent()
        assert place.GetAttribute("xformOp:translate").Get()[2] == 0.0


def test_the_stage_refers_to_its_files_relatively(outputs, tmp_path):
    """A composed stage moved with the outputs it references still opens whole."""
    shutil.copytree(outputs["cables"], tmp_path / "cables")
    compose(tmp_path / "scenes" / "s.usda", [tmp_path / "cables"])
    shutil.move(tmp_path, tmp_path.parent / (tmp_path.name + "_moved"))
    moved = tmp_path.parent / (tmp_path.name + "_moved")
    stage = Usd.Stage.Open(str(moved / "scenes" / "s.usda"))
    assert len(contract.asset_roots(stage)) == 3  # two cables and a socket
    assert check(stage) == []


def test_command_line(outputs, tmp_path, capsys):
    out = tmp_path / "scene.usdc"
    assert main(["compose", str(out), str(outputs["gravel"]), str(outputs["parts"]), "--limit", "1"]) == 0
    printed = capsys.readouterr().out
    assert "5 assets (1 granulaire, 4 quincaillerie)" in printed  # --limit is per file
    assert "conforms to the contract" in printed
    assert out.exists()
    assert main(["compose", str(tmp_path / "x.usda"), str(tmp_path / "nothing")]) == 2
    assert main(["compose", str(tmp_path / "x.txt"), str(outputs["gravel"])]) == 2
    with pytest.raises(SystemExit):
        main(["compose", str(out), str(outputs["gravel"]), "--limit", "0"])


def test_each_engine_layer_brings_the_assets_own_layers(outputs, tmp_path):
    """Beside the stage, one layer per engine: the stage below it, and on each placed asset a
    reference to the asset's root in its own engine layer, so its settings follow it."""
    from pxr import Sdf, UsdPhysics

    from primvaria.compose import layer_path

    out = tmp_path / "scene.usda"
    stage, assets = compose(out, [outputs["gravel"], outputs["cables"], outputs["parts"]])
    assert contract.engine_data(stage) == []  # the stage itself stays pure UsdPhysics
    for engine in ("newton", "physx"):
        path = layer_path(out, engine)
        assert list(Sdf.Layer.FindOrOpen(str(path)).subLayerPaths) == ["./scene.usda"]
        layered = Usd.Stage.Open(str(path))
        assert contract.engine_data(layered)  # the assets' engine settings are there
        for a in assets:
            spec = layered.GetRootLayer().GetPrimAtPath(a.path)
            refs = [r.assetPath for r in spec.referenceList.prependedItems] if spec else []
            own = layer_path(a.file, engine)
            if own.exists():
                assert any(r.endswith(own.name) for r in refs), (a.name, engine)
            else:
                assert not refs, (a.name, engine)
    newton = Usd.Stage.Open(str(layer_path(out, "newton")))
    gaps = [p for p in Usd.PrimRange.AllPrims(newton.GetPseudoRoot()) if p.HasAttribute("newton:contactGap")]
    assert gaps  # grains, cable segments and parts carry their contact gaps at their new paths
    cable = next(a for a in assets if a.generator == "filaire" and "usb_c_" in a.name)
    joints = [p for p in Usd.PrimRange(newton.GetPrimAtPath(cable.path)) if p.GetTypeName() == "PhysicsJoint"]
    assert joints and all(j.HasAPI(UsdPhysics.LimitAPI, "rotY") for j in joints)
    assert not layer_path(out, "omniphysics").exists()  # none of these assets has one


def test_engines_none_writes_no_layer_and_removes_old_ones(outputs, tmp_path):
    from primvaria.compose import layer_path

    out = tmp_path / "scene.usda"
    compose(out, [outputs["gravel"]])
    assert layer_path(out, "newton").exists()
    assert main(["compose", str(out), str(outputs["gravel"]), "--engines", "none"]) == 0
    assert not any(layer_path(out, e).exists() for e in ("physx", "omniphysics", "newton"))
    with pytest.raises(SystemExit) as refused:
        main(["compose", str(out), str(outputs["gravel"]), "--engines", "bullet"])
    assert refused.value.code == 2
