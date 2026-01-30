"""Tests for Matt Clark dataset parser."""

import io
import tempfile
import zipfile
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from src import matt_clark_parser


@pytest.fixture
def mock_cases_csv():
    """Sample cases CSV content."""
    return """docket_id,court,docket_number,case_name,date_filed,date_terminated
1001,nysd,1:19-cv-01234,Smith v. Jones Inc.,2019-02-15,2020-08-30
1002,cacd,2:20-cv-05678,Doe v. Acme Corp.,2020-05-10,2021-03-22
1003,nysd,1:18-cv-09999,Johnson v. State,2018-11-01,2019-06-15
"""


@pytest.fixture
def mock_entries_csv():
    """Sample entries CSV content for 2019."""
    return """docket_id,entry_number,date_filed,description
1001,1,2019-02-15,Complaint filed
1001,2,2019-02-20,Summons issued
1001,3,2019-03-15,Answer filed by defendant
1003,1,2018-11-01,Initial filing
1003,2,2018-11-15,Motion to dismiss
"""


@pytest.fixture
def mock_matt_clark_dir(tmp_path, mock_cases_csv, mock_entries_csv):
    """Create mock Matt Clark directory with ZIP files."""
    matt_clark_dir = tmp_path / "matt_clark"
    matt_clark_dir.mkdir()

    # Create cases.zip
    cases_zip = matt_clark_dir / "cases.zip"
    with zipfile.ZipFile(cases_zip, 'w') as zf:
        zf.writestr("cases.csv", mock_cases_csv)

    # Create 2019entries.zip
    entries_zip = matt_clark_dir / "2019entries.zip"
    with zipfile.ZipFile(entries_zip, 'w') as zf:
        zf.writestr("2019entries.csv", mock_entries_csv)

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
        assert matt_clark_parser is not None

    def test_exports_load_cases_df(self):
        """Module should export load_cases_df."""
        assert hasattr(matt_clark_parser, 'load_cases_df')
        assert callable(matt_clark_parser.load_cases_df)

    def test_exports_load_entries_df(self):
        """Module should export load_entries_df."""
        assert hasattr(matt_clark_parser, 'load_entries_df')
        assert callable(matt_clark_parser.load_entries_df)

    def test_exports_get_case_by_court_and_docket(self):
        """Module should export get_case_by_court_and_docket."""
        assert hasattr(matt_clark_parser, 'get_case_by_court_and_docket')
        assert callable(matt_clark_parser.get_case_by_court_and_docket)

    def test_exports_get_entries_for_case(self):
        """Module should export get_entries_for_case."""
        assert hasattr(matt_clark_parser, 'get_entries_for_case')
        assert callable(matt_clark_parser.get_entries_for_case)


class TestLoadCasesDf:
    """Test load_cases_df function."""

    def test_load_cases_df_parses_csv(self, mock_matt_clark_dir):
        """load_cases_df should parse cases.csv from ZIP."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            df = matt_clark_parser.load_cases_df()

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 3

    def test_load_cases_df_has_expected_columns(self, mock_matt_clark_dir):
        """Parsed DataFrame should have expected columns."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            df = matt_clark_parser.load_cases_df()

            expected_columns = ['docket_id', 'court', 'docket_number', 'case_name']
            for col in expected_columns:
                assert col in df.columns, f"Missing column: {col}"

    def test_load_cases_df_caches_result(self, mock_matt_clark_dir):
        """Subsequent calls should return cached DataFrame."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            df1 = matt_clark_parser.load_cases_df()
            df2 = matt_clark_parser.load_cases_df()

            # Should be the same object (cached)
            assert df1 is df2

    def test_load_cases_df_raises_file_not_found(self, tmp_path):
        """Should raise FileNotFoundError if cases.zip missing."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', empty_dir):
            with pytest.raises(FileNotFoundError):
                matt_clark_parser.load_cases_df()


