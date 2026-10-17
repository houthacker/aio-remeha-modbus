"""Tests for the appliance."""

from datetime import time

import pytest
from modbus_connection.mock import MockModbusConnection, MockModbusUnit

from aio_remeha_modbus.gtw08.appliance import (
    Appliance,
    ApplianceStatus,
    ApplianceSubStatus,
    BackupType,
    CoolingType,
    SeasonalMode,
    SilentMode,
)
from aio_remeha_modbus.gtw08.system_discovery_table import DeviceBoard, DeviceBoardType
from tests.conftest import load_modbus_store

_CU_HW_UNSUPPORTED_FIELDS = (
    "outside_temperature",
    "flow_temperature",
    "return_temperature",
    "heat_pump_flow_temperature",
    "heat_pump_return_temperature",
)

_OTHER_BOARD_TYPES = [
    pytest.param(board_type, id=board_type.name)
    for board_type in DeviceBoardType
    if board_type != DeviceBoardType.CU_HW
]


def _set_board_type(unit: MockModbusUnit, board_type: DeviceBoardType) -> None:
    """Replace the mainboard type in the high byte, keeping the generation in the low byte."""

    unit.holding[129] = (board_type << 8) | (unit.holding[129] & 0xFF)


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_appliance(remeha_modbus_unit: MockModbusUnit):
    """Test that an Appliance is read correctly."""

    appliance = Appliance(remeha_modbus_unit)
    await appliance.async_update()

    assert appliance.outside_temperature == 24.82
    assert appliance.season_mode == SeasonalMode.SUMMER
    assert appliance.summer_winter == 22.0
    assert appliance.neutral_band_summer_winter == 4.0
    assert not appliance.forced_summer_mode
    assert appliance.flow_temperature == 20.44
    assert appliance.return_temperature == 20.0
    assert appliance.heat_pump_flow_temperature == 21.14
    assert appliance.heat_pump_return_temperature == 22.54
    assert appliance.actual_water_pressure == 1.2
    assert appliance.flow_rate == 12.66
    assert appliance.appliance_status == ApplianceStatus.manual_heat_demand
    assert appliance.appliance_substatus == ApplianceSubStatus.power_controlled
    assert appliance.actual_relative_power == 0.5
    assert appliance.generator_starts_total == 1234
    assert appliance.backup1_starts == 321
    assert appliance.backup1_hours == 456
    assert appliance.backup2_starts == 100
    assert appliance.backup2_hours == 200
    assert appliance.power_on_hours == 10_000
    assert appliance.ch_energy_consumption == 5_000
    assert appliance.dhw_energy_consumption == 3000
    assert appliance.cooling_energy_consumption == 500
    assert appliance.backup_energy_consumption == 4000
    assert appliance.total_energy_consumption == 0
    assert appliance.total_energy_delivery == 0
    assert appliance.total_energy_delivery == 0
    assert appliance.ch_energy_delivery == 2200
    assert appliance.dhw_energy_delivery == 3500
    assert appliance.cooling_energy_delivery == 0
    assert appliance.backup_energy_delivery == 0
    assert appliance.pump_speed == 5.0
    assert appliance.actual_produced_power == 6562
    assert appliance.cop_calculated == 3.2
    assert appliance.silent_mode == SilentMode.LEVEL_1
    assert appliance.silent_mode_start_time == time(hour=22)
    assert appliance.silent_mode_end_time == time(hour=7)
    assert appliance.ch_enabled
    assert appliance.cooling_type == CoolingType.ACTIVE_COOLING
    assert not appliance.forced_cooling_mode
    assert appliance.hybrid_cop_calculated == 3.5


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_appliance_write(remeha_modbus_unit: MockModbusUnit):
    """Test that an Appliance can be written to successfully."""

    appliance = Appliance(remeha_modbus_unit)
    await appliance.async_update()

    expected = time(hour=23)
    assert appliance.silent_mode_start_time != expected

    await appliance.async_set_silent_mode_start_time(expected)
    await appliance.async_update()
    assert appliance.silent_mode_start_time == expected


