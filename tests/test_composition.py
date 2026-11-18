"""Assets of the four generators in one stage, as the contract promises (PRV-40).

A grain, a cloth piece, a cable and a screw with its nut, each referenced alone from the file its
generator wrote, are placed side by side on the shared ground by `primvaria compose` (PRV-14). The
composed stage must conform to the contract and pass the OpenUSD validators; each asset keeps its own
materials (render and physics) and its labels; and the rigid ones settle in MuJoCo with their own friction.

What MuJoCo is not given here: the cable and the cloth. Each generator's own MuJoCo checks build
those (a chain of jointed segments, a flex); no converter reads both from one stage yet.
"""

from pathlib import Path

import numpy as np
import pytest
from pxr import Kind, Usd, UsdGeom, UsdPhysics, UsdSemantics, UsdShade

granulaire = pytest.importorskip("granulaire")
maillage = pytest.importorskip("maillage")
filaire = pytest.importorskip("filaire")
quincaillerie = pytest.importorskip("quincaillerie")

from granulaire import contract, ground  # noqa: E402  (the same files in the four generators)
from granulaire.validate import validate  # noqa: E402

from primvaria.compose import compose  # noqa: E402

GENERATORS = ("granulaire", "maillage", "filaire", "quincaillerie")


@pytest.fixture(scope="module")
def sources(tmp_path_factory):
    """The files the four generators wrote: a grain, a cloth piece, a cable, a screw and its nut."""
    out = tmp_path_factory.mktemp("composition")
    g = granulaire.write_outputs(granulaire.generate_scene("crushed_gravel", shapes=2, copies=1), out / "g")
    m = maillage.write_outputs(maillage.generate_scene("tea_towel", count=1, vertices=300), out / "m")
    f = filaire.write_outputs(filaire.generate_scene("usb_c", count=1, seed=1), out / "f")
    q = quincaillerie.generate(
        quincaillerie.resolve("screw", "M6", 12, ["nut"]), str(out / "q"), "q", count=1, seed=1, detail="low"
    )
    assets = Path(q.out_dir) / "assets"
    return [
        next(g.glob("granulaire_*.usdc")),
        next(m.glob("maillage_*.usdc")),
        next(f.glob("filaire_*.usdc")),
        next(assets.glob("ISO4017_*_000.usdc")),
        next(assets.glob("ISO4032_*_000.usdc")),
    ]


@pytest.fixture(scope="module")
def composed(sources, tmp_path_factory):
    """The stage `primvaria compose` writes (PRV-14): the shared ground and physics scene, and each
    asset referenced on its own under a placing Xform (a group model), its own pose kept."""
    path = tmp_path_factory.mktemp("stage") / "composed.usda"
    stage, _ = compose(path, sources, limit=1)
    return stage


def test_every_generator_is_in_the_stage(composed):
    found = {r.GetAttribute("primvaria:generator").Get() for r in contract.asset_roots(composed)}
    assert found == set(GENERATORS)


def test_the_composed_stage_conforms_and_validates(composed):
    assert contract.conformance(composed, own=False) == []
    assert ground.conformance(composed) == []
    assert validate(composed.GetRootLayer().realPath) == []


def _lowest(root) -> float:
    """The lowest point of an asset's geometry, exactly (a bounding box of a tilted capsule or of
    a mesh's extent reaches lower than the shape does)."""
    cache, low = UsdGeom.XformCache(), np.inf
    for prim in Usd.PrimRange(root):
        M = np.asarray(cache.GetLocalToWorldTransform(prim))
        scale = np.linalg.norm(M[:3, :3], axis=1)
        if prim.IsA(UsdGeom.Mesh):
            P = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(), float)
            z = (P @ M[:3, :3] + M[3, :3])[:, 2].min()
        elif prim.IsA(UsdGeom.Cube):
            s = UsdGeom.Cube(prim).GetSizeAttr().Get() / 2
            corners = np.array([[x, y, w] for x in (-s, s) for y in (-s, s) for w in (-s, s)])
            z = (corners @ M[:3, :3] + M[3, :3])[:, 2].min()
        elif prim.IsA(UsdGeom.Capsule) or prim.IsA(UsdGeom.Cylinder):
            shape = UsdGeom.Capsule(prim) if prim.IsA(UsdGeom.Capsule) else UsdGeom.Cylinder(prim)
            r, h = shape.GetRadiusAttr().Get(), shape.GetHeightAttr().Get()
            a = {"X": 0, "Y": 1, "Z": 2}[shape.GetAxisAttr().Get()]
            axis = M[a, :3] / scale[a]
            reach = np.sqrt(max(0.0, 1 - axis[2] ** 2))  # a disc's edge, or a capsule's sphere
            r_down = r * (1.0 if prim.IsA(UsdGeom.Capsule) else reach) * scale[(a + 1) % 3]
            z = M[3, 2] - abs(M[a, 2]) * h / 2 - r_down
        else:
            continue
        low = min(low, z)
    return low


