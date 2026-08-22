# ruff: noqa: SLF001
"""Tests for FastFrameDigitalWaveform (Phase 3 / TekHSI digital FastFrame)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from tm_data_types import FastFrameDigitalWaveform, FrameTimingInfo
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform
from tm_data_types.datum.waveforms.digital_waveform import DigitalWaveform
from tm_data_types.helpers.enums import SummaryFrameType
from tm_data_types.io_factory_methods import read_file, write_file

if TYPE_CHECKING:
    from pathlib import Path


def _synthetic_digital_fastframe(
    *,
    num_frames: int = 4,
    record_length: int = 16,
    bitmask: int = 0x1,
) -> FastFrameDigitalWaveform:
    waveform = FastFrameDigitalWaveform.create_fastframe(
        num_frames,
        record_length,
        dtype=np.int8,
    )
    waveform.digital_bitmask = bitmask
    waveform.x_axis_spacing = 1e-9
    for index in range(num_frames):
        waveform.fill_frame(
            index,
            np.full(record_length, index + 1, dtype=np.int8),
        )
        waveform.frame_info.append(
            FrameTimingInfo(
                frame_index=index,
                time_offset=float(index) * 1e-6,
                gmt_sec=100 + index,
                fract_sec=0.0,
                real_point_offset=0,
                frame_duration_sec=record_length * waveform.x_axis_spacing,
            ),
        )
    return waveform


def test_create_fastframe_preallocates() -> None:
    waveform = FastFrameDigitalWaveform.create_fastframe(100, 2500, dtype=np.int8)
    assert waveform.is_fastframe
    assert waveform.num_frames == 100
    assert waveform._frame_data.shape == (100, 2500)


def test_fill_frame_and_frame_data_round_trip() -> None:
    waveform = _synthetic_digital_fastframe()
    expected = np.full(16, 3, dtype=np.int8)
    waveform.fill_frame(3, expected)
    assert np.array_equal(waveform.frame_data(3), expected)


def test_isinstance_digital_subclass() -> None:
    waveform = _synthetic_digital_fastframe()
    assert isinstance(waveform, FastFrameDigitalWaveform)
    assert isinstance(waveform, DigitalWaveform)
    assert not isinstance(waveform, AnalogWaveform)


def test_frame_returns_digital_waveform_with_bitstream() -> None:
    waveform = _synthetic_digital_fastframe(record_length=32)
    frame = waveform.frame(1)
    assert type(frame) is DigitalWaveform
    assert not isinstance(frame, FastFrameDigitalWaveform)
    assert frame.digital_bitmask == waveform.digital_bitmask
    bitstream = frame.get_nth_bitstream(0)
    assert len(bitstream) == frame.record_length


def test_frames_iterator() -> None:
    waveform = _synthetic_digital_fastframe(num_frames=3)
    pairs = list(waveform.frames())
    assert len(pairs) == 3
    assert all(isinstance(idx, int) and isinstance(frame, DigitalWaveform) for idx, frame in pairs)


def test_digital_bitmask_on_frame_view() -> None:
    waveform = _synthetic_digital_fastframe(bitmask=0x5)
    assert waveform.frame(0).digital_bitmask == 0x5


def test_per_frame_summary_flags_authoritative() -> None:
    waveform = _synthetic_digital_fastframe(num_frames=5)
    waveform.summary_frame_type = SummaryFrameType.SUMMARY_FRAME_AVERAGE
    waveform.per_frame_summary_authoritative = True
    assert waveform.summary_frame_index is None
    assert waveform.data_frame_count == 5


def test_per_frame_summary_flag_sets_index() -> None:
    waveform = _synthetic_digital_fastframe(num_frames=5)
    waveform.per_frame_summary_authoritative = True
    waveform.frame_info[2] = FrameTimingInfo(
        frame_index=2,
        time_offset=0.0,
        gmt_sec=0,
        fract_sec=0.0,
        real_point_offset=0,
        frame_duration_sec=1.0,
        is_summary_frame=True,
    )
    assert waveform.summary_frame_index == 2
    assert waveform.data_frame_count == 4
    assert waveform.is_summary_frame(2)


def test_single_frame_digital_passthrough() -> None:
    waveform = DigitalWaveform()
    waveform.y_axis_byte_values = np.array([1, 2, 3], dtype=np.int8)
    assert waveform.frame(0) is waveform
    with pytest.raises(ValueError):
        waveform.frame(1)


def test_phase1_create_fastframe_on_base_still_works() -> None:
    waveform = DigitalWaveform.create_fastframe(2, 8, dtype=np.int8)
    assert isinstance(waveform, DigitalWaveform)
    assert not isinstance(waveform, FastFrameDigitalWaveform)
    assert waveform.frame_count == 2


def test_ff_digital_programmatic_roundtrip(tmp_path: Path) -> None:
    """Programmatic digital FastFrame round-trips through WFM write/read."""
    output_path = tmp_path / "ff_digital_programmatic.wfm"
    waveform = FastFrameDigitalWaveform.create_fastframe(8, 64, dtype=np.int8)
    waveform.x_axis_spacing = 1e-9
    waveform.x_axis_units = "s"
    waveform.y_axis_units = "logic"
    for index in range(8):
        waveform.fill_frame(index, np.full(64, index + 1, dtype=np.int8))
        waveform.set_frame_timing(index, tt_offset=index * 1e-6, gmt_sec=100 + index)
    write_file(output_path.as_posix(), waveform)
    restored = read_file(output_path.as_posix())
    assert isinstance(restored, FastFrameDigitalWaveform)
    assert isinstance(restored, DigitalWaveform)
    assert restored.is_fastframe
    assert restored.frame_count == 8
    for index in range(8):
        assert np.array_equal(waveform.frame_data(index), restored.frame_data(index))
    assert restored.tt_offsets is not None
    assert np.allclose(waveform.tt_offsets, restored.tt_offsets)
    assert restored.frame_gmt_sec is not None
    assert np.array_equal(waveform.frame_gmt_sec, restored.frame_gmt_sec)
