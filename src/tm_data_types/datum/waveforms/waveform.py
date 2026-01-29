"""Handles information pertaining to waveforms."""

import warnings

from abc import ABC, abstractmethod
from functools import cached_property
from typing import Any, Dict, Optional

import numpy as np

from pydantic.dataclasses import dataclass as pydantic_dataclass

from tm_data_types.datum.data_types import MeasuredData
from tm_data_types.datum.datum import Datum
from tm_data_types.helpers.byte_data_class import EnforcedTypeDataClass
from tm_data_types.helpers.enums import SIBaseUnit


# pylint: disable=too-few-public-methods
@pydantic_dataclass(kw_only=True)
class ExclusiveMetaInfo(EnforcedTypeDataClass):  # pylist: disable=too-few-public-methods
    """Data which is exclusive from tekmeta, enforces types through casting before init."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    waveform_label: str = ""


@pydantic_dataclass(kw_only=True)
class WaveformMetaInfo(ExclusiveMetaInfo):
    """Data which can come from tekmeta or a header.

    This class contains standard waveform metadata fields that are common across
    different waveform types. It also supports custom metadata through the
    extended_metadata dictionary.

    Standard fields include:
    - waveform_label: User-defined label for the waveform
    - y_offset, y_position: Vertical positioning information
    - clipping_initialized: Whether clipping detection is enabled

    Custom metadata can be added using the extended_metadata dictionary or
    the set_custom_metadata() convenience method.

    Examples:
        >>> meta_info = WaveformMetaInfo()
        >>> meta_info.waveform_label = "Test Signal"
        >>> meta_info.set_custom_metadata(
        ...     test_equipment="MSO54",
        ...     test_engineer="John Doe"
        ... )
        >>> print(meta_info.test_equipment)  # "MSO54"

    Note:
        Custom metadata fields are preserved in WFM files but may be dropped
        when writing to CSV or MAT formats.
    """

    ################################################################################################
    # Public Methods
    ################################################################################################

    def operable_metainfo(self) -> Dict[str, Any]:
        """Meta info that contains non None values within the fields.

        This method returns a dictionary containing all metadata fields that have
        non-None values, including both standard fields and the extended_metadata
        dictionary itself (if it's not None).

        Returns:
            A dictionary containing meta info which do not have None values.

        Examples:
            >>> meta_info = WaveformMetaInfo()
            >>> meta_info.waveform_label = "Test Signal"
            >>> meta_info.set_custom_metadata(test_equipment="MSO54")
            >>> operable = meta_info.operable_metainfo()
            >>> print(operable)
            {'waveform_label': 'Test Signal', 'extended_metadata': {'test_equipment': 'MSO54'}, ...}

        Note:
            This method is used internally by file format classes to determine
            which metadata fields to include when writing files.
        """
        return {key: value for key, value in self.__dict__.items() if value is not None}

    def operable_exclusive_metadata(self) -> Dict[str, Any]:
        """Meta info that is exclusively tekmeta.

        This method returns metadata fields that come from tekmeta (Tektronix metadata)
        and are not part of the standard waveform header fields. This excludes fields
        that are defined in the ExclusiveMetaInfo base class.

        Returns:
            A dictionary containing meta info which is exclusively tekmeta.

        Examples:
            >>> meta_info = WaveformMetaInfo()
            >>> meta_info.set_custom_metadata(tekmeta_field="value")
            >>> exclusive = meta_info.operable_exclusive_metadata()
            >>> print(exclusive)
            {'tekmeta_field': 'value', ...}

        Note:
            This method is used internally to separate tekmeta-specific fields from
            standard waveform metadata fields.
        """
        return {
            key: value
            for key, value in self.__dict__.items()
            if value is not None and key not in ExclusiveMetaInfo.__annotations__
        }

    def set_custom_metadata(self, **kwargs: Any) -> None:
        """Set custom metadata fields in extended_metadata.

        This is a convenience method to make it easier to add custom metadata
        without having to manually manage the extended_metadata dictionary.

        Args:
            **kwargs: Key-value pairs to add as custom metadata. Keys will become
                     accessible as attributes on the meta_info object.

        Examples:
            >>> meta_info = WaveformMetaInfo()
            >>> meta_info.set_custom_metadata(
            ...     pattern_type="prbs7",
            ...     encoding_type="nrz",
            ...     symbol_rate=10e9,
            ...     test_equipment="MSO54"
            ... )
            >>> print(meta_info.pattern_type)  # "prbs7"
            >>> print(meta_info.test_equipment)  # "MSO54"

        You can also add metadata incrementally:
            >>> meta_info.set_custom_metadata(test_engineer="John Doe")
            >>> meta_info.set_custom_metadata(test_date="2024-01-15")
            >>> print(meta_info.test_engineer)  # "John Doe"

        Note:
            - If extended_metadata is None, it will be initialized as an empty dict
            - Existing custom metadata will be updated, not replaced
            - Custom metadata fields are preserved in WFM files but may be dropped
              when writing to CSV or MAT formats
        """
        if self.extended_metadata is None:
            self.extended_metadata = {}
        self.extended_metadata.update(kwargs)

    @classmethod
    def remap(
        cls, lookup: dict[str, str], data: dict[str, Any], drop_non_existant: bool = False
    ) -> dict[str, Any]:
        """Remap the data to the correct format.

        This method transforms dictionary keys according to a lookup table, which is
        commonly used when converting between different metadata formats or file types.

        Args:
            lookup: Dictionary mapping source keys to target keys. Keys in 'data' that
                   match keys in 'lookup' will be renamed to the corresponding values.
            data: Dictionary of data to remap
            drop_non_existant: If True, drop keys not found in lookup. If False,
                              preserve them unchanged (with a warning for unknown keys).

        Returns:
            Remapped dictionary with keys transformed according to lookup

        Examples:
            >>> lookup = {"old_name": "new_name", "another_old": "another_new"}
            >>> data = {"old_name": "value1", "unknown_key": "value2", "another_old": "value3"}
            >>> result = WaveformMetaInfo.remap(lookup, data, drop_non_existant=False)
            >>> print(result)
            {'new_name': 'value1', 'unknown_key': 'value2', 'another_new': 'value3'}

        Note:
            - When drop_non_existant=False, unknown keys will trigger a UserWarning
              suggesting the use of extended_metadata for custom fields
            - This method is used internally by file format classes to convert
              between different metadata schemas
        """
        remapped_dict = {}
        unknown_keys = []

        for key, value in data.items():
            if key in lookup:
                remapped_dict[lookup[key]] = value
            elif not drop_non_existant:
                remapped_dict[key] = value
                unknown_keys.append(key)

        # Provide helpful warning for unknown keys
        if unknown_keys and not drop_non_existant:
            warnings.warn(
                f"Unknown metadata fields {unknown_keys} will be preserved but may not be "
                f"supported by all file formats. Consider using extended_metadata for custom"
                f" fields.",
                UserWarning,
                stacklevel=2,
            )

        return remapped_dict

    extended_metadata: Optional[Dict[str, Any]] = None
    """Custom metadata fields that don't fit into the standard waveform metadata.

    This dictionary allows you to store arbitrary key-value pairs for custom
    metadata fields. You can access these fields as attributes on the meta_info
    object using Python's `__getattr__` mechanism.

    The `extended_metadata` system is designed for:
    - Application-specific data (test conditions, equipment info, etc.)
    - Fields that don't fit into the standard waveform metadata schema
    - Temporary or experimental metadata fields

    Examples:
        >>> meta_info = WaveformMetaInfo()
        >>> meta_info.extended_metadata = {
        ...     "pattern_type": "prbs7",
        ...     "encoding_type": "nrz",
        ...     "symbol_rate": 10e9,
        ...     "test_equipment": "MSO54"
        ... }
        >>> print(meta_info.pattern_type)  # "prbs7"
        >>> print(meta_info.test_equipment)  # "MSO54"

    Alternative approach using set_custom_metadata():
        >>> meta_info.set_custom_metadata(
        ...     pattern_type="prbs7",
        ...     test_equipment="MSO54"
        ... )

    File Format Compatibility:
        - WFM files: All custom metadata is preserved
        - CSV files: Custom metadata is dropped (only standard fields included)
        - MAT files: Custom metadata may be lost depending on implementation

    Note:
        If extended_metadata is None or empty, accessing custom fields will
        raise an AttributeError with helpful guidance on how to add the field.
    """

    def __getattr__(self, name: str) -> Any:
        """Retrieve an attribute from the extended metadata if it exists.

        Args:
            name: The name of the attribute to retrieve.

        Returns:
            The value of the attribute from `extended_metadata` if it exists.

        Raises:
            AttributeError: If the attribute does not exist in `extended_metadata`.
        """
        if self.extended_metadata and name in self.extended_metadata:
            return self.extended_metadata[name]

        # Provide more helpful error message
        if self.extended_metadata is None:
            msg = (
                f"{type(self).__name__} object has no attribute {name!r}. "
                f"To add custom metadata, set extended_metadata first: "
                f"meta_info.extended_metadata = {{'{name}': your_value}}"
            )
            raise AttributeError(msg)
        if name not in self.extended_metadata:
            available_keys = list(self.extended_metadata.keys()) if self.extended_metadata else []
            msg = (
                f"{type(self).__name__} object has no attribute {name!r}. "
                f"Available custom metadata keys: {available_keys}. "
                f"To add this field use: meta_info.extended_metadata['{name}'] = your_value"
            )
            raise AttributeError(msg)
        msg = f"{type(self).__name__} object has no attribute {name!r}"
        raise AttributeError(msg)


class Waveform(Datum, ABC):
    """A base waveform which wraps analog, iq and digital waveforms."""

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __init__(
        self,
    ) -> None:
        """Initialize the waveform's meta info and x-axis specifications."""
        self.meta_info: Optional[WaveformMetaInfo] = None
        self.trigger_index: Optional[float] = None
        self.source_name: Optional[str] = None
        self.x_axis_values: Optional[np.ndarray] = None
        self.x_axis_spacing: float = 1.0
        self.x_axis_units: str = SIBaseUnit.SECONDS.value

    ################################################################################################
    # Properties
    ################################################################################################

    @cached_property
    def normalized_horizontal_values(self) -> np.ndarray:
        """Cache the x values with the spacing and trigger index applied.

        This is reset when x values are changed.

        Returns:
            An np array with the x_axis_spacing and trigger index applied.
        """
        trigger_location = self.trigger_index * self.x_axis_spacing
        # create an array with pre-applied ranges, spacing based on x_axis_spacing
        return np.arange(
            0 - trigger_location,
            (self.record_length * self.x_axis_spacing)
            - (self.x_axis_spacing / 2)
            - trigger_location,
            self.x_axis_spacing,
        )

    @property
    def record_length(self) -> int:
        """Get the number of samples for the waveform data.

        Returns:
            The length of the data.
        """
        return len(self._measured_data)

    @cached_property
    @abstractmethod
    def normalized_vertical_values(self) -> MeasuredData:
        """Reduce the waveform into a canonical form with no dependencies.

        This is uncached when any dependency is reset values are changed.

        Returns:
            The normalized data.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def _measured_data(self) -> np.ndarray:
        """The data that is measured (y_axis, iq_axis, etc).

        Returns:
            The measured data for the waveform.
        """
        raise NotImplementedError
