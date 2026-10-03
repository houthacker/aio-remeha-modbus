"""GTW-08 ClimateZone Protocol implementation."""

from aio_remeha_modbus.gtw08.climate_zone import ClimateZone, ClimateZoneFunction


class Gtw08ClimateZone:
    """A GTW-08 circuit."""

    _zone: ClimateZone

    def __init__(self, zone: ClimateZone):
        """Create a new ``Gtw08ClimateZone``."""

        self._zone = zone

    @property
    def disabled(self) -> bool:
        return self._zone.function is ClimateZoneFunction.DISABLED

    @property
    def id(self) -> int:
        return self._zone.id

    @property
    def name(self) -> str:
        return self._zone.short_name

    @property
    def current_temperature(self) -> float:
        return self._zone.current_temparature

    @property
    def current_setpoint(self) -> float | None:
        return self._zone.current_setpoint

    async def async_set_current_setpoint(self, setpoint: float) -> None:
        await self._zone.async_set_current_setpoint(setpoint)
