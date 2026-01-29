"""Tests for tm_data_types."""

import os
import timeit

from pathlib import Path
from typing import List, Type, TYPE_CHECKING

import numpy as np
import pytest

from tm_data_types import FileExtensions
from tm_data_types.datum.data_types import RawSample, type_max, type_min
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform
from tm_data_types.datum.waveforms.digital_waveform import (
    DigitalWaveform,
)
from tm_data_types.datum.waveforms.iq_waveform import IQWaveform
from tm_data_types.datum.waveforms.waveform import Waveform, WaveformMetaInfo
from tm_data_types.files_and_formats.wfm.data_formats.analog import (
    AnalogWaveformMetaInfo,
    WaveformFileWFMAnalog,
)
from tm_data_types.files_and_formats.wfm.data_formats.iq import WaveformFileWFMIQ
from tm_data_types.helpers.byte_data_types import (
    ByteData,
    Char,
    Double,
    Float,
    Long,
    LongLong,
    Short,
    UnsignedChar,
    UnsignedLong,
    UnsignedLongLong,
    UnsignedShort,
)
from tm_data_types.io_factory_methods import (
    read_file,
    read_files_in_parallel,
    write_file,
    write_files_in_parallel,
)

if TYPE_CHECKING:
    from numpy.typing import DTypeLike


def test_serial(tmp_path: Path) -> None:
    """Check to make sure that a serial write can write a waveform and read the same waveform."""
    waveform_path = tmp_path / "test_serial.wfm"

    values = np.array([10, 11, 12, 32222, 32223, 32224], dtype=np.int16)
    waveform = AnalogWaveform()
    waveform.meta_info = AnalogWaveformMetaInfo()
    waveform.y_axis_values = values
    waveform.y_axis_spacing = 1 / type_max(np.dtype(np.int16))
    waveform.trigger_index = 3.0

    with WaveformFileWFMAnalog(waveform_path.as_posix(), "wb+") as wfm:
        wfm.write_datum(waveform)

    with WaveformFileWFMAnalog(waveform_path.as_posix(), "rb+") as wfm:
        read_waveform = wfm.read_datum()

    assert np.array_equal(read_waveform.y_axis_values, waveform.y_axis_values)
    assert read_waveform.y_axis_spacing == waveform.y_axis_spacing
    assert read_waveform.y_axis_offset == waveform.y_axis_offset


def test_parallel(tmp_path: Path) -> None:
    """Check to make sure that a parallel write can write a waveform and read the same waveform."""
    waveform_info = {}
    file_count = 10

    for index in range(file_count):
        waveform_path = tmp_path / f"test_parallel_{index}.wfm"

        waveform_data = np.array([index * locale for locale in range(10)], np.int16)

        waveform = AnalogWaveform()
        waveform.y_axis_values = waveform_data
        waveform.meta_info = AnalogWaveformMetaInfo(
            y_offset=0.0,
            y_position=0.0,
        )
        waveform_info[waveform_path.as_posix()] = waveform

    write_files_in_parallel(list(waveform_info.keys()), list(waveform_info.values()))

    if read_info := read_files_in_parallel(list(waveform_info.keys())):
        for file_path, waveform in read_info:
            assert np.array_equal(waveform.y_axis_values, waveform_info[file_path].y_axis_values)
    else:
        msg = "No Files written/read."
        raise IOError(msg)


@pytest.mark.parametrize(
    ("waveform_type", "waveform_meta_info"),
    [(AnalogWaveform, AnalogWaveformMetaInfo)],
)
def test_wfm(
    waveform_type: Type[Waveform], waveform_meta_info: Type[WaveformMetaInfo], tmp_path: Path
) -> None:
    """Check that a saved waveform is in a format that is readable by the oscilloscope."""
    waveform = waveform_type()
    waveform.meta_info = waveform_meta_info()
    format_name = f"golden_{waveform}.wfm"
    waveform_dir = f"{Path(__file__).parent}/waveforms"
    golden_path = f"{waveform_dir}/{format_name}"

    waveform_path = tmp_path / "test_format.wfm"

    values = np.array([10, 11, 12, 32222, 32223, 32224], dtype=np.int16)

    waveform.y_axis_values = values
    waveform.y_axis_spacing = 1 / type_max(np.dtype(np.int16))
    write_file(waveform_path.as_posix(), waveform)

    with open(waveform_path, "rb+") as wfm:
        raw_test_data = wfm.read()

    with open(golden_path, "rb+") as wfm:
        golden_format_data = wfm.read()

    assert raw_test_data == golden_format_data


