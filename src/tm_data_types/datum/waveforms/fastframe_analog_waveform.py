"""FastFrame multi-frame analog waveform types and TekHSI-compatible API."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import numpy as np

from tm_data_types.datum.data_types import PossibleTypes, RawSample
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform
from tm_data_types.datum.waveforms.fastframe_common import (
    apply_wfm_summary_frame_flags,
    FastFrameMixin,
    FrameTimingInfo,
    summary_frame_type_from_wfm_value,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = [
    "FastFrameAnalogWaveform",
    "FrameTimingInfo",
    "apply_wfm_summary_frame_flags",
    "frame_info_from_wfm_timing",
    "summary_frame_type_from_wfm_value",
]


def _apply_frame_metadata(
    source: AnalogWaveform,
    dest: AnalogWaveform,
    frame_index: int,
) -> None:
    """Copy shared axis metadata and per-frame trigger index onto ``dest``."""
    dest.source_name = source.source_name
    dest.y_axis_spacing = source.y_axis_spacing
    dest.y_axis_offset = source.y_axis_offset
    dest.y_axis_units = source.y_axis_units
    dest.x_axis_spacing = source.x_axis_spacing
    dest.x_axis_units = source.x_axis_units
    if isinstance(source, FastFrameAnalogWaveform):
        dest.trigger_index = source._trigger_index_for_frame(frame_index)  # noqa: SLF001
    else:
        dest.trigger_index = source.trigger_index


class FastFrameAnalogWaveform(AnalogWaveform, FastFrameMixin):
    """Multi-frame oscilloscope acquisition with TekHSI-compatible frame access."""

    def __init__(self) -> None:
        """Initialize the FastFrame analog waveform and its multi-frame state."""
        super().__init__()
        self._init_fastframe_state()

    def __setattr__(self, key: str, value: Any) -> None:
        """Route FastFrame-specific attributes to their private storage."""
        if key == "_frame_data":
            self._invalidate_frame_data_views()
        if key in {"num_frames", "_frame_count"}:
            super().__setattr__("_frame_count", value)
            return
        if key == "current_frame_index":
            super().__setattr__("_current_frame", value)
            return
        super().__setattr__(key, value)

    def __iter__(self) -> Iterator[tuple[int, AnalogWaveform]]:
        """Iterate over ``(index, AnalogWaveform)`` pairs excluding the summary frame."""
        return self.frames(include_summary=False)

    @classmethod
    def create_fastframe(
        cls,
        frame_count: int,
        record_length: int,
        dtype: PossibleTypes = np.int16,
        precharge_length: int = 0,
        postcharge_length: int = 0,
        **kwargs: Any,
    ) -> FastFrameAnalogWaveform:
        """Pre-allocate a FastFrame waveform (returns ``FastFrameAnalogWaveform``)."""
        waveform = cls()
        waveform._frame_data = np.empty((frame_count, record_length), dtype=dtype)
        waveform._frame_count = frame_count
        waveform._current_frame = 0
        waveform._tt_offsets = np.zeros(frame_count, dtype=np.float64)
        waveform._frame_gmt_sec = np.zeros(frame_count, dtype=np.int64)
        waveform._frame_gmt_fract = np.zeros(frame_count, dtype=np.float64)
        waveform._precharge_length = precharge_length
        waveform._postcharge_length = postcharge_length
        if precharge_length:
            waveform._frame_precharge = np.zeros((frame_count, precharge_length), dtype=dtype)
        if postcharge_length:
            waveform._frame_postcharge = np.zeros((frame_count, postcharge_length), dtype=dtype)
        for key, val in kwargs.items():
            setattr(waveform, key, val)
        return waveform

    def _trigger_index_for_frame(self, index: int) -> float | None:
        for info in self.frame_info:
            if info.frame_index == index:
                if self.x_axis_spacing:
                    base = self.trigger_index or 0.0
                    return base + info.time_offset / self.x_axis_spacing
                return self.trigger_index
        return self.trigger_index

    def _build_frame_view(self, index: int, *, copy: bool = False) -> AnalogWaveform:
        backing = self._require_backing_frames()
        if index < 0 or index >= self.num_frames:
            msg = f"Frame {index} out of range [0, {self.num_frames})"
            raise IndexError(msg)

        raw = backing[index]
        if copy:
            raw = np.array(raw, copy=True)

        view = AnalogWaveform()
        _apply_frame_metadata(self, view, index)
        raw_sample = np.ndarray.__new__(RawSample, shape=raw.shape, dtype=raw.dtype, buffer=raw)
        object.__setattr__(view, "y_axis_values", raw_sample)
        return view

    def frame(self, index: int) -> AnalogWaveform:
        """Return a single-frame ``AnalogWaveform`` view for ``index``."""
        if not self.is_fastframe:
            if index == self.current_frame_index:
                return self
            msg = f"Single-frame waveform has no frame {index}"
            raise ValueError(msg)
        return self._build_frame_view(index)

    def get_summary_frame(self) -> AnalogWaveform:
        """Return the summary frame as an ``AnalogWaveform``."""
        summary_index = self.summary_frame_index
        if summary_index is None:
            msg = "Waveform has no summary frame"
            raise ValueError(msg)
        return self.frame(summary_index)

    def frame_array(self, index: int) -> np.ndarray:
        """Return normalized float physical values for ``index`` (TekHSI compat)."""
        return np.asarray(self.frame(index).normalized_vertical_values, dtype=np.float64)

    def iter_frame_arrays(
        self,
        *,
        include_summary: bool = False,
    ) -> Iterator[tuple[int, np.ndarray]]:
        """Yield ``(index, float_array)`` pairs (TekHSI compat)."""
        for index in range(self._frame_iteration_end(include_summary=include_summary)):
            yield index, self.frame_array(index)

    def frames(
        self,
        *,
        include_summary: bool = False,
        copy: bool = False,
    ) -> Iterator[tuple[int, AnalogWaveform]]:
        """Yield ``(index, AnalogWaveform)`` for each frame."""
        for index in range(self._frame_iteration_end(include_summary=include_summary)):
            yield index, self._build_frame_view(index, copy=copy)


def frame_info_from_wfm_timing(
    frame_index: int,
    tt_offset: float,
    gmt_sec: int,
    gmt_fract: float,
    record_length: int,
    x_axis_spacing: float,
    *,
    is_summary_frame: bool = False,
) -> FrameTimingInfo:
    """Build ``FrameTimingInfo`` from WFM ``UpdateSpecifications`` fields."""
    return FrameTimingInfo(
        frame_index=frame_index,
        time_offset=tt_offset,
        gmt_sec=gmt_sec,
        fract_sec=gmt_fract,
        real_point_offset=0,
        frame_duration_sec=record_length * x_axis_spacing,
        is_summary_frame=is_summary_frame,
    )
