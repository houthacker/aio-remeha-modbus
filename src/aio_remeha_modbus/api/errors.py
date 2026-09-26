"""Remeha Modbus API exceptions."""

from enum import Enum

from modbus_connection.exceptions import (
    GatewayPathUnavailableError,
    GatewayTargetError,
    IllegalDataAddressError,
    IllegalDataValueError,
    MemoryParityError,
    ModbusConnectionError,
    ModbusDesyncError,
    ModbusTimeoutError,
    ServerDeviceBusyError,
    ServerDeviceFailureError,
)

type Placeholders = dict[str, str | int | bool | Enum | Placeholders]
"""Type declaration for placeholders in a translateable error."""

type TransientModbusError = (
    GatewayPathUnavailableError
    | GatewayTargetError
    | IllegalDataAddressError
    | IllegalDataValueError
    | MemoryParityError
    | ModbusConnectionError
    | ModbusDesyncError
    | ModbusTimeoutError
    | ServerDeviceBusyError
    | ServerDeviceFailureError
)
"""Transient `ModbusError` subclasses.

These exceptions are candidates for the `async_retry` decorator.
Not all of them seem obvious, but especially `GatewayPathUnavailableError`,
`IllegalDataAddressError` and `IllegalDataValueError` have been observed
in the wild whenever either the GTW-08 itself or the backing L-bus are
overloaded or busy.
"""


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
        """Create a new RemehaApiError."""
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
    read from modbus successfully, but parsing them into a `TimeProgram` failed.
    """
