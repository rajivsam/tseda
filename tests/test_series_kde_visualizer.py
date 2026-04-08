import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import matplotlib.pyplot as plt

from tseda.visualization.series_kde_visualizer import SeriesKDEVisualizer


@pytest.fixture
def sample_series():
    dates = pd.date_range('2023-01-01', periods=100)
    values = np.random.randn(100)
    return pd.Series(values, index=dates)


@pytest.fixture
def visualizer(sample_series):
    return SeriesKDEVisualizer(sample_series, title="Test KDE")


def test_initialization(visualizer):
    assert visualizer._title == "Test KDE"
    assert visualizer._df.columns.tolist() == ["date", "signal"]
    assert len(visualizer._df) == 100


@patch('tseda.visualization.series_kde_visualizer.FFTKDE')
def test_kde_visualizer_returns_figure(mock_fftkde, visualizer):
    # Arrange: make FFTKDE.fit().evaluate() return simple arrays
    grid = np.array([0.0, 1.0, 2.0])
    y = np.array([0.1, 0.5, 0.2])
    mock_fftkde.return_value.fit.return_value.evaluate.return_value = (grid, y)

    # Act
    fig = visualizer.KDEVisualizer()

    # Assert: should return a matplotlib Figure
    assert isinstance(fig, plt.Figure)


@patch('tseda.visualization.series_kde_visualizer.plt.plot')
@patch('tseda.visualization.series_kde_visualizer.plt.scatter')
@patch('tseda.visualization.series_kde_visualizer.plt.title')
@patch('tseda.visualization.series_kde_visualizer.plt.grid')
def test_get_inflection_points_plot_calls_plot(mock_grid, mock_title, mock_scatter, mock_plot):
    # Use a simple bimodal series so there are likely inflection points
    values = np.concatenate([np.random.normal(-2, 0.5, 100), np.random.normal(2, 0.5, 100)])
    series = pd.Series(values)
    vis = SeriesKDEVisualizer(series)

    result = vis.getInflectionPointsPlot()

    # The function returns the matplotlib.pyplot module
    assert result == plt
    assert mock_plot.called
    assert mock_scatter.called
    assert mock_title.called
    mock_grid.assert_called_with(True)
