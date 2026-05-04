"""Data loader for UCI Air Quality hourly data."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import pandas as pd

from .local_dataloader import LocalDataLoader


class UCIAirQualityDataLoader(LocalDataLoader):
    """Download, normalize, and expose UCI Air Quality data as a signal series."""

    DATASET_URL = "https://archive.ics.uci.edu/static/public/360/air+quality.zip"
    CSV_NAME_IN_ZIP = "AirQualityUCI.csv"

    def __init__(self, file_path: str = "data/uci_air_quality_hourly_co.csv") -> None:
        """Configure output location for prepared hourly CO series."""
        super().__init__(file_path)

    @staticmethod
    def _normalize_air_quality(frame: pd.DataFrame) -> pd.DataFrame:
        """Return a strict two-column hourly dataset in date/signal format."""
        required = ["Date", "Time", "CO(GT)"]
        missing = [c for c in required if c not in frame.columns]
        if missing:
            raise ValueError(f"UCI Air Quality is missing expected columns: {missing}")

        normalized = frame[required].copy()
        normalized["date"] = pd.to_datetime(
            normalized["Date"].astype(str) + " " + normalized["Time"].astype(str),
            format="%d/%m/%Y %H.%M.%S",
            errors="coerce",
        )

        normalized["signal"] = pd.to_numeric(normalized["CO(GT)"], errors="coerce")
        normalized.loc[normalized["signal"] == -200, "signal"] = pd.NA

        normalized = (
            normalized[["date", "signal"]]
            .dropna(subset=["date", "signal"])
            .sort_values("date")
        )

        if len(normalized) > 2000:
            normalized = normalized.iloc[-2000:].copy()

        normalized["date"] = normalized["date"].dt.strftime("%Y-%m-%d %H:%M:%S")
        return normalized

    def download_and_prepare(self) -> pd.DataFrame:
        """Download UCI Air Quality zip, prepare data, and write CSV to data directory."""
        with urlopen(self.DATASET_URL, timeout=60) as response:
            payload = response.read()

        with ZipFile(BytesIO(payload)) as zf:
            with zf.open(self.CSV_NAME_IN_ZIP) as csv_file:
                frame = pd.read_csv(csv_file, sep=";", decimal=",")

        prepared = self._normalize_air_quality(frame)

        output_path = Path(self.file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        prepared.to_csv(output_path, index=False)

        return prepared

    def load_air_quality(self, refresh: bool = False) -> pd.DataFrame:
        """Load prepared air-quality data; download first if missing or refresh requested.

        Returns:
            DataFrame with columns ``date`` and ``signal``. Returns an empty
            DataFrame if source data cannot be loaded.
        """
        output_path = Path(self.file_path)
        if refresh or not output_path.exists():
            return self.download_and_prepare()

        data = self.load_data()
        if data.empty:
            return pd.DataFrame(columns=["date", "signal"])

        normalized = data.iloc[:, :2].copy()
        normalized.columns = ["date", "signal"]
        normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")
        normalized["signal"] = pd.to_numeric(normalized["signal"], errors="coerce")
        normalized = normalized.dropna(subset=["date", "signal"]).sort_values("date")
        return normalized

    def get_series(self, refresh: bool = False) -> pd.Series:
        """Return the air-quality CO signal as a pandas Series indexed by date.

        Returns:
            ``signal`` series indexed by ``date``. Returns an empty float series
            when no data is available.
        """
        data = self.load_air_quality(refresh=refresh)
        if data.empty:
            print("No data available to extract series.")
            return pd.Series(dtype=float)

        data = data.copy()
        data.index = pd.to_datetime(data["date"])
        return data["signal"]
