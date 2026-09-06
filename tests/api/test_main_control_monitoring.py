"""Tests for the ApplianceDemandStatus."""

from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.api.main_control_monitoring import ApplianceDemandStatus


def test_read_appliance_demand_status(remeha_modbus_unit: MockModbusUnit):
    """Test that an ApplianceDemandStatus can be read using a modbus unit."""

    status = ApplianceDemandStatus(remeha_modbus_unit)
    assert status is not None
