"""The guard that keeps the generators' shared files identical."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "check_shared_files", Path(__file__).parents[1] / "scripts" / "check_shared_files.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def _tree(root: Path, changed: str | None = None, missing: str | None = None) -> Path:
    for name in guard.GENERATORS:
        for pattern in guard.SHARED:
            if name == missing and pattern.endswith("contract.py"):
                continue
            f = root / name / pattern.format(name=name)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("x = 2\n" if name == changed and pattern.endswith("ground.py") else "x = 1\n")
    return root


def test_identical_files_pass(tmp_path, capsys):
    assert guard.main(["--local", str(_tree(tmp_path))]) == 0
    assert capsys.readouterr().out.count("identical in the four generators") == len(guard.SHARED)


def test_a_changed_file_fails(tmp_path, capsys):
    assert guard.main(["--local", str(_tree(tmp_path, changed="filaire"))]) == 1
    assert "ground.py: differs" in capsys.readouterr().out


def test_a_missing_file_fails(tmp_path, capsys):
    assert guard.main(["--local", str(_tree(tmp_path, missing="maillage"))]) == 1
    assert "contract.py: missing in maillage" in capsys.readouterr().out


def test_line_endings_are_not_drift():
    same = dict.fromkeys(guard.GENERATORS, b"a\nb\n") | {"filaire": b"a\r\nb\r\n"}
    assert guard.drift(same) == []
