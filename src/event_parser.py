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

# Pattern matching rules for event type classification
# Order matters: specific/longer patterns must come before general/shorter ones
# Categories with compound terms (e.g., "scheduling order") must be checked before
# simple terms (e.g., "order") to avoid false matches
_EVENT_PATTERNS: list[tuple[str, list[str]]] = [
    # ANSWER must come before COMPLAINT because "response to complaint" contains "complaint"
    ("ANSWER", ["answer", "response to complaint"]),
    ("COMPLAINT", ["complaint", "petition"]),
    # Specific motion types before generic MOTION_OTHER
    ("MOTION_TO_DISMISS", ["motion to dismiss", "12(b)"]),
    ("MOTION_FOR_SUMMARY_JUDGMENT", ["summary judgment", "msj"]),
    # JUDGMENT has "final order" - check before ORDER
    ("APPEAL", ["notice of appeal", "appeal"]),
    ("JUDGMENT", ["judgment", "verdict", "final order"]),
    ("DISCOVERY", ["discovery", "interrogator", "deposition", "subpoena", "request for production"]),
    # SCHEDULING has "scheduling order" patterns, must come before ORDER
    ("SCHEDULING", ["scheduling", "case management", "cmo"]),
    ("SETTLEMENT_CONFERENCE", ["settlement", "mediation", "adr"]),
    # PRETRIAL has "trial setting" - must come before TRIAL
    ("PRETRIAL", ["pretrial", "trial setting"]),
    ("TRIAL", ["trial", "jury", "bench trial"]),
    # ORDER is generic - check after more specific types
    ("ORDER", ["order", "ruling"]),
    # MOTION_OTHER must come last among motion types
    ("MOTION_OTHER", ["motion"]),
]


def normalize_description(description: str) -> str:
    """Map a raw docket entry description to an EVENT_TYPE category.

    Args:
        description: Raw docket entry text (e.g., "COMPLAINT against ABC Corp...")

    Returns:
        One of the EVENT_TYPES strings (e.g., "COMPLAINT", "MOTION_TO_DISMISS", etc.)
        Returns "OTHER" if no patterns match.
    """
    if not description:
        return "OTHER"

    desc_lower = description.lower()

    for event_type, patterns in _EVENT_PATTERNS:
        for pattern in patterns:
            if pattern in desc_lower:
                return event_type

    return "OTHER"


def parse_docket_entry(entry: dict) -> dict:
    """Parse a raw docket entry into a normalized event.

    Args:
        entry: Raw docket entry dict from API with keys:
            - date_filed: Date string (e.g., "2019-03-15")
            - description: Raw docket entry text
            - entry_number: Integer entry sequence number

    Returns:
        Normalized event dict with keys:
            - date: Date string from entry
            - event_type: Normalized EVENT_TYPE string
            - entry_number: Integer entry sequence number
    """
    return {
        "date": entry.get("date_filed"),
        "event_type": normalize_description(entry.get("description", "")),
        "entry_number": entry.get("entry_number"),
    }


def normalize_event_sequence(entries: list[dict]) -> list[dict]:
    """Normalize a sequence of docket entries into events.

    Args:
        entries: List of raw docket entry dicts from API, each with:
            - date_filed: Date string
            - description: Raw docket entry text
            - entry_number: Integer entry sequence number

    Returns:
        List of normalized event dicts sorted by entry_number, each with:
            - date: Date string
            - event_type: Normalized EVENT_TYPE string
            - entry_number: Integer entry sequence number
    """
    parsed = [parse_docket_entry(entry) for entry in entries]
    return sorted(parsed, key=lambda x: x.get("entry_number", 0))