async def _updated_appliance(unit: MockModbusUnit) -> Appliance:
    """Create an appliance and read its values."""

    appliance = Appliance(unit)
    await appliance.async_update()

    return appliance


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_appliance_set_summer_winter(remeha_modbus_unit: MockModbusUnit):
    """Test that the summer/winter outside temperature limit can be written."""

    appliance = await _updated_appliance(remeha_modbus_unit)
    assert appliance.summer_winter == 22.0

    await appliance.async_set_summer_winter(18.5)

    assert remeha_modbus_unit.holding[386] == 1850
    await appliance.async_update()
    assert appliance.summer_winter == 18.5


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_appliance_set_neutral_band_summer_winter(remeha_modbus_unit: MockModbusUnit):
    """Test that the summer/winter neutral band can be written."""

    appliance = await _updated_appliance(remeha_modbus_unit)
    assert appliance.neutral_band_summer_winter == 4.0

    await appliance.async_set_neutral_band_summer_winter(2.5)

    assert remeha_modbus_unit.holding[387] == 250
    await appliance.async_update()
    assert appliance.neutral_band_summer_winter == 2.5


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_appliance_forced_summer_mode(remeha_modbus_unit: MockModbusUnit):
    """Test that forced summer mode can be enabled and disabled."""

    appliance = await _updated_appliance(remeha_modbus_unit)
    assert not appliance.forced_summer_mode

    await appliance.async_enable_forced_summer_mode()
    assert remeha_modbus_unit.holding[389] != 0
    await appliance.async_update()
    assert appliance.forced_summer_mode is True

    await appliance.async_disable_forced_summer_mode()
    assert remeha_modbus_unit.holding[389] == 0
    await appliance.async_update()
    assert appliance.forced_summer_mode is False


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
@pytest.mark.parametrize("mode", list(SilentMode))
async def test_appliance_set_silent_mode(remeha_modbus_unit: MockModbusUnit, mode: SilentMode):
    """Test that every silent mode can be written."""

    appliance = await _updated_appliance(remeha_modbus_unit)

    await appliance.async_set_silent_mode(mode)

    assert remeha_modbus_unit.holding[490] == mode.value
    await appliance.async_update()
    assert appliance.silent_mode == mode


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_appliance_set_silent_mode_times(remeha_modbus_unit: MockModbusUnit):
    """Test that the silent mode start and end time can be written."""

    appliance = await _updated_appliance(remeha_modbus_unit)

    await appliance.async_set_silent_mode_start_time(time(21, 30))
    await appliance.async_set_silent_mode_end_time(time(6, 10))

    assert remeha_modbus_unit.holding[491] == 21 * 6 + 3
    assert remeha_modbus_unit.holding[492] == 6 * 6 + 1
    await appliance.async_update()
    assert appliance.silent_mode_start_time == time(21, 30)
    assert appliance.silent_mode_end_time == time(6, 10)


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_appliance_ch_enabled(remeha_modbus_unit: MockModbusUnit):
    """Test that central heating can be disabled and enabled."""

    appliance = await _updated_appliance(remeha_modbus_unit)
    assert appliance.ch_enabled is True

    await appliance.async_set_ch_disabled()
    assert remeha_modbus_unit.holding[500] == 0
    await appliance.async_update()
    assert appliance.ch_enabled is False

    await appliance.async_set_ch_enabled()
    assert remeha_modbus_unit.holding[500] != 0
    await appliance.async_update()
    assert appliance.ch_enabled is True


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
@pytest.mark.parametrize("cooling_type", list(CoolingType))
async def test_appliance_set_cooling_type(
    remeha_modbus_unit: MockModbusUnit, cooling_type: CoolingType
):
    """Test that every cooling type can be written."""

    appliance = await _updated_appliance(remeha_modbus_unit)

    await appliance.async_set_cooling_type(cooling_type)

    assert remeha_modbus_unit.holding[502] == cooling_type.value
    await appliance.async_update()
    assert appliance.cooling_type == cooling_type


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_appliance_forced_cooling_mode(remeha_modbus_unit: MockModbusUnit):
    """Test that forced cooling mode can be enabled and disabled."""

    appliance = await _updated_appliance(remeha_modbus_unit)
    assert not appliance.forced_cooling_mode

    await appliance.async_enable_forced_cooling_mode()
    assert remeha_modbus_unit.holding[503] != 0
    await appliance.async_update()
    assert appliance.forced_cooling_mode is True

    await appliance.async_disable_forced_cooling_mode()
    assert remeha_modbus_unit.holding[503] == 0
    await appliance.async_update()
    assert appliance.forced_cooling_mode is False


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
@pytest.mark.parametrize(
    ("season_mode", "forced_cooling", "expected"),
    [
        (SeasonalMode.WINTER, False, False),
        (SeasonalMode.WINTER_FROST_PROTECTION, False, False),
        (SeasonalMode.SUMMER_NEUTRAL_BAND, False, True),
        (SeasonalMode.SUMMER, False, True),
        (SeasonalMode.WINTER, True, True),
        (SeasonalMode.WINTER_FROST_PROTECTION, True, True),
        (SeasonalMode.SUMMER, True, True),
    ],
)
async def test_appliance_is_cooling_required(
    remeha_modbus_unit: MockModbusUnit,
    season_mode: SeasonalMode,
    forced_cooling: bool,
    expected: bool,
):
    """Test that cooling is required when forced or in a summer season mode."""

    remeha_modbus_unit.holding[385] = season_mode.value
    remeha_modbus_unit.holding[503] = 1 if forced_cooling else 0

    appliance = await _updated_appliance(remeha_modbus_unit)

    assert appliance.is_cooling_required() is expected


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["appliance.json"], indirect=True)
async def test_appliance_nan_values(remeha_modbus_unit: MockModbusUnit):
    """Test that registers reporting their nan value are read as `None`."""

    remeha_modbus_unit.holding[385] = 0xFF  # season_mode
    remeha_modbus_unit.holding[503] = 0xFF  # forced_cooling_mode
    remeha_modbus_unit.holding[419] = 0xFFFF  # generator_starts_total (high word)
    remeha_modbus_unit.holding[420] = 0xFFFF  # generator_starts_total (low word)
    remeha_modbus_unit.holding[490] = 0xFF  # silent_mode
    remeha_modbus_unit.holding[491] = 0xFF  # silent_mode_start_time
    remeha_modbus_unit.holding[482] = 0xFF  # backup_type

    appliance = await _updated_appliance(remeha_modbus_unit)

    assert appliance.backup_type is None
    assert appliance.season_mode is None
    assert appliance.forced_cooling_mode is None
    assert appliance.generator_starts_total is None
    assert appliance.silent_mode is None
    assert appliance.silent_mode_start_time is None
    assert appliance.is_cooling_required() is False


