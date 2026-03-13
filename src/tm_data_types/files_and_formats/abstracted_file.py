"""The base file type which abstracts all file formats."""

from abc import ABC, abstractmethod
from typing import Dict, Generic, Optional, TextIO, TypeVar

from bidict import bidict
from typing_extensions import Self

from tm_data_types.datum.datum import Datum
from tm_data_types.helpers.instrument_series import InstrumentSeries

DATUM_TYPE_VAR = TypeVar("DATUM_TYPE_VAR", bound=Datum)


class AbstractedFile(ABC, Generic[DATUM_TYPE_VAR]):
    """An abstracted base class containing basic filestream functionality."""

    ################################################################################################
    # Dunder Methods
    ################################################################################################

    def __init__(
        self,
        file_path: str,
        io_type: str,
        product: Optional[InstrumentSeries] = InstrumentSeries.TEKSCOPE,
    ) -> None:
        """Initialize the file like class.

        Args:
            file_path: The path for the file to read/write from.
            io_type: A file to represent what type of IO transference is occurring.
            product: The product the file is associated with.
        """
        self.file_path = file_path
        self.io_type = io_type
        self.product = product
        self.fd: TextIO

    def __enter__(self) -> Self:
        """Open a filestream for the file when entering a with statement.

        Returns:
            The instance where the filestream has been created.
        """
        self.fd = open(self.file_path, self.io_type)  # pylint: disable=unspecified-encoding
        return self

    def __exit__(self, *args: object) -> None:
        """Close the filestream when exiting a with statement."""
        self.fd.close()

    ################################################################################################
    # Public Methods
    ################################################################################################

    # Reading
    def read(self) -> str:
        """A wrapper for the filestream read method."""
        return self.fd.read()

    # Writing
    def write(self, to_write_info: str) -> None:
        """A wrapper for the filestream write method.

        Args:
            to_write_info: The information to write to the file.
        """
        self.fd.write(to_write_info)

    @staticmethod
    def update_bidict(original_bidict: bidict, operating_bidict: Dict[str, str]) -> bidict:
        """Update a bidirectional dict with new values.

        This may need to be a factory helper.

        Args:
            original_bidict: The bidirectional dictionary that needs new items to be added to it.
            operating_bidict: The bidirectional dictionary the new items are being taken from.
        """
        new_bidict = original_bidict.copy()
        for key, value in operating_bidict.items():
            new_bidict[key] = value
        return new_bidict

    @abstractmethod
    def check_style(self) -> bool:
        """Check the style of the file to put declare what waveform type the data is.

        Returns:
            A boolean indicating that the current waveform type is the correct one.
        """
        raise NotImplementedError

    # Reading
    @abstractmethod
    def read_datum(self) -> DATUM_TYPE_VAR:
        """Read the waveform data from a file."""
        raise NotImplementedError

    # Writing
    @abstractmethod
    def write_datum(self, waveform: DATUM_TYPE_VAR) -> None:
        """Write waveform data to a file.

        Args:
            waveform: The waveform to write to a file.
        """
        raise NotImplementedError
