"""Implementation of the main control monitoring sub-unit."""

from enum import IntEnum, IntFlag, auto

from modbus_connection.model import Component, enum, flags

from aio_remeha_modbus.helpers.fields import uint16


class ApplianceDemandStatus(IntFlag):
    """The appliance demand status shows bit fields from register 275."""

    UNMIXED_CIRCUITS_RELEASED = auto()
    """Whether unmixed circuits are released."""

    MIXED_CIRCUITS_RELEASED = auto()
    """Whether mixed circuits are released."""

    VALVES_OPEN_OR_PUMP_RUNNING_SAFETY = auto()
    """Whether all valves are open / pump is running within safety."""

    MANUAL_HEAT_DEMAND_ACTIVE = auto()
    """Whether manual heat demand is active."""

    COOLING_ALLOWED = auto()
    """Whether cooling is allowed at the appliance level.

    This refers to the appliance as a whole, not to an individual zone, so it may be
    `True` while no zone that is able to cool exists.
    """

    DHW_CIRCUITS_RELEASED = auto()
    """Whether DHW circuits are released."""

    BURNER_UNIT_ACTIVE = auto()
    """Whether the burner/generator unit is active."""


class ApplianceErrorPriority(IntEnum):
    """The available error priority types."""

    LOCKING = 0
    """For safety reasons, the appliance has stopped working and requires a manual reset."""

    BLOCKING = 3
    """To prevent future damage, the appliance has stopped temporarily.
    If the problem has been solved, the appliance will recover automatically.
    """

    WARNING = 6
    """The appliance has encountered and error. Refer to the manual to fix the issue."""

    NO_ERROR = 255
    """Normal state, no current error."""


class ApplianceStatus(IntFlag):
    """The appliance status shows various boolean status fields about the appliance."""

    FLAME_ON = 2**16
    """Whether the appliance flame is on."""

    HEAT_PUMP_ON = 2**17
    """Whether the appliance heat pump is on."""

    ELECTRICAL_BACKUP_ON = 2**18
    """Whether the central heating electrical backup is on."""

    ELECTRICAL_BACKUP2_ON = 2**19
    """Whether the 2nd central heating electrical backup is on."""

    DHW_ELECTRICAL_BACKUP_ON = 2**20
    """Whether the DHW electrical backup is on."""

    SERVICE_REQUIRED = 2**21
    """Whether the appliance requires service."""

    POWER_DOWN_RESET_NEEDED = 2**22
    """Whether the appliance must be powered down and reset. Leave it powered off at least 20 seconds."""

    WATER_PRESSURE_LOW = 2**23
    """Whether the water pressure is low."""

    APPLIANCE_PUMP_ON = 2**0
    """Whether the main pump is on."""

    THREE_WAY_VALVE_OPEN = 2**1
    """Whether the 3-way valve is open."""

    THREE_WAY_VALVE = 2**2
    """Unknown, but relate to 3-way valve obviously."""

    THREE_WAY_VALVE_CLOSED = 2**3
    """Whether the 3-way valve is closed."""

    DHW_ACTIVE = 2**4
    """Whether the DHW system is active."""

    CH_ACTIVE = 2**5
    """Whether the CH system is active."""

    COOLING_ACTIVE = 2**6
    """Whether the cooling system is active."""


class MainControlMonitoring(Component):
    """A component that contains status- and control fields at appliance level."""

    demand_status = flags(address=275, flag_type=ApplianceDemandStatus)
    """Status bitfield of the appliance."""

    current_error = uint16(address=277)
    """The current error, encoded in two unsigned bytes. `None` means no error.

    The joined bytes show the error that can be looked up in the manual
    , e.g. `0x0207` is error `02.07`.
    """

    error_priority = enum(address=278, enum_type=ApplianceErrorPriority)
    """The current appliance error priority."""

    status = flags(address=279, flag_type=ApplianceStatus, count=2)
    """Various appliance-level status fields."""

    def error_as_str(self) -> str:
        """Return a user-friendly string representing the current error."""

        prefix: str
        match self.error_priority:
            case ApplianceErrorPriority.NO_ERROR:
                return "OK"
            case ApplianceErrorPriority.WARNING:
                prefix = "A"
            case ApplianceErrorPriority.BLOCKING:
                prefix = "H"
            case ApplianceErrorPriority.LOCKING:
                prefix = "E"
            case _:
                prefix = "?"

        assert self.current_error is not None
        return (
            f"{prefix}{(self.current_error >> 8):02d}.{(self.current_error & int('00ff', 16)):02d}"
        )
