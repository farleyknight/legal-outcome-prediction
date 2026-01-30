# US Legal Outcome Prediction Dataset Builder

## What We're Building
A Python pipeline that joins FJC Integrated Database (IDB) case outcomes with RECAP/CourtListener docket entries to create a labeled dataset for predicting federal court case outcomes from docket entry sequences.

The pipeline will:
1. Download and filter FJC IDB civil terminations data
2. Match cases to RECAP docket entries via CourtListener API
3. Parse docket entries into normalized event sequences
4. Output a dataset suitable for sequence → outcome prediction models

## Tech Stack
- Python 3.11+
- pandas (data manipulation)
- requests (API calls)
- Standard library: json, logging, pathlib, time

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
├── requirements.txt
└── pytest.ini
```

## Commands
- Install: `pip install -r requirements.txt`
- Test: `pytest`
- Run: `python -m src.pipeline`

## Key Decisions
- **Case filter**: Employment discrimination only (NOS 442, 445, 446)
- **Outcome mapping**: Binary - plaintiff_win (1) vs defendant_win_or_dismissed (0)
- **Sample size**: 100 cases for initial validation
- **Rate limiting**: 1 request/second to RECAP API
- **Caching**: All API responses cached in data/cache/

## Success Criteria
- Pipeline runs end-to-end without errors
- At least 50% match rate between FJC and RECAP
- Output CSV has all required columns with no nulls in core fields
- Event sequences contain 5+ events on average

## References
- specs/DATA_MODEL.md - FJC fields, event types, output schema
- specs/API.md - CourtListener API integration details
