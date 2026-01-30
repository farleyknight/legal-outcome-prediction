"""FJC IDB data download and filtering."""

import bz2
import logging
from datetime import date
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# CourtListener provides FJC IDB data as quarterly bulk exports
# Data is updated on the last day of March, June, September, December
COURTLISTENER_BULK_URL = "https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/bulk-data"
DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_FILE = DATA_DIR / "fjc_civil.csv"


def _get_latest_quarterly_date() -> str:
    """Get the most recent quarterly release date (YYYY-MM-DD format).

    Bulk data is released on March 31, June 30, September 30, December 31.
    """
    today = date.today()
    year = today.year

    # Quarterly release dates for current year
    quarters = [
        date(year, 3, 31),
        date(year, 6, 30),
        date(year, 9, 30),
        date(year, 12, 31),
    ]

    # Find the most recent quarter that has passed
    for q in reversed(quarters):
        if today >= q:
            return q.isoformat()

    # If no quarter has passed this year, use Q4 of previous year
    return date(year - 1, 12, 31).isoformat()


def download_fjc_data() -> Path:
    """Download FJC IDB civil terminations data from CourtListener.

    Downloads the FJC IDB dataset from CourtListener's quarterly bulk exports
    and caches it locally. If the file already exists, returns the cached version.

    Returns:
        Path to the downloaded/cached CSV file.
    """
    if CACHE_FILE.exists():
        logger.info(f"Using cached FJC data: {CACHE_FILE}")
        return CACHE_FILE

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    quarterly_date = _get_latest_quarterly_date()
    url = f"{COURTLISTENER_BULK_URL}/fjc-integrated-database-{quarterly_date}.csv.bz2"

    logger.info(f"Downloading FJC IDB data from {url}")

    response = requests.get(url, timeout=600, stream=True)
    response.raise_for_status()

    # Decompress the bz2 file and write to CSV
    logger.info("Decompressing data...")
    decompressed_data = bz2.decompress(response.content)

    with open(CACHE_FILE, 'wb') as f:
        f.write(decompressed_data)

    logger.info(f"FJC data saved to {CACHE_FILE}")
    return CACHE_FILE


def filter_cases(nos_codes: list[int]):
    """Filter cases by Nature of Suit codes."""
    raise NotImplementedError
