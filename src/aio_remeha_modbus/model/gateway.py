"""Gateway protocol for GTW-08 and GTW-26 instances."""

from abc import abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from modbus_connection.model import UpdateReport

    from aio_remeha_modbus.model.climate_zone import ClimateZone


class GatewayType(StrEnum):
    """Describe the supported gateway types."""

    GTW08 = "gtw08"
    """The GTW-08 is an internal Modbus RTU module.

    This module is compatible with the Remeha Ace platform and some
    specific heat pumps.
    """

    GTW26 = "gtw26"
    """The GTW-26 is an external Modbus RTU module.

    This module is compatible with DIEMATIC System (d3, iSystem) control panels.
    """


@runtime_checkable
class Gateway(Protocol):
    """Represent a unified interface over GTW-08 and GTW-26 modbus gateway devices."""

    @abstractmethod
    async def async_update(self) -> UpdateReport:
        """Refresh all components.

        Raises:
          ``ModbusConnectionError`` if any of the underlying components cannot be read due to this error.
          ``ModbusTimeoutError`` if the modbus subsystem does not reply in time.

        """

    @property
    @abstractmethod
    def number_of_zones(self) -> int | None:
        """The number of zones managed by the appliance.

        Returns:
          The number of zones, or `None` if the gateway was not yet polled.

        """

    @property
    @abstractmethod
    def zones(self) -> list[ClimateZone]:
        """The zones managed by the appliance."""
