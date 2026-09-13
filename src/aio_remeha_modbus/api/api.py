"""Implementation of the Remeha Modbus API."""

import logging
import struct
from datetime import tzinfo
from typing import Any

from modbus_connection import ModbusExceptionError, ModbusUnit
from modbus_connection.model import (
    Component,
    ManualComponent,
)

from aio_remeha_modbus.api.appliance import (
    Appliance,
)
from aio_remeha_modbus.api.climate_zone import (
    ClimateZone,
)
from aio_remeha_modbus.api.const import (
    REMEHA_MAX_SPAN,
    REMEHA_ZONE_RESERVED_REGISTERS,
)
from aio_remeha_modbus.api.errors import RemehaApiError, RemehaModbusError
from aio_remeha_modbus.api.main_control_monitoring import MainControlMonitoring
from aio_remeha_modbus.api.system_discovery_table import SystemDiscoveryTable
from aio_remeha_modbus.helpers.fields import decode_bytes, uint8

_LOGGER = logging.getLogger(__name__)


class RemehaApi:
    """Use instances of this class to interact with the Remeha device through Modbus."""

    def __init__(
        self,
        name: str,
        unit: ModbusUnit,
        time_zone: tzinfo | None = None,
    ):
        """Create a new API instance."""

        self._name = name
        self._unit = unit
        self._time_zone = time_zone

        self.discovery_table = SystemDiscoveryTable(unit)
        self.main_control_monitoring = MainControlMonitoring(unit)
        self.appliance = Appliance(unit)
        self.zones: list[ClimateZone] = []

    @staticmethod
    async def async_health_check(unit: ModbusUnit) -> None:
        """Verify if the system is reachable by reading a single register.

        Raises:
            RemehaModbusError: If the health check failed.

        """

        mc = ManualComponent(unit=unit)
        mc.add("number_of_devices", uint8(address=128))

        try:
            await mc.async_update()
        except ModbusExceptionError as e:
            raise RemehaModbusError("health_check_failed") from e

    async def _async_setup(self):
        await self.discovery_table.async_update()
        await self.main_control_monitoring.async_update()
        await self.appliance.async_update()

        if self.discovery_table.number_of_zones is None:
            raise RemehaApiError(translation_key="api_setup_number_of_zones")

        for idx in range(self.discovery_table.number_of_zones):
            climate_zone = ClimateZone(
                self._unit,
                base_offset=idx * REMEHA_ZONE_RESERVED_REGISTERS,
                sequence_id=idx + 1,
                time_zone=self._time_zone,
                appliance_requires_cooling=self.appliance.is_cooling_required(),
            )

            await climate_zone.async_update()
            self.zones.append(climate_zone)

    async def _async_update(self):

        component: Component
        for component in [self.main_control_monitoring, self.appliance, *self.zones]:
            await component.async_update()

    @property
    def name(self) -> str:
        """Return the modbus hub name."""
        return self._name

    async def async_read_registers(
        self, address: int, *, count: int = 1, struct_format: str | bytes = "=H"
    ) -> tuple[Any, ...]:
        """Read registers from the modbus interface for debugging purposes.

        Args:
            address (int): The register to start reading at.
            count (int): The amount of registers to read.
            struct_format (str | bytes): The struct format to convert the register bytes to.

        Returns:
            A tuple containing values unpacked according to the format string.

        Raises:
            ValueError: if `count` is smaller than 1 or larger than the maximum span defined for the GTW-08.
            ModbusError: if a modbus error occurred while reading the registers.
            struct.error: if `struct_format` is an illegal struct format.

        """

        if count < 1 or count > REMEHA_MAX_SPAN:
            raise ValueError(f"Illegal count {count}: must be between 1 and {REMEHA_MAX_SPAN}.")

        registers = await self._unit.read_holding_registers(address, count=count)
        return struct.unpack(struct_format, decode_bytes(registers))

    async def async_update(self):
        """Refresh all components."""

        if not self.zones:
            await self._async_setup()
        else:
            await self._async_update()
