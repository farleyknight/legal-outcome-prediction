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
