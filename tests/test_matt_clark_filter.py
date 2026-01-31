"""Tests for Matt Clark dataset filter."""

import tempfile
import zipfile
from io import StringIO
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from src import matt_clark_filter
from src import matt_clark_parser


@pytest.fixture
def mock_fjc_csv(tmp_path):
    """Create mock FJC CSV file."""
    fjc_csv = tmp_path / "fjc_civil.csv"
    # district_id maps to court, docket_number is numeric FJC format
    # FJC uses 8-digit format: YYYY + sequence (e.g., 20191234 -> 2019cv1234)
    # NOS 442, 445, 446 are employment discrimination (nature_of_suit is string in FJC data)
    content = '''district_id,docket_number,nature_of_suit,disposition,judgment
nysd,201901234,"442",4,1
cacd,202001234,"445",3,0
ilnd,202101234,"446",4,2
txsd,202201234,"440",4,1
'''
    fjc_csv.write_text(content)
    return fjc_csv


@pytest.fixture
def mock_cases_csv():
    """Sample cases CSV content matching some FJC cases."""
    # FJC docket 1901234 normalizes to 2019cv01234, so Matt Clark should have matching format
    return """docket_id,court,docket_number,case_name,date_filed,date_terminated
1001,nysd,1:19-cv-01234,Smith v. Jones Inc.,2019-02-15,2020-08-30
1002,cacd,2:20-cv-01234,Doe v. Acme Corp.,2020-05-10,2021-03-22
1003,ilnd,1:21-cv-01234,Johnson v. State,2021-11-01,2022-06-15
1004,txsd,1:22-cv-01234,Other Case,2022-01-01,2022-12-31
1005,azd,1:23-cv-05555,Unrelated Case,2023-01-01,2023-12-31
"""


@pytest.fixture
def mock_entries_csv_2019():
    """Sample entries CSV for 2019."""
    return """docket_id,entry_number,date_filed,description
1001,1,2019-02-15,Complaint filed
1001,2,2019-02-20,Summons issued
1001,3,2019-03-15,Answer filed by defendant
1005,1,2019-05-01,Some other entry
"""


@pytest.fixture
def mock_entries_csv_2020():
    """Sample entries CSV for 2020."""
    return """docket_id,entry_number,date_filed,description
1002,1,2020-05-10,Initial complaint
1002,2,2020-06-01,Motion to dismiss
1005,2,2020-07-01,Another entry for unrelated case
"""


