"""Handles information pertaining to analog waveforms."""

from functools import cached_property
from typing import Any, Iterator, Optional, Type

import numpy as np

from numpy.typing import NDArray
from pydantic.dataclasses import dataclass as pydantic_dataclass

from tm_data_types.datum.data_types import (
    FeatureScaled,
    MeasuredData,
    Normalized,
    PossibleTypes,
    RawSample,
    type_max,
    type_min,
)
from tm_data_types.datum.waveforms.waveform import Waveform, WaveformMetaInfo
from tm_data_types.helpers.byte_data_types import ByteData
from tm_data_types.helpers.enums import SIBaseUnit


@pydantic_dataclass(kw_only=True)
class AnalogWaveformMetaInfo(WaveformMetaInfo):
    """Data which can come from tekmeta or a header for analog waveforms.

    This class extends WaveformMetaInfo with analog-specific metadata fields.
    It includes all the standard waveform metadata plus analog-specific fields
    like vertical offset, position, and clipping information.

    Analog-specific fields:
    - y_offset: Vertical offset of the waveform
    - y_position: Vertical position of the waveform
    - analog_thumbnail: Thumbnail representation of the analog signal
    - clipping_initialized: Whether clipping detection is enabled
    - interpreter_factor: Factor used for data interpretation
    - real_data_start_index: Index where real data starts

    Examples:
        >>> meta_info = AnalogWaveformMetaInfo()
        >>> meta_info.y_offset = 0.5
        >>> meta_info.y_position = 1.0
        >>> meta_info.set_custom_metadata(
        ...     test_equipment="MSO54",
        ...     channel="CH1"
        ... )
        >>> print(meta_info.y_offset)  # 0.5
        >>> print(meta_info.test_equipment)  # "MSO54"
    """

    ################################################################################################
    # Class Variables
    ################################################################################################

    y_offset: Optional[float] = 0.0
    y_position: Optional[float] = 0.0
    analog_thumbnail: Optional[str] = None
    clipping_initialized: Optional[int] = 1
    interpreter_factor: Optional[int] = None
    real_data_start_index: Optional[int] = None


