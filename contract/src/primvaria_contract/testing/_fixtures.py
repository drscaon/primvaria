"""The ``generator`` fixture, imported by each module of tests."""

import pytest

from . import find_generator


@pytest.fixture(scope="module")
def generator(request):
    """The generator under test: name, package and its contract, conformance and pack modules."""
    return find_generator(request.module.__file__)
