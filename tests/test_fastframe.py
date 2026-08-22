# ruff: noqa: SLF001
"""Tests for FastFrame (.wfm) support."""

from __future__ import annotations

import struct

from pathlib import Path

import numpy as np
import pytest

from tm_data_types.datum.data_types import type_max
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform
from tm_data_types.datum.waveforms.fastframe_analog_waveform import FastFrameAnalogWaveform
from tm_data_types.files_and_formats.wfm.data_formats.analog import WaveformFileWFMAnalog
from tm_data_types.files_and_formats.wfm.wfm import WFMFile
from tm_data_types.files_and_formats.wfm.wfm_data_classes import (
    CurveInformation,
    WaveformHeader,
    WaveformStaticFileInfo,
)
from tm_data_types.files_and_formats.wfm.wfm_format import WfmFormat
from tm_data_types.helpers.byte_data_types import String8
from tm_data_types.helpers.enums import ByteOrderFormat, VersionNumber, WaveformTypes
from tm_data_types.io_factory_methods import read_file, write_file

FF_FIXTURE = Path(__file__).resolve().parent / "waveforms/fastframe/FF5MhzX100From5Series.wfm"
FF_FRAME_COUNT = 100
FF_RECORD_LENGTH = 2500
FF_EXTRA_METADATA = 99
FF_BYTES_PER_FRAME_BLOCK = 2564


def _unpack_wfm_file(path: Path) -> WfmFormat:
    """Unpack a .wfm file with the stream positioned after the version header."""
    formatted_data = WfmFormat()
    with path.open("rb") as filestream:
        (byte_order,) = struct.unpack(">2s", filestream.read(2))
        endian = WFMFile._ENDIAN_PREFIX_LOOKUP[byte_order]
        version_value = String8.unpack(endian.struct, filestream)
        formatted_data.unpack_wfm_file(endian, VersionNumber(version_value), filestream)
    return formatted_data


def _unpack_ff_reference() -> WfmFormat:
    """Unpack the reference FastFrame file using local WfmFormat."""
    return _unpack_wfm_file(FF_FIXTURE)


def _manual_read_frame_charge(frame_index: int) -> np.ndarray:
    """Read charge bytes for one frame directly from the reference file."""
    with FF_FIXTURE.open("rb") as filestream:
        (byte_order,) = struct.unpack(">2s", filestream.read(2))
        if byte_order == ByteOrderFormat.INTEL.value:
            endian = WFMFile._ENDIAN_PREFIX_LOOKUP[ByteOrderFormat.INTEL.value]
        else:
            endian = WFMFile._ENDIAN_PREFIX_LOOKUP[ByteOrderFormat.PPC.value]
        String8.unpack(endian.struct, filestream)
        file_info = WaveformStaticFileInfo.unpack(endian.struct, filestream, in_order=True)
        WaveformHeader.unpack(endian.struct, filestream, in_order=True)
        curve_info = CurveInformation(
            precharge_start_offset=0,
            data_start_offset=32,
            postcharge_start_offset=2532,
            postcharge_stop_offset=2564,
            end_of_curve_buffer_offset=2564,
            state_flags=0,
            check_sum_type=0,
            check_sum=0,
        )
        block_base = file_info.byte_offset + frame_index * FF_BYTES_PER_FRAME_BLOCK
        charge_offset = block_base + curve_info.data_start_offset
        filestream.seek(charge_offset)
        return np.fromfile(filestream, dtype=np.uint8, count=FF_RECORD_LENGTH)


# ---------------------------------------------------------------------------
# Phase 0 — parser
# ---------------------------------------------------------------------------


def test_ff_reference_file_unpacks_without_error() -> None:
    """Reference FastFrame file must unpack without struct errors."""
    formatted_data = _unpack_ff_reference()
    assert formatted_data.header is not None


def test_ff_reference_metadata_counts() -> None:
    """Metadata counts must match validated reference layout."""
    formatted_data = _unpack_ff_reference()
    assert formatted_data.header is not None
    assert formatted_data.file_info is not None
    assert len(formatted_data.update_specs) == FF_EXTRA_METADATA
    assert len(formatted_data.curve_specs) == FF_EXTRA_METADATA
    assert formatted_data.header.num_acquired_fast_frames == FF_FRAME_COUNT
    assert formatted_data.header.waveform_type == WaveformTypes.FASTFRAME.value


