"""The functionality to read and write to a mat file when the waveform is digital."""

from tm_data_types.datum.data_types import MeasuredData
from tm_data_types.datum.waveforms.digital_waveform import DigitalWaveform
from tm_data_types.files_and_formats.mat.mat import MATFile


class WaveformFileMATDigital(MATFile):
    """Provides the methods of reading and writing to a .mat file with a digital waveform."""

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __str__(self) -> str:
        """Returns a string representation of the class.

        Returns:
            Digital
        """
        return "Digital"

    ################################################################################################
    # Public Methods
    ################################################################################################

    # Reading
    def _set_vertical_values(
        self,
        waveform: DigitalWaveform,
        vertical_values: MeasuredData,
        vertical_offset: float,
        vertical_spacing: float,
    ) -> None:
        """Set the vertical values of the analog waveform.

        Args:
            waveform: The analog waveform which the vertical axis are set.
            vertical_values: The values that lie on the vertical axis.
            vertical_offset: The offset of the vertical axis.
            vertical_spacing: The spacing between each value on the vertical axis.
        """

    # Writing
    def _get_vertical_values(self, waveform: DigitalWaveform) -> MeasuredData:
        """Get the vertical values from the analog waveform to a generic type.

        Args:
            waveform: The analog waveform to get the vertical values from.

        Returns:
            The vertical values that are from the waveform.
        """
