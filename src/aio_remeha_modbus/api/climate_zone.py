"""Implementation of climate zones within the Remeha Modbus integration."""

import logging
from datetime import datetime, tzinfo
from enum import IntEnum
from functools import cached_property, lru_cache
from typing import cast

from modbus_connection import ModbusUnit
from modbus_connection.model import Component, boolean, enum, gauge, integer, string

from aio_remeha_modbus.api.const import (
    REMEHA_ZONE_RESERVED_REGISTERS,
    ClimateZoneScheduleId,
    Limits,
    Weekday,
)
from aio_remeha_modbus.api.schedule import (
    Timeslot,
    TimeslotSetpointType,
    ZoneSchedule,
    get_current_timeslot,
    is_cooling_schedule,
)
from aio_remeha_modbus.helpers.fields import binary
from aio_remeha_modbus.helpers.gtw08 import TimeOfDay

_LOGGER = logging.getLogger(__name__)


class ClimateZoneType(IntEnum):
    """Enumerates the available zone types."""

    NOT_PRESENT = 0
    CH_ONLY = 1
    CH_AND_COOLING = 2
    DHW = 3
    PROCESS_HEAT = 4
    SWIMMING_POOL = 5
    OTHER = 254


class ClimateZoneFunction(IntEnum):
    """Enumerates the available zone functions."""

    DISABLED = 0
    DIRECT = 1
    MIXING_CIRCUIT = 2
    SWIMMING_POOL = 3
    HIGH_TEMPERATURE = 4
    FAN_CONVECTOR = 5
    DHW_TANK = 6
    ELECTRICAL_DHW_TANK = 7
    TIME_PROGRAM = 8
    PROCESS_HEAT = 9
    DHW_LAYERED = 10
    DHW_BIC = 11
    DHW_COMMERCIAL_TANK = 12
    DHW_PRIMARY = 254

    def is_supported(self) -> bool:
        """Return whether this `ClimateZoneFunction` is currently supported within this integration."""
        return self in [
            ClimateZoneFunction.MIXING_CIRCUIT,
            ClimateZoneFunction.DHW_PRIMARY,
        ]

    def has_cooling_capability(self) -> bool:
        """Return whether this `ClimateZoneFunction` supports cooling."""
        return self in [
            ClimateZoneFunction.MIXING_CIRCUIT,
            ClimateZoneFunction.FAN_CONVECTOR,
        ]


class ClimateZoneMode(IntEnum):
    """Enumerates the modes a zone can be in."""

    SCHEDULING = 0
    MANUAL = 1
    ANTI_FROST = 2


class ClimateZoneHeatingMode(IntEnum):
    """The mode the zone is currently functioning in."""

    STANDBY = 0
    HEATING = 1
    COOLING = 2


def _map_selected_schedule(
    zone_mode: ClimateZoneMode,
    zone_function: ClimateZoneFunction,
    appliance_requires_cooling: bool,
    selected_schedule: int | None,
) -> ClimateZoneScheduleId | None:
    """Map `selected_schedule` to the correct `ClimateZoneScheduleId`.

    Remeha uses `SCHEDULE_4` for cooling schedules but writing that to modbus
    causes an exception. Instead, Remeha uses `SCHEDULE_1` in this case and
    the cooling schedule usage must be derived from the appliance/zone state.
    """
    return (
        ClimateZoneScheduleId.SCHEDULE_4
        if zone_mode is ClimateZoneMode.SCHEDULING
        and zone_function.has_cooling_capability()
        and appliance_requires_cooling
        else (ClimateZoneScheduleId(selected_schedule) if selected_schedule is not None else None)
    )


def is_domestic_hot_water(type: ClimateZoneType, function: ClimateZoneFunction) -> bool:
    """Return whether the given type and function resolve to a DHW zone type."""

    return type == ClimateZoneType.DHW or (
        type == ClimateZoneType.OTHER
        and function
        in [
            ClimateZoneFunction.DHW_BIC,
            ClimateZoneFunction.DHW_COMMERCIAL_TANK,
            ClimateZoneFunction.DHW_LAYERED,
            ClimateZoneFunction.DHW_PRIMARY,
            ClimateZoneFunction.DHW_TANK,
            ClimateZoneFunction.ELECTRICAL_DHW_TANK,
        ]
    )


