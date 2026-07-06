"""Remeha Modbus API exceptions."""

from pymodbus import ModbusException

from aio_remeha_modbus.api.const import ClimateZoneScheduleId


class DiscoveryTableCorruptedError(ModbusException):
    """Exception to indicate the modbus discovery table seems corrupted.

    This happens for example if the number of devices is 0 or None.
    This can be fixed by calling the `force_system_rediscovery` service.
    """


class InvalidZoneSchedule(Exception):
    """API exception to indicate that an invalid zone schedule was read from modbus.

    This exception is raised when the encoded zone schedule bytes are
    read from modbus successfully, but parsing them into a ZoneSchedule failed.
    """

    def __init__(
        self, *args: object, zone: int, schedule_id: ClimateZoneScheduleId, is_dhw: bool
    ) -> None:
        """Create a new InvalidZoneSchedule.

        Args:
            *args (object): A tuple of arguments given to the `Exception` constructor.
            zone (int): The index of the zone that was attempted to read.
            schedule_id (str): The name of the schedule that was attempted to read.
            is_dhw (bool): Whether the related zone is a DHW zone.

        """
        super().__init__(*args)

        self._zone = zone
        self._schedule_id = schedule_id
        self._is_dhw = is_dhw

    @property
    def zone(self) -> int:
        """The index of the zone that was attempted to read."""
        return self._zone

    @property
    def schedule_id(self) -> ClimateZoneScheduleId:
        """The name of the schedule that was attempted to read."""
        return self._schedule_id

    @property
    def is_dhw(self) -> bool:
        """Whether the related climate zone is a DHW zone."""

        return self._is_dhw