@pytest.fixture
def mock_matt_clark_dir(tmp_path, mock_cases_csv, mock_entries_csv_2019, mock_entries_csv_2020):
    """Create mock Matt Clark directory with ZIP files."""
    matt_clark_dir = tmp_path / "matt_clark"
    matt_clark_dir.mkdir()

    # Create cases.zip
    cases_zip = matt_clark_dir / "cases.zip"
    with zipfile.ZipFile(cases_zip, 'w') as zf:
        zf.writestr("cases.csv", mock_cases_csv)

    # Create 2019entries.zip
    entries_2019 = matt_clark_dir / "2019entries.zip"
    with zipfile.ZipFile(entries_2019, 'w') as zf:
        zf.writestr("2019entries.csv", mock_entries_csv_2019)

    # Create 2020entries.zip
    entries_2020 = matt_clark_dir / "2020entries.zip"
    with zipfile.ZipFile(entries_2020, 'w') as zf:
        zf.writestr("2020entries.csv", mock_entries_csv_2020)

    return matt_clark_dir


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset parser cache before and after each test."""
    matt_clark_parser.clear_cache()
    yield
    matt_clark_parser.clear_cache()


class TestModuleImports:
    """Test that module imports correctly."""

    def test_module_imports(self):
        """Module should import without errors."""
        assert matt_clark_filter is not None

    def test_exports_load_fjc_employment_cases(self):
        """Module should export load_fjc_employment_cases."""
        assert hasattr(matt_clark_filter, 'load_fjc_employment_cases')
        assert callable(matt_clark_filter.load_fjc_employment_cases)

    def test_exports_filter_cases(self):
        """Module should export filter_cases."""
        assert hasattr(matt_clark_filter, 'filter_cases')
        assert callable(matt_clark_filter.filter_cases)

    def test_exports_filter_entries(self):
        """Module should export filter_entries."""
        assert hasattr(matt_clark_filter, 'filter_entries')
        assert callable(matt_clark_filter.filter_entries)

    def test_exports_build_match_lookup(self):
        """Module should export build_match_lookup."""
        assert hasattr(matt_clark_filter, 'build_match_lookup')
        assert callable(matt_clark_filter.build_match_lookup)


class TestBuildMatchLookup:
    """Test build_match_lookup function."""

    def test_builds_lookup_set(self):
        """Should build set of (court, docket) tuples."""
        df = pd.DataFrame({
            'district': ['nysd', 'cacd'],
            'docket_number_normalized': ['2019cv1234', '2020cv5678']
        })

        lookup = matt_clark_filter.build_match_lookup(df)

        assert isinstance(lookup, set)
        assert len(lookup) == 2
        assert ('nysd', '2019cv1234') in lookup
        assert ('cacd', '2020cv5678') in lookup

    def test_handles_case_insensitive(self):
        """Should normalize to lowercase."""
        df = pd.DataFrame({
            'district': ['NYSD', 'CaCD'],
            'docket_number_normalized': ['2019CV1234', '2020cv5678']
        })

        lookup = matt_clark_filter.build_match_lookup(df)

        assert ('nysd', '2019cv1234') in lookup
        assert ('cacd', '2020cv5678') in lookup

    def test_handles_empty_dataframe(self):
        """Should handle empty DataFrame."""
        df = pd.DataFrame({
            'district': [],
            'docket_number_normalized': []
        })

        lookup = matt_clark_filter.build_match_lookup(df)

        assert lookup == set()


class TestNormalizeMattClarkDocket:
    """Test normalize_matt_clark_docket function."""

    def test_normalizes_court_listener_format(self):
        """Should normalize CourtListener format."""
        result = matt_clark_filter.normalize_matt_clark_docket("1:19-cv-01234")
        assert result == "2019cv01234"

    def test_normalizes_to_lowercase(self):
        """Should return lowercase."""
        result = matt_clark_filter.normalize_matt_clark_docket("1:19-CV-01234")
        assert result == "2019cv01234"


class TestFilterCases:
    """Test filter_cases function."""

    def test_filters_to_matching_cases(self, mock_matt_clark_dir):
        """Should filter to only matching cases."""
        # FJC 201901234 -> 2019cv01234; Matt Clark 1:19-cv-01234 -> 2019cv01234
        match_lookup = {
            ('nysd', '2019cv01234'),
            ('cacd', '2020cv01234'),
        }

        with mock.patch.object(matt_clark_filter, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
                matched_ids = matt_clark_filter.filter_cases(match_lookup, dry_run=True)

        # Should match docket_ids 1001 (nysd) and 1002 (cacd)
        assert 1001 in matched_ids
        assert 1002 in matched_ids
        # Should not match unrelated case
        assert 1005 not in matched_ids

    def test_writes_filtered_file_when_not_dry_run(self, mock_matt_clark_dir):
        """Should write filtered ZIP when not dry run."""
        match_lookup = {('nysd', '2019cv01234')}

        with mock.patch.object(matt_clark_filter, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
                matt_clark_filter.filter_cases(match_lookup, dry_run=False)

        output_path = mock_matt_clark_dir / "cases_filtered.zip"
        assert output_path.exists()

        # Verify content
        with zipfile.ZipFile(output_path, 'r') as zf:
            with zf.open('cases.csv') as f:
                df = pd.read_csv(f)
                assert len(df) == 1
                assert df.iloc[0]['docket_id'] == 1001

    def test_returns_set_of_docket_ids(self, mock_matt_clark_dir):
        """Should return set of matched docket_ids."""
        match_lookup = {('nysd', '2019cv01234')}

        with mock.patch.object(matt_clark_filter, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
                result = matt_clark_filter.filter_cases(match_lookup, dry_run=True)

        assert isinstance(result, set)
        assert all(isinstance(id_, int) for id_ in result)


class TestFilterEntries:
    """Test filter_entries function."""

    def test_filters_entries_to_matched_docket_ids(self, mock_matt_clark_dir):
        """Should filter entries to only matched docket_ids."""
        matched_docket_ids = {1001}

        with mock.patch.object(matt_clark_filter, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            count = matt_clark_filter.filter_entries(2019, matched_docket_ids, dry_run=True)

        # Entries for docket_id 1001 only (3 entries)
        assert count == 3

    def test_writes_filtered_entries_file(self, mock_matt_clark_dir):
        """Should write filtered entries ZIP when not dry run."""
        matched_docket_ids = {1001}

        with mock.patch.object(matt_clark_filter, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            matt_clark_filter.filter_entries(2019, matched_docket_ids, dry_run=False)

        output_path = mock_matt_clark_dir / "2019entries_filtered.zip"
        assert output_path.exists()

        # Verify content
        with zipfile.ZipFile(output_path, 'r') as zf:
            with zf.open('2019entries.csv') as f:
                df = pd.read_csv(f)
                assert len(df) == 3
                assert all(df['docket_id'] == 1001)

    def test_returns_zero_for_missing_file(self, tmp_path):
        """Should return 0 if entries file not found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with mock.patch.object(matt_clark_filter, 'MATT_CLARK_DIR', empty_dir):
            count = matt_clark_filter.filter_entries(2019, {1001}, dry_run=True)

        assert count == 0

    def test_handles_multiple_years(self, mock_matt_clark_dir):
        """Should filter different year files independently."""
        matched_docket_ids = {1001, 1002}

        with mock.patch.object(matt_clark_filter, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            count_2019 = matt_clark_filter.filter_entries(2019, matched_docket_ids, dry_run=True)
            count_2020 = matt_clark_filter.filter_entries(2020, matched_docket_ids, dry_run=True)

        # 2019 has 3 entries for 1001
        assert count_2019 == 3
        # 2020 has 2 entries for 1002
        assert count_2020 == 2


class TestWriteFilteredCases:
    """Test write_filtered_cases function."""

    def test_writes_valid_zip(self, tmp_path):
        """Should write a valid ZIP file."""
        df = pd.DataFrame({
            'docket_id': [1001, 1002],
            'court': ['nysd', 'cacd'],
            'docket_number': ['1:19-cv-01234', '2:20-cv-05678'],
        })
        output_path = tmp_path / "cases_filtered.zip"

        matt_clark_filter.write_filtered_cases(df, output_path)

        assert output_path.exists()
        with zipfile.ZipFile(output_path, 'r') as zf:
            assert 'cases.csv' in zf.namelist()

    def test_drops_helper_columns(self, tmp_path):
        """Should drop docket_normalized and court_lower columns."""
        df = pd.DataFrame({
            'docket_id': [1001],
            'court': ['nysd'],
            'docket_normalized': ['2019cv1234'],
            'court_lower': ['nysd'],
        })
        output_path = tmp_path / "cases_filtered.zip"

        matt_clark_filter.write_filtered_cases(df, output_path)

        with zipfile.ZipFile(output_path, 'r') as zf:
            with zf.open('cases.csv') as f:
                result_df = pd.read_csv(f)
                assert 'docket_normalized' not in result_df.columns
                assert 'court_lower' not in result_df.columns


class TestWriteFilteredEntries:
    """Test write_filtered_entries function."""

    def test_writes_valid_zip(self, tmp_path):
        """Should write a valid ZIP file."""
        entries = [
            {'docket_id': 1001, 'entry_number': 1, 'description': 'Test entry'},
            {'docket_id': 1001, 'entry_number': 2, 'description': 'Another entry'},
        ]
        output_path = tmp_path / "2019entries_filtered.zip"

        matt_clark_filter.write_filtered_entries(entries, output_path, 2019)

        assert output_path.exists()
        with zipfile.ZipFile(output_path, 'r') as zf:
            assert '2019entries.csv' in zf.namelist()

    def test_handles_empty_entries(self, tmp_path):
        """Should not create file for empty entries list."""
        output_path = tmp_path / "2019entries_filtered.zip"

        matt_clark_filter.write_filtered_entries([], output_path, 2019)

        assert not output_path.exists()


class TestParseYears:
    """Test parse_years function."""

    def test_parses_single_year(self):
        """Should parse single year."""
        assert matt_clark_filter.parse_years("2020") == [2020]

    def test_parses_comma_separated(self):
        """Should parse comma-separated years."""
        result = matt_clark_filter.parse_years("2020,2021,2022")
        assert result == [2020, 2021, 2022]

    def test_parses_range(self):
        """Should parse year range."""
        result = matt_clark_filter.parse_years("2020-2023")
        assert result == [2020, 2021, 2022, 2023]

    def test_handles_spaces(self):
        """Should handle spaces in comma-separated list."""
        result = matt_clark_filter.parse_years("2020, 2021, 2022")
        assert result == [2020, 2021, 2022]


class TestLoadFjcEmploymentCases:
    """Test load_fjc_employment_cases function."""

    def test_returns_dataframe_with_required_columns(self, mock_fjc_csv):
        """Should return DataFrame with district and docket columns."""
        with mock.patch.object(matt_clark_filter, 'download_fjc_data', return_value=mock_fjc_csv):
            df = matt_clark_filter.load_fjc_employment_cases()

        assert isinstance(df, pd.DataFrame)
        assert 'district' in df.columns
        assert 'docket_number_normalized' in df.columns
        assert 'case_id' in df.columns

    def test_filters_to_employment_codes_only(self, mock_fjc_csv):
        """Should only include NOS codes 442, 445, 446."""
        with mock.patch.object(matt_clark_filter, 'download_fjc_data', return_value=mock_fjc_csv):
            df = matt_clark_filter.load_fjc_employment_cases()

        # Original data has 4 rows, but one is NOS 440 (excluded)
        assert len(df) == 3

    def test_drops_duplicates(self, mock_fjc_csv):
        """Should drop duplicate rows."""
        with mock.patch.object(matt_clark_filter, 'download_fjc_data', return_value=mock_fjc_csv):
            df = matt_clark_filter.load_fjc_employment_cases()

        # Each case_id should appear once
        assert df['case_id'].is_unique
