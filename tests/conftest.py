"""Fixtures for testing."""

import json
import pathlib
from collections.abc import Generator
from datetime import tzinfo
from typing import Any, Final
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from dateutil import tz
from modbus_connection import ModbusUnit
from modbus_connection.mock import MockModbusUnit

from aio_remeha_modbus.api import RemehaApi
from aio_remeha_modbus.api.const import (
    REMEHA_ZONE_RESERVED_REGISTERS,
    ZoneRegisters,
)

TESTING_TIME_ZONE: Final[str] = "Europe/Amsterdam"


def json_fixture(file_name: str) -> Any:
    """Read a fixture and return it as a `JsonValueType`."""

    path = pathlib.Path(__file__).parent.resolve().joinpath(f"fixtures/{file_name}")
    with pathlib.Path.open(path) as file:
        data = file.read()

    return json.loads(data)


def get_modbus_unit(api: RemehaApi) -> MockModbusUnit:
    """Return the modbus unit from the given api.

    Raises:
        TypeError if the unit is not a `MockModbusUnit`.

    """

    unit = api._unit  # noqa: SLF001
    if not isinstance(unit, MockModbusUnit):
        msg = f"Not a MockModbusUnit: {type(unit).__qualname__}"
        raise TypeError(msg)

    return unit


def update_raw_data(api: RemehaApi, data: tuple[int, int] | list[tuple[int, int]]):
    """Update the modbus data used by the given api.

    Args:
        api (RemehaApi): The api to use.
        data (list[tuple[int, int]]): A list of register/value tuples to update.

    """

    unit = get_modbus_unit(api)
    iterable = data if isinstance(data, list) else [data]
    for register, value in iterable:
        unit.holding[register] = value


@pytest.fixture
def remeha_modbus_unit(request, mock_modbus_unit: MockModbusUnit) -> ModbusUnit:
    """Load the contents of the `request.param` json fixture into the modbus unit."""

    json_file = request.param if hasattr(request, "param") else "modbus_store.json"
    store: dict[str, str] = json_fixture(json_file)["server"]["registers"]
    mock_modbus_unit.load_raw(
        {"holding": {int(key): int(value, 16) for key, value in store.items()}}
    )

    return mock_modbus_unit


@pytest_asyncio.fixture
async def remeha_api(
    request,
    remeha_modbus_unit: MockModbusUnit,
) -> RemehaApi:
    """Create a new RemehaApi instance with a mocked modbus client."""

    # mock_modbus_client MUST be a mock, otherwise a real connection might be made and mess up the appliance.
    if not isinstance(remeha_modbus_unit, MockModbusUnit):
        pytest.fail(
            f"Trying to create RemehaApi with non-mocked modbus client type {type(remeha_modbus_unit).__qualname__}."
        )

    require_update = (
        request.param.get("require_update", True) if hasattr(request, "param") else True
    )
    name = request.param.get("name", "test_api") if hasattr(request, "param") else "test_api"
    time_zone: tzinfo | None = (
        tz.gettz(request.param.get("time_zone", TESTING_TIME_ZONE))
        if hasattr(request, "param")
        else tz.gettz(TESTING_TIME_ZONE)
    )

    api = RemehaApi(
        name=name,
        unit=remeha_modbus_unit,
        time_zone=time_zone,
    )
    if require_update:
        await api.async_update()

    return api


@pytest.fixture
def finalizer():
    """Return a list of callables that are executed after the test method finishes."""
    callables = []
    yield callables

    for fn in callables:
        fn()


@pytest.fixture
def _disabled_mock_modbus_client(request) -> Generator[AsyncMock]:
    """Create a mocked pymodbus client.

    The registers for the modbus client are retrieved from the `request` and will be
    looked up using `load_json_object_fixture`. See `fixtures/modbus_store.json` as an example.
    """

    with (
        patch("pymodbus.client.AsyncModbusTcpClient", autospec=True) as mock,
        patch(
            "pymodbus.pdu.register_message.ReadHoldingRegistersResponse", autospec=True
        ) as read_pdu,
        patch(
            "pymodbus.pdu.register_message.WriteMultipleRegistersRequest", autospec=True
        ) as write_pdu,
    ):
        json_file = request.param if hasattr(request, "param") else "modbus_store.json"
        store: Any = json_fixture(json_file)

        def get_registers(address: int, count: int) -> list[int]:
            return [
                int(store["server"]["registers"][str(r)], 16)  # type: ignore  # noqa: PGH003
                for r in range(address, address + count)
            ]

        async def get_from_store(address: int, count: int, **kwargs):
            read_pdu.side_effect = AsyncMock()
            read_pdu.isError = Mock(return_value=False)
            read_pdu.registers = get_registers(address, count)
            read_pdu.dev_id = 100

            return read_pdu

        def close():
            return Mock()

        async def write_to_store(address: int, values: list[int], **kwargs):
            for idx, r in enumerate(values):
                store["server"]["registers"][str(address + idx)] = int(r).to_bytes(2).hex()  # type: ignore  # noqa: PGH003

            write_pdu.side_effect = AsyncMock()
            write_pdu.isError = Mock(return_value=False)
            write_pdu.dev_id = 100

            return write_pdu

        async def set_pump_state(zone_id: int, state: bool = False):
            return await write_to_store(
                address=ZoneRegisters.PUMP_RUNNING.start_address
                + (REMEHA_ZONE_RESERVED_REGISTERS * (zone_id - 1)),
                values=[int(state)],
            )

        mock.connected = MagicMock(return_value=True)
        mock.read_holding_registers.side_effect = get_from_store
        mock.write_registers = write_to_store
        mock.set_zone_pump_state = set_pump_state
        mock.close = close

        yield mock
