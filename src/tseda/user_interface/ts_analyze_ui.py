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
    compute_window_slider_config,
    format_component_indices,
    matplotlib_figure_to_data_url,
    parse_reconstruction_groups,
    parse_uploaded_series,
)
from tseda.decomposition.ssa_decomposition import SSADecomposition
from tseda.decomposition.ssa_result_summary import SSAResultSummary
from kmds.ontology.kmds_ontology import *
from kmds.tagging.tag_types import ExploratoryTags
from kmds.ontology.intent_types import IntentType

# Use a non-interactive backend since figures are rendered to buffers in callbacks.
matplotlib.use('Agg')

# Configuration
MAX_FILE_LINES = 2000  # Configurable maximum number of lines in uploaded files

series: pd.Series | None = None
window_size: int = 0
ssa_obj: SSADecomposition | None = None

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
) -> tuple[dict[str, str] | Any, dict[str, str] | Any, dict[str, str] | Any, int, bool, bool, int | Any, int | Any]:
    """Navigate the three-step workflow and update progress/navigation state."""
    # Determine which button was clicked
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = None
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # When only the analysis-complete-store changed (Apply Grouping fired), only update
    # button states — do not change which step is visible.
    if button_id == 'analysis-complete-store':
        prev_disabled = (current_step == 1)
        next_disabled = (current_step >= 3)
        return dash.no_update, dash.no_update, dash.no_update, current_step, prev_disabled, next_disabled, dash.no_update, dash.no_update

    # Update step logic
    if button_id == 'next-btn' and current_step < 3:
        # Step 3 is only allowed after analysis is completed via Apply Grouping.
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
) -> tuple[dict[str, str] | None, Any | None, bool, None, None]:
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
        return None, None, False, None, None

    if contents is None or filename is None:
        series = None
        window_size = 0
        ssa_obj = None
        return None, None, False, None, None
    
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
        return {'contents': contents, 'filename': filename}, None, False, dash.no_update, dash.no_update
    except ValueError as e:
        series = None
        window_size = 0
        ssa_obj = None
        return None, dbc.Alert(str(e), color="danger", className="mt-2"), False, dash.no_update, dash.no_update


