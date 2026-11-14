"""Implementation of appliance-scoped functionality."""

import inspect
import logging
from datetime import time
from enum import IntEnum

from modbus_connection import ModbusUnit
from modbus_connection.model import (
    CoilField,
    DiscreteInputField,
    RegisterField,
    boolean,
    enum,
    uint32,
)

from aio_remeha_modbus.gtw08.const import REMEHA_MAX_SPAN, SeasonalMode
from aio_remeha_modbus.gtw08.model import RemehaComponent
from aio_remeha_modbus.gtw08.system_discovery_table import DeviceBoard, DeviceBoardType
from aio_remeha_modbus.helpers.fields import int16, time_steps, uint8, uint16
from aio_remeha_modbus.helpers.validation import in_range

_LOGGER = logging.getLogger(__name__)


class SilentMode(IntEnum):
    """Defines the silent mode of the appliance."""

    OFF = 0
    """Normal operation."""

    LEVEL_1 = 1
    """Silent mode."""

    LEVEL_2 = 2
    """Extra silent mode."""


class BackupType(IntEnum):
    """Defines the type of heat generation backup used in the heat pump."""

    NO_BACKUP = 0
    """The heat pump has no backup heat source."""

    SINGLE_STAGE_ELECTRICAL = 1
    """The heat pump has a single-phase electrical backup."""

    DOUBLE_STAGE_ELECTRICAL = 2
    """The heat pump has a two-phase electrical backup."""

    BOILER = 3
    """The boiler is the backup heat source."""


class CoolingType(IntEnum):
    """Defines the type of cooling used by the appliance (if any)."""

    OFF = 0
    """Cooling is off."""

    ACTIVE_COOLING = 1
    """The appliance uses active cooling.

    This type of cooling is used by all air-sourced heat pumps.
    """

    FREE_COOLING = 2
    """The appliance uses free cooling.

    This type of cooling is used by geothermal and water-source
    heat pumps.
    """


class DigitalInputConfiguration(IntEnum):
    """Configures the purpose of a digital input."""

    OFF = 0
    """The digital input is turned off."""

    SMART_GRID = 1
    """The digital input is used for Smart Grid connectivity."""

    RELEASE_COMPRESSOR = 2
    """Ignores any (failing) preconditions and allows the heat pump
    compressor to be started.

    In what physical state the contact is released depends on
    the value of parameter `HP077`.
    """

    RELEASE_BACKUP = 3
    """Ignores any (failing) preconditions and allows heat delivery
    from backup sources.

    In what physical state the contact is released depends on
    the value of parameter `HP078`.
    """


class DIContactLogicConfiguration(IntEnum):
    """Configuration of digital input logic (NO/NC)."""

    NORMALLY_OPEN = 0
    """The default state of the related digital input is open (i.e. non-conductive)."""

    NORMALLY_CLOSED = 1
    """The default state of the related digital input is closed (i.e. conductive)."""


class ApplianceStatus(IntEnum):
    """The current status of the appliance."""

    standby = 0
    """The appliance is in standby mode."""

    heat_demand = 1
    """A heat demand is active."""

    generator_start = 2
    """The appliance is starting up."""

    generator_heating = 3
    """The appliance is heating the CH system."""

    generator_dhw = 4
    """The appliance is heating the DHW system."""

    generator_stop = 5
    """The appliance has stopped."""

    pump_post_run = 6
    """The pump is active after the appliance has stopped."""

    cooling = 7
    """The appliance is cooling the CH system."""

    controlled_shutdown = 8
    """The appliance is not starting because a precondition has not been met."""

    start_prevention = 9
    """The appliance is blocked."""

    locking_mode = 10
    """The appliance is locked."""

    load_test_min = 11
    """The appliance is running a load test (min) on the CH system."""

    load_test_heating_max = 12
    """The appliance is running a load test (max) on the CH system."""

    load_test_dhw_max = 13
    """The appliance is running a load test (max) on the DHW system."""

    manual_heat_demand = 15
    """A manual heat demand is active."""

    frost_protection = 16
    """The appliance is running in frost-protection mode."""

    venting = 17
    """The appliance is venting."""

    control_unit_cooling = 18
    """The appliance is cooling the control unit."""

    resetting = 19
    """The appliance is being reset."""

    automatic_filling = 20
    """The appliance is filling the circuit(s)."""

    stopped = 21
    """The appliance is paused and must be stopped manually."""

    calibration = 22
    """The appliance is being calibrated."""

    factory_test = 23
    """The appliance is in factory testing mode."""

    hydraulic_balancing = 24
    """The appliance is balancing the circuits."""

    device_mode = 200
    """The service tool interface manages the appliance modes."""

    unknown = 254
    """The appliance is in an unknown state."""


