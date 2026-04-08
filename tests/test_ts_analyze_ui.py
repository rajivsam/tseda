import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go

import tseda.user_interface.ts_analyze_ui as ui


def test_validate_components_reuses_existing_ssa_and_renders_outputs(monkeypatch):
    ui.series = pd.Series(
        [1.0, 2.0, 3.0, 4.0],
        index=pd.date_range("2021-01-01", periods=4, freq="D"),
    )
    ui.window_size = 4

    call_log = []

    class FakeSSA:
        def __init__(self):
            self._variation_by_group = {"Trend": 90.0, "Noise": 10.0}
            self._durbin_watson = 2.0
            self._noise_signal = None

        def set_reconstruction(self, recon):
            call_log.append(("set_reconstruction", recon))

        def signal_reconstruction_plot(self):
            call_log.append(("signal_reconstruction_plot", None))
            return go.Figure()

        def change_point_plot(self):
            call_log.append(("change_point_plot", None))
            return go.Figure()

        def loess_smother(self, fraction):
            call_log.append(("loess_smother", fraction))
            return go.Figure()

        def wcorr_plot(self):
            call_log.append(("wcorr_plot", None))
            return plt.figure()

        def get_reconstructed_series(self, group_key):
            if group_key == "noise":
                return None
            return None

    class CallbackContext:
        triggered = [{"prop_id": "apply-grouping-trigger.data"}]

    fake_ssa = FakeSSA()
    ui.ssa_obj = fake_ssa
    monkeypatch.setattr(ui.dash, "callback_context", CallbackContext())

    result = ui.validate_components(
        apply_trigger=1,
        name1="Trend",
        list1="0,1",
        name2="Noise",
        list2="*",
        name3="",
        list3="",
        slider_window_size=4,
        loess_fraction=0.2,
        uploaded_file=None,
    )

    assert ui.ssa_obj is fake_ssa
    assert call_log == [
        ("set_reconstruction", {"Trend": [0, 1], "Noise": [2, 3]}),
        ("signal_reconstruction_plot", None),
        ("change_point_plot", None),
        ("wcorr_plot", None),
    ]
    assert result[0].color == "success"
    assert isinstance(result[1], go.Figure)
    assert isinstance(result[2], go.Figure)
    assert result[3].startswith("data:image/png;base64,")
    assert result[4].__class__.__name__ == "Div"
    assert isinstance(result[5], go.Figure)
    assert result[6] is True


def test_logging_rank_diagnostics_uses_fresh_ssa_instance(monkeypatch):
    ui.series = pd.Series(
        [1.0, 2.0, 3.0, 4.0],
        index=pd.date_range("2021-01-01", periods=4, freq="D"),
    )
    ui.window_size = 3

    # Seed a global SSA object that should not be reused by logging diagnostics.
    ui.ssa_obj = object()

    instantiated = []

    class FreshSSA:
        def __init__(self, series, window):
            instantiated.append((series, window))
            self._eigenvalues = np.array([4.0, 2.0, 1.0], dtype=float)

    monkeypatch.setattr(ui, "SSADecomposition", FreshSSA)

    result = ui.update_logging_rank_diagnostics(
        current_step=3,
        uploaded_file=None,
        analysis_complete=True,
    )

    assert len(instantiated) == 1
    assert instantiated[0][1] == 3
    assert "AIC expressions used" in result[0].children[0].children
    assert isinstance(result[1], go.Figure)
    assert isinstance(result[2], go.Figure)
    assert len(result) == 3


def test_logging_rank_diagnostics_requires_analysis_completion(monkeypatch):
    ui.series = pd.Series(
        [1.0, 2.0, 3.0, 4.0],
        index=pd.date_range("2021-01-01", periods=4, freq="D"),
    )
    ui.window_size = 3

    # If analysis is not complete, callback should return warning and empty figures.
    result = ui.update_logging_rank_diagnostics(
        current_step=3,
        uploaded_file=None,
        analysis_complete=False,
    )

    assert result[0].color == "warning"
    assert isinstance(result[1], go.Figure)
    assert isinstance(result[2], go.Figure)