def test_ff_reference_record_length() -> None:
    """All frames share the same charge record length."""
    formatted_data = _unpack_ff_reference()
    assert formatted_data.curve_info is not None
    assert formatted_data.file_info is not None
    bytes_per_point = formatted_data.file_info.bytes_per_point
    frame0_length = (
        formatted_data.curve_info.postcharge_start_offset
        - formatted_data.curve_info.data_start_offset
    ) // bytes_per_point
    assert frame0_length == FF_RECORD_LENGTH
    assert len(formatted_data.curve_buffer) == FF_RECORD_LENGTH
    for curve_spec in formatted_data.curve_specs:
        frame_length = (
            curve_spec.postcharge_start_offset - curve_spec.data_start_offset
        ) // bytes_per_point
        assert frame_length == FF_RECORD_LENGTH


# ---------------------------------------------------------------------------
# Phase 1 — AnalogWaveform API
# ---------------------------------------------------------------------------


def test_analog_waveform_single_frame_defaults() -> None:
    """Single-frame waveforms use legacy defaults."""
    waveform = AnalogWaveform()
    assert waveform.frame_count == 1
    assert waveform.is_fastframe is False
    waveform.y_axis_values = np.array([1, 2, 3], dtype=np.int16)
    assert len(waveform.y_axis_values) == 3


def test_create_fastframe_preallocates_2d_buffer() -> None:
    """create_fastframe allocates one contiguous 2D buffer."""
    waveform = AnalogWaveform.create_fastframe(
        frame_count=FF_FRAME_COUNT,
        record_length=FF_RECORD_LENGTH,
        dtype=np.uint8,
    )
    assert waveform._frame_data is not None
    assert waveform._frame_data.shape == (FF_FRAME_COUNT, FF_RECORD_LENGTH)


def test_y_axis_values_returns_current_frame_view() -> None:
    """y_axis_values returns a view of the active frame."""
    waveform = AnalogWaveform.create_fastframe(2, 4, dtype=np.int16)
    waveform.fill_frame(0, np.array([1, 2, 3, 4], dtype=np.int16))
    waveform.fill_frame(1, np.array([9, 8, 7, 6], dtype=np.int16))
    waveform.current_frame = 1
    assert np.array_equal(waveform.y_axis_values, np.array([9, 8, 7, 6], dtype=np.int16))
    assert np.shares_memory(waveform._frame_data[1], waveform.frame_data(1))


def test_current_frame_setter_bounds() -> None:
    """current_frame rejects out-of-range indices."""
    waveform = AnalogWaveform.create_fastframe(3, 2, dtype=np.int16)
    waveform.current_frame = 2
    with pytest.raises(IndexError):
        waveform.current_frame = 3


def test_set_y_axis_values_rejected_on_fastframe() -> None:
    """Direct y_axis_values assignment is rejected on FastFrame waveforms."""
    waveform = AnalogWaveform.create_fastframe(2, 4, dtype=np.int16)
    with pytest.raises(ValueError, match="fill_frame"):
        waveform.y_axis_values = np.array([1, 2, 3, 4], dtype=np.int16)
    waveform.fill_frame(0, np.array([1, 2, 3, 4], dtype=np.int16))
    assert np.array_equal(waveform.frame_data(0), np.array([1, 2, 3, 4], dtype=np.int16))


def test_frame_data_and_iter() -> None:
    """frame_data and iteration expose all frames without changing current_frame."""
    waveform = AnalogWaveform.create_fastframe(100, 10, dtype=np.int16)
    for index in range(100):
        waveform.fill_frame(index, np.full(10, index, dtype=np.int16))
    waveform.current_frame = 0
    frames = list(waveform)
    assert len(frames) == 100
    assert np.array_equal(frames[49], np.full(10, 49, dtype=np.int16))
    assert waveform.current_frame == 0


