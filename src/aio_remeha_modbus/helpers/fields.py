"""Helpers for modbus field types."""

from typing import override

from modbus_connection import WordOrder
from modbus_connection.model import RegisterField, WriteValidator


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