def test_every_asset_starts_on_the_ground_not_in_it(composed):
    """Contract, section 3: an asset rests on z = 0. Placed at z = 0, none starts inside the ground
    (a Granulaire pile or a cloth is laid a little above it); a standalone part rests on it exactly."""
    for root in contract.asset_roots(composed):
        low = _lowest(root)
        assert low > -1e-6, (root.GetPath(), low)
        if root.GetAttribute("primvaria:generator").Get() in ("quincaillerie", "filaire"):
            assert low < 1e-6, (root.GetPath(), low)


def test_one_physics_scene_and_one_ground(composed):
    """No asset brings a scene or a floor of its own: they are the composing stage's."""
    prims = list(composed.Traverse())
    assert [str(p.GetPath()) for p in prims if p.IsA(UsdPhysics.Scene)] == ["/World/PhysicsScene"]
    static = [p for p in prims if p.HasAPI(UsdPhysics.CollisionAPI) and not _body_of(p)]
    assert [str(p.GetPath()) for p in static] == ["/World/Ground"]


def test_every_asset_keeps_its_materials(composed):
    """Referenced alone, an asset still finds its render and physics materials: they are inside it."""
    for root in contract.asset_roots(composed):
        meshes = [
            p
            for p in Usd.PrimRange(root)
            if p.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(p).ComputePurpose() != UsdGeom.Tokens.guide
        ]
        assert meshes, root.GetPath()
        for mesh in meshes:
            material, _ = UsdShade.MaterialBindingAPI(mesh).ComputeBoundMaterial()
            subsets = UsdShade.MaterialBindingAPI(mesh).GetMaterialBindSubsets()
            bound = [material] + [UsdShade.MaterialBindingAPI(s).ComputeBoundMaterial()[0] for s in subsets]
            assert any(m and m.GetPrim().IsValid() for m in bound), mesh.GetPath()
            assert all(m.GetPath().HasPrefix(root.GetPath()) for m in bound if m), mesh.GetPath()
        for collider in (p for p in Usd.PrimRange(root) if p.HasAPI(UsdPhysics.CollisionAPI)):
            material, _ = UsdShade.MaterialBindingAPI(collider).ComputeBoundMaterial("physics")
            assert material and material.GetPrim().HasAPI(UsdPhysics.MaterialAPI), collider.GetPath()


def test_labels_name_each_asset_once(composed):
    query = UsdSemantics.LabelsQuery("instance", Usd.TimeCode.Default())
    names = [tuple(query.ComputeUniqueDirectLabels(r)) for r in contract.asset_roots(composed)]
    assert len(names) == len(set(names))
    assert all(len(contract.labels(r)) >= 2 for r in contract.asset_roots(composed))


def _body_of(prim):
    while prim and not prim.IsPseudoRoot():
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            return prim
        prim = prim.GetParent()
    return None


def test_the_rigid_assets_settle_in_mujoco_with_their_own_friction(composed):
    mujoco = pytest.importorskip("mujoco")
    from quincaillerie.sim.mujoco_model import _friction, convert

    stage = Usd.Stage.Open(composed.GetRootLayer())  # its own session layer: the fixture is kept
    with Usd.EditContext(stage, stage.GetSessionLayer()):
        for scope in ("Cables", "Cloths"):  # see the module's docstring
            stage.GetPrimAtPath(f"/World/{scope}").SetActive(False)
    grain = next(
        r for r in contract.asset_roots(stage) if r.GetAttribute("primvaria:generator").Get() == "granulaire"
    )
    collider = next(p for p in Usd.PrimRange(grain) if p.HasAPI(UsdPhysics.CollisionAPI))
    expected = UsdShade.MaterialBindingAPI(collider).ComputeBoundMaterial("physics")[0]
    friction = UsdPhysics.MaterialAPI(expected).GetDynamicFrictionAttr().Get()
    assert _friction(collider, -1.0) == pytest.approx(friction)  # its own, not a default

    model = mujoco.MjModel.from_xml_string(convert(stage, options='<option timestep="0.0005"/>'))
    data = mujoco.MjData(model)
    bodies = [model.body(i).name for i in range(1, model.nbody)]
    assert len(bodies) == 3  # the grain, the screw, the nut
    while data.time < 1.5:
        mujoco.mj_step(model, data)
    for i in range(1, model.nbody):
        speed = np.linalg.norm(data.cvel[i][3:])
        assert speed < 0.005, (bodies[i - 1], speed)  # at rest
        assert data.xipos[i][2] > 0, bodies[i - 1]  # above the floor, not through it
    assert Kind.Tokens.assembly == Usd.ModelAPI(stage.GetPrimAtPath("/World")).GetKind()
