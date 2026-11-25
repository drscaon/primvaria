"""``primvaria compose``: one stage referencing assets from the generators' outputs (PRV-14).

Every generator writes files whose assets are whole on their own (contract, sections 3 and 4): an
asset root of kind component, its materials inside it, resting on z = 0. Composing is therefore
referencing each asset root alone, side by side, on the shared ground and under the shared physics
scene, with no copy of geometry:

    /World                      kind assembly, the default prim
      /PhysicsScene             gravity along -Z (primvaria_contract.ground)
      /Ground, /GroundMaterial  the shared floor, sized to what is on it
      /Grains, /Cloths, ...     one scope per kind of asset, kind group
        /place_0007             an Xform that places one asset (kind group)
          /g_0000               the asset root, a reference to its file and prim

Each asset keeps its own pose and height from its file; the placing Xform only slides it along x
and y, so the assets stand in rows without touching. Two assets with the same name (the first
grains of two Granulaire packs are both g_0000) get the preset in front of their name, and the
instance label follows the name, as the contract requires.

The composed stage itself is pure UsdPhysics. Beside it, one engine layer per engine some of its
assets have a layer for (contract, section 9): ``<stage>_newton.usda``, ``<stage>_physx.usda``,
``<stage>_omniphysics.usda``. Each has the stage as its only sublayer and, on each placed asset
that has a layer for that engine, a stronger reference to the asset's root in that layer: the
asset's engine settings follow it into the scene, at its new path. Open the layer of the engine
you use instead of the stage. What an engine layer sets outside the asset roots (a file's own
physics scene or ground) is not carried: the composed stage has its own.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdSemantics

from primvaria_contract import contract, ground  # the contract code the four generators share

SCOPES = {"granulaire": "Grains", "maillage": "Cloths", "filaire": "Cables", "quincaillerie": "Parts"}
SKIP = ("materials",)  # folders of a generator's output that hold no assets


ENGINES = contract.ENGINES  # the engine layers of the contract, section 9


@dataclass
class Asset:
    file: Path  # the file that defines it
    prim: str  # its root's path in that file
    name: str  # its name in the composed stage
    generator: str
    preset: str
    lo: tuple  # its footprint in its file (x, y min and max), its own pose included
    hi: tuple
    path: str = ""  # its path in the composed stage, once placed


def _own_roots(stage) -> list:
    """The asset roots a file defines itself: a root that references another file (Quincaillerie's
    scene.usda places the files of its assets/ folder) is that file's asset, found there."""

    def external(root) -> bool:
        for spec in root.GetPrimStack():
            if any(r.assetPath for r in spec.referenceList.GetAddedOrExplicitItems()):
                return True
        return False

    return [root for root in contract.asset_roots(stage) if not external(root)]


def find_assets(inputs, limit: int | None = None) -> list[Asset]:
    """The assets of the given files and generator output folders, in the order given; at most
    ``limit`` from each file. Engine layers are left out: the files under them are read."""
    files = []
    for path in map(Path, inputs):
        if not path.exists():
            raise FileNotFoundError(f"{path}: no such file or folder")
        for f in contract.usd_files([path]):
            inside = f.relative_to(path).parts[:-1] if path.is_dir() else ()
            if not contract.is_engine_layer(f) and not any(part in SKIP for part in inside):
                files.append(f)
    assets = []
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    for file in files:
        stage = Usd.Stage.Open(str(file))
        roots = _own_roots(stage)
        for root in roots[:limit] if limit else roots:
            cache.Clear()
            box = cache.ComputeLocalBound(root).ComputeAlignedRange()  # with its own transform
            lo, hi = box.GetMin(), box.GetMax()
            assets.append(
                Asset(
                    file=file.resolve(),
                    prim=str(root.GetPath()),
                    name=root.GetName(),
                    generator=root.GetAttribute(f"{contract.NAMESPACE}:generator").Get() or "",
                    preset=root.GetAttribute(f"{contract.NAMESPACE}:preset").Get() or "",
                    lo=(lo[0], lo[1]),
                    hi=(hi[0], hi[1]),
                )
            )
    _unique_names(assets)
    return assets


def _unique_names(assets: list[Asset]) -> None:
    """Rename the assets whose names repeat: the preset in front, then a number if still needed."""
    count = {}
    for a in assets:
        count[a.name] = count.get(a.name, 0) + 1
    taken = {a.name for a in assets if count[a.name] == 1}
    for a in assets:
        if count[a.name] == 1:
            continue
        base = f"{a.preset}_{a.name}" if a.preset and not a.name.startswith(a.preset) else a.name
        name, k = base, 2
        while name in taken:
            name, k = f"{base}_{k}", k + 1
        a.name = name
        taken.add(name)


