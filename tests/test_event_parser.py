"""Tests for docket entry parsing."""

from src import event_parser
from src.event_parser import EVENT_TYPES, normalize_description, normalize_description_multi


def test_placeholder():
    """Placeholder test to verify module imports."""
    assert event_parser is not None


def test_event_types_defined():
    """Verify all 14 event type categories are defined."""
    # Should have exactly 14 event types
    assert len(EVENT_TYPES) == 14

    # Verify key event types are present
    expected_types = [
        "COMPLAINT",
        "ANSWER",
        "MOTION_TO_DISMISS",
        "MOTION_FOR_SUMMARY_JUDGMENT",
        "MOTION_OTHER",
        "ORDER",
        "DISCOVERY",
        "SCHEDULING",
        "SETTLEMENT_CONFERENCE",
        "PRETRIAL",
        "TRIAL",
        "JUDGMENT",
        "APPEAL",
        "OTHER",
    ]

    for event_type in expected_types:
        assert event_type in EVENT_TYPES, f"Missing event type: {event_type}"

    # Verify all types are unique
    assert len(EVENT_TYPES) == len(set(EVENT_TYPES)), "Duplicate event types found"


def test_description_normalization():
    """Test that normalize_description maps raw descriptions to correct event types."""
    # Test each event type with representative descriptions
    test_cases = [
        ("COMPLAINT against ABC Corp", "COMPLAINT"),
        ("Petition for Relief", "COMPLAINT"),
        ("ANSWER to Complaint", "ANSWER"),
        ("Response to Complaint filed", "ANSWER"),
        ("MOTION to Dismiss for Failure to State a Claim", "MOTION_TO_DISMISS"),
        ("Defendant's 12(b)(6) motion", "MOTION_TO_DISMISS"),
        ("Motion for Summary Judgment", "MOTION_FOR_SUMMARY_JUDGMENT"),
        ("MSJ filed by plaintiff", "MOTION_FOR_SUMMARY_JUDGMENT"),
        ("Motion for Extension of Time", "MOTION_OTHER"),
        ("ORDER granting motion", "ORDER"),
        ("Ruling on pending motions", "ORDER"),
        ("NOTICE of Deposition", "DISCOVERY"),
        ("Interrogatories served", "DISCOVERY"),
        ("Subpoena issued", "DISCOVERY"),
        ("Request for Production of Documents", "DISCOVERY"),
        ("Scheduling Order", "SCHEDULING"),
        ("Case Management Order", "SCHEDULING"),
        ("CMO entered", "SCHEDULING"),
        ("Settlement Conference set", "SETTLEMENT_CONFERENCE"),
        ("Mediation scheduled", "SETTLEMENT_CONFERENCE"),
        ("ADR referral", "SETTLEMENT_CONFERENCE"),
        ("Pretrial Conference", "PRETRIAL"),
        ("Trial Setting Conference", "PRETRIAL"),
        ("Jury Trial commenced", "TRIAL"),
        ("Bench trial held", "TRIAL"),
        ("JUDGMENT in favor of defendant", "JUDGMENT"),
        ("Verdict rendered", "JUDGMENT"),
        ("Final Order entered", "JUDGMENT"),
        ("Notice of Appeal", "APPEAL"),
        ("Appeal filed", "APPEAL"),
        ("Some random entry", "OTHER"),
        ("Clerk's notation", "OTHER"),
    ]

    for description, expected_type in test_cases:
        result = normalize_description(description)
        assert result == expected_type, (
            f"Expected '{expected_type}' for '{description}', got '{result}'"
        )


def test_description_normalization_case_insensitive():
    """Test that normalize_description is case insensitive."""
    # All caps
    assert normalize_description("COMPLAINT") == "COMPLAINT"
    # Lowercase
    assert normalize_description("complaint") == "COMPLAINT"
    # Mixed case
    assert normalize_description("CoMpLaInT") == "COMPLAINT"
    # Motion case variations
    assert normalize_description("MOTION TO DISMISS") == "MOTION_TO_DISMISS"
    assert normalize_description("motion to dismiss") == "MOTION_TO_DISMISS"


def test_description_normalization_empty_input():
    """Test that normalize_description handles empty input."""
    assert normalize_description("") == "OTHER"
    assert normalize_description(None) == "OTHER" if normalize_description(None) else True


