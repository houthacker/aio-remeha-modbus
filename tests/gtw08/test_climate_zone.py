"""Tests for ClimateZone."""

import logging
from datetime import datetime, time, timedelta
from types import SimpleNamespace
from typing import Final

import pytest
from dateutil import tz
from freezegun import freeze_time
from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.gtw08 import GTW08
from aio_remeha_modbus.gtw08.climate_zone import (
    ClimateZone,
    ClimateZoneFunction,
    ClimateZoneMode,
    ClimateZoneScheduleId,
    ClimateZoneType,
    _map_selected_schedule_for_read,
    _map_selected_schedule_for_write,
    _time_program_start_address,
    _writable_schedule_id,
    is_central_heating,
    is_domestic_hot_water,
)
from aio_remeha_modbus.gtw08.const import (
    REMEHA_TIME_PROGRAM_RESERVED_REGISTERS,
    REMEHA_ZONE_RESERVED_REGISTERS,
    Limits,
    Weekday,
)
from aio_remeha_modbus.gtw08.errors import InvalidZoneSchedule, RemehaApiError
from aio_remeha_modbus.gtw08.schedule import (
    Timeslot,
    TimeslotActivity,
    TimeslotSetpointType,
)
from aio_remeha_modbus.helpers.gtw08 import TimeOfDay
from tests.conftest import get_modbus_unit, update_raw_data


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
async def test_invalid_zone_schedule(gtw_08: GTW08):
    """Test that an invalid zone schedule read from modbus causes an InvalidZoneSchedule."""

    zone: ClimateZone | None = gtw_08.zones[1]
    assert zone is not None
    assert zone.is_domestic_hot_water()

    # Store invalid values for the first zone schedule.
    # The first time slot is stored in byte 1-3 (inclusive, 0-based), so scramble that.
    update_raw_data(
        gtw_08,
        [
            (688 + REMEHA_ZONE_RESERVED_REGISTERS, 0x01),  # select schedule_1
            (690 + REMEHA_ZONE_RESERVED_REGISTERS, 0x1515),  # garbage
        ],
    )

    with pytest.raises(InvalidZoneSchedule):
        await gtw_08.async_update()


@pytest.mark.asyncio
async def test_climate_zone_dhw_get_current_setpoint(gtw_08: GTW08):
    """Test retrieval of the current setpoint of a climate zone."""

    zone: ClimateZone | None = gtw_08.zones[1]
    assert zone is not None
    assert zone.is_domestic_hot_water()

    # Prepare setpoint values
    update_raw_data(
        gtw_08,
        [
            (665 + REMEHA_ZONE_RESERVED_REGISTERS, 0x157C),  # 55 degrees C
            (666 + REMEHA_ZONE_RESERVED_REGISTERS, 0x09C4),  # 25 degrees C
        ],
    )

    # Validate setpoint in SCHEDULING mode
    update_raw_data(gtw_08, (649 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneMode.SCHEDULING))
    await gtw_08.async_update()
    assert zone.current_setpoint is not None

    # Validate setpoint in MANUAL mode
    update_raw_data(gtw_08, (649 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneMode.MANUAL))
    await gtw_08.async_update()
    assert zone.current_setpoint == 55

    # Validate setpoint in ANTI_FROST mode
    update_raw_data(gtw_08, (649 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneMode.ANTI_FROST))
    await gtw_08.async_update()
    assert zone.current_setpoint == 25

    # Validate setpoint in unsupported type
    update_raw_data(gtw_08, (640 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneType.SWIMMING_POOL))
    await gtw_08.async_update()
    assert zone.current_setpoint is None


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["modbus_store_ch_scheduling.json"], indirect=True)
async def test_climate_zone_ch_get_current_cooling_setpoint(gtw_08: GTW08):
    """Test retrieval of the current setpoint of a CH climate zone."""

    zone: ClimateZone | None = gtw_08.zones[0]
    assert zone is not None

    assert not zone.is_domestic_hot_water()
    assert zone.is_central_heating()

    # Remeha uses schedule 4 for cooling, but doesn't expose it as selected.
    # instead, schedule 1 is selected. GTW08 maps this to schedule 4.
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
@pytest.mark.parametrize(
    "remeha_modbus_unit", ["modbus_store_ch_heating_scheduling.json"], indirect=True
)
async def test_climate_zone_ch_get_current_heating_setpoint(gtw_08: GTW08):
    """Test retrieval of the current heating setpoint of a CH climate zone in scheduling mode."""

    zone: ClimateZone | None = gtw_08.zones[0]
    assert zone is not None

    assert not zone.is_domestic_hot_water()
    assert zone.is_central_heating()
    assert not zone.appliance_requires_cooling()

    assert zone.mode == ClimateZoneMode.SCHEDULING
    assert zone.selected_schedule is ClimateZoneScheduleId.SCHEDULE_1

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
@pytest.mark.parametrize(
    "remeha_modbus_unit", ["modbus_store_ch_cooling_scheduling.json"], indirect=True
)
async def test_write_ch_zone_cooling_schedule_is_supported(gtw_08: GTW08):
    """Test that writing the schedule of a non-DHW cooling schedule is supported."""

    zone: ClimateZone | None = gtw_08.zones[0]
    assert zone is not None
    assert zone.current_schedule is not None
    assert zone.current_schedule[Weekday.MONDAY] is not None

    # Can set the current schedule
    await zone.async_set_current_schedule(
        schedule_id=ClimateZoneScheduleId.SCHEDULE_4,
        schedule=zone.current_schedule,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "remeha_modbus_unit", ["modbus_store_ch_heating_scheduling.json"], indirect=True
)
async def test_write_ch_zone_heating_schedule_not_supported(gtw_08: GTW08):
    """Test that writing the schedule of a non-DHW heating schedule raises an error."""

    zone: ClimateZone | None = gtw_08.zones[0]
    assert zone is not None
    assert zone.current_schedule is not None
    assert zone.current_schedule[Weekday.MONDAY] is not None

    # Cannot set the current schedule
    with pytest.raises(
        RemehaApiError, check=lambda e: e.translation_key == "schedule_write_not_supported"
    ):
        await zone.async_set_current_schedule(
            schedule_id=ClimateZoneScheduleId.SCHEDULE_1, schedule=zone.current_schedule
        )


