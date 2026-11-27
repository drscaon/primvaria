"""A generated file as one ``.usdz`` package: the file, everything it depends on, and its engine
layers, in one archive that viewers and tools outside robotics open directly.

``package(file)`` writes ``<file stem>.usdz`` beside the file. The file is the package's root
layer, so opening the package opens it as it is; the textures, material libraries and assets it
references are copied in (OpenUSD's asset localization, which rewrites their paths to lie inside
the package); the engine layers beside it (``<stem>_physx.usda``, ``_newton``, ``_omniphysics``,
contract section 9) go in too, at the root next to the file, each still holding the file as its
only sublayer. One opens with ``Usd.Stage.Open("<stem>.usdz[<stem>_physx.usda]")``.

The pack (``instances.csv``, ``manifest.json``) lists the OpenUSD files, not their packages: a
``.usdz`` is a copy of what is already there, made on request (``--usdz`` in each generator).
``check(package)`` runs the validators of the UsdValidation registry on the package, the
packaging rules included, which the generators' ``validate`` leaves out.

Command line::

    python -m primvaria_contract.usdz FILES...        # one .usdz beside each file
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

from pxr import Sdf, Usd, UsdUtils, UsdValidation

from .contract import ENGINE_LAYERS, is_engine_layer
from .validate import _materialx_in_sdr

__all__ = ["package", "package_pack", "engine_layers", "check", "main"]

SUFFIXES = (".usd", ".usda", ".usdc")


def engine_layers(path: str | Path) -> list[Path]:
    """The engine layers beside a file: ``<stem>_physx``, ``_omniphysics``, ``_newton``."""
    path = Path(path)
    found = []
    for suffix in ENGINE_LAYERS:
        found += sorted(f for f in path.parent.glob(f"{path.stem}{suffix}.*") if f.suffix in SUFFIXES)
    return found


class _Quiet:
    """Hide what OpenUSD prints on the C++ side while localizing: a second resolve of paths it has
    already rewritten warns ("Failed to resolve reference @0/...@") though nothing is wrong. What
    it prints otherwise is passed on."""

    NOISE = ("Failed to resolve reference @", "_EnqueueDependency")

    def __enter__(self):
        sys.stderr.flush()
        self._log = tempfile.TemporaryFile(mode="w+b")
        self._saved = os.dup(2)
        os.dup2(self._log.fileno(), 2)
        return self

    def __exit__(self, *exc):
        sys.stderr.flush()
        os.dup2(self._saved, 2)
        os.close(self._saved)
        self._log.seek(0)
        for line in self._log.read().decode(errors="replace").splitlines():
            if line.strip() and not any(n in line for n in self.NOISE):
                print(line, file=sys.stderr)
        self._log.close()
        return False


def _add_engine_layers(path: Path, root: Path) -> None:
    """Copy the engine layers of ``path`` into the localized package at ``root``, with the engine
    layers they in turn sublayer or reference (a scene's layer points at its assets' layers), at
    the same place relative to the file. Anything else they need must already be in the package."""
    base = path.parent
    queue, seen = list(engine_layers(path)), set()
    while queue:
        layer = queue.pop(0).resolve()
        if layer in seen:
            continue
        seen.add(layer)
        rel = layer.relative_to(base)
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(layer, root / rel)
        for dep in Sdf.Layer.FindOrOpen(str(layer)).GetCompositionAssetDependencies():
            target = (layer.parent / dep).resolve()
            if is_engine_layer(target):
                queue.append(target)
            elif not target.is_relative_to(base) or not (root / target.relative_to(base)).exists():
                raise ValueError(f"{rel}: depends on {dep}, which the package does not hold")


def package(path: str | Path, out: str | Path | None = None) -> Path:
    """Write ``path`` as one .usdz (``out``, default ``<stem>.usdz`` beside it): the file as root
    layer, its dependencies, its engine layers. Returns the package's path."""
    path = Path(path).resolve()
    if is_engine_layer(path):
        raise ValueError(f"{path.name} is an engine layer: package the file it extends")
    out = Path(out) if out else path.with_suffix(".usdz")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "package"
        with _Quiet():
            ok = UsdUtils.LocalizeAsset(str(path), str(root))
        if not ok:
            raise RuntimeError(f"OpenUSD could not gather what {path.name} depends on")
        _add_engine_layers(path, root)
        main_file = root / path.name
        writer = Sdf.ZipFileWriter.CreateNew(str(out))
        writer.AddFile(str(main_file), path.name)  # the root layer comes first
        for f in sorted(f for f in root.rglob("*") if f.is_file() and f != main_file):
            writer.AddFile(str(f), f.relative_to(root).as_posix())
        writer.Save()
    return out


def package_pack(folder: str | Path) -> list[Path]:
    """One .usdz per OpenUSD file at the top of a pack folder (its scene or scenes, not the assets
    they reference from subfolders, which go inside), engine layers left to their file; a pack
    with no file at its top (assets without a scene) gets one per asset."""
    folder = Path(folder)

    def main_files(found):
        return sorted(f for f in found if f.suffix in SUFFIXES and not is_engine_layer(f))

    files = main_files(folder.iterdir()) or [
        f for f in main_files(folder.rglob("*")) if "materials" not in f.relative_to(folder).parts
    ]
    return [package(f) for f in files]


def check(path: str | Path) -> list[str]:
    """What the validators of the UsdValidation registry find in a package, packaging rules
    included (empty: nothing)."""
    reg = UsdValidation.ValidationRegistry()
    validators = reg.GetOrLoadValidatorsByName([m.name for m in reg.GetAllValidatorMetadata()])
    stage = Usd.Stage.Open(str(path))
    context = UsdValidation.ValidationContext(validators)
    messages = [e.GetMessage() for e in context.Validate(stage)]
    if not _materialx_in_sdr():  # usd-core wheels: MaterialX nodes unknown, as in validate
        messages = [m for m in messages if not ("'ND_" in m and "not found in sdrRegistry" in m)]
    return [f"{Path(path).name}: {m}" for m in messages]


def main(argv: list[str] | None = None) -> int:
    files = [Path(a) for a in (sys.argv[1:] if argv is None else argv)]
    if not files:
        print("usage: python -m primvaria_contract.usdz FILES...", file=sys.stderr)
        return 2
    failed = 0
    for f in files:
        out = package(f)
        problems = check(out)
        failed += bool(problems)
        print(f"{out}: {'; '.join(problems) if problems else 'written, no issue'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
