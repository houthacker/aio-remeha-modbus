"""API model tests."""

from datetime import time

import pytest
from modbus_connection.exceptions import IllegalFunctionError
from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.gtw08.appliance import Appliance


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_component_write(remeha_modbus_unit: MockModbusUnit):
    """Test that a field value is returned after a successful write."""

    appliance = Appliance(remeha_modbus_unit)
    await appliance.async_update()

    expected = time(hour=23)
    assert appliance.silent_mode_start_time != expected

    # Write a value
    await appliance.async_set_silent_mode_start_time(expected)

    # RemehaComponent retains the written value so it must be returned
    # when queried.
    assert appliance.silent_mode_start_time == expected

    # After an update, it also must have this value.
    await appliance.async_update()
    assert appliance.silent_mode_start_time == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_component_failed_write_is_not_retained(remeha_modbus_unit: MockModbusUnit):
    """Test that a value is not retained if writing it failed."""

    appliance = Appliance(remeha_modbus_unit)
    await appliance.async_update()

    original = appliance.silent_mode_start_time
    remeha_modbus_unit.fail_write(491, IllegalFunctionError(exception_code=0x01))

    with pytest.raises(IllegalFunctionError):
        await appliance.async_set_silent_mode_start_time(time(hour=23))

    assert appliance.silent_mode_start_time == original


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_component_write_read_only_field(remeha_modbus_unit: MockModbusUnit):
    """Test that writing a read-only field is refused and not retained."""

    appliance = Appliance(remeha_modbus_unit)
    await appliance.async_update()
    original = appliance.outside_temperature

    with pytest.raises(AttributeError):
        await appliance.write("outside_temperature", 1.0)

    assert appliance.outside_temperature == original


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_component_write_unknown_field(remeha_modbus_unit: MockModbusUnit):
    """Test that writing an unknown field is refused."""

    appliance = Appliance(remeha_modbus_unit)
    await appliance.async_update()

    with pytest.raises(AttributeError):
        await appliance.write("does_not_exist", 1)
