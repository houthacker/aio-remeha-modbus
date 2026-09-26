"""Test GTW-08 helper."""

from datetime import UTC, datetime, time
from typing import Final

import pytest
from dateutil import tz
from freezegun import freeze_time

from aio_remeha_modbus.gtw08.const import Weekday
from aio_remeha_modbus.gtw08.time_program import Timeslot, TimeslotActivity, TimeslotSetpointType
from aio_remeha_modbus.helpers.gtw08 import SteppedTimeOfDay, TimeOfDay, get_current_timeslot


def test_time_of_day_encode():
    """Test that encoding and decoding a value returns the same value."""

    # Simulate an aware datetime coming from Home Assistant
    expected: Final[datetime] = datetime(
        year=2025,
        month=4,
        day=28,
        hour=18,
        minute=00,
        second=00,
        tzinfo=tz.gettz("Europe/Amsterdam"),
    )

    encoded = TimeOfDay.to_bytes(expected)
    assert encoded == b"\xc5\x00\x03\xdc\x3a\xf5"


def test_time_of_day_decode():
    """Test decoding a bytes object into a datetime."""

    expected: Final[datetime] = datetime(
        year=2025,
        month=4,
        day=28,
        hour=18,
        minute=00,
        second=00,
        tzinfo=tz.gettz("Europe/Amsterdam"),
    )

    byte_string: bytes = b"\xc5\x00\x03\xdc\x3a\xf5"
    assert TimeOfDay.from_bytes(byte_string, tz.gettz(name="Europe/Amsterdam")) == expected


def test_time_of_day_round_trip():
    """Test that a datetime with milliseconds survives a round trip."""

    expected: Final[datetime] = datetime(
        2026, 1, 15, 7, 30, 15, 250000, tzinfo=tz.gettz("Europe/Amsterdam")
    )

    assert (
        TimeOfDay.from_bytes(TimeOfDay.to_bytes(expected), tz.gettz("Europe/Amsterdam")) == expected
    )


@pytest.mark.parametrize("length", [0, 5, 7])
def test_time_of_day_from_bytes_invalid_length(length: int):
    """Test that decoding data that is not 6 bytes long is refused."""

    with pytest.raises(ValueError, match="exactly 6 bytes"):
        TimeOfDay.from_bytes(bytes(length))


def test_time_of_day_from_bytes_naive():
    """Test that decoding without a time zone gives a naive datetime."""

    decoded = TimeOfDay.from_bytes(b"\xc5\x00\x03\xdc\x3a\xf5")
    assert decoded == datetime(2025, 4, 28, 18, 0, 0)
    assert decoded.tzinfo is None


@pytest.mark.parametrize(
    ("steps", "expected"),
    [(0, time(0, 0)), (1, time(0, 10)), (6, time(1, 0)), (143, time(23, 50))],
)
def test_stepped_time_of_day_from_steps(steps: int, expected: time):
    """Test decoding steps to a time of day."""

    assert SteppedTimeOfDay.from_steps(steps) == expected


def test_stepped_time_of_day_from_steps_none():
    """Test that `None` steps decode to `None`."""

    assert SteppedTimeOfDay.from_steps(None) is None


def test_stepped_time_of_day_step_minutes():
    """Test that a custom step size is used."""

    assert SteppedTimeOfDay.from_steps(3, step_minutes=15) == time(0, 45)
    assert SteppedTimeOfDay.to_steps(time(0, 45), step_minutes=15) == 3


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (time(0, 0), 0),
        (time(0, 9), 0),
        (time(0, 10), 1),
        (time(1, 19), 7),
        (time(23, 59), 143),
    ],
)
def test_stepped_time_of_day_to_steps(value: time, expected: int):
    """Test that encoding truncates to whole steps."""

    assert SteppedTimeOfDay.to_steps(value) == expected


def _timeslot(hour: int, setpoint: TimeslotSetpointType = TimeslotSetpointType.COMFORT) -> Timeslot:
    """Create a timeslot at the given hour."""

    return Timeslot(
        switch_time=time(hour, 0),
        setpoint_type=setpoint,
        activity=TimeslotActivity.HEAT_COOL,
    )


def test_get_current_timeslot_none():
    """Test that no schedule means no current timeslot."""

    assert get_current_timeslot(None, tz.gettz("Europe/Amsterdam")) is None  # pyright: ignore[reportArgumentType]


@freeze_time("2026-06-01 12:30:00")  # a monday
def test_get_current_timeslot_no_slots_for_day():
    """Test that a day without timeslots has no current timeslot."""

    assert get_current_timeslot({Weekday.MONDAY: None}, UTC) is None
    assert get_current_timeslot({}, UTC) is None


@freeze_time("2026-06-01 12:30:00")  # a monday
def test_get_current_timeslot_latest_started():
    """Test that the latest timeslot that has started is returned."""

    slots = [_timeslot(6), _timeslot(10), _timeslot(14)]

    assert get_current_timeslot({Weekday.MONDAY: slots}, UTC) == slots[1]


@freeze_time("2026-06-01 05:59:00")  # a monday
def test_get_current_timeslot_before_first_slot():
    """Test that there is no current timeslot before the first one starts."""

    assert get_current_timeslot({Weekday.MONDAY: [_timeslot(6)]}, UTC) is None


@freeze_time("2026-06-01 22:00:00")  # a monday, but already tuesday in Amsterdam
def test_get_current_timeslot_uses_time_zone():
    """Test that the weekday is determined in the given time zone."""

    monday = [_timeslot(6)]
    tuesday = [_timeslot(0)]
    schedule = {Weekday.MONDAY: monday, Weekday.TUESDAY: tuesday}

    assert get_current_timeslot(schedule, UTC) == monday[0]
    assert get_current_timeslot(schedule, tz.gettz("Europe/Amsterdam")) == tuesday[0]
