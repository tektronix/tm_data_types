"""Enumerators used to enforce typing."""

from enum import Enum
from typing import cast, List


class CustomStrEnum(Enum):
    """A custom base class for string Enums.

    This class provides better type hinting for the value property.
    """

    # pylint: disable=function-redefined,invalid-overridden-method
    @property
    def name(
        self,
    ) -> str:
        """Return the name of the Enum member."""
        return self._name_  # pylint: disable=no-member

    @property
    def value(self) -> str:  # pylint: disable=invalid-overridden-method
        """Return the value of the Enum member."""
        return cast(str, self._value_)  # pylint: disable=no-member

    @classmethod
    def list_values(cls) -> List[str]:
        """Return a list of all the values of the enum."""
        return [enum_entry.value for enum_entry in cls]


class SIBaseUnit(Enum):
    """Different SI units that can be used in a waveform."""

    SECONDS = "s"
    SAMPLES = "S"
    VOLTS = "V"
    AMPERES = "A"
    HERTZ = "Hz"
    DB = "dB"
    WATTS = "W"
    NONE = ""


class WaveformTypes(Enum):
    """What the waveform file format consists of."""

    SINGLE = 0
    FASTFRAME = 1
    MIXED = 2
    INVALID = 3


class CurveFormats(Enum):
    """What data type each value is in the curve."""

    EXPLICIT_INT16 = 0  # 2 Byte Integer
    EXPLICIT_INT32 = 1  # 4 Byte Integer
    EXPLICIT_UINT32 = 2  # 4 Byte Unsigned Integer
    EXPLICIT_UINT64 = 3  # 8 Byte Unsigned Integer
    EXPLICIT_FP32 = 4  # 4 Byte Floating Point
    EXPLICIT_FP64 = 5  # 8 Byte Floating Point
    EXPLICIT_INVALID_FORMAT = 6  # Invalid Format


class CurveFormatsVer3(Enum):
    """What data type each value is in the curve for Version 3 files."""

    EXPLICIT_INT16 = 0  # 2 Byte Integer
    EXPLICIT_INT32 = 1  # 4 Byte Integer
    EXPLICIT_UINT32 = 2  # 4 Byte Unsigned Integer
    EXPLICIT_UINT64 = 3  # 8 Byte Unsigned Integer
    EXPLICIT_FP32 = 4  # 4 Byte Floating Point
    EXPLICIT_FP64 = 5  # 8 Byte Floating Point
    EXPLICIT_UINT8 = 6  # 1 Byte Integer switched with uint8
    EXPLICIT_INT8 = 7  # 1 Byte Unsigned Integer
    EXPLICIT_INVALID_FORMAT = 8  # Invalid Format
    EXPLICIT_NO_DIMENSION = 9  # No Dimension


class StorageTypes(Enum):
    """How the curve data is formatted."""

    EXPLICIT_SAMPLE = 0
    EXPLICIT_MIN_MAX = 1
    EXPLICIT_VERT_HIST = 2
    EXPLICIT_HOR_HIST = 3
    EXPLICIT_ROW_ORDER = 4
    EXPLICIT_COLUMN_ORDER = 5
    EXPLICIT_INVALID_STORAGE = 6


class DataTypes(Enum):
    """What data type is being written to the scope."""

    SCALAR_MEAS = 0
    SCALAR_CONST = 1
    VECTOR = 2
    PIXMAP = 3
    INVALID = 4
    WFMDB = 5
    DIGITAL = 6


class DSYFormat(Enum):
    """Pixel map display format."""

    DSY_FORMAT_INVALID = 0
    DSY_FORMAT_YT = 1
    DSY_FORMAT_XY = 2
    DSY_FORMAT_XYZ = 3


class SweepTypes(Enum):
    """Type of acquisition."""

    SWEEP_ROLL = 0
    SWEEP_SAMPLE = 1
    SWEEP_ET = 2
    SWEEP_INVALID = 3


class BaseTypes(Enum):
    """What kind of base is used for acquisition."""

    BASE_TIME = 0
    BASE_SPECTRAL_MAG = 1
    BASE_SPECTRAL_PHASE = 2
    BASE_INVALID = 3


class ChecksumType(Enum):
    """How each fast frame is checksum.

    Currently not used.
    """

    NO_CHECKSUM = 0
    CTYPE_CRC16 = 1
    CTYPE_SUM16 = 2
    CTYPE_CRC32 = 3
    CTYPE_SUM32 = 4


class SummaryFrameType(Enum):
    """Available in version 3 .wfm files."""

    SUMMARY_FRAME_OFF = 0
    SUMMARY_FRAME_AVERAGE = 1
    SUMMARY_FRAME_ENVELOPE = 2


class VersionNumber(Enum):
    """The version of the .wfm file."""

    ONE = b":WFM#001"
    TWO = b":WFM#002"
    THREE = b":WFM#003"


class ByteOrderFormat(Enum):
    """The endianness of the .wfm file."""

    INTEL = b"\xf0\xf0"  # little endian
    PPC = b"\x0f\x0f"  # big endian


class WaveformDimension(CustomStrEnum):
    """The names of the two dimensions in the dimensions class."""

    FIRST = "first"  # first dimension
    SECOND = "second"  # second dimension


class IQWindowTypes(CustomStrEnum):
    """The window type used when determining the sample rate of the IQ waveform."""

    BLACKHARRIS = "BlackHarris"
    FLATTOP = "Flattop2"
    HANNING = "Hanning"
    HAMMING = "Hamming"
    RECTANGLE = "Rectangle"
    KAISERBESSEL = "Kaiserbessel"
