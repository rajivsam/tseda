import base64

import dash
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import tseda.user_interface.ts_analyze_ui as ui
import tseda.user_interface.callback_services as callback_services


def _csv_upload_payload(csv_text: str) -> str:
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("utf-8")
    return f"data:text/csv;base64,{encoded}"


def test_store_uploaded_file_clear_resets_kb_location_state(monkeypatch):
    class _Ctx:
        triggered = [{"prop_id": "clear-upload-btn.n_clicks"}]

    monkeypatch.setattr(ui.dash, "callback_context", _Ctx())

    result = ui.store_uploaded_file(
        contents=None,
        filename=None,
        clear_clicks=1,
    )

    assert result == (None, None, False, None, None, 0)


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
        refined_window=4,
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


def test_update_ssa_plots_populates_suggested_grouping(monkeypatch):
    ui.series = pd.Series(
        [1.0, 2.0, 3.0, 4.0],
        index=pd.date_range("2021-01-01", periods=4, freq="D"),
    )
    ui.window_size = 4

    class FakeSSA:
        def __init__(self, series, window):
            self._window = window
            self._eigenvalues = np.array([5.0, 4.0, 3.0, 2.0], dtype=float)
            self._exp_var = {
                "var_comp-0": 0.35,
                "var_comp-1": 0.30,
                "var_comp-2": 0.20,
                "var_comp-3": 0.15,
            }

        def eigenplot(self):
            return go.Figure()

        def eigen_vector_plot(self):
            return plt.figure()

        def suggest_reconstruction_groups(self):
            return (
                {
                    "Trend": [0],
                    "Seasonality": [1, 2],
                    "Noise": [3],
                },
                True,
            )

    class CallbackContext:
        triggered = [{"prop_id": "uploaded-file-store.data"}]

    monkeypatch.setattr(ui, "SSADecomposition", FakeSSA)
    monkeypatch.setattr(ui.dash, "callback_context", CallbackContext())

    result = ui.update_ssa_plots(
        current_step=2,
        analysis_complete=False,
        uploaded_file={"contents": "stub", "filename": "stub.csv"},
        slider_window_size=4,
    )

    assert isinstance(result[0], go.Figure)
    assert result[5].__class__.__name__ == "Div"
    assert result[6:12] == ("Trend", "0", "Seasonality", "1, 2", "Noise", "*")


def test_update_ssa_plots_reruns_heuristic_when_slider_changes(monkeypatch):
    ui.series = pd.Series(
        [1.0, 2.0, 3.0, 4.0],
        index=pd.date_range("2021-01-01", periods=4, freq="D"),
    )
    ui.window_size = 4

    heuristic_calls = []

    class FakeSSA:
        def __init__(self, series, window):
            self._window = window
            self._eigenvalues = np.array([5.0, 4.0, 3.0, 2.0], dtype=float)
            self._exp_var = {
                "var_comp-0": 0.35,
                "var_comp-1": 0.30,
                "var_comp-2": 0.20,
                "var_comp-3": 0.15,
            }

        def eigenplot(self):
            return go.Figure()

        def eigen_vector_plot(self):
            return plt.figure()

        def suggest_reconstruction_groups(self):
            heuristic_calls.append(self._window)
            return (
                {"Trend": [0], "Seasonality": [1, 2], "Noise": [3]},
                True,
            )

    class SliderCallbackContext:
        triggered = [{"prop_id": "ssa-window-slider.value"}]

    monkeypatch.setattr(ui, "SSADecomposition", FakeSSA)
    monkeypatch.setattr(ui.dash, "callback_context", SliderCallbackContext())

    result = ui.update_ssa_plots(
        current_step=2,
        analysis_complete=False,
        uploaded_file={"contents": "stub", "filename": "stub.csv"},
        slider_window_size=8,
    )

    # Heuristic must have been called once with the new window size.
    assert heuristic_calls == [8]
    # Global window_size must be updated so validate_components does not rebuild.
    assert ui.window_size == 8
    # Suggestion table and input fields must be populated.
    assert result[5].__class__.__name__ == "Div"
    assert result[6:12] == ("Trend", "0", "Seasonality", "1, 2", "Noise", "*")


