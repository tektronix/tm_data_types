"""The functionality to read and write to a csv file when the waveform is digital."""

from tm_data_types.datum.data_types import RawSample
from tm_data_types.datum.waveforms.digital_waveform import (
    DigitalWaveform,
    DigitalWaveformMetaInfo,
)
from tm_data_types.files_and_formats.wfm.wfm import WFMFile
from tm_data_types.files_and_formats.wfm.wfm_format import WfmFormat
from tm_data_types.helpers.byte_data_types import SignedChar
from tm_data_types.helpers.enums import DataTypes


class WaveformFileWFMDigital(WFMFile[DigitalWaveform]):
    """Provides the methods of reading and writing to a .wfm file with a digital waveform."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    _META_DATA_LOOKUP = WFMFile.update_bidict(
        WFMFile._META_DATA_LOOKUP,  # noqa: SLF001
        {
            "digital_probe_0_state": "d0",
            "digital_probe_1_state": "d1",
            "digital_probe_2_state": "d2",
            "digital_probe_3_state": "d3",
            "digital_probe_4_state": "d4",
            "digital_probe_5_state": "d5",
            "digital_probe_6_state": "d6",
            "digital_probe_7_state": "d7",
        },
    )
    DATUM_TYPE = DigitalWaveform
    META_DATA_TYPE = DigitalWaveformMetaInfo

    ################################################################################################
    # Private Methods
    ################################################################################################

    # Reading
    def _format_to_waveform_vertical_values(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: DigitalWaveform,
        formatted_data: WfmFormat,
    ) -> None:
        """Convert the data from a formatted data class to an digial waveform class.

        Args:
            formatted_data: The formatted data from the file.

        Returns:
            Returns a digital waveform created from the formatted data.
        """
        waveform.y_axis_byte_values = formatted_data.curve_buffer
        if formatted_data.explicit_dimensions is not None:
            waveform.y_axis_units = formatted_data.explicit_dimensions.first.units

    # Writing
    def _waveform_vertical_values_to_format(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: DigitalWaveform,
        formatted_data: WfmFormat,
    ) -> None:
        """Convert the data from a digital waveform class to a formatted data class.

        Args:
            waveform: The formatted data from the file.

        Returns:
            Returns a digital waveform created from the formatted data.
        """
        explicit_data = RawSample(waveform.y_axis_byte_values, as_type=SignedChar)

        formatted_data.setup_explicit_dimensions(
            units=waveform.y_axis_units,
            curve_format=self._CURVE_FORMAT_LOOKUP[explicit_data.dtype],
        )
        formatted_data.curve_buffer = explicit_data
        formatted_data.setup_implicit_dimensions(
            units=waveform.x_axis_units,
            scale=waveform.x_axis_spacing,
            offset=-waveform.trigger_index * waveform.x_axis_spacing,
        )
        formatted_data.setup_header(data_type=DataTypes.DIGITAL)
