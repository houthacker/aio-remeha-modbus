"""Tests for ClimateZone."""

import pytest
from freezegun import freeze_time

from aio_remeha_modbus.api import RemehaApi
from aio_remeha_modbus.api.climate_zone import (
    ClimateZone,
    ClimateZoneFunction,
    ClimateZoneMode,
    ClimateZoneScheduleId,
    ClimateZoneType,
)
from aio_remeha_modbus.api.const import REMEHA_ZONE_RESERVED_REGISTERS
from aio_remeha_modbus.api.system_discovery_table import (
    DeviceBoard,
    DeviceBoardCategory,
    DeviceBoardType,
)
from tests.conftest import update_raw_data


def test_device_board_category():
    """Test the different textual representations of the DeviceBoardCategory.

    Required because these are shown in the front-end.
    """
    assert str(DeviceBoardCategory(type=DeviceBoardType.CU_GH, generation=2)) == "CU-GH-2"
    assert str(DeviceBoardCategory(type=DeviceBoardType.CU_OH, generation=3)) == "CU-OH-3"
    assert str(DeviceBoardCategory(type=DeviceBoardType.EHC, generation=10)) == "EHC-10"
    assert str(DeviceBoardCategory(type=DeviceBoardType.MK, generation=3)) == "MK-3"
    assert str(DeviceBoardCategory(type=DeviceBoardType.SCB, generation=17)) == "SCB-17"
    assert str(DeviceBoardCategory(type=DeviceBoardType.EEC, generation=2)) == "EEC-2"
    assert str(DeviceBoardCategory(type=DeviceBoardType.GATEWAY, generation=8)) == "GTW-8"

    # Compare to a different type
    assert DeviceBoardCategory(type=DeviceBoardType.EHC, generation=10) != DeviceBoardType.EHC


@pytest.mark.asyncio
async def test_device_board_read(remeha_modbus_unit):
    """Test the device instance equality is based on it and board type.

    This allows HA to update device info if for instance the software version changes.
    """

    device_board = DeviceBoard(unit=remeha_modbus_unit)
    await device_board.async_update()
    assert device_board.id == 0
    assert device_board.board_category == DeviceBoardCategory(
        type=DeviceBoardType.EHC, generation=8
    )
    assert device_board.software_version == (1, 1)
    assert device_board.config_table_version == (1, 2)
    assert device_board.hardware_version == (2, 1)
    assert device_board.article_number == 7853960


def test_supported_climate_zone_functions():
    """Prevent regressions in the supported climate zone functions."""

    assert not ClimateZoneFunction.DISABLED.is_supported()
    assert not ClimateZoneFunction.DIRECT.is_supported()
    assert not ClimateZoneFunction.SWIMMING_POOL.is_supported()
    assert not ClimateZoneFunction.HIGH_TEMPERATURE.is_supported()
    # TODO supported FAN_CONVECTOR
    assert not ClimateZoneFunction.FAN_CONVECTOR.is_supported()
    assert not ClimateZoneFunction.DHW_TANK.is_supported()
    assert not ClimateZoneFunction.ELECTRICAL_DHW_TANK.is_supported()
    assert not ClimateZoneFunction.TIME_PROGRAM.is_supported()
    assert not ClimateZoneFunction.PROCESS_HEAT.is_supported()
    assert not ClimateZoneFunction.DHW_LAYERED.is_supported()
    assert not ClimateZoneFunction.DHW_LAYERED.is_supported()
    assert not ClimateZoneFunction.DHW_COMMERCIAL_TANK.is_supported()

    assert ClimateZoneFunction.MIXING_CIRCUIT.is_supported()
    assert ClimateZoneFunction.DHW_PRIMARY.is_supported()


