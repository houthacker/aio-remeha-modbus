"""Helpers for modbus field types."""

from enum import IntFlag
from typing import overload, override

from modbus_connection import WordOrder
from modbus_connection.model import (
    NumberField,
    PackedBitsField,
    RegisterField,
    WriteValidator,
    bits,
    gauge,
    integer,
)


def decode_bytes(words: list[int], word_order: WordOrder = "big") -> bytes:
    """Decode a list of registers to a bytes object."""

    return b"".join(word.to_bytes(2, byteorder=word_order) for word in words)


def encode_bytes(value: bytes, word_order: WordOrder = "big") -> list[int]:
    """Encode a byte object to a list of registers."""

    return [
        int.from_bytes(bytes=value[i : i + 2], byteorder=word_order)
        for i in range(0, len(value), 2)
    ]


class BinaryField(RegisterField[bytes]):
    """A field that spans multiple registers and maps them to a bytes object."""

    def __init__(
        self,
        address: int,
        *,
        count: int = 1,
        word_order: WordOrder = "big",
        writable: bool | WriteValidator = False,
        stride: int = 0,
        force_fc16: bool = False,
    ) -> None:
        """Create a new BinaryField."""

        super().__init__(
            address, count=count, writable=writable, stride=stride, force_fc16=force_fc16
        )
        self.word_order: WordOrder = word_order

    @override
    def decode(self, words: list[int], scale_exponent: int | None = None) -> bytes:
        return decode_bytes(words=words, word_order=self.word_order)

    @override
    def encode(self, value: bytes, scale_exponent: int | None = None) -> list[int]:
        return encode_bytes(value=value, word_order=self.word_order)


class NullableBinaryField(BinaryField):
    """A binary field that can handle null-values."""

    def __init__(
        self,
        address: int,
        *,
        count: int = 1,
        null_byte: int = 0xFF00,
        word_order: WordOrder = "big",
        writable: bool | WriteValidator = False,
        stride: int = 0,
        force_fc16: bool = False,
    ) -> None:
        """Create a new NullableBinaryField."""

        super().__init__(
            address,
            count=count,
            word_order=word_order,
            writable=writable,
            stride=stride,
            force_fc16=force_fc16,
        )

        self._null_bytes = decode_bytes([null_byte] * count)

    @override
    def decode(self, words: list[int], scale_exponent: int | None = None) -> bytes | None:
        decoded = super().decode(words=words, scale_exponent=scale_exponent)

        if decoded == self._null_bytes:
            return None

        return decoded

    @override
    def encode(self, value: bytes | None, scale_exponent: int | None = None) -> list[int]:
        return super().encode(
            value=self._null_bytes if value is None else value, scale_exponent=scale_exponent
        )


def binary(
    address: int,
    *,
    count: int = 1,
    word_order: WordOrder = "big",
    writable: bool | WriteValidator = False,
    stride: int = 0,
    force_fc16: bool = False,
) -> BinaryField:
    """Create a binary register field."""

    return BinaryField(
        address,
        count=count,
        word_order=word_order,
        writable=writable,
        stride=stride,
        force_fc16=force_fc16,
    )


def nullable_binary(
    address: int,
    *,
    count: int = 1,
    null_byte: int = 0xFF00,
    word_order: WordOrder = "big",
    writable: bool | WriteValidator = False,
    stride: int = 0,
    force_fc16: bool = False,
) -> NullableBinaryField:
    """Create a nullable binary register field."""

    return NullableBinaryField(
        address,
        count=count,
        null_byte=null_byte,
        word_order=word_order,
        writable=writable,
        stride=stride,
        force_fc16=force_fc16,
    )


@overload
def uint8(
    address: int,
    *,
    stride: int = 0,
    writable: bool | WriteValidator = False,
    unit: str | None = None,
) -> PackedBitsField: ...


@overload
def uint8(
    address: int,
    *,
    scale: float,
    stride: int = 0,
    writable: bool | WriteValidator = False,
    unit: str | None = None,
) -> NumberField[float]: ...


def uint8(
    address: int,
    *,
    scale: float | None = None,
    stride: int = 0,
    writable: bool | WriteValidator = False,
    unit: str | None = None,
) -> PackedBitsField | NumberField[float]:
    """Provide an 8-bit unsigned integer."""

    if scale is not None:
        return gauge(
            address=address,
            scale=scale,
            signed=False,
            nan=0xFF,
            stride=stride,
            writable=writable,
            unit=unit,
        )

    return bits(address, start=0, width=8, writable=writable, stride=stride, unit=unit)


def bits8[F: IntFlag](
    address: int, flags: type[F] | None = None, writable: bool | WriteValidator = False
) -> NumberField[F]:
    """Create an 8-bit bitfield point."""

    return NumberField(address, count=1, signed=False, nan=0xFF, convert=flags, writable=writable)


@overload
def int16(
    address: int,
    *,
    scale: float,
    stride: int = 0,
    writable: bool | WriteValidator = False,
    unit: str | None = None,
    force_fc16: bool = False,
) -> NumberField[float]: ...


@overload
def int16(
    address: int,
    *,
    stride: int = 0,
    writable: bool | WriteValidator = False,
    unit: str | None = None,
    force_fc16: bool = False,
) -> NumberField[int]: ...


def int16(
    address: int,
    *,
    scale: float | None = None,
    stride: int = 0,
    writable: bool | WriteValidator = False,
    unit: str | None = None,
    force_fc16: bool = False,
) -> NumberField[int | float]:
    """Return a field containing a signed 16-bits integer.

    If `scale` is provided, a `gauge` is returned, otherwise an `integer`.
    """

    if scale is None:
        return integer(
            address,
            nan=0x8000,
            stride=stride,
            writable=writable,
            unit=unit,
            force_fc16=force_fc16,
        )

    return gauge(
        address,
        scale,
        nan=0x8000,
        stride=stride,
        writable=writable,
        unit=unit,
        force_fc16=force_fc16,
    )


@overload
def uint16(
    address: int,
    *,
    scale: float,
    stride: int = 0,
    writable: bool | WriteValidator = False,
    unit: str | None = None,
    force_fc16: bool = False,
) -> NumberField[float]: ...


@overload
def uint16(
    address: int,
    *,
    stride: int = 0,
    writable: bool | WriteValidator = False,
    unit: str | None = None,
    force_fc16: bool = False,
) -> NumberField[int]: ...


def uint16(
    address: int,
    *,
    scale: float | None = None,
    stride: int = 0,
    writable: bool | WriteValidator = False,
    unit: str | None = None,
    force_fc16: bool = False,
) -> NumberField[int | float]:
    """Abc."""

    if scale is None:
        return integer(
            address,
            signed=False,
            nan=0xFFFF,
            stride=stride,
            writable=writable,
            unit=unit,
            force_fc16=force_fc16,
        )

    return gauge(
        address,
        scale,
        signed=False,
        nan=0xFFFF,
        stride=stride,
        writable=writable,
        unit=unit,
        force_fc16=force_fc16,
    )
