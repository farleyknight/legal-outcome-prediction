"""Tests for Matt Clark dataset downloader."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.matt_clark_downloader import (
    ARCHIVE_BASE_URL,
    DEFAULT_YEARS,
    MATT_CLARK_DIR,
    download_cases,
    download_entries,
    download_file,
    download_supporting_files,
    get_cases_url,
    get_entries_url,
    get_supporting_file_url,
    parse_years,
)


class TestUrlConstruction:
    """Test URL construction functions."""

    def test_get_cases_url(self):
        """Test cases.zip URL construction."""
        url = get_cases_url()
        assert url == f"{ARCHIVE_BASE_URL}/cases.zip"
        assert "federal-court-dockets" in url

    def test_get_entries_url(self):
        """Test entries URL construction for various years."""
        assert get_entries_url(2020) == f"{ARCHIVE_BASE_URL}/2020entries.zip"
        assert get_entries_url(2013) == f"{ARCHIVE_BASE_URL}/2013entries.zip"
        assert get_entries_url(2025) == f"{ARCHIVE_BASE_URL}/2025entries.zip"

    def test_get_supporting_file_url(self):
        """Test supporting file URL construction."""
        assert get_supporting_file_url("data_dictionary.csv") == f"{ARCHIVE_BASE_URL}/data_dictionary.csv"
        assert get_supporting_file_url("entries_count.csv") == f"{ARCHIVE_BASE_URL}/entries_count.csv"


class TestParseYears:
    """Test year parsing function."""

    def test_single_year(self):
        """Test parsing single year."""
        assert parse_years("2020") == [2020]
        assert parse_years("2013") == [2013]

    def test_comma_separated(self):
        """Test parsing comma-separated years."""
        assert parse_years("2020,2021,2022") == [2020, 2021, 2022]
        assert parse_years("2020, 2021, 2022") == [2020, 2021, 2022]

    def test_year_range(self):
        """Test parsing year range."""
        assert parse_years("2020-2023") == [2020, 2021, 2022, 2023]
        assert parse_years("2013-2015") == [2013, 2014, 2015]

    def test_default_years_range(self):
        """Test default years matches expected range."""
        assert DEFAULT_YEARS == list(range(2013, 2026))
        assert len(DEFAULT_YEARS) == 13


class TestDownloadFile:
    """Test download_file function."""

    def test_skip_existing_file(self, tmp_path):
        """Test that existing files are skipped."""
        # Create an existing file
        existing_file = tmp_path / "existing.zip"
        existing_file.write_text("existing content")

        # download_file should return True without making any requests
        with patch("src.matt_clark_downloader.requests.get") as mock_get:
            result = download_file("http://example.com/test.zip", existing_file)
            assert result is True
            mock_get.assert_not_called()

    def test_dry_run_mode(self, tmp_path):
        """Test dry run mode doesn't download."""
        dest_path = tmp_path / "test.zip"

        with patch("src.matt_clark_downloader.requests.get") as mock_get:
            result = download_file("http://example.com/test.zip", dest_path, dry_run=True)
            assert result is True
            mock_get.assert_not_called()
            assert not dest_path.exists()

    def test_download_creates_parent_dirs(self, tmp_path):
        """Test download creates parent directories."""
        dest_path = tmp_path / "nested" / "dir" / "test.zip"

        mock_response = MagicMock()
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_content.return_value = [b"test content"]

        with patch("src.matt_clark_downloader.requests.get", return_value=mock_response):
            result = download_file("http://example.com/test.zip", dest_path)
            assert result is True
            assert dest_path.parent.exists()

    def test_download_handles_request_error(self, tmp_path):
        """Test download handles request exceptions."""
        import requests

        dest_path = tmp_path / "test.zip"

        with patch("src.matt_clark_downloader.requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")
            result = download_file("http://example.com/test.zip", dest_path)
            assert result is False
            assert not dest_path.exists()


class TestDownloadFunctions:
    """Test high-level download functions."""

    def test_download_cases_dry_run(self):
        """Test download_cases in dry run mode."""
        with patch("src.matt_clark_downloader.download_file") as mock_download:
            mock_download.return_value = True
            result = download_cases(dry_run=True)
            assert result is True
            mock_download.assert_called_once()
            call_args = mock_download.call_args
            assert "cases.zip" in str(call_args[0][1])

    def test_download_entries_dry_run(self):
        """Test download_entries in dry run mode."""
        with patch("src.matt_clark_downloader.download_file") as mock_download:
            mock_download.return_value = True
            results = download_entries([2020, 2021], dry_run=True)
            assert results == {2020: True, 2021: True}
            assert mock_download.call_count == 2

    def test_download_entries_default_years(self):
        """Test download_entries uses default years when none specified."""
        with patch("src.matt_clark_downloader.download_file") as mock_download:
            mock_download.return_value = True
            results = download_entries(dry_run=True)
            assert len(results) == len(DEFAULT_YEARS)

    def test_download_supporting_files_dry_run(self):
        """Test download_supporting_files in dry run mode."""
        with patch("src.matt_clark_downloader.download_file") as mock_download:
            mock_download.return_value = True
            results = download_supporting_files(dry_run=True)
            assert "data_dictionary.csv" in results
            assert "entries_count.csv" in results
            assert all(v is True for v in results.values())


class TestMattClarkDir:
    """Test directory configuration."""

    def test_matt_clark_dir_path(self):
        """Test MATT_CLARK_DIR is correctly configured."""
        assert MATT_CLARK_DIR.name == "matt_clark"
        assert MATT_CLARK_DIR.parent.name == "data"
