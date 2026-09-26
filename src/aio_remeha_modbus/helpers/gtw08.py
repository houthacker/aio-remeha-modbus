"""GTW-08 helper functions."""

from datetime import datetime, time, timedelta, tzinfo
from enum import IntEnum
from typing import Final, Self, cast, overload

from dateutil import relativedelta
from pydantic.dataclasses import dataclass

from aio_remeha_modbus.api.const import REMEHA_TIME_PROGRAM_SLOT_SIZE as SLOT_SIZE
from aio_remeha_modbus.api.const import REMEHA_TIME_STEP_MINUTES, Weekday


class SteppedTimeOfDay:
    """Encoding to and from 'stepped' time.

    This concerns time encoded using the amount of ten-minute
    steps since midnight.
    """

    @overload
    @classmethod
    def from_steps(cls, steps: int, step_minutes: int = REMEHA_TIME_STEP_MINUTES) -> time: ...

    @overload
    @classmethod
    def from_steps(
        cls, steps: int | None, step_minutes: int = REMEHA_TIME_STEP_MINUTES
    ) -> time | None: ...

    @classmethod
    def from_steps(
        cls, steps: int | None, step_minutes: int = REMEHA_TIME_STEP_MINUTES
    ) -> time | None:
        """Decode time steps to a time of day.

        Args:
          steps (int): The amount of time steps since midnight.
          step_minutes (int): The step size in minutes. Defaults to `REMEHA_TIME_STEP_MINUTES`.

        """

        if steps is None:
            return None

        delta = relativedelta.relativedelta(minutes=steps * step_minutes)
        return time(delta.hours, delta.minutes, 0)

    @classmethod
    def to_steps(cls, time_of_day: time, step_minutes: int = REMEHA_TIME_STEP_MINUTES) -> int:
        """Encode a time of day to time steps since midnight.

        Args:
          time_of_day (time): The time of day to encode.
          step_minutes (int): The step size in minutes. Defaults to `REMEHA_TIME_STEP_MINUTES`.

        Returns:
          The amount of time steps since midnight.
          Non-integer steps are ignored, meaning 1.9 steps will count as 1.

        """

        minutes = time_of_day.hour * 60 + time_of_day.minute
        return int(minutes / step_minutes)


class TimeOfDay:
    """Encoding to and decoding from a CiA 301 TIME_OF_DAY struct."""

    _CIA301_TOD_BASE_DATE: Final[datetime] = datetime(year=1984, month=1, day=1, hour=0, minute=0)

    @classmethod
    def from_bytes(cls, data: bytes, time_zone: tzinfo | None = None) -> datetime:
        """Decode a CiA 301 TIME_OF_DAY to a `datetime` object.

        `TIME_OF_DAY` is a struct that is defined as follows:
        | Field     | Type            | Size (bits) |
        |-----------|----------------:|------------:|
        | `ms`      | `unsigned int`  |     28      |
        |`<padding>`| `N/A`           |      4      |
        | `days`    | `unsigned int`  |     16      |

        * `TIME_OF_DAY.ms` is the amount of milliseconds since midnight
        * `TIME_OF_DAY.days` is the amount of days since 1984-01-01.

        **Notes**:
          * This method assumes that naive `datetime` instances are in `time_zone`.
          * This method assumes that the Remeha appliance operates in time zone `time_zone`.

        Args:
          data (bytes): The encoded TIME_OF_DAY struct.
          time_zone (str): The name of the Home Assistant time zone, defaults to the local time zone of the running OS.

        Returns:
          datetime: The decoded `TIME_OF_DAY` struct.

        Raises:
          `ValueError` if `time_zone` is an invalid time zone string or if `len(data) != 6`.

        """

        if len(data) != 6:
            raise ValueError(
                f"Cannot decode data into datetime: data must be exactly 6 bytes, but got {len(data)}"
            )

        ms = int.from_bytes(
            data[2:4] + data[0:2],
        ) & int("0fffffff", 16)
        days = int.from_bytes(
            data[4:],
        )

        return cls._CIA301_TOD_BASE_DATE.replace(tzinfo=time_zone) + timedelta(
            days=days, milliseconds=ms
        )

    @classmethod
    def to_bytes(cls, dt: datetime) -> bytes:
        """Encode a `datetime` object to a CiA 301 TIME_OF_DAY.

        Args:
          dt (datetime): The datetime to encode into a `TIME_OF_DAY` struct.

        Returns:
          The timestamp, encoded in a `TIME_OF_DAY` struct.

        """
        delta: timedelta = dt - cls._CIA301_TOD_BASE_DATE.replace(tzinfo=dt.tzinfo)

        ms = int(delta.seconds * 1000 + delta.microseconds / 1000) & int("0fffffff", 16)
        days = delta.days

        ms_bytes: bytes = ms.to_bytes(4)
        return ms_bytes[2:4] + ms_bytes[0:2] + days.to_bytes(2)


