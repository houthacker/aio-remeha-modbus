"""Tests for the GTW08 device."""

from datetime import time

import pytest

from aio_remeha_modbus.api import GTW08
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
from aio_remeha_modbus.api.const import REMEHA_MAX_SPAN, Weekday
from aio_remeha_modbus.api.main_control_monitoring import ApplianceErrorPriority, MonitoringStatus
from aio_remeha_modbus.api.schedule import (
    Timeslot,
    TimeslotActivity,
    TimeslotSetpointType,
    ZoneSchedule,
)
from aio_remeha_modbus.helpers.fields import decode_bytes


@pytest.mark.asyncio
async def test_read_single_variable(gtw_08):
    """Test that the API can be created and a single register be read."""

    assert len(gtw_08.discovery_table.device_boards) == 2


@pytest.mark.asyncio
async def test_read_device_instance(gtw_08: GTW08):
    """Test that a device can be read through the modbus interface."""

    device_board = gtw_08.discovery_table.device_boards[0]

    assert device_board is not None
    assert device_board.id == 0
    assert device_board.hardware_version == (2, 1)
    assert device_board.config_table_version == (1, 2)
    assert device_board.software_version == (1, 1)
    assert str(device_board.board_category) == "EHC-10"
    assert device_board.article_number == 7853960


@pytest.mark.asyncio
async def test_read_zone(gtw_08):
    """Read a single zone."""

    zone: ClimateZone | None = gtw_08.zones[0]

    assert zone is not None
    assert zone.current_setpoint == 20.0
    assert zone.current_temparature == 23.2
    assert zone.dhw_calorifier_hysteresis is None
    assert zone.dhw_comfort_setpoint is None
    assert zone.dhw_reduced_setpoint is None
    assert zone.dhw_tank_temperature is None
    assert zone.flow_temperature == 25.0
    assert zone.function == ClimateZoneFunction.MIXING_CIRCUIT
    assert zone.heating_curve_slope == 0.5
    assert zone.heating_curve_base_comfort == 20.0
    assert zone.heating_curve_base_reduced == 17.0
    assert zone.heating_mode == ClimateZoneHeatingMode.COOLING
    assert zone.id == 1
    assert zone.mode == ClimateZoneMode.MANUAL
    assert zone.owning_device == 1
    assert zone.pump_running is True
    assert zone.room_manual_setpoint == 20.0
    assert zone.room_temperature == 23.2
    assert zone.selected_schedule is ClimateZoneScheduleId.SCHEDULE_1
    assert zone.short_name == "CIRCA1"
    assert zone.type == ClimateZoneType.OTHER

    assert zone.is_central_heating() is True
    assert zone.is_domestic_hot_water() is False


@pytest.mark.asyncio
async def test_read_zone_update(gtw_08):
    """Read a zone update from the modbus device."""

    # Read a single zone
    zone: ClimateZone | None = gtw_08.zones[0]
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

    await GTW08.async_health_check(mock_modbus_unit)


@pytest.mark.asyncio
async def test_read_appliance(gtw_08: GTW08):
    """Test that the API can read the appliance status from the modbus device."""

    appliance: Appliance = gtw_08.appliance
    ctrl_monitoring = gtw_08.main_control_monitoring
    assert ctrl_monitoring.current_error == int("0223", 16)  # H02.23 Flow rate error.
    assert ctrl_monitoring.error_priority == ApplianceErrorPriority.BLOCKING
    assert appliance.ch_enabled
    assert appliance.cooling_type is CoolingType.ACTIVE_COOLING
    assert appliance.summer_winter == 22.0
    assert appliance.silent_mode == SilentMode.LEVEL_1
    assert appliance.silent_mode_start_time == time(hour=22)
    assert appliance.silent_mode_end_time == time(hour=7)

    assert ctrl_monitoring.monitoring_status is not None
    status: MonitoringStatus = ctrl_monitoring.monitoring_status

    assert (
        status
        == MonitoringStatus.SERVICE_REQUIRED
        | MonitoringStatus.WATER_PRESSURE_LOW
        | MonitoringStatus.APPLIANCE_PUMP_ON
        | MonitoringStatus.COOLING_ACTIVE
    )


@pytest.mark.asyncio
async def test_read_registers(gtw_08: GTW08):
    """Test that the api can read an arbitrary set of registers."""

    assert await gtw_08.async_read_registers(address=130, count=4, struct_format=">HHHH") == (
        0x0101,
        0x0102,
        0x0201,
        0x0077,
    )


@pytest.mark.asyncio
async def test_read_too_many_registers(gtw_08: GTW08):
    """Test that the api doesn't allow reading a register count exceeding REMEHA_MAX_SPAN."""

    count = REMEHA_MAX_SPAN + 1
    with pytest.raises(
        ValueError, match=f"Illegal count {count}: must be between 1 and {REMEHA_MAX_SPAN}."
    ):
        assert await gtw_08.async_read_registers(address=649, count=count)


@pytest.mark.asyncio
async def test_overwrite_zone_schdule(gtw_08: GTW08):
    """Test that the API can overwrite a single ZoneSchedule."""

    expected: bytes = bytes.fromhex("05 c81024 c8302a c82036 c84060 c80087 0000 0000")
    schedule: ZoneSchedule = ZoneSchedule(
        id=ClimateZoneScheduleId.SCHEDULE_2,
        zone_id=1,
        day=Weekday.MONDAY,
        time_slots=[
            Timeslot(
                setpoint_type=TimeslotSetpointType.COMFORT,
                activity=TimeslotActivity.HEAT_COOL,
                switch_time=time(6, 0, 0),
            ),
            Timeslot(
                setpoint_type=TimeslotSetpointType.MORNING,
                activity=TimeslotActivity.HEAT_COOL,
                switch_time=time(7, 0, 0),
            ),
            Timeslot(
                setpoint_type=TimeslotSetpointType.AWAY,
                activity=TimeslotActivity.HEAT_COOL,
                switch_time=time(9, 0, 0),
            ),
            Timeslot(
                setpoint_type=TimeslotSetpointType.EVENING,
                activity=TimeslotActivity.HEAT_COOL,
                switch_time=time(16, 0, 0),
            ),
            Timeslot(
                setpoint_type=TimeslotSetpointType.ECO,
                activity=TimeslotActivity.HEAT_COOL,
                switch_time=time(22, 30, 0),
            ),
        ],
    )

    registers: list[int] = list(
        await gtw_08.async_read_registers(759, count=10, struct_format=">HHHHHHHHHH")
    )
    encoded_bytes = decode_bytes(registers)

    # Ensure the current schedule is different.
    assert encoded_bytes != expected

    # Overwrite the new schedule
    await gtw_08.async_overwrite_zone_schedule(schedule)

    # Re-read the registers and verify
    registers = list(await gtw_08.async_read_registers(759, count=10, struct_format=">HHHHHHHHHH"))
    assert decode_bytes(registers) == expected
