"""The SimReady report reads the validator's results; the validator itself runs in CI."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("simready_check", ROOT / "scripts" / "simready_check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def test_engine_layers_and_material_libraries_are_left_out(tmp_path):
    for name in ("a/x.usdc", "a/x_newton.usda", "a/x_physx.usda", "b/materials/lib.usda", "b/y.usda"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("#usda 1.0\n")
    assert [f.relative_to(tmp_path).as_posix() for f in check.main_files([tmp_path])] == [
        "a/x.usdc",
        "b/y.usda",
    ]


def test_only_blocking_requirements_are_reported():
    summary = {
        "CAP000": {
            "blocking_failure": True,
            "failing requirements": "['NP.005']",
            "requirement_messages": json.dumps({"NP.005": ["Exactly one USD file. Found 2"]}),
        },
        "FET005": {"blocking_failure": False, "failing requirements": "['GSP.001']"},
    }
    assert check.blocking(summary) == {"NP.005": "Exactly one USD file"}


def test_the_report_counts_files_per_requirement():
    results = {"granulaire": [(Path("a.usdc"), {"NP.005": "one file"}), (Path("b.usdc"), {})]}
    text = check.report(results, "Robotics-Prop", "5.0.0")
    assert "1 of 2 files meet the profile" in text and "| `NP.005` | 1 | one file |" in text
