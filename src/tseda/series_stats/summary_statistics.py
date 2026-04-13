"""Descriptive statistics computation for time-series signals."""

import pandas as pd

class SummaryStatistics:
    """Compute a standard set of descriptive statistics for a numeric series."""

    def __init__(self, series: pd.Series) -> None:
        """Store the series for later statistical computation.

        Args:
            series: Numeric pandas Series to summarize.
        """
        self.series = series

    def compute_statistics(self) -> pd.DataFrame:
        """Compute descriptive statistics and return them as a tidy two-column DataFrame.

        Returns:
            DataFrame with columns ``statistic`` and ``value`` containing mean,
            median, std_dev, variance, min, max, percentiles, skewness, and kurtosis.
        """
        stats = {
            "mean": self.series.mean(),
            "median": self.series.median(),
            "std_dev": self.series.std(),
            "variance": self.series.var(),
            "min": self.series.min(),
            "max": self.series.max(),
            "25th_percentile": self.series.quantile(0.25),
            "50th_percentile": self.series.quantile(0.50),
            "75th_percentile": self.series.quantile(0.75),
            "skewness": self.series.skew(),
            "kurtosis": self.series.kurtosis(),
        }
        stats_df = pd.DataFrame.from_dict(stats, orient='index', columns=['value']).reset_index()
        stats_df.columns = ['statistic', 'value']
        return stats_df