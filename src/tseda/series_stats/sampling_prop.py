"""Sampling property utilities for time-series metadata and SSA window heuristics."""

from typing import Any
import re
import pandas as pd


class SamplingProp:
    """Compute and expose sampling-related properties for a time series."""

    _N: int
    _start_ts: str
    _end_ts: str
    _duration: str
    _sampling_freq: str | None
    _freq_window: int | None

    def __init__(self, series: pd.Series) -> None:
        """Initialize summary metadata for a timestamp-indexed series.

        Args:
            series: Numeric series indexed by datetimes.
        """
        self._N = series.shape[0]
        self._start_ts = series.index.min().strftime("%Y-%m-%d")
        self._end_ts = series.index.max().strftime("%Y-%m-%d")
        self._duration = str(series.index.max() - series.index.min())
        try:
            self._sampling_freq = self.get_readable_freq(series)
            self._freq_window = self.get_freq_window(series.index)
        except Exception:
            self._sampling_freq = "UNKNOWN"
            print("could not infer sampling frequency of the series")

    def view_properties(self) -> pd.DataFrame:
        """Return a tabular view of sampling metadata.

        Returns:
            DataFrame with ``property`` and ``value`` columns.
        """
        data: dict[str, Any] = {
            "N": str(self._N),
            "start time": self._start_ts,
            "end_time": self._end_ts,
            "duration": self._duration,
            "sampling frequency": self._sampling_freq,
            "frequency window": str(self._freq_window) if self._freq_window is not None else "None"
        }

        df: pd.DataFrame = pd.DataFrame.from_dict(data, orient="index").reset_index()
        df.columns = ["property", "value"]

        return df

    def properties_data_table(self) -> Any:
        """Return sampling properties as a Dash AgGrid component.

        This compatibility method is kept for callers/tests that rely on the
        previous API surface.

        Returns:
            Dash ``AgGrid`` component with the sampling property rows.
        """
        from dash_ag_grid import AgGrid

        df = self.view_properties()
        return AgGrid(
            columnDefs=[
                {"field": "property", "headerName": "Property"},
                {"field": "value", "headerName": "Value"},
            ],
            rowData=df.to_dict("records"),
            defaultColDef={"flex": 1, "resizable": True},
        )

    def get_readable_freq(self, series: pd.Series) -> str:
        """Infer and map pandas frequency aliases to readable labels.

        Args:
            series: Timestamp-indexed input series.

        Returns:
            Human-readable frequency label.
        """
        # 1. Infer the frequency alias
        freq_str = pd.infer_freq(series.index)
        if not freq_str:
            return "Unknown"

        # 2. Extract base alias (remove numbers and split at "-")
        # e.g., '2W-SUN' -> 'W', 'ME' -> 'ME'
        base = re.sub(r"\d+", "", freq_str).split("-")[0]
    
        print(f"base: {base}, freq_str: {freq_str}")
        # 3. Define the mapping
        mapping = {
            "H": "hourly", "h": "hourly",
            "D": "daily", "d": "daily",
            "B": "daily (business)", "b": "daily (business)",
            "W": "weekly", "w": "weekly",
            "M": "monthly", "ME": "monthly", "MS": "monthly",
            "Q": "quarterly", "QE": "quarterly", "QS": "quarterly",
            "A": "yearly", "Y": "yearly", "YE": "yearly", "YS": "yearly",
        }

        return mapping.get(base, f"Other ({base})")

    def get_freq_window(self, index: pd.Index) -> int | None:
        """Map pandas inferred frequency to a default SSA window size.

        **Heuristic rationale**

        The window in Singular Spectrum Analysis (SSA) controls the width of the
        trajectory matrix.  A sensible starting point is one full dominant seasonal
        cycle so that the periodic structure appears as a pair of near-equal
        eigenvalues in the eigen spectrum.  The table below lists the cadence-to-
        window mapping used as the *initial* assignment:

        +-----------+--------+----------------------------------------------+
        | Cadence   | Window | Rationale                                    |
        +===========+========+==============================================+
        | Hourly    | 24     | One diurnal (24-hour) cycle                  |
        +-----------+--------+----------------------------------------------+
        | Daily     | 5      | One business week (5 trading/working days)   |
        +-----------+--------+----------------------------------------------+
        | Weekly    | 4      | Approximately one calendar month (4 weeks)   |
        +-----------+--------+----------------------------------------------+
        | Monthly   | 12     | One full annual cycle (12 months)            |
        +-----------+--------+----------------------------------------------+

        **Required invariant after refinement**

        The initial value returned here is a *candidate*, not a final answer.  At
        SSA construction time the caller must verify that the smallest eigenvalue
        explains strictly less than 10 % of total variance.  If it does not, the
        window is doubled and SSA is recomputed; this doubling is repeated until
        the invariant holds or the window would exceed half the series length.  The
        invariant ensures that the eigen spectrum has meaningful spread — i.e. the
        decomposition is not degenerate — and prevents the smallest component from
        carrying too much signal that should have been separated into distinct
        eigenmodes.

        Args:
            index: Datetime index from the source series.

        Returns:
            Initial candidate SSA window size for the inferred frequency, or
            ``None`` when the frequency cannot be determined.
        """
        # 1. Infer the frequency alias (e.g., 'h', 'D', 'W-SUN', 'ME')
        freq_str = pd.infer_freq(index)
        if not freq_str:
            return None

        # 2. Extract base alias: strip numbers and split at "-"
        # This handles variants like '2W-SUN' -> 'W' or 'ME' -> 'ME'
        base = re.sub(r"\d+", "", freq_str).split("-")[0]

        # 3. Define the requested mapping
        mapping = {
            "h": 24, "H": 24,  # Hourly
            "D": 5, "d": 5,  # Daily
            "W": 4, "w": 4,  # Weekly
            "M": 12, "ME": 12,  # Monthly (end)
            "MS": 12,  # Monthly (start)
        }

        return mapping.get(base)