def is_central_heating(type: ClimateZoneType, function: ClimateZoneFunction) -> bool:
    """Return whether the given type and function resolve to a CH zone type.

    This method is meant to be used by the API, in situations where no `ClimateZone`
    is available (yet).
    """

    return type in [
        ClimateZoneType.CH_ONLY,
        ClimateZoneType.CH_AND_COOLING,
    ] or (type == ClimateZoneType.OTHER and function == ClimateZoneFunction.MIXING_CIRCUIT)


class _DaySchedule(Component):
    """A component representing the raw bytes of a zone schedule for a single day."""

    id: ClimateZoneScheduleId

    zone_id: int

    _data = binary(address=689, count=10, writable=True, stride=10)
    """The binary schedule data."""

    def __init__(
        self,
        unit: ModbusUnit,
        index: int = 1,
        id: ClimateZoneScheduleId = ClimateZoneScheduleId.SCHEDULE_1,
        zone_id: int = 1,
    ):
        super().__init__(unit=unit, index=index)
        self.id = id
        self.zone_id = zone_id

    @cached_property
    def schedule(self) -> ZoneSchedule | None:
        """Decode the zone schedule bytes into a ZoneSchedule."""

        if self._data is None:
            return None

        day = Weekday(self._index - 1)
        return ZoneSchedule.decode(
            id=self.id, zone_id=self.zone_id, day=day, encoded_schedule=self._data
        )


