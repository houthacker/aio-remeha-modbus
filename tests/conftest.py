"""Fixtures for testing."""

import json
import pathlib
from collections.abc import Generator
from datetime import tzinfo
from typing import Any, Final
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from dateutil import tz
from pymodbus.client import ModbusBaseClient

from aio_remeha_modbus.api.api import ConnectionType, RemehaApi
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


def get_api(
    mock_modbus_client: ModbusBaseClient,
    name: str = "test_api",
    device_address: int = 100,
    time_zone: tzinfo | None = tz.gettz(TESTING_TIME_ZONE),
) -> RemehaApi:
    """Create a new RemehaApi instance with a mocked modbus client."""

    # mock_modbus_client MUST be a mock, otherwise a real connection might be made and mess up the appliance.
    if not isinstance(mock_modbus_client, Mock):
        pytest.fail(
            f"Trying to create RemehaApi with non-mocked modbus client type {type(mock_modbus_client).__qualname__}."
        )

    return RemehaApi(
        name=name,
        connection_type=ConnectionType.RTU_OVER_TCP,
        client=mock_modbus_client,
        device_address=device_address,
        time_zone=time_zone,
    )


@pytest.fixture
def finalizer():
    """Return a list of callables that are executed after the test method finishes."""
    callables = []
    yield callables

    for fn in callables:
        fn()


@pytest.fixture
def mock_modbus_client(request) -> Generator[AsyncMock]:
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
