# pyright: ignore [reportIncompatibleMethodOverride]
"""The functionality to read and write to a csv file when the waveform is complex."""

from typing import Any, Dict

from tm_data_types.datum.data_types import RawSample
from tm_data_types.datum.waveforms.iq_waveform import IQWaveform, IQWaveformMetaInfo
from tm_data_types.files_and_formats.wfm.wfm import WFMFile
from tm_data_types.files_and_formats.wfm.wfm_format import WfmFormat
from tm_data_types.helpers.byte_data_types import Short
from tm_data_types.helpers.enums import StorageTypes


class WaveformFileWFMIQ(WFMFile[IQWaveform]):
    """Provides the methods of reading and writing to a .wfm file with an iq waveform."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    _META_DATA_LOOKUP = WFMFile.update_bidict(
        WFMFile._META_DATA_LOOKUP,  # noqa: SLF001
        {
            "iq_center_frequency": "IQ_centerFrequency",
            "iq_fft_length": "IQ_fftLength",
            "iq_resolution_bandwidth": "IQ_rbw",
            "iq_span": "IQ_span",
            "iq_window_type": "IQ_windowType",
            "iq_sample_rate": "IQ_sampleRate",
        },
    )
    DATUM_TYPE = IQWaveform
    META_DATA_TYPE = IQWaveformMetaInfo

    ################################################################################################
    # Public Methods
    ################################################################################################

    ################################################################################################
    # Private Methods
    ################################################################################################

    # Reading
    def _check_metadata(self, meta_data: Dict[str, Any]) -> bool:  # pylint: disable=arguments-differ
        """Check if metadata indicates this is an IQ waveform.

        IQ waveforms are identified by the presence of IQ-specific metadata fields:
        - IQ_centerFrequency, IQ_fftLength, IQ_rbw, IQ_span, IQ_windowType, IQ_sampleRate
        """
        iq_fields = [
            "IQ_centerFrequency",
            "IQ_fftLength",
            "IQ_rbw",
            "IQ_span",
            "IQ_windowType",
            "IQ_sampleRate",
        ]
        return any(field in meta_data for field in iq_fields)

    # Reading
    def _format_to_waveform_vertical_values(
        self,
        waveform: IQWaveform,
        formatted_data: WfmFormat,
    ) -> None:
        """Convert the data from a formatted data class to an iq waveform class.

        Args:
            waveform: The IQ waveform object.
            formatted_data: The formatted data from the file.

        Returns:
            Returns an iq waveform created from the formatted data.
        """
        waveform.interleaved_iq_axis_values = formatted_data.curve_buffer
        if formatted_data.explicit_dimensions is not None:
            waveform.iq_axis_offset = formatted_data.explicit_dimensions.first.offset
            waveform.iq_axis_spacing = formatted_data.explicit_dimensions.first.scale
            waveform.iq_axis_units = formatted_data.explicit_dimensions.first.units

    # Writing
    def _waveform_vertical_values_to_format(
        self,
        waveform: IQWaveform,
        formatted_data: WfmFormat,
    ) -> None:
        """Convert the data from an iq waveform class to a formatted data class.

        Args:
            waveform: The IQ waveform object.
            formatted_data: The formatted data from the file.

        Returns:
            Returns an iq waveform created from the formatted data.
        """
        if type(waveform.i_axis_values) is not type(waveform.q_axis_values):
            msg = "I values are a different type than Q values."
            raise TypeError(msg)

        if not isinstance(waveform.i_axis_values, RawSample):
            explicit_data = RawSample(waveform.interleaved_iq_axis_values, as_type=Short)
        else:
            explicit_data = waveform.interleaved_iq_axis_values

        formatted_data.setup_explicit_dimensions(
            units=waveform.iq_axis_units,
            scale=waveform.iq_axis_spacing,
            offset=waveform.iq_axis_spacing,
            curve_format=self._CURVE_FORMAT_LOOKUP[explicit_data.dtype],
            storage_type=StorageTypes.EXPLICIT_MIN_MAX,
        )
        formatted_data.curve_buffer = explicit_data
