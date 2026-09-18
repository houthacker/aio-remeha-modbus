"""API model tests."""

from datetime import time

import pytest
from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.api.appliance import Appliance


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
