from math import ceil, log
import ruptures as rpt
import pandas as pd
from typing import Optional
class ChangePointEstimator:
    """
    A class to estimate change points in a time series using Pelt algorithm.
    """
    def __init__(self, series: pd.Series) -> None:
        """
        Initializes the ChangePointEstimator with a time series.

        Args:
            series (pd.Series): The input time series.
        """
        self._df: pd.DataFrame = series.to_frame().reset_index()
        self._df.columns = ["date", "signal"]
        self._change_pts: Optional[list] = None

    def label_segement(self, row: pd.Series) -> Optional[str]:
        """
        Labels a row with its corresponding segment.

        Args:
            row (pd.Series): A row of the DataFrame.

        Returns:
            Optional[str]: The segment label for the row.
        """
        row_idx: int = row.name
        row_label: Optional[str] = None
        index: int = 1
        
        for cp in self._change_pts:
            if row_idx <= cp:
                row_label = "segment-" + str(index)
                break
            else:
                index += 1
        
        return row_label
        
    def estimate_change_points(self, model_to_use : str = "rbf",penalty_coeff: float = 2.0) -> None:
        """
        Estimates the change points in the time series.

        This method uses the Pelt algorithm from the ruptures library to detect
        change points in the signal.

        Args:
            penalty_coeff (float, optional): The penalty coefficient for the
                                             Pelt algorithm. Defaults to 2.0.
        """

        print(f"Estimating change points with penalty coefficient: {penalty_coeff}")

        penalty_est: int = ceil(penalty_coeff*log(self._df.shape[0], 2))
        algo: rpt.Pelt = rpt.Pelt(model= model_to_use).fit(self._df["signal"].values)
        self._change_pts = algo.predict(pen=penalty_est)
        self._df["segment"] = self._df.apply(lambda row: self.label_segement(row), axis=1)
        