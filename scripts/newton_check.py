"""Newton on CPU as an engine of the matrix: every preset's Newton layer, opened and checked.

Two steps, in two environments, because Newton pins its own usd-core and MuJoCo:

    python scripts/newton_check.py generate packs/          # with primvaria and the generators
    python -m venv .newton && .newton/bin/pip install "newton[importers]==1.8.0"
    .newton/bin/python scripts/newton_check.py run packs/   # writes packs/newton.json and .md

`generate` writes a small pack of every preset of the four generators and lists, in
packs/files.json, the Newton layer of each file (`<file>_newton.usda`, contract section 9) and
the mass the pack's table gives for it. On a commit CI runs a sample instead (FULL is not
"true"): of each generator, the preset the composed scene uses and one picked from the commit's
hash (GITHUB_SHA), the same pair each time the commit is run; every preset before a release.

`run` opens each layer in Newton with its XPBD solver (not MuJoCo Warp: the generators are
already checked with MuJoCo's algorithm) and Newton's own schema resolver only: what Newton
needs, the layer says (contact gaps, joint limits, articulations, cloth schemas); this script
sets nothing in their place. It checks:

- every file: Newton's total mass equals the pack's, to 1e-5 relative;
- grains and parts: after 2 simulated seconds every pose is finite, no centre of mass is below
  the ground and every body is at rest (below 5 cm/s). A part of the Quincaillerie catalogue is
  checked from its own file, which has no ground: it is dropped from 5 cm onto Newton's ground
  plane;
- cables: the cable is hung from its first segment and, after 1 s, every pose is finite and the
  cable has bent under its weight (its lowest point at least 5 mm below the support: a rigid
  cable does not move). Not "at rest": under XPBD the joint drives' damping has almost no
  effect, so a hung cable keeps swinging;
- cloth: every piece is raised 5 cm and, after 1 s, every particle is finite, at rest and not
  below the ground;
- a composed scene (`primvaria compose`, one pack of each generator, opened from its own Newton
  layer, which brings each asset's): its mass is the stage's, its cloth is read, and after 1 s
  every pose and particle is finite and nothing is below the ground.

Two comparisons are measured and reported, not failed on (they say how far Newton is, not
whether a file is right):

- a cable's bend against beam theory: a straight USB-C sample, cut at both ends and long
  enough to sag about 10 % of its length, held flat at one end; its tip drop (averaged over the
  second half of SAG_SECONDS) against w L^4 / (8 E I), with w and E I read back from the file as
  Filaire's own MuJoCo sag check reads them, at 5, 20 and 50 XPBD iterations (the bend depends
  on them);
- a cloth's drape against MuJoCo: Maillage's Cusick drape test (the piece laid on a round
  pedestal, the vertices over it held) on a 300-vertex napkin, its drape coefficient in Newton
  against the one Maillage's MuJoCo test measures on the same file. Newton's VBD solver, its
  cloth solver, is used here: under XPBD the cloth stretches without bound.

Exits 1 if a check fails. See docs/trials/newton-cpu.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path

DT = 1e-3
SECONDS = {"rigid": 2.0, "cable": 1.0, "cloth": 1.0, "scene": 1.0}
AT_REST = 0.05  # m/s
MASS = 1e-5  # relative
BENT = 0.005  # m: a hung cable's lowest point below its support
RAISE = 0.05  # m
SAG_SECONDS = 3.0
SAG_ITERATIONS = (5, 20, 50)
DRAPE_SECONDS = 5.0  # as Maillage's MuJoCo drape test
HANG = 5.0  # m: a hung cable is lifted so high that it cannot reach the ground


def pack_rows(folder: Path) -> list[dict]:
    with open(folder / "instances.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def layer(file: Path) -> str:
    """The Newton layer of a file (contract section 9)."""
    return str(file.with_name(f"{file.stem}_newton.usda"))


def sample(names: list[str], keep: str) -> list[str]:
    """Every name with FULL=true (CI before a release), else `keep` and one picked from the commit."""
    if os.environ.get("FULL") == "true":
        return names
    picked = int(os.environ.get("GITHUB_SHA", "0")[:8] or "0", 16) % len(names)
    return list(dict.fromkeys([keep, names[picked]]))


def generate(out: Path) -> None:
    """A small pack of every preset (or of a sample, see `sample`), and the list of what Newton opens."""
    import filaire
    import granulaire.presets
    import maillage.presets

    out.mkdir(parents=True, exist_ok=True)
    files = []

    def run(*args: str) -> None:
        subprocess.run([sys.executable, "-m", *args], check=True, stdout=subprocess.DEVNULL)

    for preset in sample(sorted(granulaire.presets.PRESETS), "crushed_gravel"):
        run("granulaire", "generate", "--preset", preset, "--shapes", "12", "--copies", "2",
            "--no-deformable", "--out", str(out / "granulaire"))  # fmt: skip
        folder = out / "granulaire" / preset
        rows = pack_rows(folder)
        files.append({
            "generator": "granulaire", "preset": preset, "kind": "rigid",
            "file": layer(folder / rows[0]["file"]),
            "mass_kg": sum(float(r["measured:mass_kg"]) for r in rows),
        })  # fmt: skip
    for preset in sample(sorted(maillage.presets.PRESETS), "napkin"):
        run("maillage", "generate", "--preset", preset, "--count", "1", "--out", str(out / "maillage"))
        folder = out / "maillage" / preset
        rows = pack_rows(folder)
        files.append({
            "generator": "maillage", "preset": preset, "kind": "cloth",
            "file": layer(folder / f"maillage_{preset}.usdc"),
            "mass_kg": sum(float(r["measured:mass_kg"]) for r in rows),
        })  # fmt: skip
    for preset in sample(sorted(filaire.PRESETS), "usb_c"):
        run("filaire", "generate", "--preset", preset, "--count", "1", "--out", str(out / "filaire"))
        folder = out / "filaire" / preset
        cables = [r for r in pack_rows(folder) if r["file"] == f"filaire_{preset}.usdc"]
        mass = sum(float(r[f"measured:{k}_mass_kg"]) for r in cables for k in ("cable", "end_a", "end_b"))
        files.append({
            "generator": "filaire", "preset": preset, "kind": "cable",
            "file": layer(folder / f"filaire_{preset}.usdc"), "mass_kg": mass,
        })  # fmt: skip
    run("quincaillerie", "generate", "all", "--count", "1", "--collider", "simple", "--out",
        str(out / "quincaillerie"))  # fmt: skip
    folder = out / "quincaillerie" / "catalog"
    parts = {r["name"]: r for r in pack_rows(folder)}
    for name in sample(list(parts), next(iter(parts))):  # each part on its own file, which has no ground
        r = parts[name]
        files.append({
            "generator": "quincaillerie", "preset": r["name"].removesuffix("_000"), "kind": "rigid",
            "file": layer(folder / r["file"]), "mass_kg": float(r["measured:mass_kg"]), "ground": False,
        })  # fmt: skip
    files.append(composed(out))
    (out / "files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    print(f"{len(files)} files listed in {out / 'files.json'}")
    (out / "compare.json").write_text(json.dumps(compare_inputs(out), indent=1), encoding="utf-8")


def composed(out: Path) -> dict:
    """One pack of each generator composed into one stage, with the stage's mass."""
    from pxr import UsdPhysics

    from primvaria.compose import compose, layer_path

    scene = out / "composed" / "scene.usda"
    picks = [out / "granulaire" / "crushed_gravel", out / "maillage" / "napkin", out / "filaire" / "usb_c",
             out / "quincaillerie" / "catalog" / "assets"]  # fmt: skip
    stage, assets = compose(scene, picks, limit=3)
    mass = 0.0
    for prim in stage.Traverse():
        if prim.HasAPI(UsdPhysics.RigidBodyAPI) and prim.HasAPI(UsdPhysics.MassAPI):
            mass += UsdPhysics.MassAPI(prim).GetMassAttr().Get() or 0.0
        if prim.HasAttribute("maillage:mass"):
            mass += prim.GetAttribute("maillage:mass").Get()
    return {"generator": "compose", "preset": f"{len(assets)} assets of the four generators", "kind": "scene",
            "file": str(layer_path(scene, "newton")), "mass_kg": mass}  # fmt: skip


