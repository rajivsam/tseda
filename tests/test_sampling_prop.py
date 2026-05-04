import pytest
import pandas as pd
from datetime import datetime, timedelta
from tseda.series_stats.sampling_prop import SamplingProp

class TestSamplingProp:
    @pytest.fixture
    def sample_series(self):
        """Create a sample time series for testing."""
        dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
        return pd.Series(range(10), index=dates)

    def test_initialization(self, sample_series):
        """Test SamplingProp initialization."""
        sp = SamplingProp(sample_series)
        assert sp._N == 10
        assert sp._start_ts == "2023-01-01"
        assert sp._end_ts == "2023-01-10"
        assert sp._sampling_freq == "daily"

    def test_start_ts_format(self, sample_series):
        """Test that start_ts is formatted correctly as YYYY-MM-DD."""
        sp = SamplingProp(sample_series)
        assert sp._start_ts == "2023-01-01"
        assert len(sp._start_ts) == 10

    def test_end_ts_format(self, sample_series):
        """Test that end_ts is formatted correctly as YYYY-MM-DD."""
        sp = SamplingProp(sample_series)
        assert sp._end_ts == "2023-01-10"
        assert len(sp._end_ts) == 10

    def test_duration_calculation(self, sample_series):
        """Test duration is correctly calculated."""
        sp = SamplingProp(sample_series)
        assert sp._duration == "9 days 00:00:00"

    def test_view_properties(self, sample_series):
        """Test view_properties returns correct DataFrame."""
        sp = SamplingProp(sample_series)
        df = sp.view_properties()
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] == 6
        assert list(df.columns) == ["property", "value"]
        assert df[df["property"] == "start time"]["value"].values[0] == "2023-01-01"
        assert df[df["property"] == "end_time"]["value"].values[0] == "2023-01-10"

    def test_properties_data_table(self, sample_series):
        """Test properties_data_table returns correct AgGrid."""
        from dash_ag_grid import AgGrid
        sp = SamplingProp(sample_series)
        ag = sp.properties_data_table()
        assert isinstance(ag, AgGrid)
        assert len(ag.rowData) == 6
        assert ag.columnDefs[0]['field'] == 'property'
        assert ag.columnDefs[1]['field'] == 'value'

    def test_quarterly_series_maps_to_quarterly_window(self):
        """Quarterly aliases such as QS/QS-OCT should map to a valid window."""
        dates = pd.date_range(start="1981-01-01", periods=20, freq="QS-OCT")
        series = pd.Series(range(20), index=dates)

        sp = SamplingProp(series)

        assert sp._sampling_freq == "quarterly"
        assert sp._freq_window == 4

    def test_irregular_business_daily_falls_back_to_daily_window(self):
        """Daily-like series with occasional gaps should still infer a daily window."""
        dates = pd.to_datetime(
            [
                "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05", "2023-01-06",
                "2023-01-09", "2023-01-10", "2023-01-11", "2023-01-12", "2023-01-13",
                "2023-01-17", "2023-01-18", "2023-01-19", "2023-01-20",
            ]
        )
        series = pd.Series(range(len(dates)), index=dates)

        sp = SamplingProp(series)

        assert sp._sampling_freq in {"daily", "daily (business)"}
        assert sp._freq_window == 5
