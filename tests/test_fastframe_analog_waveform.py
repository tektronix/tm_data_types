# ruff: noqa: SLF001
"""Tests for FastFrameAnalogWaveform (Phase 2 API)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tm_data_types import FastFrameAnalogWaveform, FrameTimingInfo, read_file
from tm_data_types.datum.data_types import RawSample
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform
from tm_data_types.datum.waveforms.fastframe_common import apply_wfm_summary_frame_flags
from tm_data_types.helpers.enums import SummaryFrameType

FF_FIXTURE = Path(__file__).resolve().parent / "waveforms/fastframe/FF5MhzX100From5Series.wfm"
FF_CORPUS = Path(__file__).resolve().parent.parent / "archive/test_wfms/FastFrame_waveforms"


def _synthetic_fastframe(
    *,
    num_frames: int = 4,
    record_length: int = 8,
    summary_type: SummaryFrameType = SummaryFrameType.SUMMARY_FRAME_OFF,
) -> FastFrameAnalogWaveform:
    waveform = FastFrameAnalogWaveform.create_fastframe(
        num_frames,
        record_length,
        dtype=np.int16,
    )
    waveform.y_axis_spacing = 0.01
    waveform.y_axis_offset = 0.0
    waveform.summary_frame_type = summary_type
    for index in range(num_frames):
        waveform.fill_frame(index, np.arange(record_length, dtype=np.int16) + index)
        waveform.frame_info.append(
            FrameTimingInfo(
                frame_index=index,
                time_offset=float(index) * 1e-6,
                gmt_sec=100 + index,
                fract_sec=0.1 * index,
                real_point_offset=0,
                frame_duration_sec=record_length * waveform.y_axis_spacing,
            ),
        )
    apply_wfm_summary_frame_flags(waveform.frame_info, summary_type)
    return waveform


def test_read_file_returns_fastframe_analog_waveform() -> None:
    if not FF_FIXTURE.exists():
        pytest.skip("FastFrame fixture missing")
    waveform = read_file(FF_FIXTURE.as_posix())
    assert isinstance(waveform, FastFrameAnalogWaveform)
    assert waveform.is_fastframe
    assert waveform.num_frames == 100
    assert len(waveform.frame_info) == 100


@pytest.mark.parametrize(
    "filename",
    [
        "FF5MhzX100From5Series.wfm",
        "FF1MX5005Series.wfm",
        "FF1MX1095Series.wfm",
    ],
)
def test_corpus_files_load_as_fastframe(filename: str) -> None:
    path = FF_CORPUS / filename
    if not path.exists():
        pytest.skip(f"Corpus file missing: {path}")
    waveform = read_file(path.as_posix())
    assert isinstance(waveform, FastFrameAnalogWaveform)
    assert waveform.is_fastframe
    assert waveform.all_frames_loaded


def test_single_frame_passthrough() -> None:
    waveform = AnalogWaveform()
    waveform.y_axis_values = np.array([1, 2, 3], dtype=np.int16)
    assert waveform.frame(0) is waveform
    with pytest.raises(ValueError):
        waveform.frame(1)


def test_frame_returns_analog_waveform_type() -> None:
    waveform = _synthetic_fastframe()
    frame = waveform.frame(1)
    assert type(frame) is AnalogWaveform
    assert not isinstance(frame, FastFrameAnalogWaveform)


def test_frame_y_axis_values_is_raw_sample_zero_copy() -> None:
    waveform = _synthetic_fastframe()
    backing = waveform._require_backing_frames()
    frame = waveform.frame(2)
    assert isinstance(frame.y_axis_values, RawSample)
    assert frame.y_axis_values.base is backing[2].base or frame.y_axis_values.base is backing[2]


def test_frame_array_matches_normalized() -> None:
    waveform = _synthetic_fastframe()
    assert np.allclose(
        waveform.frame_array(1),
        np.asarray(waveform.frame(1).normalized_vertical_values),
    )


def test_iter_yields_index_waveform_pairs() -> None:
    waveform = _synthetic_fastframe(num_frames=3)
    pairs = list(waveform)
    assert len(pairs) == 3
    assert all(isinstance(idx, int) and isinstance(frame, AnalogWaveform) for idx, frame in pairs)


def test_current_frame_and_frame_count_aliases() -> None:
    waveform = _synthetic_fastframe(num_frames=2)
    waveform.current_frame_index = 1
    assert waveform.current_frame == 1
    assert waveform.frame_count == waveform.num_frames == 2


def test_summary_frame_type_none_returns_no_index() -> None:
    waveform = _synthetic_fastframe(summary_type=SummaryFrameType.SUMMARY_FRAME_OFF)
    assert waveform.summary_frame_index is None
    assert waveform.data_frame_count == waveform.num_frames


def test_summary_frame_type_average_returns_last_index() -> None:
    waveform = _synthetic_fastframe(
        num_frames=5,
        summary_type=SummaryFrameType.SUMMARY_FRAME_AVERAGE,
    )
    assert waveform.summary_frame_index == 4
    assert waveform.data_frame_count == 4
    assert waveform.frame_info[-1].is_summary_frame is True
    summary = waveform.get_summary_frame()
    assert isinstance(summary, AnalogWaveform)


def test_per_frame_summary_authoritative_all_false() -> None:
    waveform = _synthetic_fastframe(
        num_frames=5,
        summary_type=SummaryFrameType.SUMMARY_FRAME_AVERAGE,
    )
    waveform.per_frame_summary_authoritative = True
    for index, info in enumerate(waveform.frame_info):
        waveform.frame_info[index] = FrameTimingInfo(
            frame_index=info.frame_index,
            time_offset=info.time_offset,
            gmt_sec=info.gmt_sec,
            fract_sec=info.fract_sec,
            real_point_offset=info.real_point_offset,
            frame_duration_sec=info.frame_duration_sec,
            is_summary_frame=False,
        )
    assert waveform.summary_frame_index is None
    assert waveform.data_frame_count == 5


def test_phase1_create_fastframe_on_base_still_works() -> None:
    waveform = AnalogWaveform.create_fastframe(2, 4, dtype=np.int16)
    assert isinstance(waveform, AnalogWaveform)
    assert not isinstance(waveform, FastFrameAnalogWaveform)
    assert waveform.frame_count == 2


def test_require_raw_frames_raises_when_unloaded() -> None:
    waveform = FastFrameAnalogWaveform()
    waveform.num_frames = 3
    with pytest.raises(RuntimeError):
        waveform.frame(0)


def test_copy_true_produces_independent_array() -> None:
    waveform = _synthetic_fastframe(num_frames=2)
    _, copied = next(waveform.frames(copy=True))
    backing = waveform._require_backing_frames()
    assert copied.y_axis_values.base is not backing[0].base
