"""Helpers for modbus field types."""

from datetime import time
from enum import IntEnum, IntFlag
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

from aio_remeha_modbus.api.const import (
    REMEHA_TIME_PROGRAM_BYTE_SIZE,
    REMEHA_TIME_PROGRAM_SLOT_SIZE,
    ClimateZoneScheduleId,
)
from aio_remeha_modbus.api.errors import InvalidZoneSchedule
from aio_remeha_modbus.helpers.gtw08 import SteppedTimeOfDay, Timeslot


def decode_bytes(words: list[int], word_order: WordOrder = "big") -> bytes:
    """Decode a list of registers to a bytes object."""

    return b"".join(word.to_bytes(2, byteorder=word_order) for word in words)


def encode_bytes(value: bytes, word_order: WordOrder = "big") -> list[int]:
    """Encode a byte object to a list of registers."""

    return [
        int.from_bytes(bytes=value[i : i + 2], byteorder=word_order)
        for i in range(0, len(value), 2)
    ]


class BytePosition(IntEnum):
    """Describes the position of a byte within a 2-byte modbus register."""

    LOW = 0
    """The low byte within a single modbus register."""

    HIGH = 8
    """The high byte within a single modbus register."""


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
        nan_bytes: bytes = b"\xff\xff",
        word_order: WordOrder = "big",
        writable: bool | WriteValidator = False,
        stride: int = 0,
        force_fc16: bool = False,
    ) -> None:
        """Create a new NullableBinaryField.

        Args:
            address (int): The register address the field starts at.
            count (int): The amount of registers to read.
            nan_bytes (bytes): The designated nan-value for a register. Must have a length of 2.
            word_order (WordOrder): The word-order for multi-register values.
            writable (bool|WriteValidator): A `bool` or a `WriteValidator`.
            stride (int): Per-index address-step for a placed component.
            force_fc16 (bool): Always write with FC16, even a single register.

        Raises:
            ValueError: If `force_fc16` is `True`, but `writable` is `False`.
            ValueError: If `nan_bytes` is not exactly 2 bytes long.

        """

        super().__init__(
            address,
            count=count,
            word_order=word_order,
            writable=writable,
            stride=stride,
            force_fc16=force_fc16,
        )

        if len(nan_bytes) == 2:
            self._nan_bytes = nan_bytes * count
        else:
            raise ValueError(f"nan_bytes requires a length of 2, got {len(nan_bytes)}")

    @override
    def decode(self, words: list[int], scale_exponent: int | None = None) -> bytes | None:
        decoded = super().decode(words=words, scale_exponent=scale_exponent)

        if decoded == self._nan_bytes:
            return None

        return decoded

    @override
    def encode(self, value: bytes | None, scale_exponent: int | None = None) -> list[int]:
        return super().encode(
            value=self._nan_bytes if value is None else value, scale_exponent=scale_exponent
        )


class TimeStepsField(RegisterField[time]):
    """A time field that is built from bytes.

    The time is encoded as 10-minute time steps starting at midnight.
    """

    nan = 0xFF

    def __init__(self, address: int, *, writable: bool | WriteValidator = False):
        """Create a new TimeOfDaySteps instance."""

        super().__init__(address, writable=writable)

    @override
    def decode(self, words: list[int], scale_exponent: int | None = None) -> time | None:
        steps = words[0]
        if (steps & 0xFF) == TimeStepsField.nan:
            return None

        return SteppedTimeOfDay.from_steps(steps)

    @override
    def encode(self, value: time | None, scale_exponent: int | None = None) -> list[int]:
        if value is None:
            return [TimeStepsField.nan]

        return [SteppedTimeOfDay.to_steps(value)]