def compare_inputs(out: Path) -> dict:
    """What the two comparisons need, read with the generators' own readers."""
    from filaire.sim.checks import G
    from filaire.sim.usd_reader import cable_paths, read_cable
    from maillage.sim.mujoco_test import PEDESTAL_FRACTION, PEDESTAL_HEIGHT
    from maillage.sim.mujoco_test import run as mujoco_drape
    from maillage.sim.usd_reader import read_pieces
    from pxr import Usd

    def straight(length: float, folder: Path):
        subprocess.run(
            [sys.executable, "-m", "filaire", "generate", "--preset", "usb_c", "--count", "1", "--layout",
             "straight", "--end-a", "cut", "--end-b", "cut", "--no-vary",
             "length,layout,ends,color,stiffness,density,clearance", "--length", f"{length:.4f}",
             "--out", str(folder)],
            check=True, stdout=subprocess.DEVNULL,
        )  # fmt: skip
        stage = Usd.Stage.Open(str(folder / "usb_c" / "filaire_usb_c.usdc"))
        cable = read_cable(stage, cable_paths(stage)[0])
        seg = cable.segments[0]
        piece = seg.capsule[1] if seg.capsule else seg.box[0]
        w, ei = seg.mass / piece * G, cable.joints[0].stiffness["rotY"] * piece
        length = sum(s.capsule[1] if s.capsule else s.box[0] for s in cable.segments)
        return w, ei, length

    w, ei, _ = straight(1.0, out / "compare" / "probe")
    w, ei, length = straight((0.8 * ei / w) ** (1 / 3), out / "compare" / "sag")  # tip drop ≈ 10 %
    subprocess.run(
        [sys.executable, "-m", "maillage", "generate", "--preset", "napkin", "--count", "1",
         "--vertices", "300", "--out", str(out / "compare")],
        check=True, stdout=subprocess.DEVNULL,
    )  # fmt: skip
    napkin = out / "compare" / "napkin"
    piece = read_pieces(napkin)[0]
    drape = mujoco_drape(napkin, pieces=1, seconds=DRAPE_SECONDS)["pieces"][0]["drape_coefficient"]
    return {
        "sag": {"file": layer(out / "compare" / "sag" / "usb_c" / "filaire_usb_c.usdc"), "w_n_m": w,
                "ei_nm2": ei, "length_m": length, "beam_m": w * length**4 / (8 * ei)},
        "drape": {"file": layer(napkin / "maillage_napkin.usdc"), "area_m2": piece.area,
                  "pedestal_height_m": PEDESTAL_HEIGHT, "pedestal_fraction": PEDESTAL_FRACTION,
                  "mujoco": drape},
    }  # fmt: skip


