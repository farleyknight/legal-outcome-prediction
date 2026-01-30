# Tasks

## Setup
- [x] Create project structure (src/, tests/, data/, logs/) → Directories exist and are importable as packages
- [x] Create requirements.txt with pandas, requests, pytest → `pip install -r requirements.txt` exits 0
- [x] Create pytest.ini with basic config → `pytest --collect-only` finds test directory

## FJC Data Processing
- [x] Implement FJC data downloader with caching → `python -c "from src.fjc_processor import download_fjc_data; download_fjc_data()"` creates data/fjc_civil.csv → Note: Uses CourtListener bulk data (bz2-compressed CSV)
- [x] Implement NOS filter for employment discrimination (442, 445, 446) → `pytest tests/test_fjc_processor.py::test_nos_filter` passes
- [x] Implement outcome mapping to binary labels → `pytest tests/test_fjc_processor.py::test_outcome_mapping` passes
- [x] Implement case ID extraction (district, docket_number) → `pytest tests/test_fjc_processor.py::test_case_id_extraction` passes

## RECAP API Client
- [x] Implement CourtListener API client with auth → `pytest tests/test_recap_client.py::test_api_connection` passes
- [x] Implement rate limiting (1 req/sec) → `pytest tests/test_recap_client.py::test_rate_limiting` passes
- [x] Implement response caching to data/cache/ → `pytest tests/test_recap_client.py::test_caching` passes
- [x] Implement docket lookup by case identifier → `pytest tests/test_recap_client.py::test_docket_lookup` passes

## Event Parsing
- [x] Define event type categories (COMPLAINT, ANSWER, MOTION_TO_DISMISS, etc.) → `pytest tests/test_event_parser.py::test_event_types_defined` passes
- [x] Implement docket description normalization → `pytest tests/test_event_parser.py::test_description_normalization` passes
- [x] Implement sequence extraction with dates → `pytest tests/test_event_parser.py::test_sequence_extraction` passes

## Pipeline Integration
- [x] Implement main pipeline orchestration → `pytest tests/test_pipeline.py::test_pipeline_runs` passes
- [x] Implement unmatched case logging → Running pipeline creates logs/unmatched_cases.log with entries
- [x] Implement output CSV generation → `python -m src.pipeline --sample 100` creates data/sample_100.csv → Note: Requires COURTLISTENER_API_TOKEN env var for API access

## Validation
- [x] Verify output schema (all required columns present) → `pytest tests/test_pipeline.py::test_output_schema` passes
- [x] Verify no nulls in core fields → `pytest tests/test_pipeline.py::test_no_nulls` passes
- [x] Verify average event sequence length >= 5 → `pytest tests/test_pipeline.py::test_sequence_length` passes
- [x] Run full pipeline on 100-case sample → `pytest` passes with all tests green → Note: 32 tests pass in ~3s

## Documentation
- [x] Add: README.md with project overview, setup instructions, and usage examples → README.md exists and includes: project description, installation steps, environment setup (.env), how to run tests, how to run pipeline

## Integration Tests (Live API)
- [x] Add: Integration test for API authentication with live token → `pytest tests/test_integration.py::test_live_api_auth -v` passes using real COURTLISTENER_API_TOKEN from .env
- [x] Add: Integration test for docket search with real case → `pytest tests/test_integration.py::test_live_docket_search -v` returns valid docket data from CourtListener
- [x] Add: Integration test for docket entries retrieval → `pytest tests/test_integration.py::test_live_docket_entries -v` returns real docket entries with descriptions → Note: Skips if API token lacks docket-entries permission (paid tier required)
- [x] Add: Integration test for end-to-end pipeline with small sample → `pytest tests/test_integration.py::test_live_pipeline_sample -v` processes 5 real cases successfully → Note: Test passes even if no RECAP matches found (older FJC cases may not be available)

## API Robustness (High Priority)
- [x] Fix: Add HTTP 429 rate limit response handling in `src/recap_client.py` → `pytest tests/test_recap_client.py::test_429_handling` passes with retry logic on rate limit responses
- [x] Add: Exponential backoff for failed API requests in `src/recap_client.py` → `pytest tests/test_recap_client.py::test_exponential_backoff` passes with configurable retry delays
- [x] Add: Configurable max retry attempts for transient failures → `pytest tests/test_recap_client.py::test_max_retries` passes respecting retry limits

## Match Rate Improvements (High Priority)
- [x] Fix: Add docket number normalization in `src/fjc_processor.py:139` to standardize formats → `pytest tests/test_fjc_processor.py::test_docket_normalization` passes with consistent formatting (e.g., "1:19-cv-01234" vs "19cv1234")
- [x] Add: Match rate logging and metrics to `src/pipeline.py` → Running pipeline logs match rate percentage and saves to `logs/match_metrics.json`

## Data Quality (Medium Priority)
- [ ] Fix: Handle multi-event docket descriptions in `src/event_parser.py:64-67` → `pytest tests/test_event_parser.py::test_multi_event_description` returns multiple event types from single description
- [ ] Add: Validation to reject cases with negative `days_to_resolution` in `src/pipeline.py` → `pytest tests/test_pipeline.py::test_negative_days_validation` passes excluding invalid date ranges

## Performance (Low Priority)
- [ ] Add: Cache negative API lookup results to avoid repeated failed searches → `pytest tests/test_recap_client.py::test_negative_cache` passes caching "not found" responses
- [ ] Add: Improve case ID parsing robustness in `src/pipeline.py:129` for edge case docket formats → `pytest tests/test_pipeline.py::test_complex_docket_parsing` passes with various docket number formats
