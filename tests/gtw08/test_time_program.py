"""Tests for the time program encoding."""

from datetime import time

import pytest
from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.gtw08.const import REMEHA_TIME_PROGRAM_BYTE_SIZE, Weekday
from aio_remeha_modbus.gtw08.errors import InvalidZoneSchedule
from aio_remeha_modbus.gtw08.time_program import (
    DaySchedule,
    TimeProgram,
    TimeProgramField,
    Timeslot,
    TimeslotActivity,
    TimeslotSetpointType,
    time_slots,
)
from aio_remeha_modbus.helpers.fields import decode_bytes, encode_bytes


def _slot(
    hour: int,
    minute: int = 0,
    setpoint_type: TimeslotSetpointType = TimeslotSetpointType.COMFORT,
    activity: TimeslotActivity = TimeslotActivity.HEAT_COOL,
) -> Timeslot:
    """Create a `Timeslot`."""

    return Timeslot(setpoint_type=setpoint_type, activity=activity, switch_time=time(hour, minute))


def test_timeslot_encode():
    """Test that a timeslot is encoded as activity, setpoint type and time steps."""

    assert _slot(6).encode() == bytes.fromhex("c81024")
    assert _slot(22, 30, TimeslotSetpointType.ECO).encode() == bytes.fromhex("c80087")
    assert _slot(
        0, 0, TimeslotSetpointType.COMFORT, TimeslotActivity.DHW
    ).encode() == bytes.fromhex("001000")


def test_timeslot_decode():
    """Test that bytes are decoded into a timeslot."""

    assert Timeslot.decode(bytes.fromhex("c8302a")) == _slot(7, 0, TimeslotSetpointType.MORNING)
    assert Timeslot.decode(bytes.fromhex("000006")) == _slot(
        1, 0, TimeslotSetpointType.ECO, TimeslotActivity.DHW
    )


@pytest.mark.parametrize("activity", list(TimeslotActivity))
@pytest.mark.parametrize("setpoint_type", list(TimeslotSetpointType))
def test_timeslot_round_trip(activity: TimeslotActivity, setpoint_type: TimeslotSetpointType):
    """Test that decoding an encoded timeslot gives the same timeslot."""

    timeslot = _slot(13, 40, setpoint_type, activity)

    assert Timeslot.decode(timeslot.encode()) == timeslot


def test_timeslot_encode_truncates_to_time_steps():
    """Test that a switch time that is not a multiple of 10 minutes is truncated."""

    assert Timeslot.decode(_slot(7, 59).encode()) == _slot(7, 50)


@pytest.mark.parametrize("length", [0, 1, 2, 4])
def test_timeslot_decode_invalid_length(length: int):
    """Test that decoding bytes that are not exactly 3 bytes long is refused."""

    with pytest.raises(ValueError, match="require time slot of 3 bytes"):
        Timeslot.decode(bytes(length))


def test_timeslot_decode_unknown_values():
    """Test that an unknown activity or setpoint type is refused."""

    with pytest.raises(ValueError, match="is not a valid TimeslotSetpointType"):
        Timeslot.decode(bytes.fromhex("c8ff00"))

    with pytest.raises(ValueError, match="is not a valid TimeslotActivity"):
        Timeslot.decode(bytes.fromhex("aa1000"))


@pytest.mark.parametrize(
    ("is_dhw", "activity"),
    [(True, TimeslotActivity.DHW), (False, TimeslotActivity.HEAT_COOL)],
)
def test_timeslot_create_default(is_dhw: bool, activity: TimeslotActivity):
    """Test the default timeslot for both zone kinds."""

    default = Timeslot.create_default(is_dhw=is_dhw)

    assert default.activity is activity
    assert default.setpoint_type is TimeslotSetpointType.ECO
    assert default.switch_time == time(0, 0)


def test_timeslot_ordering():
    """Test that timeslots are ordered by switch time."""

    early, late = _slot(6), _slot(18)

    assert early < late
    assert not late < early
    assert sorted([late, early]) == [early, late]
    assert not early < early  # noqa: PLR0124


def test_timeslot_ordering_other_type():
    """Test that comparing to something else is never 'less than'."""

    assert (_slot(6) < 5) is False
    assert (_slot(6) < time(23)) is False


def test_timeslot_str():
    """Test the human-readable representation."""

    assert (
        str(_slot(6, 30, TimeslotSetpointType.AWAY))
        == "Timeslot(setpoint_type=AWAY, activity=HEAT_COOL, switch_time=06:30:00)"
    )


