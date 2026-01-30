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


def test_docket_lookup(tmp_path, monkeypatch):
    """Test search_case() looks up dockets via CourtListener API."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")
    monkeypatch.setattr(recap_client, "CACHE_DIR", tmp_path)

    # Sample API response
    sample_response = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": 12345678,
                "resource_uri": "https://www.courtlistener.com/api/rest/v4/dockets/12345678/",
                "court": "https://www.courtlistener.com/api/rest/v4/courts/nysd/",
                "docket_number": "1:19-cv-01234",
                "date_filed": "2019-03-15",
                "date_terminated": "2021-06-22",
            }
        ],
    }

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = sample_response

    with patch("src.recap_client.requests.get", return_value=mock_response) as mock_get:
        result = recap_client.search_case("2019cv01234", "nysd")

        # Verify correct URL called
        expected_url = f"{recap_client.BASE_URL}dockets/?court=nysd&docket_number=2019cv01234"
        mock_get.assert_called_once_with(
            expected_url,
            headers={"Authorization": "Token test_token_123"},
            timeout=30,
        )

        # Verify result contains expected docket data
        assert result is not None
        assert result["id"] == 12345678
        assert result["docket_number"] == "1:19-cv-01234"


def test_docket_lookup_cache_hit(tmp_path, monkeypatch):
    """Test search_case() returns cached data without API call."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")
    monkeypatch.setattr(recap_client, "CACHE_DIR", tmp_path)

    # Pre-populate cache
    cached_docket = {
        "id": 12345678,
        "docket_number": "1:19-cv-01234",
        "date_filed": "2019-03-15",
    }
    recap_client.write_cache("dockets", "nysd_2019cv01234", cached_docket)

    with patch("src.recap_client.requests.get") as mock_get:
        result = recap_client.search_case("2019cv01234", "nysd")

        # Verify no API call was made
        mock_get.assert_not_called()

        # Verify cached data returned
        assert result == cached_docket


def test_docket_lookup_not_found(tmp_path, monkeypatch):
    """Test search_case() returns None when no docket found."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")
    monkeypatch.setattr(recap_client, "CACHE_DIR", tmp_path)

    # Empty results response
    empty_response = {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = empty_response

    with patch("src.recap_client.requests.get", return_value=mock_response):
        result = recap_client.search_case("9999cv99999", "nysd")

        assert result is None


def test_negative_cache(tmp_path, monkeypatch):
    """Test search_case() caches negative (not found) results to avoid redundant API calls."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")
    monkeypatch.setattr(recap_client, "CACHE_DIR", tmp_path)

    # Empty results response (case not found)
    empty_response = {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = empty_response

    with patch("src.recap_client.requests.get", return_value=mock_response) as mock_get:
        # First call: should hit API and cache the negative result
        result1 = recap_client.search_case("nonexistent_case", "nysd")
        assert result1 is None
        assert mock_get.call_count == 1

        # Second call: should return from cache without hitting API
        result2 = recap_client.search_case("nonexistent_case", "nysd")
        assert result2 is None
        assert mock_get.call_count == 1  # No additional API call

    # Verify cache file contains NEGATIVE_CACHE_SENTINEL
    cache_file = tmp_path / "dockets" / "nysd_nonexistent_case.json"
    assert cache_file.exists()
    cached_data = recap_client.read_cache("dockets", "nysd_nonexistent_case")
    assert cached_data == recap_client.NEGATIVE_CACHE_SENTINEL


def test_429_handling(monkeypatch):
    """Test _make_request retries once after HTTP 429 rate limit response."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")

    # First response: 429 rate limit
    mock_response_429 = Mock()
    mock_response_429.status_code = 429

    # Second response: 200 success
    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.raise_for_status = Mock()

    with patch("src.recap_client.requests.get", side_effect=[mock_response_429, mock_response_200]) as mock_get:
        with patch("src.recap_client.time.sleep") as mock_sleep:
            # Reset rate limit timer to avoid interference
            recap_client._last_request_time = 0

            result = recap_client._make_request(
                "https://example.com/api",
                {"Authorization": "Token test"},
            )

            # Verify retry happened
            assert mock_get.call_count == 2

            # Verify sleep was called with retry delay
            mock_sleep.assert_called_with(recap_client.RATE_LIMIT_RETRY_DELAY)

            # Verify successful response returned
            assert result.status_code == 200


def test_exponential_backoff(monkeypatch):
    """Test _make_request uses exponential backoff for 5xx errors."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")

    # First two responses: 500 server error
    mock_response_500_1 = Mock()
    mock_response_500_1.status_code = 500

    mock_response_500_2 = Mock()
    mock_response_500_2.status_code = 500

    # Third response: 200 success
    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.raise_for_status = Mock()

    with patch(
        "src.recap_client.requests.get",
        side_effect=[mock_response_500_1, mock_response_500_2, mock_response_200]
    ) as mock_get:
        with patch("src.recap_client.time.sleep") as mock_sleep:
            # Mock time.time to return incrementing values to avoid rate limit sleeps
            time_counter = [1000.0]

            def mock_time():
                time_counter[0] += 2.0  # Increment by 2s each call (> RATE_LIMIT_SECONDS)
                return time_counter[0]

            with patch("src.recap_client.time.time", side_effect=mock_time):
                recap_client._last_request_time = 0

                result = recap_client._make_request(
                    "https://example.com/api",
                    {"Authorization": "Token test"},
                )

                # Verify retries happened (3 total requests)
                assert mock_get.call_count == 3

                # Verify exponential backoff delays
                # First retry: 1.0 * (2.0 ** 0) = 1.0s
                # Second retry: 1.0 * (2.0 ** 1) = 2.0s
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert len(sleep_calls) == 2
                assert sleep_calls[0] == 1.0  # First backoff delay
                assert sleep_calls[1] == 2.0  # Second backoff delay

                # Verify successful response returned
                assert result.status_code == 200