class ClimateZone(Component):
    """Defines a climate zone following the GTW-08 parameter list.

    In the GTW-08 parameter list, a climate zone contains all fields for all zone types.
    The API must stay as close as possible to the original mapping and therefore a
    `ClimateZone` does not differentiate between zone types.
    However, the entities created from `ClimateZone` instances have distinct types for all supported zone types.
    """

    register_ranges = ((640, 646), (648, 980), (1100, 1120))

    type = enum(address=640, enum_type=ClimateZoneType, nan=0xFF)
    """The type of climate zone"""

    function = enum(address=641, enum_type=ClimateZoneFunction, nan=0xFF)
    """The climate zone function"""

    short_name = string(address=642, length=3)
    """The climate zone short name"""

    owning_device = integer(address=646, signed=False, nan=0xFFFF)
    """The id of the device owning the zone."""

    mode = enum(address=649, enum_type=ClimateZoneMode, nan=0xFF)
    """The current mode the zone is in"""

    room_cooling_setpoint_1 = gauge(
        address=656, scale=0.1, signed=False, nan=0xFFFF, writable=True, unit="°C"
    )
    """Cooling setpoint in ECO mode"""

    room_cooling_setpoint_2 = gauge(
        address=657, scale=0.1, signed=False, nan=0xFFFF, writable=True, unit="°C"
    )
    """Cooling setpoint in COMFORT mode"""

    room_cooling_setpoint_3 = gauge(
        address=658, scale=0.1, signed=False, nan=0xFFFF, writable=True, unit="°C"
    )
    """Cooling setpoint in AWAY mode"""

    room_cooling_setpoint_4 = gauge(
        address=659, scale=0.1, signed=False, nan=0xFFFF, writable=True, unit="°C"
    )
    """Cooling setpoint in MORNING mode"""

    room_cooling_setpoint_5 = gauge(
        address=660, scale=0.1, signed=False, nan=0xFFFF, writable=True, unit="°C"
    )
    """Cooling setpoint in EVENING mode"""

    temporary_setpoint = gauge(
        address=663, scale=0.1, signed=False, nan=0xFFFF, writable=True, unit="°C"
    )
    """Temporary room setpoint override. Only available when mode is SCHEDULING."""

    room_setpoint = gauge(
        address=664, scale=0.1, signed=False, nan=0xFFFF, writable=True, unit="°C"
    )
    """The current room temperature setpoint"""

    dhw_comfort_setpoint = gauge(
        address=665, scale=0.01, signed=False, nan=0xFFFF, writable=True, unit="°C"
    )
    """The setpoint for DHW in comfort mode"""

    dhw_reduced_setpoint = gauge(
        address=666, scale=0.01, signed=False, nan=0xFFFF, writable=True, unit="°C"
    )
    """The setpoint for DHW in reduced (eco) mode"""

    dhw_calorifier_hysteresis = gauge(
        address=686, scale=0.01, signed=False, nan=0xFFFF, writable=True, unit="°C"
    )
    """Hysteresis to start DHW tank load"""

    selected_schedule = enum(address=688, enum_type=ClimateZoneScheduleId, nan=0xFF, writable=True)
    """The currently selected schedule.

    Although this property is optional, it needn't be `None` if `mode != ClimateZoneMode.SCHEDULING`.
    """

    _temporary_setpoint_end_time = binary(address=978, count=3, writable=True)
    """End time of temporary setpoint override"""

    room_temperature = gauge(address=1104, scale=0.1, nan=0x8000, unit="°C")
    """The current room temperature"""

    heating_mode = enum(address=1109, enum_type=ClimateZoneHeatingMode, nan=0xFF)
    """The current heating mode of the climate zone"""

    pump_running = boolean(address=1110)
    """Whether the zone pump is currently running"""

    dhw_tank_temperature = gauge(address=1119, scale=0.01, nan=0x8000, unit="°C")
    """The current DHW tank temperature"""

    time_zone: tzinfo | None
    """The time zone of the related appliance"""

    appliance_requires_cooling: bool = False
    """Whether the related appliance requires cooling"""

    @property
    def id(self) -> int:
        """The one-based climate zone id."""

        return int(self._base_offset / REMEHA_ZONE_RESERVED_REGISTERS) + 1

    @lru_cache
    async def async_current_schedule(self) -> dict[Weekday, ZoneSchedule | None]:
        """If `selected_schedule` has a value, `current_schedule` contains that schedule for all week days."""

        empty_schedule = dict.fromkeys(Weekday)
        if self.mode is None or self.function is None:
            return empty_schedule

        selected_schedule = self.selected_schedule
        schedule_id = (
            _map_selected_schedule(
                zone_mode=self.mode,
                zone_function=self.function,
                appliance_requires_cooling=self.appliance_requires_cooling,
                selected_schedule=selected_schedule,
            )
            if selected_schedule is not None
            else None
        )
        if schedule_id is None:
            return empty_schedule

        schedule = empty_schedule.copy()
        for day in Weekday:
            day_schedule = _DaySchedule(self._unit, day + 1, id=schedule_id, zone_id=self.id)
            await day_schedule.async_update()

            schedule[day] = day_schedule.schedule

        return schedule

    @property
    def temporary_setpoint_end_time(self) -> datetime | None:
        """Get the end time of the temporary setpoint override.

        The returned `datetime` is in the configured time zone of `self.time_zone`.
        """

        if self._temporary_setpoint_end_time is None:
            return None

        return TimeOfDay.from_bytes(
            data=self._temporary_setpoint_end_time, time_zone=self.time_zone
        )

    def __init__(
        self,
        unit: ModbusUnit,
        *,
        base_offset: int = 0,
        time_zone: tzinfo | None = None,
        appliance_requires_cooling: bool = False,
    ) -> None:
        """Create a new ClimateZone component.

        Raises:
            AssertionError if `base_offset`is not a multiple of `REMEHA_ZONE_RESERVED_REGISTERS`

        """
        assert base_offset % REMEHA_ZONE_RESERVED_REGISTERS == 0, (
            f"ClimateZone base offset must be divisible by {REMEHA_ZONE_RESERVED_REGISTERS}, which {base_offset} is not."
        )

        super().__init__(unit, 1, base_offset=base_offset)

        self.time_zone = time_zone
        self.appliance_requires_cooling = appliance_requires_cooling

    def _get_cooling_scheduling_setpoint(self, setpoint_type: TimeslotSetpointType) -> float | None:
        match setpoint_type:
            case TimeslotSetpointType.ECO:
                return self.room_cooling_setpoint_1
            case TimeslotSetpointType.COMFORT:
                return self.room_cooling_setpoint_2
            case TimeslotSetpointType.AWAY:
                return self.room_cooling_setpoint_3
            case TimeslotSetpointType.MORNING:
                return self.room_cooling_setpoint_4
            case TimeslotSetpointType.EVENING:
                return self.room_cooling_setpoint_5

        _LOGGER.warning("Unknown setpoint type %s for climate zone %d", setpoint_type.name, self.id)
        return -1

    def _get_heating_scheduling_setpoint(self, setpoint_type: TimeslotSetpointType) -> float:
        raise NotImplementedError

    async def _async_get_current_ch_scheduling_setpoint(self) -> float | None:
        if self.temporary_setpoint_end_time is not None:
            if (
                self.temporary_setpoint_end_time is not None
                and self.temporary_setpoint_end_time >= datetime.now(tz=self.time_zone)
            ):
                # A setpoint override is currently active.
                return cast(float, self.temporary_setpoint)

        schedule = await self.async_current_schedule()
        current_timeslot: Timeslot | None = get_current_timeslot(
            schedule=schedule, time_zone=self.time_zone
        )

        if current_timeslot is None:
            _LOGGER.warning(
                "Cannot determine current CH setpoint because current timeslot failed to resolve."
            )
            return -1

        if is_cooling_schedule(schedule, self.time_zone):
            return self._get_cooling_scheduling_setpoint(current_timeslot.setpoint_type)

        return self._get_heating_scheduling_setpoint(current_timeslot.setpoint_type)

    async def _async_get_current_dhw_scheduling_setpoint(self) -> float | None:
        if self.temporary_setpoint_end_time is not None:
            if (
                self.temporary_setpoint_end_time is not None
                and self.temporary_setpoint_end_time >= datetime.now(tz=self.time_zone)
            ):
                # A setpoint override is currently active.
                return cast(float, self.temporary_setpoint)

        current_timeslot: Timeslot | None = get_current_timeslot(
            schedule=await self.async_current_schedule(), time_zone=self.time_zone
        )
        if current_timeslot is not None:
            match current_timeslot.setpoint_type:
                case TimeslotSetpointType.ECO:
                    return self.dhw_reduced_setpoint
                case TimeslotSetpointType.COMFORT:
                    return self.dhw_comfort_setpoint

        return -1

    async def async_get_current_setpoint(self) -> float | None:
        """Return the current setpoint of this zone.

        The actual returned setpoint field depends on the type of zone and
        the current zone mode.

        Returns:
            `float`: The current zone setpoint, or `-1` if zone type or mode does not support a current setpoint.

        """

        if self.is_central_heating():
            match self.mode:
                case ClimateZoneMode.SCHEDULING:
                    return await self._async_get_current_ch_scheduling_setpoint()
                case ClimateZoneMode.MANUAL:
                    return self.room_setpoint
                case ClimateZoneMode.ANTI_FROST:
                    return self.min_temp
        if self.is_domestic_hot_water():
            match self.mode:
                case ClimateZoneMode.SCHEDULING:
                    return await self._async_get_current_dhw_scheduling_setpoint()
                case ClimateZoneMode.MANUAL:
                    return self.dhw_comfort_setpoint
                case ClimateZoneMode.ANTI_FROST:
                    return self.dhw_reduced_setpoint

        _LOGGER.warning("Current setpoint not supported for climate zones of type %s", self.type)
        return -1

    def set_current_setpoint(self, value: float):
        """Set the current setpoint of this zone."""

        # Check requested setpoint against min/max
        if value < self.min_temp or value > self.max_temp:
            _LOGGER.warning(
                "Ignoring requested setpoint of %0.2f since it is outside allowed range (%0.2f, %0.2f)",
                value,
                self.min_temp,
                self.max_temp,
            )
            return

        if self.is_central_heating():
            match self.mode:
                case ClimateZoneMode.SCHEDULING:
                    # Ignore, user must adjust schedule.
                    # TODO implement temporary setpoint override
                    _LOGGER.warning(
                        "Not setting CH climate temporary setpoint, adjust schedule to do this."
                    )
                case ClimateZoneMode.MANUAL:
                    self.room_setpoint = value
                case _:
                    pass

        elif self.is_domestic_hot_water():
            match self.mode:
                case ClimateZoneMode.SCHEDULING:
                    # The required end time is set by the HA climate entity.
                    self.temporary_setpoint = value
                case ClimateZoneMode.MANUAL:
                    self.dhw_comfort_setpoint = value
                case ClimateZoneMode.ANTI_FROST:
                    self.dhw_reduced_setpoint = value
        else:
            _LOGGER.warning(
                "Setting setpoint not supported for climate zones of type %s", self.type
            )

    @property
    def current_temparature(self) -> float:
        """Return the current temperature of this zone.

        The actual returned temperature field depends on the type of zone.
        """

        if self.is_central_heating():
            return cast(float, self.room_temperature)

        if self.is_domestic_hot_water():
            return cast(float, self.dhw_tank_temperature)

        _LOGGER.warning("Current temperature not supported for climate zones of type %s", self.type)
        return -1

    @property
    def max_temp(self) -> float:
        """The highest allowed setpoint for this zone.

        The maximum temperature differs per zone type:
        * For DHW (Domestinc Hot Water) it's 65 degrees C
        * For CH (Central Heating) or mixing circuits it's 30 degrees C
        * For all others it's the lowest value of the above.
        This is to ensure unknown zone types won't get a flow temperature they can't handle.
        """

        if self.is_central_heating():
            return Limits.CH_MAX_TEMP

        if self.is_domestic_hot_water():
            return Limits.DHW_MAX_TEMP

        return min(Limits.CH_MAX_TEMP, Limits.DHW_MAX_TEMP)

    @property
    def min_temp(self) -> float:
        """The lowest allowed setpoint for this zone.

        The minimum temperature differs per zone type:
        * For DHW (Domestinc Hot Water) it's 6 degrees C
        * For CH (Central Heating) or mixing circuits it's 10 degrees C
        * For all others it's the highest value of the above.
        This is to ensure unknown zone types won't get a flow temperature they can't handle.
        """

        if self.is_central_heating():
            return Limits.CH_MIN_TEMP

        if self.is_domestic_hot_water():
            return Limits.DHW_MIN_TEMP

        return max(Limits.CH_MIN_TEMP, Limits.DHW_MIN_TEMP)

    def has_cooling_capability(self) -> bool:
        """Whether this type of climate zone is capable of cooling."""

        return cast(ClimateZoneFunction, self.function).has_cooling_capability()

    def is_central_heating(self) -> bool:
        """Determine if this zone is a CH (central heating) zone."""

        return is_central_heating(
            cast(ClimateZoneType, self.type), cast(ClimateZoneFunction, self.function)
        )

    def is_domestic_hot_water(self) -> bool:
        """Determine if this zone is a DHW (domestic hot water) zone."""

        return is_domestic_hot_water(
            cast(ClimateZoneType, self.type), cast(ClimateZoneFunction, self.function)
        )

    async def async_set_room_cooling_setpoint_1(self, value: float):
        """Write the `ECO` room setpoint."""

        await self.write("room_cooling_setpoint_1", value)

    async def async_set_room_cooling_setpoint_2(self, value: float):
        """Write the `COMFORT` room setpoint."""

        await self.write("room_cooling_setpoint_2", value)

    async def async_set_room_cooling_setpoint_3(self, value: float):
        """Write the `AWAY` room setpoint."""

        await self.write("room_cooling_setpoint_3", value)

    async def async_set_room_cooling_setpoint_4(self, value: float):
        """Write the `MORNING` room setpoint."""

        await self.write("room_cooling_setpoint_4", value)

    async def async_set_room_cooling_setpoint_5(self, value: float):
        """Write the `EVENING` room setpoint."""

        await self.write("room_cooling_setpoint_5", value)

    def __eq__(self, other) -> bool:
        """Compare this `ClimateZone` with another for equality.

        For equality, only the properties `id`, `type` and `function` are considered.

        Returns:
            `bool`: `True` if the objects are considered equal, `False` otherwise.

        """
        if isinstance(other, self.__class__):
            return (
                self.id == other.id and self.type == other.type and self.function == other.function
            )

        return False

    def __hash__(self) -> int:
        """Return a hash of this zone."""

        return hash(vars(self))
