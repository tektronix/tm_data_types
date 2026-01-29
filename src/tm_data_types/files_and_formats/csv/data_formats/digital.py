"""The functionality to read and write to a csv file when the waveform is digital."""

from typing import Tuple

import numpy as np

from tm_data_types.datum.data_types import Digitized, RawSample
from tm_data_types.datum.waveforms.digital_waveform import (
    DigitalWaveform,
    DigitalWaveformMetaInfo,
)
from tm_data_types.files_and_formats.csv.csv import CSVFile


class WaveformFileCSVDigital(CSVFile[DigitalWaveform]):
    """Provides the methods of reading and writing to a .csv file with an analog waveform."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    WAVEFORM_TYPE = DigitalWaveform
    META_DATA_TYPE = DigitalWaveformMetaInfo

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __str__(self) -> str:
        """Returns a string representation of the class.

        Returns:
            DIGITAL
        """
        return "DIGITAL"

    ################################################################################################
    # Private Methods
    ################################################################################################

    # Reading
    def _check_file_contents(self) -> bool:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Check the contents of the file and find info that dictates if the waveform is digital.

        Returns:
            Whether the waveform is digital.
        """
        for row in self.csv_reader:
            if row[0] == "Waveform Type":
                return row[1] == str(self)

            # the pointer has gone too far, exit the loop
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
        waveform: DigitalWaveform,
        values_matrix: np.ndarray,
    ) -> None:
        """Set the vertical values for the waveform using the csv data.

        Args:
            waveform: The waveform which is being formatted.
            values_matrix: A matrix containing the x axis and all bit streams.
        """
        digitized_vertical_values = Digitized(values_matrix[:, 1:], as_type=np.int8)
        waveform.y_axis_byte_values = RawSample(digitized_vertical_values, as_type=np.int8)

    # Writing
    def _setup_waveform_headers(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: DigitalWaveform,
    ) -> str:
        """Set up the headers specific to digital waveforms.

        Args:
            waveform: The digital waveform to use when setting up the specific headers.

        Returns:
            The specific digital waveform headers to append to the csv output.
        """
        return f"Digital Type,{np.dtype(waveform.y_axis_byte_values.dtype).itemsize * 8}x1\n"

    # Writing
    def _formatted_waveform_values(self, waveform: DigitalWaveform) -> Tuple[Digitized, str, str]:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Return the formatted information for csv writing.

        Args:
            waveform: The digital waveform to use when setting up the formatted information.

        Returns:
            The normalized vertical values, the csv format, and the channels to use.
        """
        if not isinstance(waveform.y_axis_byte_values, Digitized):
            y_axis_byte_values = waveform.normalized_vertical_values
        else:
            y_axis_byte_values = waveform.y_axis_byte_values
        if not waveform.source_name:
            channels = ",".join(
                [f"CH1_D{bitstream}" for bitstream in range(y_axis_byte_values.dtype.itemsize * 8)],
            )
        elif "DALL" in waveform.source_name:
            channel_name = waveform.source_name.replace("_DALL", "")
            channels = ",".join(
                [
                    f"{channel_name}_D{bitstream}"
                    for bitstream in range(y_axis_byte_values.dtype.itemsize * 8)
                ],
            )
        else:
            channels = waveform.source_name
        return y_axis_byte_values, "%10.8e,%u,%u,%u,%u,%u,%u,%u,%u", channels
