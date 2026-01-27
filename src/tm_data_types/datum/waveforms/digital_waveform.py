"""Handles information pertaining to digital waveforms."""

from functools import cached_property
from typing import Any

import numpy as np

from pydantic.dataclasses import dataclass as pydantic_dataclass

from tm_data_types.datum.data_types import Digitized, MeasuredData, RawSample
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


class DigitalWaveform(Waveform):
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
        """Initialize the analog waveform class with the raw data."""
        super().__init__()
        self.y_axis_byte_values: MeasuredData = MeasuredData(np.empty(0))
        self.y_axis_units: str = SIBaseUnit.NONE.value

    def __setattr__(self, key: str, value: Any) -> None:
        """Set the attributes for the waveform class.

        Args:
            key: The attribute name to set as a string.
            value: The value that the attribute is set to.
        """
        if key in {"y_axis_values", "y_axis_spacing", "y_axis_offset"}:
            self.__dict__.pop("normalized_vertical_values", None)

        if key == "y_axis_byte_values":
            # y axis values need to be typecase when set.
            # if hasattr(self, "normalized_y_values"):
            # del self.normalized_y_values
            if not isinstance(value, MeasuredData):
                super().__setattr__("y_axis_byte_values", RawSample(value))
            else:
                super().__setattr__("y_axis_byte_values", value)
        else:
            super().__setattr__(key, value)

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

    ################################################################################################
    # Properties
    ################################################################################################

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
