"""The functionality to read and write to a csv file when the waveform is digital."""

import struct

from typing import Any, Dict, Optional

import numpy as np

from tm_data_types.datum.data_types import RawSample
from tm_data_types.datum.waveforms.digital_waveform import (
    DigitalWaveform,
    DigitalWaveformMetaInfo,
)
from tm_data_types.datum.waveforms.fastframe_analog_waveform import (
    frame_info_from_wfm_timing,
    summary_frame_type_from_wfm_value,
)
from tm_data_types.datum.waveforms.fastframe_common import apply_wfm_summary_frame_flags
from tm_data_types.datum.waveforms.fastframe_digital_waveform import FastFrameDigitalWaveform
from tm_data_types.files_and_formats.wfm.wfm import WFMFile
from tm_data_types.files_and_formats.wfm.wfm_data_classes import (
    WaveformHeader,
    WaveformStaticFileInfo,
)
from tm_data_types.files_and_formats.wfm.wfm_format import WfmFormat
from tm_data_types.helpers.byte_data_types import SignedChar, String8, UnsignedLong, UnsignedShort
from tm_data_types.helpers.enums import DataTypes, VersionNumber


class WaveformFileWFMDigital(WFMFile[DigitalWaveform]):
    """Provides the methods of reading and writing to a .wfm file with a digital waveform."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    _META_DATA_LOOKUP = WFMFile.update_bidict(
        WFMFile._META_DATA_LOOKUP,  # noqa: SLF001
        {
            "digital_probe_0_state": "d0",
            "digital_probe_1_state": "d1",
            "digital_probe_2_state": "d2",
            "digital_probe_3_state": "d3",
            "digital_probe_4_state": "d4",
            "digital_probe_5_state": "d5",
            "digital_probe_6_state": "d6",
            "digital_probe_7_state": "d7",
        },
    )
    DATUM_TYPE = DigitalWaveform
    META_DATA_TYPE = DigitalWaveformMetaInfo

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize digital WFM reader/writer state."""
        super().__init__(*args, **kwargs)
        self._fastframe_read_result: Optional[FastFrameDigitalWaveform] = None

    ################################################################################################
    # Public Methods
    ################################################################################################

    def read_datum(self) -> DigitalWaveform:
        """Read a digital waveform, returning ``FastFrameDigitalWaveform`` for multi-frame files."""
        self._fastframe_read_result = None
        waveform = super().read_datum()
        if self._fastframe_read_result is not None:
            return self._fastframe_read_result
        return waveform

    # Reading
    def check_style(self) -> bool:
        """Check the style of the waveform data to see if it works in this format.

        Checks metadata first, and if metadata is empty, checks the header's data_type field.

        Returns:
            A boolean indicating whether the format supports the data provided.
        """
        # Read endian and version (same as parent)
        (byte_order,) = struct.unpack(">2s", self.fd.read(2))
        if byte_order in self._ENDIAN_PREFIX_LOOKUP:
            endian_prefix = self._ENDIAN_PREFIX_LOOKUP[byte_order]
        else:
            self.fd.seek(0)
            msg = "Endian Format in wfm invalid."
            raise ValueError(msg)

        version_number = String8.unpack(endian_prefix.struct, self.fd)
        enum_version_num = VersionNumber(version_number)

        # Seek out the tekmeta
        self.fd.seek(11)
        curve_local = UnsignedLong.unpack(endian_prefix.struct, self.fd)
        self.fd.seek(curve_local - 5 + (20 if enum_version_num == VersionNumber.THREE else 0))

        # Parse metadata
        meta_data = WfmFormat.parse_tekmeta(endian_prefix, self.fd)
        self.fd.seek(0)

        # First try standard metadata check
        if self._check_metadata(meta_data):
            return True

        # If metadata is empty, check header data_type
        if not meta_data:
            try:
                # File structure: [endian(2)][version(8)][file_info][header]...
                # We're at position 0, need to skip endian and version (10 bytes total)
                # Then read file_info and header
                self.fd.seek(10)  # Skip endian (2) + version (8)
                WaveformStaticFileInfo.unpack(endian_prefix.struct, self.fd, in_order=True)
                header = WaveformHeader.unpack(endian_prefix.struct, self.fd, in_order=True)
                # Check if data_type indicates digital
                if header.data_type == DataTypes.DIGITAL.value:
                    self.fd.seek(0)
                    return True
            except (OSError, struct.error, ValueError, TypeError):
                # If we can't read the header, fall through to return False
                pass
            finally:
                self.fd.seek(0)

        return False

    ################################################################################################
    # Private Methods
    ################################################################################################

    # Reading
    def _check_metadata(self, meta_data: Dict[str, Any]) -> bool:  # pylint: disable=arguments-differ
        """Check if metadata indicates this is a digital waveform.

        Digital waveforms are identified by the presence of any of the following fields:
        - "d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7"

        Args:
            meta_data: A dictionary containing metadata to check.

        Returns:
            True if the metadata indicates a digital waveform, False otherwise.
        """
        digital_probe_fields = ["d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7"]
        return any(field in meta_data for field in digital_probe_fields)

    # Reading
    def _format_to_waveform_vertical_values(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: DigitalWaveform,
        formatted_data: WfmFormat,
    ) -> None:
        """Convert the data from a formatted data class to a digital waveform class.

        Args:
            waveform: The digital waveform object.
            formatted_data: The formatted data from the file.

        Returns:
            Returns a digital waveform created from the formatted data.
        """
        if formatted_data.is_fastframe():
            self._fastframe_read_result = self._read_fastframe_waveform(waveform, formatted_data)
            return
        waveform.y_axis_byte_values = formatted_data.curve_buffer
        if formatted_data.explicit_dimensions is not None:
            waveform.y_axis_units = formatted_data.explicit_dimensions.first.units

    @staticmethod
    def _read_fastframe_waveform(  # pylint: disable=too-many-locals
        waveform: DigitalWaveform,
        formatted_data: WfmFormat,
    ) -> FastFrameDigitalWaveform:
        """Populate a FastFrameDigitalWaveform with all charge data and timing."""
        frame_count = formatted_data.fastframe_total_frames()
        record_length = len(formatted_data.curve_buffer)
        precharge_length = len(formatted_data.precharge_buffer)
        postcharge_length = len(formatted_data.postcharge_buffer)
        dtype = formatted_data.curve_buffer.dtype
        x_spacing = waveform.x_axis_spacing

        fastframe = FastFrameDigitalWaveform.create_fastframe(
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
            fastframe.y_axis_units = formatted_data.explicit_dimensions.first.units

        return fastframe

    # Writing
    def _waveform_vertical_values_to_format(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
        waveform: DigitalWaveform,
        formatted_data: WfmFormat,
    ) -> None:
        """Convert the data from a digital waveform class to a formatted data class.

        Args:
            waveform: The digital waveform object.
            formatted_data: The formatted data from the file.

        Returns:
            Returns a digital waveform created from the formatted data.
        """
        if waveform.is_fastframe:
            if (frame_data := waveform.all_frames) is None:
                msg = "FastFrame waveform is missing frame data."
                raise ValueError(msg)
            formatted_data.setup_explicit_dimensions(
                units=waveform.y_axis_units,
                curve_format=self._CURVE_FORMAT_LOOKUP[np.dtype(frame_data.dtype)],
            )
            formatted_data.populate_fastframe_from_waveform(waveform)
            if isinstance(waveform, FastFrameDigitalWaveform):
                formatted_data.summary_frame_type = UnsignedShort(
                    waveform.summary_frame_type.value,
                )
            if waveform.trigger_index is None:
                trigger_index = frame_data.shape[1] / 2
            else:
                trigger_index = waveform.trigger_index
            formatted_data.setup_implicit_dimensions(
                units=waveform.x_axis_units,
                scale=waveform.x_axis_spacing,
                offset=-trigger_index * waveform.x_axis_spacing,
            )
            formatted_data.setup_header(data_type=DataTypes.DIGITAL)
            return

        explicit_data = RawSample(waveform.y_axis_byte_values, as_type=SignedChar)

        formatted_data.setup_explicit_dimensions(
            units=waveform.y_axis_units,
            curve_format=self._CURVE_FORMAT_LOOKUP[explicit_data.dtype],
        )
        formatted_data.curve_buffer = explicit_data
        formatted_data.setup_implicit_dimensions(
            units=waveform.x_axis_units,
            scale=waveform.x_axis_spacing,
            offset=-waveform.trigger_index * waveform.x_axis_spacing,
        )
        formatted_data.setup_header(data_type=DataTypes.DIGITAL)