@pytest.mark.asyncio
async def test_climate_zone_set_current_setpoint(gtw_08):
    """Test setting the current setpoint of a DHW zone."""

    zone: ClimateZone | None = gtw_08.zones[1]
    assert zone is not None

    # Prepare setpoint values, zone mode
    update_raw_data(
        gtw_08,
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
    assert zone.room_manual_setpoint == 20.5
    assert zone.dhw_comfort_setpoint is None
    assert zone.dhw_reduced_setpoint is None
    assert zone.temporary_room_setpoint is None

    # Reset room setpoint, set mode to manual
    update_raw_data(
        gtw_08,
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
    assert zone.room_manual_setpoint is None
    assert zone.temporary_room_setpoint is None

    # Validate setpoint for DHW zone in SCHEDULING mode.
    # Overriding current setpoint in SCHEDULING mode is not supported (by Remeha)
    # for DHW zones. So the setpoint must not be updated.
    update_raw_data(
        gtw_08,
        [
            (
                649 + REMEHA_ZONE_RESERVED_REGISTERS,
                ClimateZoneMode.SCHEDULING,
            ),
            # (665 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF),  # dhw comfort setpoint
        ],
    )
    await zone.async_update()

    await zone.async_set_current_setpoint(51)
    await zone.async_update()
    assert zone.is_domestic_hot_water()
    assert zone.current_setpoint != 51
    assert zone.dhw_comfort_setpoint != 51
    assert zone.dhw_reduced_setpoint != 51
    assert zone.room_manual_setpoint != 51
    assert zone.temporary_room_setpoint != 51

    # Validate setpoint for DHW zone in ANTI_FROST mode, reset temporary setpoint.
    update_raw_data(
        gtw_08,
        [
            (649 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneMode.ANTI_FROST),
            (663 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF),  # temporary setpoint
            (665 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF),  # DHW comfort setpoint
        ],
    )
    await zone.async_update()

    await zone.async_set_current_setpoint(25)
    await zone.async_update()
    assert zone.current_setpoint == 25
    assert zone.dhw_comfort_setpoint is None
    assert zone.dhw_reduced_setpoint == 25
    assert zone.room_manual_setpoint is None
    assert zone.temporary_room_setpoint is None

    # reset dhw reduced setpoint
    update_raw_data(gtw_08, (666 + REMEHA_ZONE_RESERVED_REGISTERS, 0xFFFF))
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
    update_raw_data(gtw_08, (640 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneType.SWIMMING_POOL))
    await zone.async_update()

    await zone.async_set_current_setpoint(30)
    await zone.async_update()
    assert zone.current_setpoint is None  # Unsupported zones report None


@pytest.mark.asyncio
async def test_climate_zone_set_selected_schedule(gtw_08):
    """Test that the CH schedule is always mapped to schedule_1 from schedule_4."""

    zone: ClimateZone | None = gtw_08.zones[0]
    assert zone is not None
    assert zone.is_central_heating()

    await zone.async_set_mode(ClimateZoneMode.SCHEDULING)
    await zone.async_set_selected_schedule(ClimateZoneScheduleId.SCHEDULE_4)

    # The backing field must contain schedule_1
    assert zone._selected_schedule is ClimateZoneScheduleId.SCHEDULE_1  # noqa: SLF001

    # From the API's perspective, the selected schedule is still required to be schedule_4
    assert zone.selected_schedule is ClimateZoneScheduleId.SCHEDULE_4


@pytest.mark.asyncio
async def test_climate_zone_get_current_temperature(gtw_08):
    """Test the retrieval of the current temperature of a climate zone."""

    zone: ClimateZone | None = gtw_08.zones[1]
    assert zone is not None

    assert zone.is_domestic_hot_water()
    assert zone.current_temparature == 53.2

    update_raw_data(gtw_08, (640 + REMEHA_ZONE_RESERVED_REGISTERS, ClimateZoneType.SWIMMING_POOL))
    await zone.async_update()
    assert zone.current_temparature == -1


@pytest.mark.asyncio
async def test_climate_zone_equality(gtw_08):
    """Test the equality of climate zones."""

    zones: list[ClimateZone] = gtw_08.zones

    assert zones[0] != zones[1]
    assert zones[1] != ClimateZoneMode.MANUAL
    assert zones[0] == zones[0]
    assert zones[1] == zones[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["modbus_store_ch_scheduling.json"], indirect=True)
async def test_dhw_scheduling_temporary_setpoint(gtw_08: GTW08):
    """Test that a temporary setpoint can be set if the zone is in scheduling mode."""

    # Retrieve a single zone.
    zone: ClimateZone = gtw_08.zones[0]
    assert zone.mode == ClimateZoneMode.SCHEDULING
    assert zone.is_central_heating()
    assert zone.has_cooling_capability()
    assert zone.selected_schedule == ClimateZoneScheduleId.SCHEDULE_4

    # Override the setpoint
    assert zone.current_setpoint is not None
    current_setpoint: float = zone.current_setpoint
    temporary_setpoint = current_setpoint + 1

    await zone.async_set_current_setpoint(temporary_setpoint)
    await gtw_08.async_update()

    assert zone.current_setpoint == temporary_setpoint


@pytest.mark.asyncio
async def test_climate_zone_end_change_mode_time(gtw_08: GTW08):
    """Test that the temporary setpoint end time is read correctly."""

    expected: Final[datetime] = datetime(
        year=2025,
        month=4,
        day=28,
        hour=18,
        minute=00,
        second=00,
        tzinfo=tz.gettz("Europe/Amsterdam"),
    )

    zone: ClimateZone = gtw_08.zones[0]
    assert zone.temporary_room_setpoint_end_time == expected


@pytest.mark.asyncio
async def test_write_zone_schedule(gtw_08: GTW08):
    """Test that a time program can be written to the modbus device."""

    time_slots = [
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
    ]

    # Retrieve schedule from modbus, must not be None.
    current_schedule = gtw_08.zones[1].current_schedule
    assert current_schedule is not None
    actual_schedule = current_schedule[Weekday.FRIDAY]
    assert actual_schedule is not None
    assert actual_schedule != time_slots

    await gtw_08.zones[1].async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_2, dict.fromkeys(Weekday, time_slots)
    )
    await gtw_08.async_update()

    # Read it back and check if it was successful.
    current_schedule = gtw_08.zones[1].current_schedule
    assert current_schedule is not None
    actual_schedule = current_schedule[Weekday.FRIDAY]

    assert actual_schedule == time_slots


@pytest.mark.asyncio
async def test_write_cooling_schedule(gtw_08: GTW08):
    """Test that a cooling schedule can be written to the modbus device."""

    expected_time_slots = [
        Timeslot(
            setpoint_type=TimeslotSetpointType.ECO,
            activity=TimeslotActivity.HEAT_COOL,
            switch_time=time.fromisoformat("00:00"),
        ),
        Timeslot(
            setpoint_type=TimeslotSetpointType.COMFORT,
            activity=TimeslotActivity.HEAT_COOL,
            switch_time=time.fromisoformat("10:00"),
        ),
        Timeslot(
            setpoint_type=TimeslotSetpointType.ECO,
            activity=TimeslotActivity.HEAT_COOL,
            switch_time=time.fromisoformat("13:00"),
        ),
        Timeslot(
            setpoint_type=TimeslotSetpointType.COMFORT,
            activity=TimeslotActivity.HEAT_COOL,
            switch_time=time.fromisoformat("18:00"),
        ),
        Timeslot(
            setpoint_type=TimeslotSetpointType.ECO,
            activity=TimeslotActivity.HEAT_COOL,
            switch_time=time.fromisoformat("21:00"),
        ),
    ]

    await gtw_08.zones[0].async_set_mode(ClimateZoneMode.SCHEDULING)
    await gtw_08.zones[0].async_set_selected_schedule(ClimateZoneScheduleId.SCHEDULE_4)

    # Write the actual schedule
    current_schedule = gtw_08.zones[0].current_schedule
    current_schedule[Weekday.FRIDAY] = expected_time_slots
    await gtw_08.zones[0].async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_4, current_schedule
    )

    # TODO validate that the state is equal before and after the write.
    await gtw_08.async_update()

    # Read it back and check if it was successful.
    current_schedule = gtw_08.zones[0].current_schedule
    assert current_schedule is not None
    actual_schedule = current_schedule[Weekday.FRIDAY]

    assert actual_schedule == expected_time_slots
    assert gtw_08.zones[0].mode is ClimateZoneMode.SCHEDULING
    assert gtw_08.zones[0].selected_schedule is ClimateZoneScheduleId.SCHEDULE_4


