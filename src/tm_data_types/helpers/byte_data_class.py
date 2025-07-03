"""Data types for different classes that need to be saved as byte values."""

import struct

from typing import Any, Dict, get_args, List, Optional, TextIO, Type, TypeVar

from pydantic import model_validator
from pydantic.dataclasses import dataclass as pydantic_dataclass

T = TypeVar("T")


def convert_to_type(field_type: T, value_to_convert: Any) -> Optional[T]:
    """Convert the value provided to the first instance of a usable typecast recursively.

    Example:
        "6" will be converted to 6 if the field annotation is Optional[int].

    Args:
        field_type: The type annotation being checked for this conversion.
        value_to_convert: The value to type cast as a new type.

    Returns:
        The field type if it is usable for a type conversion.
    """
    error = TypeError(f"Type {type(value_to_convert)} cannot be converted to type {field_type}.")
    try:
        if isinstance(value_to_convert, bytes):
            # try to convert the type
            string_to_convert = ""
            for character in value_to_convert:
                if chr(character).isalpha():
                    string_to_convert += chr(character)
                else:
                    break
            converted_value = string_to_convert
        else:
            converted_value = field_type(value_to_convert)  # pyright: ignore [reportCallIssue]
        # no error means we are able to do it
        return converted_value  # noqa: TRY300
    except TypeError:
        # type error means failed type conversion
        # we can't convert None, field type is needs to be used here as we can't isinstance None
        if value_to_convert is None and field_type is type(None):
            return None
        # if it's Optional or Union, we can get args from it
        for recursed_type in get_args(field_type):
            try:
                # recurse
                convert_to_type(recursed_type, value_to_convert)
                if value_to_convert is None:
                    # we can't convert None
                    return None
                # return what the type that was returned
                return recursed_type(value_to_convert)
            except TypeError:  # noqa: PERF203
                pass
    except ValueError as e:
        raise error from e
    raise error


@pydantic_dataclass(frozen=False)
class EnforcedTypeDataClass:
    """A class which force type casts the field annotations, including child class variables."""

    ################################################################################################
    # Public Methods
    ################################################################################################

    # pylint: disable=too-few-public-methods
    @model_validator(mode="before")
    def validate(cls, values) -> Dict[str, Any]:  # pylint: disable=no-self-argument  # noqa: N805
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
                        raise TypeError(
                            f"__init__ missing 1 required argument: {field_name}",
                        ) from e
                # type cast the vlue
                new_values[field_name] = convert_to_type(field_type, value_to_convert)
        return new_values


class StructuredInfo(EnforcedTypeDataClass):
    """A class which contains information structured to be read from or written to."""

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __len__(self):
        """Sum the number of bytes for all annotations in this dataclass."""
        total_length = 0
        for value in self.__annotations__.values():  # pylint: disable=no-member
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
            raise IndexError("Requested custom order unpacking, but order not provided")

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
        output_list = {key: value for value, key in zip(info, unpacking_order)}
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
        # pylint: disable=no-member
        struct_repr_str = ""
        if not in_order and not order:
            raise IndexError("Requested custom order unpacking, but order not provided")

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
    def get_value_summation(self):
        """Sum each byte for all annotations in this dataclass."""
        total_summation = 0
        for key in self.__annotations__:  # pylint: disable=no-member
            value = getattr(self, key)
            total_summation += value.get_value_summation()
        return total_summation

    # Writing
    @classmethod
    def get_cls_length(cls):
        """Sum the number of bytes for all annotations in this dataclass."""
        total_length = 0
        for field in cls.__annotations__.values():
            total_length += field.length
        return total_length
