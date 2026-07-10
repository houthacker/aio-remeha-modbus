"""Configuration classes."""

from typing import Literal

from pydantic.dataclasses import dataclass
from pymodbus import FramerType

from aio_remeha_modbus.api.const import ConnectionType


@dataclass
class Configuration:
    """The configuration to use when creating new `RemehaApi` instances."""

    connection_type: ConnectionType
    """The type of connection required to connect to the modbus device."""

    device_address: int
    """The modbus slave id."""

    port: str | int
    """The port to connect to.

    Examples:
    * `/dev/ttyUSB0` for a serial connection
    * `502` for a TCP connection
    """


@dataclass
class SerialConfiguration(Configuration):
    """Configuration for serial connections."""

    connection_type = ConnectionType.SERIAL

    framer: Literal[FramerType.RTU, FramerType.ASCII]
    """The type of framer to use."""

    baudrate: int = 9600
    """The speed of the connection."""

    bytesize: Literal[5, 6, 7, 8] = 8
    """Data size in bits of each byte."""

    parity: Literal["E", "O", "N"] = "N"
    """Parity if the data bytes."""

    stopbits: Literal[1, 2] = 2
    """Stopbits of the data bytes."""


@dataclass
class TcpConfiguration(Configuration):
    """Configuration for TCP connection types."""

    framer: Literal[FramerType.SOCKET, FramerType.RTU]

    host: str
    """The IP-address or hostname of the modbus device."""

    timeout: int = 120
    """Response timeout in seconds."""


@dataclass
class UdpConfiguration(Configuration):
    """Configuration for UDP connection types."""

    framer: Literal[FramerType.SOCKET]

    host: str
    """The IP-address or hostname of the modbus device."""

    timeout: int = 120
    """Response timeout in seconds."""
