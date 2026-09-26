"""Implementation of the Remeha Modbus API."""

import logging
import struct
from datetime import tzinfo
from typing import Any

from modbus_connection import ModbusExceptionError, ModbusUnit
from modbus_connection.model import ComponentGroup, Device, ManualComponent, UpdateReport

from aio_remeha_modbus.gtw08.appliance import (
    Appliance,
)
from aio_remeha_modbus.gtw08.climate_zone import ClimateZone, ClimateZoneFunction
from aio_remeha_modbus.gtw08.const import REMEHA_MAX_SPAN, REMEHA_ZONE_RESERVED_REGISTERS
from aio_remeha_modbus.gtw08.errors import RemehaApiError, RemehaModbusError
from aio_remeha_modbus.gtw08.main_control_monitoring import MainControlMonitoring
from aio_remeha_modbus.gtw08.system_discovery_table import SystemDiscoveryTable
from aio_remeha_modbus.helpers.fields import decode_bytes, uint8

# Attribute names of syb-systems each update method reads.
READINGS = ("main_control_monitoring", "appliance", "_zones")
SETTINGS = ("discovery_table",)
ALL = (*READINGS, *SETTINGS)

_LOGGER = logging.getLogger(__name__)


class GTW08(Device):
    """Represents a GTW-08 modbus gateway."""

    def __init__(
        self,
        name: str,
        unit: ModbusUnit,
        time_zone: tzinfo | None = None,
        message_spacing_seconds: float = 0.00175,
        request_timeout: float = 0.003,
    ):
        """Create a new GTW08 device instance.

        When creating a new `GTW08`, the message spacing and timeout are
        set on `unit`.

        Args:
            name (str): An arbitrary name of this API.
            unit (ModbusUnit): The unit to use to query the remote appliance.
            time_zone (tzinfo|None): The time zone of the Remeha appliance.
            message_spacing_seconds (float): The required message spacing in seconds.
            request_timeout (float): The required request timeout in seconds.

        """

        super().__init__(unit)

        unit.set_message_spacing(message_spacing_seconds)
        unit.require_timeout(request_timeout)

        self._name = name
        self._unit = unit
        self._time_zone = time_zone

        self.discovery_table = SystemDiscoveryTable(unit)
        self.main_control_monitoring = MainControlMonitoring(unit)
        self.appliance = Appliance(unit)

        self.zones: list[ClimateZone] = []
        self._zones: ComponentGroup | None = None

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

        self.zones = []
        for idx in range(self.discovery_table.number_of_zones):
            # Read the zone function first. We don't read disabled zones.
            zone_function_address = 641 + REMEHA_ZONE_RESERVED_REGISTERS * idx
            registers = await self.modbus_unit.read_holding_registers(
                address=zone_function_address, count=1
            )
            zone_function = ClimateZoneFunction(registers[0])

            if zone_function is ClimateZoneFunction.DISABLED:
                _LOGGER.info("Skipping zone %d because it is disabled.", idx + 1)
                continue

            climate_zone = ClimateZone(
                self._unit,
                sequence_id=idx + 1,
                time_zone=self._time_zone,
                appliance_requires_cooling=self.appliance.is_cooling_required,
            )

            await climate_zone.async_update()
            self.zones.append(climate_zone)

        self._zones = ComponentGroup(
            self._unit,
            list(self.zones),
        )

    async def async_update_readings(self) -> UpdateReport:
        """Refresh the GTW08 measurements."""

        return await self.async_poll(READINGS)

    async def async_update_settings(self) -> UpdateReport:
        """Refresh the GTW08 settings."""

        return await self.async_poll(SETTINGS)

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

    async def async_update(self) -> UpdateReport:
        """Refresh all components."""

        report = await self.async_poll(SETTINGS)
        return await self.async_poll(READINGS, report)
