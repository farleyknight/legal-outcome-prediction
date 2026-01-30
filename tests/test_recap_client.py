"""Tests for CourtListener API client."""

import os
from unittest.mock import Mock, patch

import pytest

from src import recap_client


def test_placeholder():
    """Placeholder test to verify module imports."""
    assert recap_client is not None


def test_get_api_headers_with_token(monkeypatch):
    """Test get_api_headers returns correct header when token is set."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")
    headers = recap_client.get_api_headers()
    assert headers == {"Authorization": "Token test_token_123"}


def test_get_api_headers_without_token(monkeypatch):
    """Test get_api_headers raises ValueError when token is not set."""
    monkeypatch.delenv("COURTLISTENER_API_TOKEN", raising=False)
    with pytest.raises(ValueError, match="COURTLISTENER_API_TOKEN"):
        recap_client.get_api_headers()


def test_api_connection(monkeypatch):
    """Test check_api_connection returns True on successful API response."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()

    with patch("src.recap_client.requests.get", return_value=mock_response) as mock_get:
        result = recap_client.check_api_connection()

        assert result is True
        mock_get.assert_called_once_with(
            recap_client.BASE_URL,
            headers={"Authorization": "Token test_token_123"},
            timeout=30,
        )


def test_api_connection_failure(monkeypatch):
    """Test check_api_connection returns False on API error."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")

    with patch("src.recap_client.requests.get") as mock_get:
        mock_get.side_effect = recap_client.requests.RequestException("Connection error")
        result = recap_client.check_api_connection()

        assert result is False


def test_api_connection_missing_token(monkeypatch):
    """Test check_api_connection returns False when token is missing."""
    monkeypatch.delenv("COURTLISTENER_API_TOKEN", raising=False)
    result = recap_client.check_api_connection()
    assert result is False


def test_rate_limiting(monkeypatch):
    """Test rate limiting enforces 1 request per second."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")

    # Set last request time to simulate a previous request at t=0
    # This way we can test the rate limiting logic cleanly
    recap_client._last_request_time = 100.0

    # Mock time.time to return controlled values
    time_values = [
        100.3,  # First call to time.time() in rate_limit - only 0.3s passed, need to wait
        101.0,  # First call to time.time() after sleep (update _last_request_time)
        102.5,  # Second call to time.time() in rate_limit - 1.5s passed, no wait needed
        102.5,  # Second call to time.time() after sleep (update _last_request_time)
    ]
    time_iter = iter(time_values)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()

    with patch("src.recap_client.time.time", side_effect=lambda: next(time_iter)):
        with patch("src.recap_client.time.sleep") as mock_sleep:
            with patch("src.recap_client.requests.get", return_value=mock_response):
                # First request - should wait 0.7s (1.0 - 0.3)
                recap_client.check_api_connection()

                # Second request - no wait needed (1.5s > 1.0s)
                recap_client.check_api_connection()

    # Verify sleep was called exactly once with correct duration
    assert mock_sleep.call_count == 1
    call_args = mock_sleep.call_args[0][0]
    assert abs(call_args - 0.7) < 0.01  # Allow small floating point tolerance


def test_caching(tmp_path, monkeypatch):
    """Test file-based caching for API responses."""
    # Point CACHE_DIR to tmp_path for test isolation
    monkeypatch.setattr(recap_client, "CACHE_DIR", tmp_path)

    cache_type = "dockets"
    key = "nysd_2019cv01234"
    test_data = {"id": 12345, "court": "nysd", "docket_number": "2019cv01234"}

    # Test cache miss returns None
    result = recap_client.read_cache(cache_type, key)
    assert result is None

    # Test write_cache creates file with correct JSON
    recap_client.write_cache(cache_type, key, test_data)
    cache_file = tmp_path / cache_type / f"{key}.json"
    assert cache_file.exists()

    # Test read_cache returns the cached data
    cached_result = recap_client.read_cache(cache_type, key)
    assert cached_result == test_data

    # Test different cache_type (entries)
    entries_key = "12345678"
    entries_data = {"id": 12345678, "description": "Motion to dismiss"}
    recap_client.write_cache("entries", entries_key, entries_data)

    entries_result = recap_client.read_cache("entries", entries_key)
    assert entries_result == entries_data
