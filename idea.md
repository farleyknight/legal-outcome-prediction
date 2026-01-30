# US Legal Outcome Prediction Dataset Builder

Python pipeline that creates a labeled dataset for predicting federal court 
case outcomes from docket entry sequences.

## Goal
Join FJC IDB outcomes (labels) with RECAP docket entries (features) to produce
a dataset suitable for sequence → outcome prediction models.

## Data Sources
- FJC Integrated Database (IDB): https://www.fjc.gov/research/idb
  - Civil terminations file (cv_1988-present.csv or similar)
  - Contains: case_id, disposition, judgment_for, nature_of_suit, dates
- RECAP / CourtListener API: https://www.courtlistener.com/api/rest/v4/
  - Docket entries with timestamps and descriptions
  - Free tier, rate limited

## Pipeline Steps

### 1. Download & Filter FJC Data
- Download FJC IDB civil terminations file
- Filter to employment discrimination cases (NOS 442, 445, 446)
- Filter to clear outcomes:
  - Judgment for plaintiff
  - Judgment for defendant  
  - Dismissed (various codes)
- Map to binary label: plaintiff_win (1) vs defendant_win_or_dismissed (0)
- Extract: district, office, docket_number, filing_date, termination_date, outcome

### 2. Build RECAP Query Keys
- Construct CourtListener-compatible case identifiers from FJC fields
- Format: {district_court}:{docket_number}

### 3. Fetch Docket Entries from RECAP
- Query CourtListener API for each case
- Handle rate limiting (sleep between requests)
- Cache responses locally to avoid re-fetching
- Extract: entry_number, date_filed, description

### 4. Parse Docket Entries to Event Sequences
- Normalize entry descriptions to event categories:
  - COMPLAINT, ANSWER, MOTION_TO_DISMISS, MOTION_FOR_SUMMARY_JUDGMENT,
    ORDER, DISCOVERY, SETTLEMENT_CONFERENCE, TRIAL, JUDGMENT, etc.
- Output sequence as ordered list of (date, event_type) tuples

### 5. Assemble Final Dataset
- Join FJC outcomes with RECAP sequences by case_id
- Output CSV columns:
  - case_id, district, filing_date, termination_date
  - event_sequence (JSON array of event types in order)
  - days_to_resolution
  - outcome (0 or 1)

## Tech Stack
- Python 3.11+
- pandas for data manipulation
- requests for API calls
- No ML libraries yet (just data prep)

## Constraints
- Start with 100-case sample to validate pipeline
- Respect RECAP rate limits (1 req/sec)
- Cache all API responses in data/cache/
- Log cases that fail to match (for debugging)

## Output
- data/sample_100.csv - initial validation set
- data/cache/ - raw API responses
- logs/unmatched_cases.log - cases without RECAP data

## Success Criteria
- Pipeline runs end-to-end without errors
- At least 50% match rate between FJC and RECAP
- Output CSV has all required columns with no nulls in core fields
- Event sequences contain 5+ events on average