_DHW_SCHEDULE = [
    Timeslot(TimeslotSetpointType.ECO, TimeslotActivity.DHW, time(0, 0)),
    Timeslot(TimeslotSetpointType.COMFORT, TimeslotActivity.DHW, time(10, 0)),
    Timeslot(TimeslotSetpointType.ECO, TimeslotActivity.DHW, time(13, 0)),
    Timeslot(TimeslotSetpointType.COMFORT, TimeslotActivity.DHW, time(18, 0)),
    Timeslot(TimeslotSetpointType.ECO, TimeslotActivity.DHW, time(21, 0)),
]
"""A well-formed DHW schedule, used for every weekday."""

_DHW_ZONE_OFFSET = REMEHA_ZONE_RESERVED_REGISTERS
"""The register offset of the DHW zone in the default fixture."""


def _end_time_registers(end_time: datetime) -> list[tuple[int, int]]:
    """Return the DHW zone register values that hold `end_time` as temporary setpoint end time."""

    encoded = TimeOfDay.to_bytes(end_time)
    return [
        (978 + _DHW_ZONE_OFFSET + i, int.from_bytes(encoded[i * 2 : i * 2 + 2])) for i in range(3)
    ]


@pytest.mark.parametrize(
    ("zone_type", "function", "expected"),
    [
        (ClimateZoneType.DHW, ClimateZoneFunction.DISABLED, True),
        (ClimateZoneType.DHW, ClimateZoneFunction.MIXING_CIRCUIT, True),
        (ClimateZoneType.OTHER, ClimateZoneFunction.DHW_BIC, True),
        (ClimateZoneType.OTHER, ClimateZoneFunction.DHW_COMMERCIAL_TANK, True),
        (ClimateZoneType.OTHER, ClimateZoneFunction.DHW_LAYERED, True),
        (ClimateZoneType.OTHER, ClimateZoneFunction.DHW_PRIMARY, True),
        (ClimateZoneType.OTHER, ClimateZoneFunction.DHW_TANK, True),
        (ClimateZoneType.OTHER, ClimateZoneFunction.ELECTRICAL_DHW_TANK, True),
        (ClimateZoneType.OTHER, ClimateZoneFunction.MIXING_CIRCUIT, False),
        (ClimateZoneType.OTHER, ClimateZoneFunction.DISABLED, False),
        (ClimateZoneType.CH_ONLY, ClimateZoneFunction.DHW_PRIMARY, False),
        (ClimateZoneType.CH_AND_COOLING, ClimateZoneFunction.DHW_TANK, False),
        (ClimateZoneType.NOT_PRESENT, ClimateZoneFunction.DHW_PRIMARY, False),
    ],
)
def test_is_domestic_hot_water(
    zone_type: ClimateZoneType,
    function: ClimateZoneFunction,
    expected: bool,
):
    """Test which combinations of zone type and function are DHW zones."""

    assert is_domestic_hot_water(zone_type, function) is expected


