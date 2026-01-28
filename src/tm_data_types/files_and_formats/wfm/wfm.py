"""The file formatting for a .wfm file."""

import struct

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, NoReturn, Optional, Tuple

import numpy as np

from bidict import bidict

from tm_data_types.datum.waveforms.waveform import Waveform, WaveformMetaInfo
from tm_data_types.files_and_formats.abstracted_file import AbstractedFile, DATUM_TYPE_VAR
from tm_data_types.files_and_formats.wfm.wfm_format import Endian, WfmFormat
from tm_data_types.helpers.byte_data_types import (
    Double,
    Float,
    Long,
    Short,
    SignedChar,
    String8,
    UnsignedChar,
    UnsignedLong,
    UnsignedLongLong,
)
from tm_data_types.helpers.enums import ByteOrderFormat, CurveFormatsVer3, VersionNumber


class WFMFile(AbstractedFile[DATUM_TYPE_VAR], ABC):
    """A generic .wfm file class."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    # a lookup for the byte formats provided by the .wfm file
    _ENDIAN_PREFIX_LOOKUP: ClassVar[Dict[str, Endian]] = {
        ByteOrderFormat.INTEL.value: Endian(
            struct=">",
            from_byte="little",
            format=ByteOrderFormat.INTEL.value,
        ),
        ByteOrderFormat.PPC.value: Endian(
            struct="<",
            from_byte="big",
            format=ByteOrderFormat.PPC.value,
        ),
    }

    # a lookup for np types to what's provided by the .wfm file
    _CURVE_FORMAT_LOOKUP = bidict(
        {
            np.dtype(Short.np_repr): CurveFormatsVer3.EXPLICIT_INT16,
            np.dtype(Long.np_repr): CurveFormatsVer3.EXPLICIT_INT32,
            np.dtype(UnsignedLong.np_repr): CurveFormatsVer3.EXPLICIT_UINT32,
            np.dtype(UnsignedLongLong.np_repr): CurveFormatsVer3.EXPLICIT_UINT64,
            np.dtype(Float.np_repr): CurveFormatsVer3.EXPLICIT_FP32,
            np.dtype(Double.np_repr): CurveFormatsVer3.EXPLICIT_FP64,
            np.dtype(UnsignedChar.np_repr): CurveFormatsVer3.EXPLICIT_UINT8,
            np.dtype(SignedChar.np_repr): CurveFormatsVer3.EXPLICIT_INT8,
        },
    )

    # a lookup for the meta info class to what's provided by the .wfm file
    _META_DATA_LOOKUP = bidict(
        {
            "waveform_label": "waveform_label",
            "y_offset": "yOffset",
            "y_position": "yPosition",
            "analog_thumbnail": "ANALOG_Thumbnail",
            "clipping_initialized": "clippingInitialized",
            "interpreter_factor": "interpFactor",
            "real_data_start_index": "realDataStartIndex",
        },
    )
    META_DATA_TYPE = WaveformMetaInfo
    DATUM_TYPE = Waveform

    ################################################################################################
    # Public Methods
    ################################################################################################

    # Reading
    def check_style(self) -> bool:
        """Check the style of the waveform data to see if it works in this format.

        Returns:
            A boolean indicating whether the format supports the data provided.
        """
        meta_data, _ = self._get_metadata_for_check_style()
        return self._check_metadata(meta_data)

    # Reading
    def read_datum(self) -> DATUM_TYPE_VAR:
        """Unpack a provided .wfm file.

        Returns:
            A waveform filled with information from the .wfm file.
        """
        # lookup the endian type
        (byte_order,) = struct.unpack(">2s", self.fd.read(2))

        if byte_order in self._ENDIAN_PREFIX_LOOKUP:
            endian_prefix = self._ENDIAN_PREFIX_LOOKUP[byte_order]
        else:
            msg = "Endian Format in wfm invalid."
            raise ValueError(msg)
        # figure out the version string
        version_value = String8.unpack(endian_prefix.struct, self.fd)
        version_number = VersionNumber(version_value)
        # create a format class and unpack the read data into it
        formatted_data = WfmFormat()
        formatted_data.unpack_wfm_file(endian_prefix, version_number, self.fd)

        waveform: DATUM_TYPE_VAR = self.DATUM_TYPE()  # pylint: disable=abstract-class-instantiated
        # Remap and separate known/unknown keys for meta_info
        remapped = self.META_DATA_TYPE.remap(
            self._META_DATA_LOOKUP.inverse, formatted_data.meta_data
        )

        # Convert bytes to strings for string-like metadata
        def convert_bytes_to_str(value):  # noqa: ANN001,ANN202
            if isinstance(value, bytes):
                try:
                    return value.decode("utf-8")
                except UnicodeDecodeError:
                    return value
            return value

        remapped = {k: convert_bytes_to_str(v) for k, v in remapped.items()}

        # Collect all annotated fields from the class and its parents
        known_fields = set()
        for cls in self.META_DATA_TYPE.__mro__:
            if hasattr(cls, "__annotations__"):
                known_fields.update(cls.__annotations__.keys())
        known_data = {k: v for k, v in remapped.items() if k in known_fields}
        extra_data = {k: v for k, v in remapped.items() if k not in known_fields}
        meta_data = self.META_DATA_TYPE(**known_data, extended_metadata=extra_data or None)
        if formatted_data.implicit_dimensions is not None:
            waveform.x_axis_units = formatted_data.implicit_dimensions.first.units
            waveform.x_axis_spacing = formatted_data.implicit_dimensions.first.scale
            waveform.trigger_index = (
                -formatted_data.implicit_dimensions.first.offset / waveform.x_axis_spacing
            )
        waveform.meta_info = meta_data

        self._format_to_waveform_vertical_values(waveform, formatted_data)

        # pylint: disable=unreachable
        return waveform

    # Writing
    def write_datum(self, waveform: Waveform) -> None:
        """Pack to a provided .wfm file.

        Args:
            waveform: The waveform to pack into the .wfm file.
        """
        # lookup the endian type and version number based on the provided product
        endian_prefix = self._ENDIAN_PREFIX_LOOKUP[self.product.value.byte_order.value]
        version_number = self.product.value.version

        # fill out a format class with the data written, then pack it
        formatted_data = WfmFormat()
        if waveform.meta_info:
            # Get all metadata, including extended metadata
            all_metadata = {}
            if waveform.meta_info.extended_metadata:
                all_metadata.update(waveform.meta_info.extended_metadata)
            # Add standard metadata, excluding extended_metadata field
            for key, value in waveform.meta_info.operable_metainfo().items():
                if key != "extended_metadata":
                    all_metadata[key] = value  # noqa: PERF403
            # Remap all metadata using the lookup table
            formatted_data.meta_data = self.META_DATA_TYPE.remap(
                self._META_DATA_LOOKUP,
                all_metadata,
            )
        else:
            formatted_data.meta_data = self.META_DATA_TYPE.remap(self._META_DATA_LOOKUP, {})
        self._waveform_vertical_values_to_format(waveform, formatted_data)

        # pylint: disable=unreachable
        if waveform.trigger_index is None:
            trigger_index = waveform.normalized_vertical_values.size / 2
        else:
            trigger_index = waveform.trigger_index

        if formatted_data.implicit_dimensions is None:
            formatted_data.setup_implicit_dimensions(
                units=waveform.x_axis_units,
                scale=waveform.x_axis_spacing,
                offset=-trigger_index * waveform.x_axis_spacing,
            )

        formatted_data.pack_wfm_file(endian_prefix, version_number, self.fd)

    ################################################################################################
    # Private Methods
    ################################################################################################

    def _get_metadata_for_check_style(
        self,
    ) -> Tuple[Optional[Dict[str, Long | Double | UnsignedLong]], Endian]:
        """Get the metadata from the waveform meta info class for the check_style() method."""
        # Read endian and version
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

        return meta_data, endian_prefix

    # Reading
    @staticmethod
    def _check_metadata(meta_data: Dict[str, Any]) -> bool:  # noqa: ARG004
        """Check if metadata can be used to construct a WaveformMetaInfo object."""
        try:
            # Just try to construct with empty known fields - we'll handle the rest in read_datum
            WaveformMetaInfo()
        except Exception:  # noqa: BLE001
            return False
        return True

    # Reading
    @abstractmethod
    def _format_to_waveform_vertical_values(
        self, waveform: Waveform, formatted_data: WfmFormat
    ) -> NoReturn:
        """Convert the data from a formatted data class to an analog waveform class.

        Args:
            waveform: The waveform object.
            formatted_data: The formatted data from the file.

        Returns:
            Returns an analog waveform created from the formatted data.
        """
        raise NotImplementedError

    # Writing
    @abstractmethod
    def _waveform_vertical_values_to_format(
        self, waveform: Waveform, formatted_data: WfmFormat
    ) -> NoReturn:
        """Convert the data from a waveform class to a formatted data class.

        Args:
            waveform: The waveform object.
            formatted_data: The formatted data from the file.

        Returns:
            Returns an analog waveform created from the formatted data.
        """
        raise NotImplementedError

    def remap(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remap the data to the correct format."""
        return self.remap_keys(data)

    def remap_keys(self, data: dict) -> dict:
        """Remap keys according to the lookup dictionary."""
        remapped = {}
        for key, value in data.items():
            if key in self._META_DATA_LOOKUP:
                remapped[self._META_DATA_LOOKUP[key]] = value
            else:
                remapped[key] = value
        return remapped
