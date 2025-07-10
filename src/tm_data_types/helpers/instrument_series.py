"""A file which provides a series of instruments and values that are unique to them."""

# TODO: add docstrings to all classes, and enum members

from enum import Enum
from typing import Literal, NamedTuple

from tm_data_types.helpers.enums import ByteOrderFormat, VersionNumber


class InstrumentSeriesDataStyle(NamedTuple):
    """A class representing the data style of a specific instrument series."""

    byte_order: ByteOrderFormat
    version: VersionNumber
    slot_ids: int
    gen_purpose_default: int


class Endian(NamedTuple):
    """A class representing the endian-ness and format of data."""

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

    MSO54 = TEKSCOPE  # noqa: PIE796s
