"""Tests for FJC data processing."""

import bz2
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from src import fjc_processor
from src.fjc_processor import download_fjc_data, extract_case_id, filter_nos, map_outcome, normalize_docket_number, _get_latest_quarterly_date


def test_placeholder():
    """Placeholder test to verify module imports."""
    assert fjc_processor is not None


def test_docket_normalization():
    """Test that normalize_docket_number handles various docket number formats."""
    # FJC short format: 2-digit year + sequence
    assert normalize_docket_number("191234") == "2019cv1234"
    assert normalize_docket_number("001234") == "2000cv1234"
    assert normalize_docket_number("991234") == "1999cv1234"

    # FJC long format: 4-digit year + sequence
    assert normalize_docket_number("20191234") == "2019cv1234"
    assert normalize_docket_number("19991234") == "1999cv1234"
    assert normalize_docket_number("202012345") == "2020cv12345"

    # CourtListener format with division prefix: "1:19-cv-01234"
    assert normalize_docket_number("1:19-cv-01234") == "2019cv01234"
    assert normalize_docket_number("2:21-cv-00001") == "2021cv00001"

    # Hyphenated format without prefix: "19-cv-1234"
    assert normalize_docket_number("19-cv-1234") == "2019cv1234"
    assert normalize_docket_number("21-cv-567") == "2021cv567"

    # Already semi-normalized: "1:2019cv12345"
    assert normalize_docket_number("1:2019cv12345") == "2019cv12345"
    assert normalize_docket_number("2019cv12345") == "2019cv12345"

    # Edge cases
    assert normalize_docket_number("") == ""
    assert normalize_docket_number("  191234  ") == "2019cv1234"  # whitespace
    assert normalize_docket_number("invalid-format") == "invalid-format"  # returns cleaned original


def test_download_fjc_data_returns_path(tmp_path):
    """Test that download_fjc_data returns a Path object."""
    # Create mock bz2-compressed CSV content
    csv_content = b"CIRCUIT,DISTRICT,NOS\n1,36,442\n"
    compressed_content = bz2.compress(csv_content)

    mock_response = MagicMock()
    mock_response.content = compressed_content
    mock_response.raise_for_status = MagicMock()

    cache_file = tmp_path / "fjc_civil.csv"

    with patch('src.fjc_processor.requests.get', return_value=mock_response), \
         patch('src.fjc_processor.CACHE_FILE', cache_file), \
         patch('src.fjc_processor.DATA_DIR', tmp_path):
        result = download_fjc_data()

    assert isinstance(result, Path)
    assert result.exists()
    assert result.read_text() == "CIRCUIT,DISTRICT,NOS\n1,36,442\n"


def test_get_latest_quarterly_date():
    """Test that _get_latest_quarterly_date returns valid date format."""
    result = _get_latest_quarterly_date()
    # Should be in YYYY-MM-DD format
    assert len(result) == 10
    assert result[4] == '-'
    assert result[7] == '-'
    # Should end with a valid quarterly date (31 for Q1/Q4, 30 for Q2/Q3)
    day = int(result[-2:])
    assert day in [30, 31]


def test_download_fjc_data_uses_cache(tmp_path):
    """Test that download_fjc_data uses cached file if it exists."""
    cache_file = tmp_path / "fjc_civil.csv"
    cache_file.write_text("cached data")

    with patch('src.fjc_processor.CACHE_FILE', cache_file), \
         patch('src.fjc_processor.requests.get') as mock_get:
        result = download_fjc_data()

    # Should not make HTTP request when cache exists
    mock_get.assert_not_called()
    assert result == cache_file
    assert result.read_text() == "cached data"


def test_nos_filter():
    """Test that filter_nos filters DataFrame by NOS codes."""
    # Create sample DataFrame with mixed NOS codes
    df = pd.DataFrame({
        'nature_of_suit': ['442', '110', '445', '320', '446', '890'],
        'district_id': [1, 2, 3, 4, 5, 6],
        'disposition': ['A', 'B', 'C', 'D', 'E', 'F'],
    })

    # Filter with default employment discrimination codes [442, 445, 446]
    result = filter_nos(df)

    # Should return only rows with NOS 442, 445, 446
    assert len(result) == 3
    assert set(result['nature_of_suit'].tolist()) == {'442', '445', '446'}
    # Should preserve all columns
    assert list(result.columns) == list(df.columns)


