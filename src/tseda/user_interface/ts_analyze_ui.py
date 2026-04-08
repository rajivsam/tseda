import base64
import io

import numpy as np
from scipy import stats
import matplotlib
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from tseda.series_stats.sampling_prop import SamplingProp
from tseda.user_interface.components.initial_eval_components import create_summary_table, create_kde_plot, create_box_plot, create_scatter_plot, create_acf_plot, create_pacf_plot, create_ssa_decomposition_plot
from tseda.user_interface.components.analysis_assessment import analysis_layout
from tseda.decomposition.ssa_decomposition import SSADecomposition
from tseda.decomposition.ssa_result_summary import SSAResultSummary

# Use a non-interactive backend since figures are rendered to buffers in callbacks.
matplotlib.use('Agg')

# Configuration
MAX_FILE_LINES = 2000  # Configurable maximum number of lines in uploaded files

series = None
window_size = 0
ssa_obj = None

# Initialize the app with a bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)

# --- 1. Step Layouts ---

def initial_assessment_layout():
    return html.Div([
        html.H3("Step 1: Initial Assessment"),
        dbc.Row([
            dbc.Col(html.Div([
                dcc.Upload(
                    id='upload-data',
                    children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
                    style={'width': '100%', 'height': '60px', 'lineHeight': '60px', 'borderWidth': '1px', 'borderStyle': 'dashed', 'textAlign': 'center'}
                ),
                dbc.Button("Clear Uploaded File", id='clear-upload-btn', color='danger', className='mt-3'),
                html.Div(id='upload-error-message', className='mt-3')
            ]), width=4),
            dbc.Col(html.Div("Data Preview Table Placeholder", id='data-preview-container', className="p-3 border bg-light"), width=8),
        ]),
        dbc.Row([
            dbc.Col(html.Div([
                dbc.Checklist(
                    options=[{"label": "Show KDE overlay", "value": "show"}],
                    value=["show"],
                    id='kde-overlay-toggle',
                    switch=True,
                    inline=True
                ),
                html.Div([
                    dbc.Label("Histogram bin count", html_for='hist-bin-count-slider', className='mt-3'),
                    dcc.Slider(
                        id='hist-bin-count-slider',
                        min=0,
                        max=100,
                        step=1,
                        value=0,
                        marks={0: 'Auto', 5: '5', 10: '10', 20: '20', 40: '40', 80: '80'},
                        tooltip={"placement": "bottom", "always_visible": False}
                    ),
                    html.Small('Use 0 for automatic bin sizing based on data spread.', className='text-muted')
                ])
            ]), width=12)
        ], className='mb-4'),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Kernel Density Estimate", className="mb-0")),
                dbc.CardBody(html.Div("KDE Plot Placeholder", id='kde-plot-container', className="p-3 bg-light"))
            ]), width=6),
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Box Plot", className="mb-0")),
                dbc.CardBody(html.Div("Box Plot Placeholder", id='box-plot-container', className="p-3 bg-light"))
            ]), width=6),
        ], className="mt-4"),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Series Scatter Plot", className="mb-0")),
                dbc.CardBody(html.Div("Scatter Plot Placeholder", id='scatter-plot-container', className="p-3 bg-light"))
            ]), width=12),
        ], className="mt-4"),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Autocorrelation (ACF)", className="mb-0")),
                dbc.CardBody(html.Div("ACF Plot Placeholder", id='acf-plot-container', className="p-3 bg-light"))
            ]), width=6),
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Partial Autocorrelation (PACF)", className="mb-0")),
                dbc.CardBody(html.Div("PACF Plot Placeholder", id='pacf-plot-container', className="p-3 bg-light"))
            ]), width=6),
        ], className="mt-4")
    ])

def logging_layout():
    return html.Div([
        html.H3("Step 3: Observation Logging"),
        dbc.Card([
            dbc.CardHeader(html.H5("SSA Rank Diagnostics", className="mb-0")),
            dbc.CardBody([
                html.Div(id='ssa-aic-formulas', className='mb-3'),
                dbc.Row([
                    dbc.Col(dcc.Graph(id='variance-explained-rank-plot', style={"height": "320px"}), width=6),
                    dbc.Col(dcc.Graph(id='noise-variance-rank-plot', style={"height": "320px"}), width=6),
                ])
            ])
        ], className='mb-4'),
        dbc.Textarea(id='observation-text', placeholder="Enter your expert observations here...", style={'height': '200px'}),
        dbc.Button("Finalize & Save Report", color="success", className="mt-3")
    ])

