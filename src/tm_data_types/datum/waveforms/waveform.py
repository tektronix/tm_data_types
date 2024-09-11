"""Handles information pertaining to waveforms."""

from abc import ABC, abstractmethod
from functools import cached_property
from typing import Any, Dict, Optional

import numpy as np

from bidict import bidict
from pydantic.dataclasses import dataclass as pydantic_dataclass

from tm_data_types.datum.data_types import MeasuredData
from tm_data_types.datum.datum import Datum
from tm_data_types.helpers.byte_data_class import EnforcedTypeDataClass
from tm_data_types.helpers.enums import Enum, SIBaseUnit


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
    """Data which can come from tekmeta or a header."""

    ################################################################################################
    # Public Methods
    ################################################################################################

    def operable_metainfo(self) -> Dict[str, Any]:
        """Meta info that contains non None values within the fields.

        Returns:
            A dictionary containing meta info which do not have None values.
        """
        return {key: value for key, value in self.__dict__.items() if value is not None}

    def operable_exclusive_metadata(self) -> Dict[str, Any]:
        """Meta info that is exclusively tekmeta.

        Returns:
            A dictionary containing meta info which is exclusively tekmeta.
        """
        data = {
            key: value
            for key, value in self.__dict__.items()
            if value is not None and key not in ExclusiveMetaInfo.__annotations__
        }
        return data

    @staticmethod
    def remap(
        lookup: bidict[str, str],
        data: Dict[str, Any],
        drop_non_existant: bool = False,
    ) -> Dict[str, Any]:
        """Remap the pythonic naming convention to tekmeta naming/ file format naming.

        Returns:
            A dictionary which provides the opposite naming convention.
        """
        remapped_dict = {
            lookup[key]: (val if not isinstance(val, Enum) else val.value)
            for key, val in data.items()
            if key in lookup or not drop_non_existant
        }
        return remapped_dict


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
        x_axis_values = np.arange(
            0 - trigger_location,
            (self.record_length * self.x_axis_spacing)
            - (self.x_axis_spacing / 2)
            - trigger_location,
            self.x_axis_spacing,
        )
        return x_axis_values

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
