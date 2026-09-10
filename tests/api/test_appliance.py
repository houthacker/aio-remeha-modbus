"""Tests for the appliance."""

from datetime import time

import pytest
from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.api.appliance import (
    Appliance,
    ApplianceStatus,
    ApplianceSubStatus,
    CoolingType,
    SeasonalMode,
    SilentMode,
)


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
    assert appliance.flow_temperature == 20.44
    assert appliance.return_temperature == 20.0
    assert appliance.heat_pump_flow_temperature == 21.14
    assert appliance.heat_pump_return_temperature == 22.54
    assert appliance.actual_water_pressure == 1.2
    assert appliance.flow_rate == 12.66
    assert appliance.status == ApplianceStatus.manual_heat_demand
    assert appliance.substatus == ApplianceSubStatus.power_controlled
    assert appliance.actual_relative_power == 0.5
    assert appliance.generator_starts_total == 1234
    assert appliance.backup1_starts == 321
    assert appliance.backup1_hours == 456
    assert appliance.backup2_starts == 100
    assert appliance.backup2_hours == 200
    assert appliance.power_on_hours == 10_000
    assert appliance.ch_energy_consumption == 5_000
    assert appliance.dhw_energy_consumption == 3000
    assert appliance.cooling_energy_consumption == 500
    assert appliance.backup_energy_consumption == 4000
    assert appliance.total_energy_consumption == 0
    assert appliance.total_energy_delivery == 0
    assert appliance.total_energy_delivery == 0
    assert appliance.ch_energy_delivery == 2200
    assert appliance.dhw_energy_delivery == 3500
    assert appliance.cooling_energy_delivery == 0
    assert appliance.backup_energy_delivery == 0
    assert appliance.pump_speed == 5.0
    assert appliance.actual_produced_power == 57
    assert appliance.cop_calculated == 3.2
    assert appliance.silent_mode == SilentMode.LEVEL_1
    assert appliance.silent_mode_start_time == time(22, 0)
    assert appliance.silent_mode_end_time == time(7, 0)
    assert appliance.ch_enabled
    assert appliance.cooling_type == CoolingType.ACTIVE_COOLING
    assert not appliance.forced_cooling_mode
    assert appliance.hybrid_cop_calculated == 3.5