@pytest.mark.parametrize(
    ("zone_type", "function", "expected"),
    [
        (ClimateZoneType.CH_ONLY, ClimateZoneFunction.DISABLED, True),
        (ClimateZoneType.CH_ONLY, ClimateZoneFunction.DHW_PRIMARY, True),
        (ClimateZoneType.CH_AND_COOLING, ClimateZoneFunction.MIXING_CIRCUIT, True),
        (ClimateZoneType.OTHER, ClimateZoneFunction.MIXING_CIRCUIT, True),
        (ClimateZoneType.OTHER, ClimateZoneFunction.DHW_PRIMARY, False),
        (ClimateZoneType.OTHER, ClimateZoneFunction.FAN_CONVECTOR, False),
        (ClimateZoneType.DHW, ClimateZoneFunction.MIXING_CIRCUIT, False),
        (ClimateZoneType.NOT_PRESENT, ClimateZoneFunction.MIXING_CIRCUIT, False),
        (ClimateZoneType.SWIMMING_POOL, ClimateZoneFunction.MIXING_CIRCUIT, False),
    ],
)
def test_is_central_heating(
    zone_type: ClimateZoneType,
    function: ClimateZoneFunction,
    expected: bool,
):
    """Test which combinations of zone type and function are CH zones."""

    assert is_central_heating(zone_type, function) is expected


@pytest.mark.parametrize("function", list(ClimateZoneFunction))
def test_climate_zone_function_has_cooling_capability(function: ClimateZoneFunction):
    """Test that only mixing circuits and fan convectors can cool."""

    expected = function in {ClimateZoneFunction.MIXING_CIRCUIT, ClimateZoneFunction.FAN_CONVECTOR}

    assert function.has_cooling_capability() is expected


@pytest.mark.parametrize(
    ("mode", "function", "requires_cooling", "selected", "expected"),
    [
        # The cooling schedule is used when scheduling, cooling is possible and required.
        (
            ClimateZoneMode.SCHEDULING,
            ClimateZoneFunction.MIXING_CIRCUIT,
            True,
            0,
            ClimateZoneScheduleId.SCHEDULE_4,
        ),
        (
            ClimateZoneMode.SCHEDULING,
            ClimateZoneFunction.FAN_CONVECTOR,
            True,
            2,
            ClimateZoneScheduleId.SCHEDULE_4,
        ),
        # Otherwise the selected schedule is used.
        (
            ClimateZoneMode.SCHEDULING,
            ClimateZoneFunction.MIXING_CIRCUIT,
            False,
            1,
            ClimateZoneScheduleId.SCHEDULE_2,
        ),
        (
            ClimateZoneMode.MANUAL,
            ClimateZoneFunction.MIXING_CIRCUIT,
            True,
            1,
            ClimateZoneScheduleId.SCHEDULE_2,
        ),
        (
            ClimateZoneMode.ANTI_FROST,
            ClimateZoneFunction.MIXING_CIRCUIT,
            True,
            2,
            ClimateZoneScheduleId.SCHEDULE_3,
        ),
        (
            ClimateZoneMode.SCHEDULING,
            ClimateZoneFunction.DHW_PRIMARY,
            True,
            0,
            ClimateZoneScheduleId.SCHEDULE_1,
        ),
        # The cooling schedule doesn't depend on the selected schedule at all.
        (
            ClimateZoneMode.SCHEDULING,
            ClimateZoneFunction.MIXING_CIRCUIT,
            True,
            None,
            ClimateZoneScheduleId.SCHEDULE_4,
        ),
        (ClimateZoneMode.MANUAL, ClimateZoneFunction.MIXING_CIRCUIT, False, None, None),
    ],
)
def test_map_selected_schedule_for_read(
    mode: ClimateZoneMode,
    function: ClimateZoneFunction,
    requires_cooling: bool,
    selected: int | None,
    expected: ClimateZoneScheduleId | None,
):
    """Test when the cooling schedule shadows the selected schedule."""

    assert (
        _map_selected_schedule_for_read(
            zone_mode=mode,
            zone_function=function,
            appliance_requires_cooling=requires_cooling,
            selected_schedule=selected,
        )
        is expected
    )


@pytest.mark.parametrize(
    ("schedule_id", "expected"),
    [
        (ClimateZoneScheduleId.SCHEDULE_1, ClimateZoneScheduleId.SCHEDULE_1),
        (ClimateZoneScheduleId.SCHEDULE_2, ClimateZoneScheduleId.SCHEDULE_2),
        (ClimateZoneScheduleId.SCHEDULE_3, ClimateZoneScheduleId.SCHEDULE_3),
        (ClimateZoneScheduleId.SCHEDULE_4, ClimateZoneScheduleId.SCHEDULE_1),
    ],
)
def test_map_selected_schedule_for_write(
    schedule_id: ClimateZoneScheduleId, expected: ClimateZoneScheduleId
):
    """Test that the cooling schedule is written as schedule 1."""

    assert _map_selected_schedule_for_write(schedule_id) is expected


def test_writable_schedule_id():
    """Test that schedule 4 can not be written, but schedules 1 to 3 can."""

    validate = _writable_schedule_id()

    for schedule_id in (
        ClimateZoneScheduleId.SCHEDULE_1,
        ClimateZoneScheduleId.SCHEDULE_2,
        ClimateZoneScheduleId.SCHEDULE_3,
    ):
        assert validate(schedule_id) is schedule_id

    with pytest.raises(TypeError, match="SCHEDULE_4 is not writable"):
        validate(ClimateZoneScheduleId.SCHEDULE_4)


