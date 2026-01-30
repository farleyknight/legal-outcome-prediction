"""Tests for FJC data processing."""

import bz2
from pathlib import Path
from unittest.mock import MagicMock, patch

from src import fjc_processor
from src.fjc_processor import download_fjc_data, _get_latest_quarterly_date


def test_placeholder():
    """Placeholder test to verify module imports."""
    assert fjc_processor is not None


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
