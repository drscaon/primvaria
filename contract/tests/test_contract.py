"""The checks of the contract, on stages written here (the generators test their own files).

Moved from the generators' shared tests/test_contract.py, which keeps the tests of each
generator's files.
"""

import json

import pytest
from pxr import Sdf, Usd, UsdGeom, UsdShade

from primvaria_contract import conformance as cli
from primvaria_contract import contract, ground, pack


def _one_asset(generator="granulaire"):
    """A stage that conforms, with one asset /World/Part, written with the contract's own helpers
    and said to be of ``generator``: the one a variant set of the test belongs to (section 7)."""
    from pxr import UsdGeom, UsdPhysics

    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    contract.set_group(world, assembly=True)
    prim = UsdGeom.Xform.Define(stage, "/World/Part").GetPrim()
    contract.write_identity(
        prim, name="Part", preset="test", seed=1, identifier="./part.usda", generator=generator, version="1.0"
    )
    contract.write_variation(prim, (), {})
    contract.write_labels(prim, ("part", "test"))
    assert contract.conformance(stage) == []
    return stage, prim


def _variant_set(prim, name, variants, selection=None):
    vset = prim.GetVariantSets().AddVariantSet(name)
    for v in variants:
        vset.AddVariant(v)
    if selection:
        vset.SetVariantSelection(selection)
    return vset


@pytest.mark.parametrize(
    "name, variants, selection, problem",
    [
        ("Moisture", ["dry", "wet"], "dry", "not lowercase snake_case"),
        ("moisture", ["dry", "Wet"], "dry", "variant 'Wet' is not lowercase snake_case"),
        ("moisture", ["dry", "wet"], None, "no default selection"),
    ],
)
def test_a_variant_set_against_section_7_is_reported(name, variants, selection, problem):
    stage, prim = _one_asset("granulaire")
    _variant_set(prim, name, variants, selection)
    assert any(problem in p for p in contract.conformance(stage))


CHANGED = "/World/Part: variant brass of finish changes the asset's identity"


def test_a_variant_that_changes_the_identity_is_reported():
    """A variant changes the asset's state, never what it is (section 5): its preset, its labels."""
    stage, prim = _one_asset("quincaillerie")
    prim.RemoveProperty("primvaria:preset")  # a local opinion is stronger than a variant's
    vset = _variant_set(prim, "finish", ["as_generated", "brass"])
    for variant, preset in (("as_generated", "test"), ("brass", "another")):
        vset.SetVariantSelection(variant)
        with vset.GetVariantEditContext():
            prim.CreateAttribute("primvaria:preset", Sdf.ValueTypeNames.String).Set(preset)
    vset.SetVariantSelection("as_generated")
    assert contract.conformance(stage) == [CHANGED]

    stage, prim = _one_asset("quincaillerie")
    prim.RemoveProperty("semantics:labels:class")
    vset = _variant_set(prim, "finish", ["as_generated", "brass"])
    for variant, classes in (("as_generated", ["part", "test"]), ("brass", ["part", "brass"])):
        vset.SetVariantSelection(variant)
        with vset.GetVariantEditContext():
            prim.CreateAttribute("semantics:labels:class", Sdf.ValueTypeNames.TokenArray).Set(classes)
            prim.CreateAttribute("test:roughness", Sdf.ValueTypeNames.Float).Set(0.3)  # a state: allowed
    vset.SetVariantSelection("as_generated")
    assert contract.conformance(stage) == [CHANGED]


def test_the_variant_check_leaves_the_stage_as_it_was():
    stage, prim = _one_asset("granulaire")
    vset = _variant_set(prim, "moisture", ["dry", "wet"], "dry")
    with vset.GetVariantEditContext():
        prim.CreateAttribute("test:water", Sdf.ValueTypeNames.Float).Set(0.0)
    vset.SetVariantSelection("wet")
    with vset.GetVariantEditContext():
        prim.CreateAttribute("test:water", Sdf.ValueTypeNames.Float).Set(0.2)
    stage.SetEditTarget(stage.GetSessionLayer())
    vset.SetVariantSelection("dry")  # the selection of the session layer is kept as it is
    session = stage.GetSessionLayer().ExportToString()
    assert contract.conformance(stage) == []
    assert stage.GetSessionLayer().ExportToString() == session
    assert vset.GetVariantSelection() == "dry" and prim.GetAttribute("test:water").Get() == 0.0


@pytest.mark.parametrize(
    "generator, name",
    [("maillage", "state"), ("quincaillerie", "moisture"), ("granulaire", "wetness")],
)
def test_a_variant_set_the_contract_does_not_give_its_generator_is_reported(generator, name):
    """Section 7 says what each variant set means and who uses it: a new one, or one used by another
    generator, is written into the contract first, so that a name means the same everywhere."""
    stage, prim = _one_asset(generator)
    _variant_set(prim, name, ["a", "b"], "a")
    problems = contract.conformance(stage)
    assert problems == [f"/World/Part: variant set {name}: not in the contract's section 7 for {generator}"]


@pytest.mark.parametrize(
    "path, type_name, problem",
    [
        ("/World/Part/MateFrameThread", "Xform", "not named MateFrame or MateFrame_<feature>"),
        ("/World/Part/MateFrame_Thread", "Xform", "not named MateFrame or MateFrame_<feature>"),
        ("/World/Part/MateFrame_thread", "Scope", "a MateFrame is an Xform, not Scope"),
        ("/World/MateFrame", "Xform", "a MateFrame outside an asset root"),
    ],
)
def test_a_mate_frame_against_section_8_is_reported(path, type_name, problem):
    stage, _ = _one_asset()
    stage.DefinePrim(path, type_name)
    assert any(problem in p for p in contract.conformance(stage))


