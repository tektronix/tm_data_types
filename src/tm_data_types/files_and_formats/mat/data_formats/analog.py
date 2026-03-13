"""The functionality to read and write to a mat file when the waveform is analog."""

from tm_data_types.datum.data_types import MeasuredData, Normalized
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform
from tm_data_types.files_and_formats.mat.mat import MATFile


class WaveformFileMATAnalog(MATFile[AnalogWaveform]):
    """Provides the methods of reading and writing to a .mat file with an analog waveform."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    WAVEFORM_TYPE = AnalogWaveform

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __str__(self) -> str:
        """Returns a string representation of the class.

        Returns:
            Analog
        """
        return "Analog"

    ################################################################################################
    # Public Methods
    ################################################################################################

    # Reading
    def _set_vertical_values(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: AnalogWaveform,
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
        waveform.y_axis_values = vertical_values
        waveform.y_axis_offset = vertical_offset
        waveform.y_axis_spacing = vertical_spacing

    # Writing
    def _get_vertical_values(self, waveform: AnalogWaveform) -> MeasuredData:  # pyright: ignore [reportIncompatibleMethodOverride]
        """Get the vertical values from the analog waveform to a generic type.

        Args:
            waveform: The analog waveform to get the vertical values from.

        Returns:
            The vertical values that are from the waveform.
        """
        if not isinstance(waveform.y_axis_values, Normalized):
            y_axis_values = waveform.normalized_vertical_values
        else:
            y_axis_values = waveform.y_axis_values
        return y_axis_values