class AnalogWaveform(Waveform):  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """Class which represents an analog waveform with a y-axis and x-axis."""

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __str__(self) -> str:
        """Returns a string representation of the class.

        Returns:
            analog
        """
        return "analog"

    def __init__(self) -> None:
        """Initialize the analog waveform class with the raw data."""
        super().__init__()
        self.meta_info: Optional[AnalogWaveformMetaInfo]  # pyright: ignore [reportIncompatibleVariableOverride]
        self.y_axis_values: MeasuredData = MeasuredData(np.empty(0))
        self.y_axis_spacing: float = 1.0
        self.y_axis_offset: float = 0.0
        self.y_axis_units: str = SIBaseUnit.VOLTS.value
        self._frame_data: Optional[np.ndarray] = None
        self._frame_count: int = 1
        self._current_frame: int = 0
        self._tt_offsets: Optional[np.ndarray] = None
        self._frame_gmt_sec: Optional[np.ndarray] = None
        self._frame_gmt_fract: Optional[np.ndarray] = None
        self._summary_frame: int = -1
        self._frame_precharge: Optional[np.ndarray] = None
        self._frame_postcharge: Optional[np.ndarray] = None
        self._precharge_length: int = 0
        self._postcharge_length: int = 0

    def __getattribute__(self, key: str) -> Any:
        """Return the active frame view when accessing y_axis_values on FastFrame data."""
        if key == "y_axis_values":
            frame_data = object.__getattribute__(self, "__dict__").get("_frame_data")
            if frame_data is not None:
                current_frame = object.__getattribute__(self, "_current_frame")
                return RawSample(frame_data[current_frame])
            return object.__getattribute__(self, "__dict__")["y_axis_values"]
        return super().__getattribute__(key)

    def __setattr__(self, key: str, value: Any) -> None:
        """Set the attributes for the waveform class.

        Args:
            key: The attribute name to set as a string.
            value: The value that the attribute is set to.
        """
        if key in {"y_axis_values", "y_axis_spacing", "y_axis_offset", "_frame_data"}:
            self.__dict__.pop("normalized_vertical_values", None)

        if key == "y_axis_values":
            if self.__dict__.get("_frame_data") is not None:
                msg = "Cannot set y_axis_values directly on FastFrame waveform. Use fill_frame()."
                raise ValueError(msg)
            if not isinstance(value, MeasuredData):
                super().__setattr__("y_axis_values", RawSample(value))
            else:
                super().__setattr__("y_axis_values", value)
        elif key == "current_frame":
            frame_count = self.__dict__.get("_frame_count", 1)
            if not 0 <= value < frame_count:
                msg = f"Frame {value} out of range [0, {frame_count})"
                raise IndexError(msg)
            super().__setattr__("_current_frame", value)
        else:
            super().__setattr__(key, value)

    def __iter__(self) -> Iterator[NDArray[Any]]:
        """Iterate over all frames as numpy array views."""
        if self._frame_data is not None:
            for index in range(self._frame_count):
                yield self._frame_data[index]
        else:
            yield np.asarray(self.y_axis_values)

    ################################################################################################
    # Public Methods
    ################################################################################################

    @classmethod
    def create_fastframe(
        cls,
        frame_count: int,
        record_length: int,
        dtype: PossibleTypes = np.int16,
        precharge_length: int = 0,
        postcharge_length: int = 0,
        **kwargs: Any,
    ) -> "AnalogWaveform":
        """Pre-allocate a FastFrame waveform.

        Args:
            frame_count: Number of frames to allocate.
            record_length: Samples per frame.
            dtype: Sample data type.
            precharge_length: Samples per frame in the precharge region.
            postcharge_length: Samples per frame in the postcharge region.
            **kwargs: Additional waveform attributes.

        Returns:
            Pre-allocated AnalogWaveform ready for fill_frame() calls.
        """
        waveform = cls()
        waveform._frame_data = np.empty((frame_count, record_length), dtype=dtype)
        waveform._frame_count = frame_count
        waveform._current_frame = 0
        waveform._tt_offsets = np.zeros(frame_count, dtype=np.float64)
        waveform._frame_gmt_sec = np.zeros(frame_count, dtype=np.int64)
        waveform._frame_gmt_fract = np.zeros(frame_count, dtype=np.float64)
        waveform._precharge_length = precharge_length
        waveform._postcharge_length = postcharge_length
        if precharge_length:
            waveform._frame_precharge = np.zeros((frame_count, precharge_length), dtype=dtype)
        if postcharge_length:
            waveform._frame_postcharge = np.zeros((frame_count, postcharge_length), dtype=dtype)
        for key, val in kwargs.items():
            setattr(waveform, key, val)
        return waveform

    def fill_frame(self, frame_idx: int, data: np.ndarray) -> None:
        """Copy frame data into the pre-allocated buffer."""
        if self._frame_data is None:
            msg = "Not a FastFrame waveform. Use create_fastframe() first."
            raise ValueError(msg)
        self._frame_data[frame_idx] = data
        self.__dict__.pop("normalized_vertical_values", None)

    def set_frame_timing(
        self,
        frame_idx: int,
        tt_offset: float,
        gmt_sec: int = 0,
        gmt_fract: float = 0.0,
    ) -> None:
        """Set per-frame timing metadata."""
        if self._tt_offsets is not None:
            self._tt_offsets[frame_idx] = tt_offset
        if self._frame_gmt_sec is not None:
            self._frame_gmt_sec[frame_idx] = gmt_sec
        if self._frame_gmt_fract is not None:
            self._frame_gmt_fract[frame_idx] = gmt_fract

    def frame_data(self, idx: int) -> NDArray[Any]:
        """Get a specific frame's data without changing current_frame."""
        if self._frame_data is not None:
            return self._frame_data[idx]
        if not idx:
            return np.asarray(self.y_axis_values)
        frame_count = self.__dict__.get("_frame_count", 1)
        msg = f"Frame {idx} out of range [0, {frame_count})"
        raise IndexError(msg)

    def frame(self, index: int) -> "AnalogWaveform":
        """Return this waveform for single-frame data (TekHSI compat)."""
        if index == self.current_frame:
            return self
        msg = f"Single-frame waveform has no frame {index}"
        raise ValueError(msg)

    def transform_to_normalized(self) -> "AnalogWaveform":
        """Convert the waveform to normalized."""
        copied_waveform = self.copy()
        new_spacing = self.y_axis_extent_magnitude
        ratio = float(1 / (self.y_axis_values.calculate_spacing() * new_spacing))

        copied_waveform.y_axis_values = Normalized(
            self.y_axis_values,
            offset=self.y_axis_offset,
            spacing=self.y_axis_spacing,
        )
        copied_waveform.y_axis_spacing *= ratio
        copied_waveform.y_axis_offset = 0.0
        return copied_waveform

    def transform_to_type(
        self,
        as_type: Type[ByteData] | Type[PossibleTypes] | PossibleTypes,
    ) -> "AnalogWaveform":
        """Convert the waveform to a new type."""
        copied_waveform = self.copy()
        copied_waveform.y_axis_offset = self.y_axis_values.calculate_offset(self.y_axis_offset)
        copied_waveform.y_axis_values = RawSample(copied_waveform.y_axis_values, as_type=as_type)
        new_spacing = copied_waveform.y_axis_values.calculate_spacing()
        ratio = float(new_spacing / self.y_axis_values.calculate_spacing())
        copied_waveform.y_axis_spacing *= ratio
        return copied_waveform

    def _convert_to_feature_scaled(self) -> "AnalogWaveform":
        """Hidden For now."""
        copied_waveform = self.copy()
        copied_waveform.y_axis_values = FeatureScaled(self.y_axis_values)
        return copied_waveform

    ################################################################################################
    # Properties
    ################################################################################################

    @property
    def frame_count(self) -> int:
        """Number of frames.

        1 for normal waveforms, >1 for FastFrame.
        """
        return self._frame_count

    @property
    def is_fastframe(self) -> bool:
        """True if this waveform contains multiple FastFrame acquisitions."""
        return self._frame_count > 1

    @property
    def current_frame(self) -> int:
        """Active frame index."""
        return self._current_frame

    @property
    def tt_offsets(self) -> Optional[np.ndarray]:
        """Per-frame trigger-to-trigger offsets in seconds."""
        return self._tt_offsets

    @property
    def summary_frame(self) -> int:
        """Index of the summary frame, or -1 if none."""
        return self._summary_frame

    @property
    def all_frames(self) -> Optional[np.ndarray]:
        """Direct access to the 2D frame array."""
        return self._frame_data

    @property
    def frame_gmt_sec(self) -> Optional[np.ndarray]:
        """Per-frame GMT seconds array."""
        return self._frame_gmt_sec

    @property
    def frame_gmt_fract(self) -> Optional[np.ndarray]:
        """Per-frame GMT fractional seconds array."""
        return self._frame_gmt_fract

    @property
    def precharge_length(self) -> int:
        """Number of precharge samples stored per frame."""
        return self._precharge_length

    @property
    def postcharge_length(self) -> int:
        """Number of postcharge samples stored per frame."""
        return self._postcharge_length

    def frame_precharge(self, idx: int) -> Optional[NDArray[Any]]:
        """Return precharge samples for a frame when present."""
        if self._frame_precharge is None:
            return None
        return self._frame_precharge[idx]

    def frame_postcharge(self, idx: int) -> Optional[NDArray[Any]]:
        """Return postcharge samples for a frame when present."""
        if self._frame_postcharge is None:
            return None
        return self._frame_postcharge[idx]

    @cached_property
    def normalized_vertical_values(self) -> Normalized:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Cache the y values with the extent and offset are applied.

        This is reset when y values are changed.

        Returns:
            An np array with the y_axis_extent_magnitude and y_axis_offset are applied.
        """
        return Normalized(self.y_axis_values, self.y_axis_spacing, self.y_axis_offset)

    @property
    def y_axis_extent_magnitude(self) -> float:
        """Get the magnitude extent of values that can be represented in the y-axis units.

        Returns:
            A float value which represents the magnitude of what values which can be represented
            by the waveform.
        """
        # FOILed to support float64
        return self.y_axis_spacing / self.y_axis_values.calculate_spacing()

    @y_axis_extent_magnitude.setter
    def y_axis_extent_magnitude(self, extent_magnitude: float) -> None:
        """Set the spacing based on values that can be represented in the y-axis units.

        Example:
            If the extent magnitude is 1.0 and the numpy type is a long, then it will
            functionally set the spacing to 1.0 / 2**16.

        Args:
            extent_magnitude: A float value which represents the magnitude of what values which
            can be represented by the waveform.
        """
        # FOILed to support float64
        # find the ratio between the min and the max
        ratio = 0.5 - (
            abs(type_min(self.y_axis_values.dtype)) - abs(type_max(self.y_axis_values.dtype))
        ) / (abs(type_min(self.y_axis_values.dtype) - type_max(self.y_axis_values.dtype)) * 2)
        upper_extent = 0
        lower_extent = 0
        if ratio:
            upper_extent = (ratio**2) * (extent_magnitude / type_max(self.y_axis_values.dtype))
        if ratio != 1:
            lower_extent = ((1 - ratio) ** 2) * (
                extent_magnitude / type_min(self.y_axis_values.dtype)
            )

        self.y_axis_spacing = upper_extent - lower_extent

    @property
    def _measured_data(self) -> NDArray:
        """The abstract representation of the y_axis data.

        Returns:
            The y_axis values
        """
        return self.y_axis_values
