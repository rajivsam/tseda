from scipy import stats
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from KDEpy import FFTKDE


class SeriesKDEVisualizer:
    def __init__(self, series: pd.Series, title: str = "Signal KDE") -> None:
        self._df = series.to_frame().reset_index()
        self._df.columns = ["date", "signal"]
        self._title = title
        return

    def KDEVisualizer(self, bandwidth: str = 'ISJ') -> plt.Figure:

        data = self._df["signal"].values

        # Fit KDE using KDEpy's FFTKDE
        kde = FFTKDE(bw=bandwidth)
        grid, y_values = kde.fit(data).evaluate()

        fig, ax = plt.subplots()
        ax.plot(grid, y_values, color='dodgerblue')
        ax.set_title('Kernel Density Estimation for the Signal')
        ax.grid(True)
        return fig
    
    
    
    def getInflectionPointsPlot(self, bandwidth: str = 'scott') -> plt.Figure:
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
        
    
    

    