def test_outcome_mapping():
    """Test that map_outcome correctly maps disposition/judgment to binary outcomes."""
    # Create DataFrame with various disposition/judgment combinations
    df = pd.DataFrame({
        'disposition': [
            0,   # Transfer - EXCLUDE
            1,   # Remand - EXCLUDE
            2,   # Dismissal lack of jurisdiction - defendant_win (0)
            3,   # Dismissal want of prosecution - defendant_win (0)
            12,  # Voluntary dismissal - defendant_win (0)
            4,   # Judgment on default - judgment=1 → plaintiff_win (1)
            5,   # Judgment on consent - judgment=2 → defendant_win (0)
            6,   # Judgment on motion - judgment=3 → EXCLUDE (both)
            7,   # Judgment on jury - judgment=1 → plaintiff_win (1)
            9,   # Judgment on court trial - judgment=4 → EXCLUDE (unknown)
            10,  # MDL transfer - EXCLUDE
            13,  # Settled - EXCLUDE
            18,  # Arbitrator award - judgment=2 → defendant_win (0)
        ],
        'judgment': [
            0,  # N/A for exclusion
            0,  # N/A for exclusion
            0,  # N/A for direct defendant_win
            0,  # N/A for direct defendant_win
            0,  # N/A for direct defendant_win
            1,  # Plaintiff
            2,  # Defendant
            3,  # Both - EXCLUDE
            1,  # Plaintiff
            4,  # Unknown - EXCLUDE
            0,  # N/A for exclusion
            0,  # N/A for exclusion
            2,  # Defendant
        ],
        'case_id': list(range(13)),
    })

    result = map_outcome(df)

    # Should exclude rows with disposition 0, 1, 10, 11, 13, 14, 15
    # Should exclude judgment-dependent rows with judgment 3, 4, 0
    # Expected outcomes:
    # - disposition 2 → 0 (defendant_win)
    # - disposition 3 → 0 (defendant_win)
    # - disposition 12 → 0 (defendant_win)
    # - disposition 4, judgment 1 → 1 (plaintiff_win)
    # - disposition 5, judgment 2 → 0 (defendant_win)
    # - disposition 7, judgment 1 → 1 (plaintiff_win)
    # - disposition 18, judgment 2 → 0 (defendant_win)
    assert len(result) == 7

    # Verify outcome column exists and contains only 0 and 1
    assert 'outcome' in result.columns
    assert set(result['outcome'].unique()) == {0, 1}

    # Verify specific mappings
    # Direct defendant wins (disposition 2, 3, 12)
    direct_defendant_wins = result[result['disposition'].isin([2, 3, 12])]
    assert all(direct_defendant_wins['outcome'] == 0)
    assert len(direct_defendant_wins) == 3

    # Plaintiff wins (judgment=1)
    plaintiff_wins = result[result['outcome'] == 1]
    assert len(plaintiff_wins) == 2
    # These should be disposition 4 and 7 with judgment=1
    assert set(plaintiff_wins['disposition'].tolist()) == {4, 7}

    # Defendant wins from judgment (judgment=2)
    judgment_defendant = result[(result['judgment'] == 2) & (result['outcome'] == 0)]
    assert len(judgment_defendant) == 2  # disposition 5 and 18


def test_case_id_extraction():
    """Test that extract_case_id creates case IDs from district and docket number."""
    # Create sample DataFrame with district_id and docket_number columns (CourtListener naming)
    df = pd.DataFrame({
        'district_id': ['  CA  ', 'NY', 'TX', '', 'nan', 'FL'],
        'docket_number': ['1:2020cv12345', '2:2021cv67890', '3:2019cv11111', '4:2020cv99999', '5:2021cv88888', '6:2022cv77777'],
        'nature_of_suit': ['442', '442', '445', '446', '442', '445'],
    })

    result = extract_case_id(df)

    # Should drop rows with empty or 'nan' district
    assert len(result) == 4

    # district column should be lowercase and stripped
    assert result['district'].tolist() == ['ca', 'ny', 'tx', 'fl']

    # case_id should be in format "{district}:{normalized_docket_number}"
    # Docket numbers are now normalized (division prefixes stripped)
    expected_case_ids = [
        'ca:2020cv12345',
        'ny:2021cv67890',
        'tx:2019cv11111',
        'fl:2022cv77777',
    ]
    assert result['case_id'].tolist() == expected_case_ids

    # Should have normalized docket number column
    assert 'docket_number_normalized' in result.columns
    assert result['docket_number_normalized'].tolist() == ['2020cv12345', '2021cv67890', '2019cv11111', '2022cv77777']

    # Should preserve original columns
    assert 'nature_of_suit' in result.columns
    assert 'district_id' in result.columns
    assert 'docket_number' in result.columns
