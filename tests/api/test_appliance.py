"""Tests for the appliance."""

from datetime import time

import pytest
from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.api.appliance import Appliance, CoolingType, SeasonalMode, SilentMode


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_appliance(remeha_modbus_unit: MockModbusUnit):
    """Test that an Appliance is read correctly."""

    appliance = Appliance(remeha_modbus_unit)
    await appliance.async_update()

    assert appliance.outside_temperature == 24.82
    assert appliance.season_mode == SeasonalMode.SUMMER
    assert appliance.summer_winter == 22.0
    assert appliance.neutral_band_summer_winter == 4.0
    assert not appliance.forced_summer_mode
    assert appliance.silent_mode == SilentMode.LEVEL_1
    assert appliance.silent_mode_start_time == time(22, 0)
    assert appliance.silent_mode_end_time == time(7, 0)
    assert appliance.ch_enabled
    assert appliance.cooling_type == CoolingType.ACTIVE_COOLING
    assert not appliance.forced_cooling_mode