async def _restricted_appliance(unit: MockModbusUnit) -> Appliance:
    """Create an appliance restricted to the unit's mainboard and read its values."""

    device_board = DeviceBoard(unit=unit)
    await device_board.async_update()

    appliance = Appliance(unit)
    appliance.restrict_fields_for_device(device_board)
    await appliance.async_update()

    return appliance


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["azorra_ace_store.json"], indirect=True)
async def test_appliance_restrict_fields_for_cu_hw(remeha_modbus_unit: MockModbusUnit):
    """Test that fields unsupported by a CU-HW mainboard read as `None`."""

    appliance = await _restricted_appliance(remeha_modbus_unit)

    assert all(getattr(appliance, name) is None for name in _CU_HW_UNSUPPORTED_FIELDS)
    assert appliance.silent_mode == SilentMode.LEVEL_1


@pytest.mark.asyncio
@pytest.mark.parametrize("board_type", _OTHER_BOARD_TYPES)
async def test_appliance_restrict_fields_for_other_boards(
    remeha_modbus_unit: MockModbusUnit, board_type: DeviceBoardType
):
    """Test that all fields remain available for non CU-HW mainboards."""

    _set_board_type(remeha_modbus_unit, board_type)

    appliance = await _restricted_appliance(remeha_modbus_unit)

    assert all(getattr(appliance, name) is not None for name in _CU_HW_UNSUPPORTED_FIELDS)
    assert appliance.silent_mode == SilentMode.LEVEL_1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("remeha_modbus_unit", "expected"),
    [
        pytest.param("azorra_ace_store.json", BackupType.SINGLE_STAGE_ELECTRICAL, id="CU_HW"),
        pytest.param("modbus_store.json", BackupType.DOUBLE_STAGE_ELECTRICAL, id="EHC"),
    ],
    indirect=["remeha_modbus_unit"],
)
async def test_appliance_read_backup_type(remeha_modbus_unit: MockModbusUnit, expected: BackupType):
    """Test that the backup type is read."""

    appliance = await _restricted_appliance(remeha_modbus_unit)

    assert appliance.backup_type == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["azorra_ace_store.json"], indirect=True)
