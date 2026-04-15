"""Synthetic multi-periodic time-series generator used for testing and demos."""

from .local_dataloader import LocalDataLoader
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from scipy.stats import norm
from math import ceil

class SyntheticSeriesDataLoader(LocalDataLoader):
    """Generate a deterministic synthetic time series with two superimposed periodicities."""

    def __init__(self, file_path: str = "data/synthetic_series.csv"):
        """Initialize with the synthetic series CSV path (unused; series is generated in memory).

        Args:
            file_path: Placeholder path; the series is always generated programmatically.
        """
        super().__init__(file_path)

    def get_series(self) -> pd.Series:
        """Generate and return a synthetic multi-periodic signal series.

        Returns:
            Numeric series indexed by hourly timestamps. Returns an empty float
            series only if generation fails.
        """
        now = datetime.now()
        p1_peak = 5
        p2_peak = 7
        p1 = 6
        p2 = 10
        N = ceil(24*90/1)  # 90 days of hourly data
        time_idx = [float(i) for i in range(N)]
        p1_omega = [(2*np.pi* t)/(p1) for t in time_idx]
        p2_omega = [(2*np.pi* t)/(p2) for t in time_idx]
        p1_vals = [p1_peak*np.sin(w) for w in p1_omega]
        p2_vals = [p2_peak*np.sin(w) for w in p2_omega]
        noise = norm.rvs(loc=0, scale=0.5, size=N)
        level = [20 for _ in range(N)]
        signal = np.array(level) + np.array(p1_vals) + np.array(p2_vals) + np.array(noise)
        time_vals = [now + timedelta(hours=i) for i in range(N)]
        data = {"time": time_vals, "signal": signal}
        df = pd.DataFrame.from_dict(data)
        df.index = df.time
        if not df.empty:
            series = df["signal"]
            series.index = df.time

            return series
        else:
            print("No data available to extract series.")
            return pd.Series(dtype=float)