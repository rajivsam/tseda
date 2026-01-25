import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from tseda.visualization.series_histogram_visualizer import SeriesHistogramVisualizer

import matplotlib.pyplot as plt


@pytest.fixture
def sample_series():
    """Create a sample time series for testing."""
    dates = pd.date_range('2023-01-01', periods=100)
    values = np.random.randn(100)
    return pd.Series(values, index=dates)


@pytest.fixture
def visualizer(sample_series):
    """Create a SeriesHistogramVisualizer instance."""
    return SeriesHistogramVisualizer(sample_series, title="Test Histogram")


def test_histogram_visualizer_returns_plt(visualizer):
    """Test that plot returns a plt object."""
    result = visualizer.plot()
    assert result == plt


@patch('matplotlib.pyplot.hist')
@patch('matplotlib.pyplot.title')
@patch('matplotlib.pyplot.grid')
def test_histogram_visualizer_plot_calls(mock_grid, mock_title, mock_hist, visualizer):
    """Test that plot makes expected plot calls."""
    visualizer.plot()
    
    assert mock_hist.called
    assert mock_title.called
    assert mock_grid.called
    mock_title.assert_called_with('Test Histogram')
    mock_grid.assert_called_with(True)


def test_histogram_visualizer_with_single_value():
    """Test HistogramVisualizer with a series of identical values."""
    series = pd.Series([5.0] * 50)
    visualizer = SeriesHistogramVisualizer(series)
    result = visualizer.plot()
    assert result == plt


def test_histogram_visualizer_with_negative_values():
    """Test HistogramVisualizer with negative values in the series."""
    series = pd.Series(np.linspace(-10, -1, 50))
    visualizer = SeriesHistogramVisualizer(series)
    result = visualizer.plot()
    assert result == plt


def test_histogram_visualizer_initialization():
    """Test SeriesHistogramVisualizer initialization."""
    dates = pd.date_range('2023-01-01', periods=50)
    series = pd.Series(np.random.randn(50), index=dates)
    visualizer = SeriesHistogramVisualizer(series, title="Custom Title")
    assert visualizer._title == "Custom Title"
    assert visualizer._df.columns.tolist() == ["date", "signal"]
    assert len(visualizer._df) == 50


def test_histogram_visualizer_default_title():
    """Test SeriesHistogramVisualizer with default title."""
    series = pd.Series([1, 2, 3, 4, 5])
    visualizer = SeriesHistogramVisualizer(series)
    assert visualizer._title == "Signal Histogram"


def test_histogram_visualizer_with_large_dataset():
    """Test plot with a large dataset."""
    series = pd.Series(np.random.randn(10000))
    visualizer = SeriesHistogramVisualizer(series)
    result = visualizer.plot()
    assert result == plt


def test_histogram_visualizer_with_mixed_positive_negative():
    """Test plot with mixed positive and negative values."""
    series = pd.Series(np.linspace(-50, 50, 100))
    visualizer = SeriesHistogramVisualizer(series)
    result = visualizer.plot()
    assert result == plt


def test_histogram_visualizer_with_outliers():
    """Test plot with outliers in the series."""
    values = [1, 2, 3, 4, 5, 100, 2, 3, 4]
    series = pd.Series(values)
    visualizer = SeriesHistogramVisualizer(series)
    result = visualizer.plot()
    assert result == plt
