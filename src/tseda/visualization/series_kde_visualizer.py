from scipy import stats
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter


class SeriesKDEVisualizer:
    def __init__(self, series: pd.Series, title: str = "Signal KDE") -> None:
        self._df = series.to_frame().reset_index()
        self._df.columns = ["date", "signal"]
        self._title = title
        return

    def KDEVisualizer(self, bandwidth: str = 'scott') -> plt.Figure:
        data = self._df["signal"].values
        kde = stats.gaussian_kde(data, bw_method = bandwidth) # nice feature is bandwidth selection by scott's rule is the default.
        
        # 3. Create a range of points where you want to evaluate the PDF
        xmin = data.min()
        xmax = data.max()
        # Create 500 equally spaced points for a smooth plot
        xs = np.linspace(xmin - (xmax - xmin) * 0.2, xmax + (xmax - xmin) * 0.2, 500)
        
        # 4. Evaluate the PDF at these points
        y_values = kde(xs)
        
        # 5. Plot the results (optional, for visualization)
        plt.plot(xs, y_values, color='dodgerblue')
        plt.title('Kernel Density Estimation for the Signal')
        plt.grid(True)
        return plt
    
    
    
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
        
    
    

    
