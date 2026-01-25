import plotly.express as px
from pandas import Series, DataFrame
from typing import Optional
from plotly.graph_objects import Figure
import numpy as np
import pandas as pd
import statsmodels.api as sm

class SeriesVisualizer:
    def __init__(self, series: Series, title: str = "Signal Visualization") -> None:
        self._df: DataFrame = series.to_frame().reset_index()
        self._df.columns = ["date", "signal"]
        self._title: str = title

    def getVisualization(self) -> Figure:
        # Create the figure and add a scatter trace
        fig = px.scatter(self._df, x="date", y="signal", color="signal")
        return fig
            
        
    def calc_epoch(self, ts: np.datetime64  = 10) -> float:
        return pd.to_datetime(ts).timestamp()/(3600*24*365.25)
    
    def calc_dates(self, ts: np.datetime64) -> np.ndarray:
        return pd.to_datetime(ts).strftime("%Y-%m-%d")
    
    def LowessVisualizer(self, frac: float = 0.05) -> Figure:
        data = self._df["signal"].values
        get_epochs = np.vectorize(self.calc_epoch)
        epochs = get_epochs(self._df["date"].values)
        get_dates = np.vectorize(self.calc_dates)
        date_vals = get_dates(self._df["date"].values)

        lowess = sm.nonparametric.lowess
        smoothed = lowess(data, epochs, frac=frac)

        pdata = {"date": date_vals, "signal" : smoothed[:,1]}
        df_lowess = pd.DataFrame.from_dict(pdata)

        fig = px.line(df_lowess, x='date', y='signal', title='Smooth Line Plot with LOWESS')
        

        return fig


class SegmentedSeriesVisualizer(SeriesVisualizer):
    def __init__(self, df: pd.DataFrame, title: str = "Signal Visualization") -> None:
        self._df: DataFrame = df
        self._title: str = title

    def getVisualization(self) -> Figure:
        # Create the line plot with the 'color' attribute
        fig = px.line(
            self._df,
            x="date",
            y="signal",
            color="segment",  # This attribute automatically colors lines by country
            title="Segmented Change Point Representation"
        )

        # Customize the plot appearance (optional)
        fig.update_traces(mode='lines+markers') # Add markers to the lines

        # Return the figure
        return fig