def test_timeslot_is_frozen():
    """Test that a timeslot cannot be modified."""

    with pytest.raises(AttributeError):
        _slot(6).switch_time = time(7)  # pyright: ignore[reportAttributeAccessIssue]


def test_time_program_field_encode():
    """Test that the slots are encoded with a count and padded to 20 bytes."""

    field = time_slots(address=1)
    encoded = field.encode([_slot(6), _slot(22, 30, TimeslotSetpointType.ECO)])

    assert len(encoded) == 10
    assert decode_bytes(encoded) == bytes.fromhex("02c81024c80087") + bytes(13)


def test_time_program_field_encode_empty():
    """Test that an empty schedule is encoded as a count of zero."""

    assert decode_bytes(time_slots(address=1).encode([])) == bytes(REMEHA_TIME_PROGRAM_BYTE_SIZE)


def test_time_program_field_encode_maximum():
    """Test that the maximum number of slots fits exactly."""

    slots = [_slot(hour) for hour in range(TimeProgramField.max_element_count)]
    encoded = decode_bytes(time_slots(address=1).encode(slots))

    assert TimeProgramField.max_element_count == 6
    assert encoded[0] == 6
    assert len(encoded) == REMEHA_TIME_PROGRAM_BYTE_SIZE


def test_time_program_field_encode_too_many_slots():
    """Test that more than the maximum number of slots is refused."""

    slots = [_slot(hour) for hour in range(TimeProgramField.max_element_count + 1)]

    with pytest.raises(ValueError, match="Too many Timeslots to encode"):
        time_slots(address=1).encode(slots)


def test_time_program_field_decode():
    """Test that only the announced number of slots is decoded."""

    words = encode_bytes(bytes.fromhex("02c81024c80087") + bytes(13))

    assert time_slots(address=1).decode(words) == [
        _slot(6),
        _slot(22, 30, TimeslotSetpointType.ECO),
    ]


def test_time_program_field_decode_empty():
    """Test that a count of zero decodes into an empty list."""

    assert time_slots(address=1).decode([0] * 10) == []


def test_time_program_field_decode_nan():
    """Test that the nan value is decoded into `None`."""

    words = encode_bytes(TimeProgramField.nan_bytes)

    assert time_slots(address=1).decode(words) is None


@pytest.mark.parametrize("word_count", [0, 1, 9, 11])
def test_time_program_field_decode_invalid_length(word_count: int):
    """Test that a number of registers other than 10 is refused."""

    with pytest.raises(ValueError, match="require 20 bytes"):
        time_slots(address=1).decode([0] * word_count)


def test_time_program_field_decode_invalid_slot():
    """Test that an unparsable slot is reported as an `InvalidZoneSchedule`."""

    words = encode_bytes(bytes.fromhex("01151515") + bytes(16))

    with pytest.raises(InvalidZoneSchedule) as exc_info:
        time_slots(address=1).decode(words)

    assert exc_info.value.translation_key == "invalid_time_program"


def test_time_program_field_round_trip():
    """Test that encoding and decoding gives back the same slots."""

    field = time_slots(address=1)
    slots = [_slot(hour, 10 * hour % 60) for hour in range(6)]

    assert field.decode(field.encode(slots)) == slots


def test_time_program_field_word_order():
    """Test that the word order of the field is applied."""

    field = TimeProgramField(address=1, word_order="little")
    slots = [_slot(6)]

    assert field.encode(slots)[0] == int.from_bytes(bytes.fromhex("01c8"), "little")
    assert field.decode(field.encode(slots)) == slots


def test_time_slots_factory():
    """Test that the factory creates a field of ten registers."""

    field = time_slots(address=899, writable=True, stride=10)

    assert isinstance(field, TimeProgramField)
    assert field.address == 899
    assert field.count == 10


@pytest.mark.asyncio
async def test_day_schedule_set_time_slots(remeha_modbus_unit: MockModbusUnit):
    """Test that a day schedule writes its slots to the registers."""

    day = DaySchedule(remeha_modbus_unit)
    slots = [_slot(6), _slot(22, 30, TimeslotSetpointType.ECO)]

    await day.async_set_time_slots(slots)

    written = [int(remeha_modbus_unit.holding[689 + i]) for i in range(10)]
    assert decode_bytes(written) == bytes.fromhex("02c81024c80087") + bytes(13)
    assert day.slots == slots


@pytest.mark.asyncio
async def test_time_program_reads_all_weekdays(remeha_modbus_unit: MockModbusUnit):
    """Test that a time program contains a day schedule for every weekday."""

    program = TimeProgram(remeha_modbus_unit)
    await program.async_update()

    assert len(program.day_schedules) == len(Weekday)
