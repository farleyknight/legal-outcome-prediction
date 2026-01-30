"""CourtListener API client for RECAP docket entries."""

import json
import logging
import os
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_DIR = DATA_DIR / "cache"

BASE_URL = "https://www.courtlistener.com/api/rest/v4/"
COURTLISTENER_API_TOKEN_VAR = "COURTLISTENER_API_TOKEN"
RATE_LIMIT_SECONDS = 1.0

_last_request_time = 0.0


def get_cache_path(cache_type: str, key: str) -> Path:
    """Get the file path for a cached response.

    Args:
        cache_type: Type of cache ("dockets" or "entries").
        key: Cache key (e.g., "nysd_2019cv01234" or "12345678").

    Returns:
        Path to the cache file.
    """
    return CACHE_DIR / cache_type / f"{key}.json"


def read_cache(cache_type: str, key: str) -> dict | None:
    """Read cached API response from disk.

    Args:
        cache_type: Type of cache ("dockets" or "entries").
        key: Cache key.

    Returns:
        Cached JSON data as dict if exists, None otherwise.
    """
    cache_path = get_cache_path(cache_type, key)
    if not cache_path.exists():
        return None
    with open(cache_path, "r") as f:
        return json.load(f)


def write_cache(cache_type: str, key: str, data: dict) -> None:
    """Write API response to cache.

    Args:
        cache_type: Type of cache ("dockets" or "entries").
        key: Cache key.
        data: JSON response data to cache.
    """
    cache_path = get_cache_path(cache_type, key)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(data, f)


def rate_limit():
    """Enforce rate limiting of 1 request per second.

    Sleeps if necessary to ensure at least RATE_LIMIT_SECONDS
    have passed since the last request.
    """
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_SECONDS:
        sleep_time = RATE_LIMIT_SECONDS - elapsed
        time.sleep(sleep_time)
    _last_request_time = time.time()


def _make_request(url: str, headers: dict, timeout: int = 30) -> requests.Response:
    """Make an HTTP GET request with rate limiting.

    Args:
        url: The URL to request.
        headers: Request headers.
        timeout: Request timeout in seconds.

    Returns:
        The response object.
    """
    rate_limit()
    return requests.get(url, headers=headers, timeout=timeout)


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
        response = _make_request(BASE_URL, headers, timeout=30)
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
