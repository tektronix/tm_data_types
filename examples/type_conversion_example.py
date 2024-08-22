import numpy as np
from tm_data_types import AnalogWaveformMetaInfo, AnalogWaveform, RawSample, Normalized
from tm_data_types.datum.data_types import type_max, type_min
from tm_data_types.helpers.byte_data_types import Short, Long, LongLong, Float

if __name__ == "__main__":
    values_int8 = RawSample(np.array([1, 2, 4, 8, 16, 32, 64, 127], dtype=np.int8))
    analog_meta = AnalogWaveformMetaInfo()
    waveform_int8 = AnalogWaveform()
    waveform_int8.meta_info = analog_meta
    waveform_int8.y_axis_values = values_int8
    waveform_int8.y_axis_extent_magnitude = 1.0
    waveform_int8.y_axis_offset = 0.1

    waveform_int16 = waveform_int8.transform_to_type(as_type=np.int16)

    assert all(
        np.isclose(
            waveform_int8.normalized_vertical_values,
            waveform_int16.normalized_vertical_values,
            atol=0.0015,
        )
    )

    values_int16 = RawSample(values_int8, as_type=Short)
    values_int32 = RawSample(values_int8, as_type=Long)
    values_int64 = RawSample(values_int8, as_type=LongLong)
    values_float32 = RawSample(values_int8, as_type=Float)

    normalized_values_int8 = Normalized(
        values_int8, spacing=1 / (type_max(np.int8) - type_min(np.int8)), offset=0.0
    )
    normalized_values_int16 = Normalized(
        values_int16, spacing=1 / (type_max(np.int16) - type_min(np.int16)), offset=0.0
    )
    normalized_values_int32 = Normalized(
        values_int32, spacing=1 / (type_max(np.int32) - type_min(np.int32)), offset=0.0
    )
    normalized_values_int64 = Normalized(
        values_int64, spacing=1 / (type_max(np.int64) - type_min(np.int64)), offset=0.0
    )
    normalized_values_float32 = Normalized(
        values_float32, spacing=1 / (type_max(np.float32) - type_min(np.float32)), offset=0.0
    )

    assert any(
        np.isclose(
            normalized_values_int8,
            normalized_values_int16,
            atol=0.0015,
        )
    )
