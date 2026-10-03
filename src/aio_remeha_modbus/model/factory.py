"""Factories for Gateway protocol implementations."""

import logging
from datetime import tzinfo
from typing import overload

from modbus_connection import ModbusUnit

from aio_remeha_modbus.gtw08 import GTW08
from aio_remeha_modbus.gtw08.gtw08 import DetectionFailureReason as Gtw08DetectionFailureReason
from aio_remeha_modbus.gtw26 import GTW26
from aio_remeha_modbus.gtw26.const import MESSAGE_SPACING as GTW26_MESSAGE_SPACING
from aio_remeha_modbus.gtw26.system_discovery_table import (
    DetectionFailureReason as Gtw26DetectionFailureReason,
)
from aio_remeha_modbus.helpers.modbus import retry_on_transient
from aio_remeha_modbus.model.errors import GatewayDetectionFailure
from aio_remeha_modbus.model.gateway import Gateway, GatewayType

_LOGGER = logging.getLogger(__name__)


@retry_on_transient()
async def _async_detect_gtw08(unit: ModbusUnit) -> bool:
    detection = await GTW08.async_detect(unit)
    if detection.success:
        return True

    match detection.failure_reason:
        case Gtw08DetectionFailureReason.NO_GATEWAY:
            _LOGGER.debug(
                "Detection of GTW-08 failed: it's probably a GTW-08 but its discovery table doesn't list it."
            )
            raise GatewayDetectionFailure(translation_key="gateway_detection_no_gateway_detected")
        case Gtw08DetectionFailureReason.NO_MAINBOARD:
            _LOGGER.debug(
                "Detection of GTW-08 failed: it's probably a GTW-08 but its discovery table doesn't list any main boards."
            )
            raise GatewayDetectionFailure(translation_key="gateway_detection_no_gateway_detected")
        case Gtw08DetectionFailureReason.NOT_A_GTW08:
            _LOGGER.debug("Detection of GTW-08 failed: device is not a GTW-08.")
            return False


@retry_on_transient()
async def _async_detect_gtw26(
    unit: ModbusUnit, message_spacing_seconds: float = GTW26_MESSAGE_SPACING
) -> bool:
    detection = await GTW26.async_detect(unit, message_spacing_seconds=message_spacing_seconds)

    if detection.success:
        return True

    match detection.failure_reason:
        case Gtw26DetectionFailureReason.UNKNOWN_MODEL:
            _LOGGER.debug("Detection of GTW-26 failed: device is an unknown gateway model.")
            raise GatewayDetectionFailure("gateway_detection_no_gateway_detected")
        case Gtw26DetectionFailureReason.NOT_A_GTW26:
            _LOGGER.debug("Detection of GTW-26 failed: device is not a GTW-26.")
            return False


async def async_detect_gateway(
    unit: ModbusUnit,
    message_spacing_seconds: float = GTW26_MESSAGE_SPACING,
) -> GatewayType:
    """Detect the type of gateway the appliance provides.

    Args:
        unit (ModbusUnit): The unit to use to connect to the gateway.
        message_spacing_seconds (float): The messaging space as enforced on ``unit``.

    Returns:
        ``GatewayType`` the detected type of gateway.

    Raises:
        ``GatewayDetectionFailure(gateway_detection_no_gateway_detected)`` if neither a GTW-08 nor a
            GTW-26 could successfully be detected.

    """

    if await _async_detect_gtw08(unit):
        return GatewayType.GTW08

    if await _async_detect_gtw26(unit, message_spacing_seconds=message_spacing_seconds):
        return GatewayType.GTW26

    raise GatewayDetectionFailure(translation_key="gateway_detection_no_gateway_detected")


@overload
def create_gateway(
    unit: ModbusUnit,
    gateway_type: GatewayType.GTW08,
    time_zone: tzinfo | None = None,
    message_spacing_seconds: float = 0.00175,
    request_timeout: float = 10,
) -> Gateway: ...


@overload
def create_gateway(
    unit: ModbusUnit,
    gateway_type: GatewayType.GTW26,
    message_spacing_seconds: float = GTW26_MESSAGE_SPACING,
    request_timeout: float | None = None,
) -> Gateway: ...


def create_gateway(
    unit: ModbusUnit,
    gateway_type: GatewayType,
    message_spacing_seconds: float = 0.00175,
    request_timeout: float | None = None,
    time_zone: tzinfo | None = None,
) -> Gateway:
    """Create a ``Gateway`` instance of the requested type.

    Args:
        unit (ModbusUnit): The modbus unit to use for the connection to the gateway.
        gateway_type (GatewayType): The requested gateway type.
        message_spacing_seconds (float): The message spacing in seconds, enforced on ``unit``.
        request_timeout (float|None): The request timeout. For GTW-08, this value is mandatory.
        time_zone (tzinfo|None): The time zone of the appliance used for calculating
            current scheduling time slots. GTW-08 only.

    """

    match gateway_type:
        case GatewayType.GTW08:
            return GTW08(
                "GTW-08",
                unit,
                time_zone=time_zone,
                message_spacing_seconds=message_spacing_seconds,
                request_timeout=request_timeout or 10,
            )
        case GatewayType.GTW26:
            return GTW26(
                "GTW-26",
                unit,
                message_spacing_seconds=message_spacing_seconds,
                request_timeout=request_timeout,
            )
