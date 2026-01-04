from ssalib import SingularSpectrumAnalysis
from matplotlib import pyplot as plt
from typing import List
import pandas as pd

class SSADecomposition:
    """
    A class to perform Singular Spectrum Analysis (SSA) on a time series.
    """
    def __init__(self, df: pd.DataFrame, window: int) -> None:
        """
        Initializes the SSADecomposition with a time series DataFrame.

        Args:
            df (pd.DataFrame): The input DataFrame with "date" and "signal" columns.
            window (int): The window size for SSA.
        """
        if df.shape[1] == 3:
            cols = ["date","signal"]
            df = df[cols]
        self._df = df
        series = self._df.signal
        self._window = window
        series.index = self._df.date
        self._ssa = SingularSpectrumAnalysis(series, window=window)
        self._ssa.decompose()
        return

    def decomposition_plot(self, comp1: List[int], comp2: List[int] ) -> plt.Figure:
        """
        Creates a plot of the SSA decomposition.

        Args:
            comp1 (List[int]): A list of integers representing the components for the trend.
            comp2 (List[int]): A list of integers representing the components for seasonality.

        Returns:
            plt.Figure: A matplotlib Figure object containing the decomposition plot.
        """
        self._ssa.reconstruct(groups={'Trend': comp1, 'Seasonal': comp2})
        fig, axes = self._ssa.plot(kind='timeseries',exclude=['ssa_preprocessed', 'ssa_reconstructed'],subplots=True)
        
        return fig

        