class ApplianceSubStatus(IntEnum):
    """The appliance sub status provides more details about the status."""

    standby = 0
    """Appliance is waiting on a process or action."""

    anti_cyclus = 1
    """Appliance is waiting to restart because of short cycle protection."""

    close_hydraulic_valve = 2
    """Closing hydraulic valve."""

    stop_pump = 3
    """Stopping pump."""

    wait_start_release = 4
    """The appliance is waiting for temperature to meet the start up-conditions."""

    generator_starting = 21
    """The generator is starting."""

    internal_setpoint = 30
    """The appliance is working to reach the requested setpoint."""

    limited_internal_setpoint = 31
    """The appliance is working to reach the requested reduced setpoint."""

    power_controlled = 32
    """The appliance is working on the desired power level."""

    pump_post_run = 60
    """The pump is running after the appliance has stopped to release the leftover heat."""

    start_pump = 61
    """The pump has stopped."""

    start_pause_time = 63
    """Starting short cycle protection."""

    compressor_unloaded = 65
    """The compressor is running at minimum capacity."""

    hp_tmax_backup_on = 66
    """The heat pump flow temperature has exceeded its maximum limit."""

    outside_temp_limit_hp_off = 67
    """The heat pump has shut off because of an external condition; backup power is used."""

    hp_stop_by_hybrid = 68
    """The hybrid heat pump has shut off because of an external condition; backup power is used."""

    defrost_with_heat_pump = 69
    """Defrost running using only the heat pump."""

    defrost_with_backup = 70
    """Defrost running using only backup power."""

    defrost_hp_and_backup = 71
    """Defrost running using both heat pump- and backup power."""

    hp_flow_above_tmax = 73
    """The heat pump flow temperature exceeds its maximum limit."""

    hp_off_high_humidity = 75
    """The heat pump has shut off because the humidity is too high."""

    hp_off_flow = 76
    """The heat pump has shut off because the flow rate is too low."""

    generator_unloaded = 79
    """Heat pump and backup not allowed for CH and DHW."""

    hp_unloaded_cooling = 80
    """Heat pump cooling not allowed."""

    hp_stop_outside_temp = 81
    """Heat pump shut off because outside temperature is outside its limits."""

    hp_off_flow_tmax = 82
    """Heat pump shut off because it has too little operating time."""

    bl_backup_off = 88
    """Blocking input: backup power off."""

    bl_heat_pump_off = 89
    """Blocking input: heat pump power off."""

    bl_hp_and_backup_off = 90
    """Blocking input: heat pump and backup power off."""

    low_tariff = 91
    """Blocking input: low tariff."""

    pv_with_heat_pump = 92
    """Blocking input: heat pump off because of excess PV power."""

    pv_hp_and_backup = 93
    """Blocking input: heat pump and backup power off because of excess PV power."""

    smart_grid = 94
    """Blocking input: heat pump off because of smart grid settings."""

    wait_water_pressure = 95
    """Waiting for water pressure to become acceptable."""

    no_generator_available = 96
    """No generator available."""

    free_cooling_pump_off = 102
    """Heat pump free cooling mode: CH pump off"""

    free_cooling_pump_on = 103
    """Heat pump free cooling mode: CH pump on"""

    blocking_active = 106
    """The appliance has paused operation due to an unusual external and/or temporary condition."""

    warming_up = 107
    """The appliance is warming up."""

    curative_defrost = 108
    """The appliance is actively performing a corrective defrost to
    clear ice accumulation from the outdoor unit."""

    preventive_defrost = 109
    """The appliance is performing a defrost to prevent ice accumulation on the outdoor unit."""

    init_completed = 200
    """Initialization complete."""

    init_csu = 201
    """Configuration Storage Unit is being initialized.

    The CSU is a memory module that stores settings and software parameters of the appliance.
    """

    init_identification = 202
    """Initializing identifiers.

    The appliance is discovering installed devices and sensors.
    """

    init_blocking_parameters = 203
    """Blocking parameters are being initialized."""

    init_safety_unit = 204
    """Safety group is being initialized.

    A safety group is a mandatory safety element in your heat pump.
    It combines overpressure protection, a non-return valve and a shut-off valve.
    """

    init_blocking = 205
    """BLocking is being initialized."""

    unknown = 254
    """The substatus is not defined."""

    safety_shutdown = 255
    """The safety group is shut down due to too many resets.

    Wait for 60 minutes and power cycle your appliance.
    """