class TimeProgramField(RegisterField[list[Timeslot]]):
    """A field that returns decodes a time program for a single day."""

    max_element_count = int(REMEHA_TIME_PROGRAM_BYTE_SIZE / REMEHA_TIME_PROGRAM_SLOT_SIZE)
    """The maximum amount of `Timeslot` instances in a given or returned `list[Timeslot]`"""

    nan_bytes = b"".join([b"\xff"] * REMEHA_TIME_PROGRAM_BYTE_SIZE)

    def __init__(
        self,
        address: int,
        *,
        word_order: WordOrder = "big",
        writable: bool | WriteValidator = False,
        stride: int = 0,
        force_fc16: bool = False,
    ) -> None:
        """Create a new TimeProgramField."""

        super().__init__(address, count=10, writable=writable, stride=stride, force_fc16=force_fc16)
        self.word_order: WordOrder = word_order

    @override
    def decode(self, words: list[int], scale_exponent: int | None = None) -> list[Timeslot] | None:
        schedule_bytes = decode_bytes(words=words, word_order=self.word_order)

        if len(schedule_bytes) != REMEHA_TIME_PROGRAM_BYTE_SIZE:
            raise ValueError(
                f"Cannot decode time program: require {REMEHA_TIME_PROGRAM_BYTE_SIZE} bytes but got {len(schedule_bytes)}."
            )

        if schedule_bytes == TimeProgramField.nan_bytes:
            return None

        no_of_slots: int = int.from_bytes(schedule_bytes[0:1])

        def _generate_timeslots():
            for slot_index in range(
                1, no_of_slots * REMEHA_TIME_PROGRAM_SLOT_SIZE, REMEHA_TIME_PROGRAM_SLOT_SIZE
            ):
                slot_bytes: bytes = schedule_bytes[
                    slot_index : slot_index + REMEHA_TIME_PROGRAM_SLOT_SIZE
                ]

                yield Timeslot.decode(encoded_time_slot=slot_bytes)

        try:
            return [time_slot for time_slot in list(_generate_timeslots()) if time_slot is not None]
        except ValueError as ex:
            raise InvalidZoneSchedule(
                zone=0, schedule_id=ClimateZoneScheduleId.SCHEDULE_1, is_dhw=False
            ) from ex

    @override
    def encode(self, value: list[Timeslot], scale_exponent: int | None = None) -> list[int]:
        if len(value) > TimeProgramField.max_element_count:
            raise ValueError(
                f"Too many Timeslots to encode. Maximum is {TimeProgramField.max_element_count}, got {len(value)}"
            )

        time_slot_count: bytes = len(value).to_bytes()
        not_padded_slots: bytes = b"".join(
            [
                time_slot_count,
                *[t.encode() for t in value],
            ]
        )

        # Add padding null-bytes until length is REMEHA_TIME_PROGRAM_BYTE_SIZE bytes.
        schedule_bytes = b"".join(
            [
                not_padded_slots,
                *[b"\00" for _ in range(REMEHA_TIME_PROGRAM_BYTE_SIZE - len(not_padded_slots))],
            ]
        )

        return encode_bytes(schedule_bytes, word_order=self.word_order)


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
    nan_bytes: bytes = b"\xff\xff",
    word_order: WordOrder = "big",
    writable: bool | WriteValidator = False,
    stride: int = 0,
    force_fc16: bool = False,
) -> NullableBinaryField:
    """Create a nullable binary register field."""

    return NullableBinaryField(
        address,
        count=count,
        nan_bytes=nan_bytes,
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
    position: BytePosition = BytePosition.LOW,
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
    position: BytePosition | None = BytePosition.LOW,
) -> PackedBitsField | NumberField[float]:
    """Provide an 8-bit unsigned integer.

    For a non-scaled value, `position` determines which register byte to read.
    This is useful for reading registers that contain two distinct values.
    """

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

    assert position is not None
    return bits(address, start=position, width=8, writable=writable, stride=stride, unit=unit)


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
    """Create a field containing a signed 16-bits integer.

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
    """Provide an unsigned 16-bit integer field."""

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


def time_steps(address: int, *, writable: bool | WriteValidator = False) -> TimeStepsField:
    """Create a field that contains the time of day in 10-minute steps since midnight."""

    return TimeStepsField(address, writable=writable)


def time_slots(
    address: int, *, writable: bool | WriteValidator = False, stride: int = 0
) -> TimeProgramField:
    """Create a field that represents a time program."""

    return TimeProgramField(address=address, writable=writable, stride=stride)