@pytest.mark.parametrize(
    "backup_type",
    [
        pytest.param(backup_type, id=backup_type.name)
        for backup_type in BackupType
        if backup_type != BackupType.DOUBLE_STAGE_ELECTRICAL
    ],
)
async def test_appliance_set_backup_type_cu_hw(
    remeha_modbus_unit: MockModbusUnit, backup_type: BackupType
):
    """Test that a CU-HW mainboard accepts all backup types except a double stage electrical one."""

    appliance = await _restricted_appliance(remeha_modbus_unit)

    await appliance.async_set_backup_type(backup_type)

    assert remeha_modbus_unit.holding[482] == backup_type.value
    await appliance.async_update()
    assert appliance.backup_type == backup_type


@pytest.mark.asyncio
@pytest.mark.parametrize("remeha_modbus_unit", ["azorra_ace_store.json"], indirect=True)
async def test_appliance_set_backup_type_cu_hw_rejects_double_stage_electrical(
    remeha_modbus_unit: MockModbusUnit,
):
    """Test that a CU-HW mainboard rejects a double stage electrical backup type."""

    appliance = await _restricted_appliance(remeha_modbus_unit)

    with pytest.raises(ValueError, match="DOUBLE_STAGE_ELECTRICAL"):
        await appliance.async_set_backup_type(BackupType.DOUBLE_STAGE_ELECTRICAL)

    assert remeha_modbus_unit.holding[482] == BackupType.SINGLE_STAGE_ELECTRICAL.value


@pytest.mark.asyncio
@pytest.mark.parametrize("board_type", _OTHER_BOARD_TYPES)
@pytest.mark.parametrize(
    "backup_type", [pytest.param(backup_type, id=backup_type.name) for backup_type in BackupType]
)
async def test_appliance_set_backup_type_other_boards(
    remeha_modbus_unit: MockModbusUnit, board_type: DeviceBoardType, backup_type: BackupType
):
    """Test that non CU-HW mainboards accept all backup types."""

    _set_board_type(remeha_modbus_unit, board_type)
    appliance = await _restricted_appliance(remeha_modbus_unit)

    await appliance.async_set_backup_type(backup_type)

    assert remeha_modbus_unit.holding[482] == backup_type.value
    await appliance.async_update()
    assert appliance.backup_type == backup_type


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "backup_type", [pytest.param(backup_type, id=backup_type.name) for backup_type in BackupType]
)
async def test_appliance_set_backup_type_unrestricted(
    remeha_modbus_unit: MockModbusUnit, backup_type: BackupType
):
    """Test that an appliance without a known mainboard accepts all backup types."""

    appliance = await _updated_appliance(remeha_modbus_unit)

    await appliance.async_set_backup_type(backup_type)

    assert remeha_modbus_unit.holding[482] == backup_type.value


@pytest.mark.asyncio
async def test_appliance_unsupported_backup_types_are_per_instance(
    remeha_modbus_unit: MockModbusUnit, mock_modbus_connection: MockModbusConnection
):
    """Test that restricting one appliance does not restrict another."""

    azorra_ace_unit = mock_modbus_connection.for_unit(2)
    load_modbus_store(azorra_ace_unit, "azorra_ace_store.json")
    await _restricted_appliance(azorra_ace_unit)

    appliance = await _restricted_appliance(remeha_modbus_unit)

    await appliance.async_set_backup_type(BackupType.DOUBLE_STAGE_ELECTRICAL)

    assert remeha_modbus_unit.holding[482] == BackupType.DOUBLE_STAGE_ELECTRICAL.value
