from datetime import timedelta, date, datetime
from typing import Any, Optional

import pandas as pd


class SamplingProp:
    _N: int
    _start_ts: str
    _end_ts: str
    _duration: str
    _sampling_freq: Optional[str]

    def __init__(self, series: pd.Series) -> None:
        self._N = series.shape[0]
        self._start_ts = series.index.min().strftime("%Y-%m-%d")
        self._end_ts = series.index.max().strftime("%Y-%m-%d")
        self._duration = str(series.index.max() - series.index.min())
        try:
            self._sampling_freq = pd.infer_freq(series.index)
        except Exception:
            self._sampling_freq = "UNKNOWN"
            print("could not infer sampling frequency of the series")

        return

    def view_properties(self) -> pd.DataFrame:
        data: dict[str, Any] = {
            "N": self._N,
            "start time": self._start_ts,
            "end_time": self._end_ts,
            "duration": self._duration,
            "sampling frequency": self._sampling_freq,
        }

        df: pd.DataFrame = pd.DataFrame.from_dict(data, orient="index").reset_index()
        df.columns = ["property", "value"]

        return df
        