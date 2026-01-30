"""FJC IDB data download and filtering."""

import bz2
import logging
import re
from datetime import date
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)


def normalize_docket_number(docket_number: str) -> str:
    """Normalize docket number to a consistent format for RECAP API matching.

    Handles various input formats:
    - FJC short format: "191234" → "2019cv1234"
    - FJC long format: "20191234" → "2019cv1234"
    - CourtListener format: "1:19-cv-01234" → "2019cv01234"
    - Hyphenated format: "19-cv-1234" → "2019cv1234"
    - Already normalized: "1:2019cv12345" → "2019cv12345"

    Args:
        docket_number: Raw docket number string in any format.

    Returns:
        Normalized docket number in format "{year}cv{sequence}" for API search.
        Returns cleaned original string if format cannot be parsed.
    """
    if not docket_number or not isinstance(docket_number, str):
        return str(docket_number) if docket_number else ""

    docket_number = docket_number.strip()

    # Pattern 1: CourtListener format "1:19-cv-01234" or "19-cv-1234"
    # Matches optional division prefix, 2 or 4 digit year, -cv-, sequence
    cl_pattern = r'^(?:\d+:)?(\d{2,4})-cv-(\d+)$'
    match = re.match(cl_pattern, docket_number, re.IGNORECASE)
    if match:
        year_str, sequence = match.groups()
        year = _normalize_year(year_str)
        return f"{year}cv{sequence}"

    # Pattern 2: Already semi-normalized "1:2019cv12345" or "2019cv12345"
    # Matches optional division prefix, 4-digit year, cv, sequence
    semi_pattern = r'^(?:\d+:)?(\d{4})cv(\d+)$'
    match = re.match(semi_pattern, docket_number, re.IGNORECASE)
    if match:
        year_str, sequence = match.groups()
        return f"{year_str}cv{sequence}"

    # Pattern 3: FJC numeric format - just digits
    # Short: 6 digits "YYDDDDD" (2-digit year + 4-digit sequence)
    # Long: 8+ digits "YYYYDDDDD" (4-digit year + sequence)
    if docket_number.isdigit():
        if len(docket_number) <= 6:
            # Short format: first 2 digits are year
            year_str = docket_number[:2]
            sequence = docket_number[2:]
            year = _normalize_year(year_str)
            return f"{year}cv{sequence}"
        else:
            # Long format: first 4 digits are year
            year_str = docket_number[:4]
            sequence = docket_number[4:]
            return f"{year_str}cv{sequence}"

    # Cannot parse - return cleaned string
    return docket_number


def _normalize_year(year_str: str) -> str:
    """Convert 2-digit year to 4-digit year.

    Assumes years 00-29 are 2000s, 30-99 are 1900s.
    If already 4 digits, returns as-is.
    """
    if len(year_str) == 4:
        return year_str
    year_int = int(year_str)
    if year_int <= 29:
        return f"20{year_str.zfill(2)}"
    else:
        return f"19{year_str.zfill(2)}"


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


def extract_case_id(df: pd.DataFrame) -> pd.DataFrame:
    """Extract district and create case_id from FJC data.

    Args:
        df: DataFrame with 'district_id' column (CourtListener format).

    Returns:
        DataFrame with new 'district' and 'case_id' columns.
        Rows with missing/empty district are dropped.
    """
    df = df.copy()

    # Convert district_id to lowercase string, stripping whitespace
    df['district'] = df['district_id'].astype(str).str.strip().str.lower()

    # Drop rows with missing or empty district (can't match to RECAP)
    invalid_mask = df['district'].isin(['', 'nan', 'none', 'null'])
    df = df[~invalid_mask]

    # Normalize docket numbers for consistent API matching
    df['docket_number_normalized'] = df['docket_number'].astype(str).apply(normalize_docket_number)

    # Create case_id in format "{district}:{docket_number_normalized}"
    df['case_id'] = df['district'] + ':' + df['docket_number_normalized']

    dropped_count = invalid_mask.sum()
    if dropped_count > 0:
        logger.info(f"Dropped {dropped_count} rows with missing district")

    logger.info(f"Extracted case IDs for {len(df)} rows")

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
