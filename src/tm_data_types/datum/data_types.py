"""The different formats which are wrapped by a MeasuredData class."""

from abc import abstractmethod
from decimal import Decimal
from typing import Any, List, Optional, Type, Union

import numpy as np

from numpy.typing import NDArray
from typing_extensions import Self

from tm_data_types.helpers.byte_data_types import ByteData, Double

PossibleTypes = np.integer[Any] | np.floating[Any]


def _check_type(
    as_type: Optional[Type[ByteData] | PossibleTypes | Type[PossibleTypes]],
    measured_data: Optional[
        Union[NDArray[PossibleTypes], "MeasuredData", List[float | int]]
    ] = None,
) -> PossibleTypes:
    """Convert types to np dtype, or grab the measured data dtype.

    Args:
        measured_data: Information provided through measurement of a device.
        as_type: The dtype/bytetype to convert the measured data to.

    Returns:
        The np dtype.
    """
    # convert to the provided type, or it's an ndarray use the previous dtype
    if isinstance(as_type, np.dtype):
        dtype = as_type
    elif (as_type and np.issubdtype(as_type, np.floating)) or np.issubdtype(as_type, np.integer):
        dtype = np.dtype(as_type)
    elif as_type is None and MeasuredData and isinstance(measured_data, np.ndarray):
        dtype = measured_data.dtype

    elif as_type is not None and isinstance(ByteData, type(as_type)) and as_type.np_repr:  # pyright: ignore [reportAttributeAccessIssue]
        dtype = np.dtype(as_type.np_repr)  # pyright: ignore [reportAttributeAccessIssue]
    else:
        msg = "No type can be gotten from the passed parameters."
        raise TypeError(msg)
    return dtype


def type_ratio(dtype_from: PossibleTypes, dtype_to: PossibleTypes) -> float:
    """Calculate the ratio of ranges between two separate types.

    Example:
        Converting from np.int16 to np.int8 will give you a ratio of 1/256.

    Args:
        dtype_from: The current dtype that is being converted.
        dtype_to: The dtype that is being converted to.

    Returns:
        The ratio between the two dtypes.
    """
    old_dtype_range = Decimal(type_max(dtype_from)) - Decimal(type_min(dtype_from))
    new_dtype_range = Decimal(type_max(dtype_to)) - Decimal(type_min(dtype_to))
    return float(new_dtype_range / old_dtype_range)


def type_max(
    data_format: Type[ByteData] | PossibleTypes | Type[PossibleTypes],
) -> float | int:
    """Get the maximum extent of a dtype.

    Args:
        data_format: The dtype to get the maximum extent of.

    Returns:
        The maximum extent of the type.
    """
    dtype = _check_type(data_format)
    if issubclass(dtype.type, np.integer):
        return int(np.iinfo(dtype).max)
    if issubclass(dtype.type, np.floating):
        return float(np.finfo(dtype).max)
    msg = "Invalid type for maximum possible value."
    raise TypeError(msg)


def type_min(
    data_format: Type[ByteData] | PossibleTypes | Type[PossibleTypes],
) -> float | int:
    """Get the minimum extent of a dtype.

    Args:
        data_format: The dtype to get the minimum extent of.
    """
    dtype = _check_type(data_format)
    if issubclass(dtype.type, np.integer):
        return int(np.iinfo(dtype).min)
    if issubclass(dtype.type, np.floating):
        return float(np.finfo(dtype).min)
    msg = "Invalid type for minimum possible value."
    raise TypeError(msg)


