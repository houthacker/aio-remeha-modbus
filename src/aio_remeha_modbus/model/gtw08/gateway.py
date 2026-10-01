"""GTW-08 Gateway protocol implementation."""

from typing import override

from modbus_connection.model import UpdateReport

from aio_remeha_modbus.gtw08.gtw08 import GTW08
from aio_remeha_modbus.model.climate_zone import ClimateZone
from aio_remeha_modbus.model.gtw08.climate_zone import Gtw08ClimateZone


class Gtw08Gateway:
    """Implementation of the ``Gateway`` protocol for the GTW-08."""

    _gateway: GTW08
    """The actual modbus gateway."""

    def __init__(self, gateway: GTW08) -> None:
        """Create a new ``Gtw08gateway`` instance."""

        self._gateway = gateway

    @override
    async def async_update(self) -> UpdateReport:
        return await self._gateway.async_update()

    @property
    @override
    def number_of_zones(self) -> int | None:
        return self._gateway.discovery_table.number_of_zones

    @property
    @override
    def zones(self) -> list[ClimateZone]:
        return [Gtw08ClimateZone(zone) for zone in self._gateway.zones]
