"""Modbus helper functions."""

from typing import TYPE_CHECKING

from aio_remeha_modbus.api.const import (
    REMEHA_DEVICE_INSTANCE_RESERVED_REGISTERS,
    REMEHA_TIME_PROGRAM_RESERVED_REGISTERS,
    REMEHA_ZONE_RESERVED_REGISTERS,
)

if TYPE_CHECKING:
    from aio_remeha_modbus.api.climate_zone import ClimateZone
    from aio_remeha_modbus.api.const import ClimateZoneScheduleId
    from aio_remeha_modbus.api.system_discovery_table import DeviceBoard


def get_zone_register_offset(zone: ClimateZone | int) -> int:
    """Get the offset in registers for the given `ClimateZone | int`."""
    zone_id: int = zone if isinstance(zone, int) else zone.id
    return (zone_id - 1) * REMEHA_ZONE_RESERVED_REGISTERS


def get_device_register_offset(device: DeviceBoard | int) -> int:
    """Get the offset in registers for the given `DeviceInfo | int`."""

    device_id: int = device if isinstance(device, int) else device.id
    return device_id * REMEHA_DEVICE_INSTANCE_RESERVED_REGISTERS


def get_schedule_register_offset(self, schedule: ClimateZoneScheduleId | int) -> int:
    """Get the offset in registers for the given `ClimateZoneScheduleId | int."""
    return schedule * REMEHA_TIME_PROGRAM_RESERVED_REGISTERS