def test_mate_frames_are_checked_in_every_variant():
    """A MateFrame often comes with a variant (a connector on a cable end): each one is checked."""
    stage, prim = _one_asset("filaire")
    vset = _variant_set(prim, "end_a", ["cut", "plug"], "cut")
    vset.SetVariantSelection("plug")
    with vset.GetVariantEditContext():
        stage.DefinePrim("/World/Part/Plug/MateFrame_Pins", "Xform")
    vset.SetVariantSelection("cut")
    problems = contract.conformance(stage)
    assert any("MateFrame_Pins: not named" in p and "(variant plug of end_a)" in p for p in problems)


def test_common_mate_attributes_are_not_written_yet():
    """Section 8: mate attributes stay in the generator's namespace; primvaria:mate:* is not in v1."""
    stage, prim = _one_asset()
    frame = stage.DefinePrim("/World/Part/MateFrame", "Xform")
    frame.CreateAttribute("test:role", Sdf.ValueTypeNames.Token).Set("plug")
    assert contract.conformance(stage) == []
    prim.CreateAttribute("primvaria:mate:role", Sdf.ValueTypeNames.Token).Set("plug")
    problems = contract.conformance(stage)
    assert any("primvaria:mate:* attributes are not in the contract" in p for p in problems)


def test_an_asset_that_points_outside_itself_is_reported():
    """Section 4: an asset is whole on its own, so that referenced alone it keeps its materials."""
    from pxr import UsdShade

    stage, prim = _one_asset()
    outside = UsdShade.Material.Define(stage, "/World/Looks/paint")
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(outside)
    problems = contract.conformance(stage)
    assert problems == ["/World/Part: material:binding points outside its asset, to /World/Looks/paint"]
    inside = UsdShade.Material.Define(stage, "/World/Part/Looks/paint")
    UsdShade.MaterialBindingAPI(prim).Bind(inside)
    assert contract.conformance(stage) == []


def test_the_generator_that_wrote_a_stage_is_checked_when_given():
    stage, prim = _one_asset("granulaire")
    assert contract.conformance(stage, "granulaire", "1.0") == []
    assert contract.conformance(stage, "maillage", "1.0") == [
        "/World/Part: primvaria:generator is 'granulaire', not 'maillage'"
    ]
    assert contract.conformance(stage, "granulaire", "2.0") == [
        "/World/Part: primvaria:version is '1.0', not '2.0'"
    ]
    prim.GetAttribute("primvaria:generator").Set("someone")
    assert contract.conformance(stage) == ["/World/Part: unknown primvaria:generator 'someone'"]


def test_write_identity_needs_the_generator_and_its_version():
    stage, prim = _one_asset()
    with pytest.raises(TypeError):
        contract.write_identity(prim, name="Part", preset="test", seed=1, identifier="./part.usda")


def _folder_with_a_file(tmp_path, generator="filaire"):
    stage, prim = _one_asset(generator)
    ground.physics_scene(stage)
    ground.ground(stage)
    UsdGeom.Cube.Define(stage, "/World/Part/Box")
    stage.GetRootLayer().Export(str(tmp_path / "part.usda"))
    return tmp_path


def test_a_pack_names_its_generator_and_agrees_with_its_files(tmp_path):
    folder = _folder_with_a_file(tmp_path)
    pack.write_pack(folder, pack="test", seed=1, summary={"n": 1}, generator="filaire", version="1.0")
    manifest = json.loads((folder / pack.MANIFEST).read_text())
    assert (manifest["generator"], manifest["version"], manifest["assets"]) == ("filaire", "1.0", 1)
    assert pack.check_pack(folder) == []
    with pytest.raises(TypeError):
        pack.write_pack(folder, pack="test", seed=1)


def test_the_command_line_checks_files_of_any_generator_or_of_one(tmp_path, capsys):
    folder = _folder_with_a_file(tmp_path, "quincaillerie")
    assert cli.main([str(folder)]) == 0
    assert cli.main([str(folder)], "quincaillerie", "1.0") == 0
    assert cli.main([str(folder)], "granulaire", "1.0") == 1
    assert "not 'granulaire'" in capsys.readouterr().out
    assert cli.main([]) == 2


def test_the_ground_follows_the_contract(tmp_path):
    folder = _folder_with_a_file(tmp_path)
    stage = Usd.Stage.Open(str(folder / "part.usda"))
    assert ground.conformance(stage) == []
    assert ground.read_ground(stage)["top"] == pytest.approx(0.0, abs=1e-6)
    g = stage.GetPrimAtPath(ground.GROUND_PATH)
    assert contract.labels(g) == [ground.GROUND_LABEL]
    look, _ = UsdShade.MaterialBindingAPI(g).ComputeBoundMaterial()
    assert str(look.GetPath()) == ground.GROUND_MATERIAL_PATH and look.GetSurfaceOutput().HasConnectedSource()
    assert contract.labels(look.GetPrim(), contract.MATERIAL_LABEL) == [ground.GROUND_MATERIAL_LABEL]


def test_every_material_says_what_it_is_made_of():
    """Section 5: a Material carries semantics:labels:material, one word."""
    from pxr import UsdShade

    stage, prim = _one_asset()
    mat = UsdShade.Material.Define(stage, "/World/Part/Looks/steel")
    assert contract.unlabelled_materials(stage) == ["/World/Part/Looks/steel"]
    assert contract.conformance(stage) == []  # optional in contract 0
    contract.write_material_label(mat, "steel")
    assert contract.unlabelled_materials(stage) == []
    assert contract.labels(mat.GetPrim(), contract.MATERIAL_LABEL) == ["steel"]
    with pytest.raises(ValueError, match="material label"):
        contract.write_material_label(mat, "zinc plated steel")
