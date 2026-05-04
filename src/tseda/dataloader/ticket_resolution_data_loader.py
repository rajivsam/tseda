"""Downloader and normalizer for an hourly ticket-resolution time series."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd

from .local_dataloader import LocalDataLoader


class TicketResolutionDataLoader(LocalDataLoader):
    """Build an hourly resolved-ticket count dataset from NYC 311 closed tickets."""

    def __init__(
        self,
        file_path: str = "data/ticket_resolution_hourly_nyc311.csv",
        lookback_days: int = 30,
    ) -> None:
        """Configure output location and default lookback window.

        Args:
            file_path: Destination CSV path for prepared hourly data.
            lookback_days: Number of days to include ending at current UTC hour.
        """
        super().__init__(file_path)
        self.lookback_days = lookback_days
        self.base_url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

    @staticmethod
    def _floor_to_hour_utc(value: datetime) -> datetime:
        """Normalize any datetime to UTC and remove minute/second precision."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)

    def download_and_prepare(
        self,
        start_utc: datetime | None = None,
        end_utc: datetime | None = None,
    ) -> pd.DataFrame:
        """Download, aggregate, regularize, and persist hourly resolved ticket counts.

        The output is constrained for ``tseda`` ingestion:
        1) exactly two columns (``date``, ``signal``),
        2) regular hourly cadence,
        3) no missing values, and
        4) at most 2,000 rows.

        Args:
            start_utc: Optional inclusive window start in UTC.
            end_utc: Optional inclusive window end in UTC.

        Returns:
            Prepared DataFrame written to ``self.file_path``.
        """
        now_hour = self._floor_to_hour_utc(datetime.now(timezone.utc))
        end_dt = self._floor_to_hour_utc(end_utc) if end_utc else now_hour
        start_dt = (
            self._floor_to_hour_utc(start_utc)
            if start_utc
            else end_dt - timedelta(days=self.lookback_days)
        )

        if start_dt >= end_dt:
            raise ValueError("start_utc must be earlier than end_utc")

        where_clause = (
            f"closed_date between '{start_dt.strftime('%Y-%m-%dT%H:%M:%S')}' "
            f"and '{end_dt.strftime('%Y-%m-%dT%H:%M:%S')}'"
        )
        query = {
            "$select": "date_trunc_ymd(closed_date) as day, date_extract_hh(closed_date) as hour, count(*) as value",
            "$where": where_clause,
            "$group": "day, hour",
            "$order": "day, hour",
            "$limit": "5000",
        }

        query_url = f"{self.base_url}?{urlencode(query)}"
        aggregate = pd.read_json(query_url)

        if aggregate.empty:
            raise RuntimeError("No rows returned from NYC 311 for the selected date window")

        aggregate["day"] = pd.to_datetime(aggregate["day"], utc=True)
        aggregate["hour"] = pd.to_numeric(aggregate["hour"], errors="coerce").fillna(0).astype(int)
        aggregate["date"] = aggregate["day"] + pd.to_timedelta(aggregate["hour"], unit="h")
        aggregate["signal"] = pd.to_numeric(aggregate["value"], errors="coerce").fillna(0)
        aggregate = aggregate[["date", "signal"]].sort_values("date")

        hourly_index = pd.date_range(start=start_dt, end=end_dt, freq="h", tz="UTC")
        prepared = (
            aggregate.set_index("date")
            .reindex(hourly_index, fill_value=0)
            .rename_axis("date")
            .reset_index()
        )

        if len(prepared) > 2000:
            raise ValueError(
                "Prepared dataset exceeds 2,000 rows; reduce lookback_days or narrow the date range"
            )

        prepared["signal"] = prepared["signal"].astype(float)
        prepared["date"] = prepared["date"].dt.strftime("%Y-%m-%d %H:%M:%S")

        output_path = Path(self.file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        prepared.to_csv(output_path, index=False)
        return prepared

    def load_ticket_resolution(self, refresh: bool = False, start_utc: datetime | None = None, end_utc: datetime | None = None) -> pd.DataFrame:
        """Load prepared ticket-resolution data; download first if missing or refresh requested.

        Returns:
            DataFrame with columns ``date`` and ``signal``. Returns an empty
            DataFrame if source data cannot be loaded.
        """
        output_path = Path(self.file_path)
        if refresh or not output_path.exists():
            return self.download_and_prepare(start_utc=start_utc, end_utc=end_utc)

        data = self.load_data()
        if data.empty:
            return pd.DataFrame(columns=["date", "signal"])

        normalized = data.iloc[:, :2].copy()
        normalized.columns = ["date", "signal"]
        normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")
        normalized["signal"] = pd.to_numeric(normalized["signal"], errors="coerce")
        normalized = normalized.dropna(subset=["date", "signal"]).sort_values("date")
        return normalized

    def get_series(self, refresh: bool = False, start_utc: datetime | None = None, end_utc: datetime | None = None) -> pd.Series:
        """Return the hourly ticket-resolution count as a pandas Series indexed by date.

        Returns:
            ``signal`` series indexed by ``date``. Returns an empty float series
            when no data is available.
        """
        data = self.load_ticket_resolution(refresh=refresh, start_utc=start_utc, end_utc=end_utc)
        if data.empty:
            print("No data available to extract series.")
            return pd.Series(dtype=float)

        data = data.copy()
        data.index = pd.to_datetime(data["date"])
        return data["signal"]
