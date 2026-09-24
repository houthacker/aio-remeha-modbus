"""Test validation helper."""

import re

import pytest

from aio_remeha_modbus.helpers import validation


def test_require_not_none():
    """Test the require_not_none method."""

    assert validation.require_not_none("test") == "test"

    with pytest.raises(expected_exception=ValueError, match="Require a value, but got None"):
        validation.require_not_none(None)

    with pytest.raises(expected_exception=ValueError, match="Custom error message"):
        validation.require_not_none(None, "Custom error message")


def test_in_range():
    """Test the in_range validator."""

    r = range(1, 3)

    assert validation.in_range(r)(1) == 1
    assert validation.in_range(r)(2) == 2

    with pytest.raises(
        expected_exception=ValueError, match=re.escape("Value 3 not in range(1, 3) (exclusive)")
    ):
        validation.in_range(r)(3)

    with pytest.raises(
        expected_exception=ValueError, match=re.escape("Value 0 not in range(1, 3) (exclusive)")
    ):
        validation.in_range(r)(0)
