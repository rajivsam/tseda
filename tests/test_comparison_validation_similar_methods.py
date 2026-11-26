import numpy as np
import pytest
from statsmodels.tsa.seasonal import MSTL, STL

from tseda.notebook_api import NotebookThreeStepAPI, load_series_from_csv


COMPARISON_DATASETS = [
    ("monthly_car_sales", "data/monthly-car-sales.csv", 12),
    ("uci_air_quality_hourly_co", "data/uci_air_quality_hourly_co.csv", 24),
    (
        "hyndman_arrivals_quarterly_japan",
        "data/hyndman_arrivals_quarterly_japan.csv",
        4,
    ),
    (
        "hyndman_hyndsight_daily_pageviews",
        "data/hyndman_hyndsight_daily_pageviews.csv",
        7,
    ),
    (
        "hyndman_sunspot_monthly_area",
        "data/hyndman_sunspot_monthly_area.csv",
        132,
    ),
]

SIMILARITY_TOLERANCE_PERCENT = 15.0


def _variance_shares(
    observed: np.ndarray,
    reconstructed: np.ndarray,
) -> tuple[float, float]:
    residual_sum_of_squares = float(np.sum((observed - reconstructed) ** 2))
    total_sum_of_squares = float(np.sum((observed - np.mean(observed)) ** 2))
    explained = 100.0 * (1.0 - residual_sum_of_squares / total_sum_of_squares)
    return explained, 100.0 - explained


def test_default_alternatives_match_ssa_reconstruction_variance() -> None:
    for name, path, period in COMPARISON_DATASETS:
        series = load_series_from_csv(path)
        api = NotebookThreeStepAPI(series)

        suitability = api.get_suitability_result()
        assert suitability.is_suitable, (
            f"{name} must pass the initial suitability triage before decomposition comparison."
        )

        api.suggest_grouping_with_window_autotune()
        ssa = api._ensure_ssa()
        raw_signal = ssa.get_reconstructed_series("raw_signal")
        ssa_signal = ssa.get_reconstructed_series("smoothed_signal")
        assert raw_signal is not None
        assert ssa_signal is not None

        observed = raw_signal.to_numpy(dtype=float)
        ssa_explained, ssa_unexplained = _variance_shares(
            observed,
            ssa_signal.to_numpy(dtype=float),
        )

        # The alternatives intentionally receive only the documented period.
        # All optional smoothing and robustness controls retain library defaults.
        stl_result = STL(observed, period=period).fit()
        mstl_result = MSTL(observed, periods=(period,)).fit()
        stl_explained, stl_unexplained = _variance_shares(
            observed,
            np.asarray(stl_result.trend) + np.asarray(stl_result.seasonal),
        )
        mstl_explained, mstl_unexplained = _variance_shares(
            observed,
            np.asarray(mstl_result.trend) + np.asarray(mstl_result.seasonal),
        )

        assert np.isfinite(
            [
                ssa_explained,
                ssa_unexplained,
                stl_explained,
                stl_unexplained,
                mstl_explained,
                mstl_unexplained,
            ]
        ).all()
        assert ssa_explained + ssa_unexplained == pytest.approx(100.0)
        assert stl_explained + stl_unexplained == pytest.approx(100.0)
        assert mstl_explained + mstl_unexplained == pytest.approx(100.0)
        assert abs(ssa_explained - stl_explained) <= SIMILARITY_TOLERANCE_PERCENT
        assert abs(ssa_explained - mstl_explained) <= SIMILARITY_TOLERANCE_PERCENT