def test_update_ssa_plots_preserves_suggestions_after_apply_grouping(monkeypatch):
    ui.series = pd.Series(
        [1.0, 2.0, 3.0, 4.0],
        index=pd.date_range("2021-01-01", periods=4, freq="D"),
    )
    ui.window_size = 4

    class FakeSSA:
        def __init__(self, series, window):
            self._window = window
            self._eigenvalues = np.array([5.0, 4.0, 3.0, 2.0], dtype=float)
            self._exp_var = {}

        def eigenplot(self):
            return go.Figure()

        def eigen_vector_plot(self):
            return plt.figure()

        def suggest_reconstruction_groups(self):
            raise AssertionError("heuristic must not run when analysis-complete-store fires")

    class AnalysisCompleteCallbackContext:
        triggered = [{"prop_id": "analysis-complete-store.data"}]

    ui.ssa_obj = FakeSSA(None, 4)
    monkeypatch.setattr(ui.dash, "callback_context", AnalysisCompleteCallbackContext())

    result = ui.update_ssa_plots(
        current_step=2,
        analysis_complete=True,
        uploaded_file={"contents": "stub", "filename": "stub.csv"},
        slider_window_size=4,
    )

    # All six suggestion outputs must be no_update.
    assert all(v is dash.no_update for v in result[6:12])


def test_segment_selection_advice_and_default_segment_are_configured():
    ui.series = pd.Series(np.linspace(0, 10, 200))

    options, selected, warning = ui.sync_segment_dropdown(None, "l2")
    advice = ui.update_segment_advice(1, ui.series, "l2")

    assert all(option["value"] != "full" for option in options)
    assert len(options) >= 2
    assert selected == len(options) - 1
    assert "Advisor recommendation" in advice
    assert warning is None


def test_segment_view_plot_uses_selected_segment_and_scatter_plot_keeps_full_series():
    ui.series = pd.Series(np.linspace(0, 10, 120))

    options, selected, warning = ui.sync_segment_dropdown(None, "l2")
    scatter_fig = ui.create_scatter_plot(ui.series)
    selected_fig = ui.build_segment_view_figure("selected", 0)

    assert all(option["value"] != "full" for option in options)
    assert selected == len(options) - 1
    assert warning is None
    assert len(scatter_fig.data) >= 3
    assert len(scatter_fig.data[0].x) == len(ui.series)
    segment_total = sum(len(trace.x) for trace in scatter_fig.data[1:-1])
    assert segment_total == len(ui.series)
    assert len(selected_fig.data[0].x) <= len(ui.series)


def test_sync_segment_dropdown_preserves_user_selection():
    ui.series = pd.Series(np.linspace(0, 10, 2000))

    options, selected, warning = ui.sync_segment_dropdown(None, 2)

    assert warning is None
    assert selected == 2
    assert options[2]["value"] == 2
    assert options[2]["label"].startswith("segment-3")


def test_summary_table_uses_selected_segment_for_acf_and_pacf_titles():
    ui.series = pd.Series(
        np.linspace(0, 10, 120),
        index=pd.date_range("2021-01-01", periods=120, freq="D"),
    )

    selected_index = 0
    summary = ui.update_summary_table(
        uploaded_file={"contents": "stub", "filename": "stub.csv"},
        kde_toggle=["show"],
        hist_bin_count=0,
        selected_segment_value=selected_index,
    )

    acf_fig = summary[4].figure
    pacf_fig = summary[5].figure

    assert "Segment 1" in acf_fig.layout.title.text
    assert "Segment 1" in pacf_fig.layout.title.text
    assert len(acf_fig.data[0].y) <= len(ui.series)
    assert len(pacf_fig.data[0].y) <= len(ui.series)


