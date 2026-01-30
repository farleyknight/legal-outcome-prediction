# Data Model Specification

## FJC IDB Civil Terminations Schema

### Source
- URL: https://www.fjc.gov/research/idb
- File: `cv_1988-present.csv` (or similar civil terminations file)

### Relevant Fields
| Field | Description | Example |
|-------|-------------|---------|
| `CIRCUIT` | Circuit number | 2 |
| `DISTRICT` | District code | 36 (SDNY) |
| `OFFICE` | Office code within district | 1 |
| `DESSION` | Docket number (year + sequence) | 2019-1234 |
| `NOS` | Nature of suit code | 442 |
| `FILEDATE` | Filing date (YYYYMMDD) | 20190315 |
| `TERMDATE` | Termination date (YYYYMMDD) | 20210622 |
| `DIESSION` | Disposition code | 4 |
| `JUDGMENT` | Judgment for whom | 1 (plaintiff) |
| `PROCPROG` | Procedural progress at termination | 6 |

### Nature of Suit Filter
- **442**: Civil Rights - Employment
- **445**: Americans with Disabilities - Employment
- **446**: Americans with Disabilities - Other (employment-related subset)

### Disposition Code Mapping
| Code | Meaning | Outcome |
|------|---------|---------|
| 0 | Transfer to another district | EXCLUDE |
| 1 | Remand to state court | EXCLUDE |
| 2 | Dismissal - lack of jurisdiction | defendant_win |
| 3 | Dismissal - want of prosecution | defendant_win |
| 4 | Judgment on default | Use JUDGMENT field |
| 5 | Judgment on consent | Use JUDGMENT field |
| 6 | Judgment on motion before trial | Use JUDGMENT field |
| 7 | Judgment on jury verdict | Use JUDGMENT field |
| 8 | Judgment on directed verdict | Use JUDGMENT field |
| 9 | Judgment on court trial | Use JUDGMENT field |
| 10 | Multi-district litigation transfer | EXCLUDE |
| 11 | Remand to US agency | EXCLUDE |
| 12 | Voluntary dismissal | defendant_win |
| 13 | Settled | EXCLUDE (unclear winner) |
| 14 | Other | EXCLUDE |
| 15 | Statistical closing | EXCLUDE |
| 18 | Award of arbitrator | Use JUDGMENT field |

### Judgment Field Mapping
| Code | Meaning | Outcome |
|------|---------|---------|
| 1 | Plaintiff | plaintiff_win (1) |
| 2 | Defendant | defendant_win (0) |
| 3 | Both | EXCLUDE |
| 4 | Unknown | EXCLUDE |
| 0/blank | Not applicable | Use disposition only |

---

## Event Type Categories

Normalized categories for docket entry descriptions:

| Event Type | Pattern Matches |
|------------|-----------------|
| `COMPLAINT` | complaint, petition |
| `ANSWER` | answer, response to complaint |
| `MOTION_TO_DISMISS` | motion to dismiss, 12(b) |
| `MOTION_FOR_SUMMARY_JUDGMENT` | summary judgment, MSJ |
| `MOTION_OTHER` | motion (fallback) |
| `ORDER` | order, ruling |
| `DISCOVERY` | discovery, interrogator, deposition, subpoena, request for production |
| `SCHEDULING` | scheduling, case management, CMO |
| `SETTLEMENT_CONFERENCE` | settlement, mediation, ADR |
| `PRETRIAL` | pretrial, trial setting |
| `TRIAL` | trial, jury, bench trial |
| `JUDGMENT` | judgment, verdict, final order |
| `APPEAL` | appeal, notice of appeal |
| `OTHER` | fallback for unmatched entries |

---

## Output Dataset Schema

### File: `data/sample_100.csv`

| Column | Type | Description | Nullable |
|--------|------|-------------|----------|
| `case_id` | string | Unique identifier: `{district}:{docket_number}` | No |
| `district` | string | District court code (e.g., "nysd") | No |
| `filing_date` | date | Case filing date (YYYY-MM-DD) | No |
| `termination_date` | date | Case termination date (YYYY-MM-DD) | No |
| `event_sequence` | JSON | Ordered array of event types | No |
| `days_to_resolution` | int | Days between filing and termination | No |
| `outcome` | int | 0 = defendant win/dismissed, 1 = plaintiff win | No |

### Example Row
```json
{
  "case_id": "nysd:2019cv01234",
  "district": "nysd",
  "filing_date": "2019-03-15",
  "termination_date": "2021-06-22",
  "event_sequence": "[\"COMPLAINT\", \"ANSWER\", \"DISCOVERY\", \"MOTION_FOR_SUMMARY_JUDGMENT\", \"ORDER\", \"JUDGMENT\"]",
  "days_to_resolution": 830,
  "outcome": 0
}
```

---

## District Code Mapping

FJC uses numeric district codes. CourtListener uses string abbreviations.

| FJC Code | District | CourtListener Code |
|----------|----------|-------------------|
| 36 | Southern District of New York | nysd |
| 37 | Eastern District of New York | nyed |
| 38 | Northern District of New York | nynd |
| 39 | Western District of New York | nywd |
| 21 | Northern District of California | cand |
| 22 | Eastern District of California | caed |
| 23 | Central District of California | cacd |
| 24 | Southern District of California | casd |

(Full mapping needed in implementation - FJC provides reference tables)
