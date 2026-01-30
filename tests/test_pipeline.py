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
    # Create mock FJC data that matches what the real pipeline would see
    mock_fjc_data = pd.DataFrame({
        'nature_of_suit': ['442', '442', '445', '446', '440'],
        'disposition': ['4', '4', '5', '3', '4'],
        'judgment': ['1', '2', '1', '0', '1'],
        'DISTRICT': ['CACD', 'NYSD', 'TXED', 'FLSD', 'ILND'],
        'DESSION': ['1:21-cv-00001', '1:21-cv-00002', '1:21-cv-00003', '1:21-cv-00004', '1:21-cv-00005'],
    })

    # Create a temporary CSV file
    csv_path = tmp_path / "fjc_civil.csv"
    mock_fjc_data.to_csv(csv_path, index=False)

    # Mock download_fjc_data to return our temp file
    with patch('src.pipeline.download_fjc_data', return_value=csv_path):
        result = run_pipeline()

    # Verify result is a DataFrame
    assert isinstance(result, pd.DataFrame)

    # Verify required columns exist
    assert 'case_id' in result.columns
    assert 'district' in result.columns
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
    # Create mock FJC data
    mock_fjc_data = pd.DataFrame({
        'nature_of_suit': ['442', '445'],
        'disposition': ['4', '5'],
        'judgment': ['1', '1'],
        'DISTRICT': ['CACD', 'NYSD'],
        'DESSION': ['1:21-cv-00001', '1:21-cv-00002'],
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