@pytest.mark.parametrize(
    ("zone_id", "schedule_id", "expected"),
    [
        (1, ClimateZoneScheduleId.SCHEDULE_1, 0),
        (1, ClimateZoneScheduleId.SCHEDULE_2, REMEHA_TIME_PROGRAM_RESERVED_REGISTERS),
        (1, ClimateZoneScheduleId.SCHEDULE_4, 3 * REMEHA_TIME_PROGRAM_RESERVED_REGISTERS),
        (2, ClimateZoneScheduleId.SCHEDULE_1, REMEHA_ZONE_RESERVED_REGISTERS),
        (
            3,
            ClimateZoneScheduleId.SCHEDULE_3,
            2 * REMEHA_ZONE_RESERVED_REGISTERS + 2 * REMEHA_TIME_PROGRAM_RESERVED_REGISTERS,
        ),
    ],
)
def test_time_program_start_address(
    zone_id: int, schedule_id: ClimateZoneScheduleId, expected: int
):
    """Test the offset of a time program, relative to the start of the first zone."""

    assert _time_program_start_address(zone_id, schedule_id) == expected


def test_time_program_start_address_defaults():
    """Test that the defaults refer to the first schedule of the first zone."""

    assert _time_program_start_address() == 0


@pytest.mark.asyncio
async def test_climate_zone_defaults(remeha_modbus_unit: MockModbusUnit):
    """Test the default arguments of a climate zone."""

    zone = ClimateZone(remeha_modbus_unit)

    assert zone.id == 1
    assert zone.time_zone is None
    assert zone.appliance_requires_cooling() is False


@pytest.mark.asyncio
async def test_climate_zone_sequence_id_offsets_registers(remeha_modbus_unit: MockModbusUnit):
    """Test that the sequence id determines which registers are read."""

    zone = ClimateZone(remeha_modbus_unit, sequence_id=2)
    await zone.async_update()

    assert zone.id == 2
    assert zone.is_domestic_hot_water()
    assert zone.dhw_comfort_setpoint == 55.0


@pytest.mark.asyncio
async def test_climate_zone_has_cooling_capability(gtw_08: GTW08):
    """Test that the mixing circuit can cool and the DHW zone cannot."""

    assert gtw_08.zones[0].has_cooling_capability() is True
    assert gtw_08.zones[1].has_cooling_capability() is False


@pytest.mark.asyncio
async def test_climate_zone_set_mode(gtw_08: GTW08):
    """Test that the mode of a zone can be written."""

    zone = gtw_08.zones[0]
    unit = get_modbus_unit(gtw_08)

    for mode in ClimateZoneMode:
        await zone.async_set_mode(mode)

        assert unit.holding[649] == mode.value
        await zone.async_update()
        assert zone.mode is mode


@pytest.mark.asyncio
async def test_climate_zone_selected_schedule_not_set(gtw_08: GTW08):
    """Test that a zone without a selected schedule has no schedule at all."""

    zone = gtw_08.zones[0]
    update_raw_data(gtw_08, (688, 0xFF))
    await zone.async_update()

    assert zone.selected_schedule is None
    assert zone.current_schedule == dict.fromkeys(Weekday)


@pytest.mark.asyncio
async def test_climate_zone_current_schedule(gtw_08: GTW08):
    """Test that the current schedule contains the slots of every weekday."""

    zone = gtw_08.zones[1]
    await zone.async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_1, dict.fromkeys(Weekday, _DHW_SCHEDULE)
    )
    await gtw_08.async_update()

    assert zone.current_schedule == dict.fromkeys(Weekday, _DHW_SCHEDULE)


@pytest.mark.asyncio
async def test_climate_zone_end_time_not_set(gtw_08: GTW08):
    """Test that a zone without a temporary setpoint has no end time."""

    assert gtw_08.zones[1].temporary_room_setpoint_end_time is None


@pytest.mark.asyncio
async def test_climate_zone_selected_schedule_cannot_be_written_directly(gtw_08: GTW08):
    """Test that schedule 4 is refused when writing the backing field."""

    with pytest.raises(TypeError, match="not writable"):
        await gtw_08.zones[0].write("_selected_schedule", ClimateZoneScheduleId.SCHEDULE_4)


@pytest.mark.asyncio
async def test_climate_zone_set_selected_schedule_writes_register(gtw_08: GTW08):
    """Test that schedules 1 to 3 are written unchanged."""

    zone = gtw_08.zones[1]
    unit = get_modbus_unit(gtw_08)

    for schedule_id in (
        ClimateZoneScheduleId.SCHEDULE_1,
        ClimateZoneScheduleId.SCHEDULE_2,
        ClimateZoneScheduleId.SCHEDULE_3,
    ):
        await zone.async_set_selected_schedule(schedule_id)

        assert unit.holding[688 + _DHW_ZONE_OFFSET] == schedule_id.value
        assert zone.selected_schedule is schedule_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("setter", "register", "value"),
    [
        ("async_set_room_setpoint_1", 650, 17.0),
        ("async_set_room_setpoint_2", 651, 21.0),
        ("async_set_room_setpoint_3", 652, 15.0),
        ("async_set_room_setpoint_4", 653, 19.0),
        ("async_set_room_setpoint_5", 654, 22.0),
        ("async_set_room_cooling_setpoint_1", 656, 25.5),
        ("async_set_room_cooling_setpoint_2", 657, 24.0),
        ("async_set_room_cooling_setpoint_3", 658, 27.5),
        ("async_set_room_cooling_setpoint_4", 659, 24.5),
        ("async_set_room_cooling_setpoint_5", 660, 23.5),
    ],
)
async def test_climate_zone_set_room_setpoints(
    gtw_08: GTW08, setter: str, register: int, value: float
):
    """Test that every room setpoint is written to its own register, scaled by 0.1."""

    zone = gtw_08.zones[0]
    unit = get_modbus_unit(gtw_08)

    await getattr(zone, setter)(value)

    assert unit.holding[register] == round(value * 10)
    await zone.async_update()
    field = setter.removeprefix("async_set_")
    assert getattr(zone, field) == value


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="in_range(range(5, 31)) refuses fractional degrees such as 21.5.",
)
async def test_climate_zone_set_room_setpoint_fractional_degrees(gtw_08: GTW08):
    """Test that a heating setpoint can be set in half degrees."""

    zone = gtw_08.zones[0]

    await zone.async_set_room_setpoint_2(21.5)
    await zone.async_update()

    assert zone.room_setpoint_2 == 21.5


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [4.0, 31.0, -1.0])
@pytest.mark.parametrize("setter", [f"async_set_room_setpoint_{n}" for n in range(1, 6)])
async def test_climate_zone_set_room_setpoint_out_of_range(
    gtw_08: GTW08, setter: str, value: float
):
    """Test that heating setpoints outside of 5 - 30 °C are refused and not written."""

    zone = gtw_08.zones[0]
    unit = get_modbus_unit(gtw_08)
    before = dict(unit.holding)

    with pytest.raises(ValueError, match=r"\S"):
        await getattr(zone, setter)(value)

    assert unit.holding == before


