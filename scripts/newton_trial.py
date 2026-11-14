"""Trial (PRV-30): open a Primvaria file in Newton on CPU and let it settle.

Not part of the test suite. Newton's MuJoCo extra pins another MuJoCo than the
generators use, so run this in its own environment:

    python -m venv .newton && .newton/bin/pip install "newton[importers]"
    .newton/bin/python scripts/newton_trial.py scene_physx.usda --physx --seconds 1

The solver is XPBD, not MuJoCo Warp, so that the result is a second opinion.
The report is docs/trials/newton-cpu.md.
"""

import argparse
import json
import time
import warnings

import numpy as np
import warp as wp

wp.config.quiet = True

import newton  # noqa: E402
import newton.usd  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", help="a file written by a generator, or its engine layer")
    parser.add_argument("--seconds", type=float, default=1.0, help="simulated time (0: import only)")
    parser.add_argument("--dt", type=float, default=1e-3)
    parser.add_argument("--gap", type=float, help="contact gap in metres, every shape (default 0.1)")
    parser.add_argument("--physx", action="store_true", help="read the gap from a PhysX layer")
    args = parser.parse_args()

    wp.set_device("cpu")
    builder = newton.ModelBuilder()
    options = {"return_deformable_results": True}
    if args.gap is not None:
        builder.rigid_gap = args.gap
        builder.default_shape_cfg.gap = args.gap
    if args.physx:
        options["schema_resolvers"] = [newton.usd.SchemaResolverNewton(), newton.usd.SchemaResolverPhysx()]
    start = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        found = builder.add_usd(args.file, **options)
    report = {
        "file": args.file,
        "newton": newton.__version__,
        "solver": "XPBD",
        "device": "cpu",
        "import_s": round(time.time() - start, 1),
        "bodies": builder.body_count,
        "joints": builder.joint_count,
        "shapes": builder.shape_count,
        "cloths": len(found.get("path_cloth_map", {})),
        "particles": builder.particle_count,
        "mass_kg": round(float(sum(builder.body_mass)) + float(sum(builder.particle_mass)), 6),
    }
    if args.seconds > 0 and builder.body_count:
        model = builder.finalize()
        solver = newton.solvers.SolverXPBD(model, iterations=10)
        state, other, control = model.state(), model.state(), model.control()
        pipeline = newton.CollisionPipeline(model)
        contacts = pipeline.contacts()
        pipeline.collide(state, contacts)
        report["contacts_at_start"] = int(contacts.rigid_contact_count.numpy()[0])
        report["contact_capacity"] = int(contacts.rigid_contact_max)
        start = time.time()
        for _ in range(round(args.seconds / args.dt)):
            state.clear_forces()
            pipeline.collide(state, contacts)
            solver.step(state, other, control, contacts, args.dt)
            state, other = other, state
        poses, speeds = state.body_q.numpy(), state.body_qd.numpy()
        report |= {
            "simulated_s": args.seconds,
            "wall_s": round(time.time() - start, 1),
            "finite": bool(np.isfinite(poses).all() and np.isfinite(speeds).all()),
            "lowest_origin_m": round(float(np.nanmin(poses[:, 2])), 5),
            "max_linear_speed_m_s": round(float(np.nanmax(np.abs(speeds[:, :3]))), 5),
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
