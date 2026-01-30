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


RATE_LIMIT_RETRY_DELAY = 5.0


def _make_request(url: str, headers: dict, timeout: int = 30) -> requests.Response:
    """Make an HTTP GET request with rate limiting.

    Handles HTTP 429 (rate limit) responses by waiting and retrying once.

    Args:
        url: The URL to request.
        headers: Request headers.
        timeout: Request timeout in seconds.

    Returns:
        The response object.

    Raises:
        requests.HTTPError: If request fails after retry or for non-429 errors.
    """
    rate_limit()
    response = requests.get(url, headers=headers, timeout=timeout)

    if response.status_code == 429:
        logger.warning(f"Rate limited (429) for {url}, retrying after {RATE_LIMIT_RETRY_DELAY}s")
        time.sleep(RATE_LIMIT_RETRY_DELAY)
        response = requests.get(url, headers=headers, timeout=timeout)

    return response


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


def search_case(case_number: str, court: str) -> dict | None:
    """Search for a case in RECAP via CourtListener API.

    Args:
        case_number: The docket number to search for (e.g., "2019cv01234").
        court: Court abbreviation (e.g., "nysd").

    Returns:
        Dict with docket data if found, None if not found.
    """
    cache_key = f"{court}_{case_number}"

    # Check cache first
    cached = read_cache("dockets", cache_key)
    if cached is not None:
        logger.debug(f"Cache hit for docket {cache_key}")
        return cached

    # Make API request
    url = f"{BASE_URL}dockets/?court={court}&docket_number={case_number}"
    headers = get_api_headers()
    response = _make_request(url, headers)
    response.raise_for_status()

    data = response.json()
    results = data.get("results", [])

    if not results:
        logger.info(f"No docket found for {court}:{case_number}")
        return None

    # Extract first matching docket
    docket = results[0]
    write_cache("dockets", cache_key, docket)
    logger.info(f"Found docket {docket.get('id')} for {court}:{case_number}")

    return docket


def get_docket_entries(docket_id: int) -> list[dict]:
    """Get docket entries for a given docket ID.

    Args:
        docket_id: The CourtListener docket ID.

    Returns:
        List of docket entry dicts, each with date_filed, description, entry_number.
        Returns empty list if no entries found.
    """
    cache_key = str(docket_id)

    # Check cache first
    cached = read_cache("entries", cache_key)
    if cached is not None:
        logger.debug(f"Cache hit for docket entries {docket_id}")
        return cached

    # Make API request for docket entries
    url = f"{BASE_URL}docket-entries/?docket={docket_id}"
    headers = get_api_headers()

    all_entries = []
    while url:
        response = _make_request(url, headers)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        all_entries.extend(results)

        url = data.get("next")  # Pagination

    write_cache("entries", cache_key, all_entries)
    logger.info(f"Fetched {len(all_entries)} docket entries for docket {docket_id}")

    return all_entries
