"""Matt Clark Federal Court Dockets dataset parser.

Parses the Matt Clark dataset CSV files from ZIP archives:
- cases.csv: Case metadata (docket_id, court, case_name, etc.)
- {year}entries.csv: Docket entries (docket_id, date_filed, description, etc.)

Dataset source: https://archive.org/details/federal-court-dockets
"""

import logging
import zipfile
from io import TextIOWrapper
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Data directories (matches matt_clark_downloader.py)
DATA_DIR = Path(__file__).parent.parent / "data"
MATT_CLARK_DIR = DATA_DIR / "matt_clark"

# Cached DataFrames to avoid re-parsing
_cases_df: pd.DataFrame | None = None
_entries_dfs: dict[int, pd.DataFrame] = {}


def load_cases_df() -> pd.DataFrame:
    """Load and parse cases.csv from cases.zip.

    Returns:
        DataFrame with case metadata. Key columns:
        - docket_id: Unique identifier for the case
        - court: Court abbreviation (e.g., "nysd", "cacd")
        - docket_number: The case number (e.g., "1:19-cv-01234")
        - case_name: Case title

    Raises:
        FileNotFoundError: If cases.zip does not exist.
    """
    global _cases_df

    if _cases_df is not None:
        logger.debug("Using cached cases DataFrame")
        return _cases_df

    zip_path = MATT_CLARK_DIR / "cases.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"Cases file not found: {zip_path}")

    logger.info(f"Loading cases from {zip_path}")

    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Find the cases.csv file inside the ZIP
        csv_name = None
        for name in zf.namelist():
            if name.endswith('cases.csv'):
                csv_name = name
                break

        if csv_name is None:
            raise FileNotFoundError("cases.csv not found in cases.zip")

        with zf.open(csv_name) as f:
            # Wrap in TextIOWrapper for pandas to read as text
            text_file = TextIOWrapper(f, encoding='utf-8')
            _cases_df = pd.read_csv(text_file, low_memory=False)

    logger.info(f"Loaded {len(_cases_df)} cases")
    return _cases_df


def load_entries_df(year: int) -> pd.DataFrame:
    """Load and parse {year}entries.csv from {year}entries.zip.

    Args:
        year: Year of entries to load (e.g., 2020).

    Returns:
        DataFrame with docket entries. Key columns:
        - docket_id: Foreign key to cases
        - date_filed: Date the entry was filed
        - description: Text description of the entry
        - entry_number: Sequential entry number within the case

    Raises:
        FileNotFoundError: If the entries ZIP file does not exist.
    """
    global _entries_dfs

    if year in _entries_dfs:
        logger.debug(f"Using cached entries DataFrame for {year}")
        return _entries_dfs[year]

    zip_path = MATT_CLARK_DIR / f"{year}entries.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"Entries file not found: {zip_path}")

    logger.info(f"Loading entries from {zip_path}")

    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Find the entries CSV file inside the ZIP
        csv_name = None
        for name in zf.namelist():
            if name.endswith(f'{year}entries.csv') or name.endswith('entries.csv'):
                csv_name = name
                break

        if csv_name is None:
            raise FileNotFoundError(f"{year}entries.csv not found in {zip_path}")

        with zf.open(csv_name) as f:
            text_file = TextIOWrapper(f, encoding='utf-8')
            _entries_dfs[year] = pd.read_csv(text_file, low_memory=False)

    logger.info(f"Loaded {len(_entries_dfs[year])} entries for {year}")
    return _entries_dfs[year]


def get_case_by_court_and_docket(court_id: str, docket_number: str) -> dict | None:
    """Look up a case by court ID and docket number.

    Args:
        court_id: Court abbreviation (e.g., "nysd", "cacd").
        docket_number: The docket number to search for.

    Returns:
        Dict with case data if found, None if not found.
        Keys include: docket_id, court, docket_number, case_name, etc.
    """
    cases_df = load_cases_df()

    # Normalize inputs for matching
    court_lower = court_id.lower().strip()
    docket_lower = docket_number.lower().strip()

    # Filter by court first (more selective)
    court_mask = cases_df['court'].str.lower().str.strip() == court_lower

    # Then match docket number
    # Try exact match first
    docket_mask = cases_df['docket_number'].str.lower().str.strip() == docket_lower

    matches = cases_df[court_mask & docket_mask]

    if len(matches) == 0:
        # Try partial match (docket number might be formatted differently)
        # Extract numeric parts for fuzzy matching
        docket_numeric = ''.join(filter(str.isdigit, docket_number))
        if docket_numeric:
            docket_mask = cases_df['docket_number'].str.replace(r'\D', '', regex=True) == docket_numeric
            matches = cases_df[court_mask & docket_mask]

    if len(matches) == 0:
        logger.debug(f"No case found for {court_id}:{docket_number}")
        return None

    # Return first match as dict
    case = matches.iloc[0].to_dict()
    logger.debug(f"Found case {case.get('docket_id')} for {court_id}:{docket_number}")
    return case


def get_entries_for_case(case_id: str, year: int | None = None) -> list[dict]:
    """Get all docket entries for a case.

    Args:
        case_id: The docket_id from the cases table.
        year: Year to load entries from. If None, will attempt to infer
              from the case data or search multiple years.

    Returns:
        List of entry dicts, each with date_filed, description, entry_number, etc.
        Returns empty list if no entries found.
    """
    # Convert case_id to the appropriate type for matching
    try:
        case_id_val = int(case_id)
    except (ValueError, TypeError):
        case_id_val = str(case_id)

    if year is not None:
        # Load specific year
        try:
            entries_df = load_entries_df(year)
            matches = entries_df[entries_df['docket_id'] == case_id_val]
            entries = matches.to_dict('records')
            logger.debug(f"Found {len(entries)} entries for case {case_id} in {year}")
            return entries
        except FileNotFoundError:
            logger.warning(f"Entries file for {year} not found")
            return []

    # Year not specified - search available years
    # Try to infer year from case metadata first
    all_entries = []

    # Check which entry files exist
    available_years = []
    for y in range(2013, 2027):
        if (MATT_CLARK_DIR / f"{y}entries.zip").exists():
            available_years.append(y)

    for y in available_years:
        try:
            entries_df = load_entries_df(y)
            matches = entries_df[entries_df['docket_id'] == case_id_val]
            if len(matches) > 0:
                all_entries.extend(matches.to_dict('records'))
        except FileNotFoundError:
            continue

    logger.debug(f"Found {len(all_entries)} entries for case {case_id} across {len(available_years)} years")
    return all_entries


def clear_cache() -> None:
    """Clear cached DataFrames to free memory."""
    global _cases_df, _entries_dfs
    _cases_df = None
    _entries_dfs = {}
    logger.debug("Cleared Matt Clark parser cache")
