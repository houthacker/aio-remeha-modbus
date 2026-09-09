"""Tests for the ApplianceDemandStatus."""

import pytest
from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.api.main_control_monitoring import (
    ApplianceErrorPriority,
    MainControlMonitoring,
)


@pytest.mark.asyncio
async def test_read_main_control_monitorinbg(remeha_modbus_unit: MockModbusUnit):
    """Test that an ApplianceDemandStatus can be read using a modbus unit."""

    status = MainControlMonitoring(remeha_modbus_unit)
    await status.async_update()

    assert status.current_error == 0x0223
    assert status.error_priority == ApplianceErrorPriority.BLOCKING
    assert status.error_as_str() == "H02.35"
