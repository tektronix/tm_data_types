"""A file which provides a series of instruments and values that are unique to them."""

# TODO: add docstrings to all classes, and enum members

from enum import Enum
from typing import Literal, NamedTuple

from tm_data_types.helpers.enums import ByteOrderFormat, VersionNumber


class InstrumentSeriesDataStyle(NamedTuple):
    byte_order: ByteOrderFormat
    version: VersionNumber
    slot_ids: int
    gen_purpose_default: int


class Endian(NamedTuple):
    struct: str
    from_byte: Literal["little", "big"]
    format: bytes


class InstrumentSeries(Enum):
    """Which instrument series is being written to or read from."""

    TEKSCOPE = InstrumentSeriesDataStyle(
        byte_order=ByteOrderFormat.PPC,
        version=VersionNumber.THREE,
        slot_ids=5,
        gen_purpose_default=0,
    )
    MSO64 = TEKSCOPE
    MSO64B = TEKSCOPE  # noqa: PIE796
    MSO54 = TEKSCOPE  # noqa: PIE796
    MSO54B = TEKSCOPE  # noqa: PIE796
    MSO44 = TEKSCOPE  # noqa: PIE796
    MSO44B = TEKSCOPE  # noqa: PIE796
    MSO24 = TEKSCOPE  # noqa: PIE796
