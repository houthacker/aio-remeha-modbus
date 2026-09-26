"""Tests for the system discovery table."""

import pytest
from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.gtw08 import GTW08
from aio_remeha_modbus.gtw08.system_discovery_table import (
    DeviceBoard,
    DeviceBoardCategory,
    DeviceBoardType,
    SystemDiscoveryTable,
)
from tests.conftest import get_modbus_unit

_BOARD_0_TYPE_REGISTER = 129
_BOARD_1_TYPE_REGISTER = 135


def test_device_board_category():
    """Test the different textual representations of the DeviceBoardCategory.

    Required because these are shown in the front-end.
    """
    assert str(DeviceBoardCategory(type=DeviceBoardType.CU_GH, generation=2)) == "CU-GH-2"
    assert str(DeviceBoardCategory(type=DeviceBoardType.CU_OH, generation=3)) == "CU-OH-3"
    assert str(DeviceBoardCategory(type=DeviceBoardType.EHC, generation=10)) == "EHC-10"
    assert str(DeviceBoardCategory(type=DeviceBoardType.MK, generation=3)) == "MK-3"
    assert str(DeviceBoardCategory(type=DeviceBoardType.SCB, generation=17)) == "SCB-17"
    assert str(DeviceBoardCategory(type=DeviceBoardType.EEC, generation=2)) == "EEC-2"
    assert str(DeviceBoardCategory(type=DeviceBoardType.GATEWAY, generation=8)) == "GTW-8"

    # Compare to a different type
    assert DeviceBoardCategory(type=DeviceBoardType.EHC, generation=10) != DeviceBoardType.EHC


def test_device_board_category_equality_ignores_generation():
    """Test that only the type determines equality and the hash of a category."""

    ehc_8 = DeviceBoardCategory(type=DeviceBoardType.EHC, generation=8)
    ehc_10 = DeviceBoardCategory(type=DeviceBoardType.EHC, generation=10)
    scb_8 = DeviceBoardCategory(type=DeviceBoardType.SCB, generation=8)

    assert ehc_8 == ehc_10
    assert hash(ehc_8) == hash(ehc_10)
    assert ehc_8 != scb_8
    assert len({ehc_8, ehc_10, scb_8}) == 2


@pytest.mark.parametrize(
    ("board_type", "expected"),
    [
        (DeviceBoardType.CU_GH, True),
        (DeviceBoardType.CU_OH, True),
        (DeviceBoardType.EHC, True),
        (DeviceBoardType.EHC_ALT, True),
        (DeviceBoardType.EEC, True),
        (DeviceBoardType.MK, False),
        (DeviceBoardType.SCB, False),
        (DeviceBoardType.GATEWAY, False),
    ],
)
def test_device_board_type_is_mainboard(board_type: DeviceBoardType, expected: bool):
    """Test which device board types are mainboards."""

    assert board_type.is_mainboard() is expected


@pytest.mark.asyncio
async def test_device_board_read(remeha_modbus_unit):
    """Test the device instance equality is based on it and board type.

    This allows HA to update device info if for instance the software version changes.
    """

    device_board = DeviceBoard(unit=remeha_modbus_unit)
    await device_board.async_update()
    assert device_board.id == 0
    assert device_board.board_category == DeviceBoardCategory(
        type=DeviceBoardType.EHC, generation=8
    )
    assert device_board.software_version == (1, 1)
    assert device_board.config_table_version == (1, 2)
    assert device_board.hardware_version == (2, 1)
    assert device_board.article_number == 7853960
    assert device_board.is_mainboard() is True


@pytest.mark.asyncio
async def test_device_board_equality(remeha_modbus_unit: MockModbusUnit):
    """Test that boards are equal if their category is equal, regardless of versions."""

    first = DeviceBoard(unit=remeha_modbus_unit)
    await first.async_update()

    remeha_modbus_unit.holding[130] = 0x0909  # a software upgrade
    second = DeviceBoard(unit=remeha_modbus_unit)
    await second.async_update()

    assert first.software_version != second.software_version
    assert first == second
    assert hash(first) == hash(second)
    assert first != first.board_category


@pytest.mark.asyncio
async def test_device_board_not_equal_for_other_category(remeha_modbus_unit: MockModbusUnit):
    """Test that boards with a different category are not equal."""

    first = DeviceBoard(unit=remeha_modbus_unit)
    await first.async_update()

    remeha_modbus_unit.holding[_BOARD_0_TYPE_REGISTER] = 0x190A  # SCB
    second = DeviceBoard(unit=remeha_modbus_unit)
    await second.async_update()

    assert second.board_category is not None
    assert second.board_category.type is DeviceBoardType.SCB
    assert second.is_mainboard() is False
    assert first != second


@pytest.mark.asyncio
async def test_device_board_unset_versions(remeha_modbus_unit: MockModbusUnit):
    """Test that versions that report nan are read as `None`."""

    for register in (130, 131, 132):
        remeha_modbus_unit.holding[register] = 0xFFFF

    board = DeviceBoard(unit=remeha_modbus_unit)
    await board.async_update()

    assert board.software_version is None
    assert board.config_table_version is None
    assert board.hardware_version is None


@pytest.mark.asyncio
async def test_device_board_unknown_type(remeha_modbus_unit: MockModbusUnit):
    """Test that a board type that is not known is refused by the category."""

    remeha_modbus_unit.holding[_BOARD_0_TYPE_REGISTER] = 0x7F0A

    board = DeviceBoard(unit=remeha_modbus_unit)
    await board.async_update()

    with pytest.raises(ValueError, match="is not a valid DeviceBoardType"):
        _ = board.board_category


@pytest.mark.asyncio
async def test_device_board_id_uses_register_stride(remeha_modbus_unit: MockModbusUnit):
    """Test that the id of a board follows from its register offset."""

    remeha_modbus_unit.holding[_BOARD_1_TYPE_REGISTER] = 0x190A
    table = SystemDiscoveryTable(remeha_modbus_unit)
    await table.async_update()

    assert [board.id for board in table.device_boards] == [0, 1]


@pytest.mark.asyncio
async def test_discovery_table_number_of_zones(gtw_08: GTW08):
    """Test that the number of zones is read."""

    assert gtw_08.discovery_table.number_of_zones == 2


@pytest.mark.asyncio
async def test_discovery_table_reset(gtw_08: GTW08):
    """Test that a reset writes the reset command to the discovery table."""

    unit = get_modbus_unit(gtw_08)
    assert unit.holding[200] == 0

    await gtw_08.discovery_table.reset()

    assert unit.holding[200] == 0x5A