def test_window_selection_helper_returns_candidate_window_for_variance_and_spectral_methods():
    series = pd.Series(np.sin(np.linspace(0, 20, 200)))

    variance_window = callback_services.choose_window_size_for_method(series, "variance-plateau", default_window_size=12)
    adaptive_window = callback_services.choose_window_size_for_method(series, "adaptive-spectral-refinement", default_window_size=12)

    assert isinstance(variance_window, int)
    assert isinstance(adaptive_window, int)
    assert variance_window > 0
    assert adaptive_window > 0


def test_variance_plateau_prefers_the_end_of_the_stable_plateau():
    rng = np.random.default_rng(0)
    signal = rng.normal(0.0, 1.0, size=200)
    signal *= np.where(np.linspace(0.0, 1.0, 200) < 0.5, 1.0, 2.0)
    series = pd.Series(signal)

    selected = callback_services._estimate_variance_plateau_window(series, default_window_size=12)

    assert selected == 96


def test_compute_window_slider_config_creates_full_valid_range_for_manual_method():
    marks, value, min_value, max_value, step = callback_services.compute_window_slider_config(
        current_step=2,
        series_length=768,
        default_window_size=192,
    )

    assert list(marks) == [192, 384]
    assert value == 192
    assert min_value == 192
    assert max_value == 384
    assert step is None


def test_configure_window_selection_dropdown_rebuilds_full_manual_range(monkeypatch):
    ui.series = pd.Series(np.sin(np.linspace(0, 12, 768)))
    ui.window_size = 192

    class MethodChangeContext:
        triggered = [{"prop_id": "window-selection-method.value"}]

    monkeypatch.setattr(ui.dash, "callback_context", MethodChangeContext())

    options, selected = ui.configure_window_selection_dropdown(
        current_step=2,
        uploaded_file=None,
        refined_window=192,
        window_selection_method="manual",
    )

    assert len(options) >= 2
    assert selected == 192
    assert [item["value"] for item in options] == [192, 384]


def test_configure_redo_slider_resets_to_method_recommendation_when_method_changes(monkeypatch):
    ui.series = pd.Series(np.sin(np.linspace(0, 12, 120)))
    ui.window_size = 12

    class MethodChangeContext:
        triggered = [{"prop_id": "window-selection-method.value"}]

    monkeypatch.setattr(ui.dash, "callback_context", MethodChangeContext())

    marks, value, min_value, max_value, step = ui.configure_redo_slider(
        current_step=2,
        uploaded_file=None,
        refined_window=12,
        window_selection_method="variance-plateau",
    )

    recommended = callback_services.choose_window_size_for_method(ui.series, "variance-plateau", 12)

    assert value == 12
    assert recommended > 0
    assert min_value == min(marks)
    assert max_value == max(marks)
    assert step is None


def test_update_window_selection_summary_reports_method_and_recommendation():
    ui.series = pd.Series(np.sin(np.linspace(0, 12, 120)))
    ui.window_size = 12

    summary = ui.update_window_selection_summary(
        current_step=2,
        uploaded_file={"contents": "stub", "filename": "stub.csv"},
        slider_window_size=12,
        window_selection_method="variance-plateau",
    )
    recommended = callback_services.choose_window_size_for_method(ui.series, "variance-plateau", 12)

    assert "Variance plateau" in summary
    assert "Suggested window" in summary
    assert str(recommended) in summary


