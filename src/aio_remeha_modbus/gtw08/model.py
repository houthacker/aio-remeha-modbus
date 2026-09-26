"""Remeha-specific modbus models."""

from typing import Any, override

from modbus_connection.model import Component


class RemehaComponent(Component):
    """A Remeha subsystem."""

    @override
    async def write(self, field: str, value: Any) -> None:
        """Write a writable register or coil by attribute name.

        After a successful write, the written value is retained and returned
        when the field is read until the next call to `async_update()`.

        Raises:
          `AttributeError`: for an unknown or read-only field
          `ValueError`: if the value cannot be scaled.

        """

        await super().write(field=field, value=value)
        self._values[field] = value
