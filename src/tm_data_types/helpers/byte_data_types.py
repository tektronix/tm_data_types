"""Byte."""

import struct

from abc import ABC
from typing import Any, Optional, TextIO

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema, CoreSchema


class ByteData(ABC):  # noqa: B024
    """Class which handles the packing and unpacking of individual datum."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    tek_meta: Optional[int] = None  # the tek metadata representation for the datum
    struct_repr: str = ""  # the struct unpack representation for the datum
    np_repr: str = ""  # the numpy unpack representation for the datum
    length: int = 0  # the byte length of the datum

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __len__(self) -> int:
        """Get the length of the datum."""
        return self.get_cls_length()

    ################################################################################################
    # Public Methods
    ################################################################################################

    def get_value_summation(self) -> int:
        """Sum the byte values of the datum."""
        # convert to byte
        representation = struct.pack(self.struct_repr, self)
        # sum
        return sum(representation)

    def pack(self, endian: str, filestream: TextIO) -> None:
        """Pack the current value of the datum into the specified file.

        Args:
            endian: The Endianness of the waveform format.
            filestream: The filestream that will be written to.
        """
        filestream.write(struct.pack(endian + self.struct_repr, self))

    @classmethod
    def unpack(cls, endian: str, filestream: TextIO) -> "ByteData":
        """Unpack a number of bytes based on the datum's length.

        Args:
            endian: The Endianness of the waveform format.
            filestream: The filestream that will be read from.
        """
        (info,) = struct.unpack(endian + cls.struct_repr, filestream.read(cls.length))
        return cls(info)

    @classmethod
    def get_cls_length(cls) -> int:
        """Get the length of the datum, reflects the StructuredInfo class."""
        return cls.length


class String(ByteData, bytes):
    """A byte string which can be used in pydantic."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    tek_meta: Optional[int] = 1
    length: int = 1
    struct_repr: str = "1s"
    np_repr: str = "S1"

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    # pylint: disable=unused-argument
    @classmethod
    def __get_pydantic_core_schema__(  # pylint: disable=bad-dunder-name
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Get the core schema for the class."""
        return core_schema.no_info_after_validator_function(cls, handler(bytes))

    def __new__(cls, x: Any) -> bytes:
        """When a new class is created, fill the datum with null determinations based on the length.

        Args:
            x: The value of the datum.
        """
        if isinstance(x, int):
            x = x.to_bytes(length=cls.length, byteorder="big").zfill(cls.length)
        elif isinstance(x, str):
            x = str.encode(x.ljust(cls.length, "\x00"))
        else:
            pass
        return bytes.__new__(cls, x)

    def __str__(self) -> str:
        """Remove the null terminations and return it."""
        return self.decode("utf_8").rstrip("\x00")

    ################################################################################################
    # Public Methods
    ################################################################################################

    def get_value_summation(self) -> int:
        """Sum the byte values of the datum."""
        return sum(self)


class String2(String):
    """A string with a length of 2."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    struct_repr: str = "2s"
    np_repr: str = "S2"
    length: int = 2


class String8(String):
    """A string with a length of 8."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    struct_repr: str = "8s"
    np_repr: str = "S8"
    length: int = 8


class String20(String):
    """A string with a length of 20."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    struct_repr: str = "20s"
    np_repr: str = "S20"
    length: int = 20


class String32(String):
    """A string with a length of 32."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    struct_repr: str = "32s"
    np_repr: str = "S32"
    length: int = 32


class Char(String):
    """Single byte of information."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    struct_repr: str = "c"
    np_repr: str = "i1"
    length: int = 1


class SignedChar(int, ByteData):
    """Single byte of a signed numeric value."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    struct_repr: str = "b"
    np_repr: str = "i1"
    length: int = 1

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    # pylint: disable=unused-argument
    @classmethod
    def __get_pydantic_core_schema__(  # pylint: disable=bad-dunder-name
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Get the core schema for the class."""
        return core_schema.no_info_after_validator_function(cls, handler(int))


class UnsignedChar(SignedChar):
    """Single byte of an unsigned numeric value."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    struct_repr: str = "B"
    np_repr: str = "u1"
    length: int = 1


class Short(SignedChar):
    """Two bytes of a signed numeric value."""

    struct_repr: str = "h"
    np_repr: str = "i2"
    length: int = 2


class UnsignedShort(SignedChar):
    """Two bytes of an unsigned numeric value."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    struct_repr: str = "H"
    np_repr: str = "u2"
    length: int = 2


class Int(SignedChar):
    """Four bytes of a signed numeric value."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    tek_meta: Optional[int] = 2
    struct_repr: str = "i"
    np_repr: str = "i4"
    length: int = 4


class UnsignedInt(SignedChar):
    """Four bytes of an unsigned numeric value."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    tek_meta: Optional[int] = 4
    struct_repr: str = "I"
    np_repr: str = "u4"
    length: int = 4


class Long(SignedChar):
    """Four bytes of a signed numeric value.

    The same as Int in this case.
    """

    tek_meta: Optional[int] = 2
    struct_repr: str = "l"
    np_repr: str = "i4"
    length: int = 4


class UnsignedLong(SignedChar):
    """Four bytes of an unsigned numeric value.

    The same as UnsignedInt in this case.
    """

    tek_meta: Optional[int] = 4
    struct_repr: str = "L"
    np_repr: str = "u4"
    length: int = 4


class LongLong(SignedChar):
    """Eight bytes of a signed numeric value."""

    struct_repr: str = "q"
    np_repr: str = "i8"
    length: int = 8


class UnsignedLongLong(SignedChar):
    """Eight bytes of an unsigned numeric value."""

    struct_repr: str = "Q"
    np_repr: str = "u8"
    length: int = 8


class Float(ByteData, float):
    """Four bytes of a signed floating point value."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    struct_repr: str = "f"
    np_repr: str = "f4"
    length: int = 4

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    # pylint: disable=unused-argument, disable=bad-dunder-name
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Get the core schema for the class."""
        return core_schema.no_info_after_validator_function(cls, handler(float))


class Double(Float):
    """Eight bytes of a signed floating point value."""

    tek_meta: Optional[int] = 3
    struct_repr: str = "d"
    np_repr: str = "f8"
    length: int = 8
