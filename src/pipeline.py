"""Main pipeline orchestration."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.fjc_processor import download_fjc_data, filter_nos, map_outcome, extract_case_id
from src.recap_client import search_case, get_docket_entries
from src.event_parser import normalize_event_sequence

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
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


def convert_fjc_date(date_str: str) -> str | None:
    """Convert FJC date format (YYYYMMDD) to ISO format (YYYY-MM-DD).

    Args:
        date_str: Date string in YYYYMMDD format.

    Returns:
        Date string in YYYY-MM-DD format, or None if invalid.
    """
    if not date_str or len(date_str) != 8:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def calculate_days_to_resolution(filing_date: str, termination_date: str) -> int | None:
    """Calculate days between filing and termination dates.

    Args:
        filing_date: Filing date in YYYY-MM-DD format.
        termination_date: Termination date in YYYY-MM-DD format.

    Returns:
        Number of days between dates, or None if invalid.
    """
    if not filing_date or not termination_date:
        return None
    try:
        start = datetime.strptime(filing_date, "%Y-%m-%d")
        end = datetime.strptime(termination_date, "%Y-%m-%d")
        return (end - start).days
    except ValueError:
        return None


def run_pipeline(sample_size: int | None = None) -> pd.DataFrame:
    """Run the full data pipeline.

    Orchestrates the FJC data processing pipeline:
    1. Downloads FJC IDB data (or uses cached version)
    2. Filters by Nature of Suit codes (employment discrimination)
    3. Maps disposition/judgment to binary outcome
    4. Extracts case IDs for RECAP matching
    5. Matches cases to RECAP and fetches docket entries
    6. Generates output CSV with required schema

    Args:
        sample_size: If provided, limit to this many cases after filtering.

    Returns:
        DataFrame with output schema columns for matched cases.
    """
    logger.info("Starting pipeline")
    unmatched_logger = setup_unmatched_logger()

    # Step 1: Download/load FJC data
    fjc_path = download_fjc_data()
    logger.info(f"Loading FJC data from {fjc_path}")
    df = pd.read_csv(fjc_path, dtype=str, low_memory=False, on_bad_lines='skip')
    logger.info(f"Loaded {len(df)} rows from FJC data")

    # Step 2: Filter by NOS codes
    df = filter_nos(df)

    # Step 3: Map outcomes
    df = map_outcome(df)

    # Step 4: Extract case IDs
    df = extract_case_id(df)

    # Step 5: Apply sample size limit if specified
    if sample_size is not None and len(df) > sample_size:
        logger.info(f"Sampling {sample_size} cases from {len(df)} filtered cases")
        df = df.head(sample_size)

    # Step 6: Match cases to RECAP, fetch docket entries, build output
    output_rows = []
    matched_count = 0
    unmatched_count = 0

    for _, row in df.iterrows():
        case_id = row["case_id"]
        district = row["district"]
        # Parse case_id format: "district:docket_number" (docket_number may contain colons)
        parts = case_id.split(":", 1)
        if len(parts) != 2:
            unmatched_count += 1
            unmatched_logger.info(
                f"case_id={case_id} district={district} invalid_format=true"
            )
            continue

        court = parts[0].lower()
        docket_number = parts[1]

        try:
            result = search_case(docket_number, court)
            if result is None:
                unmatched_count += 1
                unmatched_logger.info(
                    f"case_id={case_id} district={district} docket_number={docket_number}"
                )
                continue

            # Fetch docket entries
            docket_id = result.get("id")
            if not docket_id:
                unmatched_count += 1
                unmatched_logger.info(
                    f"case_id={case_id} district={district} docket_number={docket_number} no_docket_id=true"
                )
                continue

            entries = get_docket_entries(docket_id)
            events = normalize_event_sequence(entries)
            event_types = [e["event_type"] for e in events]

            # Get dates (CourtListener format is already YYYY-MM-DD)
            filing_date = row.get("date_filed", "")
            termination_date = row.get("date_terminated", "")
            days_to_resolution = calculate_days_to_resolution(filing_date, termination_date)

            # Validate days_to_resolution is not negative (termination before filing)
            if days_to_resolution is not None and days_to_resolution < 0:
                unmatched_count += 1
                unmatched_logger.info(
                    f"case_id={case_id} district={district} negative_days_to_resolution=true "
                    f"filing_date={filing_date} termination_date={termination_date}"
                )
                continue

            # Build output row
            output_rows.append({
                "case_id": case_id,
                "district": district,
                "filing_date": filing_date,
                "termination_date": termination_date,
                "event_sequence": json.dumps(event_types),
                "days_to_resolution": days_to_resolution,
                "outcome": row["outcome"],
            })
            matched_count += 1

        except Exception as e:
            unmatched_count += 1
            unmatched_logger.info(
                f"case_id={case_id} district={district} docket_number={docket_number} error={e}"
            )

    logger.info(
        f"RECAP matching complete: {matched_count} matched, {unmatched_count} unmatched"
    )

    # Calculate and log match rate metrics
    total_count = matched_count + unmatched_count
    match_rate_percentage = (matched_count / total_count * 100) if total_count > 0 else 0.0
    logger.info(f"Match rate: {match_rate_percentage:.1f}% ({matched_count}/{total_count})")

    # Save metrics to JSON file
    metrics = {
        "matched_count": matched_count,
        "unmatched_count": unmatched_count,
        "total_count": total_count,
        "match_rate_percentage": round(match_rate_percentage, 2),
        "timestamp": datetime.now().isoformat(),
    }
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = LOGS_DIR / "match_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Match metrics saved to {metrics_path}")

    # Build output DataFrame
    output_df = pd.DataFrame(output_rows)
    logger.info(f"Pipeline complete: {len(output_df)} cases in output")

    # Save output CSV if we have results
    if sample_size is not None and len(output_df) > 0:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DATA_DIR / f"sample_{sample_size}.csv"
        output_df.to_csv(output_path, index=False)
        logger.info(f"Output saved to {output_path}")

    return output_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the legal outcome prediction pipeline")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Limit to N cases and save output to data/sample_N.csv"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    run_pipeline(sample_size=args.sample)
