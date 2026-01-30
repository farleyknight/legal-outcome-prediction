# Tasks

## Setup
- [x] Create project structure (src/, tests/, data/, logs/) → Directories exist and are importable as packages
- [x] Create requirements.txt with pandas, requests, pytest → `pip install -r requirements.txt` exits 0
- [x] Create pytest.ini with basic config → `pytest --collect-only` finds test directory

## FJC Data Processing
- [x] Implement FJC data downloader with caching → `python -c "from src.fjc_processor import download_fjc_data; download_fjc_data()"` creates data/fjc_civil.csv → Note: Uses CourtListener bulk data (bz2-compressed CSV)
- [x] Implement NOS filter for employment discrimination (442, 445, 446) → `pytest tests/test_fjc_processor.py::test_nos_filter` passes
- [x] Implement outcome mapping to binary labels → `pytest tests/test_fjc_processor.py::test_outcome_mapping` passes
- [ ] Implement case ID extraction (district, docket_number) → `pytest tests/test_fjc_processor.py::test_case_id_extraction` passes

## RECAP API Client
- [ ] Implement CourtListener API client with auth → `pytest tests/test_recap_client.py::test_api_connection` passes
- [ ] Implement rate limiting (1 req/sec) → `pytest tests/test_recap_client.py::test_rate_limiting` passes
- [ ] Implement response caching to data/cache/ → `pytest tests/test_recap_client.py::test_caching` passes
- [ ] Implement docket lookup by case identifier → `pytest tests/test_recap_client.py::test_docket_lookup` passes

## Event Parsing
- [ ] Define event type categories (COMPLAINT, ANSWER, MOTION_TO_DISMISS, etc.) → `pytest tests/test_event_parser.py::test_event_types_defined` passes
- [ ] Implement docket description normalization → `pytest tests/test_event_parser.py::test_description_normalization` passes
- [ ] Implement sequence extraction with dates → `pytest tests/test_event_parser.py::test_sequence_extraction` passes

## Pipeline Integration
- [ ] Implement main pipeline orchestration → `pytest tests/test_pipeline.py::test_pipeline_runs` passes
- [ ] Implement unmatched case logging → Running pipeline creates logs/unmatched_cases.log with entries
- [ ] Implement output CSV generation → `python -m src.pipeline --sample 100` creates data/sample_100.csv

## Validation
- [ ] Verify output schema (all required columns present) → `pytest tests/test_pipeline.py::test_output_schema` passes
- [ ] Verify no nulls in core fields → `pytest tests/test_pipeline.py::test_no_nulls` passes
- [ ] Verify average event sequence length >= 5 → `pytest tests/test_pipeline.py::test_sequence_length` passes
- [ ] Run full pipeline on 100-case sample → `pytest` passes with all tests green