def test_set_frame_timing() -> None:
    """Per-frame timing arrays are populated by set_frame_timing."""
    waveform = AnalogWaveform.create_fastframe(2, 4, dtype=np.int16)
    waveform.set_frame_timing(0, tt_offset=0.1, gmt_sec=100, gmt_fract=0.5)
    waveform.set_frame_timing(1, tt_offset=0.2, gmt_sec=200, gmt_fract=0.25)
    assert waveform.tt_offsets is not None
    assert waveform.tt_offsets[0] == pytest.approx(0.1)
    assert waveform.tt_offsets[1] == pytest.approx(0.2)
    assert waveform.frame_gmt_sec is not None
    assert waveform.frame_gmt_sec[1] == 200


# ---------------------------------------------------------------------------
# Phase 2 — read path
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not FF_FIXTURE.exists(), reason="FastFrame fixture missing")
def test_read_ff_reference_frame_count() -> None:
    """read_file loads all FastFrame frames."""
    waveform = read_file(FF_FIXTURE.as_posix())
    assert isinstance(waveform, FastFrameAnalogWaveform)
    assert waveform.is_fastframe
    assert waveform.frame_count == FF_FRAME_COUNT


@pytest.mark.skipif(not FF_FIXTURE.exists(), reason="FastFrame fixture missing")
def test_read_ff_reference_record_length() -> None:
    """Each frame has the expected record length."""
    waveform = read_file(FF_FIXTURE.as_posix())
    assert isinstance(waveform, FastFrameAnalogWaveform)
    assert len(waveform.y_axis_values) == FF_RECORD_LENGTH
    waveform.current_frame = 50
    assert len(waveform.y_axis_values) == FF_RECORD_LENGTH


@pytest.mark.skipif(not FF_FIXTURE.exists(), reason="FastFrame fixture missing")
def test_read_ff_reference_frame_data_not_identical() -> None:
    """Sequential frames contain different sample data."""
    waveform = read_file(FF_FIXTURE.as_posix())
    assert isinstance(waveform, FastFrameAnalogWaveform)
    assert not np.array_equal(waveform.frame_data(0), waveform.frame_data(1))


@pytest.mark.skipif(not FF_FIXTURE.exists(), reason="FastFrame fixture missing")
def test_read_ff_reference_frame49_matches_manual_parse() -> None:
    """Frame 49 matches a manual byte-level parse of the reference file."""
    waveform = read_file(FF_FIXTURE.as_posix())
    assert isinstance(waveform, FastFrameAnalogWaveform)
    expected = _manual_read_frame_charge(49)
    assert np.array_equal(np.asarray(waveform.frame_data(49), dtype=np.uint8), expected)


@pytest.mark.skipif(not FF_FIXTURE.exists(), reason="FastFrame fixture missing")
def test_read_ff_reference_timing_arrays_length() -> None:
    """Per-frame timing arrays cover every frame including frame 0."""
    waveform = read_file(FF_FIXTURE.as_posix())
    assert isinstance(waveform, FastFrameAnalogWaveform)
    assert waveform.tt_offsets is not None
    assert len(waveform.tt_offsets) == FF_FRAME_COUNT


def test_read_single_frame_regression(tmp_path: Path) -> None:
    """Single-frame write/read is unchanged."""
    waveform_path = tmp_path / "single.wfm"
    values = np.array([10, 11, 12], dtype=np.int16)
    waveform = AnalogWaveform()
    waveform.y_axis_values = values
    with WaveformFileWFMAnalog(waveform_path.as_posix(), "wb+") as wfm_file:
        wfm_file.write_datum(waveform)
    read_waveform = read_file(waveform_path.as_posix())
    assert isinstance(read_waveform, AnalogWaveform)
    assert read_waveform.frame_count == 1
    assert not read_waveform.is_fastframe
    assert np.array_equal(read_waveform.y_axis_values, values)


# ---------------------------------------------------------------------------
# Phase 3 — write path
# ---------------------------------------------------------------------------


def test_write_fastframe_header_fields(tmp_path: Path) -> None:
    """Written FastFrame files carry correct header fields."""
    output_path = tmp_path / "synthetic_ff.wfm"
    waveform = AnalogWaveform.create_fastframe(10, 100, dtype=np.uint8, source_name="CH1")
    for index in range(10):
        waveform.fill_frame(index, np.full(100, index, dtype=np.uint8))
        waveform.set_frame_timing(index, tt_offset=float(index))
    write_file(output_path.as_posix(), waveform)
    formatted_data = _unpack_wfm_file(output_path)
    assert formatted_data.header is not None
    assert formatted_data.file_info is not None
    assert formatted_data.header.waveform_type == WaveformTypes.FASTFRAME.value
    assert formatted_data.header.num_acquired_fast_frames == 10
    assert formatted_data.file_info.number_of_frames == 9


