"""Read and extract files from TSS (Tektronix Signal Suite) archives.

TSS files are ZIP archives containing waveform files (``.wfm``) and other associated files.
"""

import contextlib
import shutil
import sys
import tempfile
import zipfile

from collections.abc import Iterator
from pathlib import Path
from types import TracebackType

from typing_extensions import Self

from tm_data_types.datum.datum import Datum
from tm_data_types.io_factory_methods import read_file

MIN_MAIN_ARGS = 2


class TSSReader:
    """Read and extract files from TSS (ZIP) archives.

    TSS files are ZIP archives that can contain waveform files (``.wfm``) and other
    associated files. This class provides methods to:

    - Iterate through files in the archive (optionally filtered by extension)
    - Read waveforms directly from the archive (using temporary files)
    - Extract files to disk
    - Get metadata about files in the archive

    The class is a context manager and should be used with a ``with`` statement
    to ensure proper cleanup of resources.

    Example:
        >>> with TSSReader("file.tss") as tss:
        >>>     for wfm_file in tss.iter_files(extension=".wfm"):
        >>>         waveform = tss.read_waveform(wfm_file)
    """

    def __init__(self, tss_path: str) -> None:
        """Initialize TSS reader.

        Args:
            tss_path: Path to the TSS file (ZIP archive).

        Raises:
            FileNotFoundError: If the TSS file doesn't exist.
            zipfile.BadZipFile: If the file is not a valid ZIP archive.
        """
        self.tss_path = Path(tss_path)
        if not self.tss_path.exists():
            msg = f"TSS file not found: {tss_path}"
            raise FileNotFoundError(msg)

        self._zip: zipfile.ZipFile | None = None
        self._temp_dir: Path | None = None

    def __enter__(self) -> Self:
        """Open the TSS archive when entering context manager."""
        try:
            self._zip = zipfile.ZipFile(self.tss_path, "r")
        except zipfile.BadZipFile as exc:
            msg = f"Not a valid ZIP archive: {self.tss_path}"
            raise zipfile.BadZipFile(msg) from exc
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close the TSS archive and clean up temporary files."""
        if self._zip:
            self._zip.close()
            self._zip = None

        if self._temp_dir:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None

    def iter_files(self, extension: str | None = None) -> Iterator[str]:
        """Iterate over file names in the archive, optionally filtered by extension.

        Args:
            extension: Optional file extension to filter by (e.g., ``".wfm"``).
                Case-insensitive. If ``None``, returns all files.

        Yields:
            File names (paths) within the archive.
        """
        if self._zip is None:
            msg = "TSS archive not open. Use 'with TSSReader(...)' context manager."
            raise RuntimeError(msg)

        if extension is None:
            yield from self._zip.namelist()
            return

        extension_lower = extension.lower()
        for name in self._zip.namelist():
            if name.lower().endswith(extension_lower):
                yield name

    def get_file_info(self, archive_path: str) -> zipfile.ZipInfo:
        """Get metadata about a file in the archive.

        Args:
            archive_path: Path to the file within the archive.

        Returns:
            ZipInfo object containing file metadata (size, date, etc.).

        Raises:
            RuntimeError: If the archive has not been opened.
            KeyError: If the file doesn't exist in the archive.
        """
        if self._zip is None:
            msg = "TSS archive not open. Use 'with TSSReader(...)' context manager."
            raise RuntimeError(msg)

        try:
            return self._zip.getinfo(archive_path)
        except KeyError as exc:
            msg = f"File not found in archive: {archive_path}"
            raise KeyError(msg) from exc

    def extract_to_disk(self, archive_path: str, output_dir: str) -> Path:
        """Extract a file from the archive to disk.

        Args:
            archive_path: Path to the file within the archive.
            output_dir: Directory to extract the file to. Created if needed.

        Returns:
            Path to the extracted file.

        Raises:
            RuntimeError: If the archive has not been opened.
            KeyError: If the file doesn't exist in the archive.
            OSError: If the file cannot be written to disk.
        """
        if self._zip is None:
            msg = "TSS archive not open. Use 'with TSSReader(...)' context manager."
            raise RuntimeError(msg)

        if archive_path not in self._zip.namelist():
            msg = f"File not found in archive: {archive_path}"
            raise KeyError(msg)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        extracted_path = output_path / Path(archive_path).name
        with self._zip.open(archive_path) as source, open(extracted_path, "wb") as target:
            target.write(source.read())

        return extracted_path

    def read_waveform(self, archive_path: str) -> Datum:
        """Read a waveform directly from the archive.

        Extracts the file to a temporary location, reads it with
        :func:`~tm_data_types.read_file`, and cleans up when the context exits.

        Args:
            archive_path: Path to the ``.wfm`` file within the archive.

        Returns:
            Waveform object (``AnalogWaveform``, ``DigitalWaveform``, or ``IQWaveform``).

        Raises:
            RuntimeError: If the archive has not been opened.
            KeyError: If the file doesn't exist in the archive.
            OSError: If the file cannot be read.
            TypeError: If the waveform type cannot be determined.
            ValueError: If waveform contents cannot be converted.
        """
        if self._zip is None:
            msg = "TSS archive not open. Use 'with TSSReader(...)' context manager."
            raise RuntimeError(msg)

        if archive_path not in self._zip.namelist():
            msg = f"File not found in archive: {archive_path}"
            raise KeyError(msg)

        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="tss_reader_"))

        temp_file_path = self._temp_dir / Path(archive_path).name

        with self._zip.open(archive_path) as source, open(temp_file_path, "wb") as target:
            target.write(source.read())

        try:
            return read_file(str(temp_file_path))
        except (OSError, RuntimeError, TypeError, ValueError):
            if temp_file_path.exists():
                temp_file_path.unlink()
            raise


def main() -> None:
    """List and read waveforms from a TSS archive (CLI entry point)."""
    if len(sys.argv) < MIN_MAIN_ARGS:
        sys.exit(1)

    tss_path = sys.argv[1]

    try:
        with TSSReader(tss_path) as tss:
            for file_name in sorted(tss.iter_files()):
                tss.get_file_info(file_name)

            if wfm_files := list(tss.iter_files(extension=".wfm")):
                for wfm_file in sorted(wfm_files):
                    with contextlib.suppress(
                        OSError,
                        RuntimeError,
                        TypeError,
                        ValueError,
                        KeyError,
                    ):
                        tss.read_waveform(wfm_file)

    except (zipfile.BadZipFile, OSError, RuntimeError, TypeError, ValueError):
        sys.exit(1)


if __name__ == "__main__":
    main()
