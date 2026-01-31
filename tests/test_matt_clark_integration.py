"""Integration tests for Matt Clark dataset download from archive.org."""

import os

import pytest

from src.matt_clark_downloader import MATT_CLARK_DIR, download_cases, download_entries
from src.matt_clark_parser import load_cases_df
import src.matt_clark_parser as matt_clark_parser


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


@pytest.mark.skipif(
    not CASES_ZIP_PATH.exists(),
    reason=f"cases.zip does not exist at {CASES_ZIP_PATH}",
)
def test_case_lookup_real_data():
    """Test that cases.csv data can be loaded and queried by court_id and docket number.

    This test loads the actual cases.csv from cases.zip and verifies that
    cases can be looked up using the real column names (court_id, number).

    Note: The Matt Clark dataset uses these columns:
    - id: Unique case identifier
    - court_id: Integer court identifier
    - number: Docket number (e.g., "2:25-cv-00959")
    - name: Case name
    """
    try:
        # Load real cases data
        cases_df = load_cases_df()

        # Verify we loaded some data
        assert len(cases_df) > 0, "Expected non-empty cases DataFrame"

        # Verify expected columns exist
        expected_columns = ['id', 'court_id', 'number', 'name']
        for col in expected_columns:
            assert col in cases_df.columns, f"Expected column '{col}' in cases DataFrame"

        print(f"Loaded {len(cases_df)} cases with columns: {list(cases_df.columns)}")

        # Pick a sample case from the DataFrame (first row)
        sample_case = cases_df.iloc[0]
        court_id = sample_case['court_id']
        docket_number = sample_case['number']
        case_id = sample_case['id']

        print(f"Sample case: id={case_id}, court_id={court_id}, number={docket_number}")

        # Query by court_id and docket number directly
        matches = cases_df[
            (cases_df['court_id'] == court_id) &
            (cases_df['number'] == docket_number)
        ]

        # Verify the case was found
        assert len(matches) >= 1, f"Expected to find case for court_id={court_id}, number={docket_number}"

        found_case = matches.iloc[0]

        # Verify key fields match
        assert found_case['court_id'] == court_id, "Court ID should match"
        assert found_case['number'] == docket_number, "Docket number should match"
        assert found_case['id'] == case_id, "Case ID should match"

        # Verify required fields are not null
        assert found_case['id'] is not None, "id should not be None"
        assert found_case['court_id'] is not None, "court_id should not be None"

        print(f"Successfully found case: id={found_case['id']}, name={found_case.get('name', 'N/A')}")

    finally:
        # Clear the parser cache to avoid memory bloat between tests
        matt_clark_parser._cases_df = None
