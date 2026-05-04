import numpy as np
import pandas as pd

from tseda.decomposition.automatic_grouping_heuristic import AutomaticGroupingHeuristic
from tseda.decomposition.ssa_decomposition import SSADecomposition


def build_series(n=60):
    t = np.arange(n)
    values = 0.05 * t + np.sin(2 * np.pi * t / 12)
    return pd.Series(values, index=pd.date_range("2021-01-01", periods=n, freq="D"))


def test_reconstructed_series_cache_and_getters():
    series = build_series()
    ssa = SSADecomposition(series, window=12)
    ssa.set_reconstruction({"Trend": [0, 1], "Seasonality": [2, 3], "Noise": [4, 5]})

    fig = ssa.signal_reconstruction_plot()

    trend = ssa.get_reconstructed_series("trend")
    seasonality = ssa.get_group_series("seasonality")
    noise = ssa.get_reconstructed_series("noise")
    smoothed = ssa.get_reconstructed_series("smoothed_signal")
    raw = ssa.get_reconstructed_series("raw_signal")

    assert fig is not None
    assert trend is not None
    assert seasonality is not None
    assert noise is not None
    assert smoothed is not None
    assert raw is not None

    np.testing.assert_allclose(smoothed.values, trend.values + seasonality.values)
    np.testing.assert_allclose(raw.values, ssa._ssa.to_frame()["ssa_preprocessed"].values)


def test_set_reconstruction_resets_cached_series():
    series = build_series()
    ssa = SSADecomposition(series, window=12)
    ssa.set_reconstruction({"Trend": [0, 1], "Noise": [2, 3]})
    ssa.signal_reconstruction_plot()

    assert ssa.get_reconstructed_series("trend") is not None
    assert ssa.get_reconstructed_series("smoothed_signal") is not None

    ssa.set_reconstruction({"Trend": [0], "Seasonality": [1, 2], "Noise": [3, 4]})

    assert ssa._raw_signal is None
    assert ssa._smoothed_signal is None
    assert ssa._noise_signal is None
    assert ssa._group_signals == {}

    ssa.signal_reconstruction_plot()

    assert ssa.get_reconstructed_series("trend") is not None
    assert ssa.get_reconstructed_series("seasonality") is not None
    assert ssa.get_reconstructed_series("noise") is not None


def test_seasonality_check_heuristic_detects_near_equal_leading_eigenvalues():
    series = build_series()
    ssa = SSADecomposition(series, window=12)
    ssa._eigenvalues = np.array([10.0, 9.7, 4.0, 3.0, 2.0, 1.0])

    result = ssa.seasonality_check_heuristic()

    assert result is True
    assert ssa._seasonality_check_heuristic is True


def test_seasonality_check_heuristic_returns_false_when_no_close_pair_exists():
    series = build_series()
    ssa = SSADecomposition(series, window=12)
    ssa._eigenvalues = np.array([10.0, 8.0, 6.0, 4.0, 2.0, 1.0])

    result = ssa.seasonality_check_heuristic()

    assert result is False
    assert ssa._seasonality_check_heuristic is False


def test_signal_reconstruction_plot_updates_seasonality_heuristic_flag():
    series = build_series()
    ssa = SSADecomposition(series, window=12)
    ssa._eigenvalues = np.array([12.0, 11.6, 5.0, 3.0, 2.0, 1.0])
    ssa.set_reconstruction({"Trend": [0, 1], "Seasonality": [2, 3], "Noise": [4, 5]})

    ssa.signal_reconstruction_plot()

    assert ssa._seasonality_check_heuristic is True


def test_automatic_grouping_heuristic_suggests_trend_seasonality_and_noise():
    heuristic = AutomaticGroupingHeuristic(
        eigenvalues=np.array([40.0, 21.0, 20.2, 8.0, 5.0, 2.0]),
    )

    assert heuristic.suggest_reconstruction() == {
        "Trend": [0],
        "Seasonality": [1, 2],
        "Noise": [3, 4, 5],
    }


