"""Modbus register specifications"""

from typing import Final

from aio_remeha_modbus.api.const import DataType, ModbusVariableDescription


class MetaRegisters:
    """Register mappings for meta data."""

    NUMBER_OF_DEVICES: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=128,
        name="numberOfDevices",
        data_type=DataType.UINT8,
    )
    NUMBER_OF_ZONES: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=189, name="NumberOfZones", data_type=DataType.UINT8
    )
    RESET_DISCOVERY_TABLE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=200, name="Reset discovery table", data_type=DataType.UINT8
    )

    CURRENT_ERROR: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=277, name="applianceCurrentError", data_type=DataType.UINT16
    )

    ERROR_PRIORITY: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=278, name="applianceErrorPriority", data_type=DataType.INT16
    )

    APPLIANCE_STATUS_1: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=279, name="applilanceStatus1", data_type=DataType.UINT8
    )

    APPLIANCE_STATUS_2: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=280, name="applilanceStatus2", data_type=DataType.UINT8
    )

    OUTSIDE_TEMPERATURE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=384, name="varApTOutside", data_type=DataType.INT16, scale=0.01
    )

    SEASON_MODE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=385, name="varApSeasonMode", data_type=DataType.UINT8
    )

    SUMMER_WINTER: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=386,
        name="varApSummerWinter",
        friendly_name="AP073",
        data_type=DataType.UINT16,
        scale=0.01,
    )
    """Upper limit for heating.

    Factory default is 22°C. Above this temperature, the appliance
    won't heat anymore. Setting it to 30.5°C will disable it and
    cause the appliance to stay in winter mode.
    """

    NEUTRAL_BAND_SUMMER_WINTER: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=387,
            name="parApNeutralBandSummerWinter",
            friendly_name="AP075",
            data_type=DataType.UINT16,
            scale=0.01,
        )
    )
    """Temperature band below the summer/winter limit within which the appliance
    neither heats nor cools (transition season)."""

    FORCE_SUMMER: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=389,
        name="parApForceSummer",
        friendly_name="AP074",
        data_type=DataType.UINT8,
    )
    """Whether forced summer mode is active. Heating is switched off, DHW stays active."""

    FLOW_TEMPERATURE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=400, name="varApTFlow", data_type=DataType.INT16, scale=0.01
    )

    RETURN_TEMPERATURE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=401, name="varApTReturn", data_type=DataType.INT16, scale=0.01
    )

    HEAT_PUMP_FLOW_TEMPERATURE: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=403,
            name="varHpHeatPumpTF",
            data_type=DataType.INT16,
            scale=0.01,
        )
    )

    HEAT_PUMP_RETURN_TEMPERATURE: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=404,
            name="varHpHeatPumpTR",
            data_type=DataType.INT16,
            scale=0.01,
        )
    )

    WATER_PRESSURE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=409,
        name="varApWaterPressure",
        data_type=DataType.UINT8,
        scale=0.1,
    )

    FLOW_METER: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=410, name="varApFlowmeter", data_type=DataType.UINT16, scale=0.01
    )

    STATUS: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=411, name="varApStatus", data_type=DataType.UINT8
    )

    SUBSTATUS: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=412, name="varApSubStatus", data_type=DataType.UINT8
    )

    POWER_ACTUAL: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=413,
        name="varApPowerActual",
        data_type=DataType.UINT16,
        scale=0.01,
    )

    TOTAL_ENERGY_CONSUMPTION: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=439,
            name="varApTotalEnergyConsumption",
            data_type=DataType.UINT32,
        )
    )

    TOTAL_ENERGY_DELIVERY: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=443, name="varApTotalEnergyDelivery", data_type=DataType.UINT32
    )

    CH_ENERGY_DELIVERY: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=445, name="varApChEnergyDelivery", data_type=DataType.UINT32
    )

    DHW_ENERGY_DELIVERY: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=447, name="varApDhwEnergyDelivery", data_type=DataType.UINT32
    )

    COOLING_ENERGY_DELIVERY: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=449,
            name="varApCoolingEnergyDelivery",
            data_type=DataType.UINT32,
        )
    )

    BACKUP_ENERGY_DELIVERY: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=451,
            name="varApBackupEnergyDelivery",
            data_type=DataType.UINT32,
        )
    )

    PUMP_SPEED: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=459, name="varApPumpSpeed", data_type=DataType.UINT16, scale=0.01
    )

    ACTUAL_PRODUCED_POWER: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=460,
        name="varApActualProducerPower",
        data_type=DataType.UINT32,
        scale=0.01,
    )

    SILENT_MODE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=490,
        name="enabling_heat_pump_silent_mode",
        friendly_name="HP058",
        data_type=DataType.UINT8,
    )

    SILENT_MODE_START_TIME: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=491,
            name="silent_mode_start_time",
            friendly_name="HP094",
            data_type=DataType.UINT8,
        )
    )

    SILENT_MODE_END_TIME: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=492,
        name="silent_mode_end_time",
        friendly_name="HP095",
        data_type=DataType.UINT8,
    )

    CH_ENABLED: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=500,
        name="parApChEnabled",
        friendly_name="AP016",
        data_type=DataType.UINT8,
    )

    COOLING_ENABLED: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=502,
        name="parApCoolingEnabled",
        friendly_name="AP028",
        data_type=DataType.UINT8,
    )

    # This variable exists on the appliance level. In the Remeha Home app however, this variable
    # is configurable in two places: in the CH zone and at the system level. Change one, change
    # the other too.
    # In this integration, this value is shown in all CH climates and can be set as follows:
    # * To force cooling, set HVACMode to COOL
    # * To let the system decide to cool or heat, set HVACMode to HEAT_COOL
    COOLING_FORCED: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=503,
        name="parApCoolingForced",
        friendly_name="AP015",
        data_type=DataType.UINT8,
    )