class TestLoadEntriesDf:
    """Test load_entries_df function."""

    def test_load_entries_df_parses_csv(self, mock_matt_clark_dir):
        """load_entries_df should parse entries CSV from ZIP."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            df = matt_clark_parser.load_entries_df(2019)

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 5

    def test_load_entries_df_has_expected_columns(self, mock_matt_clark_dir):
        """Parsed DataFrame should have expected columns."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            df = matt_clark_parser.load_entries_df(2019)

            expected_columns = ['docket_id', 'entry_number', 'date_filed', 'description']
            for col in expected_columns:
                assert col in df.columns, f"Missing column: {col}"

    def test_load_entries_df_caches_result(self, mock_matt_clark_dir):
        """Subsequent calls should return cached DataFrame."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            df1 = matt_clark_parser.load_entries_df(2019)
            df2 = matt_clark_parser.load_entries_df(2019)

            # Should be the same object (cached)
            assert df1 is df2

    def test_load_entries_df_raises_file_not_found(self, tmp_path):
        """Should raise FileNotFoundError if entries ZIP missing."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', empty_dir):
            with pytest.raises(FileNotFoundError):
                matt_clark_parser.load_entries_df(2019)


class TestGetCaseByCourtAndDocket:
    """Test get_case_by_court_and_docket function."""

    def test_returns_dict_when_found(self, mock_matt_clark_dir):
        """Should return dict when case is found."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            result = matt_clark_parser.get_case_by_court_and_docket('nysd', '1:19-cv-01234')

            assert isinstance(result, dict)
            assert result['docket_id'] == 1001
            assert result['court'] == 'nysd'

    def test_returns_none_when_not_found(self, mock_matt_clark_dir):
        """Should return None when case is not found."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            result = matt_clark_parser.get_case_by_court_and_docket('nysd', '1:99-cv-99999')

            assert result is None

    def test_case_insensitive_court_lookup(self, mock_matt_clark_dir):
        """Should match court regardless of case."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            result = matt_clark_parser.get_case_by_court_and_docket('NYSD', '1:19-cv-01234')

            assert result is not None
            assert result['docket_id'] == 1001

    def test_result_has_expected_keys(self, mock_matt_clark_dir):
        """Returned dict should have expected keys."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            result = matt_clark_parser.get_case_by_court_and_docket('nysd', '1:19-cv-01234')

            expected_keys = ['docket_id', 'court', 'docket_number', 'case_name']
            for key in expected_keys:
                assert key in result, f"Missing key: {key}"


class TestGetEntriesForCase:
    """Test get_entries_for_case function."""

    def test_returns_list_of_dicts(self, mock_matt_clark_dir):
        """Should return list of dicts."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            result = matt_clark_parser.get_entries_for_case(1001, year=2019)

            assert isinstance(result, list)
            assert len(result) == 3
            assert all(isinstance(entry, dict) for entry in result)

    def test_returns_empty_list_when_not_found(self, mock_matt_clark_dir):
        """Should return empty list when no entries found."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            result = matt_clark_parser.get_entries_for_case(9999, year=2019)

            assert result == []

    def test_entries_have_expected_keys(self, mock_matt_clark_dir):
        """Returned entries should have expected keys."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            result = matt_clark_parser.get_entries_for_case(1001, year=2019)

            expected_keys = ['docket_id', 'entry_number', 'date_filed', 'description']
            for entry in result:
                for key in expected_keys:
                    assert key in entry, f"Missing key: {key}"

    def test_returns_correct_entries_for_case(self, mock_matt_clark_dir):
        """Should return only entries for the specified case."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            result = matt_clark_parser.get_entries_for_case(1001, year=2019)

            # All entries should be for docket_id 1001
            assert all(entry['docket_id'] == 1001 for entry in result)

    def test_handles_string_case_id(self, mock_matt_clark_dir):
        """Should handle case_id passed as string."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            result = matt_clark_parser.get_entries_for_case('1001', year=2019)

            assert isinstance(result, list)
            # May or may not find entries depending on DataFrame dtype


class TestClearCache:
    """Test clear_cache function."""

    def test_clear_cache_resets_cases(self, mock_matt_clark_dir):
        """clear_cache should reset cases DataFrame cache."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            df1 = matt_clark_parser.load_cases_df()
            matt_clark_parser.clear_cache()
            df2 = matt_clark_parser.load_cases_df()

            # After clearing, should be different objects
            assert df1 is not df2

    def test_clear_cache_resets_entries(self, mock_matt_clark_dir):
        """clear_cache should reset entries DataFrame cache."""
        with mock.patch.object(matt_clark_parser, 'MATT_CLARK_DIR', mock_matt_clark_dir):
            df1 = matt_clark_parser.load_entries_df(2019)
            matt_clark_parser.clear_cache()
            df2 = matt_clark_parser.load_entries_df(2019)

            # After clearing, should be different objects
            assert df1 is not df2
