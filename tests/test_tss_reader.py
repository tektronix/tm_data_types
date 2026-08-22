"""Tests for TSS archive reading."""

from pathlib import Path

import pytest

from tm_data_types import read_file, TSSReader
from tm_data_types.datum.waveforms.waveform import Waveform

TSS_FIXTURE = Path(__file__).resolve().parent / "waveforms/tss/Tek000.tss"


@pytest.mark.skipif(not TSS_FIXTURE.exists(), reason="TSS fixture missing")
def test_tss_iter_files_lists_wfm_members() -> None:
    with TSSReader(TSS_FIXTURE.as_posix()) as tss:
        wfm_files = list(tss.iter_files(extension=".wfm"))

    assert len(wfm_files) > 0
    assert all(name.lower().endswith(".wfm") for name in wfm_files)


@pytest.mark.skipif(not TSS_FIXTURE.exists(), reason="TSS fixture missing")
def test_tss_read_waveform_returns_waveform() -> None:
    with TSSReader(TSS_FIXTURE.as_posix()) as tss:
        wfm_path = next(tss.iter_files(extension=".wfm"))
        waveform = tss.read_waveform(wfm_path)

    assert isinstance(waveform, Waveform)
    assert waveform.record_length > 0


@pytest.mark.skipif(not TSS_FIXTURE.exists(), reason="TSS fixture missing")
def test_tss_read_waveform_matches_extracted_read_file(tmp_path: Path) -> None:
    with TSSReader(TSS_FIXTURE.as_posix()) as tss:
        wfm_path = next(tss.iter_files(extension=".wfm"))
        from_archive = tss.read_waveform(wfm_path)
        extracted = tss.extract_to_disk(wfm_path, tmp_path.as_posix())

    from_disk = read_file(extracted.as_posix())
    assert from_archive.record_length == from_disk.record_length