def _centres(model, state):
    """Centres of mass in the world: a part's origin may lie on its face (a nut's, a cell's base)."""
    import numpy as np

    poses = state.body_q.numpy()
    com, q = model.body_com.numpy(), poses[:, 3:7]  # quaternions x, y, z, w
    t = 2 * np.cross(q[:, :3], com)
    return poses[:, :3] + com + q[:, 3:4] * t + np.cross(q[:, :3], t)


def check(item: dict) -> dict:
    import numpy as np
    import warp as wp

    wp.config.quiet = True
    import newton
    import newton.usd

    wp.set_device("cpu")
    kind = item["kind"]
    part = newton.ModelBuilder()
    options = {"return_deformable_results": True, "schema_resolvers": [newton.usd.SchemaResolverNewton()]}
    if item.get("ground", True) is False:  # an asset file alone: dropped onto Newton's ground
        options["xform"] = wp.transform((0.0, 0.0, RAISE), wp.quat_identity())
    start = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        found = part.add_usd(item["file"], **options)
    mass = float(np.sum(part.body_mass)) + float(np.sum(part.particle_mass))
    r = {
        "generator": item["generator"],
        "preset": item["preset"],
        "import_s": round(time.time() - start, 1),
        "bodies": part.body_count,
        "joint_dofs": part.joint_dof_count,
        "cloths": len(found.get("path_cloth_map", {}) or {}),
        "particles": part.particle_count,
        "mass_kg": mass,
        "pack_mass_kg": item["mass_kg"],
        "failed": [],
    }
    if abs(mass - item["mass_kg"]) > MASS * item["mass_kg"]:
        r["failed"].append(f"mass {mass:.6g} kg, pack {item['mass_kg']:.6g} kg")
    if kind in ("cloth", "scene") and not r["cloths"]:
        r["failed"].append("no cloth read")
    builder = newton.ModelBuilder()  # the content in a world of its own (gravity is per world)
    if item.get("ground", True) is False:
        builder.add_ground_plane()
    builder.add_world(part)
    if kind == "cable":  # hung from its first segment, high above the ground: the segment no longer moves
        builder.body_q = [wp.transform(wp.vec3(t.p[0], t.p[1], t.p[2] + HANG), t.q) for t in builder.body_q]
        builder.body_mass[0], builder.body_inv_mass[0] = 0.0, 0.0
        builder.body_inertia[0], builder.body_inv_inertia[0] = wp.mat33(0.0), wp.mat33(0.0)
    if kind == "cloth":
        builder.particle_q = [(x, y, z + RAISE) for x, y, z in builder.particle_q]
    model = builder.finalize()
    solver = newton.solvers.SolverXPBD(model, iterations=20 if kind == "cable" else 10)
    state, other, control = model.state(), model.state(), model.control()
    pipeline = newton.CollisionPipeline(model)
    contacts = pipeline.contacts()
    support = float(state.body_q.numpy()[0, 2]) if kind == "cable" else 0.0
    start = time.time()
    for _ in range(round(SECONDS[kind] / DT)):
        state.clear_forces()
        pipeline.collide(state, contacts)
        solver.step(state, other, control, contacts, DT)
        state, other = other, state
    r["simulate_s"] = round(time.time() - start, 1)
    seconds = f"{SECONDS[kind]:g} s"
    if kind == "cloth":
        q, v = state.particle_q.numpy(), state.particle_qd.numpy()
        if not (np.isfinite(q).all() and np.isfinite(v).all()):
            r["failed"].append("non-finite particle")
        r["lowest_m"] = float(np.nanmin(q[:, 2]))
        r["fastest_m_s"] = float(np.nanmax(np.linalg.norm(v, axis=1)))
        if r["lowest_m"] < -1e-3:
            r["failed"].append(f"a particle {r['lowest_m']:.4g} m below the ground")
        if r["fastest_m_s"] > AT_REST:
            r["failed"].append(f"not at rest: {r['fastest_m_s']:.3g} m/s")
        drop = f"{RAISE * 100:g} cm"
        r["read"] = f"{r['cloths']} cloth, {r['particles']} particles; at rest after a {drop} drop"
        return r
    poses, speeds = state.body_q.numpy(), state.body_qd.numpy()
    if not (np.isfinite(poses).all() and np.isfinite(speeds).all()):
        r["failed"].append("non-finite pose or speed")
    if kind == "scene":
        q = state.particle_q.numpy()
        if not np.isfinite(q).all():
            r["failed"].append("non-finite particle")
        lowest = min(float(np.nanmin(_centres(model, state)[:, 2])), float(np.nanmin(q[:, 2])))
        if lowest < -1e-3:
            r["failed"].append(f"something {lowest:.4g} m below the ground")
        r["read"] = (
            f"{part.body_count} bodies, {r['cloths']} cloth, {part.joint_dof_count} degrees of freedom; "
            f"finite, above the ground after {seconds}"
        )
        return r
    r["fastest_m_s"] = float(np.nanmax(np.linalg.norm(speeds[:, :3], axis=1)))
    if kind == "cable":
        r["bent_m"] = support - float(np.nanmin(poses[:, 2]))
        if not r["bent_m"] >= BENT:
            r["failed"].append(f"hung from one end, it does not bend: {r['bent_m'] * 1e3:.1f} mm")
        r["read"] = (
            f"{part.joint_dof_count} degrees of freedom; hung from one end, bends {r['bent_m'] * 100:.0f} cm "
            f"in {seconds}"
        )
        return r
    r["lowest_centre_m"] = float(np.nanmin(_centres(model, state)[:, 2]))
    if r["lowest_centre_m"] < 0:
        r["failed"].append(f"a centre of mass {r['lowest_centre_m']:.4g} m below the ground")
    if r["fastest_m_s"] > AT_REST:
        r["failed"].append(f"not at rest: {r['fastest_m_s']:.3g} m/s")
    dofs = f"{part.joint_dof_count} degrees of freedom"
    r["read"] = f"{part.body_count} bodies, {dofs}; at rest after {seconds}"
    return r


