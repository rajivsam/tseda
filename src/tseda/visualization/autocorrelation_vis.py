"""ACF/PACF plotting helpers for quick correlation diagnostics."""

import statsmodels.api as sm
from statsmodels.graphics.tsaplots import plot_pacf
import matplotlib.pyplot as plt
from types import ModuleType
import pandas as pd
from pandas import DataFrame


class ACFPlotter:
    """Generate autocorrelation and partial autocorrelation plots."""

    def __init__(self, series: pd.Series, title: str = "PACF Plot", lags: int = 10) -> None:
        """Prepare plotting data and PACF cache containers.

        Args:
            series: Input numeric series.
            title: Reserved title argument for compatibility.
            lags: Number of lags used in ACF/PACF visualizations.
        """
        self._df: DataFrame = series.to_frame().reset_index()
        self._df.columns = ["date", "signal"]
        self._lags: int = lags
        self._pacf_df: DataFrame = pd.DataFrame({"pacf": [], "CI": []})

    def calc_PACF(self) -> ModuleType:
        """Plot and cache partial autocorrelation values.

        Returns:
            The ``matplotlib.pyplot`` module (legacy behavior).
        """
        plot_pacf(self._df["signal"], lags=self._lags, method='yw')
        plt.grid(True)
        plt.title("PACF Plot")
        pacf_values, conf_int = sm.tsa.stattools.pacf(self._df["signal"], alpha=0.05)
        self._pacf_df["pacf"] = pacf_values
        self._pacf_df["CI"] = conf_int

        return plt
    
    def calc_ACF(self) -> ModuleType:
        """Plot autocorrelation values.

        Returns:
            The ``matplotlib.pyplot`` module (legacy behavior).
        """
        sm.graphics.tsa.plot_acf(self._df["signal"], lags=self._lags)
        plt.grid(True)
        plt.title("ACF Plot")
        return plt