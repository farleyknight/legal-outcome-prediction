"""Integration tests that require real API access."""

import os

import pytest

from src.recap_client import check_api_connection


@pytest.mark.skipif(
    not os.environ.get("COURTLISTENER_API_TOKEN"),
    reason="COURTLISTENER_API_TOKEN not set",
)
def test_live_api_auth():
    """Test that API authentication works with a real token."""
    result = check_api_connection()
    assert result is True, "API authentication failed - check your COURTLISTENER_API_TOKEN"