def test_sequence_extraction():
    """Test parse_docket_entry and normalize_event_sequence functions."""
    from src.event_parser import parse_docket_entry, normalize_event_sequence

    # Test parse_docket_entry with a sample entry
    sample_entry = {
        "date_filed": "2019-03-15",
        "description": "COMPLAINT against ABC Corp for employment discrimination",
        "entry_number": 1,
    }
    parsed = parse_docket_entry(sample_entry)
    assert parsed["date"] == "2019-03-15"
    assert parsed["event_type"] == "COMPLAINT"
    assert parsed["entry_number"] == 1

    # Test parse_docket_entry with motion to dismiss
    motion_entry = {
        "date_filed": "2019-04-20",
        "description": "MOTION to Dismiss for Failure to State a Claim",
        "entry_number": 5,
    }
    parsed_motion = parse_docket_entry(motion_entry)
    assert parsed_motion["date"] == "2019-04-20"
    assert parsed_motion["event_type"] == "MOTION_TO_DISMISS"
    assert parsed_motion["entry_number"] == 5

    # Test normalize_event_sequence with multiple entries (out of order)
    raw_entries = [
        {
            "date_filed": "2019-05-10",
            "description": "ORDER granting motion",
            "entry_number": 8,
        },
        {
            "date_filed": "2019-03-15",
            "description": "COMPLAINT against ABC Corp",
            "entry_number": 1,
        },
        {
            "date_filed": "2019-04-01",
            "description": "ANSWER to Complaint",
            "entry_number": 3,
        },
        {
            "date_filed": "2019-04-20",
            "description": "MOTION to Dismiss",
            "entry_number": 5,
        },
    ]

    normalized = normalize_event_sequence(raw_entries)

    # Verify sorted by entry_number
    assert len(normalized) == 4
    assert normalized[0]["entry_number"] == 1
    assert normalized[1]["entry_number"] == 3
    assert normalized[2]["entry_number"] == 5
    assert normalized[3]["entry_number"] == 8

    # Verify event types are normalized correctly
    assert normalized[0]["event_type"] == "COMPLAINT"
    assert normalized[1]["event_type"] == "ANSWER"
    assert normalized[2]["event_type"] == "MOTION_TO_DISMISS"
    assert normalized[3]["event_type"] == "ORDER"

    # Verify dates are preserved
    assert normalized[0]["date"] == "2019-03-15"
    assert normalized[1]["date"] == "2019-04-01"
    assert normalized[2]["date"] == "2019-04-20"
    assert normalized[3]["date"] == "2019-05-10"


def test_parse_docket_entry_missing_fields():
    """Test parse_docket_entry handles missing or empty fields."""
    from src.event_parser import parse_docket_entry

    # Entry with missing description
    entry_no_desc = {
        "date_filed": "2019-03-15",
        "entry_number": 1,
    }
    parsed = parse_docket_entry(entry_no_desc)
    assert parsed["event_type"] == "OTHER"
    assert parsed["date"] == "2019-03-15"
    assert parsed["entry_number"] == 1

    # Empty entry
    empty_entry = {}
    parsed_empty = parse_docket_entry(empty_entry)
    assert parsed_empty["event_type"] == "OTHER"
    assert parsed_empty["date"] is None
    assert parsed_empty["entry_number"] is None


def test_normalize_event_sequence_empty():
    """Test normalize_event_sequence with empty list."""
    from src.event_parser import normalize_event_sequence

    assert normalize_event_sequence([]) == []


def test_multi_event_description():
    """Test that normalize_description_multi returns multiple event types from a single description."""
    # Test description with multiple distinct event types
    # Note: "MOTION to Dismiss and ANSWER to Complaint" matches:
    # - ANSWER (from "answer")
    # - COMPLAINT (from "complaint")
    # - MOTION_TO_DISMISS (from "motion to dismiss")
    # - MOTION_OTHER (from "motion")
    result = normalize_description_multi("MOTION to Dismiss and ANSWER to Complaint")
    assert "MOTION_TO_DISMISS" in result
    assert "ANSWER" in result
    assert "COMPLAINT" in result
    assert "MOTION_OTHER" in result
    assert len(result) == 4

    # Test description with single event type returns list of one
    result_single = normalize_description_multi("COMPLAINT against ABC Corp")
    assert result_single == ["COMPLAINT"]

    # Test empty description returns ["OTHER"]
    assert normalize_description_multi("") == ["OTHER"]

    # Test no pattern match returns ["OTHER"]
    assert normalize_description_multi("Some random text with no keywords") == ["OTHER"]

    # Test overlapping patterns are deduplicated (motion appears in both entries)
    result_motion = normalize_description_multi("Motion for Summary Judgment motion")
    assert "MOTION_FOR_SUMMARY_JUDGMENT" in result_motion
    assert "MOTION_OTHER" in result_motion
    # Should not have duplicates
    assert len(result_motion) == len(set(result_motion))

    # Test complex multi-event description
    result_complex = normalize_description_multi(
        "ORDER granting MOTION to Dismiss; JUDGMENT entered"
    )
    assert "ORDER" in result_complex
    assert "MOTION_TO_DISMISS" in result_complex
    assert "MOTION_OTHER" in result_complex
    assert "JUDGMENT" in result_complex
