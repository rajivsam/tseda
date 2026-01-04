from ssalib import SingularSpectrumAnalysis
from matplotlib import pyplot as plt
from typing import List
import pandas as pd

class SSADecomposition:
    def __init__(self, df: pd.DataFrame, window) -> None:
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
        self._ssa.reconstruct(groups={'Trend': comp1, 'Seasonal': comp2})
        fig, axes = self._ssa.plot(kind='timeseries',exclude=['ssa_preprocessed', 'ssa_reconstructed'],subplots=True)
        
        return fig

        