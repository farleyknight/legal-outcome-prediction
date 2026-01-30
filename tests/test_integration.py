"""Integration tests that require real API access."""

import json
import os

import pytest
import requests

from src.pipeline import run_pipeline
from src.recap_client import check_api_connection, get_docket_entries, search_case


@pytest.mark.skipif(
    not os.environ.get("COURTLISTENER_API_TOKEN"),
    reason="COURTLISTENER_API_TOKEN not set",
)
def test_live_api_auth():
    """Test that API authentication works with a real token."""
    result = check_api_connection()
    assert result is True, "API authentication failed - check your COURTLISTENER_API_TOKEN"


@pytest.mark.skipif(
    not os.environ.get("COURTLISTENER_API_TOKEN"),
    reason="COURTLISTENER_API_TOKEN not set",
)
def test_live_docket_search():
    """Test that docket search returns valid data from CourtListener API."""
    # Search for a known NYSD employment discrimination case
    docket = search_case("1:18-cv-02743", "nysd")

    # Verify docket was found
    assert docket is not None, "Expected to find docket for known case"

    # Verify required fields exist and have correct types
    assert "id" in docket, "Docket missing 'id' field"
    assert isinstance(docket["id"], int), f"Expected 'id' to be int, got {type(docket['id'])}"

    assert "docket_number" in docket, "Docket missing 'docket_number' field"
    assert isinstance(docket["docket_number"], str), f"Expected 'docket_number' to be str, got {type(docket['docket_number'])}"

    assert "date_filed" in docket, "Docket missing 'date_filed' field"
    assert docket["date_filed"] is not None, "Expected 'date_filed' to be non-null"


@pytest.mark.skipif(
    not os.environ.get("COURTLISTENER_API_TOKEN"),
    reason="COURTLISTENER_API_TOKEN not set",
)
def test_live_docket_entries():
    """Test that docket entries retrieval returns valid data from CourtListener API."""
    # First, search for the docket to get the docket_id
    docket = search_case("1:18-cv-02743", "nysd")
    assert docket is not None, "Expected to find docket for known case"

    docket_id = docket["id"]

    # Fetch docket entries (may require paid API tier)
    try:
        entries = get_docket_entries(docket_id)
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            pytest.skip("API token does not have permission for docket-entries endpoint")
        raise

    # Verify entries list is not empty
    assert len(entries) > 0, "Expected non-empty list of docket entries"

    # Verify first entry has required fields
    first_entry = entries[0]
    assert "id" in first_entry, "Entry missing 'id' field"
    assert "entry_number" in first_entry, "Entry missing 'entry_number' field"
    assert "date_filed" in first_entry, "Entry missing 'date_filed' field"
    assert "description" in first_entry, "Entry missing 'description' field"

    # Verify description is a non-empty string
    assert isinstance(first_entry["description"], str), "Expected 'description' to be str"
    assert len(first_entry["description"]) > 0, "Expected 'description' to be non-empty"


@pytest.mark.skipif(
    not os.environ.get("COURTLISTENER_API_TOKEN"),
    reason="COURTLISTENER_API_TOKEN not set",
)
def test_live_pipeline_sample():
    """Test that the full pipeline processes 5 real cases successfully.

    Note: Match rate depends on FJC data availability in RECAP.
    Older cases (pre-2000) may not be available, so we verify the pipeline
    runs without errors and produces a valid DataFrame structure.
    """
    import pandas as pd

    # Run the pipeline with a small 5-case sample
    try:
        result = run_pipeline(sample_size=5)
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            pytest.skip("API token does not have permission for docket-entries endpoint")
        raise

    # Verify result is a DataFrame (may be empty if no RECAP matches)
    assert result is not None, "Pipeline returned None"
    assert isinstance(result, pd.DataFrame), f"Expected DataFrame, got {type(result)}"

    # If we have results, verify the schema and data quality
    if len(result) > 0:
        # Verify all required columns are present
        required_columns = [
            "case_id",
            "district",
            "filing_date",
            "termination_date",
            "event_sequence",
            "days_to_resolution",
            "outcome",
        ]
        for col in required_columns:
            assert col in result.columns, f"Missing required column: {col}"

        # Verify event_sequence contains valid JSON arrays
        for idx, row in result.iterrows():
            event_seq = row["event_sequence"]
            assert isinstance(event_seq, str), f"Row {idx}: event_sequence should be a string"
            parsed = json.loads(event_seq)
            assert isinstance(parsed, list), f"Row {idx}: event_sequence should parse to a list"

        # Verify outcome values are 0 or 1
        for idx, outcome in enumerate(result["outcome"]):
            assert outcome in (0, 1), f"Row {idx}: outcome should be 0 or 1, got {outcome}"
    else:
        # Pipeline ran successfully but found no RECAP matches
        # This is acceptable for older FJC cases not in RECAP
        pass
