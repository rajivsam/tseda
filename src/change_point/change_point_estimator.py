from math import ceil, log
import ruptures as rpt
import pandas as pd
from typing import Optional
class ChangePointEstimator:
    def __init__(self, series: pd.Series) -> None:
        self._df: pd.DataFrame = series.to_frame().reset_index()
        self._df.columns = ["date", "signal"]
        self._change_pts: Optional[list] = None

    def label_segement(self, row: pd.Series) -> Optional[str]:
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
        
    def estimate_change_points(self, penalty_coeff: float = 2.0) -> None:
        penalty_est: int = ceil(2*log(self._df.shape[0], 2))
        algo: rpt.Pelt = rpt.Pelt(model="rbf").fit(self._df["signal"].values)
        self._change_pts = algo.predict(pen=penalty_est)
        self._df["segment"] = self._df.apply(lambda row: self.label_segement(row), axis=1)
        