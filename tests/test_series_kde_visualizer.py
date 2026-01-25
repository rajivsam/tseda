import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from tseda.visualization.series_kde_visualizer import SeriesKDEVisualizer

import matplotlib.pyplot as plt


@pytest.fixture
def sample_series():
    """Create a sample time series for testing."""
    dates = pd.date_range('2023-01-01', periods=100)
    values = np.random.randn(100)
    return pd.Series(values, index=dates)


@pytest.fixture
def visualizer(sample_series):
    """Create a SeriesKDEVisualizer instance."""
    return SeriesKDEVisualizer(sample_series, title="Test KDE")


def test_kde_visualizer_returns_plt(visualizer):
    """Test that KDEVisualizer returns a plt object."""
    result = visualizer.KDEVisualizer()
    assert result == plt


def test_kde_visualizer_with_scott_bandwidth(visualizer):
    """Test KDEVisualizer with scott bandwidth method."""
    result = visualizer.KDEVisualizer(bandwidth='scott')
    assert result == plt


def test_kde_visualizer_with_silverman_bandwidth(visualizer):
    """Test KDEVisualizer with silverman bandwidth method."""
    result = visualizer.KDEVisualizer(bandwidth='silverman')
    assert result == plt


@patch('matplotlib.pyplot.plot')
@patch('matplotlib.pyplot.title')
@patch('matplotlib.pyplot.grid')
def test_kde_visualizer_plot_calls(mock_grid, mock_title, mock_plot, visualizer):
    """Test that KDEVisualizer makes expected plot calls."""
    visualizer.KDEVisualizer()
    
    assert mock_plot.called
    assert mock_title.called
    assert mock_grid.called
    mock_title.assert_called_with('Kernel Density Estimation for the Signal')
    mock_grid.assert_called_with(True)


def test_kde_visualizer_with_single_value():
    """Test KDEVisualizer with a series of identical values."""
    series = pd.Series([5.0] * 50)
    visualizer = SeriesKDEVisualizer(series)
    result = visualizer.KDEVisualizer()
    assert result == plt


def test_kde_visualizer_with_negative_values():
    """Test KDEVisualizer with negative values in the series."""
    series = pd.Series(np.linspace(-10, -1, 50))
    visualizer = SeriesKDEVisualizer(series)
    result = visualizer.KDEVisualizer()
    def test_kde_visualizer_with_negative_values():
        """Test KDEVisualizer with negative values in the series."""
        series = pd.Series(np.linspace(-10, -1, 50))
        visualizer = SeriesKDEVisualizer(series)
        result = visualizer.KDEVisualizer()
        assert result == plt


    def test_kde_visualizer_initialization():
        """Test SeriesKDEVisualizer initialization."""
        dates = pd.date_range('2023-01-01', periods=50)
        series = pd.Series(np.random.randn(50), index=dates)
        visualizer = SeriesKDEVisualizer(series, title="Custom Title")
        assert visualizer._title == "Custom Title"
        assert visualizer._df.columns.tolist() == ["date", "signal"]
        assert len(visualizer._df) == 50


    def test_kde_visualizer_default_title():
        """Test SeriesKDEVisualizer with default title."""
        series = pd.Series([1, 2, 3, 4, 5])
        visualizer = SeriesKDEVisualizer(series)
        assert visualizer._title == "Signal KDE"


    def test_kde_visualizer_with_large_dataset():
        """Test KDEVisualizer with a large dataset."""
        series = pd.Series(np.random.randn(10000))
        visualizer = SeriesKDEVisualizer(series)
        result = visualizer.KDEVisualizer()
        assert result == plt


    def test_kde_visualizer_with_mixed_positive_negative():
        """Test KDEVisualizer with mixed positive and negative values."""
        series = pd.Series(np.linspace(-50, 50, 100))
        visualizer = SeriesKDEVisualizer(series)
        result = visualizer.KDEVisualizer()
        assert result == plt


    def test_kde_visualizer_with_outliers():
        """Test KDEVisualizer with outliers in the series."""
        values = [1, 2, 3, 4, 5, 100, 2, 3, 4]
        series = pd.Series(values)
        visualizer = SeriesKDEVisualizer(series)
        result = visualizer.KDEVisualizer()
        assert result == plt