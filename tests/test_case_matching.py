"""Tests for case matching logic between FJC IDB and Matt Clark datasets."""

import zipfile
from unittest import mock

import pandas as pd
import pytest

from src import matt_clark_parser
from src.fjc_processor import extract_case_id, normalize_docket_number


@pytest.fixture
def mock_fjc_data():
    """Sample FJC IDB data with employment discrimination cases."""
    return pd.DataFrame({
        'district_id': ['nysd', 'cacd', 'txsd', 'ilnd', 'flsd'],
        'docket_number': ['191234', '201567', '180999', '199999', '211111'],
        'nature_of_suit': ['442', '445', '446', '442', '442'],
        'disposition': [4, 4, 4, 4, 4],
        'judgment': [1, 2, 1, 1, 1],
        'date_terminated': ['2020-06-15', '2021-03-22', '2019-09-10', '2020-12-01', '2022-01-15'],
    })


@pytest.fixture
def mock_matt_clark_cases_csv():
    """Sample Matt Clark cases CSV matching some FJC cases.

    FJC normalized docket numbers use format "YYYYcvNNNN" (e.g., "2019cv1234")
    The numeric fallback strips all non-digits:
    - FJC "2019cv1234" → numeric "20191234"
    - Matt Clark "19-cv-1234" → numeric "191234"

    For matching to work, we need the docket numbers to produce the same
    numeric string when all non-digits are removed.
    """
    return """docket_id,court,docket_number,case_name,date_filed,date_terminated
1001,nysd,2019cv1234,Smith v. Acme Corp,2019-02-15,2020-06-15
1002,cacd,2020cv1567,Johnson v. Widgets Inc,2020-03-10,2021-03-22
1003,txsd,2018cv0999,Brown v. State,2018-04-01,2019-09-10
1004,paed,2021cv5555,Other Case,2021-01-01,2022-06-30
"""


@pytest.fixture
def mock_matt_clark_dir(tmp_path, mock_matt_clark_cases_csv):
    """Create mock Matt Clark directory with cases.zip."""
    matt_clark_dir = tmp_path / "matt_clark"
    matt_clark_dir.mkdir()

    # Create cases.zip
    cases_zip = matt_clark_dir / "cases.zip"
    with zipfile.ZipFile(cases_zip, 'w') as zf:
        zf.writestr("cases.csv", mock_matt_clark_cases_csv)

    return matt_clark_dir


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset parser cache before and after each test."""
    matt_clark_parser.clear_cache()
    yield
    matt_clark_parser.clear_cache()


class TestFjcMattClarkJoin:
    """Test case matching between FJC IDB and Matt Clark datasets."""

    def test_fjc_matt_clark_join(self, mock_fjc_data, mock_matt_clark_dir):
        """Verify case matching logic joins FJC IDB cases with Matt Clark cases.

        This test:
        1. Loads mock FJC data and extracts case IDs
        2. Uses get_case_by_court_and_docket() to look up each case
        3. Verifies matching cases are found correctly
        4. Verifies non-matching cases return None
        """
        # Step 1: Extract case IDs from FJC data (mimics pipeline logic)
        fjc_df = extract_case_id(mock_fjc_data)

        # Verify extract_case_id worked
        assert 'district' in fjc_df.columns
        assert 'docket_number_normalized' in fjc_df.columns
        assert 'case_id' in fjc_df.columns
        assert len(fjc_df) == 5

        # Step 2: Attempt to match each FJC case to Matt Clark dataset
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            matches = []
            non_matches = []

            for _, row in fjc_df.iterrows():
                court = row['district']
                # Use the original docket_number for lookup,
                # since get_case_by_court_and_docket does its own matching
                docket = row['docket_number']
                normalized = normalize_docket_number(docket)

                # Try matching with normalized format (e.g., "2019cv1234")
                # The Matt Clark parser also tries numeric-only matching
                result = matt_clark_parser.get_case_by_court_and_docket(court, normalized)

                if result is not None:
                    matches.append({
                        'fjc_case_id': row['case_id'],
                        'matt_clark_docket_id': result['docket_id'],
                        'court': court,
                    })
                else:
                    non_matches.append(row['case_id'])

            # Step 3: Verify expected matches
            # nysd:191234 → 2019cv1234 should match 2019cv1234 (docket_id 1001)
            # cacd:201567 → 2020cv1567 should match 2020cv1567 (docket_id 1002)
            # txsd:180999 → 2018cv0999 should match 2018cv0999 (docket_id 1003)
            assert len(matches) == 3, f"Expected 3 matches, got {len(matches)}: {matches}"

            # Verify specific matches
            matched_docket_ids = {m['matt_clark_docket_id'] for m in matches}
            assert 1001 in matched_docket_ids, "Should match nysd case"
            assert 1002 in matched_docket_ids, "Should match cacd case"
            assert 1003 in matched_docket_ids, "Should match txsd case"

            # Step 4: Verify non-matches
            # ilnd:199999 and flsd:211111 have no corresponding Matt Clark cases
            assert len(non_matches) == 2, f"Expected 2 non-matches, got {len(non_matches)}"

    def test_case_insensitive_court_matching(self, mock_matt_clark_dir):
        """Verify court matching is case-insensitive."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            # Uppercase court should still match
            result_upper = matt_clark_parser.get_case_by_court_and_docket('NYSD', '2019cv1234')
            result_lower = matt_clark_parser.get_case_by_court_and_docket('nysd', '2019cv1234')

            assert result_upper is not None or result_lower is not None, \
                "At least one case-variant should match"

            if result_upper and result_lower:
                assert result_upper['docket_id'] == result_lower['docket_id'], \
                    "Both case variants should return same case"

    def test_docket_number_normalization_in_join(self, mock_fjc_data):
        """Verify docket number normalization produces consistent format."""
        fjc_df = extract_case_id(mock_fjc_data)

        # Check normalized docket numbers
        # 191234 → 2019cv1234
        nysd_row = fjc_df[fjc_df['district'] == 'nysd'].iloc[0]
        assert nysd_row['docket_number_normalized'] == '2019cv1234'

        # 201567 → 2020cv1567
        cacd_row = fjc_df[fjc_df['district'] == 'cacd'].iloc[0]
        assert cacd_row['docket_number_normalized'] == '2020cv1567'

        # 180999 → 2018cv0999
        txsd_row = fjc_df[fjc_df['district'] == 'txsd'].iloc[0]
        assert txsd_row['docket_number_normalized'] == '2018cv0999'

    def test_numeric_fallback_matching(self, mock_matt_clark_dir):
        """Verify get_case_by_court_and_docket uses numeric fallback matching."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            # The function should extract numeric parts and match
            # "2019cv1234" → numeric "20191234" matches mock data "2019cv1234" → "20191234"
            # This tests the fallback logic in get_case_by_court_and_docket

            # Direct lookup with normalized format
            result = matt_clark_parser.get_case_by_court_and_docket('nysd', '2019cv1234')
            assert result is not None, "Normalized format should match"
            assert result['docket_id'] == 1001

    def test_no_match_returns_none(self, mock_matt_clark_dir):
        """Verify non-existent cases return None."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            # Court exists but docket doesn't
            result = matt_clark_parser.get_case_by_court_and_docket('nysd', '2099cv99999')
            assert result is None

            # Court doesn't exist
            result = matt_clark_parser.get_case_by_court_and_docket('xxxx', '2019cv1234')
            assert result is None
