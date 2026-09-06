"""Modbus helper functions."""

from collections.abc import Iterable
from enum import IntFlag

from modbus_connection.model import NumberField, PackedBitsField, WriteValidator, bits, integer


def uint8(
    address: int,
    *,
    stride: int = 0,
    writable: bool | WriteValidator = False,
    unit: str | None = None,
) -> PackedBitsField:
    """Provide an 8-bit unsigned integer."""

    return bits(address, start=0, width=8, writable=writable, stride=stride, unit=unit)


def uint16(
    address: int,
    *,
    nan: int | Iterable[int] | None = None,
    stride: int = 0,
    writable: bool | WriteValidator = False,
    unit: str | None = None,
    force_fc16: bool = False,
) -> NumberField[int]:
    """Abc."""

    return integer(
        address,
        signed=False,
        nan=nan,
        stride=stride,
        writable=writable,
        unit=unit,
        force_fc16=force_fc16,
    )


def bits8[F: (IntFlag)](
    address: int, flags: type[F] | None = None, writable: bool | WriteValidator = False
) -> NumberField[F]:
    """Create an 8-bit bitfield point."""

    return NumberField(address, count=1, signed=False, nan=0xFF, convert=flags, writable=writable)