class MeasuredData(np.ndarray):
    """A wrapper class for np.ndarray which provides more functionality towards type conversion."""

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __new__(
        cls,
        measured_data: Union["MeasuredData", NDArray[PossibleTypes], List[int | float]],
        as_type: Optional[Type[ByteData] | PossibleTypes | Type[PossibleTypes]] = None,
    ) -> Self:
        """When a new instance of MeasuredData is created, retype it.

        Args:
            measured_data: Information provided through measurement of a device.
            as_type: The dtype/bytetype to convert the measured data to.

        Returns:
            The current new instance of MeasuredData.
        """
        # if the provided data is a list but no conversion type is provided, error out
        if isinstance(measured_data, List) and as_type is None:
            msg = "No type specified for data."
            raise TypeError(msg)

        dtype = _check_type(as_type, measured_data)

        # if the previous type is a MeasuredData, retype it to whatever the current class is
        if isinstance(measured_data, MeasuredData):
            our_type_array = cls._convert_data_to_type(measured_data, dtype=dtype)
            return super().__new__(
                cls,
                buffer=our_type_array,
                shape=our_type_array.shape,
                dtype=our_type_array.dtype,
            )
        # otherwise assume that the type is correct and use that without conversion
        if isinstance(measured_data, List):
            shape = len(measured_data)
            measured_data = np.array(measured_data, dtype=dtype)
        else:
            shape = measured_data.shape
        # needs astype, __new__ does some strange things converting from float64 to float32
        return super().__new__(cls, buffer=measured_data.astype(dtype), shape=shape, dtype=dtype)

    ################################################################################################
    # Public Methods
    ################################################################################################
    def append(
        self,
        new_measured_data: Union["MeasuredData", NDArray[PossibleTypes]],
    ) -> "MeasuredData":
        """Append new values to the waveform which are automatically type converted.

        Args:
            new_measured_data: The data that should be appended.
        """
        if isinstance(new_measured_data, np.ndarray):
            new_measured_data = RawSample(new_measured_data)
        return type(self)(
            np.append(self, self._convert_data_to_type(new_measured_data, dtype=self.dtype)),
        )

    @abstractmethod
    def calculate_offset(self, known_offset: float = 0.0) -> float:
        """Calculate what the absolute offset is based on the current data and known offset.

        Args:
            known_offset: The known offset of the waveform.

        Returns:
            The calculated offset.
        """
        raise NotImplementedError

    @abstractmethod
    def calculate_spacing(self) -> float:
        """Calculate the spacing based on information contained within the data.

        Returns:
            The calculated spacing.
        """
        raise NotImplementedError

    ################################################################################################
    # Private Methods
    ################################################################################################

    @classmethod
    def _convert_data_to_type(
        cls,
        measured_data: "MeasuredData",
        dtype: PossibleTypes,
    ) -> NDArray[PossibleTypes]:
        """Convert the passed data to the numpy dtype specified.

        Args:
            measured_data: Information provided through measurement of a device.
            dtype: The numpy dtype to convert to.
        """
        previous_data_type = type(measured_data)
        np_measured_data = np.asarray(measured_data)

        if not issubclass(previous_data_type, cls) or measured_data.dtype != dtype:
            raw_sample_data = previous_data_type._this_format_to_raw_sample_format(  # noqa: SLF001
                np_measured_data,
                dtype,
            )

            return cls._raw_sample_format_to_this_format(raw_sample_data)

        return np_measured_data

    @classmethod
    @abstractmethod
    def _this_format_to_raw_sample_format(
        cls,
        measured_data: NDArray[PossibleTypes],
        dtype: PossibleTypes,
    ) -> NDArray[PossibleTypes]:
        """Abstracted method that converts whatever the current type is to FeatureScaled.

        Args:
            measured_data: Information provided through measurement of a device.
            dtype: The dtype to convert to.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _raw_sample_format_to_this_format(
        cls,
        raw_sample_data: NDArray[PossibleTypes],
    ) -> NDArray[PossibleTypes]:
        """Abstracted method that converts whatever the current type is to a provided dtype.

        Args:
            raw_sample_data: Data that has been feature scaled.
        """
        raise NotImplementedError


class RawSample(MeasuredData):
    """The raw digitized sample values that have been measured."""

    ################################################################################################
    # Public Methods
    ################################################################################################

    def calculate_offset(self, known_offset: float = 0.0) -> float:
        """Return the already known offset, as the value is maintained on conversion.

        Args:
            known_offset: The known offset of the waveform.

        Returns:
            The known offset.
        """
        return known_offset

    def calculate_spacing(self) -> float:
        """Calculate the spacing based on the minimum and maximum of the dtype.

        Returns:
            The calculated spacing.
        """
        return 1 / (type_max(self.dtype) - type_min(self.dtype))

    ################################################################################################
    # Private Methods
    ################################################################################################

    @classmethod
    def _this_format_to_raw_sample_format(  # pyright: ignore [reportIncompatibleMethodOverride]
        cls,
        measured_data: NDArray[PossibleTypes],
        dtype: PossibleTypes,
    ) -> NDArray[PossibleTypes]:
        """Convert MeasuredData data to RawSample data.

        Args:
            measured_data: Information provided through measurement of a device.
            dtype: The dtype to convert to.
        """
        if dtype != measured_data.dtype:
            ratio = type_ratio(measured_data.dtype, dtype)
            # ideally, this could be done with math, but unfortunately, precision on float64
            # and Decimal causes there to be rounding errors
            if not np.issubdtype(measured_data.dtype.type, np.unsignedinteger) and np.issubdtype(
                dtype.type,
                np.unsignedinteger,
            ):
                offset = type_min(measured_data.dtype) * ratio
            elif np.issubdtype(measured_data.dtype.type, np.unsignedinteger) and not np.issubdtype(
                dtype.type,
                np.unsignedinteger,
            ):
                offset = -type_min(dtype)
            else:
                offset = 0
            raw_sample_data = (measured_data * float(ratio) - offset).astype(dtype)
        else:
            raw_sample_data = measured_data
        return raw_sample_data

    @classmethod
    def _raw_sample_format_to_this_format(
        cls,
        raw_sample_data: NDArray[PossibleTypes],
    ) -> NDArray[PossibleTypes]:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Convert FeatureScaled data to RawSample data.

        Args:
            raw_sample_data: Data that has been feature scaled.
        """
        return raw_sample_data


