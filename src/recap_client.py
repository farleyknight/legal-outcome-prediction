"""CourtListener API client for RECAP docket entries."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.courtlistener.com/api/rest/v4/"
COURTLISTENER_API_TOKEN_VAR = "COURTLISTENER_API_TOKEN"


def get_api_headers() -> dict:
    """Get authorization headers for CourtListener API.

    Returns:
        Dict with Authorization header containing the API token.

    Raises:
        ValueError: If COURTLISTENER_API_TOKEN environment variable is not set.
    """
    token = os.environ.get(COURTLISTENER_API_TOKEN_VAR)
    if not token:
        raise ValueError(
            f"{COURTLISTENER_API_TOKEN_VAR} environment variable is not set"
        )
    return {"Authorization": f"Token {token}"}


def check_api_connection() -> bool:
    """Check if API connection is working with valid authentication.

    Returns:
        True if API responds with 200 status, False otherwise.
    """
    try:
        headers = get_api_headers()
        response = requests.get(BASE_URL, headers=headers, timeout=30)
        response.raise_for_status()
        return True
    except (requests.RequestException, ValueError) as e:
        logger.warning(f"API connection check failed: {e}")
        return False


def search_case(case_number: str, court: str):
    """Search for a case in RECAP via CourtListener API."""
    raise NotImplementedError


def get_docket_entries(docket_id: int):
    """Get docket entries for a given docket ID."""
    raise NotImplementedError
