import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

class SeriesHistogramVisualizer:
    def __init__(self, series: pd.Series, title: str = "Signal Histogram") -> None:
        self._df = series.to_frame().reset_index()
        self._df.columns = ["date", "signal"]
        self._title = title
        return

    def plot(self) -> plt.Figure:
        data = self._df["signal"].values
        
        # Calculate bin width using Scott's rule
        bin_width = 3.5 * np.std(data) / (len(data)**(1/3))
        
        # Calculate number of bins
        if bin_width > 0:
            num_bins = int((data.max() - data.min()) / bin_width)
        else:
            num_bins = 1
        
        # Plot the histogram
        plt.hist(data, bins=num_bins, color='dodgerblue', density=True)
        plt.title(self._title)
        plt.grid(True)
        return plt