class Appliance(RemehaComponent):  # ruff: ignore[too-many-public-methods]
    """Represents a Remeha appliance.

    An `Appliance` stores information about the appliance that cannot be linked to any of
    the other available api types, like appliance error status or burning hours counters.
    """

    _cu_hw_board_unsupported_fields: set[str] = {
        "outside_temperature",
        "flow_temperature",
        "return_temperature",
        "heat_pump_flow_temperature",
        "heat_pump_return_temperature",
    }

    _other_board_unsupported_fields: set[str] = {
        "digital_input_1_configuration",
        "digital_input_2_configuration",
        "digital_input_1_contact_logic",
        "digital_input_2_contact_logic",
    }

    restrictions_by_gtw_version: dict[int, set[str]] = {
        0x0100: {
            "outside_temperature",
            "season_mode",
            "summer_winter",
            "neutral_band_summer_winter",
            "flow_temperature",
            "return_temperature",
            "heat_pump_flow_temperature",
            "heat_pump_return_temperature",
            "actual_water_pressure",
            "flow_rate",
            "appliance_status",
            "appliance_substatus",
            "actual_relative_power",
            "generator_starts_total",
            "generator_hours_total",
            "backup1_starts",
            "backup1_hours",
            "backup2_starts",
            "backup2_hours",
            "power_on_hours",
            "ch_energy_consumption",
            "dhw_energy_consumption",
            "cooling_energy_consumption",
        },
        0x0101: {
            "forced_summer_mode",
            "ch_enabled",
            "dhw_enabled",
            "cooling_type",
            "forced_cooling_mode",
        },
        0x0102: {
            "total_energy_consumption",
            "backup_energy_consumption",
            "total_energy_delivery",
            "ch_energy_delivery",
            "dhw_energy_delivery",
            "cooling_energy_delivery",
            "backup_energy_delivery",
            "pump_speed",
            "actual_produced_power",
            "hybrid_internal_dhw_setpoint",
            "min_time_between_dhw_productions",
            "max_dhw_production_time",
            "heat_pump_defrost_active",
        },
        0x0103: {
            "cop_calculated",
            "backup_type",
            "silent_mode",
            "silent_mode_start_time",
            "silent_mode_end_time",
            "bivalent_temperature",
            "starting_delay_ch_backup",
            "heat_pump_compressor_min_temperature",
        },
    }
    """Field names indexed by the GTW software version in which they were added to the parameter list."""

    max_span = REMEHA_MAX_SPAN
    register_ranges = (
        (384, 390),
        (400, 438),
        (439, 494),
        (500, 503),
        (9009, 9012),
        (9202, 9202),
        (9230, 9230),
    )

    outside_temperature = int16(address=384, scale=0.01, unit="°C")
    """The outside temperature."""

    season_mode = enum(address=385, enum_type=SeasonalMode, signed=False, nan=0xFF)
    """Which season mode is currently active."""

    summer_winter = uint16(address=386, scale=0.01, writable=True, unit="°C")
    """Upper limit of outdoor temperature for heating (30.5 means disabled)."""

    neutral_band_summer_winter = uint16(address=387, scale=0.01, writable=True, unit="°C")
    """Temperature band below the summer/winter limit within which the appliance
    neither heats nor cools (parameter AP075)."""

    forced_summer_mode = boolean(address=389, nan=0xFF, writable=True)
    """Whether forced summer mode is active (parameter AP074)."""

    flow_temperature = int16(address=400, scale=0.01, unit="°C")
    """Current flow temperature (parameter AM016)."""

    return_temperature = int16(address=401, scale=0.01, unit="°C")
    """Current return temperature (parameter AM018)."""

    heat_pump_flow_temperature = int16(address=403, scale=0.01, unit="°C")
    """Current heat pump flow temperature (parameter HM001)."""

    heat_pump_return_temperature = int16(address=404, scale=0.01, unit="°C")
    """Current heat pump return temperature (parameter HM001)."""

    actual_water_pressure = uint8(address=409, scale=0.1, unit="bar")
    """The actual water pressure measured in bar."""

    flow_rate = uint16(address=410, scale=0.01, unit="L/min")
    """The current flow rate in L/min."""

    appliance_status = enum(address=411, enum_type=ApplianceStatus, nan=0xFF)
    """The current appliance status (parameter AM012)."""

    appliance_substatus = enum(address=412, enum_type=ApplianceSubStatus)
    """The current appliance substatus. Shows details about the current status (parameter AM014)."""

    actual_relative_power = uint16(address=413, scale=0.01, unit="%")
    """The actual relative power being produced (parameter AM024)."""

    generator_starts_total = uint32(address=419, nan=0xFFFFFFFF)
    """The total burner/compressor start count (parameter PC002)."""

    generator_hours_total = uint32(address=421, unit="h", nan=0xFFFFFFFF)
    """The total burner/compressor run time in hours (parameter PC003)."""

    backup1_starts = uint32(address=423, nan=0xFFFFFFFF)
    """The total start count of backup 1 (parameter AC030)."""

    backup1_hours = uint32(address=425, unit="h", nan=0xFFFFFFFF)
    """The total backup1 run time in hours (parameter AC028)."""

    backup2_starts = uint32(address=427, nan=0xFFFFFFFF)
    """The total start count of backup 2 (parameter AC031)."""

    backup2_hours = uint32(address=429, unit="h", nan=0xFFFFFFFF)
    """The total backup2 run time in hours (parameter AC029)."""

    power_on_hours = uint32(address=431, unit="h", nan=0xFFFFFFFF)
    """The total number of hours the appliance was active (parameter AC001)."""

    ch_energy_consumption = uint32(address=433, unit="kWh", nan=0xFFFFFFFF)
    """Total energy consumed for production of central heat (parameter AC005)."""

    dhw_energy_consumption = uint32(address=435, unit="kWh", nan=0xFFFFFFFF)
    """Total energy consumed for production of domestic hot water (parameter AC006)."""

    cooling_energy_consumption = uint32(address=437, unit="kWh", nan=0xFFFFFFFF)
    """Total energy consumed for cooling (parameter AC007)."""

    total_energy_consumption = uint32(address=439, unit="kWh", nan=0xFFFFFFFF)
    """Total energy consumed in the current year."""

    backup_energy_consumption = uint32(address=441, unit="kWh", nan=0xFFFFFFFF)
    """Total energy consumed by electrical or hydraulic backup (parameter AC018)."""

    total_energy_delivery = uint32(address=443, unit="kWh", nan=0xFFFFFFFF)
    """Total energy delivered in the current year."""

    ch_energy_delivery = uint32(address=445, unit="kWh", nan=0xFFFFFFFF)
    """Energy delivered for central heating (parameter AC008)."""

    dhw_energy_delivery = uint32(address=447, unit="kWh", nan=0xFFFFFFFF)
    """Energy delivered for domestic hot water (parameter AC009)."""

    cooling_energy_delivery = uint32(address=449, unit="kWh", nan=0xFFFFFFFF)
    """Energy delivered for cooling (parameter AC010)."""

    backup_energy_delivery = uint32(address=451, unit="kWh", nan=0xFFFFFFFF)
    """Energy delivered for electrical or hydraulic backup (parameter AC019)."""

    pump_speed = uint16(address=459, scale=0.1, unit="%")
    """Current pump speed in percent."""

    actual_produced_power = uint32(address=460, scale=0.01, unit="W", nan=0xFFFFFFFF)
    """Signal used to capture actual power calculation."""

    cop_calculated = uint16(address=462, scale=0.001)
    """Instantaneous calculated Coefficient of Performance (COP) (parameter HM031)."""

    min_time_between_dhw_productions = uint8(address=477, writable=in_range(range(11)), unit="h")
    """The minimum time between two periods of producing DHW."""

    max_dhw_production_time = uint8(address=478, writable=in_range(range(1, 11)), unit="h")
    """Maximum time allowed to produce DHW."""

    heat_pump_defrost_active = boolean(address=481, nan=0xFF)
    """Heat pump defrost mode active (parameter HM009)."""

    backup_type = enum(address=482, enum_type=BackupType, signed=False, nan=0xFF, writable=True)
    """The type of backup heat source for the heat pump."""

    bivalent_temperature = int16(
        address=487, scale=0.01, writable=in_range(range(-10, 21)), unit="°C"
    )
    """Outside temperature level above which the backup operation is blocked for a standard heating mode."""

    starting_delay_ch_backup = uint16(address=488, writable=in_range(range(601)), unit="min")
    """Delay for starting the next generator (backup stage) in central heating mode."""

    heat_pump_compressor_min_temperature = int16(
        address=489, scale=0.01, writable=in_range(range(-20, 6)), unit="°C"
    )
    """Minimum outside temperature below which the heat pump compressor is stopped."""

    silent_mode = enum(address=490, enum_type=SilentMode, signed=False, nan=0xFF, writable=True)
    """The silent mode level of the appliance."""

    silent_mode_start_time = time_steps(address=491, writable=True)
    """The time of day at which the silent mode starts."""

    silent_mode_end_time = time_steps(address=492, writable=True)
    """The time of day at which the silent mode ends."""

    ch_enabled = boolean(address=500, nan=0xFF, writable=True)
    """Whether central heating demand processing is enabled."""

    dhw_enabled = boolean(address=501, nan=0xFF, writable=True)
    """Whether domestic hot water processing is enabled."""

    cooling_type = enum(address=502, enum_type=CoolingType, signed=False, nan=0xFF, writable=True)
    """The type of cooling."""

    forced_cooling_mode = boolean(address=503, nan=0xFF, writable=True)
    """Whether the appliance is in forced cooling mode.

    This variable is defined on the appliance level. In the Remeha Home app however, this variable
    is configurable in two places: in the CH zone and at the system level. Change one, change
    the other too.
    In this integration, this value is shown in all CH climates and can be set as follows:

    * To force cooling, set HVACMode to COOL
    * To let the system decide to cool or heat, set HVACMode to HEAT_COOL
    """

    # TODO These registers are for a Thermodynamic Water Heater. Move to dedicated class if more follow.
    digital_input_1_configuration = enum(
        address=9009, enum_type=DigitalInputConfiguration, signed=False, nan=0xFF, writable=True
    )
    """Configuration of digital input 1 (`D.I1`, parameter `HP059`). Only available for `CU_HW` mainboards."""

    digital_input_2_configuration = enum(
        address=9010, enum_type=DigitalInputConfiguration, signed=False, nan=0xFF, writable=True
    )
    """Configuration of digital input 2 (`D.I2`, parameter `HP076`). Only available for `CU_HW` mainboards."""

    digital_input_1_contact_logic = enum(
        address=9011, enum_type=DIContactLogicConfiguration, signed=False, nan=0xFF, writable=True
    )
    """Configuration of the default state of digital input 1. Only available for `CU_HW` mainboards."""

    digital_input_2_contact_logic = enum(
        address=9012, enum_type=DIContactLogicConfiguration, signed=False, nan=0xFF, writable=True
    )
    """Configuration of the default state of digital input 2. Only available for `CU_HW` mainboards."""

    # TODO These are registers for hybrid appliances. If more than 4 are required, move to dedicated class.
    hybrid_internal_dhw_setpoint = int16(address=9202, scale=0.01)
    """Internal setpoint used for hot water production."""

    hybrid_cop_calculated = uint16(address=9230, scale=0.001)
    """Instantaneous calculated Coefficient of Performance (COP) on a hybrid system (parameter HM031)."""

    def __init__(
        self, unit: ModbusUnit, index: int = 1, *, base_offset: int = 0, _instance_offset: int = 0
    ) -> None:
        """Create a new ``Appliance`` instance."""

        super().__init__(unit, index, base_offset=base_offset, _instance_offset=_instance_offset)

    @classmethod
    def _gateway_restrictions(cls, gateway: DeviceBoard) -> set[str]:
        gateway_version = gateway.software_version

        if gateway_version is None:
            _LOGGER.info("Could not detect gateway version; using all Appliance fields.")
            return {f for fs in cls.restrictions_by_gtw_version.values() for f in fs}
        _LOGGER.info(
            "Using Appliance fields for gateway version %02d.%02d",
            gateway_version[0],
            gateway_version[1],
        )
        merged_version = (gateway_version[0] << 8) | gateway_version[1]
        return {
            field
            for version, version_fields in cls.restrictions_by_gtw_version.items()
            for field in version_fields
            if merged_version >= version
        }

    def restrict_fields_for_device(self, device: DeviceBoard, gateway: DeviceBoard) -> None:
        """Ensure that only fields supported by `device` can be read and written.

        This method assumes it is called once, on gateway setup.

        Args:
            device (DeviceBoard): The device to restrict field availability by.
            gateway (DeviceBoard): The modbus gateway board to restrict field availability by.

        """

        board_category = device.board_category
        if not board_category or board_category.type is None:
            # Keep all fields. If restrict_fields_for_device is called multiple times,
            # restricted fields are only overwritten for DeviceBoardType.CU_HW.
            return

        if board_category.type is DeviceBoardType.CU_HW:
            # Restrict unsupported sensors.
            self.restrict_fields([
                name
                for name, _ in inspect.getmembers_static(
                    Appliance,
                    lambda member: (
                        (isinstance(member, (RegisterField, CoilField, DiscreteInputField)))
                        and member.name not in self._cu_hw_board_unsupported_fields
                    ),
                )
            ])
            return

        # Restrict fields by gateway version
        self.restrict_fields([
            name
            for name, _ in inspect.getmembers_static(
                Appliance,
                lambda member: (
                    (isinstance(member, (RegisterField, CoilField, DiscreteInputField)))
                    and member.name not in self._other_board_unsupported_fields
                    and member.name in Appliance._gateway_restrictions(gateway)
                ),
            )
        ])

    def is_cooling_required(self) -> bool:
        """Whether the appliance cooling mode is required.

        This can be forced (`forced_cooling_mode == True`) or derived (`season_mode` is in a summer variant).
        """

        return self.forced_cooling_mode or self.season_mode in {
            SeasonalMode.SUMMER_NEUTRAL_BAND,
            SeasonalMode.SUMMER,
        }

    async def async_set_summer_winter(self, temperature: float) -> None:
        """Set the outdoor temperature upper limit for heating.

        Args:
            temperature (float): The outdoor temperature in °C.

        """

        await self.write("summer_winter", temperature)

    async def async_set_neutral_band_summer_winter(self, bandwidth: float) -> None:
        """Set the neutral band in which the heat pump is deactivated.

        Args:
            bandwidth (float): The bandwidth in °C

        """

        await self.write("neutral_band_summer_winter", bandwidth)

    async def async_enable_forced_summer_mode(self) -> None:
        """Stop heating, maintain hot water. Force summer mode."""

        await self.write("forced_summer_mode", True)

    async def async_disable_forced_summer_mode(self) -> None:
        """Do not force summer mode."""

        await self.write("forced_summer_mode", False)

    async def async_set_min_time_between_dhw_productions(self, hours: float) -> None:
        """Set the minimum required time between two DHW productions.

        Args:
            hours (float): The required time in hours. Must be between 0 and 10.

        """

        await self.write("min_time_between_dhw_productions", hours)

    async def async_set_max_dhw_production_time(self, hours: float) -> None:
        """Set the maximum allowed duration of DHW production.

        Args:
            hours (float): The maximum allowed duration in hours. Must be between 1 and 10.

        """

        await self.write("max_dhw_production_time", hours)

    async def async_set_backup_type(self, backup_type: BackupType) -> None:
        """Set the backup type for this appliance.

        Not all appliances support all backup types. For instance, a heat pump boiler
        like Azorra Ace 200/250H _does_ support a 2-stage electrical backup, while the
        non-H versions do not support that.

        Users are assumed to know what their appliance supports and act accordingly.

        Args:
            backup_type(BackupType): The new backup type for this appliance.

        """

        await self.write("backup_type", backup_type)

    async def async_set_bivalent_temperature(self, temperature: float) -> None:
        """Set the outside temperature above which the backup operation is blocked.

        Args:
            temperature (float): The temperature in °C. Must be between -10 and 20 °C.

        """

        await self.write("bivalent_temperature", temperature)

    async def async_set_starting_delay_ch_backup(self, minutes: float) -> None:
        """Set the delay for starting the next generator (backup stage) in central heating mode.

        Args:
            minutes (float): The delay in minutes. Must be between 0 and 600.

        """

        await self.write("starting_delay_ch_backup", minutes)

    async def async_set_heat_pump_compressor_min_temperature(self, temperature: float) -> None:
        """Set the minimum outside temperature below which the heat pump compressor is stopped.

        If the outside temperature falls below `temperature`, the heat pump compressor is stopped
        and backup takes over.

        Args:
            temperature (float): The minimum temperature in °C. Must be between -20 and 5 °C.

        """

        await self.write("heat_pump_compressor_min_temperature", temperature)

    async def async_set_silent_mode(self, value: SilentMode) -> None:
        """Set the silent mode level.

        Args:
            value (SilentMode): The requested silent mode.

        """
        await self.write("silent_mode", value)

    async def async_set_silent_mode_start_time(self, start_time: time) -> None:
        """Set the time of day at which the silent mode starts.

        Args:
            start_time (time): The time at which the silent mode should start.

        """
        await self.write("silent_mode_start_time", start_time)

    async def async_set_silent_mode_end_time(self, end_time: time) -> None:
        """Set the time of day at which the silent mode ends.

        Args:
            end_time (time): The time at which the silent mode should end.

        """
        await self.write("silent_mode_end_time", end_time)

    async def async_enable_ch_processing(self) -> None:
        """Enable central heat demand processing."""
        await self.write("ch_enabled", True)

    async def async_disable_ch_processing(self) -> None:
        """Disable central heat demand processing."""
        await self.write("ch_enabled", False)

    async def async_enable_dhw_processing(self) -> None:
        """Enable domestic hot water demand processing."""
        await self.write("dhw_enabled", True)

    async def async_disable_dhw_processing(self) -> None:
        """Disable domestic hot water demand processing."""
        await self.write("dhw_enabled", False)

    async def async_set_cooling_type(self, value: CoolingType) -> None:
        """Set the type of cooling for this appliance.

        Args:
            value (CoolingType): The requested cooling type.

        """
        await self.write("cooling_type", value)

    async def async_enable_forced_cooling_mode(self) -> None:
        """Enable forced cooling mode."""

        await self.write("forced_cooling_mode", True)

    async def async_disable_forced_cooling_mode(self) -> None:
        """Disable forced cooling mode."""

        await self.write("forced_cooling_mode", False)

    async def async_set_digital_input_1_configuration(
        self, value: DigitalInputConfiguration
    ) -> None:
        """Set the configuration of digital input 1."""

        await self.write("digital_input_1_configuration", value)

    async def async_set_digital_input_2_configuration(
        self, value: DigitalInputConfiguration
    ) -> None:
        """Set the configuration of digital input 2."""

        await self.write("digital_input_2_configuration", value)

    async def async_set_digital_input_1_contact_logic(
        self, value: DIContactLogicConfiguration
    ) -> None:
        """Set the contact logic for digital input 1."""

        await self.write("digital_input_1_contact_logic", value)

    async def async_set_digital_input_2_contact_logic(
        self, value: DIContactLogicConfiguration
    ) -> None:
        """Set the contact logic for digital input 2."""

        await self.write("digital_input_2_contact_logic", value)