def test_window_selection_comparison_figure_uses_metric_curves_for_each_method():
    ui.series = pd.Series(np.sin(np.linspace(0, 8, 240)))
    ui.window_size = 12

    fig = ui.build_window_selection_comparison_figure(
        current_step=2,
        uploaded_file={"contents": "stub", "filename": "stub.csv"},
        refined_window=12,
        slider_window_size=12,
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    assert {trace.name for trace in fig.data} == {"Variance plateau", "Adaptive spectral refinement"}
    assert fig.layout.xaxis.title.text == "Window size"
    assert "Variance" in fig.layout.yaxis.title.text or "Residual noise" in fig.layout.yaxis.title.text


def test_adaptive_spectral_curve_uses_base_window_multiples():
    ui.series = pd.Series(np.sin(np.linspace(0, 8, 240)))
    ui.window_size = 12

    fig = ui.build_window_selection_comparison_figure(
        current_step=2,
        uploaded_file={"contents": "stub", "filename": "stub.csv"},
        refined_window=12,
        slider_window_size=12,
    )

    spectral_trace = next(trace for trace in fig.data if trace.name == "Adaptive spectral refinement")
    assert spectral_trace.x is not None
    assert all(int(x) % 12 == 0 for x in spectral_trace.x)
    assert 12 in spectral_trace.x


def test_variance_curve_uses_one_window_step_resolution():
    ui.series = pd.Series(np.sin(np.linspace(0, 8, 240)))
    ui.window_size = 12

    fig = ui.build_window_selection_comparison_figure(
        current_step=2,
        uploaded_file={"contents": "stub", "filename": "stub.csv"},
        refined_window=12,
        slider_window_size=12,
    )

    variance_trace = next(trace for trace in fig.data if trace.name == "Variance plateau")
    x_values = sorted(int(x) for x in variance_trace.x)
    diffs = np.diff(x_values)
    assert diffs.size > 0
    assert all(diff <= 2 for diff in diffs)
    assert not any(diff >= 12 for diff in diffs)

    y_values = [float(value) for value in variance_trace.y]
    assert all(np.isfinite(value) for value in y_values)
    assert len(y_values) > 0
    assert y_values[0] != 0.0


def test_configure_redo_slider_keeps_manual_window_on_method_change(monkeypatch):
    ui.series = pd.Series(np.sin(np.linspace(0, 12, 120)))
    ui.window_size = 12

    class MethodChangeContext:
        triggered = [{"prop_id": "window-selection-method.value"}]

    monkeypatch.setattr(ui.dash, "callback_context", MethodChangeContext())

    marks, value, min_value, max_value, step = ui.configure_redo_slider(
        current_step=2,
        uploaded_file=None,
        refined_window=12,
        window_selection_method="manual",
    )

    assert value == 12
    assert min_value == min(marks)
    assert max_value == max(marks)
    assert step is None


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


def test_parse_upload_rejects_sub_five_minute_frequency():
    csv_text = (
        "timestamp,value\n"
        "2024-01-01 00:00:00,1\n"
        "2024-01-01 00:02:00,2\n"
        "2024-01-01 00:04:00,3\n"
    )

    payload = _csv_upload_payload(csv_text)

    try:
        ui.parse_upload(payload, "sub_5_min.csv")
        assert False, "Expected ValueError for sub-five-minute sampling frequency"
    except ValueError as exc:
        assert "sampling frequency of 5 minutes or higher" in str(exc)


def test_parse_upload_rejects_missing_values_any_column():
    csv_text = (
        "timestamp,value,aux\n"
        "2024-01-01 00:00:00,1,10\n"
        "2024-01-01 01:00:00,,11\n"
        "2024-01-01 02:00:00,3,12\n"
    )

    payload = _csv_upload_payload(csv_text)

    try:
        ui.parse_upload(payload, "has_missing.csv")
        assert False, "Expected ValueError for missing values"
    except ValueError as exc:
        assert "requires data without missing values" in str(exc)


def test_parse_uploaded_series_handles_arrow_string_timestamp_mode():
    csv_text = (
        "timestamp,value\n"
        "1990-01-01,75.8\n"
        "1990-02-01,84.0\n"
        "1990-03-01,93.9\n"
    )
    payload = _csv_upload_payload(csv_text)

    # Exercise parser in an environment that prefers Arrow-backed string storage.
    with pd.option_context("future.infer_string", True, "mode.string_storage", "pyarrow"):
        parsed = callback_services.parse_uploaded_series(
            contents=payload,
            filename="coffee_prices.csv",
            max_file_lines=2000,
        )

    assert parsed is not None
    assert len(parsed) == 3
    assert pd.api.types.is_datetime64_any_dtype(parsed.index)
    assert float(parsed.iloc[0]) == 75.8


# ---------------------------------------------------------------------------
# toggle_save_kb_modal tests
# ---------------------------------------------------------------------------

class _FakeCallbackContext:
    def __init__(self, trigger_id):
        self.triggered = [{"prop_id": f"{trigger_id}.n_clicks"}]


def test_toggle_modal_opens_when_save_as_clicked(monkeypatch):
    monkeypatch.setattr(ui.dash, "callback_context", _FakeCallbackContext("save-to-kb-btn"))
    result = ui.toggle_save_kb_modal(
        save_clicks=1, cancel_clicks=None, confirm_clicks=None, is_open=False
    )
    assert result is True


def test_toggle_modal_closes_when_cancel_clicked(monkeypatch):
    monkeypatch.setattr(ui.dash, "callback_context", _FakeCallbackContext("save-kb-cancel-btn"))
    result = ui.toggle_save_kb_modal(
        save_clicks=None, cancel_clicks=1, confirm_clicks=None, is_open=True
    )
    assert result is False


def test_toggle_modal_closes_when_confirm_clicked(monkeypatch):
    monkeypatch.setattr(ui.dash, "callback_context", _FakeCallbackContext("save-kb-confirm-btn"))
    result = ui.toggle_save_kb_modal(
        save_clicks=None, cancel_clicks=None, confirm_clicks=1, is_open=True
    )
    assert result is False


def test_toggle_modal_no_change_when_untriggered(monkeypatch):
    class _EmptyCtx:
        triggered = []

    monkeypatch.setattr(ui.dash, "callback_context", _EmptyCtx())
    result = ui.toggle_save_kb_modal(
        save_clicks=None, cancel_clicks=None, confirm_clicks=None, is_open=False
    )
    assert result is False


def test_sync_kb_location_state_persists_trimmed_values():
    result = ui.sync_kb_location_state(" /tmp ", " kb.xml ")
    assert result[0] == "/tmp"
    assert result[1] == "kb.xml"
    assert result[2].color == "info"
    assert result[3] is False


def test_sync_kb_location_state_maps_empty_to_none():
    result = ui.sync_kb_location_state("  ", "")
    assert result[0] is None
    assert result[1] is None
    assert result[2].color == "warning"
    assert result[3] is True


def test_sync_kb_location_state_nonexistent_dir_is_invalid():
    result = ui.sync_kb_location_state("/nonexistent_dir_abc_xyz", "kb.xml")
    assert result[2].color == "danger"
    assert "does not exist" in result[2].children
    assert result[3] is True


def test_sync_kb_location_state_permission_denied_is_invalid(monkeypatch):
    monkeypatch.setattr(ui, "validate_kb_directory", lambda _: "Directory is not writable with current privileges: /restricted")
    result = ui.sync_kb_location_state("/restricted", "kb.xml")
    assert result[2].color == "danger"
    assert "not writable" in result[2].children
    assert result[3] is True


def test_hydrate_kb_location_fields_on_modal_open():
    result = ui.hydrate_kb_location_fields(True, "/tmp", "kb.xml")
    assert result == ("/tmp", "kb.xml")


def test_hydrate_kb_location_fields_no_update_when_closed():
    result = ui.hydrate_kb_location_fields(False, "/tmp", "kb.xml")
    assert result[0] is ui.dash.no_update
    assert result[1] is ui.dash.no_update


# ---------------------------------------------------------------------------
# save_kmds_knowledge_base tests
# ---------------------------------------------------------------------------

def test_save_kb_no_clicks_returns_no_update():
    result = ui.save_kmds_knowledge_base(
        confirm_clicks=None, observations="some text", file_dir="/tmp", file_name="kb.xml"
    )
    assert result is ui.dash.no_update


def test_save_kb_empty_observations_returns_warning():
    result = ui.save_kmds_knowledge_base(
        confirm_clicks=1, observations="", file_dir="/tmp", file_name="kb.xml"
    )
    assert result.color == "warning"
    assert "No observations" in result.children


def test_save_kb_missing_dir_returns_warning():
    result = ui.save_kmds_knowledge_base(
        confirm_clicks=1, observations="my obs", file_dir="", file_name="kb.xml"
    )
    assert result.color == "warning"
    assert "directory path" in result.children


def test_save_kb_missing_filename_returns_warning():
    result = ui.save_kmds_knowledge_base(
        confirm_clicks=1, observations="my obs", file_dir="/tmp", file_name=""
    )
    assert result.color == "warning"
    assert "file name" in result.children


def test_save_kb_nonexistent_dir_returns_danger():
    result = ui.save_kmds_knowledge_base(
        confirm_clicks=1,
        observations="my obs",
        file_dir="/nonexistent_path_xyz_12345",
        file_name="kb.xml",
    )
    assert result.color == "danger"
    assert "does not exist" in result.children


def test_save_kb_permission_denied_returns_danger(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, "validate_kb_directory", lambda _: "Directory is not writable with current privileges: /restricted")
    result = ui.save_kmds_knowledge_base(
        confirm_clicks=1,
        observations="my obs",
        file_dir=str(tmp_path),
        file_name="kb.xml",
    )
    assert result.color == "danger"
    assert "not writable" in result.children


def test_save_kb_creates_file_and_returns_success(tmp_path, monkeypatch):
    """Integration test: verifies a KMDS KB file is written to disk."""
    saved_paths = []

    class _FakeKAW:
        def __init__(self, path, namespace):
            self._path = path
            self.has_exploratory_observations = []

    class _FakeOnto:
        def save(self, file, format):
            saved_paths.append(file)
            import pathlib
            pathlib.Path(file).write_text("<rdf/>")

    class _FakeExploratoryObservation:
        def __init__(self, namespace):
            self.finding = None
            self.finding_sequence = None
            self.exploratory_observation_type = None
            self.intent = None

    monkeypatch.setattr(ui, "onto", _FakeOnto())
    monkeypatch.setattr(ui, "ExploratoryObservation", _FakeExploratoryObservation)
    monkeypatch.setattr(ui, "KnowledgeExtractionExperimentationWorkflow", _FakeKAW)

    kb_file = "test_kb.xml"
    result = ui.save_kmds_knowledge_base(
        confirm_clicks=1,
        observations="Time series shows strong trend component.",
        file_dir=str(tmp_path),
        file_name=kb_file,
    )

    assert result.color == "success"
    expected_path = str(tmp_path / kb_file)
    assert expected_path in result.children
    assert len(saved_paths) == 1
    assert saved_paths[0] == expected_path


def test_save_kb_handles_exception_gracefully(tmp_path, monkeypatch):
    class _BrokenOnto:
        def save(self, file, format):
            raise RuntimeError("disk full")

    class _FakeExploratoryObservation:
        def __init__(self, namespace):
            self.finding = None
            self.finding_sequence = None
            self.exploratory_observation_type = None
            self.intent = None

    class _FakeKAW:
        def __init__(self, path, namespace):
            self.has_exploratory_observations = []

    monkeypatch.setattr(ui, "onto", _BrokenOnto())
    monkeypatch.setattr(ui, "ExploratoryObservation", _FakeExploratoryObservation)
    monkeypatch.setattr(ui, "KnowledgeExtractionExperimentationWorkflow", _FakeKAW)

    result = ui.save_kmds_knowledge_base(
        confirm_clicks=1,
        observations="Some obs",
        file_dir=str(tmp_path),
        file_name="kb.xml",
    )

    assert result.color == "danger"
    assert "disk full" in result.children

