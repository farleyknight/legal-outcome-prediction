"""Filter Matt Clark dataset to employment discrimination cases only.

Creates filtered versions of cases.zip and entries files containing only
cases that match FJC IDB employment discrimination cases (NOS codes 442, 445, 446).

Usage:
    python -m src.matt_clark_filter [--dry-run] [--years 2020-2024]
"""

import argparse
import csv
import logging
import zipfile
from io import StringIO, TextIOWrapper
from pathlib import Path

import pandas as pd

from src.fjc_processor import (
    download_fjc_data,
    extract_case_id,
    filter_nos,
    normalize_docket_number,
)
from src.matt_clark_parser import MATT_CLARK_DIR, load_cases_df

logger = logging.getLogger(__name__)


def load_fjc_employment_cases() -> pd.DataFrame:
    """Load FJC data filtered to employment discrimination cases.

    Returns:
        DataFrame with columns: district, docket_number_normalized, case_id
    """
    fjc_path = download_fjc_data()
    # Use on_bad_lines='skip' to handle malformed rows in the FJC data
    fjc_df = pd.read_csv(fjc_path, low_memory=False, on_bad_lines='skip')

    # Convert nature_of_suit to string for filter_nos (pandas reads as int)
    fjc_df['nature_of_suit'] = fjc_df['nature_of_suit'].astype(str)

    # Filter to employment discrimination (NOS 442, 445, 446)
    fjc_df = filter_nos(fjc_df)

    # Extract case identifiers
    fjc_df = extract_case_id(fjc_df)

    logger.info(f"Loaded {len(fjc_df)} FJC employment discrimination cases")

    return fjc_df[['district', 'docket_number_normalized', 'case_id']].drop_duplicates()


def build_match_lookup(fjc_df: pd.DataFrame) -> set[tuple[str, str]]:
    """Build a lookup set of (court, normalized_docket_number) tuples.

    Args:
        fjc_df: DataFrame with district and docket_number_normalized columns.

    Returns:
        Set of (court, docket_number) tuples for fast lookup.
    """
    lookup = set()
    for _, row in fjc_df.iterrows():
        # FJC uses district_id like "nysd", Matt Clark uses "court" same format
        court = row['district'].lower().strip()
        docket = row['docket_number_normalized'].lower().strip()
        lookup.add((court, docket))

    logger.info(f"Built lookup with {len(lookup)} unique (court, docket) pairs")
    return lookup


def normalize_matt_clark_docket(docket_number: str) -> str:
    """Normalize Matt Clark docket number to match FJC format.

    Matt Clark format: "1:19-cv-01234" -> "2019cv01234"
    """
    return normalize_docket_number(docket_number).lower()


def filter_cases(match_lookup: set[tuple[str, str]], dry_run: bool = False) -> set[int]:
    """Filter cases.zip to only employment discrimination cases.

    Args:
        match_lookup: Set of (court, docket_number) tuples to match.
        dry_run: If True, don't write output file.

    Returns:
        Set of matched docket_ids for filtering entries.
    """
    cases_df = load_cases_df()

    # Normalize Matt Clark docket numbers for matching
    cases_df['docket_normalized'] = cases_df['docket_number'].astype(str).apply(
        normalize_matt_clark_docket
    )
    cases_df['court_lower'] = cases_df['court'].str.lower().str.strip()

    # Match cases
    matched_mask = cases_df.apply(
        lambda row: (row['court_lower'], row['docket_normalized']) in match_lookup,
        axis=1
    )
    matched_cases = cases_df[matched_mask]
    matched_docket_ids = set(matched_cases['docket_id'].astype(int).tolist())

    logger.info(
        f"Matched {len(matched_cases)} of {len(cases_df)} Matt Clark cases "
        f"({100*len(matched_cases)/len(cases_df):.2f}%)"
    )

    if dry_run:
        logger.info("[DRY RUN] Would write filtered cases.zip")
    else:
        output_path = MATT_CLARK_DIR / "cases_filtered.zip"
        write_filtered_cases(matched_cases, output_path)
        logger.info(f"Wrote filtered cases to {output_path}")

    return matched_docket_ids


def write_filtered_cases(df: pd.DataFrame, output_path: Path) -> None:
    """Write filtered cases DataFrame to a ZIP file.

    Args:
        df: Filtered cases DataFrame.
        output_path: Path for output ZIP file.
    """
    # Drop helper columns before writing
    df = df.drop(columns=['docket_normalized', 'court_lower'], errors='ignore')

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV to memory buffer
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_content = csv_buffer.getvalue().encode('utf-8')

    # Write to ZIP
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('cases.csv', csv_content)