# --- 2. Main App Layout ---

app.layout = dbc.Container([
    # Store to track current step (1, 2, or 3)
    dcc.Store(id='step-tracker', data=1),
    # Store to indicate analysis completion (set only after Apply Grouping succeeds)
    dcc.Store(id='analysis-complete-store', data=False),
    # Memory store for the uploaded file contents and filename (avoids session storage quota limits)
    dcc.Store(id='uploaded-file-store', storage_type='memory', data=None),
    # Bridge stores: relay dynamic Step-2 component values into permanent IDs so that
    # global callbacks never reference IDs that exist only in the dynamic layout.
    dcc.Store(id='apply-grouping-trigger', data=0),
    dcc.Store(id='loess-fraction-store', data=0.05),
    
    html.H1("Data Analysis Workflow", className="text-center my-4"),

    # Progress Indicator
    dbc.Progress([
        dbc.Progress(value=33, label="1. Assessment", id="p1", color="primary", bar=True),
        dbc.Progress(value=0, label="2. Analysis", id="p2", color="secondary", bar=True),
        dbc.Progress(value=0, label="3. Logging", id="p3", color="secondary", bar=True),
    ], className="mb-4", style={"height": "30px"}),

    # All three step containers are always present in the DOM.
    # Dash 4.x validates all Output/Input IDs against the initial DOM, so keeping
    # everything rendered (toggling display) avoids all reference errors at startup.
    html.Div(id='step1-container', children=initial_assessment_layout(), style={'display': 'block'}),
    html.Div(id='step2-container', children=analysis_layout(), style={'display': 'none'}),
    html.Div(id='step3-container', children=logging_layout(), style={'display': 'none'}),

    # Navigation Buttons
    dbc.Row([
        dbc.Col(dbc.Button("← Previous", id="prev-btn", color="secondary", disabled=True), width="auto"),
        dbc.Col(dbc.Button("Next Step →", id="next-btn", color="primary"), width="auto"),
    ], justify="center", className="mt-5"),

], fluid=True)

# --- 3. Callbacks for Navigation ---

@app.callback(
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
    [State('step-tracker', 'data')]
)
def navigate_steps(next_clicks, prev_clicks, analysis_complete, current_step):
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
        next_disabled = (current_step >= 3) or (current_step == 2 and not bool(analysis_complete))
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
    next_disabled = (current_step >= 3) or (current_step == 2 and not bool(analysis_complete))

    return s1, s2, s3, current_step, prev_disabled, next_disabled, p2_val, p3_val



def parse_upload(contents, filename):
    global series

    if contents is None:
        series = None
        return

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    if filename.lower().endswith('.csv'):
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    elif filename.lower().endswith(('.xls', '.xlsx')):
        df = pd.read_excel(io.BytesIO(decoded))
    else:
        raise ValueError('Unsupported file format. Please upload a CSV or Excel file.')
    
    # Check if file has too many lines
    if len(df) > MAX_FILE_LINES:
        series = None
        raise ValueError(f'File has {len(df)} rows, but maximum allowed is {MAX_FILE_LINES} rows. Please upload a smaller file.')

    if df.shape[1] < 2:
        raise ValueError('Uploaded file must contain at least two columns: timestamp and value.')

    # Use the first column as the timestamp index and the second column as the series values.
    try:
        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
    except Exception as exc:
        raise ValueError('Could not parse the first column as datetime.') from exc

    df = df.set_index(df.columns[0])
    series = df.iloc[:, 0]

    if not pd.api.types.is_numeric_dtype(series):
        series = pd.to_numeric(series, errors='coerce')

    if series.isna().all():
        raise ValueError('The selected value column does not contain numeric data.')


