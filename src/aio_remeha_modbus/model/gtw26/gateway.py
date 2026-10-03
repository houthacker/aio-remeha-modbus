"""GTW-26 Gateway protocol implementation."""

from typing import override

from modbus_connection.model import UpdateReport

from aio_remeha_modbus.gtw26.gtw26 import GTW26


class Gtw26Gateway:
    """Implementation of the ``Gateway`` protocol for the GTW-26."""

    _gateway: GTW26

    def __init__(self, gateway: GTW26):
        """Create a new ``Gtw26Gateway`` instance."""

        self._gateway = gateway

    @override
    async def async_update(self) -> UpdateReport:
        return await self._gateway.async_update()

    @property
    @override
    def number_of_zones(self) -> int | None:
        return len(self._gateway.climate_zones) if self._gateway.climate_zones else None
