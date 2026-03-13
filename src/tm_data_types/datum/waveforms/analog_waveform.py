"""Handles information pertaining to analog waveforms."""

from functools import cached_property
from typing import Any, Optional, Type

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


class AnalogWaveform(Waveform):
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

    def __setattr__(self, key: str, value: Any) -> None:
        """Set the attributes for the waveform class.

        Args:
            key: The attribute name to set as a string.
            value: The value that the attribute is set to.
        """
        if key in {"y_axis_values", "y_axis_spacing", "y_axis_offset"}:
            self.__dict__.pop("normalized_vertical_values", None)

        if key == "y_axis_values":
            # y-axis values need to be typecase when set.
            if not isinstance(value, MeasuredData):
                super().__setattr__("y_axis_values", RawSample(value))
            else:
                super().__setattr__("y_axis_values", value)
        else:
            super().__setattr__(key, value)

    ################################################################################################
    # Public Methods
    ################################################################################################

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
        """Convert the waveform to a new type.

        Args:
            as_type: The type to convert to.

        Returns:
            A copy of the waveform transformed to raw sample values.
        """
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
