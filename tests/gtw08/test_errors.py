"""Tests for the API errors."""

import pytest

from aio_remeha_modbus.gtw08.errors import (
    AutoSchedulingError,
    DiscoveryTableCorruptedError,
    InvalidZoneSchedule,
    RemehaApiError,
    RemehaModbusError,
)


def test_remeha_api_error_translation():
    """Test that the translation key and placeholders are stored."""

    error = RemehaApiError("some_key", {"count": 3, "name": "zone"})

    assert error.translation_key == "some_key"
    assert error.translation_placeholders == {"count": 3, "name": "zone"}


def test_remeha_api_error_default_placeholders():
    """Test that an error without placeholders has an empty placeholder dict."""

    assert RemehaApiError("some_key").translation_placeholders == {}


def test_remeha_api_error_keyword_arguments():
    """Test that the error can be created with keyword arguments."""

    error = AutoSchedulingError(
        translation_key="auto_schedule_no_forecasts", translation_placeholders={"a": "b"}
    )

    assert error.translation_key == "auto_schedule_no_forecasts"
    assert error.translation_placeholders == {"a": "b"}


@pytest.mark.parametrize(
    "error_class",
    [RemehaModbusError, AutoSchedulingError, DiscoveryTableCorruptedError, InvalidZoneSchedule],
)
def test_error_hierarchy(error_class: type[RemehaApiError]):
    """Test that every API error can be caught as a `RemehaApiError`."""

    with pytest.raises(RemehaApiError) as exc_info:
        raise error_class("some_key")

    assert type(exc_info.value) is error_class
    assert exc_info.value.translation_key == "some_key"


def test_discovery_table_corrupted_is_modbus_error():
    """Test that a corrupted discovery table is a modbus error."""

    assert issubclass(DiscoveryTableCorruptedError, RemehaModbusError)
