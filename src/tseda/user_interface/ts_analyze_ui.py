"""Dash application entrypoint, layouts, and callback orchestration for TSEDA."""

import base64
import io
import os
import tempfile
from typing import Any

import numpy as np
import matplotlib
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from tseda.series_stats.sampling_prop import SamplingProp
from tseda.user_interface.components.initial_eval_components import create_summary_table, create_kde_plot, create_box_plot, create_scatter_plot, create_acf_plot, create_pacf_plot, create_ssa_decomposition_plot
from tseda.user_interface.components.analysis_assessment import analysis_layout as decomposition_layout
from tseda.user_interface.analysis import (
    assessment_placeholders,
    build_initial_assessment_layout,
    build_logging_layout,
    build_main_layout,
    empty_figure,
)
from tseda.user_interface.callback_services import (
    build_noise_kde_figure,
    build_reconstruction_metadata,
    build_suggested_grouping_table,
    choose_window_size_for_method,
    compute_window_slider_config,
    format_component_indices,
    matplotlib_figure_to_data_url,
    parse_reconstruction_groups,
    parse_uploaded_series,
    _select_curve_points,
)
from tseda.decomposition.ssa_decomposition import SSADecomposition
from tseda.decomposition.ssa_result_summary import SSAResultSummary
from tseda.change_point.change_point_estimator import PELT_ChangePointEstimator
from tseda.config.config_loader import ConfigurationManager
from tseda.segmentation.pelt_segmentation import (
    build_adjusted_analysis_segment,
    get_short_segment_confirmation_message,
    infer_cadence_from_series,
    resolve_minimum_segment_points,
    select_pelt_model,
)
from kmds.ontology.kmds_ontology import *
from kmds.tagging.tag_types import ExploratoryTags
from kmds.ontology.intent_types import IntentType

# Use a non-interactive backend since figures are rendered to buffers in callbacks.
matplotlib.use('Agg')

# Load configuration at startup
try:
    ConfigurationManager.load_config()
except Exception as e:
    print(f"Warning: Failed to load configuration: {e}")
    print("Using default values as fallback.")

# Configuration - loaded from config file, with fallback defaults
MAX_FILE_LINES = ConfigurationManager.get("file_upload.max_file_lines", 2000)

series: pd.Series | None = None
window_size: int = 0
ssa_obj: SSADecomposition | None = None
WINDOW_EXT_OPTIMAL = int(ConfigurationManager.get("window_selection.window_ext_optimal", 5))
WINDOW_SELECTION_PLOT_POINTS = int(ConfigurationManager.get("window_selection.plot_points_per_curve", 12))

# --- 1. Step Layouts ---

def initial_assessment_layout() -> html.Div:
    """Build the Step-1 initial assessment layout."""
    return build_initial_assessment_layout()

def logging_layout() -> html.Div:
    """Build the Step-3 observation logging layout."""
    return build_logging_layout()

# --- 2. Main App Layout ---

def build_app_layout() -> dbc.Container:
    """Build the complete multi-step app layout container."""
    return build_main_layout(
        assessment_layout=initial_assessment_layout(),
        decomposition_layout=decomposition_layout(),
        logging_layout=logging_layout(),
    )

# --- 3. Callbacks for Navigation ---

