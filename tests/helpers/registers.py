"""Helpers for modbus registers."""

from typing import Final

from aio_remeha_modbus.api.const import ModbusVariableDescription
from aio_remeha_modbus.api.registers import HybridRegisters, MetaRegisters

SENSOR_REGISTERS: Final[list[ModbusVariableDescription]] = [
    MetaRegisters.CURRENT_ERROR,
    MetaRegisters.ERROR_PRIORITY,
    MetaRegisters.OUTSIDE_TEMPERATURE,
    MetaRegisters.FLOW_TEMPERATURE,
    MetaRegisters.RETURN_TEMPERATURE,
    MetaRegisters.HEAT_PUMP_FLOW_TEMPERATURE,
    MetaRegisters.HEAT_PUMP_RETURN_TEMPERATURE,
    MetaRegisters.WATER_PRESSURE,
    MetaRegisters.FLOW_METER,
    MetaRegisters.STATUS,
    MetaRegisters.SUBSTATUS,
    MetaRegisters.POWER_ACTUAL,
    MetaRegisters.TOTAL_ENERGY_CONSUMPTION,
    MetaRegisters.TOTAL_ENERGY_DELIVERY,
    MetaRegisters.CH_ENERGY_DELIVERY,
    MetaRegisters.DHW_ENERGY_DELIVERY,
    MetaRegisters.COOLING_ENERGY_DELIVERY,
    MetaRegisters.BACKUP_ENERGY_DELIVERY,
    MetaRegisters.PUMP_SPEED,
    MetaRegisters.ACTUAL_PRODUCED_POWER,
    HybridRegisters.COP_CALCULATED,
]