def read_write_read(
    vertical_data: str,
    waveform_path: str,
    data_path: str,
    temp_path: str,
) -> None:
    """Read a file, then write the waveform from the file, then read it again.

    Args:
        vertical_data: The name of the data attribute for vertical data.
        data_path: The path for a saved numpy file for data that should be retrieved from the file.
        waveform_path: The path of a saved waveform.
        temp_path: The path of a temporarily saved waveform.
    """
    read_wfm: Waveform = read_file(waveform_path)
    read_wfm_values = getattr(read_wfm, vertical_data)
    loaded_data = np.load(data_path)
    # needs to be a multiple as .csv files don't know what the actual range of the values are
    # so we check to see if each value is fractionally the same
    waveforms_are_multiple = np.dot(read_wfm_values, loaded_data) * np.dot(
        read_wfm_values,
        loaded_data,
    ) == np.dot(read_wfm_values, read_wfm_values) * np.dot(loaded_data, loaded_data)
    assert waveforms_are_multiple

    write_file(temp_path, read_wfm)

    re_read_waveform: Waveform = read_file(temp_path)
    assert read_wfm.trigger_index == re_read_waveform.trigger_index
    assert np.all(
        np.isclose(
            read_wfm.normalized_vertical_values,
            re_read_waveform.normalized_vertical_values,
            atol=0.0005,
        ),
    )
    assert np.all(
        np.isclose(
            read_wfm.normalized_horizontal_values,
            re_read_waveform.normalized_horizontal_values,
            atol=0.0005,
        ),
    )
    if waveform_path.split(".")[-1] == temp_path.split(".")[-1]:
        assert np.array_equal(getattr(re_read_waveform, vertical_data), read_wfm_values)
    else:
        re_read_values = getattr(re_read_waveform, vertical_data)
        assert np.dot(re_read_values, read_wfm_values) * np.dot(
            re_read_values,
            read_wfm_values,
        ) == np.dot(re_read_values, re_read_values) * np.dot(read_wfm_values, read_wfm_values)


def test_analog(tmp_path: Path) -> None:
    """Test to see if analog waveforms will return the same data when saved and loaded."""
    waveform_data = "analog_data.npy"
    waveform_name = "analog_waveform."
    waveform_dir = f"{Path(__file__).parent}/waveforms"

    waveform_path = f"{waveform_dir}/{waveform_name}"
    data_path = f"{waveform_dir}/{waveform_data}"

    extensions = [
        FileExtensions.CSV.value,
        FileExtensions.WFM.value,
        FileExtensions.MAT.value,
    ]
    for known_extension in extensions:
        for temporary_extension in extensions:
            temp_waveform = (
                f"test_analog_{known_extension}_to_{temporary_extension}.{temporary_extension}"
            )
            temporary_path = tmp_path / temp_waveform
            read_write_read(
                "y_axis_values",
                waveform_path + known_extension,
                data_path,
                temporary_path.as_posix(),
            )


def test_iq(tmp_path: Path) -> None:
    """Test to see if IQ waveforms will return the same data when saved and loaded."""
    temp_waveform = "test_iq."
    waveform_data = "iq_data.npy"
    waveform_name = "iq_waveform."
    waveform_dir = f"{Path(__file__).parent}/waveforms"
    waveform_path = f"{waveform_dir}/{waveform_name}"
    data_path = f"{waveform_dir}/{waveform_data}"

    extensions = [
        FileExtensions.WFM.value,
        FileExtensions.CSV.value,
        FileExtensions.MAT.value,
    ]
    file_types = [WaveformFileWFMIQ]
    for extension, _ in zip(extensions, file_types, strict=False):
        temporary_path = tmp_path / (temp_waveform + extension)
        read_write_read(
            "interleaved_iq_axis_values",
            waveform_path + extension,
            data_path,
            temporary_path.as_posix(),
        )


def test_digital(tmp_path: Path) -> None:
    """Test to see if digital waveforms will return the same data when saved and loaded."""
    waveform_data = "digital_data.npy"
    waveform_name = "digital_waveform."
    waveform_dir = f"{Path(__file__).parent}/waveforms"
    waveform_path = f"{waveform_dir}/{waveform_name}"
    data_path = f"{waveform_dir}/{waveform_data}"
    extensions = [
        FileExtensions.WFM.value,
        FileExtensions.CSV.value,
    ]
    for known_extension in extensions:
        for temporary_extension in extensions:
            temp_waveform = (
                f"test_digital_{known_extension}_to_{temporary_extension}.{temporary_extension}"
            )
            temporary_path = tmp_path / temp_waveform
            read_write_read(
                "y_axis_byte_values",
                waveform_path + known_extension,
                data_path,
                temporary_path.as_posix(),
            )


