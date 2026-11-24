"""Newton on CPU as a third engine (PRV-30): what Newton reads of every preset, checked.

Two steps, in two environments, because Newton pins its own usd-core and MuJoCo:

    python scripts/newton_check.py generate packs/          # with primvaria and the generators
    python -m venv .newton && .newton/bin/pip install "newton[importers]==1.8.0"
    .newton/bin/python scripts/newton_check.py run packs/   # writes packs/newton.json and .md

`generate` writes a small pack of every preset of the four generators and lists, in
packs/files.json, the file Newton opens and the mass the pack's table gives for it.

`run` opens each file in Newton with its XPBD solver (not MuJoCo Warp: the generators are
already checked with MuJoCo's algorithm) and checks what Newton reads:

- every rigid file: Newton's total mass equals the pack's, to 1e-5 relative;
- grains and fasteners: after 2 simulated seconds every pose is finite, no centre of mass is below
  the ground and every body is at rest (below 5 cm/s, Newton's XPBD is noisier at rest than
  MuJoCo);
- cables: the mass is checked and the joints' degrees of freedom are recorded, not settled:
  Newton 1.8.0 gives a generic joint a degree of freedom only on an axis with a limit, so a
  Filaire cable, whose rotations are free, comes out rigid. That is Newton's reading of the file;
- battery holders: Newton 1.8.0 refuses a joint outside an articulation, which UsdPhysics
  allows; the holders' clip and spring joints are such joints, so the refusal is recorded;
- cloth: what Newton reads is recorded. Newton 1.8.0 reads the AOUSD proposal's deformable
  schemas, not the OmniPhysics ones Maillage writes, so it finds no cloth.

A part of the Quincaillerie catalogue is checked from its own file, which has no ground: it is
dropped from 5 cm onto Newton's ground plane. The contact gap comes from the PhysX layer where
there is one (Quincaillerie, Filaire), and otherwise is a quarter of the pack's smallest grain,
at most 0.5 mm: Newton's default, 0.1 m, is for robots and floods the contact buffer with parts
this small. See docs/trials/newton-cpu.md.
Exits 1 if a check fails.
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

SECONDS, DT = 2.0, 1e-3
# what Newton 1.8.0 refuses in files that follow UsdPhysics: recorded, not failed
REFUSED = {"not belonging to any articulation": "refused: joints outside an articulation"}
AT_REST = 0.05  # m/s
MASS = 1e-5  # relative


def pack_rows(folder: Path) -> list[dict]:
    with open(folder / "instances.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
            "file": str(folder / rows[0]["file"]),
            "mass_kg": sum(float(r["measured:mass_kg"]) for r in rows),
            "gap_m": min(5e-4, min(float(r["measured:diameter_nominal_m"]) for r in rows) / 4),
        })  # fmt: skip
    for preset in sorted(maillage.presets.PRESETS):
        run("maillage", "generate", "--preset", preset, "--count", "2", "--out", str(out / "maillage"))
        folder = out / "maillage" / preset
        rows = pack_rows(folder)
        files.append({
            "generator": "maillage", "preset": preset, "kind": "cloth",
            "file": str(folder / f"maillage_{preset}_omniphysics.usda"),
            "mass_kg": sum(float(r["measured:mass_kg"]) for r in rows),
        })  # fmt: skip
    for preset in sorted(filaire.PRESETS):
        run("filaire", "generate", "--preset", preset, "--count", "1", "--out", str(out / "filaire"))
        folder = out / "filaire" / preset
        cables = [r for r in pack_rows(folder) if r["file"] == f"filaire_{preset}.usdc"]
        mass = sum(float(r[f"measured:{k}_mass_kg"]) for r in cables for k in ("cable", "end_a", "end_b"))
        files.append({
            "generator": "filaire", "preset": preset, "kind": "cable",
            "file": str(folder / f"filaire_{preset}_physx.usda"), "mass_kg": mass,
        })  # fmt: skip
    run("quincaillerie", "generate", "all", "--count", "1", "--collider", "simple", "--out",
        str(out / "quincaillerie"))  # fmt: skip
    folder = out / "quincaillerie" / "catalog"
    for r in pack_rows(folder):  # each part on its own; battery holders are fixed, without a mass
        files.append({
            "generator": "quincaillerie", "preset": r["name"].removesuffix("_000"), "kind": "rigid",
            "file": str(folder / r["file"].replace(".usda", "_physx.usda")),
            "mass_kg": float(r["measured:mass_kg"] or 0), "ground": False,
        })  # fmt: skip
    (out / "files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    print(f"{len(files)} files listed in {out / 'files.json'}")


def check(item: dict) -> dict:
    import numpy as np
    import warp as wp

    wp.config.quiet = True
    import newton
    import newton.usd

    wp.set_device("cpu")
    builder = newton.ModelBuilder()
    options = {"return_deformable_results": True}
    if "gap_m" in item:
        builder.rigid_gap = item["gap_m"]
        builder.default_shape_cfg.gap = item["gap_m"]
    else:
        options["schema_resolvers"] = [newton.usd.SchemaResolverNewton(), newton.usd.SchemaResolverPhysx()]
    if item.get("ground", True) is False:  # an asset file alone: Newton's ground, the part 5 cm above it
        builder.add_ground_plane()
        options["xform"] = wp.transform((0.0, 0.0, 0.05), wp.quat_identity())
    start = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        found = builder.add_usd(item["file"], **options)
    mass = float(np.sum(builder.body_mass)) + float(np.sum(builder.particle_mass))
    r = {
        "generator": item["generator"],
        "preset": item["preset"],
        "import_s": round(time.time() - start, 1),
        "bodies": builder.body_count,
        "joint_dofs": builder.joint_dof_count,
        "cloths": len(found.get("path_cloth_map", {}) or {}),
        "mass_kg": mass,
        "pack_mass_kg": item["mass_kg"],
        "failed": [],
    }
    if item["kind"] == "cloth":
        r["read"] = f"{r['cloths']} cloths"
        return r
    if abs(mass - item["mass_kg"]) > MASS * item["mass_kg"]:
        r["failed"].append(f"mass {mass:.6g} kg, pack {item['mass_kg']:.6g} kg")
    if item["kind"] == "cable":
        r["read"] = f"{builder.joint_count} joints, {builder.joint_dof_count} degrees of freedom"
        return r
    model = builder.finalize()
    solver = newton.solvers.SolverXPBD(model, iterations=10)
    state, other, control = model.state(), model.state(), model.control()
    pipeline = newton.CollisionPipeline(model)
    contacts = pipeline.contacts()
    start = time.time()
    for _ in range(round(SECONDS / DT)):
        state.clear_forces()
        pipeline.collide(state, contacts)
        solver.step(state, other, control, contacts, DT)
        state, other = other, state
    poses, speeds = state.body_q.numpy(), state.body_qd.numpy()
    r["settle_s"] = round(time.time() - start, 1)
    finite = bool(np.isfinite(poses).all() and np.isfinite(speeds).all())
    # centre of mass in the world: a part's origin may lie on its face (a nut's, a cell's base)
    com, q = model.body_com.numpy(), poses[:, 3:7]  # quaternions x, y, z, w
    t = 2 * np.cross(q[:, :3], com)
    centres = poses[:, :3] + com + q[:, 3:4] * t + np.cross(q[:, :3], t)
    r["lowest_centre_m"] = float(np.nanmin(centres[:, 2]))
    r["fastest_m_s"] = float(np.nanmax(np.linalg.norm(speeds[:, :3], axis=1)))
    if not finite:
        r["failed"].append("non-finite pose or speed")
    if r["lowest_centre_m"] < 0:
        r["failed"].append(f"a centre of mass {r['lowest_centre_m']:.4g} m below the ground")
    if r["fastest_m_s"] > AT_REST:
        r["failed"].append(f"not at rest: {r['fastest_m_s']:.3g} m/s")
    r["read"] = f"{r['bodies']} bodies, at rest after {SECONDS:g} s" if not r["failed"] else ""
    return r


def run(folder: Path) -> int:
    import newton

    files = json.loads((folder / "files.json").read_text(encoding="utf-8"))
    results = []
    for item in files:
        try:
            results.append(check(item))
        except Exception as e:  # a file Newton cannot open is a result too
            known = [v for k, v in REFUSED.items() if k in str(e)]
            results.append({"generator": item["generator"], "preset": item["preset"],
                            "read": known[0] if known else "",
                            "failed": [] if known else [f"{type(e).__name__}: {e}"]})  # fmt: skip
        r = results[-1]
        outcome = "FAIL " + "; ".join(r["failed"]) if r["failed"] else r["read"]
        print(f"{r['generator']:14} {r['preset']:28} {outcome}", flush=True)
    report = {"newton": newton.__version__, "solver": "XPBD", "device": "cpu", "results": results}
    (folder / "newton.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    lines = [
        f"Newton {newton.__version__}, XPBD on CPU.",
        "",
        "| Generator | Preset | Newton reads | Mass, Newton / pack (kg) | Result |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        mass = f"{r['mass_kg']:.6g} / {r['pack_mass_kg']:.6g}" if "mass_kg" in r else ""
        lines.append(f"| {r['generator']} | {r['preset']} | {r.get('read', '')} | {mass} | "
                     f"{'FAIL: ' + '; '.join(r['failed']) if r['failed'] else 'pass'} |")  # fmt: skip
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