def navigate_steps(
    next_clicks: int | None,
    prev_clicks: int | None,
    analysis_complete: bool,
    current_step: int,
    selected_segment_value: int | str | None,
) -> tuple[dict[str, str] | Any, dict[str, str] | Any, dict[str, str] | Any, int, bool, bool, int | Any, int | Any]:
    """Navigate the three-step workflow and update progress/navigation state."""
    global series, window_size

    # Determine which button was clicked
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = None
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'analysis-complete-store':
        prev_disabled = (current_step == 1)
        next_disabled = (current_step >= 3)
        return dash.no_update, dash.no_update, dash.no_update, current_step, prev_disabled, next_disabled, dash.no_update, dash.no_update

    if button_id == 'next-btn' and current_step < 3:
        if current_step == 1 and series is not None and len(series) > 0:
            required_points = resolve_minimum_segment_points(cadence=infer_cadence_from_series(series))
            boundaries = compute_segment_boundaries(len(series), max(1, min(5, len(series) // max(1, required_points))))
            segment_index = coerce_segment_index(selected_segment_value, fallback=max(0, len(boundaries) - 1))
            if segment_index < len(boundaries):
                segment_start, segment_end = boundaries[segment_index]
                if segment_index == len(boundaries) - 1:
                    adjusted_segment, adjustment = _resolve_segment_adjustment(series, boundaries, segment_index)
                    if adjustment.get("is_adjusted"):
                        segment_start, segment_end = adjusted_segment
                active_segment = series.iloc[segment_start:segment_end]
                series = active_segment
                if len(series) > 0:
                    sampling_props = SamplingProp(series)
                    if sampling_props._freq_window is not None and sampling_props._freq_window > 0:
                        window_size = int(sampling_props._freq_window)
        if current_step == 2 and not bool(analysis_complete):
            pass
        else:
            current_step += 1
    elif button_id == 'prev-btn' and current_step > 1:
        current_step -= 1

    show = {'display': 'block'}
    hide = {'display': 'none'}
    s1 = show if current_step == 1 else hide
    s2 = show if current_step == 2 else hide
    s3 = show if current_step == 3 else hide

    p2_val = 33 if current_step >= 2 else 0
    p3_val = 34 if current_step == 3 else 0

    prev_disabled = (current_step == 1)
    next_disabled = (current_step >= 3)

    return s1, s2, s3, current_step, prev_disabled, next_disabled, p2_val, p3_val



def parse_upload(contents: str | None, filename: str) -> None:
    """Parse uploaded content and store the validated series in module state."""
    global series

    series = parse_uploaded_series(contents=contents, filename=filename, max_file_lines=MAX_FILE_LINES)


def store_uploaded_file(
    contents: str | None,
    filename: str | None,
    clear_clicks: int | None,
) -> tuple[dict[str, str] | None, Any | None, bool, None, None, int]:
    """Persist uploaded file metadata and initialize decomposition prerequisites."""
    global series, window_size, ssa_obj
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger_id == 'clear-upload-btn':
        series = None
        window_size = 0
        ssa_obj = None
        return None, None, False, None, None, 0

    if contents is None or filename is None:
        series = None
        window_size = 0
        ssa_obj = None
        return None, None, False, None, None, 0
    
    try:
        parse_upload(contents, filename)
        if series is None or len(series) == 0:
            raise ValueError("Uploaded file parsing did not produce a valid series.")

        sampling_props = SamplingProp(series)
        freq_window = sampling_props._freq_window
        if freq_window is None or int(freq_window) <= 0:
            raise ValueError("Could not infer a valid window size from the uploaded series.")

        window_size = int(freq_window)
        ssa_obj = None
        return {'contents': contents, 'filename': filename}, None, False, dash.no_update, dash.no_update, 0
    except ValueError as e:
        series = None
        window_size = 0
        ssa_obj = None
        return None, dbc.Alert(str(e), color="danger", className="mt-2"), False, dash.no_update, dash.no_update, 0


def update_summary_table(
    uploaded_file: dict[str, str] | None,
    kde_toggle: list[str] | None,
    hist_bin_count: int | None,
    selected_segment_value: int | str | None = None,
) -> tuple[Any, Any, Any, Any, Any, Any]:
    """Render summary table and exploratory plots for the uploaded series."""
    global series, window_size, ssa_obj

    if not uploaded_file:
        series = None
        window_size = 0
        ssa_obj = None
        return assessment_placeholders()

    try:
        if series is None:
            raise ValueError('Uploaded file parsing did not produce a valid series.')

        show_kde = bool(kde_toggle and 'show' in kde_toggle)
        bin_count = int(hist_bin_count) if hist_bin_count and int(hist_bin_count) > 0 else None

        segment_series = series
        acf_segment_label = None
        pacf_segment_label = None
        if selected_segment_value is not None:
            if isinstance(selected_segment_value, str):
                try:
                    selected_segment_value = int(selected_segment_value)
                except (TypeError, ValueError):
                    selected_segment_value = None
            if selected_segment_value is not None:
                segment_count = max(1, min(5, len(series) // max(1, resolve_minimum_segment_points(cadence=infer_cadence_from_series(series)))))
                boundaries = compute_segment_boundaries(len(series), segment_count)
                selected_index = coerce_segment_index(selected_segment_value, fallback=max(0, len(boundaries) - 1))
                selected_index = min(max(selected_index, 0), len(boundaries) - 1 if boundaries else 0)
                adjusted_segment, adjustment = _resolve_segment_adjustment(series, boundaries, selected_index)
                if adjustment.get("is_adjusted") and selected_index == len(boundaries) - 1:
                    start, end = adjusted_segment
                    acf_segment_label = f"Segment {selected_index + 1} (adjusted)"
                    pacf_segment_label = f"Segment {selected_index + 1} (adjusted)"
                else:
                    start, end = boundaries[selected_index]
                    acf_segment_label = f"Segment {selected_index + 1}"
                    pacf_segment_label = f"Segment {selected_index + 1}"
                segment_series = series.iloc[start:end]

        sampling_props = SamplingProp(series)
        window_size = sampling_props._freq_window if sampling_props._freq_window is not None else 0
        ssa_obj = None
        kde_fig = create_kde_plot(series, show_kde=show_kde, bin_count=bin_count)
        box_fig = create_box_plot(series)
        scatter_fig = create_scatter_plot(series)
        acf_fig = create_acf_plot(segment_series, lags=40, segment_label=acf_segment_label)
        pacf_fig = create_pacf_plot(segment_series, lags=40, segment_label=pacf_segment_label)
        
        return (
            create_summary_table(sampling_props),
            dcc.Graph(figure=kde_fig, style={"height": "400px", "width": "100%"}),
            dcc.Graph(figure=box_fig, style={"height": "400px", "width": "100%"}),
            dcc.Graph(figure=scatter_fig, style={"height": "400px", "width": "100%"}),
            dcc.Graph(figure=acf_fig, style={"height": "400px", "width": "100%"}),
            dcc.Graph(figure=pacf_fig, style={"height": "400px", "width": "100%"})
        )
    except Exception:
        series = None
        window_size = 0
        ssa_obj = None
        # Clear error messages and show placeholders
        return assessment_placeholders()


def _window_method_metric_curve(series: pd.Series, method_key: str, default_window: int) -> tuple[list[int], list[float]]:
    """Return a compact diagnostic curve for one window-selection heuristic."""
    # The spectral heuristic compares coarse multiples of the starting window so the
    # curve captures the broader window sweep. The variance plateau should remain at
    # one-window resolution to show the local plateau structure without skipping over it.
    step_size = max(1, default_window) if method_key == "adaptive-spectral-refinement" else 1
    optimal_window = max(step_size, choose_window_size_for_method(series, method_key, default_window))
    extension = WINDOW_EXT_OPTIMAL * step_size if method_key == "adaptive-spectral-refinement" else WINDOW_EXT_OPTIMAL
    search_end = min(len(series) // 2, optimal_window + extension)
    if search_end <= 0:
        return [default_window], [0.0]

    start_window = max(step_size, min(default_window, search_end))
    windows = list(range(start_window, search_end + 1, step_size))
    if not windows:
        return [default_window], [0.0]

    values: list[float] = []
    for window in windows:
        if window >= len(series):
            continue
        if method_key == "variance-plateau":
            rolling_var = series.rolling(window).var().dropna()
            value = float(rolling_var.mean()) if not rolling_var.empty else np.nan
        else:
            try:
                ssa_obj = SSADecomposition(series, window)
                eig = np.asarray(getattr(ssa_obj, "_eigenvalues", []), dtype=float)
                total = float(np.sum(eig))
                value = float(np.abs(eig[-1]) / total) if eig.size > 0 and total > 0 else np.nan
            except Exception:
                value = np.nan

        values.append(float(value) if np.isfinite(value) else np.nan)

    clean_windows = []
    clean_values = []
    for window, value in zip(windows, values):
        if np.isfinite(value):
            clean_windows.append(window)
            clean_values.append(float(value))

    if not clean_windows:
        return [optimal_window], [0.0]

    if method_key == "variance-plateau":
        percent_changes: list[float] = []
        percent_windows: list[int] = []
        for idx, value in enumerate(clean_values):
            if idx == 0:
                continue
            previous = clean_values[idx - 1]
            if previous == 0:
                percent_changes.append(0.0)
            else:
                percent_changes.append(((value - previous) / previous) * 100.0)
            percent_windows.append(clean_windows[idx])
        clean_windows = percent_windows
        clean_values = percent_changes

    max_points = max(3, min(int(WINDOW_SELECTION_PLOT_POINTS), len(clean_windows)))
    clean_windows, clean_values = _select_curve_points(
        windows=clean_windows,
        values=clean_values,
        method_key=method_key,
        target_points=max_points,
    )

    return clean_windows, clean_values


def build_window_selection_comparison_figure(
    current_step: int,
    uploaded_file: dict[str, str] | None,
    refined_window: int | None,
    slider_window_size: int | None,
) -> go.Figure:
    """Return the two-panel window-selection diagnostic chart for the active methods."""
    if current_step != 2 or series is None or len(series) == 0:
        return empty_figure("No data available")

    base_window = int(refined_window) if refined_window and int(refined_window) > 0 else int(window_size or 0)
    if base_window <= 0:
        return empty_figure("No valid window available")

    method_specs = {
        "Adaptive spectral refinement": {
            "key": "adaptive-spectral-refinement",
            "metric": "Residual noise share",
            "color": "#4c78a8",
        },
        "Variance plateau": {
            "key": "variance-plateau",
            "metric": "Variance change vs previous window (%)",
            "color": "#f58518",
        },
    }

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=False,
        shared_yaxes=False,
        subplot_titles=[label for label in method_specs],
        vertical_spacing=0.12,
        row_heights=[0.5, 0.5],
    )

    for row_idx, (label, spec) in enumerate(method_specs.items(), start=1):
        windows, values = _window_method_metric_curve(series, spec["key"], base_window)
        if not windows:
            continue
        fig.add_trace(
            go.Scatter(
                x=windows,
                y=values,
                mode="lines+markers",
                name=label,
                line={"color": spec["color"], "width": 2},
                marker={"size": 5, "color": spec["color"]},
                hovertemplate=f"{label}<br>Window size: %{{x}}<br>{spec['metric']}: %{{y:.4f}}<extra></extra>",
            ),
            row=row_idx,
            col=1,
        )
        suggested_window = choose_window_size_for_method(series, spec["key"], base_window)
        if windows and suggested_window in windows:
            idx = windows.index(suggested_window)
            fig.add_annotation(
                x=suggested_window,
                y=values[idx],
                text=f"Suggested: {suggested_window}",
                showarrow=True,
                arrowhead=2,
                yshift=10,
                row=row_idx,
                col=1,
            )

        fig.update_xaxes(title_text="Window size", row=row_idx, col=1)
        fig.update_yaxes(title_text=spec["metric"], row=row_idx, col=1)

        x_min, x_max = min(windows), max(windows)
        y_min, y_max = min(values), max(values)
        if y_min == y_max:
            y_pad = max(1.0, abs(y_min) * 0.05)
            y_min -= y_pad
            y_max += y_pad
        fig.update_xaxes(range=[x_min - 1, x_max + 1], row=row_idx, col=1)
        fig.update_yaxes(range=[y_min, y_max], row=row_idx, col=1)

    fig.update_layout(
        title="Window selection diagnostics by method",
        template="plotly_white",
        width=1500,
        height=1300,
        margin={"l": 40, "r": 30, "t": 50, "b": 30},
        showlegend=False,
    )
    return fig


def update_window_selection_summary(
    current_step: int,
    uploaded_file: dict[str, str] | None,
    slider_window_size: int | None,
    window_selection_method: str | None,
) -> str:
    """Return a human-readable summary describing the method and recommended window."""
    if current_step != 2 or series is None or len(series) == 0:
        return "No series loaded."

    effective_window = int(slider_window_size) if slider_window_size is not None and int(slider_window_size) > 0 else int(window_size or 0)
    if effective_window <= 0:
        return "No valid window size available."

    if (window_selection_method or "manual").lower() in {"manual", "manual-slider", "slider"}:
        return f"Manual selection: current window {effective_window}"

    method_name = (window_selection_method or "adaptive-spectral-refinement").strip().lower()
    method_labels = {
        "adaptive-spectral-refinement": "Adaptive spectral refinement",
        "variance-plateau": "Variance plateau",
    }
    recommended = choose_window_size_for_method(series, method_name, effective_window)
    if recommended <= 0:
        recommended = effective_window
    return f"Current method: {method_labels.get(method_name, method_name)} — Suggested window: {recommended}"


def configure_redo_slider(
    current_step: int,
    uploaded_file: dict[str, str] | None,
    refined_window: int | None,
    window_selection_method: str | None = None,
) -> tuple[dict[int, str], int, int, int, None]:
    """Configure valid redo SSA window values as integer multiples of the default window.

    When the refinement loop in ``update_ssa_plots`` has doubled the initial
    adaptive spectral refinement window to satisfy the <10 % smallest-eigenvalue
    invariant, it writes the final value to ``refined-window-store``. This callback
    re-fires on that change and uses the refined value so the slider stays in sync.
    """
    global series, window_size

    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    effective_window = int(refined_window) if refined_window and int(refined_window) > 0 else window_size
    series_length = len(series) if series is not None else 0
    method_name = (window_selection_method or "adaptive-spectral-refinement").strip().lower()

    if current_step != 2 or series_length <= 0 or effective_window <= 0:
        return {}, 0, 0, 0, None

    candidate_windows = [effective_window]
    if series is not None:
        for method_key in ("adaptive-spectral-refinement", "variance-plateau"):
            recommended = choose_window_size_for_method(series, method_key, effective_window)
            if recommended > 0:
                candidate_windows.append(recommended)

    low = min(candidate_windows)
    high = max(candidate_windows)
    step_base = max(1, effective_window)
    valid_windows = [step_base * i for i in range((low + step_base - 1) // step_base, (high // step_base) + 1)]
    if not valid_windows:
        valid_windows = [effective_window]

    marks = {val: str(val) for val in valid_windows}
    value = effective_window if effective_window in valid_windows else valid_windows[0]
    return marks, value, valid_windows[0], valid_windows[-1], None


def configure_window_selection_dropdown(
    current_step: int,
    uploaded_file: dict[str, str] | None,
    refined_window: int | None,
    window_selection_method: str | None = None,
) -> tuple[list[dict[str, int | str]], int | None]:
    """Return a dropdown option list rebuilt when the method selection changes."""
    marks, value, _, _, _ = configure_redo_slider(
        current_step=current_step,
        uploaded_file=uploaded_file,
        refined_window=refined_window,
        window_selection_method=window_selection_method,
    )
    options = [{"label": str(window), "value": int(window)} for window in marks]
    return options, value if value in marks else (list(marks)[0] if marks else None)


def relay_apply_grouping(n_clicks: int | None) -> int:
    """Relay Apply Grouping button clicks into a permanent store."""
    return n_clicks or 0


def relay_loess_fraction(value: float | None) -> float:
    """Relay loess slider value into a permanent store."""
    return value if value is not None else 0.05


def update_ssa_plots(
    current_step: int,
    analysis_complete: bool,
    uploaded_file: dict[str, str] | None,
    slider_window_size: int | None,
    window_selection_method: str | None = None,
) -> tuple[go.Figure, str, bool, Any, bool, Any, str | Any, str | Any, str | Any, str | Any, str | Any, str | Any, int | Any]:
    """Generate SSA plots and series-suitability state for grouping actions."""
    global series, window_size, ssa_obj

    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    empty_suggestions = ("", "", "", "", "", "")
    preserve_suggestions = (dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update)
    
    if current_step != 2 or series is None or window_size <= 0:
        empty_fig = empty_figure("No data available")
        return empty_fig, "", False, None, False, "", *empty_suggestions, dash.no_update
    
    try:
        method_name = (window_selection_method or "adaptive-spectral-refinement").strip().lower()
        selected_window_size = int(slider_window_size) if slider_window_size is not None and int(slider_window_size) > 0 else window_size

        if method_name not in {"manual", "manual-slider", "slider"} and trigger_id in {"window-selection-method", "uploaded-file-store", "step-tracker"}:
            recommended_window = choose_window_size_for_method(series, method_name, selected_window_size)
            if recommended_window > 0:
                selected_window_size = recommended_window

        if ssa_obj is None or getattr(ssa_obj, "_window", None) != selected_window_size:
            ssa_obj = SSADecomposition(series, selected_window_size)
            # Keep the global in sync so validate_components does not rebuild SSA
            # unnecessarily when the user clicks Apply Grouping after moving the slider.
            window_size = selected_window_size

        # Refinement: if this is an initial (non-slider) window assignment and the
        # smallest eigenvalue still accounts for >= min_tail_spread of total variance, the
        # spectrum is too flat — double the window and recompute until the invariant
        # holds or the window would exceed half the series length.
        min_tail_spread = ConfigurationManager.get("window_refinement.min_tail_spread", 0.10)
        
        if trigger_id != 'ssa-window-slider' and method_name in {"adaptive-spectral-refinement", "manual"}:
            _eigs = np.asarray(getattr(ssa_obj, "_eigenvalues", []), dtype=float)
            _total = float(np.sum(_eigs))
            while (
                _eigs.size > 0
                and _total > 0.0
                and float(_eigs[-1]) / _total >= min_tail_spread
                and selected_window_size * 2 <= len(series) // 2
            ):
                selected_window_size *= 2
                ssa_obj = SSADecomposition(series, selected_window_size)
                window_size = selected_window_size
                _eigs = np.asarray(getattr(ssa_obj, "_eigenvalues", []), dtype=float)
                _total = float(np.sum(_eigs))

        eigen_fig = ssa_obj.eigenplot()
        
        mpl_fig = ssa_obj.eigen_vector_plot()
        img_src = matplotlib_figure_to_data_url(mpl_fig)
        import matplotlib
        matplotlib.pyplot.close(mpl_fig)

        # Suitability check: top-k eigenvectors must explain >= min_explained_variance of total variance.
        # A diffuse eigenspectrum means the series lacks dominant structure and SSA is uninformative.
        top_k = ConfigurationManager.get("suitability_check.top_k_eigenvectors", 5)
        min_ev = ConfigurationManager.get("suitability_check.min_explained_variance", 0.40)
        eigenvalues = np.asarray(getattr(ssa_obj, "_eigenvalues", []), dtype=float)
        total_var = float(np.sum(eigenvalues)) if eigenvalues.size > 0 else 0.0
        k = min(top_k, eigenvalues.size)
        top_k_ratio = (float(np.sum(eigenvalues[:k])) / total_var) if total_var > 0 else 0.0
        noisy_series = top_k_ratio < min_ev
        ssa_obj._noisy_series = noisy_series

        noisy_message = None
        if noisy_series:
            noisy_message = dbc.Alert(
                [
                    html.Strong("Dataset not suitable for SSA decomposition. "),
                    f"The top {k} eigenvectors explain only {top_k_ratio:.1%} of total variance "
                    f"(minimum required: {min_ev:.0%}). The eigenspectrum is too diffuse — "
                    "this application is SSA-focused. Please try an external stochastic approach "
                    "such as random walk/Brownian-motion-style models or ARIMA/SARIMA.",
                ],
                color="danger",
                className="mb-0",
            )

        # Re-run the heuristic on any trigger except the Apply Grouping confirmation
        # (analysis-complete-store) so that the user's manual edits are not
        # overwritten after reconstruction. The slider change fires this callback
        # with trigger_id == 'ssa-window-slider', which correctly lands in the
        # heuristic branch and updates the prepopulated fields.
        run_heuristic = trigger_id != 'analysis-complete-store'
        if run_heuristic:
            suggested_groups, dw_satisfied = ssa_obj.suggest_reconstruction_groups()
            suggestion_children = build_suggested_grouping_table(
                ssa_obj=ssa_obj,
                recon_dict=suggested_groups,
                dw_satisfied=dw_satisfied,
            )
            suggestion_values = (
                "Trend",
                format_component_indices(suggested_groups.get("Trend", [])),
                "Seasonality",
                format_component_indices(suggested_groups.get("Seasonality", [])),
                "Noise",
                "*",
            )
        else:
            suggestion_children = dash.no_update
            suggestion_values = preserve_suggestions

        return eigen_fig, img_src, noisy_series, noisy_message, noisy_series, suggestion_children, *suggestion_values, window_size
        
    except Exception as err:
        empty_fig = empty_figure(f"Error: {str(err)[:80]}")
        return empty_fig, "", False, None, False, "", *empty_suggestions, dash.no_update


def validate_components(
    apply_trigger: int,
    uploaded_file: dict[str, str] | None,
    name1: str | None,
    list1: str | None,
    name2: str | None,
    list2: str | None,
    name3: str | None,
    list3: str | None,
    slider_window_size: int | None,
    refined_window: int | None,
    loess_fraction: float | None,
) -> tuple[Any, go.Figure, go.Figure, str, Any, go.Figure, bool, bool]:
    """Validate component inputs and return DW validity status."""
    global series, window_size, ssa_obj

    empty_fig = empty_figure("No reconstruction available")
    empty_metadata = "Reconstruction metadata will appear here after applying grouping."

    if uploaded_file is None and series is None:
        return "", empty_fig, empty_fig, "", empty_metadata, empty_fig, False, False

    if series is None and uploaded_file and uploaded_file.get('contents') and uploaded_file.get('filename'):
        try:
            parse_upload(uploaded_file['contents'], uploaded_file['filename'])
        except Exception:
            pass

    if series is None:
        return dbc.Alert("No data loaded. Please upload a file first.", color="warning"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False, False

    if window_size <= 0:
        # Prefer the slider value (set by user or defaulted from SamplingProp); fall back to SamplingProp.
        if slider_window_size is not None and int(slider_window_size) > 0:
            window_size = int(slider_window_size)
        else:
            try:
                sampling_props = SamplingProp(series)
                freq_window = sampling_props._freq_window
                if freq_window is None or int(freq_window) <= 0:
                    raise ValueError("invalid-window")
                window_size = int(freq_window)
            except Exception:
                return dbc.Alert("No data loaded. Please upload a file first.", color="warning"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False, False

    selected_window_size = int(slider_window_size) if slider_window_size is not None and int(slider_window_size) > 0 else window_size
    refined_default = int(refined_window) if refined_window is not None and int(refined_window) > 0 else 0
    # Guard against callback ordering races: if startup refinement increased the
    # default window but the slider state is still stale, prefer the refined
    # default so all downstream plots use the latest valid SSA window.
    if refined_default > 0 and selected_window_size < refined_default:
        selected_window_size = refined_default
    window_changed = selected_window_size != window_size
    if window_changed:
        window_size = selected_window_size
        ssa_obj = SSADecomposition(series, window_size)

    rows = [(name1, list1), (name2, list2), (name3, list3)]

    try:
        recon_dict = parse_reconstruction_groups(rows=rows, window_size=window_size)

        if recon_dict:
            print(f"[DEBUG] Reconstruction groups: {recon_dict}", flush=True)
            if ssa_obj is None:
                ssa_obj = SSADecomposition(series, window_size)

            ssa_obj.set_reconstruction(recon_dict)

            signal_fig = ssa_obj.signal_reconstruction_plot()
            change_point_fig = ssa_obj.change_point_plot()
            wcorr_mpl_fig = ssa_obj.wcorr_plot()

            metadata = build_reconstruction_metadata(ssa_obj=ssa_obj, recon_dict=recon_dict)
            noise_kde_fig = build_noise_kde_figure(ssa_obj=ssa_obj, fallback_fig=empty_fig)
            wcorr_src = matplotlib_figure_to_data_url(wcorr_mpl_fig)
            import matplotlib
            matplotlib.pyplot.close(wcorr_mpl_fig)

            if window_changed:
                status_alert = dbc.Alert(f"SSA updated to window size {window_size} and components applied successfully!", color="success")
            else:
                status_alert = dbc.Alert("Components applied successfully!", color="success")

            # Check if DW is in valid range
            dw = getattr(ssa_obj, "_durbin_watson", None)
            dw_low = ConfigurationManager.get("noise_validation.dw_low", 1.5)
            dw_high = ConfigurationManager.get("noise_validation.dw_high", 2.5)
            dw_valid = dw is not None and dw_low <= dw <= dw_high

            return status_alert, signal_fig, change_point_fig, wcorr_src, metadata, noise_kde_fig, True, dw_valid

        return dbc.Alert("No valid component groups were provided.", color="warning"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False, False

    except ValueError as e:
        err_msg = str(e)
        if err_msg.startswith("Error: Overlapping components detected"):
            return dbc.Alert(err_msg, color="danger"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False, False
        return dbc.Alert(f"Validation error: {err_msg}", color="danger"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False, False
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False, False


def update_verification_plot(
    loess_fraction: float | None,
    analysis_complete: bool,
    uploaded_file: dict[str, str] | None,
) -> go.Figure:
    """Render LOESS verification plot after grouping is applied and when slider changes."""
    global ssa_obj

    empty_fig = empty_figure("Verification plot will appear after SSA is initialized")

    if uploaded_file is None or ssa_obj is None or not hasattr(ssa_obj, "_recon"):
        return empty_fig

    fraction = float(loess_fraction) if loess_fraction is not None else 0.05
    fraction = max(0.05, min(0.5, fraction))
    return ssa_obj.loess_smother(fraction)


def update_logging_rank_diagnostics(
    current_step: int,
    uploaded_file: dict[str, str] | None,
    analysis_complete: bool,
) -> tuple[Any, go.Figure, go.Figure]:
    """Render SSA rank diagnostics and AIC expressions in the logging panel."""
    global series, window_size

    blank_formula = html.Div(
        "Rank-based AIC formulas and plots will appear here after SSA is available.",
        className='text-muted'
    )
    empty_1 = empty_figure("Variance Explained vs Rank")
    empty_2 = empty_figure("Noise Variance vs Rank")

    if current_step != 3:
        return blank_formula, empty_1, empty_2

    if not bool(analysis_complete):
        return dbc.Alert("Analysis is not completed. Click 'Apply Grouping' in Step 2 first.", color="warning"), empty_1, empty_2

    if series is None and uploaded_file and uploaded_file.get('contents') and uploaded_file.get('filename'):
        try:
            parse_upload(uploaded_file['contents'], uploaded_file['filename'])
        except Exception:
            return dbc.Alert("Unable to parse uploaded file for SSA diagnostics.", color="warning"), empty_1, empty_2

    if series is None or len(series) == 0:
        return dbc.Alert("No data loaded. Upload a file and run analysis first.", color="warning"), empty_1, empty_2

    if window_size <= 0:
        return dbc.Alert("SSA window size is not configured yet.", color="warning"), empty_1, empty_2

    try:
        # Build a fresh SSA object for logging diagnostics to avoid stale/reconstructed state.
        logging_ssa_obj = SSADecomposition(series, window_size)

        summary = SSAResultSummary(ssa_obj=logging_ssa_obj, series=series, window_size=window_size)

        explained_fig = summary.plot_variance_explained()
        noise_fig = summary.plot_noise_variance()

        formulas_dict = summary.formulas()

        formulas = html.Div([
            html.P("AIC expressions used in the rank diagnostics (Gaussian residual approximation):"),
            html.Ul([
                html.Li("AICₑₓₚ(r) = n log(max(ε, σ²_total (1 − EV(r)))) + 2r"),
                html.Li("AICₙₒᵢₛₑ(r) = n log(max(ε, σ²_noise(r))) + 2r"),
                html.Li("EV(r) = Σᵢ₌₁ʳ λᵢ / Σᵢ₌₁ᴸ λᵢ"),
                html.Li("σ²_noise(r) = σ²_total (1 − EV(r))"),
            ]),
            html.Small(
                f"r = reconstruction rank, λᵢ = SSA eigenvalues, {formulas_dict['meta']}.",
                className='text-muted'
            )
        ])

        return formulas, explained_fig, noise_fig

    except Exception as err:
        return dbc.Alert(f"Could not compute rank diagnostics: {str(err)}", color="danger"), empty_1, empty_2


def populate_observation_text(
    current_step: int,
    analysis_complete: bool,
    uploaded_file: dict[str, str] | None,
) -> str | Any:
    """Auto-generate the observation summary text and pre-populate the textarea."""
    global series, window_size, ssa_obj

    if current_step != 3 or not bool(analysis_complete):
        return dash.no_update

    if series is None and uploaded_file and uploaded_file.get('contents') and uploaded_file.get('filename'):
        try:
            parse_upload(uploaded_file['contents'], uploaded_file['filename'])
        except Exception:
            return dash.no_update

    if series is None or len(series) == 0 or window_size <= 0:
        return dash.no_update

    try:
        # Use the live ssa_obj so that reconstruction / Durbin-Watson results are included.
        active_ssa = ssa_obj if ssa_obj is not None else SSADecomposition(series, window_size)
        summary = SSAResultSummary(ssa_obj=active_ssa, series=series, window_size=window_size)
        return summary.build_observation_text()
    except Exception:
        return dash.no_update


def update_segment_advice(
    n_clicks: int | None,
    series_value: pd.Series | None,
    selected_model: str | None,
) -> str:
    """Recommend the PELT cost model and return the advice text."""
    if series_value is None or len(series_value) == 0:
        return "Upload a series to generate segmentation advice."

    model = select_pelt_model(np.asarray(series_value, dtype=float), component_type="trend")
    if selected_model == "rbf":
        model = "rbf"
    return (
        f"Advisor recommendation: {model} (linear/l2 is the default for trend-dominant data; "
        "RBF is used only when the seasonal signal shows non-normal, multimodal behavior or a strong variance shift)."
    )


def _resolve_segment_adjustment(active_series: pd.Series, boundaries: list[tuple[int, int]], selected_index: int | None = None) -> tuple[tuple[int, int], dict[str, Any]]:
    """Return the actual working segment and any adjustment metadata for the final regime."""
    selected_index = max(0, int(selected_index)) if selected_index is not None else len(boundaries) - 1
    selected_index = min(selected_index, max(0, len(boundaries) - 1))
    segment_start, segment_end = boundaries[selected_index]
    cadence = infer_cadence_from_series(active_series)
    required_points = resolve_minimum_segment_points(cadence=cadence)
    half_life = float(ConfigurationManager.get("segmentation.final_segment_half_life", 30.0))
    threshold = float(ConfigurationManager.get("segmentation.final_segment_weight_threshold", 0.95))
    adjustment = build_adjusted_analysis_segment(
        active_series.to_numpy(),
        segments=boundaries,
        min_points=required_points,
        half_life=half_life,
        threshold=threshold,
        cadence=cadence,
    )
    if adjustment.get("is_adjusted") and selected_index == len(boundaries) - 1:
        return tuple(adjustment["selected_segment"]), adjustment
    return (segment_start, segment_end), adjustment


def compute_segment_boundaries(total_points: int, segment_count: int) -> list[tuple[int, int]]:
    """Return segment ranges for the UI.

    Prefer the actual PELT-detected regime boundaries when available, but never
    expose more than the requested segment cap. This keeps the selector readable
    while still honoring the genuine first-stage segmentation signal when the
    series has a small number of meaningful regime changes.
    """
    if total_points <= 0:
        return []

    cap = max(1, int(segment_count))
    cap = min(cap, 5)

    active_series = globals().get("series")
    if isinstance(active_series, pd.Series) and len(active_series) == total_points and total_points > 1:
        try:
            estimator = PELT_ChangePointEstimator(active_series, model="l2")
            labels = estimator.predict_series()
            if len(labels) == total_points and labels.nunique() > 1:
                raw_breaks: list[int] = []
                start_idx = 0
                current_label = labels.iloc[0]
                for idx in range(1, total_points):
                    if labels.iloc[idx] != current_label:
                        raw_breaks.append(idx)
                        start_idx = idx
                        current_label = labels.iloc[idx]
                if raw_breaks:
                    if len(raw_breaks) > cap - 1:
                        step = max(1, len(raw_breaks) // max(1, cap - 1))
                        selected_breaks = raw_breaks[::step]
                        if selected_breaks[-1] != raw_breaks[-1]:
                            selected_breaks.append(raw_breaks[-1])
                        selected_breaks = sorted(set(selected_breaks))
                    else:
                        selected_breaks = raw_breaks

                    boundaries: list[tuple[int, int]] = []
                    prev = 0
                    for break_idx in selected_breaks:
                        boundaries.append((prev, int(break_idx)))
                        prev = int(break_idx)
                    boundaries.append((prev, total_points))
                    if len(boundaries) > 1:
                        return boundaries
        except Exception:
            pass

    if cap <= 1:
        return [(0, total_points)]

    boundaries = []
    for idx in range(cap):
        start = idx * (total_points // cap)
        end = total_points if idx == cap - 1 else (idx + 1) * (total_points // cap)
        boundaries.append((start, end))
    return boundaries


def sync_segment_dropdown(
    uploaded_file: dict[str, str] | None,
    selected_segment_value: int | str | None,
) -> tuple[list[dict[str, str | int]], int | None, str | None]:
    """Populate the selector with actual analysis segments and preserve the user's selected segment."""
    active = series if series is not None and len(series) > 0 else None
    if active is None:
        return [], None, "Upload a series to segment."

    num_points = len(active)
    if num_points <= 1:
        return [{"label": "segment-1", "value": 0}], 0, "Only one segment is available."

    min_points = resolve_minimum_segment_points(cadence=infer_cadence_from_series(active))
    segment_count = max(1, min(5, num_points // max(1, min_points)))
    boundaries = compute_segment_boundaries(num_points, segment_count)
    display_boundaries = list(boundaries)
    if boundaries:
        adjusted_segment, adjustment = _resolve_segment_adjustment(active, boundaries, len(boundaries) - 1)
        if adjustment.get("is_adjusted"):
            display_boundaries[-1] = tuple(adjusted_segment)

    options: list[dict[str, str | int]] = []
    for idx, (start, end) in enumerate(display_boundaries):
        if idx == len(display_boundaries) - 1:
            adjustment = _resolve_segment_adjustment(active, boundaries, idx)[1]
            if adjustment.get("is_adjusted"):
                options.append({"label": f"segment-{idx + 1} (adjusted: {start}:{end})", "value": idx})
                continue
        options.append({"label": f"segment-{idx + 1} ({start}:{end})", "value": idx})

    default_value = len(options) - 1
    if selected_segment_value is None:
        selected_value = default_value
    else:
        selected_value = coerce_segment_index(selected_segment_value, fallback=default_value)
        selected_value = min(max(selected_value, 0), len(options) - 1)

    warning_detail = ""
    if selected_value == default_value:
        warning_detail, _, _ = describe_segment_adjustment(active, boundaries, selected_value)
    return options, selected_value, warning_detail or None


def build_segment_view_figure(view_mode: str | None = "selected", selected_segment_value: int | str | None = None) -> go.Figure:
    """Render the selected analysis segment; the full series is shown separately on the scatter plot."""
    if series is None or len(series) == 0:
        return empty_figure("Upload a series to inspect a segment")

    segment_count = max(1, min(5, len(series) // max(1, resolve_minimum_segment_points(cadence=infer_cadence_from_series(series)))))
    boundaries = compute_segment_boundaries(len(series), segment_count)
    fallback_index = max(0, len(boundaries) - 1)
    if selected_segment_value is None:
        selected_segment_value = fallback_index
    selected_index = coerce_segment_index(selected_segment_value, fallback=fallback_index)
    selected_index = min(max(selected_index, 0), len(boundaries) - 1 if boundaries else 0)

    segment_start, segment_end = boundaries[selected_index]
    adjusted_segment, adjustment = _resolve_segment_adjustment(series, boundaries, selected_index)
    if adjustment.get("is_adjusted") and selected_index == len(boundaries) - 1:
        segment_start, segment_end = adjusted_segment
    data = series.iloc[segment_start:segment_end]
    x_values = data.index
    y_values = data.to_numpy(dtype=float)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_values, y=y_values, mode="lines", line={"color": "#4c78a8", "width": 2}, hovertemplate="%{x}<br>Value: %{y}<extra></extra>"))
    if adjustment.get("is_adjusted") and selected_index == len(boundaries) - 1:
        fig.update_layout(title=f"Segment view: {selected_index + 1} (adjusted final segment)", xaxis_title="Time", yaxis_title="Value", template="plotly_white", margin={"l": 45, "r": 20, "t": 40, "b": 30})
        return fig

    axis_min = x_values[0]
    axis_max = x_values[-1]
    if isinstance(x_values, pd.DatetimeIndex):
        fig.update_xaxes(range=[axis_min.to_pydatetime(), axis_max.to_pydatetime()])
    else:
        fig.update_xaxes(range=[float(axis_min), float(axis_max)])
    fig.update_layout(title=f"Segment view: {selected_index + 1}", xaxis_title="Time", yaxis_title="Value", template="plotly_white", margin={"l": 45, "r": 20, "t": 40, "b": 30})
    return fig


def coerce_segment_index(value: int | str | None, fallback: int = 0) -> int:
    """Translate a dropdown value into a numeric segment index while treating the full-series option as a visualization-only choice."""
    if value is None:
        return fallback
    if isinstance(value, str):
        if value.lower() in {"full", "whole", "whole-series", "full-series"}:
            return fallback
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def describe_segment_adjustment(active_series: pd.Series, boundaries: list[tuple[int, int]], selected_segment_value: int | str | None) -> tuple[str, tuple[int, int], dict[str, Any]]:
    """Describe the effective final-segment adjustment and return the adjusted working segment."""
    if active_series is None or len(active_series) == 0:
        return "Upload a series to inspect segmentation.", (0, 0), {}

    cadence = infer_cadence_from_series(active_series)
    required_points = resolve_minimum_segment_points(cadence=cadence)
    fallback_index = max(0, len(boundaries) - 1)
    selected_index = coerce_segment_index(selected_segment_value, fallback=fallback_index)
    selected_index = min(max(selected_index, 0), max(0, len(boundaries) - 1))
    adjusted_segment, adjustment = _resolve_segment_adjustment(active_series, boundaries, selected_index)
    if not adjustment.get("is_adjusted"):
        return "", adjusted_segment, adjustment

    final_segment = adjustment.get("final_segment", (0, len(active_series)))
    selected_start, selected_end = adjusted_segment
    final_start, final_end = final_segment
    detail = (
        f"PELT created a final segment of {max(0, final_end - final_start)} points, below the minimum stable window "
        f"for {cadence} data ({required_points} points). tseda applied a half-life look-back from the previous regime "
        f"to expand the working segment from ({final_start}:{final_end}) to ({selected_start}:{selected_end}) using a "
        f"half-life of {adjustment.get('half_life', 30.0)} and weight threshold {adjustment.get('threshold', 0.95)}."
    )
    return detail, adjusted_segment, adjustment


def update_segment_view_plot(
    selected_segment_value: int | str | None,
    uploaded_file: dict[str, str] | None = None,
    view_mode: str | None = None,
) -> go.Figure:
    """Refresh the segmentation preview plot using the actual dropdown selection.

    Dash invokes this callback with ``(selected_segment_value, uploaded_file)``. A full-series
    selection is rendered as a full-series visualization while the downstream analysis target
    remains the chosen segment rather than the entire original series.
    """
    if view_mode is None and isinstance(uploaded_file, str):
        view_mode = uploaded_file
        uploaded_file = None
    elif view_mode is None:
        view_mode = "selected"
    if isinstance(selected_segment_value, str) and selected_segment_value.lower() in {"full", "whole", "whole-series", "full-series"}:
        view_mode = "full"
    return build_segment_view_figure(view_mode=view_mode, selected_segment_value=selected_segment_value)


def evaluate_segment_warning(
    uploaded_file: dict[str, str] | None,
    selected_segment_idx: int | str | None,
    segment_options: list[dict[str, str | int]] | None,
) -> tuple[bool, str]:
    """Check whether the selected analysis segment should prompt a short-tail warning and adjustment."""
    active = series if series is not None and len(series) > 0 else None
    if active is None:
        return False, ""

    cadence = infer_cadence_from_series(active)
    required_points = resolve_minimum_segment_points(cadence=cadence)
    fallback_index = max(0, len(segment_options or []) - 1)
    selected_segment_idx = coerce_segment_index(selected_segment_idx, fallback=fallback_index)

    boundaries = compute_segment_boundaries(len(active), max(1, min(5, len(active) // max(1, required_points))))
    if selected_segment_idx < 0 or selected_segment_idx >= len(boundaries):
        selected_segment_idx = fallback_index

    segment_start, segment_end = boundaries[selected_segment_idx]
    final_len = max(0, segment_end - segment_start)
    if final_len < required_points:
        adjusted_segment, adjustment = _resolve_segment_adjustment(active, boundaries, selected_segment_idx)[0], _resolve_segment_adjustment(active, boundaries, selected_segment_idx)[1]
        if adjustment.get("is_adjusted"):
            return True, (
                f"PELT created a final segment of {final_len} points, below the minimum stable window for {cadence} data ({required_points} points). "
                f"The working series will be adjusted to {adjusted_segment[0]}:{adjusted_segment[1]} using a half-life look-back of {adjustment.get('half_life', 30.0)}."
            )
        return True, get_short_segment_confirmation_message(cadence=cadence, required_points=required_points, final_len=final_len)
    return False, ""


def accept_adjusted_segment(
    open_clicks: int | None,
    cancel_clicks: int | None,
    selected_segment_value: int | None,
) -> tuple[bool, dict[str, object] | None]:
    """Accept or cancel the segment-warning modal and return the adjusted selection state."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, None
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger == "segment-warning-cancel-btn":
        return False, None
    if trigger == "segment-warning-continue-btn":
        if selected_segment_value is None:
            return False, None
        return False, {"accepted": True, "segment_index": coerce_segment_index(selected_segment_value)}
    return False, None


def toggle_segment_warning(
    open_clicks: int | None,
    close_clicks: int | None,
    is_open: bool,
) -> bool:
    """Open or close the short-tail analysis warning modal."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger in ("segment-warning-continue-btn", "segment-warning-cancel-btn"):
        return False
    return is_open


def toggle_save_kb_modal(
    save_clicks: int | None,
    cancel_clicks: int | None,
    confirm_clicks: int | None,
    is_open: bool,
) -> bool:
    """Open or close the Save Knowledge Base modal."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger in ("save-to-kb-btn", "save-kb-cancel-btn", "save-kb-confirm-btn"):
        return not is_open
    return is_open


def toggle_window_selection_modal(
    open_clicks: int | None,
    close_clicks: int | None,
    is_open: bool,
) -> bool:
    """Open or close the detailed window-selection diagnostics modal."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger in ("window-selection-diagnostics-btn", "window-selection-modal-close-btn"):
        return not is_open
    return is_open


def sync_kb_location_state(
    file_dir: str | None,
    file_name: str | None,
) -> tuple[str | None, str | None, Any, bool]:
    """Persist KB save directory/filename and validate KB target location in real time."""
    directory = (file_dir or "").strip() or None
    filename = (file_name or "").strip() or None
    if not directory:
        return directory, filename, dbc.Alert("Please enter a directory path.", color="warning", dismissable=True), True

    validation_error = validate_kb_directory(directory)
    if validation_error is not None:
        return directory, filename, dbc.Alert(f"{validation_error} Please try again.", color="danger", dismissable=True), True

    return directory, filename, dbc.Alert("KB location is valid.", color="info", dismissable=True), False


def validate_kb_directory(directory: str) -> str | None:
    """Validate that KB directory exists and is writable by this process.

    Returns:
        ``None`` when valid; otherwise a user-facing error string.
    """
    from pathlib import Path

    dir_path = Path(directory)
    if not dir_path.is_dir():
        return f"Directory does not exist: {directory}"

    if not os.access(dir_path, os.W_OK | os.X_OK):
        return f"Directory is not writable with current privileges: {directory}"

    # Verify writable privileges with an actual create/delete operation.
    try:
        fd, temp_path = tempfile.mkstemp(prefix=".tseda_kb_write_test_", dir=str(dir_path))
        os.close(fd)
        os.unlink(temp_path)
    except OSError:
        return f"Directory is not writable with current privileges: {directory}"

    return None


def hydrate_kb_location_fields(
    is_open: bool,
    stored_dir: str | None,
    stored_filename: str | None,
) -> tuple[str | None | Any, str | None | Any]:
    """Pre-fill KB location fields from app state when the save modal opens."""
    if not is_open:
        return dash.no_update, dash.no_update
    return stored_dir, stored_filename


def save_kmds_knowledge_base(
    confirm_clicks: int | None,
    observations: str | None,
    file_dir: str | None,
    file_name: str | None,
) -> Any:
    """Create a KMDS knowledge base file with the current observations."""
    if not confirm_clicks:
        return dash.no_update

    observations = (observations or "").strip()
    file_dir = (file_dir or "").strip()
    file_name = (file_name or "").strip()

    if not observations:
        return dbc.Alert("No observations to save. Please enter observations first.", color="warning", dismissable=True)
    if not file_dir:
        return dbc.Alert("Please enter a directory path.", color="warning", dismissable=True)
    if not file_name:
        return dbc.Alert("Please enter a file name.", color="warning", dismissable=True)

    import os
    from pathlib import Path

    if not Path(file_dir).is_dir():
        return dbc.Alert(f"Directory does not exist: {file_dir}", color="danger", dismissable=True)

    validation_error = validate_kb_directory(file_dir)
    if validation_error is not None:
        return dbc.Alert(f"{validation_error} Please try again.", color="danger", dismissable=True)

    full_path = os.path.join(file_dir, file_name)

    try:
        exp_obs_list = []
        e1 = ExploratoryObservation(namespace=onto)
        e1.finding = observations
        e1.finding_sequence = 1
        e1.exploratory_observation_type = ExploratoryTags.DATA_QUALITY_OBSERVATION.value
        e1.intent = IntentType.DATA_UNDERSTANDING.value
        exp_obs_list.append(e1)

        kaw = KnowledgeExtractionExperimentationWorkflow(full_path, namespace=onto)
        kaw.has_exploratory_observations = exp_obs_list
        onto.save(file=full_path, format="rdfxml")

        return dbc.Alert(f"Knowledge base saved to: {full_path}", color="success", dismissable=True)
    except Exception as err:
        return dbc.Alert(f"Failed to save knowledge base: {str(err)}", color="danger", dismissable=True)


def register_callbacks(dash_app: dash.Dash) -> None:
    """Register all app callbacks explicitly to separate wiring from logic."""
    dash_app.callback(
        [Output('step1-container', 'style'),
         Output('step2-container', 'style'),
         Output('step3-container', 'style'),
         Output('step-tracker', 'data'),
         Output('prev-btn', 'disabled'),
         Output('next-btn', 'disabled'),
         Output('p2', 'value'),
         Output('p3', 'value')],
        [Input('next-btn', 'n_clicks'),
         Input('prev-btn', 'n_clicks'),
         Input('analysis-complete-store', 'data')],
        [State('step-tracker', 'data'),
         State('selected-segment-dropdown', 'value')],
    )(navigate_steps)

    dash_app.callback(
        [Output('uploaded-file-store', 'data'),
         Output('upload-error-message', 'children'),
         Output('analysis-complete-store', 'data', allow_duplicate=True),
         Output('kb-save-dir-store', 'data'),
         Output('kb-save-filename-store', 'data'),
         Output('refined-window-store', 'data', allow_duplicate=True)],
        Input('upload-data', 'contents'),
        State('upload-data', 'filename'),
        Input('clear-upload-btn', 'n_clicks'),
        prevent_initial_call=True,
    )(store_uploaded_file)

    dash_app.callback(
        [Output('data-preview-container', 'children'),
         Output('kde-plot-container', 'children'),
         Output('box-plot-container', 'children'),
         Output('scatter-plot-container', 'children'),
         Output('acf-plot-container', 'children'),
         Output('pacf-plot-container', 'children')],
        [
            Input('uploaded-file-store', 'data'),
            Input('kde-overlay-toggle', 'value'),
            Input('hist-bin-count-slider', 'value'),
            Input('selected-segment-dropdown', 'value'),
        ],
    )(update_summary_table)

    dash_app.callback(
        [Output('selected-segment-dropdown', 'options'),
         Output('selected-segment-dropdown', 'value'),
         Output('segment-warning-detail', 'children')],
        [Input('uploaded-file-store', 'data'),
         Input('selected-segment-dropdown', 'value')],
    )(sync_segment_dropdown)

    dash_app.callback(
        Output('segment-advisor-output', 'children'),
        [Input('segment-advisor-btn', 'n_clicks'),
         Input('uploaded-file-store', 'data'),
         Input('segment-model-dropdown', 'value')],
    )(lambda n_clicks, uploaded_file, selected_model: update_segment_advice(n_clicks, series, selected_model))

    dash_app.callback(
        Output('segment-view-plot', 'figure'),
        [Input('selected-segment-dropdown', 'value'),
         Input('uploaded-file-store', 'data')],
    )(update_segment_view_plot)

    dash_app.callback(
        Output('segment-warning-modal', 'is_open'),
        [Input('segment-advisor-btn', 'n_clicks'),
         Input('segment-warning-continue-btn', 'n_clicks'),
         Input('segment-warning-cancel-btn', 'n_clicks')],
        [State('selected-segment-dropdown', 'value'),
         State('segment-warning-modal', 'is_open')],
    )(lambda n_clicks, continue_clicks, cancel_clicks, selected_segment_value, is_open: bool(is_open) or (selected_segment_value is not None and bool(n_clicks)))

    dash_app.callback(
        [Output('segment-selection-store', 'data'),
         Output('segment-warning-modal', 'is_open', allow_duplicate=True)],
        [Input('segment-warning-continue-btn', 'n_clicks'),
         Input('segment-warning-cancel-btn', 'n_clicks')],
        [State('selected-segment-dropdown', 'value'),
         State('segment-selection-store', 'data')],
        prevent_initial_call=True,
    )(lambda continue_clicks, cancel_clicks, selected_segment_value, current_store: (
        {"segment_index": coerce_segment_index(selected_segment_value), "accepted": True}, False
    ) if continue_clicks else ({"segment_index": coerce_segment_index(current_store.get("segment_index") if isinstance(current_store, dict) else None), "accepted": False}, False))

    dash_app.callback(
        [Output('ssa-window-slider', 'marks'),
         Output('ssa-window-slider', 'value'),
         Output('ssa-window-slider', 'min'),
         Output('ssa-window-slider', 'max'),
         Output('ssa-window-slider', 'step')],
        [Input('step-tracker', 'data'),
         Input('uploaded-file-store', 'data'),
         Input('refined-window-store', 'data'),
         Input('window-selection-method', 'value')],
    )(configure_redo_slider)

    dash_app.callback(
        Output('window-selection-comparison-plot', 'figure'),
        [Input('step-tracker', 'data'),
         Input('uploaded-file-store', 'data'),
         Input('refined-window-store', 'data'),
         Input('ssa-window-slider', 'value')],
    )(build_window_selection_comparison_figure)

    dash_app.callback(
        Output('window-selection-modal', 'is_open'),
        [Input('window-selection-diagnostics-btn', 'n_clicks'),
         Input('window-selection-modal-close-btn', 'n_clicks')],
        State('window-selection-modal', 'is_open'),
    )(toggle_window_selection_modal)

    dash_app.callback(
        Output('window-selection-summary', 'children'),
        [Input('step-tracker', 'data'),
         Input('uploaded-file-store', 'data'),
         Input('ssa-window-slider', 'value'),
         Input('window-selection-method', 'value')],
    )(update_window_selection_summary)

    dash_app.callback(
        Output('apply-grouping-trigger', 'data'),
        Input('apply-components-btn', 'n_clicks'),
        prevent_initial_call=True,
    )(relay_apply_grouping)

    dash_app.callback(
        Output('loess-fraction-store', 'data'),
        Input('loess-fraction-slider', 'value'),
        prevent_initial_call=True,
    )(relay_loess_fraction)

    dash_app.callback(
        [Output('eigen-plot', 'figure'),
         Output('eigenvector-plot', 'src'),
         Output('noisy-series-store', 'data'),
         Output('noisy-series-message', 'children'),
         Output('apply-components-btn', 'disabled'),
         Output('suggested-grouping-table', 'children'),
         Output('component-name-1', 'value'),
         Output('component-list-1', 'value'),
         Output('component-name-2', 'value'),
         Output('component-list-2', 'value'),
         Output('component-name-3', 'value'),
         Output('component-list-3', 'value'),
         Output('refined-window-store', 'data')],
        [Input('step-tracker', 'data'),
         Input('analysis-complete-store', 'data'),
         Input('uploaded-file-store', 'data'),
         Input('ssa-window-slider', 'value'),
         Input('window-selection-method', 'value')],
        prevent_initial_call=True,
    )(update_ssa_plots)

    dash_app.callback(
        [Output('component-validation-error', 'children'),
         Output('signal-reconstruction-plot', 'figure'),
         Output('change-point-plot', 'figure'),
         Output('wcorr-plot', 'src'),
         Output('reconstruction-metadata', 'children'),
         Output('noise-kde-plot', 'figure'),
         Output('analysis-complete-store', 'data'),
         Output('dw-valid-store', 'data')],
        [Input('apply-grouping-trigger', 'data'),
         Input('uploaded-file-store', 'data')],
        [State('component-name-1', 'value'), State('component-list-1', 'value'),
         State('component-name-2', 'value'), State('component-list-2', 'value'),
         State('component-name-3', 'value'), State('component-list-3', 'value'),
         State('ssa-window-slider', 'value'),
         State('refined-window-store', 'data'),
         State('loess-fraction-store', 'data')],
        prevent_initial_call=True,
    )(validate_components)

    dash_app.callback(
        Output('verification-plot', 'figure'),
        [Input('loess-fraction-store', 'data'),
         Input('analysis-complete-store', 'data'),
         Input('uploaded-file-store', 'data')],
        prevent_initial_call=True,
    )(update_verification_plot)

    dash_app.callback(
        [Output('ssa-aic-formulas', 'children'),
         Output('variance-explained-rank-plot', 'figure'),
         Output('noise-variance-rank-plot', 'figure')],
        [Input('step-tracker', 'data'),
         Input('uploaded-file-store', 'data'),
         Input('analysis-complete-store', 'data')],
    )(update_logging_rank_diagnostics)

    dash_app.callback(
        Output('observation-text', 'value'),
        [Input('step-tracker', 'data'),
         Input('analysis-complete-store', 'data'),
         Input('uploaded-file-store', 'data')],
        prevent_initial_call=True,
    )(populate_observation_text)

    dash_app.callback(
        Output('save-kb-modal', 'is_open'),
        [Input('save-to-kb-btn', 'n_clicks'),
         Input('save-kb-cancel-btn', 'n_clicks'),
         Input('save-kb-confirm-btn', 'n_clicks')],
        State('save-kb-modal', 'is_open'),
        prevent_initial_call=True,
    )(toggle_save_kb_modal)

    dash_app.callback(
        [Output('kb-save-dir-store', 'data', allow_duplicate=True),
         Output('kb-save-filename-store', 'data', allow_duplicate=True),
         Output('save-kb-feedback', 'children', allow_duplicate=True),
         Output('save-kb-confirm-btn', 'disabled')],
        [Input('save-dir-input', 'value'),
         Input('save-filename-input', 'value')],
        prevent_initial_call=True,
    )(sync_kb_location_state)

    dash_app.callback(
        [Output('save-dir-input', 'value'),
         Output('save-filename-input', 'value')],
        Input('save-kb-modal', 'is_open'),
        [State('kb-save-dir-store', 'data'),
         State('kb-save-filename-store', 'data')],
        prevent_initial_call=True,
    )(hydrate_kb_location_fields)

    dash_app.callback(
        Output('save-kb-feedback', 'children'),
        Input('save-kb-confirm-btn', 'n_clicks'),
        [State('observation-text', 'value'),
         State('save-dir-input', 'value'),
         State('save-filename-input', 'value')],
        prevent_initial_call=True,
    )(save_kmds_knowledge_base)

    dash_app.callback(
        Output('export-components-btn', 'disabled'),
        Input('dw-valid-store', 'data'),
        prevent_initial_call=True,
    )(lambda dw_valid: not dw_valid)

    dash_app.callback(
        Output('download-components-csv', 'data'),
        Input('export-components-btn', 'n_clicks'),
        prevent_initial_call=True,
    )(export_components_to_csv)


def export_components_to_csv(n_clicks: int) -> dict:
    """Export the decomposed components (Trend, Seasonality, Noise) to CSV.
    
    Returns:
        Dictionary with base64-encoded CSV data for download.
    """
    global ssa_obj, series
    
    if ssa_obj is None or series is None or not hasattr(ssa_obj, "_group_signals"):
        return None
    
    try:
        # Prepare data for export
        data_dict = {"timestamp": series.index}
        
        # Add reconstructed components
        for group_name, signal in ssa_obj._group_signals.items():
            # Capitalize group name for display
            display_name = group_name.capitalize()
            data_dict[display_name] = signal.values
        
        # Create DataFrame
        df = pd.DataFrame(data_dict)
        
        # Convert to CSV string
        csv_string = df.to_csv(index=False)
        
        return dict(
            content=csv_string,
            filename="ssa_components.csv"
        )
    except Exception as e:
        print(f"Error exporting components: {str(e)}", flush=True)
        return None


def create_app() -> dash.Dash:
    """Create and configure the Dash app instance."""
    dash_app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
    dash_app.layout = build_app_layout()
    register_callbacks(dash_app)
    return dash_app


app = create_app()


def main() -> None:
    """Run the installed Dash application via the console script entrypoint."""
    host = os.getenv("TSEDA_HOST", "127.0.0.1")
    port = int(os.getenv("TSEDA_PORT", "8050"))
    debug = os.getenv("TSEDA_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
