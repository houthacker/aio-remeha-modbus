"""Tests for RemehaApi."""

from datetime import time

import pytest

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
from tests.conftest import get_modbus_unit

# from tests.util.registers import SENSOR_REGISTERS


@pytest.mark.asyncio
async def test_read_retries_on_timeout(remeha_api):
    """A transient modbus timeout on a read is retried instead of failing the read.

    The GTW-08 occasionally does not answer a single request in time; such a timeout
    raises a `ModbusException` rather than returning an error response. It must be
    retried so one missing reply does not fail the whole update cycle.
    """

    unit = get_modbus_unit(remeha_api)
    events = []
    unit.on_connection_lost(lambda: events.append("connection_lost"))

    appliance = remeha_api.appliance
    await appliance.async_update()
    assert events == ["connection_lost"]
    assert appliance is not None


@pytest.mark.asyncio
async def test_read_single_variable(remeha_api):
    """Test that the API can be created and a single register be read."""

    assert len(remeha_api.discovery_table.device_boards) == 2


@pytest.mark.asyncio
async def test_read_device_instance(remeha_api):
    """Test that a device can be read through the modbus interface."""

    device_board = remeha_api.discovery_table.device_boards[0]

    assert device_board is not None
    assert device_board.id == 0
    assert device_board.hardware_version == (2, 1)
    assert device_board.software_version == (1, 1)
    assert str(device_board.board_category) == "EHC-10"
    assert device_board.article_number == 7853960


@pytest.mark.asyncio
@pytest.mark.parametrize("mock_modbus_client", ["modbus_store.json"], indirect=True)
@pytest.mark.skip(reason="RemehaApi.sensors is not yet implemented.")
async def test_read_sensor_values(mock_modbus_client):
    """Read values for a given list of variables that are configured as sensors."""

    # api: RemehaApi = get_api(mock_modbus_client=mock_modbus_client)
    # v = await api.async_read_sensor_values(descriptions=SENSOR_REGISTERS)
    # assert v == dict(
    #     zip(
    #         SENSOR_REGISTERS,
    #         [
    #             int("0223", 16),
    #             3,
    #             24.82,
    #             20.44,
    #             20.00,
    #             21.14,
    #             22.54,
    #             1.2,
    #             12.66,
    #             None,
    #             None,
    #             0.5,
    #             1234,
    #             2345,
    #             321,
    #             456,
    #             100,
    #             200,
    #             10000,
    #             5000,
    #             3000,
    #             500,
    #             4000,
    #             None,
    #             None,
    #             2200,
    #             3500,
    #             0,
    #             0,
    #             0.5,
    #             57,
    #             None,
    #         ],
    #         strict=True,
    #     )
    # )


@pytest.mark.asyncio
async def test_read_zone(remeha_api):
    """Read a single zone."""

    zone: ClimateZone | None = remeha_api.zones[0]

    assert zone is not None
    assert await zone.async_get_current_setpoint() == 20.0
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
    current_setpoint = await zone.async_get_current_setpoint()
    assert current_setpoint is not None

    # Update a variable directly at the modbus interface
    new_setpoint: float = current_setpoint + 2
    zone.set_current_setpoint(new_setpoint)

    # Retrieve the updated value
    await zone.async_update()

    # Validate updated setpoint
    assert await zone.async_get_current_setpoint() == new_setpoint


@pytest.mark.asyncio
async def test_health_check(remeha_api):
    """Test a health check can be run without raising an exception."""

    await remeha_api.async_health_check()


@pytest.mark.asyncio
async def test_read_appliance(remeha_api):
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

    status: ApplianceStatus = ctrl_monitoring.status
    assert status is not None

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
async def test_write_zone_schedule(remeha_api):
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
    actual_schedule: ZoneSchedule | None = await remeha_api.zones[2].async_current_schedule()
    assert actual_schedule is None

    # TODO
    # await remeha_api.zones[2].async_set_schedule(expected_schedule)

    # Read it back and check if it was successful.
    actual_schedule = await remeha_api.zones[2].async_current_schedule()

    assert actual_schedule == expected_schedule
