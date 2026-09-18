"""Tests for the modbus helpers."""

import pytest
from modbus_connection.exceptions import IllegalDataValueError, IllegalFunctionError

from aio_remeha_modbus.helpers.modbus import retry_on_transient


@pytest.mark.asyncio
async def test_async_retry():
    """Test that async_retry retries function execution for the right kind of exceptions."""

    # 1 retry (2 attempts)
    attempts: dict[str, int] = {"test_retries": 0, "test_raises": 0}

    @retry_on_transient(2)
    async def test_retries() -> int:
        try:
            if attempts["test_retries"] == 0:
                raise IllegalDataValueError(exception_code=0x03)

            return 42
        finally:
            attempts["test_retries"] = attempts["test_retries"] + 1

    # IllegalDataValueError is in TransientModbusError so must be retried.
    assert await test_retries() == 42
    assert attempts["test_retries"] == 2

    @retry_on_transient(2)
    async def test_raises() -> int:
        try:
            if attempts["test_raises"] == 0:
                raise IllegalFunctionError(exception_code=0x03)

            return 42
        finally:
            attempts["test_raises"] = attempts["test_raises"] + 1

    # IllegalFunctionError is not in TransientModbusError so must not be retried.
    with pytest.raises(
        expected_exception=IllegalFunctionError, match="Device returned Modbus exception code 3"
    ):
        await test_raises()

    assert attempts["test_raises"] == 1
