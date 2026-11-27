"""Every generated file follows the Primvaria OpenUSD contract.

Collected in each generator by ``tests/test_contract.py``, which imports this module. The
``contract_files`` fixture (the generator's ``conftest.py``) gives OpenUSD files freshly written
by the generator, one folder. The checks themselves, on stages written by hand, are tested in
primvaria-contract's own tests.
"""

import pytest
from pxr import Sdf, Usd

from ._fixtures import generator  # noqa: F401 (a fixture, collected where this module is imported)


def _stage_with_assets(files, contract):
    for f in files:
        stage = Usd.Stage.Open(str(f))
        if contract.asset_roots(stage):
            stage.SetEditTarget(stage.GetSessionLayer())  # never touch the file
            return stage
    raise AssertionError("no generated file has an asset root")


@pytest.mark.slow
def test_generated_files_conform(generator, contract_files):
    assert contract_files
    for f in contract_files:
        assert generator.contract.check(f) == [], f.name


def test_assets_name_their_generator(generator, contract_files):
    stage = _stage_with_assets(contract_files, generator.contract)
    for prim in generator.contract.asset_roots(stage):
        assert prim.GetAttribute("primvaria:contract").Get() == generator.contract.CONTRACT
        assert prim.GetAttribute("primvaria:generator").Get() == generator.name
        assert prim.GetAttribute("primvaria:version").Get() == generator.package.__version__
        assert prim.GetAttribute("primvaria:preset").Get()
        assert isinstance(prim.GetAttribute("primvaria:seed").Get(), int)
        info = Usd.ModelAPI(prim).GetAssetInfo()
        assert info["name"] and info["identifier"].path and info["version"] == generator.package.__version__


@pytest.mark.parametrize("key", ["contract", "generator", "version", "preset", "seed"])
def test_a_missing_attribute_is_reported(generator, contract_files, key):
    stage = _stage_with_assets(contract_files, generator.contract)
    prim = generator.contract.asset_roots(stage)[0]
    prim.GetAttribute(f"primvaria:{key}").Block()
    assert any(f"no primvaria:{key}" in p for p in generator.contract.conformance(stage))


def test_assets_say_what_was_drawn(generator, contract_files):
    stage = _stage_with_assets(contract_files, generator.contract)
    for prim in generator.contract.asset_roots(stage):
        drawn = generator.contract.variation(prim)
        assert isinstance(drawn["aspects"], list)
        assert all(generator.contract.VALUE_NAME.fullmatch(name) for name in drawn)


def test_missing_aspects_are_reported(generator, contract_files):
    stage = _stage_with_assets(contract_files, generator.contract)
    generator.contract.asset_roots(stage)[0].GetAttribute(generator.contract.ASPECTS).Block()
    assert any(f"no {generator.contract.ASPECTS}" in p for p in generator.contract.conformance(stage))


def test_a_variation_name_must_be_snake_case(generator, contract_files):
    stage = _stage_with_assets(contract_files, generator.contract)
    prim = generator.contract.asset_roots(stage)[0]
    with pytest.raises(ValueError, match="snake_case"):
        generator.contract.write_variation(prim, (), {"clearanceMm": 0.1})
    generator.contract.write_variation(
        prim, ("size",), {"flags": [True, False], "names": ["a", "b"], "none": None}
    )
    drawn = generator.contract.variation(prim)
    assert drawn["aspects"] == ["size"] and drawn["flags"] == [1.0, 0.0] and drawn["names"] == ["a", "b"]
    assert "none" not in drawn


def test_another_generator_is_reported_only_for_own_files(generator, contract_files):
    stage = _stage_with_assets(contract_files, generator.contract)
    other = next(g for g in generator.contract.GENERATORS if g != generator.name)
    prim = generator.contract.asset_roots(stage)[0]
    prim.GetAttribute("primvaria:generator").Set(other)
    assert any("primvaria:generator" in p for p in generator.contract.conformance(stage))
    # only a variant set this generator's assets carry, which section 7 gives to no other
    assert [p for p in generator.contract.conformance(stage, own=False) if "section 7" not in p] == []


def test_a_broken_model_hierarchy_is_reported(generator, contract_files):
    stage = _stage_with_assets(contract_files, generator.contract)
    prim = generator.contract.asset_roots(stage)[0]
    parent = prim.GetParent()
    if parent.IsPseudoRoot():
        pytest.skip("the asset root is the file's root prim")
    Usd.ModelAPI(parent).SetKind("")
    assert any("not a group model" in p for p in generator.contract.conformance(stage))


