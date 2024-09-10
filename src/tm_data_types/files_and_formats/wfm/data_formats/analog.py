"""The functionality to read and write to a csv file when the waveform is analog."""

from tm_data_types.datum.data_types import RawSample
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform, AnalogWaveformMetaInfo
from tm_data_types.files_and_formats.wfm.wfm import WFMFile
from tm_data_types.files_and_formats.wfm.wfm_format import WfmFormat
from tm_data_types.helpers.byte_data_types import Short


class WaveformFileWFMAnalog(WFMFile[AnalogWaveform]):
    """Provides the methods of reading and writing to a .wfm file with an analog waveform."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    DATUM_TYPE = AnalogWaveform
    META_DATA_TYPE = AnalogWaveformMetaInfo

    ################################################################################################
    # Private Methods
    ################################################################################################

    # Reading
    def _format_to_waveform_vertical_values(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: AnalogWaveform,
        formatted_data: WfmFormat,
    ) -> None:
        """Convert the data from a formatted data class to an analog waveform class.

        Args:
            formatted_data: The formatted data from the file.

        Returns:
            Returns an analog waveform created from the formatted data.
        """
        waveform.y_axis_values = formatted_data.curve_buffer
        if formatted_data.explicit_dimensions is not None:
            waveform.y_axis_offset = formatted_data.explicit_dimensions.first.offset
            waveform.y_axis_spacing = formatted_data.explicit_dimensions.first.scale
            waveform.y_axis_units = formatted_data.explicit_dimensions.first.units

    # Writing
    def _waveform_vertical_values_to_format(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: AnalogWaveform,
        formatted_data: WfmFormat,
    ) -> None:
        """Convert the data from an analog waveform class to a formatted data class.

        Args:
            waveform: The formatted data from the file.

        Returns:
            Returns an analog waveform created from the formatted data.
        """
        if not isinstance(waveform.y_axis_values, RawSample):
            output_waveform = waveform.transform_to_type(Short)
        else:
            output_waveform = waveform
        formatted_data.setup_explicit_dimensions(
            units=output_waveform.y_axis_units,
            scale=output_waveform.y_axis_spacing,
            offset=output_waveform.y_axis_offset,
            curve_format=self._CURVE_FORMAT_LOOKUP[output_waveform.y_axis_values.dtype],
        )

        formatted_data.curve_buffer = output_waveform.y_axis_values