def _load(path: str):
    """A file's Newton layer in a builder of its own, and the model builder holding it as world 0."""
    import warp as wp

    wp.config.quiet = True
    import newton
    import newton.usd

    wp.set_device("cpu")
    part = newton.ModelBuilder()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        part.add_usd(
            path, schema_resolvers=[newton.usd.SchemaResolverNewton()], return_deformable_results=True
        )
    builder = newton.ModelBuilder()
    builder.add_world(part)
    return builder


def sag(c: dict) -> dict:
    """The tip drop of a cable held flat at one end, against beam theory, at three XPBD iteration
    counts: Newton's XPBD does not carry its constraint multipliers across iterations, so a
    drive's effective stiffness grows with them."""
    import newton
    import numpy as np
    import warp as wp

    drops_mm = {}
    for iterations in SAG_ITERATIONS:
        b = _load(c["file"])
        b.body_q = [wp.transform(wp.vec3(t.p[0], t.p[1], t.p[2] + 1.0), t.q) for t in b.body_q]
        b.body_mass[0], b.body_inv_mass[0] = 0.0, 0.0
        b.body_inertia[0], b.body_inv_inertia[0] = wp.mat33(0.0), wp.mat33(0.0)
        model = b.finalize()
        solver = newton.solvers.SolverXPBD(model, iterations=iterations)
        state, other, control = model.state(), model.state(), model.control()
        start = state.body_q.numpy()[-1, 2]
        drops, steps = [], round(SAG_SECONDS / DT)
        for k in range(steps):
            state.clear_forces()
            solver.step(state, other, control, None, DT)
            state, other = other, state
            if k >= steps // 2:
                drops.append(start - state.body_q.numpy()[-1, 2])
        drops_mm[iterations] = round(float(np.mean(drops)) * 1e3, 1)
    beam_mm = c["beam_m"] * 1e3
    shown = ", ".join(f"{v} mm at {k}" for k, v in drops_mm.items())
    return {"what": "cable bend, USB-C sample held flat at one end", "solver": "XPBD",
            "newton": shown, "reference": round(beam_mm, 1), "unit": "XPBD iterations",
            "reference_is": "mm, beam theory w L^4 / (8 E I)",
            "ratio": ", ".join(f"{v / beam_mm:.2f}" for v in drops_mm.values())}  # fmt: skip