def test_exponential_backoff_max_retries_exhausted(monkeypatch):
    """Test _make_request returns error response when max retries exhausted for 5xx."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")

    # All responses are 500 errors
    mock_response_500 = Mock()
    mock_response_500.status_code = 500

    with patch(
        "src.recap_client.requests.get",
        return_value=mock_response_500
    ) as mock_get:
        with patch("src.recap_client.time.sleep") as mock_sleep:
            # Mock time.time to return incrementing values to avoid rate limit sleeps
            time_counter = [1000.0]

            def mock_time():
                time_counter[0] += 2.0
                return time_counter[0]

            with patch("src.recap_client.time.time", side_effect=mock_time):
                recap_client._last_request_time = 0

                result = recap_client._make_request(
                    "https://example.com/api",
                    {"Authorization": "Token test"},
                )

                # Verify all retries were attempted (initial + 3 retries = 4)
                assert mock_get.call_count == 4

                # Verify backoff delays (3 sleeps for retries)
                assert mock_sleep.call_count == 3

                # Verify error response returned after exhausting retries
                assert result.status_code == 500


def test_exponential_backoff_connection_error(monkeypatch):
    """Test _make_request retries on connection errors with exponential backoff."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")

    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.raise_for_status = Mock()

    # First two calls raise ConnectionError, third succeeds
    with patch(
        "src.recap_client.requests.get",
        side_effect=[
            recap_client.requests.ConnectionError("Connection refused"),
            recap_client.requests.ConnectionError("Connection refused"),
            mock_response_200,
        ]
    ) as mock_get:
        with patch("src.recap_client.time.sleep") as mock_sleep:
            # Mock time.time to return incrementing values to avoid rate limit sleeps
            time_counter = [1000.0]

            def mock_time():
                time_counter[0] += 2.0
                return time_counter[0]

            with patch("src.recap_client.time.time", side_effect=mock_time):
                recap_client._last_request_time = 0

                result = recap_client._make_request(
                    "https://example.com/api",
                    {"Authorization": "Token test"},
                )

                # Verify retries happened
                assert mock_get.call_count == 3

                # Verify exponential backoff delays
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert len(sleep_calls) == 2
                assert sleep_calls[0] == 1.0
                assert sleep_calls[1] == 2.0

                # Verify successful response returned
                assert result.status_code == 200