def test_suggest_next_expansion_adds_trend_component():
    # eigenvalue[3]=8.0, eigenvalue[4]=5.0 → not near-equal → trend
    heuristic = AutomaticGroupingHeuristic(
        eigenvalues=np.array([40.0, 21.0, 20.2, 8.0, 5.0, 2.0]),
    )
    current = {"Trend": [0], "Seasonality": [1, 2], "Noise": [3, 4, 5]}

    expanded, did_expand = heuristic.suggest_next_expansion(current)

    assert did_expand is True
    assert expanded["Trend"] == [0, 3]
    assert expanded["Seasonality"] == [1, 2]
    assert expanded["Noise"] == [4, 5]


def test_suggest_next_expansion_adds_seasonal_pair():
    # eigenvalue[3]=10.0, eigenvalue[4]=9.7 → near-equal adjacent pair → seasonality
    heuristic = AutomaticGroupingHeuristic(
        eigenvalues=np.array([40.0, 21.0, 20.2, 10.0, 9.7, 2.0]),
    )
    current = {"Trend": [0], "Seasonality": [1, 2], "Noise": [3, 4, 5]}

    expanded, did_expand = heuristic.suggest_next_expansion(current)

    assert did_expand is True
    assert expanded["Seasonality"] == [1, 2, 3, 4]
    assert expanded["Noise"] == [5]


def test_suggest_next_expansion_returns_false_when_pool_empty():
    heuristic = AutomaticGroupingHeuristic(
        eigenvalues=np.array([40.0, 21.0, 20.2]),
    )
    current = {"Trend": [0], "Seasonality": [1, 2], "Noise": []}

    _, did_expand = heuristic.suggest_next_expansion(current)

    assert did_expand is False


def test_ssa_decomposition_suggest_reconstruction_groups_returns_tuple():
    series = build_series()
    ssa = SSADecomposition(series, window=12)

    groups, dw_satisfied = ssa.suggest_reconstruction_groups()

    assert isinstance(groups, dict)
    assert "Trend" in groups
    assert "Noise" in groups
    assert isinstance(dw_satisfied, bool)


# ---------------------------------------------------------------------------
# Suitability check tests
# ---------------------------------------------------------------------------

def _top_k_ratio(eigenvalues: np.ndarray, k: int) -> float:
    """Compute the fraction of total variance explained by the top-k eigenvalues."""
    eigenvalues = np.asarray(eigenvalues, dtype=float)
    total = float(np.sum(eigenvalues))
    if total <= 0:
        return 0.0
    k = min(k, eigenvalues.size)
    return float(np.sum(eigenvalues[:k])) / total


def test_suitability_check_fails_on_white_noise():
    """White noise produces a flat eigenspectrum; top-5 should not reach 40% of variance."""
    rng = np.random.default_rng(42)
    noise_values = rng.standard_normal(200)
    series = pd.Series(noise_values, index=pd.date_range("2021-01-01", periods=200, freq="D"))

    ssa = SSADecomposition(series, window=20)
    ratio = _top_k_ratio(ssa._eigenvalues, k=5)

    assert ratio < 0.40, (
        f"Expected white noise to fail suitability check (top-5 < 40%), got {ratio:.2%}"
    )


def test_suitability_check_passes_on_structured_series():
    """A trend + seasonality series should have concentrated eigenvalues in the top few."""
    series = build_series(n=120)

    ssa = SSADecomposition(series, window=12)
    ratio = _top_k_ratio(ssa._eigenvalues, k=5)

    assert ratio >= 0.40, (
        f"Expected structured series to pass suitability check (top-5 >= 40%), got {ratio:.2%}"
    )


def test_suitability_check_k_capped_at_spectrum_size():
    """top_k larger than the number of eigenvalues should not raise an error."""
    series = build_series(n=20)
    ssa = SSADecomposition(series, window=5)

    # Request k=100 on a very small spectrum — must not crash
    ratio = _top_k_ratio(ssa._eigenvalues, k=100)

    assert 0.0 <= ratio <= 1.0
