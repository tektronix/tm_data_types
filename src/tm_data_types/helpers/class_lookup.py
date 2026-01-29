"""Helpers used to find what type of format needs to be used to write to/read from the file."""

from enum import Enum
from typing import Dict, List, Type

from tm_data_types.datum.datum import Datum
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform
from tm_data_types.datum.waveforms.digital_waveform import DigitalWaveform
from tm_data_types.datum.waveforms.iq_waveform import IQWaveform
from tm_data_types.files_and_formats.abstracted_file import AbstractedFile
from tm_data_types.files_and_formats.csv.data_formats.analog import WaveformFileCSVAnalog
from tm_data_types.files_and_formats.csv.data_formats.digital import WaveformFileCSVDigital
from tm_data_types.files_and_formats.csv.data_formats.iq import WaveformFileCSVIQ
from tm_data_types.files_and_formats.mat.data_formats.analog import WaveformFileMATAnalog
from tm_data_types.files_and_formats.mat.data_formats.digital import WaveformFileMATDigital
from tm_data_types.files_and_formats.mat.data_formats.iq import WaveformFileMATIQ
from tm_data_types.files_and_formats.wfm.data_formats.analog import WaveformFileWFMAnalog
from tm_data_types.files_and_formats.wfm.data_formats.digital import WaveformFileWFMDigital
from tm_data_types.files_and_formats.wfm.data_formats.iq import WaveformFileWFMIQ
from tm_data_types.helpers.enums import CustomStrEnum


class CustomFormatEnum(Enum):
    """A custom base class for string Enums.

    This class provides better type hinting for the value property.
    """

    @classmethod
    def list_values(cls) -> List[AbstractedFile]:
        """Return a list of all the values of the enum."""
        return [enum_entry.value for enum_entry in cls]


class FileExtensions(CustomStrEnum):
    """The different file extensions that can be read from/written to."""

    CSV = "csv"  # Comma Seperated Values
    WFM = "wfm"  # Waveform Format
    MAT = "mat"  # MATLab File Format
    WFMX = "wfmx"


class CSVFormats(CustomFormatEnum):
    """The different formats that a csv file can exist in."""

    WAVEFORM = WaveformFileCSVAnalog  # Analog CSV waveform
    WAVEFORMIQ = WaveformFileCSVIQ  # IQ CSV waveform
    WAVEFORMDIGITAL = WaveformFileCSVDigital


class WFMFormats(CustomFormatEnum):
    """The different formats that a wfm file can exist in."""

    WAVEFORMDIGITAL = WaveformFileWFMDigital  # Digital WFM waveform (checked first)
    WAVEFORMIQ = WaveformFileWFMIQ  # IQ WFM waveform (checked second)
    WAVEFORM = WaveformFileWFMAnalog  # Analog WFM waveform (checked last, default fallback)


class MATFormats(CustomFormatEnum):
    """The different formats that a mat file can exist in."""

    WAVEFORM = WaveformFileMATAnalog  # Analog WFM waveform
    WAVEFORMIQ = WaveformFileMATIQ  # IQ WFM waveform
    WAVEFORMDIGITAL = WaveformFileMATDigital  # Digital WFM waveform


def handle_extensions(
    extension: FileExtensions,
) -> CustomFormatEnum:
    """Handle the extensions based on what the file path is.

    Args:
        extension: The extensions of the file that is being written to.
    """
    try:
        # what formats to check based on the file extension
        extension_lookup = {
            FileExtensions.CSV: CSVFormats,
            FileExtensions.WFM: WFMFormats,
            FileExtensions.MAT: MATFormats,
        }
        format_lookup = extension_lookup[extension]
    except KeyError as e:
        msg = f"Extension {extension} cannot be written or read from."
        raise KeyError(msg) from e
    return format_lookup


def find_class_format(
    extension: FileExtensions,
    waveform_type: Type[Datum],
) -> AbstractedFile:
    """Find the file and class format based on what waveform was provided.

    Args:
        extension: The extensions of the file that is being written to.
        waveform_type: The waveform type that is being written.
    """
    format_lookup = handle_extensions(extension)
    class_lookup: Dict[Type[Datum], CustomFormatEnum] = {
        AnalogWaveform: format_lookup.WAVEFORM,
        IQWaveform: format_lookup.WAVEFORMIQ,
        DigitalWaveform: format_lookup.WAVEFORMDIGITAL,
    }
    check = waveform_type
    return class_lookup[check].value


def find_class_format_list(
    extension: FileExtensions,
) -> List[AbstractedFile]:
    """Find what possible file formats can be used based on the extension or waveform.

    Args:
        extension: The extensions of the file that is being read from.
    """
    format_lookup = handle_extensions(extension)

    return format_lookup.list_values()


def access_type(extension: FileExtensions, write: bool) -> str:
    """How the file should be accessed.

    Args:
        extension: The extensions of the file that is being written to/read from.
        write: Whether the file is being written to or not.
    """
    base_access = "w" if write else "r"
    # wfm and mat files are accessed via a binary write, whereas csvs are text based
    access_type_lookup = {
        FileExtensions.CSV: base_access + "+",
        FileExtensions.WFM: base_access + "b+",
        FileExtensions.MAT: base_access + "b+",
    }
    return access_type_lookup[extension]
