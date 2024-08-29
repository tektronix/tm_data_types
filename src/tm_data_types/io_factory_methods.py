"""Factory methods to read and write to a generic file using generic data."""

import multiprocessing
import os
from typing import List, Optional

from typing_extensions import TypeVar

from tm_data_types.datum.datum import Datum
from tm_data_types.files_and_formats.waveform_file import AbstractedFile
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform
from tm_data_types.datum.waveforms.iq_waveform import IQWaveform
from tm_data_types.helpers.class_lookup import (
    find_class_format,
    find_class_format_list,
    access_type,
    FileExtensions,
    CSVFormats,
)
from tm_data_types.helpers.instrument_series import InstrumentSeries

DatumAlias = TypeVar("DatumAlias", bound=Datum, default=Datum)


# pylint: disable=unused-argument
def write_file(
    file_path: str,
    datum: Datum,
    product: InstrumentSeries = InstrumentSeries.TEKSCOPE,
    file_format: Optional[CSVFormats] = None,
) -> None:
    """Write a waveform to a provided file.

    Args:
        file_path: The path file to write to.
        datum: The datum that is being written.
        product: The product being written to.
        file_format: A specialized file format we are writing as.
    """

    _, path_extension = os.path.splitext(file_path)
    try:
        file_extension = FileExtensions[path_extension.replace(".", "").upper()]
    except KeyError as e:
        raise IOError(f"The {path_extension} extension cannot be written to.") from e
    # find the format based on the waveform extension
    format_class: AbstractedFile = find_class_format(file_extension, type(datum))
    # using __init__ for instantiation due to pyright confusion
    format_class = format_class(file_path, access_type(file_extension, write=True), product)
    with format_class as fd:
        fd.write_datum(datum)


def read_file(file_path: str) -> DatumAlias:
    """Read a waveform from a provided file.

    Args:
        file_path: The path file to read from.
    """
    _, path_extension = os.path.splitext(file_path)
    try:
        file_extension = FileExtensions[path_extension.replace(".", "").upper()]
    except KeyError as e:
        raise IOError(f"The {path_extension} extension cannot be read from.") from e
    class_formats: List[AbstractedFile] = find_class_format_list(file_extension)
    for file_format in class_formats:
        with file_format(file_path, access_type(file_extension, write=False)) as fd:
            if fd.check_style():
                waveform = fd.read_datum()
                return waveform
    raise TypeError("No class found which associates with this file extension and data format.")


def read_analog_file(file_path: str) -> AnalogWaveform:
    """Read a waveform from a provided file, type hinted as an AnalogWaveform.

    Args:
        file_path: The path file to read from.
    """
    return read_file(file_path)


def read_iq_file(file_path: str) -> IQWaveform:
    """Read a waveform from a provided file, type hinted as an IQWaveform.

    Args:
        file_path: The path file to read from.
    """
    return read_file(file_path)


def _write_files(
    file_paths: List[str],
    datums: List[Datum],
    product: InstrumentSeries = InstrumentSeries.TEKSCOPE,
    file_format: Optional[CSVFormats] = None,
) -> None:
    """Write a list of waveforms to a list of provided files.

    Args:
        file_paths: The path file to write to.
        datums: The datum that is being written.
        product: The product being written to.
        file_format: A specialized file format we are writing as.
    """
    for file_path, datum in zip(file_paths, datums):
        write_file(file_path, datum, product, file_format)


# pylint: disable=unused-argument
def write_files_in_parallel(
    file_paths: List[str],
    datums: List[Datum],
    force_process_count: int = 4,
    product: InstrumentSeries = InstrumentSeries.TEKSCOPE,
    file_format: Optional[CSVFormats] = None,
) -> None:
    """Write a list of waveforms to a list of provided files in parallel.

    Args:
        file_paths: The path file to write to.
        datums: The datum that is being written.
        force_process_count: The number of processes that will be created.
        product: The product being written to.
        file_format: A specialized file format we are writing as.
    """
    if len(file_paths) != len(datums):
        msg = "The number of files paths must be equal to the number of waveforms to write."
        raise IndexError(msg)
    process_count = min(force_process_count, len(file_paths))
    with multiprocessing.Pool(process_count) as process_pool:
        previous_index = 0
        for index in range(process_count):
            end_index = min(
                round((index + 1) * (len(file_paths) / process_count)) + 1,
                len(file_paths),
            )
            result = process_pool.apply_async(
                _write_files,
                args=(
                    file_paths[previous_index:end_index],
                    datums[previous_index:end_index],
                ),
            )
            previous_index = end_index

        for index in range(process_count):
            try:
                result.get()
            except Exception as e:
                raise ChildProcessError(f"Error on process {index}, view process stack.") from e


def _read_files(file_paths: str, file_queue: multiprocessing.Queue) -> None:
    """Read a waveform from a provided file.

    Args:
        file_paths: The file paths to read from.
        file_queue: The queue to put the read data into.
    """
    for file_path in file_paths:
        file_queue.put((file_path, read_file(file_path)))


def read_files_in_parallel(file_paths: List[str], force_process_count: int = 4) -> List[Datum]:
    """Read a list of files in parallel.

    Args:
        file_paths: The file paths to read from.
        force_process_count: The number of processes that should be created for this operation.
    """
    process_count = min(force_process_count, len(file_paths))
    with multiprocessing.Pool(process_count) as process_pool:
        previous_index = 0
        manager = multiprocessing.Manager()
        file_queue = manager.Queue()
        for index in range(process_count):
            end_index = min(
                round((index + 1) * (len(file_paths) / process_count)) + 1,
                len(file_paths),
            )

            result = process_pool.apply_async(
                _read_files,
                args=(
                    file_paths[previous_index:end_index],
                    file_queue,
                ),
            )
            previous_index = end_index

        for index in range(process_count):
            try:
                result.get()
            except Exception as e:
                raise ChildProcessError(f"Error on process {index}, view process stack.") from e

    file_queue.put(None)
    return list(iter(file_queue.get, None))
