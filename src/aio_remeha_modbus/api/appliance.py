"""Implementation of appliance-scoped functionality."""

from datetime import time
from enum import IntEnum

from modbus_connection.model import Component, boolean, enum

from aio_remeha_modbus.helpers.fields import int16, uint8, uint16
from aio_remeha_modbus.helpers.gtw08 import SteppedTimeOfDay


class SilentMode(IntEnum):
    """Defines the silent mode of the appliance."""

    OFF = 0
    """Normal operation."""

    LEVEL_1 = 1
    """Silent mode."""

    LEVEL_2 = 2
    """Extra silent mode."""


class CoolingType(IntEnum):
    """Defines the type of cooling used by the appliance (if any)."""

    OFF = 0
    """Cooling is off."""

    ACTIVE_COOLING = 1
    """The appliance uses active cooling.

    This type of cooling is used by all air-sourced heat pumps.
    """

    FREE_COOLING = 2
    """The appliance uses free cooling.

    This type of cooling is used by geothermal and water-source
    heat pumps.
    """


class SeasonalMode(IntEnum):
    """Defines the current seasonal mode of the appliance."""

    WINTER = 0

    WINTER_FROST_PROTECTION = 1

    SUMMER_NEUTRAL_BAND = 2

    SUMMER = 3


class Appliance(Component):
    """Represents a Remeha appliance.

    An `Appliance` stores information about the appliance that cannot be linked to any of
    the other available api types, like appliance error status or burning hours counters.
    """

    outside_temperature = int16(address=384, scale=0.01, unit="°C")
    """The outside temperature."""

    season_mode = enum(address=385, enum_type=SeasonalMode, signed=False)
    """Which season mode is currently active."""

    summer_winter = uint16(address=386, scale=0.01, writable=True, unit="°C")
    """Upper limit of outdoor temperature for heating (30.5 means disabled)."""

    neutral_band_summer_winter = uint16(address=387, scale=0.01, unit="°C")
    """Temperature band below the summer/winter limit within which the appliance
    neither heats nor cools (parameter AP075)."""

    forced_summer_mode = boolean(address=389, nan=0xFF, writable=True)
    """Whether forced summer mode is active (parameter AP074)."""

    silent_mode = enum(address=490, enum_type=SilentMode, signed=False, nan=0xFF, writable=True)
    """The silent mode level of the appliance."""

    _silent_mode_start_time = uint8(address=491, writable=True)

    @property
    def silent_mode_start_time(self) -> time | None:
        """The time of day at which the silent mode starts."""

        return SteppedTimeOfDay.from_steps(self._silent_mode_start_time)

    _silent_mode_end_time = uint8(address=492, writable=True)

    @property
    def silent_mode_end_time(self) -> time | None:
        """The time of day at which the silent mode ends."""

        return SteppedTimeOfDay.from_steps(self._silent_mode_end_time)

    ch_enabled = boolean(address=500, nan=0xFF, writable=True)
    """Whether central heating demand processing is enabled."""

    cooling_type = enum(address=502, enum_type=CoolingType, signed=False, nan=0xFF, writable=True)
    """The type of cooling."""

    forced_cooling_mode = boolean(address=503, nan=0xFF, writable=True)
    """Whether the appliance is in forced cooling mode.

    This variable is defined on the appliance level. In the Remeha Home app however, this variable
    is configurable in two places: in the CH zone and at the system level. Change one, change
    the other too.
    In this integration, this value is shown in all CH climates and can be set as follows:
      * To force cooling, set HVACMode to COOL
      * To let the system decide to cool or heat, set HVACMode to HEAT_COOL
    """

    def is_cooling_required(self) -> bool:
        """Whether the appliance cooling mode is required.

        This can be forced (`cooling_forced == True`) or derived (`season_mode` is in a summer variant).
        """

        return self.forced_cooling_mode or self.season_mode in [
            SeasonalMode.SUMMER_NEUTRAL_BAND,
            SeasonalMode.SUMMER,
        ]

    async def set_summer_winter(self, value: float):
        """Set the outdoor temperature upper limit for heating."""

        await self.write("summer_winter", value)

    async def set_neutral_band_summer_winter(self, value: float):
        """Set the neutral band in which the heat pump is deactivated.

        Args:
            value: The bandwidth in °C

        """

        await self.write("neutral_band_summer_winter", value)

    async def enable_forced_summer_mode(self):
        """Stop heating, maintain hot water. Force summer mode."""

        await self.write("forced_summer_mode", True)

    async def disable_forced_summer_mode(self):
        """Do not force summer mode."""

        await self.write("forced_summer_mode", False)

    async def set_silent_mode(self, value: SilentMode):
        """Set the silent mode level."""
        await self.write("silent_mode", value)

    async def set_silent_mode_start_time(self, value: time):
        """Set the time of day at which the silent mode starts."""
        await self.write("_silent_mode_start_time", SteppedTimeOfDay.to_steps(value))

    async def set_silent_mode_end_time(self, value: time):
        """Set the time of day at which the silent mode ends."""
        await self.write("_silent_mode_end_time", SteppedTimeOfDay.to_steps(value))

    async def set_ch_enabled(self):
        """Enable central heat demand processing."""
        await self.write("ch_enabled", True)

    async def set_ch_disabled(self):
        """Disable central heat demand processing."""
        await self.write("ch_enabled", False)

    async def set_cooling_type(self, value: CoolingType):
        """Set the type of cooling for this appliance."""
        await self.write("cooling_type", value)