def hull_area(xy) -> float:
    """Area of the convex hull of points in the plane: the same measure as Maillage's drape test
    (maillage.sim.mujoco_test.hull_area), here because Maillage is not installed beside Newton."""
    import numpy as np

    pts = np.unique(np.round(xy, 9), axis=0)
    if len(pts) < 3:
        return 0.0
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def half(ps):
        h = []
        for p in ps:
            while (
                len(h) >= 2
                and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0
            ):
                h.pop()
            h.append(p)
        return h

    hull = np.array(half(pts)[:-1] + half(pts[::-1])[:-1])
    x, y = hull[:, 0], hull[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def drape(c: dict) -> dict:
    """Maillage's Cusick drape test in Newton, against its MuJoCo result on the same file."""
    import newton
    import numpy as np
    import warp as wp

    b = _load(c["file"])
    q = np.array(b.particle_q, float)
    lo, hi = q[:, :2].min(0), q[:, :2].max(0)
    centre, radius = (lo + hi) / 2, c["pedestal_fraction"] * (hi - lo).min() / 2
    h = c["pedestal_height_m"]
    b.particle_q = [(x - centre[0], y - centre[1], z - q[:, 2].min() + h + 0.002) for x, y, z in q]
    for i in np.flatnonzero(np.linalg.norm(q[:, :2] - centre, axis=1) <= radius):  # held, as in the tester
        b.particle_mass[i] = 0.0
    b.add_shape_cylinder(
        -1, xform=wp.transform((0, 0, h / 2), wp.quat_identity()), radius=radius, half_height=h / 2
    )
    b.color()
    model = b.finalize()
    solver = newton.solvers.SolverVBD(model)
    state, other, control = model.state(), model.state(), model.control()
    pipeline = newton.CollisionPipeline(model)
    contacts = pipeline.contacts()
    for _ in range(round(DRAPE_SECONDS / DT)):
        state.clear_forces()
        pipeline.collide(state, contacts)
        solver.step(state, other, control, contacts, DT)
        state, other = other, state
    p = state.particle_q.numpy()
    disc = np.pi * radius**2
    coefficient = (hull_area(p[:, :2]) - disc) / (c["area_m2"] - disc)
    return {"what": "cloth drape, napkin on a Cusick pedestal", "solver": "VBD",
            "newton": round(float(coefficient), 3), "reference": round(c["mujoco"], 3),
            "unit": "drape coefficient",
            "reference_is": "Maillage's MuJoCo drape test, same file",
            "ratio": round(float(coefficient) / c["mujoco"], 2)}  # fmt: skip


def run(folder: Path) -> int:
    import newton

    files = json.loads((folder / "files.json").read_text(encoding="utf-8"))
    results = []
    for item in files:
        try:
            results.append(check(item))
        except Exception as e:  # a file Newton cannot open is a result too
            results.append({"generator": item["generator"], "preset": item["preset"], "read": "",
                            "failed": [f"{type(e).__name__}: {e}"]})  # fmt: skip
        r = results[-1]
        outcome = "FAIL " + "; ".join(r["failed"]) if r["failed"] else r["read"]
        print(f"{r['generator']:14} {r['preset']:28} {outcome}", flush=True)
    compared = []
    inputs = json.loads((folder / "compare.json").read_text(encoding="utf-8"))
    for name, measure in (("sag", sag), ("drape", drape)):
        try:
            compared.append(measure(inputs[name]))
        except Exception as e:  # noqa: BLE001  (a measurement, not a check: report it and go on)
            compared.append({"what": name, "error": f"{type(e).__name__}: {e}"})
        print("compared:", json.dumps(compared[-1]), flush=True)
    report = {"newton": newton.__version__, "solver": "XPBD", "device": "cpu", "results": results,
              "compared": compared}  # fmt: skip
    (folder / "newton.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    lines = [
        f"Newton {newton.__version__}, XPBD on CPU, from each file's Newton layer.",
        "",
        "| Generator | Preset | Newton reads | Mass, Newton / pack (kg) | Result |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        mass = f"{r['mass_kg']:.6g} / {r['pack_mass_kg']:.6g}" if "mass_kg" in r else ""
        result = "FAIL: " + "; ".join(r["failed"]) if r["failed"] else "pass"
        lines.append(f"| {r['generator']} | {r['preset']} | {r.get('read', '')} | {mass} | {result} |")
    lines += ["", "| Compared | Solver | Newton | Reference | Ratio |", "|---|---|---|---|---|"]
    for c in compared:
        if "error" in c:
            lines.append(f"| {c['what']} | | {c['error']} | | |")
        else:
            lines.append(f"| {c['what']} | {c['solver']} | {c['newton']} {c['unit']} | {c['reference']} "
                         f"({c['reference_is']}) | {c['ratio']} |")  # fmt: skip
    (folder / "newton.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    failed = [r for r in results if r["failed"]]
    print(f"{len(results) - len(failed)} of {len(results)} pass")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=("generate", "run"))
    parser.add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    if args.step == "generate":
        generate(args.folder)
        return 0
    return run(args.folder)


if __name__ == "__main__":
    sys.exit(main())
