"""A file which provides a series of instruments and values that are unique to them."""

from enum import Enum
from typing import NamedTuple, Literal

from tm_data_types.helpers.enums import ByteOrderFormat, VersionNumber

InstrumentSeriesDataStyle = NamedTuple(
    "InstrumentSeriesDataStyle",
    [
        ("byte_order", ByteOrderFormat),
        ("version", VersionNumber),
        ("slot_ids", int),
        ("gen_purpose_default", int),
    ],
)

Endian = NamedTuple(
    "Endian",
    [("struct", str), ("from_byte", Literal["little", "big"]), ("format", bytes)],
)


class InstrumentSeries(Enum):
    """Which instrument series is being written to or read from."""

    TEKSCOPE = InstrumentSeriesDataStyle(
        byte_order=ByteOrderFormat.PPC,
        version=VersionNumber.THREE,
        slot_ids=5,
        gen_purpose_default=0,
    )
    MSO64 = TEKSCOPE
    MSO64B = TEKSCOPE
    MSO54 = TEKSCOPE
    MSO54B = TEKSCOPE
    MSO44 = TEKSCOPE
    MSO44B = TEKSCOPE
    MSO24 = TEKSCOPE
