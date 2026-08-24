"""Shared FastFrame types and mixin logic for analog and digital waveforms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from tm_data_types.helpers.enums import SummaryFrameType

if TYPE_CHECKING:
    import numpy as np


@dataclass
class FrameTimingInfo:
    """Per-frame timing metadata for a FastFrame acquisition."""

    frame_index: int
    time_offset: float
    gmt_sec: int
    fract_sec: float
    real_point_offset: int
    frame_duration_sec: float
    is_summary_frame: bool = False


class FastFrameMixin:  # pylint: disable=too-many-instance-attributes
    """Shared frame metadata, backing storage views, and summary-frame logic."""

    frame_info: list[FrameTimingInfo]
    summary_frame_type: SummaryFrameType
    load_timing: Any | None
    _stream_frames: list[np.ndarray] | None
    _frame_data_views: list[np.ndarray] | None
    per_frame_summary_authoritative: bool

    def _init_fastframe_state(self) -> None:
        self.frame_info = []
        self.summary_frame_type = SummaryFrameType.SUMMARY_FRAME_OFF
        self.load_timing = None
        self._stream_frames = None
        self._frame_data_views = None
        self.per_frame_summary_authoritative = False

    def _invalidate_frame_data_views(self) -> None:
        self._frame_data_views = None

    @property
    def num_frames(self) -> int:
        """Total number of frames (canonical name)."""
        return self._frame_count

    @num_frames.setter
    def num_frames(self, value: int) -> None:
        self._frame_count = value

    @property
    def current_frame_index(self) -> int:
        """Active frame index (canonical name)."""
        return self._current_frame

    @current_frame_index.setter
    def current_frame_index(self, value: int) -> None:
        self.current_frame = value

    @property
    def _backing_frames(self) -> list[np.ndarray] | None:
        if self._stream_frames is not None:
            return self._stream_frames
        if self._frame_data is not None:
            if self._frame_data_views is None:
                self._frame_data_views = list(self._frame_data)
            return self._frame_data_views
        return None

    @property
    def all_frames_loaded(self) -> bool:
        """True when backing frame data is present for every frame."""
        backing = self._backing_frames
        return backing is not None and len(backing) == self.num_frames

    @property
    def summary_frame_index(self) -> int | None:
        """Index of the summary frame, or ``None`` when no summary is present."""
        if not self.is_fastframe:
            return None

        if flagged := [info.frame_index for info in self.frame_info if info.is_summary_frame]:
            return flagged[0]

        if self.per_frame_summary_authoritative:
            return None

        if self.summary_frame_type == SummaryFrameType.SUMMARY_FRAME_OFF:
            return None

        return self.num_frames - 1

    @property
    def data_frame_count(self) -> int:
        """Number of data frames (excludes summary when present)."""
        if self.summary_frame_index is None:
            return self.num_frames
        return self.num_frames - 1

    def is_summary_frame(self, index: int) -> bool:
        """Return True when ``index`` is the summary frame."""
        for info in self.frame_info:
            if info.frame_index == index:
                return info.is_summary_frame
        summary_index = self.summary_frame_index
        return summary_index is not None and index == summary_index

    def _require_backing_frames(self) -> list[np.ndarray]:
        if (backing := self._backing_frames) is None:
            msg = (
                f"FastFrame capture has {self.num_frames} frames but raw data was not "
                "loaded during acquisition"
            )
            raise RuntimeError(msg)
        return backing

    def _frame_iteration_end(self, *, include_summary: bool) -> int:
        return self.num_frames if include_summary else self.data_frame_count


def apply_wfm_summary_frame_flags(
    frame_info: list[FrameTimingInfo],
    summary_frame_type: SummaryFrameType,
) -> None:
    """Mark the last frame as summary when WFM header indicates a summary frame."""
    if summary_frame_type == SummaryFrameType.SUMMARY_FRAME_OFF or not frame_info:
        return
    last = frame_info[-1]
    frame_info[-1] = FrameTimingInfo(
        frame_index=last.frame_index,
        time_offset=last.time_offset,
        gmt_sec=last.gmt_sec,
        fract_sec=last.fract_sec,
        real_point_offset=last.real_point_offset,
        frame_duration_sec=last.frame_duration_sec,
        is_summary_frame=True,
    )


def summary_frame_type_from_wfm_value(value: int | None) -> SummaryFrameType:
    """Map a WFM ``summary_frame_type`` integer to ``SummaryFrameType``."""
    if value is None:
        return SummaryFrameType.SUMMARY_FRAME_OFF
    try:
        return SummaryFrameType(value)
    except ValueError:
        return SummaryFrameType.SUMMARY_FRAME_OFF
