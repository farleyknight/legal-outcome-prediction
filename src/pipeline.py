"""Main pipeline orchestration."""

import logging
from pathlib import Path

import pandas as pd

from src.fjc_processor import download_fjc_data, filter_nos, map_outcome, extract_case_id
from src.recap_client import search_case

logger = logging.getLogger(__name__)

LOGS_DIR = Path(__file__).parent.parent / "logs"
UNMATCHED_LOG_PATH = LOGS_DIR / "unmatched_cases.log"


def setup_unmatched_logger() -> logging.Logger:
    """Set up a dedicated logger for unmatched cases.

    Returns:
        Logger configured to write to logs/unmatched_cases.log
    """
    unmatched_logger = logging.getLogger("unmatched_cases")
    unmatched_logger.setLevel(logging.INFO)

    # Avoid adding duplicate handlers
    if not unmatched_logger.handlers:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(UNMATCHED_LOG_PATH)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        file_handler.setFormatter(formatter)
        unmatched_logger.addHandler(file_handler)

    return unmatched_logger


def run_pipeline() -> pd.DataFrame:
    """Run the full data pipeline.

    Orchestrates the FJC data processing pipeline:
    1. Downloads FJC IDB data (or uses cached version)
    2. Filters by Nature of Suit codes (employment discrimination)
    3. Maps disposition/judgment to binary outcome
    4. Extracts case IDs for RECAP matching
    5. Matches cases to RECAP and logs unmatched cases

    Returns:
        DataFrame with columns: case_id, district, outcome (plus original columns)
    """
    logger.info("Starting pipeline")
    unmatched_logger = setup_unmatched_logger()

    # Step 1: Download/load FJC data
    fjc_path = download_fjc_data()
    logger.info(f"Loading FJC data from {fjc_path}")
    df = pd.read_csv(fjc_path, dtype=str, low_memory=False)
    logger.info(f"Loaded {len(df)} rows from FJC data")

    # Step 2: Filter by NOS codes
    df = filter_nos(df)

    # Step 3: Map outcomes
    df = map_outcome(df)

    # Step 4: Extract case IDs
    df = extract_case_id(df)

    # Step 5: Match cases to RECAP and log unmatched
    matched_count = 0
    unmatched_count = 0

    for _, row in df.iterrows():
        case_id = row["case_id"]
        district = row["district"]
        # Parse case_id format: "district:docket_number"
        parts = case_id.split(":")
        if len(parts) == 2:
            court = parts[0].lower()
            docket_number = parts[1]
            try:
                result = search_case(docket_number, court)
                if result is None:
                    unmatched_count += 1
                    unmatched_logger.info(
                        f"case_id={case_id} district={district} docket_number={docket_number}"
                    )
                else:
                    matched_count += 1
            except Exception as e:
                unmatched_count += 1
                unmatched_logger.info(
                    f"case_id={case_id} district={district} docket_number={docket_number} error={e}"
                )
        else:
            unmatched_count += 1
            unmatched_logger.info(
                f"case_id={case_id} district={district} invalid_format=true"
            )

    logger.info(
        f"RECAP matching complete: {matched_count} matched, {unmatched_count} unmatched"
    )
    logger.info(f"Pipeline complete: {len(df)} cases processed")
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_pipeline()
