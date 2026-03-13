"""The functionality to read and write to a mat file when the waveform is IQ."""

from tm_data_types.datum.data_types import MeasuredData
from tm_data_types.datum.waveforms.iq_waveform import IQWaveform
from tm_data_types.files_and_formats.mat.mat import MATFile


class WaveformFileMATIQ(MATFile):
    """Provides the methods of reading and writing to a .mat file with a digital waveform."""

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
    # Public Methods
    ################################################################################################

    # Reading
    def _set_vertical_values(
        self,
        waveform: IQWaveform,
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
    def _get_vertical_values(self, waveform: IQWaveform) -> MeasuredData:
        """Get the vertical values from the analog waveform to a generic type.

        Args:
            waveform: The analog waveform to get the vertical values from.

        Returns:
            The vertical values that are from the waveform.
        """
