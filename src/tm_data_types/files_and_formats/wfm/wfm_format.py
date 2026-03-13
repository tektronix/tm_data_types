# pylint: disable=too-many-lines
# pyright: reportArgumentType=false
"""A class which hosts a readable representation of the format information in a .wfm file."""

import contextlib
import struct

from dataclasses import dataclass, replace
from typing import (
    Any,
    Dict,
    Generic,
    get_args,
    List,
    Optional,
    TextIO,
    Tuple,
    Type,
    TYPE_CHECKING,
    TypeVar,
)

import numpy as np

from numba import njit
from numpy import ndarray

from tm_data_types.files_and_formats.wfm.wfm_data_classes import (
    CurveInformation,
    DimensionsUserView,
    DimensionsUserViewVer3,
    DimensionsUserViewVer12,
    ExplicitDimensions,
    ImplicitDimensions,
    PixMap,
    TimeBaseInformation,
    UpdateSpecifications,
    WaveformHeader,
    WaveformStaticFileInfo,
)
from tm_data_types.helpers.byte_data_class import StructuredInfo
from tm_data_types.helpers.byte_data_types import (
    ByteData,
    Char,
    Double,
    Float,
    Long,
    Short,
    String,
    String8,
    UnsignedChar,
    UnsignedLong,
    UnsignedLongLong,
    UnsignedShort,
)
from tm_data_types.helpers.enums import (
    BaseTypes,
    ChecksumType,
    CurveFormatsVer3,
    DataTypes,
    DSYFormat,
    StorageTypes,
    SummaryFrameType,
    SweepTypes,
    VersionNumber,
    WaveformDimension,
    WaveformTypes,
)
from tm_data_types.helpers.instrument_series import Endian

if TYPE_CHECKING:
    from collections.abc import Callable

T1 = TypeVar("T1")  # pylint: disable=invalid-name
T2 = TypeVar("T2")  # pylint: disable=invalid-name


