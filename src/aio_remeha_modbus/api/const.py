"""Constants for the Remeha Modbus API."""

from enum import Enum, StrEnum
from typing import Final, Self

from pydantic import Field, model_validator
from pydantic.dataclasses import dataclass

from aio_remeha_modbus.api.registers import ZoneRegisters

# Base register information for zones, device info, time schedules
REMEHA_ZONE_RESERVED_REGISTERS: Final[int] = 512
REMEHA_DEVICE_INSTANCE_RESERVED_REGISTERS: Final[int] = 6
REMEHA_TIME_PROGRAM_RESERVED_REGISTERS: Final[int] = 70
REMEHA_TIME_PROGRAM_BYTE_SIZE: Final[int] = 20
REMEHA_TIME_PROGRAM_SLOT_SIZE: Final[int] = 3
REMEHA_TIME_STEP_MINUTES: Final[int] = 10


class DataType(StrEnum):
    """Data types for GTW-08 modbus.

    #### Notes
    The HA modbus component also provides a `DataType` enum, but it has a deprecated
    `UINT8` variant, which is used extensively by the GTW-08 parameter list.
    Not providing an `UINT8` variant would require a more generic approach
    while reading/writing registers, that is more complex than adding a new
    variant and handling it specifically.
    """

    UINT8 = "uint8"
    """A single byte, read from a 2-byte register with struct format of `xB`.
    Also used for ENUM8"""

    INT16 = "int16"
    INT32 = "int32"
    INT64 = "int64"
    UINT16 = "uint16"
    UINT32 = "uint32"
    UINT64 = "uint64"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    STRING = "string"
    CIA_301_TIME_OF_DAY = "cia301_time_of_day"
    """A time of day, encoded as defined in the CAN301 par 9.1.6.4, 'Time of Day'."""

    TUPLE16 = "tuple16"
    """A `tuple[int, int]` read from a single register."""

    ZONE_TIME_PROGRAM = "zone_time_program"
    """A zone time program for a single day, encoded in bytes as defined in the GTW-08 parameter list."""


class Weekday(Enum):
    """Enumeration for days of the week."""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class ClimateZoneFunction(Enum):
    """Enumerates the available zone functions."""

    DISABLED = 0
    DIRECT = 1
    MIXING_CIRCUIT = 2
    SWIMMING_POOL = 3
    HIGH_TEMPERATURE = 4
    FAN_CONVECTOR = 5
    DHW_TANK = 6
    ELECTRICAL_DHW_TANK = 7
    TIME_PROGRAM = 8
    PROCESS_HEAT = 9
    DHW_LAYERED = 10
    DHW_BIC = 11
    DHW_COMMERCIAL_TANK = 12
    DHW_PRIMARY = 254

    def is_supported(self) -> bool:
        """Return whether this `ClimateZoneFunction` is currently supported within this integration."""
        return self in [
            ClimateZoneFunction.MIXING_CIRCUIT,
            ClimateZoneFunction.DHW_PRIMARY,
        ]

    def has_cooling_capability(self) -> bool:
        """Return whether this `ClimateZoneFunction` supports cooling."""
        return self in [
            ClimateZoneFunction.MIXING_CIRCUIT,
            ClimateZoneFunction.FAN_CONVECTOR,
        ]


class ClimateZoneHeatingMode(Enum):
    """The mode the zone is currently functioning in."""

    STANDBY = 0
    HEATING = 1
    COOLING = 2


class ClimateZoneMode(Enum):
    """Enumerates the modes a zone can be in."""

    SCHEDULING = 0
    MANUAL = 1
    ANTI_FROST = 2


class ClimateZoneScheduleId(Enum):
    """The climate zone time program selected by the user.

    Note: After updating the enum values, **ALWAYS** update the mapping to _attr_preset_modes of RemehaModbusClimateEntity!
    """

    SCHEDULE_1 = 0
    SCHEDULE_2 = 1
    SCHEDULE_3 = 2
    SCHEDULE_4 = 3


class ClimateZoneType(Enum):
    """Enumerates the available zone types."""

    NOT_PRESENT = 0
    CH_ONLY = 1
    CH_AND_COOLING = 2
    DHW = 3
    PROCESS_HEAT = 4
    SWIMMING_POOL = 5
    OTHER = 254


# Reference to Remeha modbus registers
type ModbusVariableRef = int


@dataclass(unsafe_hash=True)
class ModbusVariableDescription:
    """Modbus register description.

    Attributes:
        start_address (ModbusRegisterRef): The register index as specified in the GTW-08 parameter list.
        name (str): The name as shown in the 'Data' field in the GTW-08 parameter list.
        data_type (DataType): The data type of the variable.
        scale (float): Multiply the 'raw' variable value by this.
        count (int): The amount of registers to read/write. Required, and calculated for all types except `DataType.STRING`.
        friendly_name (str | None): The optional parameter name as shown in the Remeha installation manual of the appliance.

    """

    start_address: ModbusVariableRef
    name: str
    data_type: DataType
    scale: float | None = Field(default=None)
    count: int | None = Field(default=None)
    friendly_name: str | None = Field(default=None)

    @model_validator(mode="after")
    def ensure_mandatory_fields(self) -> Self:
        """Ensure the fields `count` and `struct_format` have a value when they are required.

        Additionally, if `count` has no value, it is calculated for data types other than `DataType.STRING`.

        * `count` is required if `data_type == DataType.STRING`
        * `scale` must be `None` if `data_type == DataType.TUPLE16`

        """

        def ensure_register_count() -> int:
            match self.data_type:
                case (
                    DataType.UINT8 | DataType.UINT16 | DataType.INT16 | DataType.TUPLE16
                ):
                    return 1
                case DataType.UINT32 | DataType.INT32 | DataType.FLOAT32:
                    return 2
                case DataType.CIA_301_TIME_OF_DAY:
                    return 3
                case DataType.UINT64 | DataType.INT64 | DataType.FLOAT64:
                    return 4
                case DataType.ZONE_TIME_PROGRAM:
                    return 10
                case _:
                    # Raise an error if self.count cannot be calculated.
                    raise ValueError(
                        f"Cannot calculate amount of registers required for {self.data_type}"
                    )

        if self.data_type == DataType.STRING and self.count is None:
            raise ValueError(
                "Attribute self.count has no value, but it is required because data_type is DataType.STRING"
            )

        if self.data_type == DataType.TUPLE16 and self.scale is not None:
            raise ValueError(
                "self.scale has a value, but self.data_type is DataType.TUPLE16, which cannot be scaled."
            )

        self.count = ensure_register_count() if self.count is None else self.count

        return self


WEEKDAY_TO_MODBUS_VARIABLE: Final[dict[Weekday, ModbusVariableDescription]] = {
    Weekday.MONDAY: ZoneRegisters.TIME_PROGRAM_MONDAY,
    Weekday.TUESDAY: ZoneRegisters.TIME_PROGRAM_TUESDAY,
    Weekday.WEDNESDAY: ZoneRegisters.TIME_PROGRAM_WEDNESDAY,
    Weekday.THURSDAY: ZoneRegisters.TIME_PROGRAM_THURSDAY,
    Weekday.FRIDAY: ZoneRegisters.TIME_PROGRAM_FRIDAY,
    Weekday.SATURDAY: ZoneRegisters.TIME_PROGRAM_SATURDAY,
    Weekday.SUNDAY: ZoneRegisters.TIME_PROGRAM_SUNDAY,
}
