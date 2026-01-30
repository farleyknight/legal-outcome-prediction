"""Matt Clark Federal Court Dockets dataset downloader.

Downloads the Matt Clark dataset from Internet Archive:
https://archive.org/details/federal-court-dockets

This dataset contains 350M+ docket entries from 13M+ federal cases (2013-present).
"""

import argparse
import logging
import tempfile
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Internet Archive base URL for the Matt Clark dataset
ARCHIVE_BASE_URL = "https://archive.org/download/federal-court-dockets"

# Data directories
DATA_DIR = Path(__file__).parent.parent / "data"
MATT_CLARK_DIR = DATA_DIR / "matt_clark"

# Default years to download (2026 may be incomplete)
DEFAULT_YEARS = list(range(2013, 2026))

# Timeout for large file downloads (30 minutes)
DOWNLOAD_TIMEOUT = 1800


def download_file(url: str, dest_path: Path, dry_run: bool = False) -> bool:
    """Download a file from URL to destination path.

    Uses streaming download for large files. Skips if file already exists (cached).
    Writes to a temp file first then renames for atomic write.

    Args:
        url: URL to download from.
        dest_path: Local path to save file to.
        dry_run: If True, only log what would be downloaded without downloading.

    Returns:
        True if file was downloaded or already exists, False on error.
    """
    if dest_path.exists():
        logger.info(f"File already exists (cached): {dest_path}")
        return True

    if dry_run:
        logger.info(f"[DRY RUN] Would download: {url} -> {dest_path}")
        return True

    logger.info(f"Downloading: {url}")

    try:
        response = requests.get(url, timeout=DOWNLOAD_TIMEOUT, stream=True)
        response.raise_for_status()

        # Get file size for progress logging
        total_size = int(response.headers.get('content-length', 0))
        if total_size > 0:
            size_mb = total_size / (1024 * 1024)
            logger.info(f"File size: {size_mb:.1f} MB")

        # Write to temp file first for atomic write
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(dir=dest_path.parent)

        try:
            downloaded = 0
            with open(temp_fd, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            # Rename temp file to final destination
            Path(temp_path).rename(dest_path)
            logger.info(f"Downloaded: {dest_path}")
            return True

        except Exception:
            # Clean up temp file on error
            Path(temp_path).unlink(missing_ok=True)
            raise

    except requests.RequestException as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def get_cases_url() -> str:
    """Get URL for cases.zip file."""
    return f"{ARCHIVE_BASE_URL}/cases.zip"


def get_entries_url(year: int) -> str:
    """Get URL for entries file for a specific year."""
    return f"{ARCHIVE_BASE_URL}/{year}entries.zip"


def get_supporting_file_url(filename: str) -> str:
    """Get URL for supporting files (data_dictionary.csv, entries_count.csv)."""
    return f"{ARCHIVE_BASE_URL}/{filename}"


def download_cases(dry_run: bool = False) -> bool:
    """Download cases.zip (~600MB).

    Args:
        dry_run: If True, only log what would be downloaded.

    Returns:
        True if successful, False on error.
    """
    url = get_cases_url()
    dest_path = MATT_CLARK_DIR / "cases.zip"
    return download_file(url, dest_path, dry_run=dry_run)


def download_entries(years: list[int] = None, dry_run: bool = False) -> dict[int, bool]:
    """Download entries files for specified years.

    Args:
        years: List of years to download. Defaults to DEFAULT_YEARS.
        dry_run: If True, only log what would be downloaded.

    Returns:
        Dict mapping year to success status.
    """
    if years is None:
        years = DEFAULT_YEARS

    results = {}
    for year in years:
        url = get_entries_url(year)
        dest_path = MATT_CLARK_DIR / f"{year}entries.zip"
        results[year] = download_file(url, dest_path, dry_run=dry_run)

    return results


def download_supporting_files(dry_run: bool = False) -> dict[str, bool]:
    """Download supporting files (data dictionary, entries count).

    Args:
        dry_run: If True, only log what would be downloaded.

    Returns:
        Dict mapping filename to success status.
    """
    files = ["data_dictionary.csv", "entries_count.csv"]
    results = {}

    for filename in files:
        url = get_supporting_file_url(filename)
        dest_path = MATT_CLARK_DIR / filename
        results[filename] = download_file(url, dest_path, dry_run=dry_run)

    return results


def parse_years(years_str: str) -> list[int]:
    """Parse years argument string to list of ints.

    Supports formats like:
    - "2020" -> [2020]
    - "2020,2021,2022" -> [2020, 2021, 2022]
    - "2020-2023" -> [2020, 2021, 2022, 2023]

    Args:
        years_str: Years specification string.

    Returns:
        List of year integers.
    """
    if '-' in years_str and ',' not in years_str:
        # Range format: "2020-2023"
        start, end = years_str.split('-')
        return list(range(int(start), int(end) + 1))
    elif ',' in years_str:
        # Comma-separated: "2020,2021,2022"
        return [int(y.strip()) for y in years_str.split(',')]
    else:
        # Single year: "2020"
        return [int(years_str)]


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Download Matt Clark Federal Court Dockets dataset from archive.org"
    )
    parser.add_argument(
        "--years",
        type=str,
        default="2013-2025",
        help="Years to download entries for. Supports: single (2020), "
             "comma-separated (2020,2021), or range (2020-2023). Default: 2013-2025"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading"
    )
    parser.add_argument(
        "--cases-only",
        action="store_true",
        help="Only download cases.zip (skip entries files)"
    )
    parser.add_argument(
        "--entries-only",
        action="store_true",
        help="Only download entries files (skip cases.zip)"
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

    # Create output directory
    MATT_CLARK_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {MATT_CLARK_DIR}")

    # Track overall success
    success = True

    # Download cases.zip
    if not args.entries_only:
        logger.info("Downloading cases.zip...")
        if not download_cases(dry_run=args.dry_run):
            success = False

    # Download entries files
    if not args.cases_only:
        logger.info(f"Downloading entries for {len(years)} years...")
        results = download_entries(years, dry_run=args.dry_run)
        failed_years = [y for y, ok in results.items() if not ok]
        if failed_years:
            logger.error(f"Failed to download entries for years: {failed_years}")
            success = False

    # Download supporting files
    logger.info("Downloading supporting files...")
    results = download_supporting_files(dry_run=args.dry_run)
    failed_files = [f for f, ok in results.items() if not ok]
    if failed_files:
        logger.warning(f"Failed to download supporting files: {failed_files}")
        # Don't fail overall for missing supporting files

    if success:
        logger.info("Download complete!")
    else:
        logger.error("Some downloads failed. Check logs above.")
        exit(1)


if __name__ == "__main__":
    main()
