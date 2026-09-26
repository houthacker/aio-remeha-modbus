"""Tests for the ApplianceDemandStatus."""

import pytest
from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.gtw08.main_control_monitoring import (
    ApplianceDemandStatus,
    ApplianceErrorPriority,
    MainControlMonitoring,
    MonitoringStatus,
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


@pytest.mark.asyncio
async def test_error_as_str_unknown_priority(remeha_modbus_unit: MockModbusUnit):
    """Test the prefix for an error priority that is not known."""

    monitoring = MainControlMonitoring(remeha_modbus_unit)
    await monitoring.async_update()

    # Skip field decoding, since an unknown priority is refused by the field.
    monitoring._values["error_priority"] = 42  # noqa: SLF001

    assert monitoring.error_as_str() == "?02.35"


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["main_control_monitoring_ok.json"], indirect=True)
async def test_error_as_str_ignores_error_when_priority_is_ok(
    remeha_modbus_unit: MockModbusUnit,
):
    """Test that the current error is irrelevant if the priority reports no error."""

    remeha_modbus_unit.holding[277] = 0x0207

    monitoring = MainControlMonitoring(remeha_modbus_unit)
    await monitoring.async_update()

    assert monitoring.error_priority == ApplianceErrorPriority.NO_ERROR
    assert monitoring.error_as_str() == "OK"


@pytest.mark.asyncio
async def test_error_as_str_formatting(remeha_modbus_unit: MockModbusUnit):
    """Test that both parts of the error code are zero-padded."""

    remeha_modbus_unit.holding[277] = 0x0501
    remeha_modbus_unit.holding[278] = ApplianceErrorPriority.WARNING.value

    monitoring = MainControlMonitoring(remeha_modbus_unit)
    await monitoring.async_update()

    assert monitoring.error_as_str() == "A05.01"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("priority", "prefix"),
    [
        (ApplianceErrorPriority.LOCKING, "E"),
        (ApplianceErrorPriority.BLOCKING, "H"),
        (ApplianceErrorPriority.WARNING, "A"),
    ],
)
async def test_error_as_str_prefix(
    remeha_modbus_unit: MockModbusUnit, priority: ApplianceErrorPriority, prefix: str
):
    """Test the prefix belonging to each error priority."""

    remeha_modbus_unit.holding[277] = 0x0102
    remeha_modbus_unit.holding[278] = priority.value

    monitoring = MainControlMonitoring(remeha_modbus_unit)
    await monitoring.async_update()

    assert monitoring.error_as_str() == f"{prefix}01.02"


@pytest.mark.asyncio
async def test_demand_status(remeha_modbus_unit: MockModbusUnit):
    """Test that the demand status bits are decoded into flags."""

    remeha_modbus_unit.holding[275] = 0b0100011

    monitoring = MainControlMonitoring(remeha_modbus_unit)
    await monitoring.async_update()

    assert monitoring.demand_status == (
        ApplianceDemandStatus.UNMIXED_CIRCUITS_RELEASED
        | ApplianceDemandStatus.MIXED_CIRCUITS_RELEASED
        | ApplianceDemandStatus.DHW_CIRCUITS_RELEASED
    )
    assert monitoring.demand_status is not None
    assert ApplianceDemandStatus.COOLING_ALLOWED not in monitoring.demand_status


@pytest.mark.asyncio
async def test_demand_status_empty(remeha_modbus_unit: MockModbusUnit):
    """Test that no demand bits result in an empty flag."""

    remeha_modbus_unit.holding[275] = 0

    monitoring = MainControlMonitoring(remeha_modbus_unit)
    await monitoring.async_update()

    assert monitoring.demand_status == ApplianceDemandStatus(0)


@pytest.mark.asyncio
async def test_monitoring_status_spans_two_registers(remeha_modbus_unit: MockModbusUnit):
    """Test that the monitoring status combines the low and high register."""

    remeha_modbus_unit.holding[279] = 0x0001  # FLAME_ON (2**16) sits in the first register
    remeha_modbus_unit.holding[280] = 0x0040  # COOLING_ACTIVE (2**6) sits in the second

    monitoring = MainControlMonitoring(remeha_modbus_unit)
    await monitoring.async_update()

    assert monitoring.monitoring_status is not None
    assert MonitoringStatus.FLAME_ON in monitoring.monitoring_status
    assert MonitoringStatus.COOLING_ACTIVE in monitoring.monitoring_status
    assert MonitoringStatus.HEAT_PUMP_ON not in monitoring.monitoring_status