def test_exponential_backoff_timeout_error(monkeypatch):
    """Test _make_request retries on timeout errors with exponential backoff."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")

    mock_response_200 = Mock()
    mock_response_200.status_code = 200
    mock_response_200.raise_for_status = Mock()

    # First call raises Timeout, second succeeds
    with patch(
        "src.recap_client.requests.get",
        side_effect=[
            recap_client.requests.Timeout("Request timed out"),
            mock_response_200,
        ]
    ) as mock_get:
        with patch("src.recap_client.time.sleep") as mock_sleep:
            # Mock time.time to return incrementing values to avoid rate limit sleeps
            time_counter = [1000.0]

            def mock_time():
                time_counter[0] += 2.0
                return time_counter[0]

            with patch("src.recap_client.time.time", side_effect=mock_time):
                recap_client._last_request_time = 0

                result = recap_client._make_request(
                    "https://example.com/api",
                    {"Authorization": "Token test"},
                )

                # Verify retry happened
                assert mock_get.call_count == 2

                # Verify backoff delay
                mock_sleep.assert_called_with(1.0)

                # Verify successful response returned
                assert result.status_code == 200


def test_max_retries(monkeypatch):
    """Test _make_request respects configurable max_retries parameter."""
    monkeypatch.setenv("COURTLISTENER_API_TOKEN", "test_token_123")

    # All responses are 500 errors
    mock_response_500 = Mock()
    mock_response_500.status_code = 500

    # Test max_retries=0: No retries, only 1 attempt
    with patch(
        "src.recap_client.requests.get",
        return_value=mock_response_500
    ) as mock_get:
        with patch("src.recap_client.time.sleep") as mock_sleep:
            time_counter = [1000.0]

            def mock_time():
                time_counter[0] += 2.0
                return time_counter[0]

            with patch("src.recap_client.time.time", side_effect=mock_time):
                recap_client._last_request_time = 0

                result = recap_client._make_request(
                    "https://example.com/api",
                    {"Authorization": "Token test"},
                    max_retries=0,
                )

                # Verify only 1 attempt (no retries)
                assert mock_get.call_count == 1
                # Verify no backoff sleeps
                assert mock_sleep.call_count == 0
                assert result.status_code == 500

    # Test max_retries=1: Only 1 retry, 2 total attempts
    with patch(
        "src.recap_client.requests.get",
        return_value=mock_response_500
    ) as mock_get:
        with patch("src.recap_client.time.sleep") as mock_sleep:
            time_counter = [1000.0]

            def mock_time():
                time_counter[0] += 2.0
                return time_counter[0]

            with patch("src.recap_client.time.time", side_effect=mock_time):
                recap_client._last_request_time = 0

                result = recap_client._make_request(
                    "https://example.com/api",
                    {"Authorization": "Token test"},
                    max_retries=1,
                )

                # Verify 2 total attempts (1 initial + 1 retry)
                assert mock_get.call_count == 2
                # Verify 1 backoff sleep
                assert mock_sleep.call_count == 1
                assert result.status_code == 500

    # Test default max_retries: Uses BACKOFF_MAX_RETRIES (3), so 4 total attempts
    with patch(
        "src.recap_client.requests.get",
        return_value=mock_response_500
    ) as mock_get:
        with patch("src.recap_client.time.sleep") as mock_sleep:
            time_counter = [1000.0]

            def mock_time():
                time_counter[0] += 2.0
                return time_counter[0]

            with patch("src.recap_client.time.time", side_effect=mock_time):
                recap_client._last_request_time = 0

                result = recap_client._make_request(
                    "https://example.com/api",
                    {"Authorization": "Token test"},
                )

                # Verify default behavior: 4 total attempts (1 + BACKOFF_MAX_RETRIES)
                assert mock_get.call_count == 4
                # Verify 3 backoff sleeps
                assert mock_sleep.call_count == 3
                assert result.status_code == 500