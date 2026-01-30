"""Tests for pipeline orchestration."""

import logging
from pathlib import Path
from unittest.mock import patch, Mock

import pandas as pd

from src import pipeline
from src.pipeline import run_pipeline, setup_unmatched_logger, UNMATCHED_LOG_PATH


def test_placeholder():
    """Placeholder test to verify module imports."""
    assert pipeline is not None


def test_pipeline_runs(tmp_path):
    """Test that run_pipeline orchestrates the FJC processing steps correctly."""
    # Create mock FJC data that matches what the real pipeline would see (CourtListener format)
    mock_fjc_data = pd.DataFrame({
        'nature_of_suit': ['442', '442', '445', '446', '440'],
        'disposition': ['4', '4', '5', '3', '4'],
        'judgment': ['1', '2', '1', '0', '1'],
        'district_id': ['CACD', 'NYSD', 'TXED', 'FLSD', 'ILND'],
        'docket_number': ['1:21-cv-00001', '1:21-cv-00002', '1:21-cv-00003', '1:21-cv-00004', '1:21-cv-00005'],
        'date_filed': ['2021-01-15', '2021-02-20', '2021-03-10', '2021-04-01', '2021-05-15'],
        'date_terminated': ['2021-06-15', '2021-08-20', '2021-09-10', '2021-10-01', '2021-11-15'],
    })

    # Create a temporary CSV file
    csv_path = tmp_path / "fjc_civil.csv"
    mock_fjc_data.to_csv(csv_path, index=False)

    # Mock docket search result
    mock_docket = {'id': 12345}
    mock_entries = [
        {'date_filed': '2021-01-15', 'description': 'COMPLAINT', 'entry_number': 1},
        {'date_filed': '2021-02-15', 'description': 'ANSWER', 'entry_number': 2},
    ]

    # Mock download_fjc_data to return our temp file
    with patch('src.pipeline.download_fjc_data', return_value=csv_path), \
         patch('src.pipeline.search_case', return_value=mock_docket), \
         patch('src.pipeline.get_docket_entries', return_value=mock_entries):
        result = run_pipeline()

    # Verify result is a DataFrame
    assert isinstance(result, pd.DataFrame)

    # Verify required columns exist (new output schema)
    assert 'case_id' in result.columns
    assert 'district' in result.columns
    assert 'filing_date' in result.columns
    assert 'termination_date' in result.columns
    assert 'event_sequence' in result.columns
    assert 'days_to_resolution' in result.columns
    assert 'outcome' in result.columns

    # Verify NOS filtering worked (only 442, 445, 446 should remain)
    # Row with NOS 440 should be filtered out
    assert len(result) <= 4  # At most 4 rows (one with NOS 440 removed)

    # Verify outcome mapping worked (values should be 0 or 1)
    assert result['outcome'].isin([0, 1]).all()

    # Verify case_id format is district:docket_number
    for case_id in result['case_id']:
        assert ':' in case_id


def test_unmatched_case_logging(tmp_path):
    """Test that unmatched cases are logged to logs/unmatched_cases.log."""
    # Create mock FJC data (CourtListener format)
    mock_fjc_data = pd.DataFrame({
        'nature_of_suit': ['442', '445'],
        'disposition': ['4', '5'],
        'judgment': ['1', '1'],
        'district_id': ['CACD', 'NYSD'],
        'docket_number': ['1:21-cv-00001', '1:21-cv-00002'],
    })

    # Create a temporary CSV file
    csv_path = tmp_path / "fjc_civil.csv"
    mock_fjc_data.to_csv(csv_path, index=False)

    # Create temp log directory for test
    test_log_dir = tmp_path / "logs"
    test_log_dir.mkdir(parents=True, exist_ok=True)
    test_log_path = test_log_dir / "unmatched_cases.log"

    # Clear any existing handlers from the unmatched_cases logger
    unmatched_logger = logging.getLogger("unmatched_cases")
    unmatched_logger.handlers.clear()

    # Patch LOGS_DIR and UNMATCHED_LOG_PATH to use temp directory
    with patch('src.pipeline.LOGS_DIR', test_log_dir), \
         patch('src.pipeline.UNMATCHED_LOG_PATH', test_log_path), \
         patch('src.pipeline.download_fjc_data', return_value=csv_path), \
         patch('src.pipeline.search_case', return_value=None):  # All cases unmatched
        result = run_pipeline()

    # Verify log file was created
    assert test_log_path.exists(), "Unmatched log file should be created"

    # Verify log file has entries
    log_content = test_log_path.read_text()
    assert len(log_content) > 0, "Log file should contain entries"

    # Verify case identifiers are in the log
    assert "case_id=" in log_content
    assert "district=" in log_content

    # Clean up logger handlers for subsequent tests
    unmatched_logger.handlers.clear()


def test_output_schema(tmp_path):
    """Test that output DataFrame contains all required columns per DATA_MODEL.md."""
    # Required columns from specs/DATA_MODEL.md Output Dataset Schema
    REQUIRED_COLUMNS = [
        'case_id',
        'district',
        'filing_date',
        'termination_date',
        'event_sequence',
        'days_to_resolution',
        'outcome',
    ]

    # Create mock FJC data with CourtListener format columns
    mock_fjc_data = pd.DataFrame({
        'nature_of_suit': ['442'],
        'disposition': ['4'],
        'judgment': ['1'],
        'district_id': ['CACD'],
        'docket_number': ['1:21-cv-00001'],
        'date_filed': ['2021-01-15'],
        'date_terminated': ['2021-06-15'],
    })

    # Create a temporary CSV file
    csv_path = tmp_path / "fjc_civil.csv"
    mock_fjc_data.to_csv(csv_path, index=False)

    # Mock docket search result and entries
    mock_docket = {'id': 12345}
    mock_entries = [
        {'date_filed': '2021-01-15', 'description': 'COMPLAINT', 'entry_number': 1},
        {'date_filed': '2021-03-15', 'description': 'ANSWER', 'entry_number': 2},
        {'date_filed': '2021-05-15', 'description': 'ORDER granting summary judgment', 'entry_number': 3},
    ]

    with patch('src.pipeline.download_fjc_data', return_value=csv_path), \
         patch('src.pipeline.search_case', return_value=mock_docket), \
         patch('src.pipeline.get_docket_entries', return_value=mock_entries):
        result = run_pipeline()

    # Verify all required columns are present
    for col in REQUIRED_COLUMNS:
        assert col in result.columns, f"Required column '{col}' missing from output"

    # Verify no extra unexpected columns (output should be clean)
    assert set(result.columns) == set(REQUIRED_COLUMNS), \
        f"Output columns {list(result.columns)} don't match required {REQUIRED_COLUMNS}"

    # Verify column types per DATA_MODEL.md
    assert len(result) > 0, "Result should have at least one row"

    # case_id should be string format district:docket_number
    assert result['case_id'].dtype == object  # pandas string type
    assert ':' in result['case_id'].iloc[0]

    # district should be string
    assert result['district'].dtype == object

    # filing_date and termination_date should be valid dates
    assert result['filing_date'].iloc[0] is not None
    assert result['termination_date'].iloc[0] is not None

    # event_sequence should be JSON string
    assert result['event_sequence'].dtype == object
    import json
    events = json.loads(result['event_sequence'].iloc[0])
    assert isinstance(events, list)

    # days_to_resolution should be integer
    assert result['days_to_resolution'].iloc[0] >= 0

    # outcome should be 0 or 1
    assert result['outcome'].iloc[0] in [0, 1]