class FeatureScaled(MeasuredData):
    """Data that has been scaled to (-1.0, 1.0)."""

    ################################################################################################
    # Public Methods
    ################################################################################################

    def calculate_offset(self, known_offset: float = 0.0) -> float:
        """Return the already known offset, as the value is maintained on conversion.

        Args:
            known_offset: The known offset of the waveform.

        Returns:
            The known offset.
        """
        return known_offset

    def calculate_spacing(self) -> float:
        """Return 1.0, as the range is between -1.0 and 1.0.

        Returns:
            1.0.
        """
        return 1.0

    ################################################################################################
    # Private Methods
    ################################################################################################

    @classmethod
    def _this_format_to_raw_sample_format(
        cls,
        measured_data: NDArray[PossibleTypes],
        dtype: PossibleTypes,
    ) -> NDArray[PossibleTypes]:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Return passed data as the type is already FeatureScaled.

        Args:
            measured_data: Information provided through measurement of a device.
            dtype: The dtype to convert to.
        """
        return (measured_data * type_max(dtype)).astype(dtype)

    @classmethod
    def _raw_sample_format_to_this_format(
        cls,
        raw_sample_data: NDArray[PossibleTypes],
    ) -> NDArray[PossibleTypes]:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Return passed data as the type is already FeatureScaled.

        Args:
            raw_sample_data: Data that has been feature scaled.
        """
        np_dtype = np.dtype(Double.np_repr)
        current_dtype: PossibleTypes = np.dtype(raw_sample_data.dtype)
        return (raw_sample_data / type_max(current_dtype)).astype(np_dtype)


