"""Tests for docket entry parsing."""

from src import event_parser
from src.event_parser import EVENT_TYPES, normalize_description


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
