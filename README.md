# US Legal Outcome Prediction Dataset Builder

A Python pipeline that creates labeled datasets for predicting federal court case outcomes from docket entry sequences. It joins FJC Integrated Database (IDB) case outcomes with docket entries from the Matt Clark Federal Court Dockets dataset.

## Features

- Downloads and filters FJC IDB civil terminations data
- Matches cases to docket entries from Matt Clark Federal Court Dockets dataset (350M+ entries, 13M+ cases)
- Falls back to CourtListener API for cases not in Matt Clark dataset (optional)
- Parses docket entries into normalized event sequences
- Outputs datasets suitable for sequence → outcome prediction models

## Requirements

- Python 3.11+
- ~10GB disk space for Matt Clark dataset files
- CourtListener API token (optional, only needed for fallback lookups)

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

## Data Setup

The pipeline uses the Matt Clark Federal Court Dockets dataset as its primary data source. This dataset is freely available from Internet Archive and contains 350M+ docket entries from 13M+ federal cases (2013-present).

### Download the Dataset

Download the dataset files:

```bash
python -m src.matt_clark_downloader
```

Available options:

```bash
# Preview what would be downloaded (recommended first step)
python -m src.matt_clark_downloader --dry-run

# Download only cases.zip (case metadata, ~600MB)
python -m src.matt_clark_downloader --cases-only

# Download only docket entries for specific years
python -m src.matt_clark_downloader --entries-only --years 2022 2023

# Download everything (cases + all entry years)
python -m src.matt_clark_downloader
```

Files are downloaded to `data/matt_clark/`. The cases.zip file is required; entry files are optional and can be downloaded incrementally.

**Source**: [Matt Clark Federal Court Dockets on Internet Archive](https://archive.org/details/federal-court-dockets)

## Environment Setup (Optional)

The CourtListener API is only needed as a fallback for cases not found in the Matt Clark dataset. Most users won't need this.

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

1. Download the Matt Clark dataset (see Data Setup above)

2. Run the pipeline to generate a dataset:

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
│   ├── fjc_processor.py          # FJC data download and filtering
│   ├── matt_clark_downloader.py  # Matt Clark dataset download tool
│   ├── matt_clark_parser.py      # Matt Clark CSV parsing
│   ├── recap_client.py           # CourtListener API client (fallback)
│   ├── event_parser.py           # Docket entry normalization
│   └── pipeline.py               # Main orchestration
├── tests/
│   ├── __init__.py
│   ├── test_fjc_processor.py
│   ├── test_matt_clark_parser.py # Matt Clark parser tests
│   ├── test_case_matching.py     # FJC to Matt Clark matching tests
│   ├── test_recap_client.py
│   ├── test_event_parser.py
│   └── test_pipeline.py
├── data/
│   ├── matt_clark/               # Matt Clark dataset files
│   │   ├── cases.zip             # Case metadata
│   │   └── {year}entries.zip     # Docket entries by year
│   ├── cache/                    # API response cache
│   └── sample_100.csv            # Output dataset
├── logs/
│   └── unmatched_cases.log
├── specs/
│   ├── DATA_MODEL.md             # FJC fields, event types, output schema
│   └── API.md                    # CourtListener API documentation
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

- **Primary data source**: Matt Clark Federal Court Dockets dataset (local, no API required)
- **Fallback**: CourtListener API (optional, requires COURTLISTENER_API_TOKEN)
- **Case filter**: Employment discrimination only (NOS 442, 445, 446)
- **Outcome mapping**: Binary - plaintiff_win (1) vs defendant_win_or_dismissed (0)
- **Rate limiting**: 1 request/second to CourtListener API (when used as fallback)
- **Caching**: All API responses cached in `data/cache/`

## References

- [Matt Clark Federal Court Dockets (Internet Archive)](https://archive.org/details/federal-court-dockets)
- [FJC Integrated Database](https://www.fjc.gov/research/idb)
- [CourtListener API Documentation](https://www.courtlistener.com/help/api/rest/)
