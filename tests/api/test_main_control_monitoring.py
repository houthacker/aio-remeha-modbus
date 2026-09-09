"""Tests for the ApplianceDemandStatus."""

import pytest
from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.api.main_control_monitoring import (
    ApplianceErrorPriority,
    MainControlMonitoring,
)


@pytest.mark.asyncio
async def test_read_main_control_monitoring(remeha_modbus_unit: MockModbusUnit):
    """Test that an ApplianceDemandStatus can be read using a modbus unit."""

    status = MainControlMonitoring(remeha_modbus_unit)
    await status.async_update()

    assert status.current_error == 0x0223
    assert status.error_priority == ApplianceErrorPriority.BLOCKING
    assert status.error_as_str() == "H02.35"


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["main_control_monitoring_ok.json"], indirect=True)
async def test_appliance_status_ok(remeha_modbus_unit: MockModbusUnit):
    """Test the monitoring when appliance status is OK."""

    monitoring = MainControlMonitoring(remeha_modbus_unit)
    await monitoring.async_update()

    assert monitoring.error_as_str() == "OK"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "remeha_modbus_unit", ["main_control_monitoring_warning.json"], indirect=True
)
async def test_appliance_status_warning(remeha_modbus_unit: MockModbusUnit):
    """Test the monitoring when appliance status is OK."""

    monitoring = MainControlMonitoring(remeha_modbus_unit)
    await monitoring.async_update()

    assert monitoring.error_as_str() == "A02.07"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "remeha_modbus_unit", ["main_control_monitoring_blocking.json"], indirect=True
)
async def test_appliance_status_blocking(remeha_modbus_unit: MockModbusUnit):
    """Test the monitoring when appliance status is OK."""

    monitoring = MainControlMonitoring(remeha_modbus_unit)
    await monitoring.async_update()

    assert monitoring.error_as_str() == "H02.07"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "remeha_modbus_unit", ["main_control_monitoring_locking.json"], indirect=True
)
async def test_appliance_status_locking(remeha_modbus_unit: MockModbusUnit):
    """Test the monitoring when appliance status is OK."""

    monitoring = MainControlMonitoring(remeha_modbus_unit)
    await monitoring.async_update()

    assert monitoring.error_as_str() == "E02.07"
