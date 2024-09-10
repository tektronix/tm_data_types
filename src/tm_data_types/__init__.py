"""tm_data_types.

Read and write common Test & Measurement files.

Examples:
    >>>
"""

from importlib.metadata import version

from tm_data_types.datum.data_types import Normalized, RawSample
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform, AnalogWaveformMetaInfo
from tm_data_types.datum.waveforms.digital_waveform import DigitalWaveform, DigitalWaveformMetaInfo
from tm_data_types.datum.waveforms.iq_waveform import IQWaveform, IQWaveformMetaInfo
from tm_data_types.datum.waveforms.waveform import Waveform, WaveformMetaInfo
from tm_data_types.helpers.class_lookup import FileExtensions
from tm_data_types.helpers.enums import SIBaseUnit
from tm_data_types.io_factory_methods import (
    read_file,
    read_files_in_parallel,
    write_file,
    write_files_in_parallel,
)

# Read version from installed package.
__version__ = version("tm_data_types")

__all__ = [
    "Waveform",
    "WaveformMetaInfo",
    "AnalogWaveform",
    "AnalogWaveformMetaInfo",
    "IQWaveform",
    "IQWaveformMetaInfo",
    "DigitalWaveform",
    "DigitalWaveformMetaInfo",
    "RawSample",
    "Normalized",
    "write_file",
    "write_files_in_parallel",
    "read_file",
    "read_files_in_parallel",
    "SIBaseUnit",
    "FileExtensions",
]
