"""Tests for docket entry parsing."""

from src import event_parser
from src.event_parser import EVENT_TYPES


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
