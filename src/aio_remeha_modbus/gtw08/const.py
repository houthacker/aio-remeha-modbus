"""Constants for the Remeha Modbus API."""

from datetime import date
from enum import Enum, IntEnum, StrEnum
from typing import Final

from pydantic.dataclasses import dataclass

# Error translation keys
TK_CONFIG_DICT_MISSING_KEY: Final[str] = "config_dict_missing_key"

# Base register information for zones, device info, time schedules
REMEHA_MAX_SPAN: Final[int] = 40
"""Largest single block read is 40 registers"""

REMEHA_ZONE_RESERVED_REGISTERS: Final[int] = 512
"""The register count of a `ClimateZone`."""

REMEHA_DEVICE_BOARD_RESERVED_REGISTERS: Final[int] = 6
"""The register count of a `DeviceBoard`."""

REMEHA_TIME_PROGRAM_RESERVED_REGISTERS: Final[int] = 70
"""The register count of a full time program for all days of the week (`dict[Weekday, ZoneSchedule]`)."""

REMEHA_TIME_PROGRAM_BYTE_SIZE: Final[int] = 20
"""The byte size of a single encoded `ZoneSchedule`."""

REMEHA_DAY_SCHEDULE_RESERVED_REGISTERS: Final[int] = 10
"""The register size of a single `DaySchedule`."""

REMEHA_TIME_PROGRAM_SLOT_SIZE: Final[int] = 3
"""The byte size of a single encoded `Timeslot`."""

REMEHA_TIME_STEP_MINUTES: Final[int] = 10
"""The duration of a single time step in a `SteppedTimeOfDay`."""

AUTO_SCHEDULE_MINIMAL_END_HOUR: Final[int] = 21
"""The minimal latest hour required to create a useful auto schedule.

This means that if a schedule is planned before this hour, it cannot succeed
because then no full day can be planned ahead.
"""

BOILER_MAX_ALLOWED_HEAT_DURATION: Final[int] = 3
"""The maximum amount of hours the boiler will get to heat up.

If the central heating- the heat pump unit can modulate, this
is the estimated amount of time required since that is most
energy-efficient. When the unit is unable to modulate, this time
is much shorter, but it will cost more energy.
"""

MAXIMUM_NORMAL_SURFACE_IRRADIANCE_NL: Final[int] = 1000
"""The maximum normal surface irradiance in The Netherlands, in W/m²"""


PV_MIN_TILT_DEGREES: Final[int] = 10
"""The minimum supported PV system tilt"""

PV_MAX_TILT_DEGREES: Final[int] = 90
"""The maximum supported PV system tilt"""

WATER_SPECIFIC_HEAT_CAPACITY_KJ: Final[float] = 4.18
"""The amount of energy required to warm 1 kilogram of water by one degree K"""


class BoilerEnergyLabel(StrEnum):
    """Energy label for DHW boiler.

    The energy label is used to provide an alternative method of calculating heat loss rate.
    See also https://www.energielabel.nl/apparaten/boiler-en-geiser (Dutch)
    """

    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


@dataclass(frozen=True)
class BoilerConfiguration:
    """The configuration of a DHW boiler."""

    volume: Final[float | None]
    """The volume of the boiler in m³"""

    heat_loss_rate: Final[float | None]
    """The heat loss rate in Watt"""

    energy_label: Final[BoilerEnergyLabel | None]
    """The boiler energy label, if the heat loss rate is not available."""


class ClimateZoneScheduleId(IntEnum):
    """The climate zone time program selected by the user.

    Note: After updating the enum values, **ALWAYS** update the mapping to _attr_preset_modes of RemehaModbusClimateEntity!
    """

    SCHEDULE_1 = 0
    SCHEDULE_2 = 1
    SCHEDULE_3 = 2
    SCHEDULE_4 = 3

    def is_cooling_schedule(self) -> bool:
        """Return whether this id refers to a cooling schedule."""

        return self is ClimateZoneScheduleId.SCHEDULE_4


class SeasonalMode(IntEnum):
    """Defines the current seasonal mode of the appliance."""

    WINTER = 0

    WINTER_FROST_PROTECTION = 1

    SUMMER_NEUTRAL_BAND = 2

    SUMMER = 3


# DHW auto scheduling
class ForecastField(StrEnum):
    """Describe the weather forecast action response field names that are relevant for this integration."""

    DATETIME = "datetime"
    CONDITION = "condition"
    TEMPERATURE = "temperature"
    PRECIPITATION = "precipitation"
    SOLAR_IRRADIANCE = "solar_irradiance"
    """Solar irradiance is not a field that's available by default"""


class PVSystemOrientation(StrEnum):
    """Describe the PV system orientations."""

    EAST_WEST = "EW"
    """East/West evenly distributes total PV power over east and west."""
    NORTH = "N"
    NORTH_NORTH_EAST = "NNE"
    NORTH_EAST = "NE"
    EAST_NORTH_EAST = "ENE"
    EAST = "E"
    EAST_SOUTH_EAST = "ESE"
    SOUTH_EAST = "SE"
    SOUTH_SOUTH_EAST = "SSE"
    SOUTH = "S"
    SOUTH_SOUTH_WEST = "SSW"
    SOUTH_WEST = "SW"
    WEST_SOUTH_WEST = "WSW"
    WEST = "W"
    WEST_NORTH_WEST = "WNW"
    NORTH_WEST = "NW"
    NORTH_NORTH_WEST = "NNW"


