"""An example of how to read and write using the tm_data_types module."""

import os
import shutil

import numpy as np

from tm_data_types import (
    AnalogWaveform,
    AnalogWaveformMetaInfo,
    write_file,
    write_files_in_parallel,
)

if __name__ == "__main__":
    WAVEFORM_DIR = "example_waveforms"
    if os.path.exists(os.path.join(os.getcwd(), WAVEFORM_DIR)):
        shutil.rmtree(WAVEFORM_DIR)
    os.mkdir(WAVEFORM_DIR)

    values_1 = np.array([10, 11, 12, 32222, 32223, 32224, 55, 56, 57], dtype=np.int16)
    analog_meta_info_1 = AnalogWaveformMetaInfo()
    waveform_1 = AnalogWaveform()
    waveform_1.meta_info = analog_meta_info_1
    waveform_1.y_axis_values = values_1
    waveform_1.y_axis_extent_magnitude = 1.0
    waveform_1.y_axis_offset = 0.1
    file_path_1 = f"{os.getcwd()}\\{WAVEFORM_DIR}\\write_example_serial.wfm"

    write_file(file_path_1, waveform_1)

    values_2 = np.array([15, 16, 17, -10000, -10001, -10002, 156, 157, 158], dtype=np.int16)
    analog_meta_info_2 = AnalogWaveformMetaInfo()
    waveform_2 = AnalogWaveform()
    waveform_2.meta_info = analog_meta_info_2
    waveform_2.y_axis_values = values_2
    waveform_2.y_axis_extent_magnitude = 1.0
    waveform_2.y_axis_offset = 0.1
    file_path_2 = f"{os.getcwd()}\\{WAVEFORM_DIR}\\write_example_parallel_1.wfm"
    file_path_3 = f"{os.getcwd()}\\{WAVEFORM_DIR}\\write_example_parallel_2.wfm"

    waveform_list = [waveform_1, waveform_2]
    file_path_list = [file_path_2, file_path_3]

    write_files_in_parallel(file_path_list, waveform_list)
