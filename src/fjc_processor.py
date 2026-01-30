"""FJC IDB data download and filtering."""

import bz2
import logging
from datetime import date
from pathlib import Path

import pandas as pd
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


def map_outcome(df: pd.DataFrame) -> pd.DataFrame:
    """Map FJC disposition/judgment codes to binary outcome labels.

    Args:
        df: DataFrame with 'disposition' and 'judgment' columns.

    Returns:
        DataFrame with new 'outcome' column (0=defendant_win, 1=plaintiff_win).
        Rows with ambiguous outcomes are excluded.
    """
    original_count = len(df)
    df = df.copy()

    # Disposition codes that always mean defendant win
    defendant_win_dispositions = {2, 3, 12}

    # Disposition codes that require judgment field
    judgment_dependent_dispositions = {4, 5, 6, 7, 8, 9, 18}

    # Disposition codes to exclude (transfers, remands, settlements, etc.)
    exclude_dispositions = {0, 1, 10, 11, 13, 14, 15}

    # Convert disposition to numeric if needed
    df['disposition'] = pd.to_numeric(df['disposition'], errors='coerce')
    df['judgment'] = pd.to_numeric(df['judgment'], errors='coerce').fillna(0)

    # Initialize outcome column
    df['outcome'] = pd.NA

    # Direct defendant wins
    df.loc[df['disposition'].isin(defendant_win_dispositions), 'outcome'] = 0

    # Judgment-dependent dispositions
    judgment_mask = df['disposition'].isin(judgment_dependent_dispositions)
    df.loc[judgment_mask & (df['judgment'] == 1), 'outcome'] = 1  # plaintiff win
    df.loc[judgment_mask & (df['judgment'] == 2), 'outcome'] = 0  # defendant win

    # Drop rows without clear outcome (excluded dispositions, judgment 3/4/0, etc.)
    df = df.dropna(subset=['outcome'])
    df['outcome'] = df['outcome'].astype(int)

    excluded_count = original_count - len(df)
    logger.info(f"Mapped outcomes: {len(df)} rows remain, {excluded_count} excluded")

    return df


def filter_nos(df: pd.DataFrame, nos_codes: list[int] = None) -> pd.DataFrame:
    """Filter DataFrame by Nature of Suit codes.

    Args:
        df: DataFrame with 'nature_of_suit' column (string values).
        nos_codes: List of NOS codes to keep. Defaults to employment
                   discrimination codes [442, 445, 446].

    Returns:
        Filtered DataFrame containing only rows matching the NOS codes.
    """
    if nos_codes is None:
        nos_codes = [442, 445, 446]

    # Convert codes to strings since nature_of_suit column contains strings
    nos_codes_str = [str(code) for code in nos_codes]

    filtered = df[df['nature_of_suit'].isin(nos_codes_str)]
    logger.info(f"Filtered {len(df)} rows to {len(filtered)} with NOS codes {nos_codes}")

    return filtered
