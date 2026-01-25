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
        assert sp._sampling_freq == "D"

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
        assert df.shape[0] == 5
        assert list(df.columns) == ["property", "value"]
        assert df[df["property"] == "start time"]["value"].values[0] == "2023-01-01"
        assert df[df["property"] == "end_time"]["value"].values[0] == "2023-01-10"
