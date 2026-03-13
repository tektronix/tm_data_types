"""Factory methods to read and write to a generic file using generic data."""

import multiprocessing
import os

from typing import List, Optional, TYPE_CHECKING

from typing_extensions import TypeVar

from tm_data_types.datum.datum import Datum
from tm_data_types.datum.waveforms.analog_waveform import AnalogWaveform
from tm_data_types.datum.waveforms.iq_waveform import IQWaveform
from tm_data_types.helpers.class_lookup import (
    access_type,
    CSVFormats,
    FileExtensions,
    find_class_format,
    find_class_format_list,
)
from tm_data_types.helpers.instrument_series import InstrumentSeries

if TYPE_CHECKING:
    from tm_data_types.files_and_formats.abstracted_file import AbstractedFile

DatumAlias = TypeVar("DatumAlias", bound=Datum, default=Datum)


# pylint: disable=unused-argument
def write_file(
    path: str,
    waveform: Datum,
    product: InstrumentSeries = InstrumentSeries.TEKSCOPE,
    file_format: Optional[CSVFormats] = None,  # noqa: ARG001
) -> None:
    """Write a waveform to a provided file.

    Process Overview:
        1. Lookup Table: The method begins by using a lookup table to determine the behavior based
            on the waveform type.
        2. Formatting: The waveform is formatted according to its type.
        3. Writing: Finally, the formatted waveform is written to the specified file path.

    Special Cases:
        - RawSample Type: No transformations are applied when saving data in the `.wfm`
            format, if the waveform is of the [`RawSample`][tm_data_types.RawSample] type. This is
            done to ensure that `.wfm` files are saved and loaded as quickly as possible.
        - Normalized Type: If the waveform is of the
            [`Normalized`][tm_data_types.datum.data_types.Normalized] type, a transformation is
            performed because `.wfm` files must contain digitized data, with spacing and offset
            stored separately.

    Args:
        path: The path file to write to.
        waveform: The waveform that is being written.
        product: The product being written to.
        file_format: A specialized file format we are writing as.
    """
    _, path_extension = os.path.splitext(path)
    try:
        file_extension = FileExtensions[path_extension.replace(".", "").upper()]
    except KeyError as e:
        msg = f"The {path_extension} extension cannot be written to."
        raise IOError(msg) from e
    # find the format based on the waveform extension
    format_class: AbstractedFile = find_class_format(file_extension, type(waveform))
    # using __init__ for instantiation due to pyright confusion
    format_class = format_class(path, access_type(file_extension, write=True), product)
    with format_class as fd:
        fd.write_datum(waveform)


def read_file(file_path: str) -> DatumAlias:
    """Read a waveform from a provided file.

    Process Overview:
        1. Lookup Table: Similar to  [`write_file()`][tm_data_types.write_file], a lookup table is
            used to determine the file extension.
        2. Type Detection: The method reads small sections of the file to identify the waveform
            type.
        3. Reformatting: The waveform is read and returned in the appropriate format, depending on
            how the data is structured.

    Special Cases:
        - All waveforms are returned in the [`RawSample`][tm_data_types.RawSample] format.
            The data is reformatted for compatibility with the oscilloscope, which involves
            mathematical transformations on the entire dataset. This can be time-consuming, so
            using the `.wfm` format is recommended for efficiency.

    Args:
        file_path: The path file to read from.
    """
    _, path_extension = os.path.splitext(file_path)
    try:
        file_extension = FileExtensions[path_extension.replace(".", "").upper()]
    except KeyError as e:
        msg = f"The {path_extension} extension cannot be read from."
        raise IOError(msg) from e
    class_formats: List[AbstractedFile] = find_class_format_list(file_extension)
    for file_format in class_formats:
        with file_format(file_path, access_type(file_extension, write=False)) as fd:
            if fd.check_style():
                return fd.read_datum()
    msg = "No class found which associates with this file extension and data format."
    raise TypeError(msg)


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
    for file_path, datum in zip(file_paths, datums, strict=False):
        write_file(file_path, datum, product, file_format)


def write_files_in_parallel(
    file_paths: List[str],
    datums: List[Datum],
    force_process_count: int = 4,
    product: InstrumentSeries = InstrumentSeries.TEKSCOPE,
    file_format: Optional[CSVFormats] = None,
) -> None:
    """Write a list of waveforms to a list of provided files in parallel.

    This method offers a parallelized approach to writing multiple waveform files.

    Process Overview:
        1. Multiprocessing: The lists of file paths and waveforms are partitioned and processed in
            parallel.
        2. Writing: Each process uses the same method as  [`write_file()`][tm_data_types.write_file]
            to save its assigned waveforms.

    This method is particularly useful for saving multiple waveform files efficiently.

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
                    product,
                    file_format,
                ),
            )
            previous_index = end_index

        for index in range(process_count):
            try:
                result.get()
            except Exception as e:  # noqa: PERF203
                msg = f"Error on process {index}, view process stack."
                raise ChildProcessError(msg) from e


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

    This method allows for the parallel reading of multiple waveform files.

    Process Overview:
        1. Multiprocessing: Similar to
            [`write_files_in_parallel()`][tm_data_types.write_files_in_parallel], the file paths are
            partitioned and processed in parallel.
        2. Reading: The waveforms are read using the same process as
            [`read_file()`][tm_data_types.read_file], and a queue of waveforms is returned.

    Args:
        file_paths: A list of file paths to read from.
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
            except Exception as e:  # noqa: PERF203
                msg = f"Error on process {index}, view process stack."
                raise ChildProcessError(msg) from e

    file_queue.put(None)
    return list(iter(file_queue.get, None))
