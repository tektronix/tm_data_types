from tm_data_types.files_and_formats.csv.data_formats.analog import WaveformFileCSVAnalog
from tm_data_types import AnalogWaveform, AnalogWaveformMetaInfo
import os
import shutil
import numpy as np

if __name__ == "__main__":
    WAVEFORM_DIR = "example_waveforms"
    if os.path.exists(os.path.join(os.getcwd(), WAVEFORM_DIR)):
        shutil.rmtree(WAVEFORM_DIR)
    os.mkdir(WAVEFORM_DIR)

    values = np.array([10, 11, 12, 32222, 32223, 32224, 55, 56, 57], dtype=np.int16)
    analog_meta_info = AnalogWaveformMetaInfo()
    waveform = AnalogWaveform()
    waveform.meta_info = analog_meta_info
    waveform.y_axis_values = values
    waveform.y_axis_extent_magnitude = 1.0
    waveform.y_axis_offset = 0.1
    file_path = f"{os.getcwd()}\\{WAVEFORM_DIR}\\write_example_serial.csv"

    with WaveformFileCSVAnalog(file_path, "w") as fd:
        fd.write_datum(waveform)
