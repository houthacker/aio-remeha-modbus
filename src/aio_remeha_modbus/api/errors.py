"""Remeha Modbus API exceptions."""

from enum import Enum

from aio_remeha_modbus.api.const import ClimateZoneScheduleId

type Placeholders = dict[str, str | int | bool | Enum | Placeholders]
"""Type declaration for placeholders in a translateable error."""


class RemehaApiError(Exception):
    """Base class for Remeha Modbus API exceptions."""

    translation_key: str
    """The key used to look up translations of this error."""

    translation_placeholders: Placeholders
    """Placeholders for values within the error message."""

    def __init__(
        self,
        translation_key: str,
        translation_placeholders: Placeholders = {},
    ) -> None:
        super().__init__()

        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders


class RemehaModbusError(RemehaApiError):
    """Base class for translateable modbus exceptions."""


class AutoSchedulingError(RemehaApiError):
    """Exception to indicate an error occurred while auto scheduling."""


class DiscoveryTableCorruptedError(RemehaModbusError):
    """Exception to indicate the modbus discovery table seems corrupted.

    This happens for example if the number of devices is 0 or None.
    This can be fixed by calling the `force_system_rediscovery` service.
    """


class InvalidZoneSchedule(RemehaApiError):
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
        super().__init__(
            translation_key="invalid_zone_schedule",
            translation_placeholders={
                "zone": zone,
                "schedule_id": schedule_id.name,
                "is_dhw": is_dhw,
            },
        )

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
