import pytest
import pandas as pd
from datetime import datetime, timedelta
from visualization.autocorrelation_vis import ACFPlotter

class TestACFPlotterInit:
    
    def test_init_with_default_parameters(self):
        """Test initialization with default parameters."""
        dates = pd.date_range(start='2023-01-01', periods=10)
        series = pd.Series(range(10), index=dates)
        
        plotter = ACFPlotter(series)
        
        assert plotter._lags == 10
        assert plotter._df.shape == (10, 2)
        assert list(plotter._df.columns) == ["date", "signal"]
        assert list(plotter._df["signal"]) == list(range(10))
        assert plotter._pacf_df.shape == (0, 2)
    
    def test_init_with_custom_lags(self):
        """Test initialization with custom lags parameter."""
        series = pd.Series([1, 2, 3, 4, 5])
        
        plotter = ACFPlotter(series, lags=20)
        
        assert plotter._lags == 20
    
    def test_init_with_custom_title(self):
        """Test initialization with custom title parameter."""
        series = pd.Series([1, 2, 3])
        
        plotter = ACFPlotter(series, title="Custom Title")
        
        assert plotter._lags == 10  # Default value
    
    def test_init_dataframe_structure(self):
        """Test that dataframe is properly structured."""
        dates = pd.date_range(start='2023-01-01', periods=5)
        series = pd.Series([10, 20, 30, 40, 50], index=dates)
        
        plotter = ACFPlotter(series)
        
        assert isinstance(plotter._df, pd.DataFrame)
        assert "date" in plotter._df.columns
        assert "signal" in plotter._df.columns
        assert len(plotter._df) == 5
    
    def test_init_pacf_df_empty(self):
        """Test that PACF dataframe is initialized empty."""
        series = pd.Series([1, 2, 3, 4])
        
        plotter = ACFPlotter(series)
        
        assert isinstance(plotter._pacf_df, pd.DataFrame)
        assert len(plotter._pacf_df) == 0
        assert "pacf" in plotter._pacf_df.columns
        assert "CI" in plotter._pacf_df.columns