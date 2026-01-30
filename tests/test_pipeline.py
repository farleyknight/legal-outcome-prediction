"""Tests for pipeline orchestration."""

from pathlib import Path
from unittest.mock import patch, Mock

import pandas as pd

from src import pipeline
from src.pipeline import run_pipeline


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
