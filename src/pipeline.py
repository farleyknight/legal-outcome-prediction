"""Main pipeline orchestration."""

import logging

import pandas as pd

from src.fjc_processor import download_fjc_data, filter_nos, map_outcome, extract_case_id

logger = logging.getLogger(__name__)


def run_pipeline() -> pd.DataFrame:
    """Run the full data pipeline.

    Orchestrates the FJC data processing pipeline:
    1. Downloads FJC IDB data (or uses cached version)
    2. Filters by Nature of Suit codes (employment discrimination)
    3. Maps disposition/judgment to binary outcome
    4. Extracts case IDs for RECAP matching

    Returns:
        DataFrame with columns: case_id, district, outcome (plus original columns)
    """
    logger.info("Starting pipeline")

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

    logger.info(f"Pipeline complete: {len(df)} cases ready for RECAP matching")
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_pipeline()