@pytest.mark.asyncio
async def test_climate_zone_set_dhw_calorifier_hysteresis(gtw_08: GTW08):
    """Test that the DHW calorifier hysteresis is written, scaled by 0.01."""

    zone = gtw_08.zones[1]
    unit = get_modbus_unit(gtw_08)
    assert zone.dhw_calorifier_hysteresis == 3.0

    await zone.async_set_dhw_calorifier_hysteresis(5.5)

    assert unit.holding[686 + _DHW_ZONE_OFFSET] == 550
    await zone.async_update()
    assert zone.dhw_calorifier_hysteresis == 5.5


@pytest.mark.asyncio
async def test_climate_zone_current_setpoint_ch_anti_frost(gtw_08: GTW08):
    """Test that the setpoint of a CH zone in anti-frost mode is the minimum temperature."""

    zone = gtw_08.zones[0]
    await zone.async_set_mode(ClimateZoneMode.ANTI_FROST)

    assert zone.current_setpoint == Limits.CH_MIN_TEMP


@pytest.mark.asyncio
async def test_climate_zone_set_current_setpoint_ch_manual(gtw_08: GTW08):
    """Test that the manual setpoint of a CH zone is written."""

    zone = gtw_08.zones[0]
    unit = get_modbus_unit(gtw_08)
    assert zone.mode is ClimateZoneMode.MANUAL

    await zone.async_set_current_setpoint(22.5)

    assert unit.holding[664] == 225
    await zone.async_update()
    assert zone.current_setpoint == 22.5
    assert zone.room_manual_setpoint == 22.5


@pytest.mark.asyncio
async def test_climate_zone_set_current_setpoint_ch_anti_frost(gtw_08: GTW08):
    """Test that the setpoint of a CH zone in anti-frost mode cannot be changed."""

    zone = gtw_08.zones[0]
    unit = get_modbus_unit(gtw_08)
    await zone.async_set_mode(ClimateZoneMode.ANTI_FROST)
    before = dict(unit.holding)

    await zone.async_set_current_setpoint(22.5)

    assert unit.holding == before


@pytest.mark.asyncio
@pytest.mark.parametrize("setpoint", [Limits.CH_MIN_TEMP, Limits.CH_MAX_TEMP])
async def test_climate_zone_set_current_setpoint_limits_are_allowed(
    gtw_08: GTW08, setpoint: Limits
):
    """Test that the limits themselves are valid setpoints."""

    zone = gtw_08.zones[0]

    await zone.async_set_current_setpoint(setpoint.value)
    await zone.async_update()

    assert zone.current_setpoint == setpoint.value


@pytest.mark.asyncio
async def test_climate_zone_set_current_setpoint_out_of_range_is_logged(
    gtw_08: GTW08, caplog: pytest.LogCaptureFixture
):
    """Test that a setpoint outside of the limits is ignored with a warning."""

    zone = gtw_08.zones[0]
    unit = get_modbus_unit(gtw_08)
    before = dict(unit.holding)

    with caplog.at_level(logging.WARNING):
        await zone.async_set_current_setpoint(Limits.CH_MAX_TEMP.value + 0.5)

    assert "outside allowed range" in caplog.text
    assert unit.holding == before


@pytest.mark.asyncio
async def test_climate_zone_unknown_type_limits(gtw_08: GTW08):
    """Test that a zone that is neither CH nor DHW gets the most restrictive limits."""

    zone = gtw_08.zones[1]
    update_raw_data(gtw_08, (640 + _DHW_ZONE_OFFSET, ClimateZoneType.SWIMMING_POOL))
    await zone.async_update()

    assert not zone.is_central_heating()
    assert not zone.is_domestic_hot_water()
    assert zone.max_temp == Limits.CH_MAX_TEMP
    assert zone.min_temp == Limits.DHW_MIN_TEMP


@pytest.mark.asyncio
async def test_climate_zone_limits(gtw_08: GTW08):
    """Test the limits of a CH and a DHW zone."""

    assert (gtw_08.zones[0].min_temp, gtw_08.zones[0].max_temp) == (
        Limits.CH_MIN_TEMP,
        Limits.CH_MAX_TEMP,
    )
    assert (gtw_08.zones[1].min_temp, gtw_08.zones[1].max_temp) == (
        Limits.DHW_MIN_TEMP,
        Limits.DHW_MAX_TEMP,
    )


@pytest.mark.asyncio
async def test_climate_zone_get_current_temperature_ch(gtw_08: GTW08):
    """Test that the temperature of a CH zone is the room temperature."""

    assert gtw_08.zones[0].current_temparature == gtw_08.zones[0].room_temperature == 23.2