def test_write_fastframe_metadata_batch_layout(tmp_path: Path) -> None:
    """FastFrame metadata uses batch layout: update specs then curve specs."""
    output_path = tmp_path / "synthetic_ff_meta.wfm"
    waveform = AnalogWaveform.create_fastframe(5, 50, dtype=np.uint8)
    for index in range(5):
        waveform.fill_frame(index, np.zeros(50, dtype=np.uint8))
    write_file(output_path.as_posix(), waveform)
    formatted_data = _unpack_wfm_file(output_path)
    assert len(formatted_data.update_specs) == 4
    assert len(formatted_data.curve_specs) == 4


def test_write_fastframe_curve_byte_size(tmp_path: Path) -> None:
    """Curve region size matches per-frame block layout."""
    output_path = tmp_path / "synthetic_ff_curve.wfm"
    pre_len = 32
    post_len = 32
    waveform = AnalogWaveform.create_fastframe(
        10,
        100,
        dtype=np.uint8,
        precharge_length=pre_len,
        postcharge_length=post_len,
    )
    for index in range(10):
        waveform.fill_frame(index, np.zeros(100, dtype=np.uint8))
    write_file(output_path.as_posix(), waveform)
    block_size = pre_len + 100 + post_len
    formatted_data = _unpack_wfm_file(output_path)
    assert formatted_data.file_info is not None
    curve_region = 10 * block_size
    unpacked_size = (
        len(formatted_data.precharge_buffer)
        + len(formatted_data.curve_buffer)
        + len(formatted_data.postcharge_buffer)
    )
    for precharge, charge, postcharge in formatted_data.fastframe_extra_blocks:
        unpacked_size += len(precharge) + len(charge) + len(postcharge)
    assert unpacked_size == curve_region


def test_write_single_frame_regression(tmp_path: Path) -> None:
    """Single-frame write path is unchanged after FastFrame write support."""
    waveform_path = tmp_path / "single_write.wfm"
    values = np.array([1, 2, 3, 4], dtype=np.int16)
    waveform = AnalogWaveform()
    waveform.y_axis_values = values
    write_file(waveform_path.as_posix(), waveform)
    read_waveform = read_file(waveform_path.as_posix())
    assert np.array_equal(read_waveform.y_axis_values, values)


# ---------------------------------------------------------------------------
# Phase 4 — round-trip
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not FF_FIXTURE.exists(), reason="FastFrame fixture missing")
def test_ff_roundtrip_all_frames(tmp_path: Path) -> None:
    """Reference file round-trips all frame charge data."""
    original = read_file(FF_FIXTURE.as_posix())
    assert isinstance(original, AnalogWaveform)
    output_path = tmp_path / "ff_roundtrip.wfm"
    write_file(output_path.as_posix(), original)
    restored = read_file(output_path.as_posix())
    assert isinstance(restored, AnalogWaveform)
    assert restored.frame_count == original.frame_count
    for index in range(original.frame_count):
        assert np.array_equal(original.frame_data(index), restored.frame_data(index))


@pytest.mark.skipif(not FF_FIXTURE.exists(), reason="FastFrame fixture missing")
def test_ff_roundtrip_timing(tmp_path: Path) -> None:
    """Reference file round-trips per-frame timing arrays."""
    original = read_file(FF_FIXTURE.as_posix())
    assert isinstance(original, AnalogWaveform)
    output_path = tmp_path / "ff_roundtrip_timing.wfm"
    write_file(output_path.as_posix(), original)
    restored = read_file(output_path.as_posix())
    assert isinstance(restored, AnalogWaveform)
    assert original.tt_offsets is not None
    assert restored.tt_offsets is not None
    assert np.array_equal(original.tt_offsets, restored.tt_offsets)
    assert original.frame_gmt_sec is not None
    assert restored.frame_gmt_sec is not None
    assert np.array_equal(original.frame_gmt_sec, restored.frame_gmt_sec)


