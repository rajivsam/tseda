import numpy as np
import pandas as pd

from tseda.decomposition.ssa_decomposition import SSADecomposition


def build_phase_shift_series(n=96, period=24, shift_at=48):
    t = np.arange(n)
    season1 = np.sin(2 * np.pi * t[:shift_at] / period)
    season2 = np.sin(2 * np.pi * (t[shift_at:] + period / 2) / period)
    values = np.concatenate([season1, season2])
    series = pd.Series(values, index=pd.date_range("2021-01-01", periods=n, freq="D"))
    return series


def test_change_point_plot_detects_seasonal_phase_shift():
    series = build_phase_shift_series()
    ssa = SSADecomposition(series, window=24)
    ssa.set_reconstruction({"Trend": [0], "Seasonality": [1, 2], "Noise": [3, 4]})

    fig = ssa.change_point_plot()

    assert fig is not None
    annotations = [a["text"] for a in fig.layout.annotations or []]
    assert any("phase" in text.lower() for text in annotations), (
        f"Expected phase summary annotation, got {annotations}"
    )
