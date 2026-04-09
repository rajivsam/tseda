"""Frequency-domain analysis helpers based on Lomb-Scargle periodograms."""

import numpy as np
from scipy.signal import lombscargle
import matplotlib.pyplot as plt
from pandas import DataFrame, Series


class FFT_Analyzer:
    """Analyze periodic structure in a series using Lomb-Scargle power spectra."""

    def __init__(self, series: Series, fmin: float = 0.1, fmax: float = 2.0, num_freqs: int = 1000) -> None:
        """Initialize analyzer state and centered signal representation.

        Args:
            series: Input numeric signal.
            fmin: Minimum search frequency (cycles per sample).
            fmax: Maximum search frequency (cycles per sample).
            num_freqs: Number of discrete frequencies in the scan.
        """
        self._df: DataFrame = series.to_frame().reset_index()
        self._df.columns = ["date", "signal"]
        self._df["t"] = range(1, len(self._df) + 1)
        self.fmin: float = fmin
        self.fmax: float = fmax
        self.num_freqs: int = num_freqs
        self._df["signal_centered"] = self._df["signal"] - np.mean(self._df["signal"])
        self.freqs: np.ndarray | None = None
        self.power: np.ndarray | None = None
        self.periods: np.ndarray | None = None
        self.best_period: float | None = None
    
    def periodogram(self) -> tuple[np.ndarray, np.ndarray, float]:
        """Compute Lomb-Scargle periodogram and best period estimate.

        Returns:
            Tuple of (period grid, power spectrum, best period).
        """
        self.freqs = np.linspace(self.fmin*2*np.pi, self.fmax*2*np.pi, self.num_freqs)
        self.power = lombscargle(self._df["t"], self._df["signal_centered"], self.freqs, normalize=True)
        self.periods = 2 * np.pi / self.freqs
        
        best_idx = np.argmax(self.power)
        self.best_period = self.periods[best_idx]
        return self.periods, self.power, self.best_period
    
    def plot(self) -> None:
        """Render the periodogram plot using matplotlib."""
        if self.periods is None or self.power is None:
            self.periodogram()
        
        plt.figure(figsize=(8, 4))
        plt.plot(self.periods, self.power)
        plt.xlabel('Period')
        plt.ylabel('Normalized Power')
        plt.title('Lomb-Scargle Periodogram (SciPy)')
        plt.grid(True)
        plt.show()

 