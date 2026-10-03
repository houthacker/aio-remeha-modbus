"""Error definitions for the unified gateway model."""

from aio_remeha_modbus.gtw08.errors import RemehaModbusError


class GatewayDetectionFailure(RemehaModbusError):
    """Indicate that a gateway could not be detected."""
