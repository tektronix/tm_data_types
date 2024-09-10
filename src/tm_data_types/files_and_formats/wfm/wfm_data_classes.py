"""All the dataclass which will host information about a .wfm's format."""

from tm_data_types.helpers.byte_data_class import pydantic_dataclass, StructuredInfo
from tm_data_types.helpers.byte_data_types import (
    Double,
    Float,
    Int,
    Long,
    Short,
    String20,
    String32,
    UnsignedChar,
    UnsignedLong,
    UnsignedLongLong,
    UnsignedShort,
)


@pydantic_dataclass
class WaveformStaticFileInfo(StructuredInfo):  # pylint: disable=too-many-instance-attributes
    """Generic information about the file and it's structure."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    digits_in_byte_count: UnsignedChar
    bytes_till_eof: UnsignedLong
    bytes_per_point: UnsignedChar
    byte_offset: Long
    horizontal_zoom_scale_factor: Long
    horizontal_zoom_position: Float
    vertical_zoom_scale_factor: Double
    vertical_zoom_position: Float
    waveform_label: String32
    number_of_frames: UnsignedLong
    header_size: UnsignedShort
    """
    digits_in_byte_count: Number of digits in the bytes_till_eof attribute.
    bytes_till_eof: The number of bytes from here to the end of the file.
    bytes_per_point: Number of bytes per curve data point.
    byte_offset: The number of bytes to the start of the curve buffer.
    horizontal_zoom_scale_factor: Horizontal scale zoom information.
    horizontal_zoom_position: Horizontal position zoom information.
    vertical_zoom_scale_factor: Vertical scale zoom information.
    vertical_zoom_position: Vertical position zoom information.
    waveform_label: User defined label for the reference waveform.
    number_of_frames: Number of WfmUpdateSpec and Curve items following the first.
    header_size: The size in bytes of the waveform header.
    """


@pydantic_dataclass
class WaveformHeader(StructuredInfo):  # pylint: disable=too-many-instance-attributes
    """Generic information about the waveform and it's dimensions."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    waveform_type: Int
    wfm_count: UnsignedLong
    acquisition_counter: UnsignedLongLong
    transaction_stamp: UnsignedLongLong
    slot_id: Int
    is_static: Int
    update_spec_cnt: UnsignedLong
    imp_dim_ref_cnt: UnsignedLong
    exp_dim_ref_cnt: UnsignedLong
    data_type: Int
    gen_purpose_counter: UnsignedLongLong
    accumulate_wfm_cnt: UnsignedLong
    target_accumulation_cnt: UnsignedLong
    curve_ref_cnt: UnsignedLong
    num_requested_fast_frames: UnsignedLong
    num_acquired_fast_frames: UnsignedLong
    """
    waveform_type: Type of waveform set.
    wfm_count: Number of waveforms in the set.
    acquisition_counter: Internal acquisition counter. This is not a time stamp.
    transaction_stamp: Internal acquisition translation stamp.
    slot_id: The number and type of data slots for a product.
    is_static: Used internally to determine if waveform is static or live.
    update_spec_cnt: Number of wfm update specifications in the waveform set.
    imp_dim_ref_cnt: The number of implicit dimensions for the given waveform.
    exp_dim_ref_cnt: The number of explicit dimensions for the waveform set.
    data_type: The data type (scalar, vector, pixel map or waveform db).
    gen_purpose_counter: Internal usage only. Usage varies by specific system.
    accumulate_wfm_cnt: Number of waveforms that have gone into the accumulation.
    target_accumulation_cnt: Number of acquisitions requested to be made.
    curve_ref_cnt: The number of curve objects for the given waveform set.
    num_requested_fast_frames: Number of FastFrame acquisitions that were requested.
    num_acquired_fast_frames: Number of frames that the acquisition system acquired.
    """


@pydantic_dataclass
class PixMap(StructuredInfo):
    """Information about the pixel map."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    pix_map_displ_format: Int
    pix_map_max_value: UnsignedLongLong
    """
    pix_map_displ_format: Display format for the dimensions of the waveform.
    pix_map_max_value: Max value of Pixel map.
    """


@pydantic_dataclass
class ExplicitDimensions(StructuredInfo):  # pylint: disable=too-many-instance-attributes
    """The explicit dimensions of the waveform, usually voltage."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    scale: Double
    offset: Double
    size: UnsignedLong
    units: String20
    extent_min: Double
    extent_max: Double
    resolution: Double
    reference_point: Double
    format: Int
    storage_type: Int
    null_value: Int
    over_range: Int
    under_range: Int
    high_range: Int
    low_range: Int
    """
    scale: The scale of the waveform data for the given dimension.
    offset: The distance in units from the dimensions' zero value.
    size: The size of the explicit dimension in terms of the base storage value.
    units: The units for the dimension.
    extent_min: The minimum attainable data value for the explicit dimension.
    extent_max: The maximum attainable data value for the explicit dimension.
    resolution: The smallest resolution possible given the products digitizer.
    reference_point: The ground-level reference value.
    format: The code type of data values stored in the curve buffer.
    storage_type: Describes the layout of the data values stored in the curve.
    null_value: The value that represents the NULL (unacquired) waveform value.
    over_range: Special value that indicates that a point is over-ranged.
    under_range: Special value that indicates that a point is under-ranged.
    high_range: The largest signed value that can be present in this data (not N, or OOB).
    low_range: The smallest value that can be present in this data (not N, or OOB).
    """


