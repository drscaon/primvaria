import pytest

from primvaria import MEMBERS, __version__, get_member
from primvaria.cli import main


def test_four_members():
    assert [m.name for m in MEMBERS] == ["granulaire", "maillage", "filaire", "quincaillerie"]


def test_unknown_member():
    with pytest.raises(KeyError, match="known: granulaire"):
        get_member("sable")


def test_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"primvaria {__version__}"


def test_help(capsys):
    assert main([]) == 0
    assert "primvaria list" in capsys.readouterr().out


def test_list_shows_every_member(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    for m in MEMBERS:
        assert m.name in out


def test_unknown_command(capsys):
    assert main(["sable"]) == 2
    assert "unknown generator" in capsys.readouterr().err


@pytest.mark.parametrize("member", MEMBERS, ids=lambda m: m.name)
def test_dispatch_to_member(member, capsys):
    if member.installed_version is None:
        pytest.skip(f"{member.name} not installed")
    with pytest.raises(SystemExit) as exc:
        main([member.name, "--version"])
    assert exc.value.code == 0
    assert member.installed_version in capsys.readouterr().out