@pytest.mark.asyncio
async def test_climate_zone_dhw_get_current_setpoint(remeha_api: RemehaApi):
    """Test retrieval of the current setpoint of a climate zone."""

    zone: ClimateZone | None = remeha_api.zones[1]
    assert zone is not None
    assert zone.is_domestic_hot_water()

    # Prepare setpoint values
    update_raw_data(
        remeha_api,
        [
            (665 + REMEHA_ZONE_RESERVED_REGISTERS, 0x157C),  # 55 degrees C
            (666 + REMEHA_ZONE_RESERVED_REGISTERS, 0x09C4),  # 25 degrees C
        ],
    )

    # Validate setpoint in SCHEDULING mode
    update_raw_data(remeha_api, (649 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneMode.SCHEDULING))
    await remeha_api.async_update()
    assert zone.current_setpoint is not None

    # Validate setpoint in MANUAL mode
    update_raw_data(remeha_api, (649 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneMode.MANUAL))
    await remeha_api.async_update()
    assert zone.current_setpoint == 55

    # Validate setpoint in ANTI_FROST mode
    update_raw_data(remeha_api, (649 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneMode.ANTI_FROST))
    await remeha_api.async_update()
    assert zone.current_setpoint == 25

    # Validate setpoint in unsupported type
    update_raw_data(
        remeha_api, (640 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneType.SWIMMING_POOL)
    )
    await remeha_api.async_update()
    assert zone.current_setpoint is None


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["modbus_store_ch_scheduling.json"], indirect=True)
async def test_climate_zone_ch_get_current_cooling_setpoint(remeha_api: RemehaApi):
    """Test retrieval of the current setpoint of a CH climate zone."""

    zone: ClimateZone | None = remeha_api.zones[0]
    assert zone is not None

    assert not zone.is_domestic_hot_water()
    assert zone.is_central_heating()

    # Remeha uses schedule 4 for cooling, but doesn't expose it as selected.
    # instead, schedule 1 is selected. RemehaApi maps this to schedule 4.
    assert zone.mode == ClimateZoneMode.SCHEDULING
    assert zone.selected_schedule is ClimateZoneScheduleId.SCHEDULE_4

    # Validate the schedule for a monday (all days have the same schedule in the mock data)
    # Mock data is encoded as follows:
    # 00:00 - 07:00 SLEEP
    # 07:00 - 15:00 AWAY
    # 15:00 - 18:00 HOME
    # 18:00 - 21:00 COMFORT
    # 21:00 - 00:00 EVENING
    with freeze_time("2026-06-01 00:00:00", tz_offset=-2):
        assert zone.current_setpoint == 20.5

    with freeze_time("2026-06-01 07:00:00", tz_offset=-2):
        assert zone.current_setpoint == 21.5

    with freeze_time("2026-06-01 15:00:00", tz_offset=-2):
        assert zone.current_setpoint == 21.0

    with freeze_time("2026-06-01 18:00:00", tz_offset=-2):
        assert zone.current_setpoint == 20.0

    with freeze_time("2026-06-01 21:00:00", tz_offset=-2):
        assert zone.current_setpoint == 22.0