@dataclass
class Dimension(Generic[T1, T2]):
    """A feature that has two dimensions, used within wfm formatting."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    first: T1
    second: Optional[T2]

    ################################################################################################
    # Public Methods
    ################################################################################################

    def get_value_summation(self) -> int:
        """Summate the byte values within the dimensions.

        Returns:
            The summation of each byte in the two features.
        """
        return self.first.get_value_summation() + self.second.get_value_summation()

    def get_cls_length(self) -> int:
        """Summate the byte length within the dimensions.

        Returns:
            The summation of each byte length in the two features.
        """
        return self.first.get_cls_length() + self.second.get_cls_length()


@njit(cache=True)
def calculate_checksum(value: ndarray) -> int:
    """Calculate the byte checksum for the np arrays using numba.

    Returns:
        The summation of all byte values in the numpy array
    """
    # this is the fastest possible summation of an np array
    # we view the buffer contents in a byte format. add reduce is called to
    # reduce its summation overhead and is used with an expectant uint64 output,
    # allowing for the uint8s to be summed
    # without the extra bits needed for each value. Because the buffer is contiguous,
    # the instances memorypoint is accessed, and np summation runs at c speed,
    # this is much faster than the inbuilt python sum. This is then converted to an int.
    return int(np.sum(value.view(np.uint8), dtype=np.uint64))


class WfmFormat:  # pylint: disable=too-many-instance-attributes
    """The Tektronix wfm file format."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    file_info: Optional[WaveformStaticFileInfo] = None
    header: Optional[WaveformHeader] = None
    summary_frame_type: Optional[UnsignedShort] = None
    pixel_map: Optional[PixMap] = None
    explicit_dimensions: Optional[Dimension[ExplicitDimensions, ExplicitDimensions]] = None
    explicit_user_view: Optional[Dimension[DimensionsUserView, DimensionsUserView]] = None
    implicit_dimensions: Optional[Dimension[ImplicitDimensions, ImplicitDimensions]] = None
    implicit_user_view: Optional[Dimension[DimensionsUserView, DimensionsUserView]] = None
    time_info: Optional[Dimension[TimeBaseInformation, TimeBaseInformation]] = None
    update_specifications: Optional[UpdateSpecifications] = None
    curve_info: Optional[CurveInformation] = None
    update_specs: List[UpdateSpecifications] = []  # noqa: RUF012
    curve_specs: List[CurveInformation] = []  # noqa: RUF012
    precharge_buffer: np.ndarray = np.empty(0)
    curve_buffer: np.ndarray = np.empty(0)
    postcharge_buffer: np.ndarray = np.empty(0)
    file_checksum: Optional[UnsignedLongLong] = None
    meta_data: Dict[str, str | Double | Long | UnsignedLong] = {}  # noqa: RUF012

    # Reading
    def unpack_wfm_file(
        self,
        endian: Endian,
        version_number: VersionNumber,
        filestream: TextIO,
    ) -> None:
        """Read the waveform file and unpack all the data into the enforced type data classes.

        Args:
            endian: The Endianness of the waveform format (INTEL OR PPC).
            version_number: The version number that was provided (depends on device).
            filestream: The filestream that will be written to.
        """
        self.file_info = WaveformStaticFileInfo.unpack(endian.struct, filestream, in_order=True)

        self.header = WaveformHeader.unpack(endian.struct, filestream, in_order=True)
        if version_number != VersionNumber.ONE:
            self.summary_frame_type = UnsignedShort.unpack(endian.struct, filestream)
        self.pixel_map = PixMap.unpack(endian.struct, filestream, in_order=True)

        if version_number == VersionNumber.THREE:
            dimension_view = DimensionsUserViewVer3
        else:
            dimension_view = DimensionsUserViewVer12

        self.explicit_dimensions, self.explicit_user_view = self._unpack_data(
            ExplicitDimensions,
            dimension_view,
            endian,
            filestream,
        )
        self.implicit_dimensions, self.implicit_user_view = self._unpack_data(
            ImplicitDimensions,
            dimension_view,
            endian,
            filestream,
        )
        self.time_info = self._unpack_twice(TimeBaseInformation, endian, filestream)
        self.update_specifications = UpdateSpecifications.unpack(
            endian.struct,
            filestream,
            in_order=True,
        )
        self.curve_info = CurveInformation.unpack(endian.struct, filestream, in_order=True)
        self.update_specs, self.curve_specs = self._get_fast_frame_information(endian, filestream)
        self.precharge_buffer, self.curve_buffer, self.postcharge_buffer = (
            self._get_curve_information(filestream)
        )
        with contextlib.suppress(struct.error):
            self.file_checksum = UnsignedLongLong.unpack(endian.struct, filestream)
        self.meta_data = self.parse_tekmeta(endian, filestream)

    @staticmethod
    def parse_tekmeta(  # pylint: disable=too-many-locals
        endian: Endian,
        filestream: TextIO,
    ) -> Optional[Dict[str, Long | Double | UnsignedLong]]:
        """Parse the metadata from the eof.

        Args:
            endian: The Endianness of the waveform format (INTEL OR PPC).
            filestream: The filestream that will be written to.
        """
        tek_meta_indicator = {
            2: Long,
            3: Double,
            4: UnsignedLong,
        }

        meta_data = {}

        # Store current position
        current_pos = filestream.tell()

        # Scan forward for tekmeta! marker
        chunk_size = 1024  # Read in chunks to be efficient
        while chunk := filestream.read(chunk_size):  # End of file
            # Look for tekmeta! in the chunk
            if (marker_pos := chunk.find(b"tekmeta!")) != -1:
                # Found the marker, adjust file position to start of marker
                filestream.seek(current_pos + marker_pos)
                break

            # If we didn't find it in this chunk, move forward
            current_pos = filestream.tell()

            # If we're near the end of the file, read smaller chunks
            if len(chunk) < chunk_size:
                break

        try:
            tek_meta = String8.unpack(endian.struct, filestream)
        except struct.error:
            return {}

        try:
            if tek_meta == b"tekmeta!":
                element_count = UnsignedLong.unpack(endian.struct, filestream)
                for _ in range(element_count):
                    key_size = UnsignedLong.unpack(endian.struct, filestream)
                    (key,) = struct.unpack(f"{endian.struct}{key_size}s", filestream.read(key_size))
                    type_indicator = int.from_bytes(
                        Char.unpack(endian.struct, filestream),
                        "little",
                    )
                    if type_indicator == 1:
                        value_size = UnsignedLong.unpack(endian.struct, filestream)
                        (value,) = struct.unpack(
                            f"{endian.struct}{value_size}s",
                            filestream.read(value_size),
                        )
                    else:
                        value = tek_meta_indicator[type_indicator].unpack(endian.struct, filestream)

                    meta_data[key.decode("utf_8")] = value
            else:
                msg = "Unrecognizable post-amble prefix for waveform file."
                raise IOError(msg)
        except (KeyError, ValueError) as e:
            msg = "Metadata unreadable, post-amble is formatted in a way that is not parseable."
            raise IOError(
                msg,
            ) from e

        return meta_data

    # Writing
    # pylint: disable=too-many-branches
    def pack_wfm_file(  # noqa: C901,PLR0912
        self,
        endian: Endian,
        version_number: VersionNumber,
        filestream: TextIO,
    ) -> None:
        """Pack information in the class attributes into the .wfm file provided.

        Args:
            endian: The Endianness of the waveform format (INTEL OR PPC).
            version_number: The version number that was provided (depends on device).
            filestream: The filestream that will be written to.
        """
        # if the user has not filled any meta deta for the format, automatically fill it for them
        # TODO: rehandle this using a dictionary lookup
        self._setup_wfm_format(version_number)
        # Endian direction and version number is determined before the waveform format is packed

        filestream.write(struct.pack(">2s", endian.format))

        String8(version_number.value).pack(endian.struct, filestream)

        # pack all the attributes within this class
        # TODO: rehandle this by leveraging the format of the class
        for attribute in (
            self.file_info,
            self.header,
            self.summary_frame_type,
            self.pixel_map,
        ):
            if attribute is not None:
                attribute.pack(endian.struct, filestream)

        # pack the explicit dimensions

        for item in WaveformDimension.list_values():
            if (attr_dim := getattr(self.explicit_dimensions, item)) is None:
                self.setup_explicit_dimensions(
                    scale=0.0,
                    units="",
                    curve_format=CurveFormatsVer3.EXPLICIT_NO_DIMENSION,
                    storage_type=StorageTypes.EXPLICIT_INVALID_STORAGE,
                )
                attr_dim = getattr(self.explicit_dimensions, item)
            attr_dim.pack(endian.struct, filestream, in_order=True)
            if (attr_user := getattr(self.explicit_user_view, item)) is None:
                self.setup_explicit_user_view(
                    version_number=version_number,
                    scale=0.0,
                    units="",
                    horizontal_reference=0.0,
                )
                attr_user = getattr(self.explicit_user_view, item)
            attr_user.pack(endian.struct, filestream, in_order=True)

        for item in WaveformDimension.list_values():
            if (attr := getattr(self.implicit_dimensions, item)) is None:
                self.setup_implicit_dimensions(
                    scale=0.0,
                    units="",
                )
                attr = getattr(self.implicit_dimensions, item)
            attr.pack(endian.struct, filestream, in_order=True)
            if (attr := getattr(self.implicit_user_view, item)) is None:
                self.setup_implicit_user_view(
                    version_number=version_number,
                    scale=0.0,
                    units="",
                    point_density=0,
                    horizontal_reference=0.0,
                )
                attr = getattr(self.implicit_user_view, item)
            attr.pack(endian.struct, filestream, in_order=True)

        for item in WaveformDimension.list_values():
            if (attr := getattr(self.time_info, item)) is None:
                self.setup_time_base_info(
                    real_point_spacing=0,
                    sweep_type=SweepTypes.SWEEP_INVALID,
                    type_of_base=BaseTypes.BASE_INVALID,
                )
                attr = getattr(self.time_info, item)
            attr.pack(endian.struct, filestream, in_order=True)

        for attribute in (self.update_specifications, self.curve_info):
            attribute.pack(endian.struct, filestream, in_order=True)

        for attribute in (self.update_specs, self.curve_specs):
            for spec in attribute:
                spec.pack(endian.struct, filestream, in_order=True)

        for attribute in (
            self.precharge_buffer,
            self.curve_buffer,
            self.postcharge_buffer,
        ):
            attribute.tofile(filestream)

        summation = sum(version_number.value) + sum(endian.format)
        for value in self.__dict__.values():
            if isinstance(value, np.ndarray):
                if len(value) > 100.0e6:  # noqa: PLR2004
                    summation += calculate_checksum(value)
                else:
                    summation += int(np.add.reduce(value.view(np.uint8), dtype=np.uint64))

            elif isinstance(value, List):
                summation += sum(frame.get_value_summation() for frame in value)
            elif not isinstance(value, Dict):
                summation += value.get_value_summation()

        self.file_checksum = UnsignedLongLong(summation)
        self.file_checksum.pack(endian.struct, filestream)

        self._write_tekmeta(endian, filestream)

    # Writing
    def setup_file_info(
        self,
        zoom_scale: Tuple[int, float] = (1, 1.0),
        zoom_position: Tuple[float, float] = (0.0, 0.0),
        waveform_label: str = "",
    ) -> None:
        """Fill in the generic file and structure info.

        !!!MUST OCCUR LAST!!!

        Args:
            zoom_scale: Not For Use. A range of min to max zoom scale information
            zoom_position: Not For Use. A range of min to max zoom position information
            waveform_label: A label to assign to the waveform
        """
        if (
            None not in (self.header, self.pixel_map, self.summary_frame_type)
            or not self.curve_buffer
        ):
            # find the length of the file, along with the curve position
            eof_offset, curve_offset = self._find_offsets()

            # byte offset can be calculated by ignoring the precharge buffer
            # number of frames can be calculated by checking the length of the curve specs
            # bytes per point is just the size of each item in the curve buffer
            self.file_info = WaveformStaticFileInfo(
                digits_in_byte_count=len(str(eof_offset)),
                bytes_till_eof=eof_offset,
                bytes_per_point=self.curve_buffer.dtype.itemsize,
                byte_offset=curve_offset,
                horizontal_zoom_scale_factor=zoom_scale[0],
                horizontal_zoom_position=zoom_position[0],
                vertical_zoom_scale_factor=zoom_scale[1],
                vertical_zoom_position=zoom_position[1],
                waveform_label=waveform_label,
                number_of_frames=max(len(self.curve_specs) - 1, 0),
                header_size=len(self.header) + len(self.pixel_map) + len(self.summary_frame_type),
            )
        else:
            msg = "Not enough info to generate static file info section."
            raise AttributeError(msg)
        # pylint: disable=pointless-string-statement
        """
        - digits_in_byte_count derived from the length from the bytes_till_eof.
        - bytes_till_eof derived from counting the length of each assigned byte, This value is
          dynamic, and changes based on version number.
        - bytes_per_point derived from the np type size.
        - byte_offset is derived from counting the length of each assigned byte before the curve.
          This value is dynamic, and changes based on version number.
        - horizontal_zoom_scale_factor and vertical_zoom_scale_factor derived from zoom_scale.
        - horizontal_zoom_position and vertical_zoom_position derived from zoom_position.
        - number_of_frames derived from the length of the number of the update specs.
        - header_size derived from the length of the header, pixel map and summary frame type.
        """

    # pylint: disable=too-many-arguments
    def setup_header(  # noqa: PLR0913
        self,
        waveform_type: WaveformTypes = WaveformTypes.SINGLE,
        number_of_waveforms: int = 1,
        acquisition_counter: int = 0,
        transaction_counter: int = 0,
        slot_id: int = 5,
        is_static: bool = False,
        data_type: DataTypes = DataTypes.VECTOR,
        general_purpose_counter: int = 0,
        accumulated_waveform_count: int = 1,
        target_accumulation_count: int = 1,
        curve_reference_count: int = 1,
        number_requested_fast_frames: int = 0,
    ) -> None:
        """Fill in the generic information about the waveform and its contents.

        !!!MUST OCCUR AFTER EXPLICIT, IMPLICIT AND UPDATE SPECIFICATIONS!!!

        Args:
            waveform_type: Not For Use. Type of waveform set.
            number_of_waveforms: Number of waveforms in the set.
            acquisition_counter: Not For Use. Internal acquisition counter.
            transaction_counter: Not For Use. Internal acquisition translation stamp.
            slot_id: Not For Use. The number and type of data slots for a product.
            is_static: Not For Use. Used internally to determine if waveform is static or live.
            data_type: The data type (scalar, vector, pixel map or waveform db).
            general_purpose_counter: Not for use. Usage varies by specific system.
            accumulated_waveform_count: Not for use. Number of waveforms in the accumulation.
            target_accumulation_count: Not for use. Number of acquisitions requested to be made.
            curve_reference_count: The number of curve objects for the given waveform set.
            number_requested_fast_frames: Not for use. Number of frames in the acquisition system.
        """
        # If there was no requested fast frames set, just set it to the number of current frames
        if not number_requested_fast_frames:
            number_requested_fast_frames = len(self.update_specs)

        if None not in (self.explicit_dimensions, self.implicit_dimensions):
            self.header = WaveformHeader(
                waveform_type=waveform_type.value,
                wfm_count=number_of_waveforms,
                acquisition_counter=acquisition_counter,
                transaction_stamp=transaction_counter,
                slot_id=slot_id,
                is_static=is_static,
                update_spec_cnt=len(self.update_specs) + 1,
                imp_dim_ref_cnt=2 if self.implicit_dimensions.second is not None else 1,
                exp_dim_ref_cnt=2 if self.explicit_dimensions.second is not None else 1,
                data_type=data_type.value,
                gen_purpose_counter=general_purpose_counter,
                accumulate_wfm_cnt=accumulated_waveform_count,
                target_accumulation_cnt=target_accumulation_count,
                curve_ref_cnt=curve_reference_count,
                num_requested_fast_frames=number_requested_fast_frames,
                num_acquired_fast_frames=len(self.update_specs),
            )
        else:
            msg = "Not enough info to generate a header section."
            raise AttributeError(msg)
        # pylint: disable=pointless-string-statement
        """
        - update_spec_cnt is allocated based on the length of the update specs provided (+1)
        - imp_dim_ref_cnt is dynamically allocated based on what has dimensions been assigned.
        - exp_dim_ref_cnt is dynamically allocated based on what has dimensions been assigned.
        - num_requested_fast_frames is assigned if not provided. num_acquired_fast_frames is
        - allocated based on the length of the update specs provided.
        """

    def setup_pixel_map(
        self,
        pixel_map_format: DSYFormat = DSYFormat.DSY_FORMAT_INVALID,
        pixel_map_max: int = 0,
    ) -> None:
        """Fill in the pixel map values.

        Args:
            pixel_map_format: Display format for the dimensions of the waveform.
            pixel_map_max: Not For Use. Max value of Pixel map.
        """
        self.pixel_map = PixMap(
            pix_map_displ_format=pixel_map_format.value,
            pix_map_max_value=pixel_map_max,
        )

    def setup_explicit_dimensions(  # noqa: PLR0913
        self,
        scale: float = 1.0,
        offset: float = 0.0,
        size: int = 0,
        units: str = "V",
        extent_range: Tuple[float, float] = (0.0, 0.0),
        resolution: float = 1.0,
        reference_point: float = 0.0,
        curve_format: CurveFormatsVer3 = CurveFormatsVer3.EXPLICIT_INT16,
        storage_type: StorageTypes = StorageTypes.EXPLICIT_SAMPLE,
        invalid_data: int = 0,
        over_range: bool = False,
        under_range: bool = False,
        value_range: Tuple[int, int] = (0, 0),
    ) -> None:
        """Fill in either the first or second explicit dimension.

        Args:
            scale: The scale of the waveform data for the given dimension.
            offset: The distance in units from the dimensions' zero value.
            size: The size of the explicit dimension in terms of the base storage value.
            units: The units for the dimension.
            extent_range: Not For Use. The range of attainable data for the explicit dimension.
            resolution: The smallest resolution possible given the products digitizer.
            reference_point: The ground-level reference value.
            curve_format: The code type of data values stored in the curve buffer.
            storage_type: Describes the layout of the data values stored in the curve.
            invalid_data: Not For Use. Represents the NULL (unacquired) waveform value.
            over_range: Not For Use. Special value that indicates that a point is over-ranged.
            under_range: Not For Use. Special value that indicates that a point is under-ranged.
            value_range: Not For Use. The range of values allowed in this data (not N, or OOB).
        """
        explicit_dimensions = ExplicitDimensions(
            scale=scale,
            offset=offset,
            size=size,
            units=units,
            extent_min=extent_range[0],
            extent_max=extent_range[1],
            resolution=resolution,
            reference_point=reference_point,
            format=curve_format.value,
            storage_type=storage_type.value,
            null_value=invalid_data,
            over_range=over_range,
            under_range=under_range,
            high_range=value_range[1],
            low_range=value_range[0],
        )

        self.explicit_dimensions = self._replace_dimension(
            self.explicit_dimensions,
            explicit_dimensions,
        )
        # pylint: disable=pointless-string-statement
        """
        - extent_min and extent_max derived from extent_range.
        - high_range and low_range derived from value_range.
        """

    def setup_implicit_dimensions(
        self,
        scale: float = 4.0e-7,
        offset: float = 0.0,
        units: str = "s",
        extent_range: Tuple[float, float] = (0.0, 0.0),
        resolution: float = 0.0,
        reference_point: float = 0.0,
        spacing: int = 0,
    ) -> None:
        """Fill in either the first or second implicit dimension.

        !!!MUST OCCUR AFTER BUFFER IS DEFINED!!!

        Args:
            scale: Used to specify the sample interval.
            offset: For the implicit dimension, offset is the trigger position.
            units: The record length.
            extent_range: Not For Use. The minimum attainable data value for the implicit dimension.
            resolution: Not for use in 5/6. The smallest resolution possible given the product.
            reference_point: The horizontal reference point of the time base.
            spacing: Real time point spacing.
        """
        if len(self.curve_buffer):
            implicit_dimensions = ImplicitDimensions(
                scale=scale,
                offset=offset,
                size=len(self.postcharge_buffer)
                + len(self.curve_buffer)
                + len(self.precharge_buffer),
                units=units,
                extent_min=extent_range[0],
                extent_max=extent_range[1],
                resolution=resolution,
                reference_point=reference_point,
                spacing=spacing,
            )

            self.implicit_dimensions = self._replace_dimension(
                self.implicit_dimensions,
                implicit_dimensions,
            )
        else:
            msg = "Not enough info to generate implicit dimensions sections."
            raise AttributeError(msg)
        # pylint: disable=pointless-string-statement
        """
        -Size derived from the length of the pre, post and curve buffers.
        - extend_min and extent_max derived from extent_range.
        """

    def setup_explicit_user_view(
        self,
        version_number: VersionNumber,
        scale: float = 1.0,
        units: str = "V",
        offset: float = 0.0,
        horizontal_reference: float = 50.0,
        trigger_delay: float = 0.0,
    ) -> None:
        """The relationship between the raw data and the way the user wants to view the data.

        Args:
            version_number: The version number that was provided (depends on device).
            scale: Not for use in 5/6. Used to apply additional scale information.
            units: Not for use in 5/6. User display units string, expressed in Units per Division.
            offset: Not for use in 5/6. Used to designate the screen position of the waveform.
            horizontal_reference: The horizontal position of the trigger in percentile.
            trigger_delay: The amount of delay, in seconds, from the trigger to the HRef.
        """
        user_view_class: Callable
        # version 3 uses a double for point_density
        if version_number == VersionNumber.THREE:
            user_view_class = DimensionsUserViewVer3
        else:
            user_view_class = DimensionsUserViewVer12

        user_view = user_view_class(
            scale=scale,
            units=units,
            offset=offset,
            point_density=1,
            horizontal_reference=horizontal_reference,
            trigger_delay=trigger_delay,
        )

        self.explicit_user_view = self._replace_dimension(self.explicit_user_view, user_view)
        # pylint: disable=pointless-string-statement
        """
        - point_density always 1 for explicit dimensions.
        """

    def setup_implicit_user_view(
        self,
        version_number: VersionNumber,
        scale: float = 1.0,
        units: str = "s",
        offset: float = 0.0,
        point_density: int = 1,
        horizontal_reference: float = 50.0,
        trigger_delay: float = 0.0,
    ) -> None:
        """The relationship between the raw data and the way the user wants to view the data.

        Args:
            version_number: The version number that was provided (depends on device).
            scale: Not for use in 5/6. Used to apply additional scale information.
            units: Not for use in 5/6. User display units string, expressed in Units per Division.
            offset: Not for use in 5/6. Used to designate the screen position of the waveform.
            point_density: Not for use in 5/6. The relationship of screen points to waveform data.
            horizontal_reference: The horizontal position of the trigger in percentile.
            trigger_delay: The amount of delay, in seconds, from the trigger to the HRef.
        """
        # version 3 uses a double for point_density
        if version_number == VersionNumber.THREE:
            user_view_class = DimensionsUserViewVer3
        else:
            user_view_class = DimensionsUserViewVer12

        user_view = user_view_class(
            scale=scale,
            units=units,
            offset=offset,
            point_density=point_density,
            horizontal_reference=horizontal_reference,
            trigger_delay=trigger_delay,
        )

        self.implicit_user_view = self._replace_dimension(self.implicit_user_view, user_view)

    def setup_time_base_info(
        self,
        real_point_spacing: int = 1,
        sweep_type: SweepTypes = SweepTypes.SWEEP_SAMPLE,
        type_of_base: BaseTypes = BaseTypes.BASE_TIME,
    ) -> None:
        """Describes how the waveform data was acquired and the meaning of the acquired points.

        Args:
            real_point_spacing: Integer count of the difference between the acquired points.
            sweep_type: Type of acquisition (roll, sample, et, invalid).
            type_of_base: Defines the kind of base (time, spectral_mag, spectral_phase, invalid).
        """
        time_info = TimeBaseInformation(
            real_point_spacing=real_point_spacing,
            sweep=sweep_type.value,
            type_of_base=type_of_base.value,
        )
        self.time_info = self._replace_dimension(self.time_info, time_info)

    def setup_update_specifications(
        self,
        real_point_offset: int = 0,
        trigger_time_offset: float = 0.5,
        fractional_second: float = 0.0,
        gmt_second: int = 0,
    ) -> None:
        """Timing information about the waveform data and trigger.

        Args:
            real_point_offset: The offset of the first non-interpolated point in the record.
            trigger_time_offset: The sample time from the trigger time stamp to the next sample.
            fractional_second: The fraction of a second when the trigger occurred.
            gmt_second: The time based upon gmt time that the trigger occurred.
        """
        self.update_specifications = UpdateSpecifications(
            real_point_offset=real_point_offset,
            trigger_time_offset=trigger_time_offset,
            fractional_second=fractional_second,
            gmt_second=gmt_second,
        )

    def setup_curve_information(
        self,
        state_flags: int = 81,
        check_sum_type: ChecksumType = ChecksumType.NO_CHECKSUM,
    ) -> None:
        """Locational information about the curve information and the data check sum.

        Args:
            state_flags: Indicate validity of curve buffer data.
            check_sum_type: Indicates the algorithm used to calculate the waveform checksum.
        """
        data_start_offset = len(self.precharge_buffer) * self.curve_buffer.dtype.itemsize
        postcharge_offset = (
            data_start_offset + len(self.curve_buffer) * self.curve_buffer.dtype.itemsize
        )
        postcharge_stop_offset = (
            postcharge_offset + len(self.postcharge_buffer) * self.curve_buffer.dtype.itemsize
        )
        self.curve_info = CurveInformation(
            state_flags=state_flags,
            check_sum_type=check_sum_type.value,
            check_sum=0,
            precharge_start_offset=0,
            data_start_offset=data_start_offset,
            postcharge_start_offset=postcharge_offset,
            postcharge_stop_offset=postcharge_stop_offset,
            end_of_curve_buffer_offset=postcharge_stop_offset,
        )

    ################################################################################################
    # Private Methods
    ################################################################################################

    # Reading
    @staticmethod
    def _unpack_twice(
        data_class: Type[StructuredInfo],
        endian: Endian,
        filestream: TextIO,
    ) -> Dimension:
        """Unpack an enforced data class twice and put into a dimension class.

        Args:
            data_class: The data class to unpack.
            endian: The Endianness of the waveform format (INTEL OR PPC).
            filestream: The filestream that will be written to.

        Returns:
            A class with two attributes, the first and second dimensions of a dataclass.
        """
        first_instance = data_class.unpack(endian.struct, filestream, in_order=True)
        second_instance = data_class.unpack(endian.struct, filestream, in_order=True)
        return Dimension(first=first_instance, second=second_instance)

    # Reading
    @staticmethod
    def _unpack_data(
        dimensions: Type[StructuredInfo],
        user_view: Type[DimensionsUserViewVer12 | DimensionsUserViewVer3],
        endian: Endian,
        filestream: TextIO,
    ) -> Tuple[Dimension, Dimension]:
        """Unpack the explicit data and it's user view information.

        Args:
            dimensions: Either the implicit or explicit dimension.
            user_view:  Either the implicit or explicit user view.
            endian: The Endianness of the waveform format (INTEL OR PPC).
            filestream: The filestream that will be written to.

        Returns:
            The dimension and user view data class in the dimension class.
        """
        first_dimensions = dimensions.unpack(endian.struct, filestream, in_order=True)
        first_users = user_view.unpack(endian.struct, filestream, in_order=True)
        second_dimensions = dimensions.unpack(endian.struct, filestream, in_order=True)
        second_users = user_view.unpack(endian.struct, filestream, in_order=True)
        dimension_tuple = Dimension(first_dimensions, second_dimensions)
        user_view_tuple = Dimension(first=first_users, second=second_users)
        return dimension_tuple, user_view_tuple

    # Reading
    def _get_fast_frame_information(
        self,
        endian: Endian,
        filestream: TextIO,
    ) -> Tuple[List[UpdateSpecifications], List[CurveInformation]]:
        """Fast Frame information holding both update and curve info data classes.

        Args:
            endian: The Endianness of the waveform format (INTEL OR PPC).
            filestream: The filestream that will be written to.

        Returns:
            Both the update frame and curve frame lists.
        """
        if self.header is not None:
            # update frame info
            update_spec = [
                UpdateSpecifications.unpack(endian.struct, filestream, in_order=True)
                for _ in range(self.header.num_acquired_fast_frames)
            ]
            # curve frame info
            curve_spec = [
                CurveInformation.unpack(endian.struct, filestream, in_order=True)
                for _ in range(self.header.num_acquired_fast_frames)
            ]
            return update_spec, curve_spec
        return [], []

    # Reading
    def _get_curve_information(
        self,
        filestream: TextIO,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Obtain the waveform curve.

        Args:
            endian: The Endianness of the waveform format (INTEL OR PPC).
            filestream: The filestream that will be written to.

        Returns:
            The entire curve buffer, including pre and post charge.
        """
        curve_type_lookup = {
            CurveFormatsVer3.EXPLICIT_INT16.value: Short,
            CurveFormatsVer3.EXPLICIT_INT32.value: Long,
            CurveFormatsVer3.EXPLICIT_UINT32.value: UnsignedLong,
            CurveFormatsVer3.EXPLICIT_UINT64.value: UnsignedLongLong,
            CurveFormatsVer3.EXPLICIT_FP32.value: Float,
            CurveFormatsVer3.EXPLICIT_FP64.value: Double,
            CurveFormatsVer3.EXPLICIT_UINT8.value: UnsignedChar,
            CurveFormatsVer3.EXPLICIT_INT8.value: Char,
            CurveFormatsVer3.EXPLICIT_NO_DIMENSION: None,
        }

        # using ands for pyright instead of is in
        if (
            self.explicit_dimensions is not None
            and self.curve_info is not None
            and self.file_info is not None
        ):
            curve_type = curve_type_lookup[self.explicit_dimensions.first.format]
            precharge_buffer_length = (
                self.curve_info.data_start_offset - self.curve_info.precharge_start_offset
            ) // self.file_info.bytes_per_point
            charge_buffer_length = (
                self.curve_info.postcharge_start_offset - self.curve_info.data_start_offset
            ) // self.file_info.bytes_per_point
            postcharge_buffer_length = (
                self.curve_info.postcharge_stop_offset - self.curve_info.postcharge_start_offset
            ) // self.file_info.bytes_per_point

            precharge_curve_buffer = self.get_curve_data(
                precharge_buffer_length,
                curve_type,
                filestream,
            )
            charge_curve_buffer = self.get_curve_data(charge_buffer_length, curve_type, filestream)
            postcharge_curve_buffer = self.get_curve_data(
                postcharge_buffer_length,
                curve_type,
                filestream,
            )

            return precharge_curve_buffer, charge_curve_buffer, postcharge_curve_buffer
        msg = "No primary dimensions defined in file."
        raise AttributeError(msg)

    # Reading
    @staticmethod
    def get_curve_data(length: int, data_type: Type[ByteData], filestream: TextIO) -> np.ndarray:
        """Read the curve data from the file.

        Args:
            length: The length of the array to create.
            data_type: The type of data for each value.
            filestream: The filestream that will be written to.

        Returns:
            The curve data as a numpy array.
        """
        return np.fromfile(file=filestream, dtype=data_type.np_repr, count=length)

    # Writing
    def _setup_wfm_format(self, versioning_number: VersionNumber) -> None:  # noqa: C901
        """Setup the waveform format based on what is already setup.

        Args:
            versioning_number: The version number of the waveform format.
        """
        if not self.summary_frame_type and versioning_number != VersionNumber.ONE:
            self.summary_frame_type = UnsignedShort(SummaryFrameType.SUMMARY_FRAME_OFF.value)
        if not self.pixel_map:
            self.setup_pixel_map()
        if not self.explicit_dimensions:
            self.setup_explicit_dimensions()
        if not self.explicit_user_view:
            self.setup_explicit_user_view(versioning_number)
        if not self.implicit_dimensions:
            self.setup_implicit_dimensions()
        if not self.implicit_user_view:
            self.setup_implicit_user_view(versioning_number)
        if not self.header:
            self.setup_header()
        if not self.time_info:
            self.setup_time_base_info()
        if not self.update_specifications:
            self.setup_update_specifications()
        if not self.curve_info:
            self.setup_curve_information()
        if not self.file_info:
            self.setup_file_info()

    # Writing
    def _find_offsets(self) -> Tuple[int, int]:
        """Determine the total byte length and where the curve is located dynamically.

        Returns:
            A tuple containing the byte length of the file and where the curve begins.
        """
        # starts at ten for version number and byte order verification
        # eof might just be wrong in .wfm files, check saved waveform file for verification
        # TODO: calculate it instead
        eof_offset = -7
        byte_count = 10
        curve_offset = 0

        # iterate through each class attribute
        for (
            attribute_name,
            attribute_type,
        ) in WfmFormat.__annotations__.items():
            attribute_value = getattr(self, attribute_name)
            if attribute_value is not None and attribute_name not in "meta_data":
                if isinstance(attribute_value, np.ndarray):
                    byte_count += len(attribute_value) * attribute_value.dtype.itemsize
                elif isinstance(attribute_value, List):
                    byte_count += (
                        len(attribute_value) * get_args(attribute_type)[0].get_cls_length()
                    )
                elif isinstance(attribute_value, Dimension):
                    byte_count += len(attribute_value.first) * 2
                else:
                    byte_count += len(attribute_value)
            # if attribute is undefined, then we check the length of the type to get a static length
            elif attribute_name not in {"meta_data", "file_checksum"}:
                try:
                    byte_count += attribute_type.get_cls_length()
                except AttributeError:
                    byte_count += get_args(attribute_type)[0].get_cls_length()
                    with contextlib.suppress(AttributeError):
                        byte_count += get_args(attribute_type)[1].get_cls_length()

            if (
                attribute_value is not None
                and attribute_name not in {"file_checksum", "meta_data"}
                and not isinstance(attribute_value, np.ndarray)
            ):
                curve_offset = byte_count
        return byte_count + eof_offset, curve_offset

    # Writing
    @staticmethod
    def _replace_dimension(dimension: Optional[Dimension], data_class: Any) -> Dimension:
        """Replace either the first or second dimension with new data.

        Args:
            dimension: The current dimension object, with either one or two dimensions.
            data_class: What to replace the dimension with.

        Returns:
            The new dimensions named tuple with the dimension filled.
        """
        # if there is no dimension, create the first one
        if dimension is not None:
            dimension = replace(dimension, second=data_class)
        # other wise fill the second dimension
        else:
            dimension = Dimension(first=data_class, second=None)
        return dimension

    # Writing
    def _write_tekmeta(self, endian: Endian, filestream: TextIO) -> None:
        """Write the metadata to the waveform file.

        Args:
            endian: The byte order of the file to write to.
            filestream: The filestream that will be written to.
        """
        tek_meta_indicator = {
            str: (1, String),
            bytes: (1, String),
            int: (2, Long),
            float: (3, Double),
        }
        String8("tekmeta!").pack(endian.struct, filestream)
        UnsignedLong(len(self.meta_data)).pack(endian.struct, filestream)
        for key, value in self.meta_data.items():
            UnsignedLong(len(key)).pack(endian.struct, filestream)
            filestream.write(struct.pack(f"{endian.struct}{len(key)}s", key.encode("utf_8")))

            if type(value) in tek_meta_indicator:
                type_indicator = tek_meta_indicator[type(value)][0]
                byte_type = tek_meta_indicator[type(value)][1]
            else:
                type_indicator = value.tek_meta
                byte_type = type(value)

            Char(type_indicator).pack(endian.struct, filestream)
            if type_indicator == 1:
                UnsignedLong(len(value)).pack(endian.struct, filestream)
                if isinstance(value, str):
                    value = value.encode("utf_8")  # noqa: PLW2901
                filestream.write(struct.pack(f"{endian.struct}{len(value)}s", value))
            else:
                byte_type(value).pack(endian.struct, filestream)
