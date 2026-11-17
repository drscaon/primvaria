"""The four generators look like one suite (PRV-35).

Their command lines and their pack files, with the generators installed (CI installs their main
branches); their repositories are checked by scripts/check_consistency.py. A difference fails
unless INTENDED says why it is there.
"""

import csv
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "check_consistency", Path(__file__).parents[1] / "scripts" / "check_consistency.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

GENERATORS = guard.GENERATORS
# a small pack of each, for the checks that read one
SMALL = {
    "granulaire": ["generate", "--preset", "beach_sand", "--shapes", "2", "--copies", "1"],
    "maillage": ["generate", "--preset", "tea_towel", "--count", "1"],
    "filaire": ["generate", "--preset", "usb_c", "--count", "1"],
    "quincaillerie": ["generate", "washer", "M8", "--count", "1"],
}
# subcommands and generate options every generator has
SUBCOMMANDS = {"list", "generate", "sim-test"}
OPTIONS = {"--seed", "--out", "--no-vary", "--nominal"}
# differences that are meant: (generator, what) -> why
INTENDED = {
    ("granulaire", "--count"): "a grain pack is --shapes distinct shapes times --copies copies",
    ("quincaillerie", "--preset"): "a part is named by kind and size (screw M8), not by a preset",
}


def run(name, *args):
    return subprocess.run([sys.executable, "-m", name, *args], capture_output=True, text=True)


def options(name, *command):
    return set(re.findall(r"(--[a-z][a-z0-9-]*)", run(name, *command, "--help").stdout))


@pytest.mark.parametrize("name", GENERATORS)
def test_version(name):
    out = run(name, "--version")
    assert out.returncode == 0 and re.fullmatch(rf"{name} \d+\.\d+\.\d+\S*", out.stdout.strip()), out.stdout


@pytest.mark.parametrize("name", GENERATORS)
def test_common_subcommands_and_options(name):
    listed = re.search(r"\{([a-z,-]+)\}", run(name, "--help").stdout)
    assert listed and SUBCOMMANDS <= set(listed.group(1).split(",")), f"{name}: {listed and listed.group(1)}"
    have = options(name, "generate")
    for option in OPTIONS | {"--count", "--preset"}:
        if (name, option) not in INTENDED:
            assert option in have, f"{name} generate has no {option}"


@pytest.mark.parametrize("name", GENERATORS)
def test_errors_exit_with_2(name, tmp_path):
    assert run(name, "nope").returncode == 2, f"{name}: an unknown subcommand"
    bad = run(name, *SMALL[name], "--no-vary", "nope", "--out", str(tmp_path))
    assert bad.returncode == 2 and "unknown aspect nope" in bad.stderr, f"{name}: an unknown aspect"


@pytest.fixture(scope="module")
def packs(tmp_path_factory):
    found = {}
    for name in GENERATORS:
        out = tmp_path_factory.mktemp(name)
        assert run(name, *SMALL[name], "--seed", "3", "--out", str(out)).returncode == 0, name
        (table,) = out.rglob("instances.csv")
        with table.open(newline="", encoding="utf-8") as f:
            header = next(csv.reader(f))
        found[name] = (header, json.loads(table.with_name("manifest.json").read_text(encoding="utf-8")))
    return found


def test_the_pack_tables_start_alike(packs):
    first = {name: header[: header.index("classes") + 1] for name, (header, _) in packs.items()}
    assert len({tuple(v) for v in first.values()}) == 1, first
    for name, (header, _) in packs.items():
        rest = header[len(first[name]) :]
        order = [c.split(":")[0] for c in rest if ":" in c]
        assert order == sorted(order, key=["variation", "measured"].index), f"{name}: {rest[:6]}"


def test_the_manifests_have_the_same_keys(packs):
    keys = {name: set(manifest) for name, (_, manifest) in packs.items()}
    common = set.intersection(*keys.values())
    for name, have in keys.items():
        assert have == common, f"{name} has {sorted(have - common)} the others do not"


def _tree(root: Path, extra: str | None = None) -> Path:
    for name in GENERATORS:
        base = root / name
        for page in guard.PAGES:
            (base / "docs").mkdir(parents=True, exist_ok=True)
            (base / "docs" / f"{page}.md").write_text("x\n")
        pages = [*guard.PAGES] + ([extra] if extra and name == "filaire" else [])
        if extra and name == "filaire":
            (base / "docs" / f"{extra}.md").write_text("x\n")
        rows = "\n".join(f"| [{p}](docs/{p}.md) | |" for p in pages)
        (base / "README.md").write_text(f"# {name}\n\n## Documentation\n\n| Page | |\n|---|---|\n{rows}\n")
        (base / "examples").mkdir()
        for start in guard.EXAMPLES:
            (base / "examples" / f"{start.rstrip('_')}_x.py").write_text("")
        (base / "CHANGELOG.md").write_text("## [Unreleased]\n")
    return root


def test_the_repository_check_passes_alike_repositories(tmp_path, capsys):
    assert guard.main(["--local", str(_tree(tmp_path))]) == 0
    assert capsys.readouterr().out.count("consistent with the suite") == len(GENERATORS)


def test_the_repository_check_refuses_an_unexplained_page(tmp_path, capsys):
    assert guard.main(["--local", str(_tree(tmp_path, extra="notes"))]) == 1
    assert "docs/notes.md is a page the other generators do not have" in capsys.readouterr().out
