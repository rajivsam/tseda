"""Downloader for Hyndman-based example datasets used by tseda."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class HyndmanExamplesDataLoader:
    """Download and normalize Hyndman example files into the local ``data`` directory."""

    DATASET_URLS = {
        "hyndman_goog_daily_close.csv": "https://raw.githubusercontent.com/rajivsam/tseda/main/data/hyndman_goog_daily_close.csv",
        "hyndman_hyndsight_daily_pageviews.csv": "https://raw.githubusercontent.com/rajivsam/tseda/main/data/hyndman_hyndsight_daily_pageviews.csv",
        "hyndman_arrivals_quarterly_japan.csv": "https://raw.githubusercontent.com/rajivsam/tseda/main/data/hyndman_arrivals_quarterly_japan.csv",
        "hyndman_usconsumption_quarterly_consumption.csv": "https://raw.githubusercontent.com/rajivsam/tseda/main/data/hyndman_usconsumption_quarterly_consumption.csv",
        "hyndman_sunspot_monthly_area.csv": "https://raw.githubusercontent.com/rajivsam/tseda/main/data/hyndman_sunspot_monthly_area.csv",
    }

    def __init__(self, output_dir: str = "data") -> None:
        """Set destination directory for downloaded example files."""
        self.output_dir = Path(output_dir)

    @staticmethod
    def _normalize_two_column_time_series(frame: pd.DataFrame) -> pd.DataFrame:
        """Return a strict two-column format accepted by tseda uploads."""
        if frame.empty or frame.shape[1] < 2:
            raise ValueError("Hyndman source dataset must contain at least two columns")

        normalized = frame.iloc[:, :2].copy()
        normalized.columns = ["timestamp", "value"]
        normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], errors="coerce")
        normalized["value"] = pd.to_numeric(normalized["value"], errors="coerce")
        normalized = normalized.dropna(subset=["timestamp", "value"]).sort_values("timestamp")
        normalized["timestamp"] = normalized["timestamp"].dt.strftime("%Y-%m-%d")

        if len(normalized) > 2000:
            normalized = normalized.iloc[-2000:].copy()

        return normalized

    def download_and_prepare_one(self, file_name: str, source_url: str) -> Path:
        """Download one dataset from URL, normalize it, and write to output directory."""
        frame = pd.read_csv(source_url)
        normalized = self._normalize_two_column_time_series(frame)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / file_name
        normalized.to_csv(output_path, index=False)
        return output_path

    def download_and_prepare_all(self) -> list[Path]:
        """Download, normalize, and write all configured Hyndman example datasets."""
        written_files: list[Path] = []
        for file_name, source_url in self.DATASET_URLS.items():
            written_files.append(self.download_and_prepare_one(file_name, source_url))
        return written_files