def layout(assets: list[Asset], gap: float = 0.05, width: float = 2.0) -> list[tuple[float, float]]:
    """The x-y offset of each asset: in rows along x, ``gap`` apart, a new row when a row would be
    wider than ``width`` (m). Rows go towards -y, the first one along y = 0."""
    offsets, x, y, row_depth = [], 0.0, 0.0, 0.0
    for a in assets:
        w, d = a.hi[0] - a.lo[0], a.hi[1] - a.lo[1]
        if x > 0 and x + w > width:
            x, y, row_depth = 0.0, y - row_depth - gap, 0.0
        offsets.append((x - a.lo[0], y - a.hi[1]))
        x += w + gap
        row_depth = max(row_depth, d)
    return offsets


def compose(out, inputs, limit: int | None = None, gap: float = 0.05, width: float = 2.0, engines=ENGINES):
    """Write ``out`` (.usda or .usdc): the assets of ``inputs`` on the shared ground, and beside it
    the engine layers asked for (``engines``, among ENGINES) that some asset has. Returns the stage
    and the assets placed."""
    unknown = set(engines) - set(ENGINES)
    if unknown:
        raise ValueError(f"unknown engine {sorted(unknown)[0]!r}; expected some of {', '.join(ENGINES)}")
    out = Path(out)
    if out.suffix not in (".usda", ".usdc", ".usd"):
        raise ValueError(f"{out}: the composed stage is an OpenUSD file (.usda, .usdc or .usd)")
    assets = find_assets(inputs, limit)
    if not assets:
        raise ValueError("no asset found in " + ", ".join(map(str, inputs)))
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    stage = Usd.Stage.CreateNew(str(out))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    contract.set_group(world, assembly=True)
    ground.physics_scene(stage)
    lo, hi = [float("inf")] * 2, [float("-inf")] * 2
    for i, (a, (dx, dy)) in enumerate(zip(assets, layout(assets, gap, width), strict=True)):
        scope = f"/World/{SCOPES.get(a.generator, 'Assets')}"
        if not stage.GetPrimAtPath(scope):
            contract.set_group(UsdGeom.Scope.Define(stage, scope).GetPrim())
        place = UsdGeom.Xform.Define(stage, f"{scope}/place_{i:04d}")
        place.AddTranslateOp().Set(Gf.Vec3d(dx, dy, 0.0))
        contract.set_group(place.GetPrim())
        prim = stage.DefinePrim(place.GetPath().AppendChild(a.name))
        a.path = str(prim.GetPath())
        ref = os.path.relpath(a.file, out.resolve().parent).replace(os.sep, "/")
        prim.GetReferences().AddReference(ref if ref.startswith(".") else f"./{ref}", Sdf.Path(a.prim))
        if a.name != Path(a.prim).name:  # renamed: its instance label is its new name (contract)
            UsdSemantics.LabelsAPI.Apply(prim, "instance").CreateLabelsAttr([a.name])
        for k in (0, 1):
            lo[k] = min(lo[k], a.lo[k] + (dx, dy)[k])
            hi[k] = max(hi[k], a.hi[k] + (dx, dy)[k])
    ground.ground(stage, tuple(lo), tuple(hi))
    stage.GetRootLayer().Save()
    for engine in ENGINES:
        layer_path(out, engine).unlink(missing_ok=True)
        if engine in engines:
            engine_layer(out, assets, engine)
    return stage, assets


def layer_path(file, engine: str) -> Path:
    """A file's layer for an engine, beside it (contract, section 9)."""
    file = Path(file)
    return file.with_name(f"{file.stem}_{engine}.usda")


def engine_layer(out, assets: list[Asset], engine: str) -> Path | None:
    """Write ``<out>_<engine>.usda`` over the composed stage: each placed asset that has a layer for
    the engine references its root there too, ahead of the file. None if no asset has one."""
    out = Path(out)
    layered = [a for a in assets if layer_path(a.file, engine).exists()]
    if not layered:
        return None
    path = layer_path(out, engine)
    layer = Sdf.Layer.CreateNew(str(path))
    layer.subLayerPaths.append(f"./{out.name}")
    stage = Usd.Stage.Open(layer)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))
    for a in layered:
        ref = os.path.relpath(layer_path(a.file, engine), path.resolve().parent).replace(os.sep, "/")
        stage.OverridePrim(a.path).GetReferences().AddReference(
            ref if ref.startswith(".") else f"./{ref}",
            Sdf.Path(a.prim),
            position=Usd.ListPositionFrontOfPrependList,
        )
    layer.Save()
    return path


def check(stage) -> list[str]:
    """What the composed stage gets wrong: the contract (assets from any generator) and the ground."""
    return contract.conformance(stage) + ground.conformance(stage)
