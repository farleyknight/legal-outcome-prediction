"""Docket entry normalization and event parsing."""


def parse_docket_entry(entry: dict) -> dict:
    """Parse a raw docket entry into a normalized event."""
    raise NotImplementedError


def normalize_event_sequence(entries: list[dict]) -> list[dict]:
    """Normalize a sequence of docket entries into events."""
    raise NotImplementedError
