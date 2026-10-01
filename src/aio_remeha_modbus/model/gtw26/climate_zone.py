"""GTW-26 ClimateZone Protocol implementation."""

from typing import Any, Protocol

from aio_remeha_modbus.helpers.fields import Float10Field


class _ClimateZone(Protocol):
    """A base protocol for GTW-26 limate zone classes."""

    designation: str
    """A short zone name like `A`, `B` or `C`."""

    room_temperature: Float10Field
    """The current room temperature in °C."""

    calculated_temperature: Float10Field
    """The outlet setpoint in °C."""

    async def write(self, field: str, value: Any) -> None:
        """Write a writable register or coil by attribute name."""


class Gtw26ClimateZone:
    """A GTW-26 circuit."""

    _zone: _ClimateZone

    def __init__(self, zone: _ClimateZone) -> None:
        """Create a new ``Gtw26ClimateZone``."""

        self._zone = zone

    @property
    def enabled(self) -> bool:
        """Whether this circuit is enabled in the related appliance."""

    @property
    def id(self) -> int:
        """The one-based sequence id of this circuit."""

    @property
    def name(self) -> str:
        """A short name of this circuit.

        Examples are `CIRCA` and `DHW`.
        """

    @property
    def current_temperature(self) -> float:
        return self._zone.room_temperature

    @property
    def current_setpoint(self) -> float | None:
        return self._zone.calculated_temperature

    async def async_set_current_setpoint(self, setpoint: float) -> None:
        await self._zone.write("calculated_temperature", setpoint)