@pydantic_dataclass
class ImplicitDimensions(StructuredInfo):  # pylint: disable=too-many-instance-attributes
    """The implicit dimensions of the waveform, usually time."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    scale: Double
    offset: Double
    size: UnsignedLong
    units: String20
    extent_min: Double
    extent_max: Double
    resolution: Double
    reference_point: Double
    spacing: UnsignedLong
    """
    scale: Used to specify the sample interval.
    offset: For the implicit dimension, offset is the trigger position.
    size: The record length.
    units: The units for the dimension.
    extent_min: The minimum attainable data value for the implicit dimension.
    extent_max: The maximum attainable data value for the implicit dimension.
    resolution: The smallest resolution possible given the products digitizer.
    reference_point: The horizontal reference point of the time base.
    spacing: Real time point spacing.
    """


@pydantic_dataclass
class DimensionsUserView(StructuredInfo):
    """Parent class for both dimensional user view data class."""


@pydantic_dataclass
class DimensionsUserViewVer12(DimensionsUserView):
    """The relationship between the raw data and the way the user wants to view it."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    scale: Double
    units: String20
    offset: Double
    point_density: UnsignedLong
    horizontal_reference: Double
    trigger_delay: Double
    """
    scale: # Used to apply additional scale information for display purposes.
    units: # User display units string, expressed in Units per Division.
    offset: Used to designate the screen relative position of the waveform.
    point_density: The relationship of screen points to waveform data.
    horizontal_reference: The horizontal position of the trigger in percentile.
    trigger_delay: The amount of delay, in seconds, from the trigger to the HRef.
    """


@pydantic_dataclass
class DimensionsUserViewVer3(DimensionsUserView):
    """The relationship between the raw data and the way the user wants to view it.

    (Version 3)
    """

    ################################################################################################
    # Class Variables
    ################################################################################################

    scale: Double
    units: String20
    offset: Double
    point_density: Double
    horizontal_reference: Double
    trigger_delay: Double
    """
    scale: # Used to apply additional scale information for display purposes.
    units: # User display units string, expressed in Units per Division.
    offset: Used to designate the screen relative position of the waveform.
    point_density: The relationship of screen points to waveform data.
    horizontal_reference: The horizontal position of the trigger in percentile.
    trigger_delay: The amount of delay, in seconds, from the trigger to the HRef.
    """


@pydantic_dataclass
class TimeBaseInformation(StructuredInfo):
    """Describes how the waveform data was acquired and the meaning of the acquired points."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    real_point_spacing: UnsignedLong
    sweep: Int
    type_of_base: Int
    """
    real_point_spacing: Integer count of the difference between the acquired points.
    sweep: Type of acquisition (roll, sample, et, invalid).
    type_of_base: Defines the kind of base (time, spectral_mag, spectral_phase, invalid).
    """


@pydantic_dataclass
class UpdateSpecifications(StructuredInfo):
    """Timing information about the waveform data and trigger."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    real_point_offset: UnsignedLong
    trigger_time_offset: Double
    fractional_second: Double
    gmt_second: Long
    """
    real_point_offset: The offset of the first non-interpolated point in the record.
    trigger_time_offset: The sample time from the trigger time stamp to the next sample.
    fractional_second: The fraction of a second when the trigger occurred.
    gmt_second: The time based upon gmt time that the trigger occurred.
    """


@pydantic_dataclass
class CurveInformation(StructuredInfo):  # pylint: disable=too-many-instance-attributes
    """Locational information about the curve information and the data check sum."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    state_flags: UnsignedLong  # not a double or float as labeled in some tektronix documentation
    check_sum_type: Int
    check_sum: Short
    precharge_start_offset: UnsignedLong
    data_start_offset: UnsignedLong
    postcharge_start_offset: UnsignedLong
    postcharge_stop_offset: UnsignedLong
    end_of_curve_buffer_offset: UnsignedLong
    """
    state_flags: Indicate validity of curve buffer data.
    check_sum_type: Indicates the algorithm used to calculate the waveform checksum.
    check_sum: Curve checksum. Currently not implemented.
    precharge_start_offset: Start position of the pre buffer interpolation info.
    data_start_offset: The offset from the start of the curve buffer.
    postcharge_start_offset: Start position of the post buffer interpolation info.
    postcharge_stop_offset: End position of the post buffer interpolation info.
    end_of_curve_buffer_offset: End position of information acquired via roll mode.
    """