def test_data() -> None:  # pylint: disable=too-many-locals
    """Test if normalized data is correctly represented, and that data types can be converted."""
    waveform_name = "data_test_waveform.wfm"
    waveform_dir = f"{Path(__file__).parent}/waveforms"
    waveform_path = f"{waveform_dir}/{waveform_name}"

    dtypes = [np.float32, np.int8, np.int16, np.int32, np.uint8, np.uint32, np.uint64]
    to_test_values = np.array([-4, -3, -2, -1, 0, 1, 2, 3, 4])
    extent_magnitude = 0.1
    offset = 0.1
    for dtype in dtypes:
        type_extent_max = type_max(np.dtype(dtype))
        type_extent_min = type_min(np.dtype(dtype))
        # create a value array from -5 to 5 as a np.int16,
        # then scale it to the extent of a 16 bit integer
        if np.issubdtype(dtype, np.unsignedinteger):
            to_test_values_updated = to_test_values + 5
        else:
            to_test_values_updated = to_test_values
        values_high = to_test_values_updated * (type_extent_max / 10)
        values_low = to_test_values_updated * (type_extent_min / 10)

        values = np.sort((values_high - values_low).astype(dtype))
        waveform = AnalogWaveform()
        waveform.y_axis_values = values
        waveform.y_axis_extent_magnitude = extent_magnitude
        waveform.y_axis_offset = offset

        expected_output = values * waveform.y_axis_spacing + offset
        actual_output = waveform.normalized_vertical_values
        # check if the data now has an amplitude of 0.1 and offset of 0.1
        assert np.array_equal(actual_output, expected_output)
        for converted_dtype in dtypes:
            waveform_copy = waveform.transform_to_type(converted_dtype)
            if not np.issubdtype(dtype, np.unsignedinteger) and np.issubdtype(
                converted_dtype,
                np.unsignedinteger,
            ):
                test_output = actual_output + (extent_magnitude / 2)
            elif np.issubdtype(dtype, np.unsignedinteger) and not np.issubdtype(
                converted_dtype,
                np.unsignedinteger,
            ):
                test_output = actual_output - (extent_magnitude / 2)
            else:
                test_output = actual_output

            if np.issubdtype(converted_dtype, np.unsignedinteger):
                literal_comparisons = np.isclose(
                    [0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19],
                    waveform_copy.normalized_vertical_values,
                    atol=0.002,
                )
            else:
                literal_comparisons = np.isclose(
                    [0.06, 0.07, 0.08, 0.09, 0.1, 0.11, 0.12, 0.13, 0.14],
                    waveform_copy.normalized_vertical_values,
                    atol=0.002,
                )
            value_comparisons = np.isclose(
                test_output,
                waveform_copy.normalized_vertical_values,
                atol=0.0005,
            )
            assert all(literal_comparisons)
            assert all(value_comparisons)

    # read a sin wave in from a TEKSCOPE with offset 0 and amplitude 0.5
    with WaveformFileWFMAnalog(waveform_path, "rb+") as wfm:
        read_waveform = wfm.read_datum()
    x_points = np.linspace(0, 1, read_waveform.y_axis_values.shape[0])

    # create a np sin wave magnitude and offset shifted to match the read sin wave
    sin_wave = np.sin(2 * np.pi * x_points) * 0.25

    # scale the sin wave x values so they match what should be output
    sin_wave_x_points = (
        x_points * len(x_points) - read_waveform.trigger_index
    ) * read_waveform.x_axis_spacing
    # make sure the values are very similar
    assert np.array_equal(
        np.around(read_waveform.normalized_horizontal_values, decimals=2),
        np.around(sin_wave_x_points, decimals=2),
    )

    # check if they are close with 7mV degree of error
    value_comparisons = np.isclose(sin_wave, read_waveform.normalized_vertical_values, atol=0.011)
    assert all(value_comparisons)


