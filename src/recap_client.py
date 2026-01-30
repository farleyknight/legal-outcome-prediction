"""CourtListener API client for RECAP docket entries."""


def search_case(case_number: str, court: str):
    """Search for a case in RECAP via CourtListener API."""
    raise NotImplementedError


def get_docket_entries(docket_id: int):
    """Get docket entries for a given docket ID."""
    raise NotImplementedError
