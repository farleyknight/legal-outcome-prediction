"""Tests for FJC data processing."""

import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src import fjc_processor
from src.fjc_processor import download_fjc_data


def test_placeholder():
    """Placeholder test to verify module imports."""
    assert fjc_processor is not None


def test_download_fjc_data_returns_path(tmp_path):
    """Test that download_fjc_data returns a Path object."""
    # Create a mock zip file with CSV content
    csv_content = b"CIRCUIT,DISTRICT,NOS\n1,36,442\n"
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('cv88on.txt', csv_content)
    zip_buffer.seek(0)

    mock_response = MagicMock()
    mock_response.content = zip_buffer.read()
    mock_response.raise_for_status = MagicMock()

    cache_file = tmp_path / "fjc_civil.csv"

    with patch('src.fjc_processor.requests.get', return_value=mock_response), \
         patch('src.fjc_processor.CACHE_FILE', cache_file), \
         patch('src.fjc_processor.DATA_DIR', tmp_path):
        result = download_fjc_data()

    assert isinstance(result, Path)
    assert result.exists()
    assert result.read_text() == "CIRCUIT,DISTRICT,NOS\n1,36,442\n"


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