class TimeslotActivity(IntEnum):
    """The type of activity that must run during the containing TimeSlot."""

    HEAT_COOL = int("c8", 16)
    DHW = int("00", 16)


class TimeslotSetpointType(IntEnum):
    """The setpoint that must be reached during the containing TimeSlot.

    The names used here are the default names as shown in the Remeha Home app. In the app, these names
    can be changed.
    """

    ECO = 0
    """Reduced setpoint. For `TimeslotActivity.HEAT_COOL` this is named 'Sleeping' in the Remeha Home app. """

    COMFORT = int("10", 16)
    """Comfort setpoint. For `TimeslotActivity.HEAT_COOL` this is named 'At home' in the Remeha Home app."""

    AWAY = int("20", 16)
    """Setpoint in 'away' mode."""

    MORNING = int("30", 16)
    """Setpoint in 'morning' mode."""

    EVENING = int("40", 16)
    """Setpoint in 'evening' mode."""


@dataclass(frozen=True)
class Timeslot:
    """A zone schedule time slot."""

    setpoint_type: TimeslotSetpointType
    """The type of setpoint for this time slot."""

    activity: TimeslotActivity
    """The type of activity for this time slot."""

    switch_time: time
    """The start time of this time slot."""

    def encode(self) -> bytes:
        """Encode this time slot into a `bytes` object."""

        time_steps: int = SteppedTimeOfDay.to_steps(self.switch_time)

        return (
            int(self.activity.value).to_bytes()
            + int(self.setpoint_type.value).to_bytes()
            + time_steps.to_bytes()
        )

    def __lt__(self, other) -> bool:
        """Compare this `Timeslot` to another."""
        if isinstance(other, Timeslot):
            o: Timeslot = cast(Timeslot, other)
            return self.switch_time < o.switch_time

        return False

    def __str__(self):
        """Return a human-readable representation of this time slot."""
        return f"Timeslot(setpoint_type={self.setpoint_type.name}, activity={self.activity.name}, switch_time={self.switch_time})"

    @classmethod
    def decode(cls, encoded_time_slot: bytes) -> Self:
        """Decode a `bytes` object intoa a `Timeslot`.

        Args:
            encoded_time_slot (bytes): The encoded time slot. Must be 3 bytes.

        Raises:
            `ValueError`: If `encoded_time_slot` is not exactly 3 bytes.

        """
        # slot_bytes must be exactly 3 bytes.
        if len(encoded_time_slot) != SLOT_SIZE:
            raise ValueError(
                f"Cannot decode time program: require time slot of {SLOT_SIZE} bytes but got {len(encoded_time_slot)}."
            )

        time_steps = int.from_bytes(encoded_time_slot[2:3])
        setpoint_type = TimeslotSetpointType(int.from_bytes(encoded_time_slot[1:2]))
        activity = TimeslotActivity(int.from_bytes(encoded_time_slot[:1]))

        return cls(
            activity=activity,
            setpoint_type=setpoint_type,
            switch_time=SteppedTimeOfDay.from_steps(time_steps),
        )


def get_current_timeslot(
    schedule: dict[Weekday, list[Timeslot] | None],
    time_zone: tzinfo | None,
) -> Timeslot | None:
    """Retrieve the current schedule time slot.

    Args:
        schedule (list[DaySchedule]): The selected schedule
        time_zone (datetime.tzinfo): The appliance time zone

    Returns:
        The current schedule time slot, or `None` if `schedule` is `None`.

    """

    if schedule is None:
        return None

    now: datetime = datetime.now(time_zone)
    weekday = now.weekday()
    time_slots: list[Timeslot] | None = schedule.get(Weekday(weekday))

    return next(
        reversed(
            [
                time_slot
                for time_slot in cast(list[Timeslot], time_slots)
                if time_slots is not None
                if time_slot.switch_time.hour <= now.hour
            ]
        ),
        None,
    )