class Normalized(MeasuredData):
    """Data that has been normalized to a provided offset and amplitude."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    _offset = None
    _spacing = None

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __new__(
        cls,
        measured_data: MeasuredData | NDArray[PossibleTypes] | List[float | int],
        spacing: Optional[float] = None,
        offset: Optional[float] = None,
        as_type: Optional[Type[ByteData] | Type[PossibleTypes] | PossibleTypes] = None,
    ) -> Self:
        """Override the base new, utilizing the offset and spacing class variables temporarily.

        Args:
            measured_data: Information provided through measurement of a device.
            spacing: The spacing to utilize when converting to this type.
            offset: The offset to utilize when converting to this type.
            as_type: The dtype/bytetype to convert the measured data to.

        Returns:
            The current new instance of Normalized.
        """
        dtype = _check_type(as_type, measured_data)

        if spacing is None:
            # normalize around known values
            cls._spacing = (np.max(measured_data) - np.min(measured_data)) / (
                type_max(dtype) - type_min(dtype)
            )
        else:
            cls._spacing = spacing

        if offset is None:
            # normalize around known values
            cls._offset = ((np.max(measured_data) + np.min(measured_data)) / 2) / (
                type_max(dtype) - type_min(dtype)
            )
        else:
            cls._offset = offset

        return super().__new__(cls, measured_data, as_type)

    ################################################################################################
    # Public Methods
    ################################################################################################

    def calculate_spacing(self) -> float:
        """Calculate the spacing using the range of values, as the spacing was lost when converting.

        Returns:
            The calculated spacing.
        """
        return 1 / (np.max(self) - np.min(self))

    def calculate_offset(self, known_offset: float = 0.0) -> float:
        """Return the known offset plus the mean, as the offset has been lost when converting.

        Args:
            known_offset: The known offset of the waveform.

        Returns:
            The known offset plus the data mean.
        """
        return known_offset + np.mean(self)

    ################################################################################################
    # Private Methods
    ################################################################################################

    @classmethod
    def _this_format_to_raw_sample_format(
        cls,
        measured_data: NDArray[PossibleTypes],
        dtype: PossibleTypes,
    ) -> NDArray[PossibleTypes]:
        """Return passed data as the type is already FeatureScaled.

        Args:
            measured_data: Information provided through measurement of a device.
            dtype: The dtype to convert to.
        """
        spacing = (np.max(measured_data) - np.min(measured_data)) / (
            type_max(dtype) - type_min(dtype)
        )
        offset = (np.max(measured_data) + np.min(measured_data)) / 2
        return ((measured_data - offset) / spacing).astype(dtype)

    @classmethod
    def _raw_sample_format_to_this_format(
        cls,
        raw_sample_data: NDArray[PossibleTypes],
    ) -> NDArray[PossibleTypes]:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Return passed data as the type is already FeatureScaled.

        Args:
            raw_sample_data: Data that has been feature scaled.
        """
        return raw_sample_data.copy() * cls._spacing + cls._offset


class Digitized(MeasuredData):
    """Data that has been converted to separate data streams along the 2nd axis."""

    ################################################################################################
    # Public Methods
    ################################################################################################
    def calculate_spacing(self) -> float:
        """Return 1.0, as this information is redundant.

        Returns:
            1.0.
        """
        return 1.0

    def calculate_offset(self, known_offset: float = 0.0) -> float:  # noqa: ARG002
        """Return 0.0, as this information is redundant.

        Args:
            known_offset: The known offset of the waveform.

        Returns:
            0.0.
        """
        return 0.0

    ################################################################################################
    # Private Methods
    ################################################################################################

    @classmethod
    def _this_format_to_raw_sample_format(
        cls,
        measured_data: NDArray[PossibleTypes],
        dtype: PossibleTypes,  # noqa: ARG003
    ) -> NDArray[PossibleTypes]:
        """Return passed data as the type is already FeatureScaled.

        Args:
            measured_data: Information provided through measurement of a device.
            dtype: The dtype to convert to.
        """
        return np.packbits(measured_data).view(np.int8)

    @classmethod
    def _raw_sample_format_to_this_format(
        cls,
        raw_sample_data: NDArray[PossibleTypes],
    ) -> NDArray[PossibleTypes]:
        """Return passed data as the type is already FeatureScaled.

        Args:
            raw_sample_data: Data that has been feature scaled.
        """
        return np.unpackbits(raw_sample_data.view(np.uint8))
