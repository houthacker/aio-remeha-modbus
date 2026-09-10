"""Tests for RemehaApi."""

from datetime import time

import pytest

from aio_remeha_modbus.api.api import RemehaApi
from aio_remeha_modbus.api.appliance import (
    Appliance,
    CoolingType,
    SilentMode,
)
from aio_remeha_modbus.api.climate_zone import (
    ClimateZone,
    ClimateZoneFunction,
    ClimateZoneHeatingMode,
    ClimateZoneMode,
    ClimateZoneScheduleId,
    ClimateZoneType,
)
from aio_remeha_modbus.api.const import (
    Weekday,
)
from aio_remeha_modbus.api.main_control_monitoring import ApplianceErrorPriority, ApplianceStatus
from aio_remeha_modbus.api.schedule import (
    Timeslot,
    TimeslotActivity,
    TimeslotSetpointType,
    ZoneSchedule,
)

# from tests.util.registers import SENSOR_REGISTERS


@pytest.mark.asyncio
async def test_read_single_variable(remeha_api):
    """Test that the API can be created and a single register be read."""

    assert len(remeha_api.discovery_table.device_boards) == 2


@pytest.mark.asyncio
async def test_read_device_instance(remeha_api: RemehaApi):
    """Test that a device can be read through the modbus interface."""

    device_board = remeha_api.discovery_table.device_boards[0]

    assert device_board is not None
    assert device_board.id == 0
    assert device_board.hardware_version == (2, 1)
    assert device_board.config_table_version == (1, 2)
    assert device_board.software_version == (1, 1)
    assert str(device_board.board_category) == "EHC-10"
    assert device_board.article_number == 7853960


@pytest.mark.asyncio
async def test_read_zone(remeha_api):
    """Read a single zone."""

    zone: ClimateZone | None = remeha_api.zones[0]

    assert zone is not None
    assert zone.current_setpoint == 20.0
    assert zone.current_temparature == 23.2
    assert zone.dhw_calorifier_hysteresis is None
    assert zone.dhw_comfort_setpoint is None
    assert zone.dhw_reduced_setpoint is None
    assert zone.dhw_tank_temperature is None
    assert zone.function == ClimateZoneFunction.MIXING_CIRCUIT
    assert zone.heating_mode == ClimateZoneHeatingMode.COOLING
    assert zone.id == 1
    assert zone.mode == ClimateZoneMode.MANUAL
    assert zone.owning_device == 1
    assert zone.pump_running is True
    assert zone.room_setpoint == 20.0
    assert zone.room_temperature == 23.2
    assert zone.selected_schedule is ClimateZoneScheduleId.SCHEDULE_1
    assert zone.short_name == "CIRCA1"
    assert zone.type == ClimateZoneType.OTHER

    assert zone.is_central_heating() is True
    assert zone.is_domestic_hot_water() is False


@pytest.mark.asyncio
async def test_read_zone_update(remeha_api):
    """Read a zone update from the modbus device."""

    # Read a single zone
    zone: ClimateZone | None = remeha_api.zones[0]
    assert zone is not None
    assert zone.is_central_heating()
    assert zone.mode == ClimateZoneMode.MANUAL
    current_setpoint = zone.current_setpoint
    assert current_setpoint is not None

    # Update a variable directly at the modbus interface
    new_setpoint: float = current_setpoint + 2
    await zone.async_set_current_setpoint(new_setpoint)

    # Retrieve the updated value
    await zone.async_update()

    # Validate updated setpoint
    assert zone.current_setpoint == new_setpoint


@pytest.mark.asyncio
async def test_health_check(mock_modbus_unit):
    """Test a health check can be run without raising an exception."""

    await RemehaApi.async_health_check(mock_modbus_unit)


@pytest.mark.asyncio
async def test_read_appliance(remeha_api: RemehaApi):
    """Test that the API can read the appliance status from the modbus device."""

    appliance: Appliance = remeha_api.appliance
    ctrl_monitoring = remeha_api.main_control_monitoring
    assert ctrl_monitoring.current_error == int("0223", 16)  # H02.23 Flow rate error.
    assert ctrl_monitoring.error_priority == ApplianceErrorPriority.BLOCKING
    assert appliance.ch_enabled
    assert appliance.cooling_type is CoolingType.ACTIVE_COOLING
    assert appliance.summer_winter == 22.0
    assert appliance.silent_mode == SilentMode.LEVEL_1
    assert appliance.silent_mode_start_time == time(hour=22)
    assert appliance.silent_mode_end_time == time(hour=7)

    assert ctrl_monitoring.status is not None
    status: ApplianceStatus = ctrl_monitoring.status

    assert (
        status
        == ApplianceStatus.SERVICE_REQUIRED
        | ApplianceStatus.WATER_PRESSURE_LOW
        | ApplianceStatus.APPLIANCE_PUMP_ON
        | ApplianceStatus.COOLING_ACTIVE
    )

    # assert not status.heat_pump_on
    # assert not status.electrical_backup_on
    # assert not status.electrical_backup2_on
    # assert not status.dhw_electrical_backup_on
    # assert status.service_required
    # assert not status.power_down_reset_needed
    # assert status.water_pressure_low
    # assert status.appliance_pump_on
    # assert not status.three_way_valve_open
    # assert not status.three_way_valve
    # assert not status.three_way_valve_closed
    # assert not status.dhw_active
    # assert not status.ch_active
    # assert status.cooling_active


@pytest.mark.asyncio
async def test_write_zone_schedule(remeha_api: RemehaApi):
    """Test that a time program can be written to the modbus device."""

    expected_schedule = ZoneSchedule(
        id=ClimateZoneScheduleId.SCHEDULE_2,
        zone_id=2,
        day=Weekday.FRIDAY,
        time_slots=[
            Timeslot(
                setpoint_type=TimeslotSetpointType.ECO,
                activity=TimeslotActivity.DHW,
                switch_time=time.fromisoformat("00:00"),
            ),
            Timeslot(
                setpoint_type=TimeslotSetpointType.COMFORT,
                activity=TimeslotActivity.DHW,
                switch_time=time.fromisoformat("10:00"),
            ),
            Timeslot(
                setpoint_type=TimeslotSetpointType.ECO,
                activity=TimeslotActivity.DHW,
                switch_time=time.fromisoformat("13:00"),
            ),
            Timeslot(
                setpoint_type=TimeslotSetpointType.COMFORT,
                activity=TimeslotActivity.DHW,
                switch_time=time.fromisoformat("18:00"),
            ),
            Timeslot(
                setpoint_type=TimeslotSetpointType.ECO,
                activity=TimeslotActivity.DHW,
                switch_time=time.fromisoformat("21:00"),
            ),
        ],
    )

    # Retrieve schedule from modbus, must be None.
    current_schedule = remeha_api.zones[1].current_schedule
    assert current_schedule is not None
    actual_schedule = current_schedule[Weekday.FRIDAY]
    assert actual_schedule is not None
    assert actual_schedule != expected_schedule

    await remeha_api.zones[1].async_set_single_schedule(expected_schedule)
    await remeha_api.zones[1].async_set_selected_schedule(expected_schedule.id)
    await remeha_api.async_update()

    # Read it back and check if it was successful.
    current_schedule = remeha_api.zones[1].current_schedule
    assert current_schedule is not None
    actual_schedule = current_schedule[Weekday.FRIDAY]

    assert actual_schedule == expected_schedule