def filter_entries(
    year: int, matched_docket_ids: set[int], dry_run: bool = False
) -> int:
    """Filter entries file for a year to only matched cases.

    Args:
        year: Year to filter.
        matched_docket_ids: Set of docket_ids to keep.
        dry_run: If True, don't write output file.

    Returns:
        Count of matched entries.
    """
    zip_path = MATT_CLARK_DIR / f"{year}entries.zip"
    if not zip_path.exists():
        logger.warning(f"Entries file not found: {zip_path}")
        return 0

    logger.info(f"Filtering entries for {year}...")

    matched_entries = []

    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Find the entries CSV
        csv_name = None
        for name in zf.namelist():
            if name.endswith('entries.csv'):
                csv_name = name
                break

        if csv_name is None:
            logger.warning(f"No entries.csv found in {zip_path}")
            return 0

        with zf.open(csv_name) as f:
            text_file = TextIOWrapper(f, encoding='utf-8')
            reader = csv.DictReader(text_file)

            for row in reader:
                try:
                    docket_id = int(row.get('docket_id', 0))
                    if docket_id in matched_docket_ids:
                        matched_entries.append(row)
                except (ValueError, TypeError):
                    continue

    logger.info(f"Matched {len(matched_entries)} entries for {year}")

    if dry_run:
        logger.info(f"[DRY RUN] Would write {year}entries_filtered.zip")
    elif matched_entries:
        output_path = MATT_CLARK_DIR / f"{year}entries_filtered.zip"
        write_filtered_entries(matched_entries, output_path, year)
        logger.info(f"Wrote filtered entries to {output_path}")

    return len(matched_entries)


def write_filtered_entries(
    entries: list[dict], output_path: Path, year: int
) -> None:
    """Write filtered entries to a ZIP file.

    Args:
        entries: List of entry dicts.
        output_path: Path for output ZIP file.
        year: Year for filename inside ZIP.
    """
    if not entries:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV to memory buffer
    csv_buffer = StringIO()
    fieldnames = list(entries[0].keys())
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(entries)
    csv_content = csv_buffer.getvalue().encode('utf-8')

    # Write to ZIP
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f'{year}entries.csv', csv_content)


def parse_years(years_str: str) -> list[int]:
    """Parse years argument string to list of ints.

    Supports formats like:
    - "2020" -> [2020]
    - "2020,2021,2022" -> [2020, 2021, 2022]
    - "2020-2023" -> [2020, 2021, 2022, 2023]
    """
    if '-' in years_str and ',' not in years_str:
        start, end = years_str.split('-')
        return list(range(int(start), int(end) + 1))
    elif ',' in years_str:
        return [int(y.strip()) for y in years_str.split(',')]
    else:
        return [int(years_str)]


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Filter Matt Clark dataset to employment discrimination cases"
    )
    parser.add_argument(
        "--years",
        type=str,
        default="2013-2025",
        help="Years to filter entries for. Supports: single (2020), "
             "comma-separated (2020,2021), or range (2020-2023). Default: 2013-2025"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be filtered without writing files"
    )
    parser.add_argument(
        "--cases-only",
        action="store_true",
        help="Only filter cases.zip (skip entries files)"
    )
    parser.add_argument(
        "--entries-only",
        action="store_true",
        help="Only filter entries files (requires cases_filtered.zip to exist)"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Parse years
    years = parse_years(args.years)
    logger.info(f"Target years: {years[0]}-{years[-1]} ({len(years)} years)")

    # Load FJC employment discrimination cases
    logger.info("Loading FJC employment discrimination cases...")
    fjc_df = load_fjc_employment_cases()
    match_lookup = build_match_lookup(fjc_df)

    # Filter cases
    if args.entries_only:
        # Load matched docket_ids from existing filtered cases
        filtered_cases_path = MATT_CLARK_DIR / "cases_filtered.zip"
        if not filtered_cases_path.exists():
            logger.error(
                "cases_filtered.zip not found. Run without --entries-only first."
            )
            exit(1)

        with zipfile.ZipFile(filtered_cases_path, 'r') as zf:
            with zf.open('cases.csv') as f:
                text_file = TextIOWrapper(f, encoding='utf-8')
                filtered_cases = pd.read_csv(text_file)
                matched_docket_ids = set(filtered_cases['docket_id'].astype(int).tolist())

        logger.info(f"Loaded {len(matched_docket_ids)} docket_ids from existing filtered cases")
    else:
        logger.info("Filtering cases...")
        matched_docket_ids = filter_cases(match_lookup, dry_run=args.dry_run)

    # Filter entries
    if not args.cases_only:
        logger.info(f"Filtering entries for {len(years)} years...")
        total_entries = 0
        for year in years:
            count = filter_entries(year, matched_docket_ids, dry_run=args.dry_run)
            total_entries += count

        logger.info(f"Total matched entries across all years: {total_entries}")

    logger.info("Filtering complete!")


if __name__ == "__main__":
    main()