@app.callback(
    [Output('uploaded-file-store', 'data'),
     Output('upload-error-message', 'children'),
     Output('analysis-complete-store', 'data', allow_duplicate=True)],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    Input('clear-upload-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def store_uploaded_file(contents, filename, clear_clicks):
    global series, window_size, ssa_obj
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger_id == 'clear-upload-btn':
        series = None
        window_size = 0
        ssa_obj = None
        return None, None, False

    if contents is None or filename is None:
        series = None
        window_size = 0
        ssa_obj = None
        return None, None, False
    
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
        return {'contents': contents, 'filename': filename}, None, False
    except ValueError as e:
        series = None
        window_size = 0
        ssa_obj = None
        return None, dbc.Alert(str(e), color="danger", className="mt-2"), False


@app.callback(
    [Output('data-preview-container', 'children'),
     Output('kde-plot-container', 'children'),
     Output('box-plot-container', 'children'),
     Output('scatter-plot-container', 'children'),
     Output('acf-plot-container', 'children'),
     Output('pacf-plot-container', 'children')],
    [
        Input('uploaded-file-store', 'data'),
        Input('kde-overlay-toggle', 'value'),
        Input('hist-bin-count-slider', 'value')
    ]
)
def update_summary_table(uploaded_file, kde_toggle, hist_bin_count):
    global series, window_size, ssa_obj

    if not uploaded_file:
        series = None
        window_size = 0
        ssa_obj = None
        placeholder = html.Div('Data Preview Table Placeholder', className='p-3 border bg-light')
        return (
            placeholder,
            html.Div('KDE Plot Placeholder', className='p-3 border bg-light'),
            html.Div('Box Plot Placeholder', className='p-3 border bg-light'),
            html.Div('Scatter Plot Placeholder', className='p-3 border bg-light'),
            html.Div('ACF Plot Placeholder', className='p-3 border bg-light'),
            html.Div('PACF Plot Placeholder', className='p-3 border bg-light')
        )

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
    except Exception as err:
        series = None
        window_size = 0
        ssa_obj = None
        # Clear error messages and show placeholders
        placeholder = html.Div('Data Preview Table Placeholder', className='p-3 border bg-light')
        return (
            placeholder,
            html.Div('KDE Plot Placeholder', className='p-3 border bg-light'),
            html.Div('Box Plot Placeholder', className='p-3 border bg-light'),
            html.Div('Scatter Plot Placeholder', className='p-3 border bg-light'),
            html.Div('ACF Plot Placeholder', className='p-3 border bg-light'),
            html.Div('PACF Plot Placeholder', className='p-3 border bg-light')
        )


@app.callback(
    [Output('ssa-window-slider', 'marks'),
     Output('ssa-window-slider', 'value'),
     Output('ssa-window-slider', 'min'),
     Output('ssa-window-slider', 'max'),
     Output('ssa-window-slider', 'step')],
    [Input('step-tracker', 'data'),
     Input('uploaded-file-store', 'data')]
)
def configure_redo_slider(current_step, uploaded_file):
    """Configure valid redo SSA window values as integer multiples of the default window."""
    global series, window_size

    if current_step != 2 or series is None or window_size <= 0:
        return {}, 0, 0, 0, None

    series_length = len(series)
    if series_length <= 0:
        return {}, 0, 0, 0, None

    # Stop at the next valid multiple at or above N/4 (e.g., N=422, W=12 => max=108).
    max_k = (series_length + (4 * window_size) - 1) // (4 * window_size)
    valid_windows = [k * window_size for k in range(1, max_k + 1)]

    if not valid_windows:
        return {}, 0, 0, 0, None

    marks = {val: str(val) for val in valid_windows}
    return marks, valid_windows[0], valid_windows[0], valid_windows[-1], None


@app.callback(
    Output('apply-grouping-trigger', 'data'),
    Input('apply-components-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def relay_apply_grouping(n_clicks):
    """Relay Apply Grouping button clicks into a permanent store."""
    return n_clicks or 0


@app.callback(
    Output('loess-fraction-store', 'data'),
    Input('loess-fraction-slider', 'value'),
    prevent_initial_call=True,
)
def relay_loess_fraction(value):
    """Relay loess slider value into a permanent store."""
    return value if value is not None else 0.05


@app.callback(
    [Output('eigen-plot', 'figure'),
     Output('eigenvector-plot', 'src')],
    [Input('step-tracker', 'data'),
     Input('analysis-complete-store', 'data'),
     Input('uploaded-file-store', 'data')],
    State('ssa-window-slider', 'value'),
    prevent_initial_call=True,
)
def update_ssa_plots(current_step, analysis_complete, uploaded_file, slider_window_size):
    """Generate SSA eigenvalue and eigenvector plots."""
    global series, window_size, ssa_obj
    
    if current_step != 2 or series is None or window_size <= 0:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="No data available",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False)
        )
        return empty_fig, ""
    
    try:
        if ssa_obj is None:
            ssa_obj = SSADecomposition(series, window_size)
        
        eigen_fig = ssa_obj.eigenplot()
        
        mpl_fig = ssa_obj.eigen_vector_plot()
        buf = io.BytesIO()
        mpl_fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        import matplotlib
        matplotlib.pyplot.close(mpl_fig)
        
        return eigen_fig, f"data:image/png;base64,{img_b64}"
        
    except Exception as err:
        empty_fig = go.Figure()
        empty_fig.update_layout(title=f"Error: {str(err)[:80]}")
        return empty_fig, ""


@app.callback(
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
)
def validate_components(apply_trigger, uploaded_file, name1, list1, name2, list2, name3, list3, slider_window_size, loess_fraction):
    """Validate component inputs."""
    global series, window_size, ssa_obj

    empty_fig = go.Figure()
    empty_fig.update_layout(
        title="No reconstruction available",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False)
    )
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

    def parse_group_list(comp_str, label, is_noise):
        if not comp_str or comp_str.strip() == '':
            return []

        tokens = [token.strip() for token in comp_str.split(',') if token.strip()]
        if not tokens:
            return []

        if is_noise and len(tokens) == 1 and tokens[0] == '*':
            return '*'

        if '*' in tokens:
            raise ValueError(
                f'"{label}": wildcard * is allowed only as the entire Noise list.'
            )

        try:
            components = [int(token) for token in tokens]
        except ValueError as exc:
            raise ValueError(
                f'"{label}": component list must contain comma-separated integers only (e.g., 0,1,2).'
            ) from exc

        for comp in components:
            if comp < 0 or comp >= window_size:
                raise ValueError(f'"{label}": component {comp} is out of range [0, {window_size - 1}]')

        return components

    try:
        recon_dict = {}
        used_non_noise_indices = set()
        noise_wildcard_label = None

        for name, comp_str in rows:
            if not name or not name.strip():
                continue

            label = name.strip()
            is_noise = label.lower() == "noise"

            parsed_value = parse_group_list(comp_str, label, is_noise)
            if parsed_value == '*':
                if noise_wildcard_label is not None:
                    raise ValueError("Noise wildcard can only be specified once.")
                noise_wildcard_label = label
                continue

            if parsed_value:
                recon_dict[label] = parsed_value
                if not is_noise:
                    used_non_noise_indices.update(parsed_value)

        if noise_wildcard_label is not None:
            recon_dict[noise_wildcard_label] = [
                idx for idx in range(window_size) if idx not in used_non_noise_indices
            ]

        all_indices = [idx for indices in recon_dict.values() for idx in indices]

        if len(set(all_indices)) != len(all_indices):
            return dbc.Alert("Error: Overlapping components detected. Each component can only be assigned once.", color="danger"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False

        if recon_dict:
            print(f"[DEBUG] Reconstruction groups: {recon_dict}", flush=True)
            if ssa_obj is None:
                ssa_obj = SSADecomposition(series, window_size)

            ssa_obj.set_reconstruction(recon_dict)

            signal_fig = ssa_obj.signal_reconstruction_plot()
            change_point_fig = ssa_obj.change_point_plot()
            wcorr_mpl_fig = ssa_obj.wcorr_plot()

            dw = ssa_obj._durbin_watson
            dw_text = f"{dw:.4f}" if dw is not None else "N/A"

            variation_items = [
                html.Li([
                    html.Strong(f"Variation Associated with {group_name} (%): "),
                    f"{ssa_obj.explained_variance_by_group(group_name):.2f}",
                ])
                for group_name in recon_dict.keys()
            ]

            metadata = html.Div([
                html.Ul([
                    *variation_items,
                    html.Li([html.Strong("Durbin-Watson Statistic: "), dw_text]),
                ]),
                html.Small(
                    "A Durbin-Watson value between 1.5 and 2.5 implies that the noise is uncorrelated.",
                    className="text-muted"
                ),
            ])

            noise_signal = ssa_obj.get_reconstructed_series("noise")
            if noise_signal is not None:
                noise_data = noise_signal.dropna().values.astype(float)
                kde_estimator = stats.gaussian_kde(noise_data)
                xs = np.linspace(noise_data.min(), noise_data.max(), 300)
                ys = kde_estimator(xs)
                noise_kde_fig = go.Figure()
                noise_kde_fig.add_trace(go.Scatter(
                    x=xs, y=ys, mode='lines', name='Noise KDE',
                    line=dict(color='steelblue')
                ))
                noise_kde_fig.update_layout(
                    title="Noise Kernel Density Estimate",
                    xaxis_title="Value",
                    yaxis_title="Density",
                )
            else:
                noise_kde_fig = empty_fig

            buf = io.BytesIO()
            wcorr_mpl_fig.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            wcorr_b64 = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()
            import matplotlib
            matplotlib.pyplot.close(wcorr_mpl_fig)

            if window_changed:
                status_alert = dbc.Alert(f"SSA updated to window size {window_size} and components applied successfully!", color="success")
            else:
                status_alert = dbc.Alert("Components applied successfully!", color="success")

            return status_alert, signal_fig, change_point_fig, f"data:image/png;base64,{wcorr_b64}", metadata, noise_kde_fig, True

        return dbc.Alert("No valid component groups were provided.", color="warning"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False

    except ValueError as e:
        return dbc.Alert(f"Validation error: {str(e)}", color="danger"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger"), empty_fig, empty_fig, "", empty_metadata, empty_fig, False


@app.callback(
    Output('verification-plot', 'figure'),
    [Input('loess-fraction-store', 'data'),
    Input('analysis-complete-store', 'data'),
    Input('uploaded-file-store', 'data')],
    prevent_initial_call=True,
)
def update_verification_plot(loess_fraction, analysis_complete, uploaded_file):
    """Render LOESS verification plot after grouping is applied and when slider changes."""
    global ssa_obj

    empty_fig = go.Figure()
    empty_fig.update_layout(
        title="Verification plot will appear after SSA is initialized",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False)
    )

    if uploaded_file is None or ssa_obj is None or not hasattr(ssa_obj, "_recon"):
        return empty_fig

    fraction = float(loess_fraction) if loess_fraction is not None else 0.05
    fraction = max(0.05, min(0.5, fraction))
    return ssa_obj.loess_smother(fraction)


@app.callback(
    [Output('ssa-aic-formulas', 'children'),
     Output('variance-explained-rank-plot', 'figure'),
    Output('noise-variance-rank-plot', 'figure')],
    [Input('step-tracker', 'data'),
    Input('uploaded-file-store', 'data'),
    Input('analysis-complete-store', 'data')]
)
def update_logging_rank_diagnostics(current_step, uploaded_file, analysis_complete):
    """Render SSA rank diagnostics and AIC expressions in the logging panel."""
    global series, window_size

    def empty_fig(title):
        fig = go.Figure()
        fig.update_layout(
            title=title,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False),
        )
        return fig

    blank_formula = html.Div(
        "Rank-based AIC formulas and plots will appear here after SSA is available.",
        className='text-muted'
    )
    empty_1 = empty_fig("Variance Explained vs Rank")
    empty_2 = empty_fig("Noise Variance vs Rank")

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


@app.callback(
    Output('observation-text', 'value'),
    [Input('step-tracker', 'data'),
     Input('analysis-complete-store', 'data'),
     Input('uploaded-file-store', 'data')],
    prevent_initial_call=True,
)
def populate_observation_text(current_step, analysis_complete, uploaded_file):
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


if __name__ == '__main__':
    app.run(debug=True)
