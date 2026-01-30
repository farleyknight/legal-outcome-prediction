# US Legal Outcome Prediction Dataset Builder

A Python pipeline that creates labeled datasets for predicting federal court case outcomes from docket entry sequences. It joins FJC Integrated Database (IDB) case outcomes with RECAP/CourtListener docket entries.

## Features

- Downloads and filters FJC IDB civil terminations data
- Matches cases to RECAP docket entries via CourtListener API
- Parses docket entries into normalized event sequences
- Outputs datasets suitable for sequence → outcome prediction models

## Requirements

- Python 3.11+
- CourtListener API token (free tier available)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd legal-outcome-prediction
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Environment Setup

The pipeline requires a CourtListener API token for accessing docket data.

### Getting an API Token

1. Create an account at https://www.courtlistener.com/register/
2. Go to https://www.courtlistener.com/profile/api/
3. Copy your API token

### Configuring the Token

Create a `.env` file in the project root:

```bash
COURTLISTENER_API_TOKEN=your_token_here
```

Or export directly in your shell:

```bash
export COURTLISTENER_API_TOKEN="your_token_here"
```

## Running Tests

Run the test suite with pytest:

```bash
pytest
```

Run with coverage report:

```bash
pytest --cov=src
```

## Usage

Run the pipeline to generate a dataset:

```bash
python -m src.pipeline
```

Specify a custom sample size:

```bash
python -m src.pipeline --sample 100
```

Output is written to `data/sample_100.csv` (or configured output path).

## Project Structure

```
legal-outcome-prediction/
├── src/
│   ├── __init__.py
│   ├── fjc_processor.py      # FJC data download and filtering
│   ├── recap_client.py       # CourtListener API client
│   ├── event_parser.py       # Docket entry normalization
│   └── pipeline.py           # Main orchestration
├── tests/
│   ├── __init__.py
│   ├── test_fjc_processor.py
│   ├── test_recap_client.py
│   ├── test_event_parser.py
│   └── test_pipeline.py
├── data/
│   ├── cache/                # API response cache
│   └── sample_100.csv        # Output dataset
├── logs/
│   └── unmatched_cases.log
├── specs/
│   ├── DATA_MODEL.md         # FJC fields, event types, output schema
│   └── API.md                # CourtListener API documentation
├── requirements.txt
└── pytest.ini
```

## Output Format

The pipeline generates a CSV with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `case_id` | string | Unique identifier: `{district}:{docket_number}` |
| `district` | string | District court code (e.g., "nysd") |
| `filing_date` | date | Case filing date (YYYY-MM-DD) |
| `termination_date` | date | Case termination date (YYYY-MM-DD) |
| `event_sequence` | JSON | Ordered array of event types |
| `days_to_resolution` | int | Days between filing and termination |
| `outcome` | int | 0 = defendant win/dismissed, 1 = plaintiff win |

## Key Decisions

- **Case filter**: Employment discrimination only (NOS 442, 445, 446)
- **Outcome mapping**: Binary - plaintiff_win (1) vs defendant_win_or_dismissed (0)
- **Rate limiting**: 1 request/second to CourtListener API
- **Caching**: All API responses cached in `data/cache/`

## References

- [FJC Integrated Database](https://www.fjc.gov/research/idb)
- [CourtListener API Documentation](https://www.courtlistener.com/help/api/rest/)
