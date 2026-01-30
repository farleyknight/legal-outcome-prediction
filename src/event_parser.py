"""Docket entry normalization and event parsing."""

# Event type categories for normalized docket entries
EVENT_TYPES: list[str] = [
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


def parse_docket_entry(entry: dict) -> dict:
    """Parse a raw docket entry into a normalized event."""
    raise NotImplementedError


def normalize_event_sequence(entries: list[dict]) -> list[dict]:
    """Normalize a sequence of docket entries into events."""
    raise NotImplementedError
