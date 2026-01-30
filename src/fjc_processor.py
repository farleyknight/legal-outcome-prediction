"""FJC IDB data download and filtering."""

import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# FJC IDB civil terminations data URL
FJC_CIVIL_URL = "https://www.fjc.gov/sites/default/files/idb/textfiles/cv88on.zip"
DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_FILE = DATA_DIR / "fjc_civil.csv"


def download_fjc_data() -> Path:
    """Download FJC IDB civil terminations data.

    Downloads the FJC IDB civil cases dataset and caches it locally.
    If the file already exists, returns the cached version.

    Returns:
        Path to the downloaded/cached CSV file.
    """
    if CACHE_FILE.exists():
        logger.info(f"Using cached FJC data: {CACHE_FILE}")
        return CACHE_FILE

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading FJC IDB civil data from {FJC_CIVIL_URL}")

    response = requests.get(FJC_CIVIL_URL, timeout=300, stream=True)
    response.raise_for_status()

    # FJC provides data as a zip file containing the CSV
    import io
    import zipfile

    zip_buffer = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_buffer) as zf:
        # Find the CSV file in the archive
        csv_files = [f for f in zf.namelist() if f.endswith('.txt') or f.endswith('.csv')]
        if not csv_files:
            raise ValueError("No CSV/TXT file found in FJC zip archive")

        csv_name = csv_files[0]
        logger.info(f"Extracting {csv_name} from archive")

        with zf.open(csv_name) as src, open(CACHE_FILE, 'wb') as dst:
            dst.write(src.read())

    logger.info(f"FJC data saved to {CACHE_FILE}")
    return CACHE_FILE


def filter_cases(nos_codes: list[int]):
    """Filter cases by Nature of Suit codes."""
    raise NotImplementedError
