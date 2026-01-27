"""The functionality to read and write to a csv file when the waveform is analog."""

from typing import Tuple

import numpy as np

from tm_data_types.datum.data_types import Normalized, RawSample, type_max, type_min
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform, AnalogWaveformMetaInfo
from tm_data_types.files_and_formats.csv.csv import CSVFile


class WaveformFileCSVAnalog(CSVFile[AnalogWaveform]):
    """Provides the methods of reading and writing to a .csv file with an analog waveform."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    WAVEFORM_TYPE = AnalogWaveform
    META_DATA_TYPE = AnalogWaveformMetaInfo

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __str__(self) -> str:
        """A string representation of the class.

        Returns:
            ANALOG
        """
        return "ANALOG"

    ################################################################################################
    # Private Methods
    ################################################################################################

    # Reading
    def _check_file_contents(self) -> bool:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Check the contents of the file and find info that dictates if the waveform is analog.

        Returns:
            Whether the waveform is analog.
        """
        for row in self.csv_reader:
            if row[0] == "Waveform Type":
                return row[1] == str(self)

            try:
                float(row[0])
            except ValueError:
                pass
            else:
                return False
        return False

    # Reading
    def _set_waveform_values(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: AnalogWaveform,
        values_matrix: np.ndarray,
    ) -> None:
        """Set the vertical values for the analog waveform using the csv data.

        Args:
            waveform: The analog waveform which is being formatted.
            values_matrix: A matrix containing the x-axis and y-axis values.
        """
        normalized_vertical_values = Normalized(values_matrix[:, 1], as_type=np.float32)
        vertical_minimum = normalized_vertical_values.min()
        vertical_maximum = normalized_vertical_values.max()
        vertical_axis_spacing = (vertical_maximum - vertical_minimum) / (
            type_max(np.dtype(np.int16)) - type_min(np.dtype(np.int16))
        )
        vertical_axis_offset = (vertical_maximum + vertical_minimum) / 2
        waveform.y_axis_values = RawSample(normalized_vertical_values, as_type=np.int16)
        waveform.y_axis_offset = vertical_axis_offset
        waveform.y_axis_spacing = vertical_axis_spacing

    # Writing
    def _setup_waveform_headers(self, waveform: AnalogWaveform) -> str:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Set up the headers specific to analog waveforms.

        Args:
            waveform: The analog waveform to use when setting up the specific headers.

        Returns:
            The specific analog waveform headers to append to the csv output.
        """
        return f"Vertical Units,{waveform.y_axis_units}\n"

    # Writing
    def _formatted_waveform_values(self, waveform: AnalogWaveform) -> Tuple[Normalized, str, str]:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Return the formatted information for csv writing.

        Args:
            waveform: The waveform to use when setting up the formatted information.

        Returns:
            The normalized vertical values, the csv format, and the channels to use.
        """
        if not isinstance(waveform.y_axis_values, Normalized):
            y_axis_values = waveform.normalized_vertical_values
        else:
            y_axis_values = waveform.y_axis_values
        return (
            y_axis_values[:, None],
            "%10.8e",
            waveform.source_name if waveform.source_name else "CH1",
        )
