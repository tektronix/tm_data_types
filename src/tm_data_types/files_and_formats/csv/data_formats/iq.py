"""The functionality to read and write to a iq file when the waveform is complex."""

import numpy as np

from tm_data_types.datum.data_types import Normalized, RawSample, type_max, type_min
from tm_data_types.datum.waveforms.iq_waveform import IQWaveform, IQWaveformMetaInfo
from tm_data_types.files_and_formats.csv.csv import CSVFile


class WaveformFileCSVIQ(CSVFile[IQWaveform]):
    """Provides the methods of reading and writing to a .csv file with an iq waveform."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    WAVEFORM_TYPE = IQWaveform
    META_DATA_TYPE = IQWaveformMetaInfo

    _IQ_META_DATA_LOOKUP = CSVFile.update_bidict(
        CSVFile._META_DATA_LOOKUP,  # noqa: SLF001
        {
            "iq_center_frequency": "IQ_centerFrequency",
            "iq_fft_length": "IQ_fftLength",
            "iq_resolution_bandwidth": "IQ_rbw",
            "iq_span": "IQ_span",
            "iq_window_type": "IQ_windowType",
        },
    )

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __str__(self) -> str:
        """Returns a string representation of the class.

        Returns:
            IQ
        """
        return "IQ"

    ################################################################################################
    # Private Methods
    ################################################################################################

    # Reading
    def _check_file_contents(self) -> bool:
        """Check the contents of the file and find info that dictates if the waveform is IQ.

        Returns:
            Whether the waveform is IQ.
        """
        for row in self.csv_reader:
            if row[0] == "Waveform Type":
                return row[1] == str(self)

            try:
                float(row[0])
            except ValueError:
                return False
        return False

    # Reading
    def _set_waveform_values(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: IQWaveform,
        values_matrix: np.ndarray,
    ) -> None:
        """Set the vertical values for the iq waveform using the csv data.

        Args:
            waveform: The waveform which is being formatted.
            values_matrix: A matrix containing the x axis and the iq values.
        """
        normalized_vertical_values = Normalized(values_matrix[:, 1], as_type=np.float32)
        vertical_minimum = normalized_vertical_values.min()
        vertical_maximum = normalized_vertical_values.max()
        vertical_axis_spacing = (vertical_maximum - vertical_minimum) / (
            type_max(np.dtype(np.int16)) - type_min(np.dtype(np.int16))
        )
        vertical_axis_offset = (vertical_maximum + vertical_minimum) / 2
        waveform.i_axis_values = RawSample(normalized_vertical_values[::2], as_type=np.int16)
        waveform.q_axis_values = RawSample(normalized_vertical_values[1::2], as_type=np.int16)
        waveform.iq_axis_offset = vertical_axis_offset
        waveform.iq_axis_spacing = vertical_axis_spacing

    # Writing
    def _setup_waveform_headers(self, waveform: IQWaveform) -> str:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Set up the headers specific to iq waveforms.

        Args:
            waveform: The iq waveform to use when setting up the specific headers.

        Returns:
            The specific iq waveform headers to append to the csv output.
        """
        return f"Vertical Units,{waveform.iq_axis_units}\n"

    # Writing
    def _formatted_waveform_values(self, waveform: IQWaveform) -> Normalized:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Return the formatted information for csv writing.

        Args:
            waveform: The waveform to use when setting up the formatted information.

        Returns:
            The normalized vertical values.
        """
        if not isinstance(waveform.interleaved_iq_axis_values, Normalized):
            y_axis_values = Normalized(
                waveform.interleaved_iq_axis_values,
                waveform.iq_axis_spacing,
                waveform.iq_axis_offset,
                as_type=np.float32,
            )
        else:
            y_axis_values = waveform.interleaved_iq_axis_values
        return y_axis_values
