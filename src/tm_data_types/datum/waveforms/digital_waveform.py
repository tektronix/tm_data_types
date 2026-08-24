"""Handles information pertaining to digital waveforms."""

from functools import cached_property
from typing import Any, Iterator, Optional

import numpy as np

from numpy.typing import NDArray
from pydantic.dataclasses import dataclass as pydantic_dataclass

from tm_data_types.datum.data_types import Digitized, MeasuredData, PossibleTypes, RawSample
from tm_data_types.datum.waveforms.waveform import Waveform, WaveformMetaInfo
from tm_data_types.helpers.enums import SIBaseUnit


@pydantic_dataclass(kw_only=True)
class DigitalWaveformMetaInfo(WaveformMetaInfo):  # pylint: disable=too-many-instance-attributes
    """Data which can come from tekmeta or a header for digital waveforms.

    This class extends WaveformMetaInfo with digital-specific metadata fields.
    It includes all the standard waveform metadata plus digital-specific fields
    for digital probe states and digital signal information.

    Digital-specific fields:
    - digital_probe_0_state through digital_probe_7_state: State of digital probes
    - digital_probe_0_threshold through digital_probe_7_threshold: Threshold values
    - digital_probe_0_name through digital_probe_7_name: Names of digital probes
    - digital_probe_0_unit through digital_probe_7_unit: Units for digital probes

    Examples:
        >>> meta_info = DigitalWaveformMetaInfo()
        >>> meta_info.digital_probe_0_state = b"0x01"
        >>> meta_info.digital_probe_0_threshold = 1.65
        >>> meta_info.set_custom_metadata(
        ...     test_equipment="MSO54",
        ...     digital_pattern="PRBS7"
        ... )
        >>> print(meta_info.digital_probe_0_threshold)  # 1.65
        >>> print(meta_info.test_equipment)  # "MSO54"
    """

    ################################################################################################
    # Class Variables
    ################################################################################################

    digital_probe_0_state: bytes = b"0x01"
    digital_probe_1_state: bytes = b"0x01"
    digital_probe_2_state: bytes = b"0x01"
    digital_probe_3_state: bytes = b"0x01"
    digital_probe_4_state: bytes = b"0x01"
    digital_probe_5_state: bytes = b"0x01"
    digital_probe_6_state: bytes = b"0x01"
    digital_probe_7_state: bytes = b"0x01"


class DigitalWaveform(Waveform):  # pylint: disable=too-many-instance-attributes
    """Class which represents a digital waveform with a y-axis and x-axis."""

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __str__(self) -> str:
        """Returns a string representation of the class.

        Returns:
            digital
        """
        return "digital"

    def __init__(self) -> None:
        """Initialize the digital waveform class with the raw data."""
        super().__init__()
        self.y_axis_byte_values: MeasuredData = MeasuredData(np.empty(0))
        self.y_axis_units: str = SIBaseUnit.NONE.value
        self.digital_bitmask: int = 0
        self._frame_data: Optional[np.ndarray] = None
        self._frame_count: int = 1
        self._current_frame: int = 0
        self._tt_offsets: Optional[np.ndarray] = None
        self._frame_gmt_sec: Optional[np.ndarray] = None
        self._frame_gmt_fract: Optional[np.ndarray] = None
        self._frame_precharge: Optional[np.ndarray] = None
        self._frame_postcharge: Optional[np.ndarray] = None
        self._precharge_length: int = 0
        self._postcharge_length: int = 0

    def __getattribute__(self, key: str) -> Any:
        """Return the active frame view when accessing byte values on FastFrame data."""
        if key == "y_axis_byte_values":
            frame_data = object.__getattribute__(self, "__dict__").get("_frame_data")
            if frame_data is not None:
                current_frame = object.__getattribute__(self, "_current_frame")
                return RawSample(frame_data[current_frame])
            return object.__getattribute__(self, "__dict__")["y_axis_byte_values"]
        return super().__getattribute__(key)

    def __setattr__(self, key: str, value: Any) -> None:
        """Set the attributes for the waveform class.

        Args:
            key: The attribute name to set as a string.
            value: The value that the attribute is set to.
        """
        if key in {"y_axis_values", "y_axis_spacing", "y_axis_offset", "_frame_data"}:
            self.__dict__.pop("normalized_vertical_values", None)

        if key == "y_axis_byte_values":
            if self.__dict__.get("_frame_data") is not None:
                msg = (
                    "Cannot set y_axis_byte_values directly on FastFrame waveform. "
                    "Use fill_frame()."
                )
                raise ValueError(msg)
            if not isinstance(value, MeasuredData):
                super().__setattr__("y_axis_byte_values", RawSample(value))
            else:
                super().__setattr__("y_axis_byte_values", value)
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
            yield np.asarray(self.y_axis_byte_values)

    ################################################################################################
    # Public Methods
    ################################################################################################

    def get_nth_bitstream(self, bitstream_number: int) -> Digitized:
        """Get the bitstream based on the value provided.

        Example:
            get_nth_bitstream(1) will provide the 2nd bitstream.

        Args:
            bitstream_number: The bitstream number (starting at 0) to get.

        Returns:
            The bitstream that is associated with the provided value.
        """
        return self.normalized_vertical_values.T[bitstream_number]

    @classmethod
    def create_fastframe(
        cls,
        frame_count: int,
        record_length: int,
        dtype: PossibleTypes = np.int8,
        precharge_length: int = 0,
        postcharge_length: int = 0,
        **kwargs: Any,
    ) -> "DigitalWaveform":
        """Pre-allocate a FastFrame digital waveform."""
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
            return np.asarray(self.y_axis_byte_values)
        frame_count = self.__dict__.get("_frame_count", 1)
        msg = f"Frame {idx} out of range [0, {frame_count})"
        raise IndexError(msg)

    def frame(self, index: int) -> "DigitalWaveform":
        """Return this waveform for single-frame data (TekHSI compat)."""
        if index == self.current_frame:
            return self
        msg = f"Single-frame waveform has no frame {index}"
        raise ValueError(msg)

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
    def tt_offsets(self) -> Optional[np.ndarray]:
        """Per-frame trigger-to-trigger offsets in seconds."""
        return self._tt_offsets

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

    @property
    def current_frame(self) -> int:
        """Active frame index."""
        return self._current_frame

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        self.current_frame = value

    @cached_property
    def normalized_vertical_values(self) -> Digitized:
        """Cache the iq values with the extent and offset are applied.

        This is reset when iq values are changed.

        Returns:
            An np array with the iq_axis_extent_magnitude and y_axis_offset are applied.
        """
        digitized_y_values = Digitized(self.y_axis_byte_values)
        return digitized_y_values.reshape((self.record_length, -1))

    @property
    def _measured_data(self) -> np.ndarray:
        """The abstract representation of the y_axis data.

        Returns:
            The y_axis values
        """
        return self.y_axis_byte_values
