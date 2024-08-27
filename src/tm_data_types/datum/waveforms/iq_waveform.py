"""Handles information pertaining to iq waveforms."""

from functools import cached_property
from typing import Optional, Any

import numpy as np
from pydantic.dataclasses import dataclass as pydantic_dataclass
from dataclasses import field

from tm_data_types.datum.data_types import MeasuredData
from tm_data_types.datum.data_types import RawSample, Normalized, type_max, type_min
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveformMetaInfo
from tm_data_types.datum.waveforms.waveform import Waveform
from tm_data_types.helpers.enums import IQWindowTypes
from tm_data_types.helpers.enums import SIBaseUnit


@pydantic_dataclass(frozen=False)
class IQWaveformMetaInfo(AnalogWaveformMetaInfo):
    """Data which can come from tekmeta or a header for iq waveforms."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    iq_center_frequency: float = field(default_factory=float)
    iq_fft_length: float = field(default_factory=float)
    iq_resolution_bandwidth: float = field(default_factory=float)
    iq_span: float = field(default_factory=float)
    iq_window_type: str = field(default_factory=float)
    iq_sample_rate: Optional[float] = None

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __post_init__(self) -> None:
        """Post initialization, calculate sample rate."""
        iq_window_lookup = {
            IQWindowTypes.BLACKHARRIS: 1.9,
            IQWindowTypes.FLATTOP: 3.77,
            IQWindowTypes.HANNING: 1.44,
            IQWindowTypes.HAMMING: 1.3,
            IQWindowTypes.RECTANGLE: 0.89,
            IQWindowTypes.KAISERBESSEL: 2.23,
        }
        # search the lookup for the correct window type and calculate the sample rate
        for iq_window_type, magic_number in iq_window_lookup.items():
            if self.iq_window_type.upper() == iq_window_type.value.upper():
                self.iq_sample_rate = (
                    self.iq_fft_length * self.iq_resolution_bandwidth
                ) / magic_number
                break
        else:
            self.iq_sample_rate = self.iq_span


class IQWaveform(Waveform):
    """A waveform conforming to the separate dimensions of quadrature and in phase."""

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __str__(self):
        """Returns a string representation of the class.

        Returns:
            iq
        """
        return "iq"

    def __init__(self):
        """Initialize the iq waveform class with the raw data."""
        super().__init__()
        self.meta_info: Optional[IQWaveformMetaInfo]
        self.interleaved_iq_axis_values: MeasuredData = MeasuredData(np.empty(0))
        self.iq_axis_spacing: float = 1.0
        self.iq_axis_offset: float = 0.0
        self.iq_axis_units: str = SIBaseUnit.VOLTS.value

    def __setattr__(self, key: str, value: Any) -> None:
        """Set the attributes for the waveform class.

        Args:
            key: The attribute name to set as a string.
            value: The value that the attribute is set to.
        """
        if key == "interleaved_iq_axis_values":
            # y axis values need to be typecase when set.
            # if hasattr(self, "normalized_y_values"):
            # del self.normalized_y_values
            if not isinstance(value, MeasuredData):
                super(Waveform, self).__setattr__("interleaved_iq_axis_values", RawSample(value))
            else:
                super(Waveform, self).__setattr__("interleaved_iq_axis_values", value)
        else:
            super(Waveform, self).__setattr__(key, value)

    ################################################################################################
    # Properties
    ################################################################################################

    @cached_property
    def normalized_vertical_values(self) -> np.ndarray:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Cache the iq values with the extent and offset are applied.

        This is reset when iq values are changed.

        Returns:
            An np array with the iq_axis_extent_magnitude and y_axis_offset are applied.
        """
        normalized_i_values = Normalized(
            self.i_axis_values, self.iq_axis_spacing, self.iq_axis_offset
        )
        normalized_q_values = Normalized(
            self.q_axis_values, self.iq_axis_spacing, self.iq_axis_offset
        )
        return normalized_i_values + 1j * normalized_q_values

    @property
    def i_axis_values(self) -> MeasuredData:
        """Get the in phase values in the interleaved iq values.

        Returns:
            An np view of the in phase values in the interleaved iq values.
        """
        return self.interleaved_iq_axis_values[::2]

    @i_axis_values.setter
    def i_axis_values(self, i_values: np.ndarray) -> None:
        """Set the in phase values in the interleaved iq values.

        Args:
            i_values: The in phase values to place into the interleaved values.
        """
        if not self.interleaved_iq_axis_values.shape[0]:
            self.interleaved_iq_axis_values = np.empty(len(i_values) * 2, dtype=i_values.dtype)
        self.interleaved_iq_axis_values[::2] = i_values

    @property
    def q_axis_values(self) -> MeasuredData:
        """The quadrature values in the interleaved iq values.

        Returns:
            An np view of the quadrature values in the interleaved iq values.
        """
        return self.interleaved_iq_axis_values[1::2]

    @q_axis_values.setter
    def q_axis_values(self, q_values: np.ndarray) -> None:
        """Set the quadrature values in the interleaved iq values.

        Args:
            q_values: The quadrature values to place into the interleaved values.
        """
        if not self.interleaved_iq_axis_values.shape[0]:
            self.interleaved_iq_axis_values = np.empty(len(q_values) * 2, dtype=q_values.dtype)
        self.interleaved_iq_axis_values[1::2] = q_values

    @property
    def iq_axis_extent_magnitude(self) -> float:
        """Get the magnitude extent of values that can be represented in the iq axis units.

        Returns:
            A float value which represents the magnitude of what values which can be represented
            by the waveform.
        """
        type_extent = type_max(self.interleaved_iq_axis_values.dtype) - type_min(
            self.interleaved_iq_axis_values.dtype
        )
        return self.iq_axis_spacing * type_extent

    @iq_axis_extent_magnitude.setter
    def iq_axis_extent_magnitude(self, extent_magnitude: float):
        """Set the magnitude extent of values that can be represented in the y axis units.

        Args:
            extent_magnitude: A float value which represents the magnitude of what values which
            can be represented by the waveform.
        """
        type_extent = type_max(self.interleaved_iq_axis_values.dtype) - type_min(
            self.interleaved_iq_axis_values.dtype
        )
        self.iq_axis_spacing = extent_magnitude / type_extent

    @property
    def _measured_data(self) -> MeasuredData:
        """The abstract representation of the y_axis data.

        Returns:
            The y_axis values.
        """
        return self.q_axis_values