def update_summary_table(
    uploaded_file: dict[str, str] | None,
    kde_toggle: list[str] | None,
    hist_bin_count: int | None,
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

        sampling_props = SamplingProp(series)
        window_size = sampling_props._freq_window if sampling_props._freq_window is not None else 0
        ssa_obj = None
        kde_fig = create_kde_plot(series, show_kde=show_kde, bin_count=bin_count)
        box_fig = create_box_plot(series)
        scatter_fig = create_scatter_plot(series)
        acf_fig = create_acf_plot(series, lags=40)
        pacf_fig = create_pacf_plot(series, lags=40)
        
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


def configure_redo_slider(
    current_step: int,
    uploaded_file: dict[str, str] | None,
) -> tuple[dict[int, str], int, int, int, None]:
    """Configure valid redo SSA window values as integer multiples of the default window."""
    global series, window_size

    series_length = len(series) if series is not None else 0
    return compute_window_slider_config(
        current_step=current_step,
        series_length=series_length,
        default_window_size=window_size,
    )


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
) -> tuple[go.Figure, str, bool, Any, bool, Any, str | Any, str | Any, str | Any, str | Any, str | Any, str | Any]:
    """Generate SSA plots and series-suitability state for grouping actions."""
    global series, window_size, ssa_obj

    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    empty_suggestions = ("", "", "", "", "", "")
    preserve_suggestions = (dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update)
    
    if current_step != 2 or series is None or window_size <= 0:
        empty_fig = empty_figure("No data available")
        return empty_fig, "", False, None, False, "", *empty_suggestions
    
    try:
        selected_window_size = int(slider_window_size) if slider_window_size is not None and int(slider_window_size) > 0 else window_size

        if ssa_obj is None or getattr(ssa_obj, "_window", None) != selected_window_size:
            ssa_obj = SSADecomposition(series, selected_window_size)
            # Keep the global in sync so validate_components does not rebuild SSA
            # unnecessarily when the user clicks Apply Grouping after moving the slider.
            window_size = selected_window_size

        eigen_fig = ssa_obj.eigenplot()
        
        mpl_fig = ssa_obj.eigen_vector_plot()
        img_src = matplotlib_figure_to_data_url(mpl_fig)
        import matplotlib
        matplotlib.pyplot.close(mpl_fig)

        # Flag series as noisy when leading SSA structure is too weak.
        eigenvalues = np.asarray(getattr(ssa_obj, "_eigenvalues", []), dtype=float)
        total_var = float(np.sum(eigenvalues)) if eigenvalues.size > 0 else 0.0
        first_two_ratio = (float(np.sum(eigenvalues[:2])) / total_var) if total_var > 0 else 0.0
        noisy_series = first_two_ratio <= 0.20
        ssa_obj._noisy_series = noisy_series

        noisy_message = None
        if noisy_series:
            noisy_message = dbc.Alert(
                "This series is not suitable for this tool: the first two SSA eigenvectors explain 20% or less of total variance.",
                color="warning",
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

        return eigen_fig, img_src, noisy_series, noisy_message, noisy_series, suggestion_children, *suggestion_values
        
    except Exception as err:
        empty_fig = empty_figure(f"Error: {str(err)[:80]}")
        return empty_fig, "", False, None, False, "", *empty_suggestions


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
    loess_fraction: float | None,
) -> tuple[Any, go.Figure, go.Figure, str, Any, go.Figure, bool]:
    """Validate component inputs."""
    global series, window_size, ssa_obj

    empty_fig = empty_figure("No reconstruction available")
    empty_metadata = "Reconstruction metadata will appear here after applying grouping."

    if uploaded_file is None and series is None:
        return "", empty_fig, empty_fig, "", empty_metadata, empty_fig, False

    if series is None and uploaded_file and uploaded_file.get('contents') and uploaded_file.get('filename'):
        try:
            parse_upload(uploaded_file['contents'], uploaded_file['filename'])
        except Exception:
            pass

    if series is None:
        return dbc.Alert("No data loaded. Please upload a file first.", color="warning"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False

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
                return dbc.Alert("No data loaded. Please upload a file first.", color="warning"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False

    selected_window_size = int(slider_window_size) if slider_window_size is not None and int(slider_window_size) > 0 else window_size
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

            return status_alert, signal_fig, change_point_fig, wcorr_src, metadata, noise_kde_fig, True

        return dbc.Alert("No valid component groups were provided.", color="warning"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False

    except ValueError as e:
        err_msg = str(e)
        if err_msg.startswith("Error: Overlapping components detected"):
            return dbc.Alert(err_msg, color="danger"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False
        return dbc.Alert(f"Validation error: {err_msg}", color="danger"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False


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
        [State('step-tracker', 'data')],
    )(navigate_steps)

    dash_app.callback(
        [Output('uploaded-file-store', 'data'),
         Output('upload-error-message', 'children'),
         Output('analysis-complete-store', 'data', allow_duplicate=True),
         Output('kb-save-dir-store', 'data'),
         Output('kb-save-filename-store', 'data')],
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
        ],
    )(update_summary_table)

    dash_app.callback(
        [Output('ssa-window-slider', 'marks'),
         Output('ssa-window-slider', 'value'),
         Output('ssa-window-slider', 'min'),
         Output('ssa-window-slider', 'max'),
         Output('ssa-window-slider', 'step')],
        [Input('step-tracker', 'data'),
         Input('uploaded-file-store', 'data')],
    )(configure_redo_slider)

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
         Output('component-list-3', 'value')],
        [Input('step-tracker', 'data'),
         Input('analysis-complete-store', 'data'),
         Input('uploaded-file-store', 'data'),
         Input('ssa-window-slider', 'value')],
        prevent_initial_call=True,
    )(update_ssa_plots)

    dash_app.callback(
        [Output('component-validation-error', 'children'),
         Output('signal-reconstruction-plot', 'figure'),
         Output('change-point-plot', 'figure'),
         Output('wcorr-plot', 'src'),
         Output('reconstruction-metadata', 'children'),
         Output('noise-kde-plot', 'figure'),
         Output('analysis-complete-store', 'data')],
        [Input('apply-grouping-trigger', 'data'),
         Input('uploaded-file-store', 'data')],
        [State('component-name-1', 'value'), State('component-list-1', 'value'),
         State('component-name-2', 'value'), State('component-list-2', 'value'),
         State('component-name-3', 'value'), State('component-list-3', 'value'),
         State('ssa-window-slider', 'value'),
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