@pytest.mark.asyncio
async def test_climate_zone_set_current_setpoint(remeha_api):
    """Test setting the current setpoint of a DHW zone."""

    zone: ClimateZone | None = remeha_api.zones[1]
    assert zone is not None

    # Prepare setpoint values, zone mode
    update_raw_data(
        remeha_api,
        [
            (649 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneMode.MANUAL),  # zone mode
            (640 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneType.OTHER),  # zone type
            (
                641 + REMEHA_ZONE_RESERVED_REGISTERS,
                ClimateZoneFunction.MIXING_CIRCUIT,
            ),  # zone function
            (663 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF),  # temporary setpoint
            (664 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF),  # room setpoint
            (665 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF),  # dhw comfort setpoint
            (666 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF),  # dhw reduced setpoint
        ],
    )
    await zone.async_update()

    await zone.async_set_current_setpoint(20.5)
    await zone.async_update()
    assert zone.current_setpoint == 20.5
    assert zone.room_setpoint == 20.5
    assert zone.dhw_comfort_setpoint is None
    assert zone.dhw_reduced_setpoint is None
    assert zone.temporary_setpoint is None

    # Reset room setpoint, set mode to manual
    update_raw_data(
        remeha_api,
        [
            (649 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneMode.MANUAL),
            (640 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneType.OTHER),
            (641 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneFunction.DHW_PRIMARY),
            (664 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF),  # room setpoint
        ],
    )
    await zone.async_update()

    await zone.async_set_current_setpoint(50)
    await zone.async_update()
    assert zone.current_setpoint == 50
    assert zone.dhw_comfort_setpoint == 50
    assert zone.dhw_reduced_setpoint is None
    assert zone.room_setpoint is None
    assert zone.temporary_setpoint is None

    # Validate setpoint for DHW zone in SCHEDULING mode, reset dhw comfort setpoint
    update_raw_data(
        remeha_api,
        [
            (
                649 + REMEHA_ZONE_RESERVED_REGISTERS,
                ClimateZoneMode.SCHEDULING,
            ),  # dhw comfort setpoint
            (665 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF),
        ],
    )
    await zone.async_update()

    await zone.async_set_current_setpoint(50)
    await zone.async_update()
    assert zone.current_setpoint is None
    assert zone.dhw_comfort_setpoint is None
    assert zone.dhw_reduced_setpoint is None
    assert zone.room_setpoint is None
    assert zone.temporary_setpoint == 50

    # Validate setpoint for DHW zone in ANTI_FROST mode, reset temporary setpoint.
    update_raw_data(
        remeha_api,
        [
            (663 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF),  # temporary setpoint
            (649 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneMode.ANTI_FROST),
        ],
    )
    await zone.async_update()

    await zone.async_set_current_setpoint(25)
    await zone.async_update()
    assert zone.current_setpoint == 25
    assert zone.dhw_comfort_setpoint is None
    assert zone.dhw_reduced_setpoint == 25
    assert zone.room_setpoint is None
    assert zone.temporary_setpoint is None

    # reset dhw reduced setpoint
    update_raw_data(remeha_api, (666 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF))
    await zone.async_update()

    # Validate setpoint outside of min/max values
    await zone.async_set_current_setpoint(25)
    await zone.async_update()
    assert zone.current_setpoint == 25

    # Try to update
    await zone.async_set_current_setpoint(zone.min_temp - 1.0)
    await zone.async_update()
    assert zone.current_setpoint == 25

    await zone.async_set_current_setpoint(zone.max_temp + 1.0)
    await zone.async_update()
    assert zone.current_setpoint == 25

    # Validate setting setpoint for unsupported zone
    update_raw_data(
        remeha_api, (640 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneType.SWIMMING_POOL)
    )
    await zone.async_update()

    await zone.async_set_current_setpoint(30)
    await zone.async_update()
    assert zone.current_setpoint is None  # Unsupported zones report None


@pytest.mark.asyncio
async def test_climate_zone_get_current_temperature(remeha_api):
    """Test the retrieval of the current temperature of a climate zone."""

    zone: ClimateZone | None = remeha_api.zones[1]
    assert zone is not None

    assert zone.is_domestic_hot_water()
    assert zone.current_temparature == 53.2

    update_raw_data(
        remeha_api, (640 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneType.SWIMMING_POOL)
    )
    await zone.async_update()
    assert zone.current_temparature == -1


@pytest.mark.asyncio
async def test_climate_zone_equality(remeha_api):
    """Test the equality of climate zones."""

    zones: list[ClimateZone] = remeha_api.zones

    assert zones[0] != zones[1]
    assert zones[1] != ClimateZoneMode.MANUAL
    assert zones[0] == zones[0]
    assert zones[1] == zones[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["modbus_store_ch_scheduling.json"], indirect=True)
async def test_scheduling_temporary_setpoint(remeha_api: RemehaApi):
    """Test that a temporary setpoint can be set if the zone is in scheduling mode."""

    # Retrieve a single zone.
    zone: ClimateZone = remeha_api.zones[0]
    assert zone.mode == ClimateZoneMode.SCHEDULING
    assert zone.has_cooling_capability()
    assert zone.selected_schedule == ClimateZoneScheduleId.SCHEDULE_4

    # Override the setpoint
    assert zone.current_setpoint is not None
    current_setpoint: float = zone.current_setpoint
    temporary_setpoint = current_setpoint + 1

    await zone.async_set_current_setpoint(temporary_setpoint)
    await remeha_api.async_update()

    # Temporary override for CH zones not yet implemented.
    # That means that changes in the current setpoint are not processed.
    assert zone.current_setpoint == current_setpoint
