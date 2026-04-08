import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from tseda.decomposition.ssa_result_summary import SSAResultSummary


class FakeSSA:
    def __init__(self, eigenvalues):
        self._eigenvalues = eigenvalues


def test_summary_computes_expected_arrays_and_plots():
    ssa_obj = FakeSSA([4.0, 2.0, 1.0])
    series = pd.Series([1.0, 2.0, 3.0, 4.0])

    summary = SSAResultSummary(ssa_obj=ssa_obj, series=series, window_size=3)

    expected_ranks = np.array([1, 2, 3])
    expected_ev = np.array([4.0 / 7.0, 6.0 / 7.0, 1.0])
    expected_noise = 1.0 - expected_ev

    np.testing.assert_array_equal(summary._ranks, expected_ranks)
    np.testing.assert_allclose(summary._explained_ratio, expected_ev)
    np.testing.assert_allclose(summary._noise_ratio, expected_noise)

    assert summary._n_obs == 4
    assert np.isfinite(summary._aic_exp_var).all()
    assert np.isfinite(summary._aic_noise_var).all()

    fig_ev = summary.plot_variance_explained()
    fig_noise = summary.plot_noise_variance()

    assert isinstance(fig_ev, go.Figure)
    assert isinstance(fig_noise, go.Figure)

    assert np.allclose(np.array(fig_ev.data[0].x), expected_ranks)
    assert np.allclose(np.array(fig_ev.data[0].y), expected_ev)
    assert np.allclose(np.array(fig_noise.data[0].x), expected_ranks)
    assert np.allclose(np.array(fig_noise.data[0].y), expected_noise)


def test_summary_respects_window_size_cap():
    ssa_obj = FakeSSA([5.0, 4.0, 3.0, 2.0])
    series = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])

    summary = SSAResultSummary(ssa_obj=ssa_obj, series=series, window_size=2)

    np.testing.assert_array_equal(summary._ranks, np.array([1, 2]))
    assert len(summary._explained_ratio) == 2
    assert len(summary._noise_ratio) == 2
    assert len(summary._aic_exp_var) == 2
    assert len(summary._aic_noise_var) == 2


def test_formulas_include_expected_keys_and_meta():
    ssa_obj = FakeSSA([3.0, 2.0, 1.0])
    series = pd.Series([1.0, 2.0, 3.0])

    summary = SSAResultSummary(ssa_obj=ssa_obj, series=series, window_size=3, eps=1e-9)
    formulas = summary.formulas()

    assert set(formulas.keys()) == {"ev", "noise_var", "meta"}
    assert "EV(r)" in formulas["ev"]
    assert "sigma2_noise(r)" in formulas["noise_var"]
    assert "n = 3" in formulas["meta"]
    assert "eps = 1e-09" in formulas["meta"]


@pytest.mark.parametrize(
    "ssa_obj, series, window_size, expected_message",
    [
        (None, pd.Series([1.0, 2.0]), 2, "SSA object is not initialized."),
        (FakeSSA([]), pd.Series([1.0, 2.0]), 2, "SSA eigenvalues are unavailable."),
        (FakeSSA([1.0, 2.0]), pd.Series([1.0, 2.0]), 0, "No valid rank available for SSA summary."),
        (FakeSSA([0.0, 0.0]), pd.Series([1.0, 2.0]), 2, "Total SSA variance is non-positive."),
        (FakeSSA([1.0, 2.0]), pd.Series(["a", "b"]), 2, "Series values are not numeric."),
    ],
)
def test_summary_validation_errors(ssa_obj, series, window_size, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        SSAResultSummary(ssa_obj=ssa_obj, series=series, window_size=window_size)
