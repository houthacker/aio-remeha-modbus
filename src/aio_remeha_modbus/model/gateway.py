"""Provide a unified protocol for GTW-08 and GTW-26."""

from typing import Protocol

from aio_remeha_modbus.model.appliance import Appliance
from aio_remeha_modbus.model.zone import Zone


class Gateway(Protocol):
    """A hardway interface gateway that connects to heating/cooling appliances."""

    @property
    def appliance(self) -> Appliance:
        """The appliance that controls the available zones."""

    @property
    def zones(self) -> list[Zone]:
        """List the configured climate zones of the appliance.

        Disabled zones are not exposed and must be enabled in the appliance
        before they're listed here.

        Returns:
          list[Zone]: The list of available climate zones.

        """