def test_properties() -> None:
    """Test the different properties in waveforms to see if they are correctly represented."""
    # Analog
    analog_waveform = AnalogWaveform()
    real_values = np.array([0, 1, 2, 3], dtype=np.int16) * round(
        type_max(np.dtype(np.int16)) / 3,
        1,
    )
    analog_waveform.y_axis_values = real_values.astype(np.int16)
    # check the type of the analog waveform info
    assert analog_waveform.y_axis_values.dtype is np.dtype(np.int16)
    analog_waveform.y_axis_offset = 0.1
    analog_waveform.y_axis_spacing = 0.0001
    analog_waveform.trigger_index = 2.5
    assert analog_waveform.record_length == 4
    assert np.array_equal(
        analog_waveform.normalized_horizontal_values,
        np.array([-2.5, -1.5, -0.5, 0.5]),
    )
    assert np.array_equal(
        np.around(analog_waveform.normalized_vertical_values, decimals=3),
        np.array([0.1, 1.192, 2.284, 3.377]),
    )

    # IQ
    iq_waveform = IQWaveform()
    q_values = np.array([-3, -2, -1, 0], dtype=np.int16) * round(
        type_max(np.dtype(np.int16)) / 3,
        1,
    )
    # functionally identical to creating a array and then interleaving the data.
    iq_waveform.i_axis_values = real_values.astype(np.int16)
    iq_waveform.q_axis_values = q_values.astype(np.int16)
    # check the type of iq waveform info
    assert iq_waveform.interleaved_iq_axis_values.dtype is np.dtype(np.int16)
    iq_waveform.iq_axis_extent_magnitude = 0.1
    iq_waveform.iq_axis_offset = 0.1
    iq_waveform.trigger_index = 2.5
    assert iq_waveform.record_length == 4
    assert np.array_equal(
        iq_waveform.normalized_horizontal_values,
        np.array([-2.5, -1.5, -0.5, 0.5]),
    )
    assert np.array_equal(
        np.around(iq_waveform.normalized_vertical_values, decimals=3),
        np.array([0.100 + 0.050j, 0.117 + 0.067j, 0.133 + 0.083j, 0.150 + 0.1j]),
    )

    # Digital
    digital_waveform = DigitalWaveform()
    digital_values = np.array([-1, 0, 1, 2], dtype=np.int8) * round(
        type_max(np.dtype(np.int8)) / 3,
        1,
    )
    digital_waveform.y_axis_byte_values = digital_values.astype(np.int8)
    assert np.array_equal(
        np.around(digital_waveform.normalized_vertical_values, decimals=3),
        np.array(
            [
                [1, 1, 0, 1, 0, 1, 1, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 0, 1, 0, 1, 0],
                [0, 1, 0, 1, 0, 1, 0, 0],
            ],
        ),
    )
    assert np.array_equal(digital_waveform.get_nth_bitstream(0), [1, 0, 0, 0])


def test_types() -> None:
    """Test the different types that can be used as waveform data."""
    with pytest.raises(TypeError, match=r"No type specified for data."):
        RawSample([1, 2, 3, 4])

    with pytest.raises(TypeError, match=r"No type can be gotten from the passed parameters."):
        RawSample([1, 2, 3, 4], as_type=ByteData)

    with pytest.raises(TypeError, match=r"Invalid type for minimum possible value."):
        type_min(np.dtype("c"))

    with pytest.raises(TypeError, match=r"Invalid type for maximum possible value."):
        type_max(np.dtype("c"))

    data_types = [[1, 2, 3, 4], np.array([1, 2, 3, 4]), RawSample([1, 2, 3, 4], as_type=Short)]
    data_byte_types: List[Type[ByteData]] = [
        Char,
        UnsignedChar,
        Short,
        UnsignedShort,
        Long,
        UnsignedLong,
        LongLong,
        UnsignedLongLong,
        Float,
        Double,
    ]
    np_types: List[Type[DTypeLike]] = [
        np.int8,
        np.uint8,
        np.int16,
        np.uint16,
        np.int32,
        np.uint32,
        np.int64,
        np.uint64,
        np.float32,
        np.float64,
    ]
    byte_arrays = []
    np_arrays = []
    for data in data_types:
        for data_byte in data_byte_types:
            byte_arrays.append(RawSample(data, as_type=data_byte))  # noqa: PERF401

        for np_type in np_types:
            np_arrays.append(RawSample(data, as_type=np_type))  # noqa: PERF401

        for np_array, byte_array in zip(np_arrays, byte_arrays, strict=False):
            assert np_array.dtype == byte_array.dtype


def transformation_types(waveform: AnalogWaveform) -> List[AnalogWaveform]:
    """A list containing all different transformation types dependent on waveform."""
    return [
        waveform.transform_to_type(np.int8),
        waveform.transform_to_type(np.int16),
        waveform.transform_to_type(np.int32),
        waveform.transform_to_type(np.float32),
        waveform.transform_to_normalized(),
    ]


