"""The file formatting for a .csv file."""

import csv

from abc import abstractmethod
from typing import Generic, Tuple

import numpy as np

from bidict import bidict

from tm_data_types.datum.data_types import MeasuredData
from tm_data_types.datum.waveforms.waveform import Waveform, WaveformMetaInfo
from tm_data_types.files_and_formats.abstracted_file import AbstractedFile, DATUM_TYPE_VAR


class CSVFile(AbstractedFile, Generic[DATUM_TYPE_VAR]):
    """A generic .csv file class."""

    ################################################################################################
    # Class Variables
    ################################################################################################

    WAVEFORM_TYPE = Waveform
    META_DATA_TYPE = WaveformMetaInfo

    _META_DATA_LOOKUP = bidict(
        {
            "trigger_index": "Zero Index",
            "y_offset": "yOffset",
            "y_position": "yPosition",
            "analog_thumbnail": "ANALOG_Thumbnail",
            "clipping_initialized": "clippingInitialized",
            "interpretor_factor": "interpFactor",
            "real_data_start_index": "realDataStartIndex",
            "waveform_label": "Label",
        },
    )

    ################################################################################################
    # Public Methods
    ################################################################################################
    # Reading
    def check_style(self) -> bool:
        """Check the style of the data to determine which format to use.

        Returns:
            Whether this is the correct format to use.
        """
        self.fd.seek(0)
        return self._check_file_contents()

    # Reading
    def read_datum(self) -> WAVEFORM_TYPE:  # pylint: disable=too-many-branches  # noqa: C901,PLR0912
        """Read the data from the csv file and process it into a waveform.

        Returns:
            The waveform that contains data processed from the csv file.
        """
        meta_dict = {}

        waveform_properties = {
            "TIME": "source_name",
            "Sample Interval": "x_axis_spacing",
            "Horizontal Units": "x_axis_units",
            "Vertical Units": "y_axis_units",
            "Zero Index": "trigger_index",
        }

        # pylint: disable=abstract-class-instantiated
        waveform: DATUM_TYPE_VAR = self.WAVEFORM_TYPE()

        values_matrix = None
        record_length = None
        values_row = 0
        # iterate through every row in the csv
        for row in self.csv_reader:
            # if the row is not empty
            if len(row):
                try:
                    # try to convert the first column in the row to a float
                    if values_matrix is None:
                        float(row[0])
                        if not record_length:
                            msg = "No Record Length Provided in csv."
                            raise IOError(msg)
                        values_matrix = np.empty((record_length, len(row)))
                    for index, item in enumerate(row):
                        if len(row) != values_matrix.shape[1]:
                            msg = "CSV data not parseable."
                            raise IOError(msg)
                        values_matrix[values_row][index] = float(item)
                    values_row += 1
                except ValueError:
                    # otherwise the info is in the header
                    if len(row) > 1:
                        # record length is special as it needs to be stored, but it's not relevant
                        # to the waveform values
                        if row[0] == "Record Length":
                            record_length = int(row[1])
                        # time can have multiple values in the row
                        elif row[0] == "TIME":
                            waveform.source_name = ",".join(row[1:])
                        # check to see if it can be put into the waveform
                        elif row[0] in waveform_properties:
                            try:
                                setattr(waveform, waveform_properties[row[0]], float(row[1]))
                            except ValueError:
                                setattr(waveform, waveform_properties[row[0]], row[1])
                        # otherwise, try and put it into the meta information
                        elif row[0] in self._META_DATA_LOOKUP.inverse:
                            meta_dict[row[0]] = row[1]
                        else:
                            pass

        numpy_x_axis_values = np.array(values_matrix[:, 0]) / waveform.x_axis_spacing
        waveform.x_axis_values = numpy_x_axis_values
        waveform.meta_info = self.META_DATA_TYPE(**meta_dict)
        self._set_waveform_values(waveform, values_matrix)
        return waveform

    # Writing
    def write_datum(self, waveform: WAVEFORM_TYPE) -> None:
        """Write a waveform to a csv file.

        Args:
            waveform: The waveform to use for data when writing.
        """
        output = self._setup_generic_csv_header(waveform)
        output += self._setup_waveform_headers(waveform)

        vertical_values, csv_format, channels = self._formatted_waveform_values(waveform)

        output += f"\nLabels{''.join([',' for _ in range(vertical_values.shape[1])])}\n"
        output += f"TIME,{channels}"

        np.savetxt(
            self.file_path,
            np.c_[waveform.normalized_horizontal_values, vertical_values],
            delimiter=",",
            fmt=csv_format,
            header=output,
            comments="",
        )

    ################################################################################################
    # Properties
    ################################################################################################

    # Reading
    @property
    def csv_reader(self) -> csv.reader:
        """The reader for the csv file.

        Returns:
            The csv reader object.
        """
        return csv.reader(self.fd)

    # Writing
    @property
    def csv_writer(self) -> csv.writer:
        """The writer for the csv file.

        Returns:
            The csv writer object.
        """
        return csv.writer(self.fd)

    ################################################################################################
    # Private Methods
    ################################################################################################
    # Writing
    def _setup_generic_csv_header(self, waveform: Waveform) -> str:
        """Set up the generic header values for the csv file during writing.

        Args:
            waveform: The waveform used to get the generic header values.

        Returns:
            The values to append to the output.
        """
        if self.product.name != "TEKSCOPE":  # noqa: SIM108
            model = self.product.name
        else:
            model = "MSO54"  # TODO: change this default model
        output = f"Model,{model}\n"
        output += f"Waveform Type,{self!s}\n"
        output += f"Zero Index,{waveform.trigger_index}\n"
        output += f"Sample Interval,{waveform.x_axis_spacing}\n"
        output += f"Record Length,{waveform.record_length}\n"
        output += f"Horizontal Units,{waveform.x_axis_units}\n"

        if waveform.meta_info is not None:
            operable_metadata = self.META_DATA_TYPE.remap(
                self._META_DATA_LOOKUP,
                waveform.meta_info.operable_metainfo(),
                True,
            )
            for key, item in operable_metadata.items():
                output += f"{key},{item!s}\n"

        return output

    # Reading
    @abstractmethod
    def _check_file_contents(self) -> bool:
        """Check the contents of the file and find information that dictates which format to use.

        Returns:
            Whether this is the correct format to use.
        """
        raise NotImplementedError

    # Reading
    @abstractmethod
    def _set_waveform_values(self, waveform: Waveform, values_matrix: np.ndarray) -> None:
        """Set the vertical values for the waveform using the csv data.

        Args:
            waveform: The waveform which is being formatted.
            values_matrix: A matrix for all values from the csv file.
        """
        raise NotImplementedError

    # Writing
    @abstractmethod
    def _setup_waveform_headers(self, waveform: Waveform) -> str:
        """Set up the headers specific to each waveform type.

        Args:
            waveform: The waveform to use when setting up the specific headers.

        Returns:
            The specific waveform headers to append to the csv output.
        """
        raise NotImplementedError

    # Writing
    @abstractmethod
    def _formatted_waveform_values(self, waveform: Waveform) -> Tuple[MeasuredData, str, str]:
        """Return the formatted information for csv writing.

        Args:
            waveform: The waveform to use when setting up the formatted information.

        Returns:
            The normalized vertical values, the csv format, and the channels to use.
        """
        raise NotImplementedError
