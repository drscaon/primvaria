"""The shared tests are importable, and find the generator whose tests import them."""

import importlib

import pytest

from primvaria_contract.testing import find_generator


@pytest.mark.parametrize("module", ["contract", "pack", "golden"])
def test_each_module_imports_and_has_tests(module):
    found = importlib.import_module(f"primvaria_contract.testing.{module}")
    assert any(name.startswith("test_") for name in vars(found))


def test_the_generator_is_the_package_with_a_contract(tmp_path):
    (tmp_path / "src" / "notes").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    with pytest.raises(LookupError, match="no single generator"):
        find_generator(tmp_path / "tests" / "test_contract.py")
