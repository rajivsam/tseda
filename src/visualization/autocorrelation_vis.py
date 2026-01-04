import statsmodels.api as sm
from statsmodels.graphics.tsaplots import plot_pacf
import matplotlib.pyplot as plt
import pandas as pd  # Ensure to import pandas for type hinting
from pandas import DataFrame

class ACFPlotter:

    def __init__(self, series: pd.Series, title: str = "PACF Plot", lags: int = 10) -> None:
        self._df: DataFrame = series.to_frame().reset_index()
        self._df.columns = ["date", "signal"]
        self._lags: int = lags
        self._pacf_df: DataFrame = pd.DataFrame({"pacf": [], "CI": []})
        return

    def calc_PACF(self) -> plt.Figure:
        plot_pacf(self._df["signal"], lags=self._lags, method='yw')  # 'yw' for Yule-Walker, default is ols
        plt.grid(True)
        plt.title("PACF Plot")
        pacf_values, conf_int = sm.tsa.stattools.pacf(self._df["signal"], alpha=0.05)
        self._pacf_df["pacf"] = pacf_values
        self._pacf_df["CI"] = conf_int

        return plt
    
    def calc_ACF(self) -> plt.Figure:
        sm.graphics.tsa.plot_acf(self._df["signal"], lags=self._lags)
        plt.grid(True)
        plt.title("ACF Plot")
        return plt