def test_no_asset_root_is_reported(generator, contract_files):
    stage = _stage_with_assets(contract_files, generator.contract)
    for prim in generator.contract.asset_roots(stage):
        Usd.ModelAPI(prim).SetKind("")
    assert any("no asset root" in p for p in generator.contract.conformance(stage))


@pytest.mark.slow
def test_command_line(generator, contract_files, capsys):
    assert generator.conformance.main([str(contract_files[0].parent)]) == 0
    assert "0 with issues" in capsys.readouterr().out
    assert generator.conformance.main([]) == 2


def test_files_hold_no_engine_data(generator, contract_files):
    """Contract, section 9: what only one engine reads lies in an engine layer, not in the file."""
    files = [f for f in contract_files if not generator.contract.is_engine_layer(f)]
    assert files
    for f in files:
        assert generator.contract.engine_data(Usd.Stage.Open(str(f))) == [], f.name


def test_engine_data_in_a_file_is_reported(generator, contract_files, tmp_path):
    files = [f for f in contract_files if not generator.contract.is_engine_layer(f)]
    source = next(f for f in files if generator.contract.asset_roots(Usd.Stage.Open(str(f))))
    copy = tmp_path / "copy.usda"
    Sdf.Layer.FindOrOpen(str(source)).Export(str(copy))  # the layer itself: a stage would let go of it
    stage = Usd.Stage.Open(str(copy))
    generator.contract.asset_roots(stage)[0].AddAppliedSchema("PhysxRigidBodyAPI")
    stage.GetRootLayer().Save()
    assert any("engine data in the file" in p for p in generator.contract.check(copy, own=False))


@pytest.mark.slow
def test_an_engine_layer_lies_over_its_file_only(generator, contract_files, tmp_path):
    for layer in (f for f in contract_files if generator.contract.is_engine_layer(f)):
        assert not any("engine layer" in p for p in generator.contract.check(layer)), layer.name
    stray = tmp_path / "nothing_physx.usda"
    Sdf.Layer.CreateNew(str(stray)).Save()
    assert any("only sublayer" in p for p in generator.contract.check(stray, own=False))


def test_assets_say_what_they_are_with_semantic_labels(generator, contract_files):
    """OpenUSD semantic labels: the classes, down to the preset, and the instance, the asset's name."""
    from pxr import UsdSemantics

    stage = _stage_with_assets(contract_files, generator.contract)
    for prim in generator.contract.asset_roots(stage):
        classes = generator.contract.labels(prim)
        assert len(classes) >= 2 and prim.GetAttribute("primvaria:preset").Get() in classes
        assert generator.contract.labels(prim, "instance") == [prim.GetName()]
        query = UsdSemantics.LabelsQuery("class", Usd.TimeCode.Default())
        assert set(query.ComputeUniqueInheritedLabels(prim)) == set(classes)  # what a renderer reads


def test_missing_labels_are_reported(generator, contract_files):
    stage = _stage_with_assets(contract_files, generator.contract)
    prim = generator.contract.asset_roots(stage)[0]
    prim.GetAttribute("semantics:labels:class").Set([])
    prim.GetAttribute("semantics:labels:instance").Set(["someone_else"])
    problems = generator.contract.conformance(stage)
    assert any("no class label" in p for p in problems) and any("instance label" in p for p in problems)


def test_class_labels_are_single_words(generator, contract_files):
    stage = _stage_with_assets(contract_files, generator.contract)
    prim = generator.contract.asset_roots(stage)[0]
    for bad in ((), ("Two Words",), ("grain", "")):
        with pytest.raises(ValueError, match="class labels"):
            generator.contract.write_labels(prim, bad)


def test_generated_variant_sets_follow_section_7(generator, contract_files):
    """Contract, section 7: snake_case names and a default selection, in every generated file."""
    for f in (f for f in contract_files if not generator.contract.is_engine_layer(f)):
        stage = Usd.Stage.Open(str(f))
        for prim in stage.Traverse():
            for name in prim.GetVariantSets().GetNames():
                vset = prim.GetVariantSet(name)
                assert generator.contract.VALUE_NAME.fullmatch(name), (f.name, name)
                assert all(generator.contract.VALUE_NAME.fullmatch(v) for v in vset.GetVariantNames()), (
                    f.name,
                    name,
                )
                assert vset.GetVariantSelection() in vset.GetVariantNames(), (f.name, name)
