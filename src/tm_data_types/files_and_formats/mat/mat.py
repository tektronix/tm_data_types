"""The file formatting for a .mat file."""

import datetime
import struct

from abc import abstractmethod
from typing import Any, ClassVar, Dict, Generic, List, Tuple

import numpy as np
import scipy.io as sio

from bidict import bidict
from dateutil.tz import tzlocal

from tm_data_types.datum.data_types import MeasuredData, Normalized, RawSample, type_max, type_min
from tm_data_types.datum.waveforms.waveform import Waveform
from tm_data_types.files_and_formats.abstracted_file import AbstractedFile, DATUM_TYPE_VAR
from tm_data_types.files_and_formats.wfm.wfm_format import Endian
from tm_data_types.helpers.byte_data_types import (
    ByteData,
    Double,
    Float,
    Long,
    LongLong,
    Short,
    SignedChar,
    String,
    UnsignedChar,
    UnsignedLong,
    UnsignedLongLong,
    UnsignedShort,
)

Matrix = object


class MATFile(AbstractedFile, Generic[DATUM_TYPE_VAR]):
    """A generic .mat file class."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    WAVEFORM_TYPE = Waveform
    # a lookup for the byte formats provided by the .wfm file
    _ENDIAN_PREFIX_LOOKUP: ClassVar[Dict[bytes, Endian]] = {
        b"MI": Endian(struct=">", from_byte="little", format=b"MI"),
        b"IM": Endian(struct="<", from_byte="big", format=b"IM"),
    }

    _MAT_VALUE_LOOKUP: ClassVar[Dict[int, ByteData]] = {
        1: SignedChar,
        2: UnsignedChar,
        3: Short,
        4: UnsignedShort,
        5: Long,
        6: UnsignedLong,
        7: Float,
        9: Double,
        10: UnsignedChar,
        12: LongLong,
        13: UnsignedLongLong,
        14: Matrix,
        16: String,
    }

    _WAVEFORM_PROPERTIES = bidict(
        {
            "source_name": "waveformSource",
            "y_axis_units": "horizontalUnits",
            "x_axis_units": "verticalUnits",
            "trigger_index": "zeroIndex",
            "x_axis_spacing": "sampleInterval",
        },
    )

    ################################################################################################
    # Public Methods
    ################################################################################################

    # Reading
    def check_style(self) -> bool:
        """Check which datat type is used for the read file.

        Returns:
            Whether this data type can contain the data from the file.
        """
        # seek out the past the header of the mat file
        self.fd.seek(126)
        # check the endian type
        (byte_order,) = struct.unpack(">2s", self.fd.read(2))
        if byte_order in self._ENDIAN_PREFIX_LOOKUP:
            endian_prefix = self._ENDIAN_PREFIX_LOOKUP[byte_order]
        else:
            msg = "Endian Format in wfm invalid."
            raise ValueError(msg)
        values = []
        # keep running through the file
        all_conditionals_true = False
        while not all_conditionals_true:
            _, read_values = self._unpack_data(endian_prefix)
            values.extend(read_values)
            all_conditionals_true = str(self).encode("utf_8") in values

        return all_conditionals_true

    # Reading
    def read_datum(self) -> WAVEFORM_TYPE:
        """Unpack a provided .wfm file.

        Returns:
            A waveform filled with information from the .wfm file.
        """
        formatted_data = sio.loadmat(self.file_path)
        return self._convert_from_formatted_data(formatted_data)

    # Writing
    def write_datum(self, waveform: Waveform) -> None:
        """Pack to a provided .wfm file.

        Args:
            waveform: The waveform to pack into the .wfm file.
        """
        formatted_data = self._convert_to_formatted_data(waveform)
        sio.savemat(self.file_path, formatted_data)

    ################################################################################################
    # Private Methods
    ################################################################################################

    # Reading
    def _unpack_data(self, endian_prefix: Endian) -> Tuple[int, bytes | List[Any]]:
        """Unpack the .mat values.

        Args:
            endian_prefix: What endian type is used to unpakc the information.

        Returns:
            The number of bytes were read from the section, along with the data read.
        """
        # unpack the value type
        value_type = Long.unpack(endian_prefix.struct, self.fd)
        data_type = self._MAT_VALUE_LOOKUP[value_type]
        # unpack the total bytes in the variable
        total_bytes = Long.unpack(endian_prefix.struct, self.fd)
        read_bytes = 0
        values = []
        while read_bytes < total_bytes:
            # if the data type is a matrix, the unpack method is going to recurse
            if data_type == Matrix:
                # to read the value, we need to know the value type and the byte length
                read_bytes += Long.length + Long.length
                # recurse
                byte_count, read_values = self._unpack_data(endian_prefix)
                read_bytes += byte_count
                values.append(read_values)
            else:
                value = data_type.unpack(endian_prefix.struct, self.fd)
                read_bytes += data_type.length
                values.append(value)

        # must abide by 64 bit boundary
        if total_bytes % 8:
            self.fd.read(8 - (total_bytes % 8))
            total_bytes += 8 - (total_bytes % 8)

        # convert the signed char data type to string
        if data_type == SignedChar:
            return total_bytes, b"".join(value.to_bytes(1, "little") for value in values)
        if data_type == String:
            return total_bytes, b"".join(values)

        return total_bytes, values

    # Reading
    def _convert_from_formatted_data(self, formatted_data: Dict[str, Any]) -> WAVEFORM_TYPE:
        """Convert the data from a formatted dictionary to a waveform.

        Args:
            formatted_data: The formatted dictionary from the file.

        Returns:
            Returns an analog waveform created from the formatted dictionary.
        """
        waveform: DATUM_TYPE_VAR = self.WAVEFORM_TYPE()  # pylint: disable=abstract-class-instantiated

        for key in formatted_data:
            if key in self._WAVEFORM_PROPERTIES.inverse:
                setattr(
                    waveform,
                    self._WAVEFORM_PROPERTIES.inverse[key],
                    formatted_data[key].flatten()[0],
                )
        numpy_x_axis_values = np.array(formatted_data["time"][:, 0]) / waveform.x_axis_spacing
        waveform.x_axis_values = numpy_x_axis_values
        normalized_vertical_values = Normalized(formatted_data["data"][:, 0], as_type=np.float32)
        vertical_minimum = normalized_vertical_values.min()
        vertical_maximum = normalized_vertical_values.max()
        vertical_axis_spacing = (vertical_maximum - vertical_minimum) / (
            type_max(np.dtype(np.int16)) - type_min(np.dtype(np.int16))
        )
        vertical_axis_offset = (vertical_maximum + vertical_minimum) / 2

        self._set_vertical_values(
            waveform,
            RawSample(normalized_vertical_values, as_type=np.int16),
            vertical_axis_offset,
            vertical_axis_spacing,
        )
        return waveform

    # Writing
    def _convert_to_formatted_data(self, waveform: WAVEFORM_TYPE) -> Dict[str, Any]:
        """Convert the data from an analog waveform class to a formatted dictionary.

        Args:
            waveform: The formatted data from the file.

        Returns:
            Returns an analog waveform created from the formatted data.
        """
        formatted_data = {}
        version = 1.0
        # create the header of the .mat file
        now = datetime.datetime.now(tz=tzlocal())
        if self.product.name != "TEKSCOPE":  # noqa: SIM108
            model = self.product.name
        else:
            model = "MSO54"  # TODO: change this default model
        formatted_data["__header__"] = (
            f"MATLAB 5.0 MAT-file. Tek Waveform Writer Version: {version}\n"
            f"Platform: {model}\n"
            f"Created on {now.strftime('%A')[0:3]} {now.strftime('%B')} "
            f"{now.hour}:{now.minute}:{now.second} {now.year}"
        ).encode()
        formatted_data["__version__"] = 1.0
        formatted_data["__globals__"] = []

        formatted_data["model"] = model
        formatted_data["waveformType"] = str(self)
        for key, value in self._WAVEFORM_PROPERTIES.items():
            try:
                formatted_data[value] = float(getattr(waveform, key))
            except ValueError:  # noqa: PERF203
                formatted_data[value] = str(getattr(waveform, key))
            except TypeError:
                # if None
                formatted_data[value] = ""

        if not formatted_data["waveformSource"]:
            formatted_data["waveformSource"] = "CH1"
        formatted_data["data"] = self._get_vertical_values(waveform)[:, None]
        formatted_data["time"] = waveform.normalized_horizontal_values[:, None]
        return formatted_data

    # Reading
    @abstractmethod
    def _set_vertical_values(
        self,
        waveform: Waveform,
        vertical_values: MeasuredData,
        vertical_offset: float,
        vertical_spacing: float,
    ) -> None:
        """Set the vertical values of the waveform.

        Args:
            waveform: The waveform which the vertical axis are set.
            vertical_values: The values that lie on the vertical axis.
            vertical_offset: The offset of the vertical axis.
            vertical_spacing: The spacing between each value on the vertical axis.
        """
        raise NotImplementedError

    # Writing
    @abstractmethod
    def _get_vertical_values(self, waveform: Waveform) -> MeasuredData:
        """Get the vertical values from the waveform to a generic type.

        Args:
            waveform: The waveform to get the vertical values from.

        Returns:
            The vertical values that are from the waveform.
        """
        raise NotImplementedError