class DeviceInstanceRegisters:
    """The register mappings for device instances."""

    TYPE_BOARD: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=129,
        name="DeviceTypeBoard",
        data_type=DataType.TUPLE16,
    )
    SW_VERSION: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=130,
        name="sw_version",
        data_type=DataType.TUPLE16,
    )
    HW_VERSION: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=132,
        name="hw_version",
        data_type=DataType.TUPLE16,
    )
    ARTICLE_NUMBER: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=133, name="ArticleNumber", data_type=DataType.UINT32
    )


class ZoneRegisters:
    """The register mappings for a climate zone."""

    TYPE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=640,
        name="varZoneType",
        data_type=DataType.UINT8,
    )
    FUNCTION: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=641,
        name="parZoneFunction",
        data_type=DataType.UINT8,
        friendly_name="CP020",
    )
    SHORT_NAME: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=642,
        name="parZoneFriendlyNameShort",
        data_type=DataType.STRING,
        count=3,
    )
    OWNING_DEVICE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=646,
        name="instance",
        data_type=DataType.UINT8,
    )
    MODE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=649,
        name="parZoneMode",
        data_type=DataType.UINT8,
        friendly_name="CP320",
    )
    ROOM_COOLING_SETPOINT_1: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=656,
            name="parZoneRoomCoolingSetpoint1",
            friendly_name="CP140",
            data_type=DataType.UINT16,
            scale=0.1,
        )
    )
    ROOM_COOLING_SETPOINT_2: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=657,
            name="parZoneRoomCoolingSetpoint2",
            friendly_name="CP141",
            data_type=DataType.UINT16,
            scale=0.1,
        )
    )
    ROOM_COOLING_SETPOINT_3: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=658,
            name="parZoneRoomCoolingSetpoint3",
            friendly_name="CP142",
            data_type=DataType.UINT16,
            scale=0.1,
        )
    )
    ROOM_COOLING_SETPOINT_4: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=659,
            name="parZoneRoomCoolingSetpoint4",
            friendly_name="CP143",
            data_type=DataType.UINT16,
            scale=0.1,
        )
    )
    ROOM_COOLING_SETPOINT_5: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=660,
            name="parZoneRoomCoolingSetpoint5",
            friendly_name="CP144",
            data_type=DataType.UINT16,
            scale=0.1,
        )
    )
    TEMPORARY_SETPOINT: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=663,
        name="parZoneTemporaryRoomSetpoint",
        data_type=DataType.UINT16,
        scale=0.1,
        friendly_name="CP510",
    )
    ROOM_MANUAL_SETPOINT: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=664,
        name="parZoneRoomManualSetpoint",
        data_type=DataType.UINT16,
        scale=0.1,
        friendly_name="CP200",
    )
    DHW_COMFORT_SETPOINT: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=665,
        name="parZoneDhwComfortSetpoint",
        data_type=DataType.UINT16,
        scale=0.01,
        friendly_name="CP350",
    )
    DHW_REDUCED_SETPOINT: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=666,
        name="parZoneDhwReducedSetpoint",
        data_type=DataType.UINT16,
        scale=0.01,
        friendly_name="CP360",
    )
    DHW_CALORIFIER_HYSTERESIS: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=686,
            # It's actually Hysteresis (with an e), but since the parameter list defines it
            # as Hysterisis, we'll conform to their naming.
            name="parZoneDhwCalorifierHysterisis",
            data_type=DataType.UINT16,
            scale=0.01,
            friendly_name="CP420",
        )
    )
    SELECTED_TIME_PROGRAM: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=688,
        name="parZoneTimeProgramSelected",
        data_type=DataType.UINT8,
        friendly_name="CP570",
    )
    TIME_PROGRAM_MONDAY: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=689,
        name="parZoneTimeProgramMonday",
        data_type=DataType.ZONE_TIME_PROGRAM,
    )
    TIME_PROGRAM_TUESDAY: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=699,
        name="parZoneTimeProgramTuesday",
        data_type=DataType.ZONE_TIME_PROGRAM,
    )
    TIME_PROGRAM_WEDNESDAY: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=709,
            name="parZoneTimeProgramWednesday",
            data_type=DataType.ZONE_TIME_PROGRAM,
        )
    )
    TIME_PROGRAM_THURSDAY: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=719,
        name="parZoneTimeProgramThursday",
        data_type=DataType.ZONE_TIME_PROGRAM,
    )
    TIME_PROGRAM_FRIDAY: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=729,
        name="parZoneTimeProgramFriday",
        data_type=DataType.ZONE_TIME_PROGRAM,
    )
    TIME_PROGRAM_SATURDAY: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=739,
        name="parZoneTimeProgramSaturday",
        data_type=DataType.ZONE_TIME_PROGRAM,
    )
    TIME_PROGRAM_SUNDAY: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=749,
        name="parZoneTimeProgramSunday",
        data_type=DataType.ZONE_TIME_PROGRAM,
    )
    END_TIME_MODE_CHANGE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=978,
        name="parZoneEndTimeModeChange",
        data_type=DataType.CIA_301_TIME_OF_DAY,
    )
    CURRENT_ROOM_TEMPERATURE: Final[ModbusVariableDescription] = (
        ModbusVariableDescription(
            start_address=1104,
            name="varZoneTRoom",
            data_type=DataType.INT16,
            scale=0.1,
            friendly_name="CM030",
        )
    )
    CURRENT_HEATING_MODE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=1109,
        name="varZoneCurrentHeatingMode",
        data_type=DataType.UINT8,
        friendly_name="CM200",
    )
    PUMP_RUNNING: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=1110,
        name="varZonePumpRunning",
        data_type=DataType.UINT8,
        friendly_name="CM050",
    )
    DHW_TANK_TEMPERATURE: Final[ModbusVariableDescription] = ModbusVariableDescription(
        start_address=1119,
        name="varDhwTankTemperature",
        data_type=DataType.INT16,
        scale=0.01,
        friendly_name="CM040",
    )
