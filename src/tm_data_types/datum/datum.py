"""A base class which is an abstract representation of all information from a tektronix device."""

from abc import ABC

from typing_extensions import Self


# pylint: disable=too-few-public-methods
class Datum(ABC):  # noqa: B024
    """The base class for all data formats."""

    ################################################################################################
    # Public Methods
    ################################################################################################

    def copy(self) -> Self:
        """Copy the datum and it's contents to a new datum.

        Returns:
            The new datum that is a copy of the original.
        """
        new_datum = type(self)()
        new_datum.__dict__ = self.__dict__.copy()
        return new_datum
