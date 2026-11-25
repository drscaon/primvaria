"""The OpenUSD validators, on files written here (the generators run them on their own files)."""

from pxr import Sdf, Usd, UsdGeom

from primvaria_contract import validate


def _file(tmp_path, name="part.usda", variants=False):
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(root)
    UsdGeom.Cube.Define(stage, "/World/Box")
    if variants:
        vset = root.GetVariantSets().AddVariantSet("finish")
        for v in ("matte", "glossy"):
            vset.AddVariant(v)
            vset.SetVariantSelection(v)
            with vset.GetVariantEditContext():
                UsdGeom.Sphere.Define(stage, f"/World/{v.capitalize()}")
        vset.SetVariantSelection("matte")
    stage.GetRootLayer().Export(str(tmp_path / name))
    return tmp_path / name


def test_a_plain_file_passes(tmp_path):
    assert validate.validate(_file(tmp_path)) == []


def test_every_variant_is_composed_once(tmp_path):
    stage = Usd.Stage.Open(str(_file(tmp_path, variants=True)))
    states = validate._variant_states(stage)
    assert states[0] == {}  # the file as authored first
    assert sorted(s[("/World", "finish")] for s in states[1:]) == ["glossy", "matte"]


def test_a_broken_file_is_reported(tmp_path):
    layer = Sdf.Layer.CreateNew(str(tmp_path / "broken.usda"))
    layer.subLayerPaths.append("./missing.usda")  # a sublayer that does not exist
    layer.Save()
    assert validate.validate(tmp_path / "broken.usda") != []


def test_the_command_line(tmp_path, capsys):
    _file(tmp_path)
    assert validate.main([str(tmp_path)]) == 0
    assert "1 OpenUSD files checked, 0 with issues" in capsys.readouterr().out
    assert validate.main([str(tmp_path / "nothing.usda")], "granulaire") == 1
    assert "not found" in capsys.readouterr().err
    assert validate.main([], "granulaire") == 2
    assert "python -m granulaire.validate" in capsys.readouterr().err
