"""Newton on CPU as an engine of the matrix: every preset's Newton layer, opened and checked.

Two steps, in two environments, because Newton pins its own usd-core and MuJoCo:

    python scripts/newton_check.py generate packs/          # with primvaria and the generators
    python -m venv .newton && .newton/bin/pip install "newton[importers]==1.8.0"
    .newton/bin/python scripts/newton_check.py run packs/   # writes packs/newton.json and .md

`generate` writes a small pack of every preset of the four generators and lists, in
packs/files.json, the Newton layer of each file (`<file>_newton.usda`, contract section 9) and
the mass the pack's table gives for it.

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
  below the ground.

Exits 1 if a check fails. See docs/trials/newton-cpu.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path

DT = 1e-3
SECONDS = {"rigid": 2.0, "cable": 1.0, "cloth": 1.0}
AT_REST = 0.05  # m/s
MASS = 1e-5  # relative
BENT = 0.005  # m: a hung cable's lowest point below its support
RAISE = 0.05  # m
HANG = 5.0  # m: a hung cable is lifted so high that it cannot reach the ground


def pack_rows(folder: Path) -> list[dict]:
    with open(folder / "instances.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def layer(file: Path) -> str:
    """The Newton layer of a file (contract section 9)."""
    return str(file.with_name(f"{file.stem}_newton.usda"))


def generate(out: Path) -> None:
    """A small pack of every preset, and the list of what Newton opens."""
    import filaire
    import granulaire.presets
    import maillage.presets

    out.mkdir(parents=True, exist_ok=True)
    files = []

    def run(*args: str) -> None:
        subprocess.run([sys.executable, "-m", *args], check=True, stdout=subprocess.DEVNULL)

    for preset in sorted(granulaire.presets.PRESETS):
        run("granulaire", "generate", "--preset", preset, "--shapes", "12", "--copies", "2",
            "--no-deformable", "--out", str(out / "granulaire"))  # fmt: skip
        folder = out / "granulaire" / preset
        rows = pack_rows(folder)
        files.append({
            "generator": "granulaire", "preset": preset, "kind": "rigid",
            "file": layer(folder / rows[0]["file"]),
            "mass_kg": sum(float(r["measured:mass_kg"]) for r in rows),
        })  # fmt: skip
    for preset in sorted(maillage.presets.PRESETS):
        run("maillage", "generate", "--preset", preset, "--count", "1", "--out", str(out / "maillage"))
        folder = out / "maillage" / preset
        rows = pack_rows(folder)
        files.append({
            "generator": "maillage", "preset": preset, "kind": "cloth",
            "file": layer(folder / f"maillage_{preset}.usdc"),
            "mass_kg": sum(float(r["measured:mass_kg"]) for r in rows),
        })  # fmt: skip
    for preset in sorted(filaire.PRESETS):
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
    for r in pack_rows(folder):  # each part on its own file, which has no ground
        files.append({
            "generator": "quincaillerie", "preset": r["name"].removesuffix("_000"), "kind": "rigid",
            "file": layer(folder / r["file"]), "mass_kg": float(r["measured:mass_kg"]), "ground": False,
        })  # fmt: skip
    (out / "files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    print(f"{len(files)} files listed in {out / 'files.json'}")


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
    if kind == "cloth" and not r["cloths"]:
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
    report = {"newton": newton.__version__, "solver": "XPBD", "device": "cpu", "results": results}
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
