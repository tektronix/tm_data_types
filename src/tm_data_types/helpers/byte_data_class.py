"""Data types for different classes that need to be saved as byte values."""

import struct

from typing import Any, Dict, List, Optional, TextIO, Type, TypeVar, Union

from pydantic import model_validator
from pydantic.dataclasses import dataclass as pydantic_dataclass

T = TypeVar("T")


def convert_to_type(field_type: Any, value_to_convert: Any) -> Any:  # noqa:PLR0911,C901
    """Convert a value to a type.

    Args:
        field_type: The type to convert to.
        value_to_convert: The value to convert.

    Returns:
        The converted value.
    """
    origin = getattr(field_type, "__origin__", None)
    # Handle Union/Optional types
    if origin is Union:
        for arg in field_type.__args__:
            # NoneType
            if (arg is None) and value_to_convert is None:
                return None
            # Accept if already correct type (handle generics)
            if (arg_origin := getattr(arg, "__origin__", None)) is not None:
                if isinstance(value_to_convert, arg_origin):
                    return value_to_convert
            elif isinstance(value_to_convert, arg):
                return value_to_convert
            try:
                return convert_to_type(arg, value_to_convert)
            except Exception:  # noqa:BLE001,S112
                continue
        msg = f"Type {type(value_to_convert)} cannot be converted to type {field_type}."
        raise TypeError(msg)
    # Accept if already correct type (handle generics)
    if origin is not None:
        if isinstance(value_to_convert, origin):
            return value_to_convert
    elif isinstance(value_to_convert, field_type):
        return value_to_convert
    # Special case for bytes to str
    # Handle str to bytes conversion with encoding
    if isinstance(value_to_convert, str) and field_type is bytes:
        if value_to_convert == "":
            return b""  # Empty string becomes empty bytes
        return value_to_convert.encode("utf-8", errors="ignore")
    return field_type(value_to_convert)


@pydantic_dataclass(frozen=False)
class EnforcedTypeDataClass:
    """A class which force type casts the field annotations, including child class variables."""

    ################################################################################################
    # Public Methods
    ################################################################################################

    # pylint: disable=too-few-public-methods
    @model_validator(mode="before")
    def validate(cls, values: Any) -> Dict[str, Any]:  # pylint: disable=no-self-argument  # noqa: N805
        # pylint: disable=no-member
        """Pre-init enforced type cast."""
        new_values = {}
        # iterate through the parent objects
        for base in cls.__mro__:  # pyright: ignore [reportAttributeAccessIssue]
            # if the class is self, exit the iteration
            if base is EnforcedTypeDataClass:
                break
            # if there is no class variables in the child
            try:
                _ = base.__annotations__
            except AttributeError:
                continue

            for field_name, field_type in base.__annotations__.items():
                # find the value to convert
                try:
                    value_to_convert = values.kwargs[field_name]
                except (KeyError, TypeError) as e:
                    # if pre-defined as a "no_default" value, error if not provided
                    if (value_to_convert := getattr(base, field_name)) == "no_default":
                        msg = f"__init__ missing 1 required argument: {field_name}"
                        raise TypeError(
                            msg,
                        ) from e
                # type cast the vlue
                new_values[field_name] = convert_to_type(field_type, value_to_convert)
        return new_values


class StructuredInfo(EnforcedTypeDataClass):
    """A class which contains information structured to be read from or written to."""

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __len__(self) -> int:
        """Sum the number of bytes for all annotations in this dataclass."""
        total_length = 0
        for value in self.__annotations__.values():
            total_length += value.length
        return total_length

    ################################################################################################
    # Public Methods
    ################################################################################################

    # Reading
    @classmethod
    def unpack(
        cls: Type[T],
        endian: str,
        filestream: TextIO,
        in_order: bool,
        order: Optional[List[str]] = None,
    ) -> T:
        """Read a file and unpack its contents into a specific datum format.

        Args:
            endian: The order in which the bytes should be read.
            filestream: The file buffer that is being read from.
            in_order: If the contents should be unpacked in definition order or provided order.
            order: The order in which to unpack the contents.
        """
        length = 0
        struct_repr_str = ""
        if not in_order and not order:
            msg = "Requested custom order unpacking, but order not provided"
            raise IndexError(msg)

        if not in_order and order:  # noqa: SIM108
            unpacking_order = order
        else:
            # this only works because dictionaries preserve order
            unpacking_order = cls.__annotations__.keys()

        for key in unpacking_order:
            if key in cls.__annotations__:
                field = cls.__annotations__[key]
                struct_repr_str += field.struct_repr
                length += field.length
        info = struct.unpack(endian + struct_repr_str, filestream.read(length))
        output_list = {key: value for value, key in zip(info, unpacking_order, strict=False)}
        return cls(**output_list)

    # Writing
    def pack(
        self,
        endian: str,
        filestream: TextIO,
        in_order: bool = True,
        order: Optional[List[str]] = None,
    ) -> None:
        """Pack the wfm format into a byte sequence then write it to a file.

        Args:
            endian: The order in which the byte sequence should be written.
            filestream: The file buffer that is being written to.
            in_order: If the contents should be unpacked in definition order or provided order.
            order: The order in which to unpack the contents.
        """
        struct_repr_str = ""
        if not in_order and not order:
            msg = "Requested custom order unpacking, but order not provided"
            raise IndexError(msg)

        if not in_order and order:  # noqa: SIM108
            packing = order
        else:
            # this only works because dictionaries preserve order
            packing = self.__annotations__.keys()

        value = []

        for key in packing:
            if key in self.__annotations__:
                attribute_value = getattr(self, key)
                value.append(attribute_value)
                struct_repr_str += attribute_value.struct_repr
        filestream.write(struct.pack(endian + struct_repr_str, *value))

    # Writing
    def get_value_summation(self) -> int:
        """Sum each byte for all annotations in this dataclass."""
        total_summation = 0
        for key in self.__annotations__:
            value = getattr(self, key)
            total_summation += value.get_value_summation()
        return total_summation

    # Writing
    @classmethod
    def get_cls_length(cls) -> int:
        """Sum the number of bytes for all annotations in this dataclass."""
        total_length = 0
        for field in cls.__annotations__.values():
            total_length += field.length
        return total_length