@pytest.mark.asyncio
async def test_climate_zone_dhw_scheduling_setpoint(gtw_08: GTW08):
    """Test that the DHW setpoint follows the timeslot that is active."""

    zone = gtw_08.zones[1]
    assert zone.mode is ClimateZoneMode.SCHEDULING
    await zone.async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_1, dict.fromkeys(Weekday, _DHW_SCHEDULE)
    )
    await gtw_08.async_update()
    assert zone.dhw_comfort_setpoint == 55.0
    assert zone.dhw_reduced_setpoint == 25.0

    # The zone time zone is Europe/Amsterdam, which is UTC+2 in summer.
    with freeze_time("2026-06-01 04:00:00"):  # 06:00
        assert zone.current_setpoint == 25.0
    with freeze_time("2026-06-01 08:00:00"):  # 10:00
        assert zone.current_setpoint == 55.0
    with freeze_time("2026-06-01 10:59:00"):  # 12:59
        assert zone.current_setpoint == 55.0
    with freeze_time("2026-06-01 11:00:00"):  # 13:00
        assert zone.current_setpoint == 25.0
    with freeze_time("2026-06-01 17:00:00"):  # 19:00
        assert zone.current_setpoint == 55.0
    with freeze_time("2026-06-01 20:00:00"):  # 22:00
        assert zone.current_setpoint == 25.0


@pytest.mark.asyncio
async def test_climate_zone_dhw_scheduling_without_schedule(gtw_08: GTW08):
    """Test that a DHW zone in scheduling mode without time slots has no setpoint."""

    zone = gtw_08.zones[1]
    await zone.async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_1, {day: [] for day in Weekday}
    )
    await gtw_08.async_update()

    assert zone.mode is ClimateZoneMode.SCHEDULING
    assert zone.current_setpoint is None


@pytest.mark.asyncio
async def test_climate_zone_dhw_scheduling_setpoint_of_other_activity(gtw_08: GTW08):
    """Test that a timeslot that is neither ECO nor COMFORT does not give a DHW setpoint."""

    zone = gtw_08.zones[1]
    away = [Timeslot(TimeslotSetpointType.AWAY, TimeslotActivity.DHW, time(0, 0))]
    await zone.async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_1, dict.fromkeys(Weekday, away)
    )
    await gtw_08.async_update()

    assert zone.current_setpoint is None


@pytest.mark.asyncio
@freeze_time("2026-06-01 10:00:00")  # 12:00 in Europe/Amsterdam
async def test_climate_zone_dhw_temporary_setpoint_override(gtw_08: GTW08):
    """Test that an active temporary setpoint takes precedence over the DHW schedule."""

    zone = gtw_08.zones[1]
    await zone.async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_1, dict.fromkeys(Weekday, _DHW_SCHEDULE)
    )
    now = datetime.now(tz=tz.gettz("Europe/Amsterdam"))
    update_raw_data(
        gtw_08,
        [
            (663 + _DHW_ZONE_OFFSET, 275),  # 27.5 °C
            *_end_time_registers(now + timedelta(hours=1)),
        ],
    )
    await gtw_08.async_update()

    assert zone.temporary_room_setpoint == 27.5
    assert zone.current_setpoint == 27.5


@pytest.mark.asyncio
@freeze_time("2026-06-01 10:00:00")  # 12:00 in Europe/Amsterdam
async def test_climate_zone_dhw_expired_temporary_setpoint_is_ignored(gtw_08: GTW08):
    """Test that a temporary setpoint that has ended is ignored."""

    zone = gtw_08.zones[1]
    await zone.async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_1, dict.fromkeys(Weekday, _DHW_SCHEDULE)
    )
    now = datetime.now(tz=tz.gettz("Europe/Amsterdam"))
    update_raw_data(
        gtw_08,
        [
            (663 + _DHW_ZONE_OFFSET, 275),
            *_end_time_registers(now - timedelta(minutes=1)),
        ],
    )
    await gtw_08.async_update()

    assert zone.temporary_room_setpoint == 27.5
    assert zone.current_setpoint == 55.0  # 12:00 is within the comfort timeslot.


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["modbus_store_ch_scheduling.json"], indirect=True)
async def test_climate_zone_ch_temporary_setpoint_expires(gtw_08: GTW08):
    """Test that a temporary setpoint in scheduling mode is active for two hours."""

    zone = gtw_08.zones[0]
    assert zone.mode is ClimateZoneMode.SCHEDULING

    with freeze_time("2026-06-01 10:00:00"):
        scheduled = zone.current_setpoint
        assert scheduled is not None
        await zone.async_set_current_setpoint(scheduled + 1.0)
        assert zone.current_setpoint == scheduled + 1.0

    with freeze_time("2026-06-01 11:59:00"):
        await zone.async_update()
        assert zone.current_setpoint == scheduled + 1.0

    with freeze_time("2026-06-01 12:01:00"):
        await zone.async_update()
        assert zone.current_setpoint == scheduled


@pytest.mark.asyncio
async def test_climate_zone_ch_scheduling_without_time_slots(
    gtw_08: GTW08, caplog: pytest.LogCaptureFixture
):
    """Test that a CH zone in scheduling mode without time slots has no setpoint."""

    zone = gtw_08.zones[0]
    await zone.async_set_mode(ClimateZoneMode.SCHEDULING)
    await zone.async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_4, {day: [] for day in Weekday}
    )
    await gtw_08.async_update()
    assert zone.selected_schedule is ClimateZoneScheduleId.SCHEDULE_4

    with caplog.at_level(logging.WARNING):
        assert zone.current_setpoint is None

    assert "current timeslot failed to resolve" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method", ["_get_cooling_scheduling_setpoint", "_get_heating_scheduling_setpoint"]
)
async def test_climate_zone_scheduling_setpoint_unknown_type(
    gtw_08: GTW08, method: str, caplog: pytest.LogCaptureFixture
):
    """Test that a setpoint type that is not known gives no setpoint, and a warning."""

    zone = gtw_08.zones[0]

    with caplog.at_level(logging.WARNING):
        assert getattr(zone, method)(SimpleNamespace(name="BOGUS")) is None

    assert "Unknown setpoint type BOGUS for climate zone 1" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("setpoint_type", "field"),
    [
        (TimeslotSetpointType.ECO, 1),
        (TimeslotSetpointType.COMFORT, 2),
        (TimeslotSetpointType.AWAY, 3),
        (TimeslotSetpointType.MORNING, 4),
        (TimeslotSetpointType.EVENING, 5),
    ],
)
async def test_climate_zone_scheduling_setpoint_mapping(
    gtw_08: GTW08, setpoint_type: TimeslotSetpointType, field: int
):
    """Test which setpoint belongs to which timeslot setpoint type."""

    zone = gtw_08.zones[0]
    update_raw_data(
        gtw_08,
        [(649 + n, 200 + n) for n in range(1, 6)] + [(655 + n, 250 + n) for n in range(1, 6)],
    )
    await zone.async_update()

    assert zone._get_heating_scheduling_setpoint(setpoint_type) == (200 + field) / 10  # noqa: SLF001
    assert zone._get_cooling_scheduling_setpoint(setpoint_type) == (250 + field) / 10  # noqa: SLF001