def test_manipulations() -> None:
    """Test the different methods which can manipulate waveform values."""
    data = np.array([0.0, 0.25, 0.5, 0.75, 1.0], dtype=np.float32)
    raw_sample = RawSample((data * type_max(np.int16)).astype(np.int16))
    np_types: List[Type[DTypeLike]] = [
        np.int8,
        np.int16,
        np.int32,
        np.float32,
    ]
    for np_type in np_types:
        data_test = (data * type_max(np_type)).astype(np_type)
        raw_sample = raw_sample.append(data_test)


def test_transforms(tmp_path: Path) -> None:
    """Check to make sure that a serial write can write a waveform and read the same waveform."""
    waveform_path = tmp_path / "test_transforms.wfm"

    values = np.array([41, 42, 43, 124, 125, 126], dtype=np.int8)
    waveform = AnalogWaveform()
    waveform.meta_info = AnalogWaveformMetaInfo()
    waveform.y_axis_values = values.copy()
    waveform.y_axis_spacing = 1 / type_max(np.dtype(np.int8))
    waveform.trigger_index = 3.0

    for waveform_to_convert in transformation_types(waveform):
        for converted_waveform in transformation_types(waveform_to_convert):
            with WaveformFileWFMAnalog(waveform_path.as_posix(), "wb+") as wfm:
                wfm.write_datum(converted_waveform)

            with WaveformFileWFMAnalog(waveform_path.as_posix(), "rb+") as wfm:
                read_waveform = wfm.read_datum()
            waveforms_to_compare = [
                waveform,
                waveform_to_convert,
                converted_waveform,
                read_waveform,
            ]
            for comparer_waveform in waveforms_to_compare:
                for comparee_waveform in waveforms_to_compare:
                    value_comparisons = np.isclose(
                        comparer_waveform.normalized_vertical_values,
                        comparee_waveform.normalized_vertical_values,
                        atol=0.0015,
                    )
                    assert all(value_comparisons)


@pytest.mark.parametrize(
    ("si_unit", "length"),
    [
        ("10", 10**1),
        ("100", 10**2),
        ("1K", 10**3),
        ("10K", 10**4),
        ("100K", 10**5),
        ("1M", 10**6),
        ("10M", 10**7),
        ("100M", 10**8),
        ("1G", 10**9),
    ],
)
def test_wfm_size(si_unit: str, length: int, tmp_path: Path) -> None:
    """Test how different waveform sizes function efficiently."""
    if si_unit in {"1G"} and os.getenv("GITHUB_ACTIONS"):
        pytest.skip(f"Skipping {si_unit} test in GitHub Actions environment")

    waveform_path = tmp_path / f"test_length_{length}.wfm"

    # Generate data
    data = np.linspace(
        type_min(np.dtype(np.int16)), type_max(np.dtype(np.int16)), num=length, dtype=np.int16
    )

    waveform = AnalogWaveform()
    waveform.y_axis_values = data

    start_time = timeit.default_timer()
    write_file(waveform_path.as_posix(), waveform)
    print(
        f"Write Time without conversion {si_unit}: {round(timeit.default_timer() - start_time, 4)}"
    )

    start_time = timeit.default_timer()
    read_waveform: AnalogWaveform = read_file(waveform_path.as_posix())
    print(
        f"Read Time without conversion {si_unit}: {round(timeit.default_timer() - start_time, 4)}"
    )

    assert read_waveform.y_axis_values.shape[0] == waveform.y_axis_values.shape[0]


def test_invalid_inputs() -> None:
    """Test waveforms that have invalid values or formats."""
    waveform_dir = f"{Path(__file__).parent}/waveforms/invalid_waveforms"
    invalid_tekmeta = "invalid_tekmeta.wfm"
    with pytest.raises(
        IOError,
        match=r"Metadata unreadable, post-amble is formatted in a way that is not parseable.",
    ):
        read_file(f"{waveform_dir}/{invalid_tekmeta}")

    invalid_extensions = "invalid_extension.kkw"
    with pytest.raises(IOError, match=r"The .kkw extension cannot be read from."):
        read_file(f"{waveform_dir}/{invalid_extensions}")

    waveform = AnalogWaveform()
    with pytest.raises(IOError, match=r"The .kkw extension cannot be written to."):
        write_file(f"{waveform_dir}/{invalid_extensions}", waveform)

    invalid_format = "invalid_record_length.csv"
    with pytest.raises(
        IOError,
        match=r"No Record Length Provided in csv.",
    ):
        read_file(f"{waveform_dir}/{invalid_format}")

    invalid_format = "invalid_csv.csv"
    with pytest.raises(
        IOError,
        match=r"CSV data not parseable.",
    ):
        read_file(f"{waveform_dir}/{invalid_format}")