def test_ff_programmatic_roundtrip(tmp_path: Path) -> None:
    """Programmatic FastFrame round-trips through write/read."""
    output_path = tmp_path / "ff_programmatic.wfm"
    waveform = AnalogWaveform.create_fastframe(8, 64, dtype=np.int16)
    for index in range(8):
        waveform.fill_frame(index, np.full(64, index * 10, dtype=np.int16))
        waveform.set_frame_timing(index, tt_offset=index * 1e-6)
    write_file(output_path.as_posix(), waveform)
    restored = read_file(output_path.as_posix())
    assert isinstance(restored, AnalogWaveform)
    assert restored.frame_count == 8
    for index in range(8):
        assert np.array_equal(waveform.frame_data(index), restored.frame_data(index))


def _build_ten_mhz_sine_fastframe(
    frame_count: int,
    record_length: int,
    cycles_per_frame: float,
    frequency_hz: float,
    noise_fraction: float = 0.03,
    seed: int = 0,
) -> AnalogWaveform:
    """Build a FastFrame waveform with a multi-cycle sine plus noise on every frame."""
    samples_per_cycle = record_length / cycles_per_frame
    x_axis_spacing = 1.0 / (samples_per_cycle * frequency_hz)
    y_axis_spacing = 1.0 / type_max(np.dtype(np.int16))
    amplitude = type_max(np.dtype(np.int16))
    noise_sigma = noise_fraction * amplitude

    waveform = AnalogWaveform.create_fastframe(
        frame_count=frame_count,
        record_length=record_length,
        dtype=np.int16,
        source_name="CH1",
        x_axis_spacing=x_axis_spacing,
        y_axis_spacing=y_axis_spacing,
        y_axis_units="V",
        x_axis_units="s",
        trigger_index=record_length / 2,
    )

    sample_indices = np.arange(record_length, dtype=np.float64)
    phase = 2.0 * np.pi * cycles_per_frame * sample_indices / record_length
    sine_frame = (np.sin(phase) * amplitude).astype(np.float64)

    for frame_idx in range(frame_count):
        rng = np.random.default_rng(seed + frame_idx)
        noise = rng.normal(0.0, noise_sigma, record_length)
        frame = np.clip(sine_frame + noise, -amplitude, amplitude).astype(np.int16)
        waveform.fill_frame(frame_idx, frame)
        waveform.set_frame_timing(frame_idx, tt_offset=frame_idx * x_axis_spacing)

    return waveform


def test_export_ff_ten_mhz_sine_waveform(tmp_path: Path) -> None:
    """Write 250-frame FastFrame export: 10 MHz sine, 8 cycles, 10K samples per frame."""
    frame_count = 250
    record_length = 10_000
    cycles_per_frame = 8.0
    frequency_hz = 10e6

    waveform = _build_ten_mhz_sine_fastframe(
        frame_count=frame_count,
        record_length=record_length,
        cycles_per_frame=cycles_per_frame,
        frequency_hz=frequency_hz,
    )

    export_path = tmp_path / "export_ff.wfm"
    write_file(export_path.as_posix(), waveform)
    assert export_path.exists()

    restored = read_file(export_path.as_posix())
    assert isinstance(restored, AnalogWaveform)
    assert restored.is_fastframe
    assert restored.frame_count == frame_count
    assert len(restored.y_axis_values) == record_length
    assert not np.array_equal(restored.frame_data(0), restored.frame_data(1))

    for index in range(frame_count):
        assert np.array_equal(waveform.frame_data(index), restored.frame_data(index))

    samples_per_cycle = record_length / cycles_per_frame
    expected_x_spacing = 1.0 / (samples_per_cycle * frequency_hz)
    assert restored.x_axis_spacing == pytest.approx(expected_x_spacing)

    unpacked = _unpack_wfm_file(export_path)
    assert unpacked.header is not None
    assert unpacked.header.num_acquired_fast_frames == frame_count
    assert unpacked.header.waveform_type == WaveformTypes.FASTFRAME.value
    assert len(unpacked.curve_buffer) == record_length
