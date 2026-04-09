"""KDE-based distribution visualization helpers for time-series values."""

from scipy import stats
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from KDEpy import FFTKDE
from types import ModuleType


class SeriesKDEVisualizer:
    """Render KDE curves and inflection-point diagnostics."""

    def __init__(self, series: pd.Series, title: str = "Signal KDE") -> None:
        """Initialize KDE plotting state.

        Args:
            series: Input numeric series.
            title: Plot title.
        """
        self._df = series.to_frame().reset_index()
        self._df.columns = ["date", "signal"]
        self._title = title

    def KDEVisualizer(self, bandwidth: str = 'ISJ') -> plt.Figure:
        """Plot a KDE estimate using ``KDEpy.FFTKDE``.

        Args:
            bandwidth: KDE bandwidth strategy passed to FFTKDE.

        Returns:
            Matplotlib figure object containing the KDE curve.
        """

        data = self._df["signal"].values

        # Fit KDE using KDEpy's FFTKDE
        kde = FFTKDE(bw=bandwidth)
        grid, y_values = kde.fit(data).evaluate()

        fig, ax = plt.subplots()
        ax.plot(grid, y_values, color='dodgerblue')
        ax.set_title('Kernel Density Estimation for the Signal')
        ax.grid(True)
        return fig
    
    
    
    def getInflectionPointsPlot(self, bandwidth: str = 'scott') -> ModuleType:
        """Plot KDE with estimated inflection points.

        Args:
            bandwidth: Bandwidth method used by ``scipy.stats.gaussian_kde``.

        Returns:
            The ``matplotlib.pyplot`` module (legacy behavior).
        """
        data = self._df["signal"].values
        kde = stats.gaussian_kde(data, bw_method = bandwidth) 
        
        xmin = data.min()
        xmax = data.max()
        xs = np.linspace(xmin - (xmax - xmin) * 0.2, xmax + (xmax - xmin) * 0.2, 5000)
        y_values = kde(xs)
        #y_kde = kde(xs)
        
        # Compute second derivative directly
        # Using deriv=2 in savgol_filter calculates the second derivative after smoothing
        y_d2 = savgol_filter(y_values, 5, 3, deriv=2)

        # 4. Find points where the sign of the second derivative changes
        # np.diff(np.sign(y_d2)) will be non-zero where a sign change occurs.
        # np.where gets the indices of these changes.
        inflection_indices = np.where(np.diff(np.sign(y_d2)))[0]

        # Extract the x and y coordinates of the inflection points
        inflection_points_x = xs[inflection_indices]
        inflection_points_y = y_values[inflection_indices]



        plt.plot(xs, y_values, color='dodgerblue')
        plt.scatter(inflection_points_x, inflection_points_y, color='red', zorder=5, label='Inflection Points')
        plt.title('Kernel Density Estimation for the Signal')
        plt.grid(True)
        return plt





