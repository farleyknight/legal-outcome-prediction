"""Integration tests for Matt Clark dataset download from archive.org."""

import os

import pytest

from src.matt_clark_downloader import MATT_CLARK_DIR, download_cases, download_entries


# Skip if cases.zip already exists to avoid repeated large downloads
CASES_ZIP_PATH = MATT_CLARK_DIR / "cases.zip"


@pytest.mark.skipif(
    CASES_ZIP_PATH.exists(),
    reason=f"cases.zip already exists at {CASES_ZIP_PATH}",
)
def test_download_cases_file():
    """Test that download_cases() downloads cases.zip from archive.org.

    This test makes a real HTTP request to archive.org and downloads
    the cases.zip file (~600MB). It is skipped if the file already exists.
    """
    # Download cases.zip
    result = download_cases()

    # Verify download succeeded
    assert result is True, "download_cases() returned False"

    # Verify file was created
    assert CASES_ZIP_PATH.exists(), f"Expected {CASES_ZIP_PATH} to exist after download"

    # Verify file size is reasonable (> 1MB to ensure not empty/error page)
    file_size = CASES_ZIP_PATH.stat().st_size
    min_size = 1 * 1024 * 1024  # 1 MB
    assert file_size > min_size, f"File size {file_size} bytes is too small (< 1MB)"

    # Log actual size for reference
    size_mb = file_size / (1024 * 1024)
    print(f"Downloaded cases.zip: {size_mb:.1f} MB")


# Skip if 2024entries.zip already exists to avoid repeated large downloads
ENTRIES_2024_ZIP_PATH = MATT_CLARK_DIR / "2024entries.zip"


@pytest.mark.skipif(
    ENTRIES_2024_ZIP_PATH.exists(),
    reason=f"2024entries.zip already exists at {ENTRIES_2024_ZIP_PATH}",
)
def test_download_entries_file():
    """Test that download_entries() downloads entries files from archive.org.

    This test makes a real HTTP request to archive.org and downloads
    the 2024entries.zip file. It is skipped if the file already exists.
    """
    # Download entries for 2024 only
    result = download_entries(years=[2024])

    # Verify download succeeded
    assert result == {2024: True}, f"download_entries() returned {result}, expected {{2024: True}}"

    # Verify file was created
    assert ENTRIES_2024_ZIP_PATH.exists(), f"Expected {ENTRIES_2024_ZIP_PATH} to exist after download"

    # Verify file size is reasonable (> 1MB to ensure not empty/error page)
    file_size = ENTRIES_2024_ZIP_PATH.stat().st_size
    min_size = 1 * 1024 * 1024  # 1 MB
    assert file_size > min_size, f"File size {file_size} bytes is too small (< 1MB)"

    # Log actual size for reference
    size_mb = file_size / (1024 * 1024)
    print(f"Downloaded 2024entries.zip: {size_mb:.1f} MB")