@pytest.mark.asyncio
async def test_climate_zone_set_current_schedule_invalid_length(gtw_08: GTW08):
    """Test that a schedule without a value for every weekday is refused."""

    zone = gtw_08.zones[1]
    unit = get_modbus_unit(gtw_08)
    before = dict(unit.holding)

    with pytest.raises(RemehaApiError) as exc_info:
        await zone.async_set_current_schedule(
            ClimateZoneScheduleId.SCHEDULE_1, dict.fromkeys(list(Weekday)[:-1], _DHW_SCHEDULE)
        )

    assert exc_info.value.translation_key == "invalid_schedule"
    assert unit.holding == before


@pytest.mark.asyncio
async def test_climate_zone_set_current_schedule_none_clears_day(gtw_08: GTW08):
    """Test that a day without a schedule is written as an empty list of slots."""

    zone = gtw_08.zones[1]
    schedule: dict[Weekday, list[Timeslot] | None] = dict.fromkeys(Weekday, _DHW_SCHEDULE)
    schedule[Weekday.SUNDAY] = None

    await zone.async_set_current_schedule(ClimateZoneScheduleId.SCHEDULE_1, schedule)
    await gtw_08.async_update()

    assert zone.current_schedule[Weekday.SUNDAY] == []
    assert zone.current_schedule[Weekday.SATURDAY] == _DHW_SCHEDULE


@pytest.mark.asyncio
async def test_climate_zone_set_current_schedule_selects_schedule(gtw_08: GTW08):
    """Test that the schedule is selected only if it isn't selected yet."""

    zone = gtw_08.zones[1]
    unit = get_modbus_unit(gtw_08)
    written: list[int] = []
    unit.on_write(lambda event: written.append(event.address))
    selected_schedule_register = 688 + _DHW_ZONE_OFFSET
    assert zone.selected_schedule is ClimateZoneScheduleId.SCHEDULE_1

    await zone.async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_1, dict.fromkeys(Weekday, _DHW_SCHEDULE)
    )
    assert selected_schedule_register not in written

    await zone.async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_3, dict.fromkeys(Weekday, _DHW_SCHEDULE)
    )
    assert selected_schedule_register in written
    assert unit.holding[selected_schedule_register] == ClimateZoneScheduleId.SCHEDULE_3.value


@pytest.mark.asyncio
async def test_climate_zone_set_current_schedule_writes_selected_schedule_only(gtw_08: GTW08):
    """Test that only the time program of the given schedule is changed."""

    zone = gtw_08.zones[1]
    await zone.async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_1, dict.fromkeys(Weekday, _DHW_SCHEDULE)
    )
    other = [Timeslot(TimeslotSetpointType.COMFORT, TimeslotActivity.DHW, time(0, 0))]
    await zone.async_set_current_schedule(
        ClimateZoneScheduleId.SCHEDULE_2, dict.fromkeys(Weekday, other)
    )

    await zone.async_set_selected_schedule(ClimateZoneScheduleId.SCHEDULE_1)
    await gtw_08.async_update()
    assert zone.current_schedule == dict.fromkeys(Weekday, _DHW_SCHEDULE)

    await zone.async_set_selected_schedule(ClimateZoneScheduleId.SCHEDULE_2)
    await gtw_08.async_update()
    assert zone.current_schedule == dict.fromkeys(Weekday, other)


@pytest.mark.asyncio
async def test_climate_zone_equality_ignores_other_state(
    gtw_08: GTW08, remeha_modbus_unit: MockModbusUnit
):
    """Test that zones are equal if id, type and function are equal."""

    same = ClimateZone(remeha_modbus_unit, sequence_id=1)
    await same.async_update()
    other_id = ClimateZone(remeha_modbus_unit, sequence_id=2)
    await other_id.async_update()

    assert gtw_08.zones[0] == same
    assert gtw_08.zones[0] != other_id
    assert gtw_08.zones[1] == other_id
    assert gtw_08.zones[0] != "zone"
    assert gtw_08.zones[0] != None  # noqa: E711


@pytest.mark.asyncio
async def test_climate_zone_hash(gtw_08: GTW08):
    """Test that zones can be used in sets."""

    assert hash(gtw_08.zones[0]) == hash(gtw_08.zones[0])
    assert len({gtw_08.zones[0], gtw_08.zones[0]}) == 1
    assert len({gtw_08.zones[0], gtw_08.zones[1]}) == 2


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="ClimateZone.__hash__ hashes the attribute names, so equal zones can hash differently.",
)
async def test_climate_zone_equal_zones_have_equal_hashes(
    gtw_08: GTW08, remeha_modbus_unit: MockModbusUnit
):
    """Test that zones that are equal also have the same hash."""

    same = ClimateZone(remeha_modbus_unit, sequence_id=1)
    await same.async_update()

    assert gtw_08.zones[0] == same
    assert hash(gtw_08.zones[0]) == hash(same)
