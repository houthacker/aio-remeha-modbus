"""Implementation of the Remeha Modbus API."""

import logging
from datetime import tzinfo
from typing import TYPE_CHECKING

from modbus_connection import ModbusUnit
from modbus_connection.model import integer, repeating_group

from aio_remeha_modbus.api.appliance import (
    Appliance,
)
from aio_remeha_modbus.api.climate_zone import (
    ClimateZone,
)
from aio_remeha_modbus.api.const import (
    REMEHA_DEVICE_INSTANCE_RESERVED_REGISTERS,
    REMEHA_TIME_PROGRAM_RESERVED_REGISTERS,
    REMEHA_ZONE_RESERVED_REGISTERS,
)
from aio_remeha_modbus.api.main_control_monitoring import MainControlMonitoring
from aio_remeha_modbus.api.system_discovery_table import DeviceBoard, SystemDiscoveryTable

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aio_remeha_modbus.api.const import ClimateZoneScheduleId


#################################
###     remeha_modbus API     ###
#################################


class RemehaApi:
    """Use instances of this class to interact with the Remeha device through Modbus."""

    zones = repeating_group(
        integer(address=189, signed=False),
        component_class=ClimateZone,
        stride=REMEHA_ZONE_RESERVED_REGISTERS,
    )

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
        # TODO self.sensors = xxx

    @property
    def name(self) -> str:
        """Return the modbus hub name."""
        return self._name

    def get_zone_register_offset(self, zone: ClimateZone | int) -> int:
        """Get the offset in registers for the given `ClimateZone | int`."""
        zone_id: int = zone.id if isinstance(zone, ClimateZone) else zone
        return (zone_id - 1) * REMEHA_ZONE_RESERVED_REGISTERS

    def get_device_register_offset(self, device: DeviceBoard | int) -> int:
        """Get the offset in registers for the given `DeviceInfo | int`."""

        device_id: int = device.id if isinstance(device, DeviceBoard) else device
        return device_id * REMEHA_DEVICE_INSTANCE_RESERVED_REGISTERS

    def get_schedule_register_offset(self, schedule: ClimateZoneScheduleId | int) -> int:
        """Get the offset in registers for the given `ClimateZoneScheduleId | int."""
        schedule_id: int = int(schedule)
        return schedule_id * REMEHA_TIME_PROGRAM_RESERVED_REGISTERS
