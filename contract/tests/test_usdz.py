"""A file as one .usdz: the file as root layer, its dependencies inside, its engine layers beside it."""

from pathlib import Path

import pytest
from pxr import Sdf, Usd, UsdGeom, UsdShade

from primvaria_contract import contract, ground, usdz


def _pack(tmp_path: Path) -> Path:
    """A file with a texture one folder up, and a PhysX layer beside it."""
    (tmp_path / "textures").mkdir()
    (tmp_path / "textures" / "c.png").write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
        )
    )
    folder = tmp_path / "pack"
    folder.mkdir()
    path = folder / "part.usda"
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    ground.physics_scene(stage)
    ground.ground(stage)
    mat = UsdShade.Material.Define(stage, "/World/Looks/paint")
    tex = UsdShade.Shader.Define(stage, "/World/Looks/paint/tex")
    tex.CreateIdAttr("UsdUVTexture")
    tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set("../textures/c.png")
    contract.write_material_label(mat, "paint")
    stage.Save()
    layer = Sdf.Layer.CreateNew(str(folder / "part_physx.usda"))
    layer.subLayerPaths.append("./part.usda")
    layer.Save()
    return path


def test_the_package_holds_the_file_its_texture_and_its_engine_layer(tmp_path):
    path = _pack(tmp_path)
    out = usdz.package(path)
    assert out == path.with_suffix(".usdz")
    names = Sdf.ZipFile.Open(str(out)).GetFileNames()
    assert names[0] == "part.usda" and "part_physx.usda" in names
    assert any(n.endswith("c.png") for n in names)
    stage = Usd.Stage.Open(f"{out}[part_physx.usda]")
    assert stage.GetPrimAtPath(ground.GROUND_PATH)  # the layer still holds the file
    assert usdz.check(out) == []


def test_an_engine_layer_is_not_packaged_alone(tmp_path):
    path = _pack(tmp_path)
    with pytest.raises(ValueError, match="engine layer"):
        usdz.package(path.with_name("part_physx.usda"))


def test_the_command_line_writes_and_checks(tmp_path, capsys):
    path = _pack(tmp_path)
    assert usdz.main([str(path)]) == 0
    assert "no issue" in capsys.readouterr().out
    assert usdz.main([]) == 2
