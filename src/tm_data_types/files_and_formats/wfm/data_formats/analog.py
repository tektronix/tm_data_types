"""The functionality to read and write to a csv file when the waveform is analog."""

from typing import Any, Dict, Optional

import numpy as np

from tm_data_types.datum.data_types import RawSample
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform, AnalogWaveformMetaInfo
from tm_data_types.datum.waveforms.fastframe_analog_waveform import (
    apply_wfm_summary_frame_flags,
    FastFrameAnalogWaveform,
    frame_info_from_wfm_timing,
    summary_frame_type_from_wfm_value,
)
from tm_data_types.files_and_formats.wfm.wfm import WFMFile
from tm_data_types.files_and_formats.wfm.wfm_format import WfmFormat
from tm_data_types.helpers.byte_data_types import Short, UnsignedShort


class WaveformFileWFMAnalog(WFMFile[AnalogWaveform]):
    """Provides the methods of reading and writing to a .wfm file with an analog waveform."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    DATUM_TYPE = AnalogWaveform
    META_DATA_TYPE = AnalogWaveformMetaInfo

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize analog WFM reader/writer state."""
        super().__init__(*args, **kwargs)
        self._fastframe_read_result: Optional[FastFrameAnalogWaveform] = None

    ################################################################################################
    # Public Methods
    ################################################################################################

    def read_datum(self) -> AnalogWaveform:
        """Read an analog waveform, returning ``FastFrameAnalogWaveform`` for multi-frame files."""
        self._fastframe_read_result = None
        waveform = super().read_datum()
        if self._fastframe_read_result is not None:
            return self._fastframe_read_result
        return waveform

    ################################################################################################
    # Private Methods
    ################################################################################################

    # Reading
    def _check_metadata(self, meta_data: Dict[str, Any]) -> bool:  # pylint: disable=arguments-differ
        """Check if metadata indicates this is an analog waveform.

        Analog waveforms are identified as the default case when:
        - No digital probe fields are present
        - No IQ-specific metadata fields are present
        """
        digital_probe_fields = ["d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7"]
        if any(field in meta_data for field in digital_probe_fields):
            return False

        # Check if this is an IQ waveform (has IQ-specific metadata)
        iq_fields = [
            "IQ_centerFrequency",
            "IQ_fftLength",
            "IQ_rbw",
            "IQ_span",
            "IQ_windowType",
            "IQ_sampleRate",
        ]

        # If neither digital nor IQ, assume analog
        return not any(field in meta_data for field in iq_fields)

    # Reading
    def _format_to_waveform_vertical_values(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: AnalogWaveform,
        formatted_data: WfmFormat,
    ) -> None:
        """Convert the data from a formatted data class to an analog waveform class.

        Args:
            waveform: The analog waveform object.
            formatted_data: The formatted data from the file.

        Returns:
            Returns an analog waveform created from the formatted data.
        """
        if formatted_data.is_fastframe():
            self._fastframe_read_result = self._read_fastframe_waveform(waveform, formatted_data)
            return
        waveform.y_axis_values = formatted_data.curve_buffer
        if formatted_data.explicit_dimensions is not None:
            waveform.y_axis_offset = formatted_data.explicit_dimensions.first.offset
            waveform.y_axis_spacing = formatted_data.explicit_dimensions.first.scale
            waveform.y_axis_units = formatted_data.explicit_dimensions.first.units

    @staticmethod
    def _read_fastframe_waveform(  # pylint: disable=too-many-locals
        waveform: AnalogWaveform,
        formatted_data: WfmFormat,
    ) -> FastFrameAnalogWaveform:
        """Populate a FastFrameAnalogWaveform with all charge data and timing."""
        frame_count = formatted_data.fastframe_total_frames()
        record_length = len(formatted_data.curve_buffer)
        precharge_length = len(formatted_data.precharge_buffer)
        postcharge_length = len(formatted_data.postcharge_buffer)
        dtype = formatted_data.curve_buffer.dtype
        x_spacing = waveform.x_axis_spacing

        fastframe = FastFrameAnalogWaveform.create_fastframe(
            frame_count=frame_count,
            record_length=record_length,
            dtype=dtype,
            precharge_length=precharge_length,
            postcharge_length=postcharge_length,
        )
        fastframe.meta_info = waveform.meta_info
        fastframe.x_axis_units = waveform.x_axis_units
        fastframe.x_axis_spacing = waveform.x_axis_spacing
        fastframe.trigger_index = waveform.trigger_index
        fastframe.source_name = waveform.source_name

        summary_value = (
            int(formatted_data.summary_frame_type)
            if formatted_data.summary_frame_type is not None
            else None
        )
        fastframe.summary_frame_type = summary_frame_type_from_wfm_value(summary_value)

        fastframe.fill_frame(0, formatted_data.curve_buffer)
        if precharge_length and fastframe._frame_precharge is not None:  # noqa: SLF001
            fastframe._frame_precharge[0] = formatted_data.precharge_buffer  # noqa: SLF001
        if postcharge_length and fastframe._frame_postcharge is not None:  # noqa: SLF001
            fastframe._frame_postcharge[0] = formatted_data.postcharge_buffer  # noqa: SLF001

        for index, (precharge, charge, postcharge) in enumerate(
            formatted_data.fastframe_extra_blocks,
            start=1,
        ):
            fastframe.fill_frame(index, charge)
            if precharge_length and fastframe._frame_precharge is not None:  # noqa: SLF001
                fastframe._frame_precharge[index] = precharge  # noqa: SLF001
            if postcharge_length and fastframe._frame_postcharge is not None:  # noqa: SLF001
                fastframe._frame_postcharge[index] = postcharge  # noqa: SLF001

        frame_info = []
        if formatted_data.update_specifications is not None:
            spec = formatted_data.update_specifications
            fastframe.set_frame_timing(
                0,
                tt_offset=spec.trigger_time_offset,
                gmt_sec=int(spec.gmt_second),
                gmt_fract=spec.fractional_second,
            )
            frame_info.append(
                frame_info_from_wfm_timing(
                    0,
                    spec.trigger_time_offset,
                    int(spec.gmt_second),
                    spec.fractional_second,
                    record_length,
                    x_spacing,
                ),
            )
        for index, update_spec in enumerate(formatted_data.update_specs, start=1):
            fastframe.set_frame_timing(
                index,
                tt_offset=update_spec.trigger_time_offset,
                gmt_sec=int(update_spec.gmt_second),
                gmt_fract=update_spec.fractional_second,
            )
            frame_info.append(
                frame_info_from_wfm_timing(
                    index,
                    update_spec.trigger_time_offset,
                    int(update_spec.gmt_second),
                    update_spec.fractional_second,
                    record_length,
                    x_spacing,
                ),
            )
        fastframe.frame_info = frame_info
        apply_wfm_summary_frame_flags(frame_info, fastframe.summary_frame_type)

        if formatted_data.explicit_dimensions is not None:
            fastframe.y_axis_offset = formatted_data.explicit_dimensions.first.offset
            fastframe.y_axis_spacing = formatted_data.explicit_dimensions.first.scale
            fastframe.y_axis_units = formatted_data.explicit_dimensions.first.units

        return fastframe

    # Writing
    def _waveform_vertical_values_to_format(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: AnalogWaveform,
        formatted_data: WfmFormat,
    ) -> None:
        """Convert the data from an analog waveform class to a formatted data class.

        Args:
            waveform: The analog waveform object.
            formatted_data: The formatted data from the file.

        Returns:
            Returns an analog waveform created from the formatted data.
        """
        if waveform.is_fastframe:
            if (frame_data := waveform.all_frames) is None:
                msg = "FastFrame waveform is missing frame data."
                raise ValueError(msg)
            formatted_data.setup_explicit_dimensions(
                units=waveform.y_axis_units,
                scale=waveform.y_axis_spacing,
                offset=waveform.y_axis_offset,
                curve_format=self._CURVE_FORMAT_LOOKUP[np.dtype(frame_data.dtype)],
            )
            formatted_data.populate_fastframe_from_waveform(waveform)
            if isinstance(waveform, FastFrameAnalogWaveform):
                formatted_data.summary_frame_type = UnsignedShort(
                    waveform.summary_frame_type.value,
                )
            return

        if not isinstance(waveform.y_axis_values, RawSample):
            output_waveform = waveform.transform_to_type(Short)
        else:
            output_waveform = waveform
        formatted_data.setup_explicit_dimensions(
            units=output_waveform.y_axis_units,
            scale=output_waveform.y_axis_spacing,
            offset=output_waveform.y_axis_offset,
            curve_format=self._CURVE_FORMAT_LOOKUP[output_waveform.y_axis_values.dtype],
        )

        formatted_data.curve_buffer = output_waveform.y_axis_values
