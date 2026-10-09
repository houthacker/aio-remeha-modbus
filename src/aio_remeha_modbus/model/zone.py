"""Provide a unified view of climate zones exposed by a ``Gateway``."""

from enum import IntEnum, IntFlag, auto
from typing import Protocol

from aio_remeha_modbus.model.const import ZoneScheduleId


class Capabilities(IntFlag):
    """Describe the capabilities of a zone."""

    HEAT = auto()
    """The zone is able to heat to reach a target temperature."""

    COOL = auto()
    """The zone is able to cool to reach a target temperature."""


class OperatingMode(IntEnum):
    """Describe climate zone operating modes."""

    SCHEDULING = 0
    """The zone toggles between the configured presets based on the time of day."""

    MANUAL = 1
    """The zone maintains a fixed setpoint."""

    ANTI_FROST = 2
    """The zone is turned off, except for freezing prevention measures."""


class ZoneType(IntEnum):
    """Describe the zone types."""

    DHW = 0
    """The zone is a Domestic Hot Water zone.

    A zone of this type produces and stores hot water for taps,
    showers, baths etc., independent of central heating.
    """

    CH = 1
    """The zone is a Central Heating zone.

    A zone of this type controls the temperature in a (group of) room(s).
    """


class ZoneActivity(IntEnum):
    """A ``ZoneActivity`` describes the current activity that the appliance is performing."""

    STANDBY = 0
    """The zone is currently idle, but an action will be performed if necessary."""

    HEATING = 1
    """The zone is actively being heated."""

    COOLING = 2
    """The zone is actively being cooled."""


class Zone(Protocol):
    """A heating-, cooling or mixed circuit that can be independently controlled."""

    @property
    def name(self) -> str | None:
        """A short name describing this zone.

        Examples:
            - `CIRCA`
            - `A`

        """

    @property
    def current_setpoint(self) -> float | None:
        """The current target temperature in °C."""

    @property
    def current_temperature(self) -> float | None:
        """The current temperature of the zone in °C.

        What measurement resolves to the current temperature differs per
        type of zone. For example, a heating- or cooling circuit returns
        the current room temperature while a domestic hot water circuit
        returns the temperature at the top or bottom of the tank.
        """

    @property
    def max_setpoint(self) -> float:
        """The maximum setpoint for this zone."""

    @property
    def min_setpoint(self) -> float:
        """The minimum setpoint for this zone."""

    @property
    def operating_mode(self) -> OperatingMode:
        """The operating mode of this zone.

        The operating mode controls how the zone determines
        its ``current_activity``.
        """

    @property
    def current_activity(self) -> ZoneActivity:
        """The zone activity currently performed by the appliance."""

    @property
    def capabilities(self) -> Capabilities:
        """The capabilities of this zone."""

    @property
    def zone_type(self) -> ZoneType:
        """The type of this zone."""

    @property
    def selected_schedule(self) -> ZoneScheduleId:
        """The selected zone schedule.

        A schedule can be 'selected' here while the zone is running
        in a different mode. To check if the zone is indeed following
        the selected schedule, ``self.operating_mode`` must be `SCHEDULING`.

        """

    async def async_set_current_setpoint(self, setpoint: float) -> None:
        """Set the target temperature for this zone."""

    async def async_set_operating_mode(self, mode: OperatingMode) -> None:
        """Set the operating mode for this zone."""

    async def async_set_selected_schedule(self, schedule: ZoneScheduleId) -> None:
        """Set the selected schedule for this zone.

        To ensure the zone will follow the schedule, ``self.operating_mode`` must
        be set to `SCHEDULING`.
        """