@dataclass(frozen=True)
class PVSystem:
    """Parameters that describe a PV system."""

    nominal_power: Final[int]
    """The total Wp of the system."""

    orientation: Final[PVSystemOrientation]
    """The direction the PV system faces."""

    tilt: Final[float | None]
    """The tilt of the PV system, in degrees."""

    annual_efficiency_decrease: Final[float | None]
    """The annual decrease of efficiency, in percent."""

    installation_date: Final[date | None]
    """The installation date """


PV_EFFICIENCY_TABLE = {
    PVSystemOrientation.NORTH: {
        10: 0.77,
        20: 0.68,
        30: 0.59,
        40: 0.50,
        50: 0.40,
        60: 0.35,
        70: 0.30,
        80: 0.25,
        90: 0.20,
    },
    PVSystemOrientation.NORTH_NORTH_EAST: {
        10: 0.78,
        20: 0.70,
        30: 0.59,
        40: 0.50,
        50: 0.45,
        60: 0.39,
        70: 0.35,
        80: 0.30,
        90: 0.25,
    },
    PVSystemOrientation.NORTH_EAST: {
        10: 0.79,
        20: 0.73,
        30: 0.65,
        40: 0.59,
        50: 0.53,
        60: 0.46,
        70: 0.42,
        80: 0.38,
        90: 0.35,
    },
    PVSystemOrientation.EAST_NORTH_EAST: {
        10: 0.83,
        20: 0.78,
        30: 0.73,
        40: 0.68,
        50: 0.62,
        60: 0.57,
        70: 0.52,
        80: 0.46,
        90: 0.42,
    },
    PVSystemOrientation.EAST: {
        10: 0.85,
        20: 0.82,
        30: 0.80,
        40: 0.76,
        50: 0.72,
        60: 0.67,
        70: 0.62,
        80: 0.55,
        90: 0.50,
    },
    PVSystemOrientation.EAST_SOUTH_EAST: {
        10: 0.87,
        20: 0.87,
        30: 0.86,
        40: 0.85,
        50: 0.81,
        60: 0.76,
        70: 0.71,
        80: 0.65,
        90: 0.58,
    },
    PVSystemOrientation.SOUTH_EAST: {
        10: 0.90,
        20: 0.92,
        30: 0.93,
        40: 0.92,
        50: 0.87,
        60: 0.84,
        70: 0.78,
        80: 0.71,
        90: 0.62,
    },
    PVSystemOrientation.SOUTH_SOUTH_EAST: {
        10: 0.91,
        20: 0.94,
        30: 0.96,
        40: 0.95,
        50: 0.92,
        60: 0.88,
        70: 0.82,
        80: 0.75,
        90: 0.65,
    },
    PVSystemOrientation.SOUTH: {
        10: 0.91,
        20: 0.95,
        30: 0.97,
        40: 0.96,
        50: 0.94,
        60: 0.90,
        70: 0.84,
        80: 0.75,
        90: 0.65,
    },
    PVSystemOrientation.SOUTH_SOUTH_WEST: {
        10: 0.91,
        20: 0.95,
        30: 0.96,
        40: 0.95,
        50: 0.92,
        60: 0.87,
        70: 0.82,
        80: 0.74,
        90: 0.68,
    },
    PVSystemOrientation.SOUTH_WEST: {
        10: 0.90,
        20: 0.92,
        30: 0.93,
        40: 0.92,
        50: 0.87,
        60: 0.84,
        70: 0.78,
        80: 0.70,
        90: 0.63,
    },
    PVSystemOrientation.WEST_SOUTH_WEST: {
        10: 0.87,
        20: 0.87,
        30: 0.87,
        40: 0.85,
        50: 0.81,
        60: 0.76,
        70: 0.71,
        80: 0.64,
        90: 0.57,
    },
    PVSystemOrientation.WEST: {
        10: 0.85,
        20: 0.82,
        30: 0.80,
        40: 0.76,
        50: 0.72,
        60: 0.68,
        70: 0.62,
        80: 0.55,
        90: 0.49,
    },
    PVSystemOrientation.WEST_NORTH_WEST: {
        10: 0.82,
        20: 0.77,
        30: 0.71,
        40: 0.68,
        50: 0.62,
        60: 0.57,
        70: 0.52,
        80: 0.46,
        90: 0.42,
    },
    PVSystemOrientation.NORTH_WEST: {
        10: 0.79,
        20: 0.72,
        30: 0.65,
        40: 0.59,
        50: 0.52,
        60: 0.47,
        70: 0.43,
        80: 0.38,
        90: 0.34,
    },
    PVSystemOrientation.NORTH_NORTH_WEST: {
        10: 0.78,
        20: 0.69,
        30: 0.60,
        40: 0.51,
        50: 0.44,
        60: 0.39,
        70: 0.35,
        80: 0.30,
        90: 0.26,
    },
}


class Limits(float, Enum):
    """Forced limits users must not exceed."""

    CH_MIN_TEMP = 6.0
    """Central heating minimum temperature."""

    CH_MAX_TEMP = 30.0
    """Central heating maximum temperature."""

    DHW_MIN_TEMP = 10.0
    """Domestic hot water minimum temperature."""

    DHW_MAX_TEMP = 65.0
    """Domestic hot water maximum temperature."""

    SCHEDULING_SETPOINT_OVERRIDE_DURATION = 2
    """The duration in hours of a temporary setpoint override in DHW scheduling."""

    HYSTERESIS_MIN_TEMP = 0.0
    """The minimum required hysteresis."""

    HYSTERESIS_MAX_TEMP = 40.0
    """The maximum allowed hysteresis."""


class UnitOfTemperature(StrEnum):
    """Temperature units."""

    CELSIUS = "°C"
    FAHRENHEIT = "°F"
    KELVIN = "K"


class Weekday(IntEnum):
    """Enumeration for days of the week."""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6
