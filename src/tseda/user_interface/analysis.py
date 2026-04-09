"""Reusable layout and figure helpers for the Dash time-series workflow UI."""

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html


PLACEHOLDER_TEXT = {
    "preview": "Data Preview Table Placeholder",
    "kde": "KDE Plot Placeholder",
    "box": "Box Plot Placeholder",
    "scatter": "Scatter Plot Placeholder",
    "acf": "ACF Plot Placeholder",
    "pacf": "PACF Plot Placeholder",
}


def placeholder_block(text: str) -> html.Div:
    """Create a standard light placeholder block used during empty-state rendering."""
    return html.Div(text, className="p-3 border bg-light")


def assessment_placeholders() -> tuple[html.Div, html.Div, html.Div, html.Div, html.Div, html.Div]:
    """Return the six standard Step-1 placeholders in callback output order."""
    return (
        placeholder_block(PLACEHOLDER_TEXT["preview"]),
        placeholder_block(PLACEHOLDER_TEXT["kde"]),
        placeholder_block(PLACEHOLDER_TEXT["box"]),
        placeholder_block(PLACEHOLDER_TEXT["scatter"]),
        placeholder_block(PLACEHOLDER_TEXT["acf"]),
        placeholder_block(PLACEHOLDER_TEXT["pacf"]),
    )


def empty_figure(title: str) -> go.Figure:
    """Create a standard empty figure with a title and hidden grid."""
    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
    )
    return fig


def build_initial_assessment_layout() -> html.Div:
    """Create the Step-1 Initial Assessment layout."""
    return html.Div([
        html.H3("Initial Assessment of Time Series"),
        dbc.Row([
            dbc.Col(html.Div([
                dcc.Upload(
                    id="upload-data",
                    children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
                    style={
                        "width": "100%",
                        "height": "60px",
                        "lineHeight": "60px",
                        "borderWidth": "1px",
                        "borderStyle": "dashed",
                        "textAlign": "center",
                    },
                ),
                dbc.Button("Clear Uploaded File", id="clear-upload-btn", color="danger", className="mt-3"),
                html.Div(id="upload-error-message", className="mt-3"),
            ]), width=4),
            dbc.Col(html.Div(PLACEHOLDER_TEXT["preview"], id="data-preview-container", className="p-3 border bg-light"), width=8),
        ]),
        dbc.Row([
            dbc.Col(html.Div([
                dbc.Checklist(
                    options=[{"label": "Show KDE overlay", "value": "show"}],
                    value=["show"],
                    id="kde-overlay-toggle",
                    switch=True,
                    inline=True,
                ),
                html.Div([
                    dbc.Label("Histogram bin count", html_for="hist-bin-count-slider", className="mt-3"),
                    dcc.Slider(
                        id="hist-bin-count-slider",
                        min=0,
                        max=100,
                        step=1,
                        value=0,
                        marks={0: "Auto", 5: "5", 10: "10", 20: "20", 40: "40", 80: "80"},
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                    html.Small("Use 0 for automatic bin sizing based on data spread.", className="text-muted"),
                ]),
            ]), width=12),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Kernel Density Estimate", className="mb-0")),
                dbc.CardBody(html.Div(PLACEHOLDER_TEXT["kde"], id="kde-plot-container", className="p-3 bg-light")),
            ]), width=6),
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Box Plot", className="mb-0")),
                dbc.CardBody(html.Div(PLACEHOLDER_TEXT["box"], id="box-plot-container", className="p-3 bg-light")),
            ]), width=6),
        ], className="mt-4"),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Series Scatter Plot", className="mb-0")),
                dbc.CardBody(html.Div(PLACEHOLDER_TEXT["scatter"], id="scatter-plot-container", className="p-3 bg-light")),
            ]), width=12),
        ], className="mt-4"),
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Autocorrelation (ACF)", className="mb-0")),
                dbc.CardBody(html.Div(PLACEHOLDER_TEXT["acf"], id="acf-plot-container", className="p-3 bg-light")),
            ]), width=6),
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Partial Autocorrelation (PACF)", className="mb-0")),
                dbc.CardBody(html.Div(PLACEHOLDER_TEXT["pacf"], id="pacf-plot-container", className="p-3 bg-light")),
            ]), width=6),
        ], className="mt-4"),
    ])


def build_logging_layout() -> html.Div:
    """Create the Step-3 Observation Logging layout."""
    return html.Div([
        html.H3("Observation Logging"),
        dbc.Card([
            dbc.CardHeader(html.H5("SSA Rank Diagnostics", className="mb-0")),
            dbc.CardBody([
                html.Div(id="ssa-aic-formulas", className="mb-3"),
                dbc.Row([
                    dbc.Col(dcc.Graph(id="variance-explained-rank-plot", style={"height": "320px"}), width=6),
                    dbc.Col(dcc.Graph(id="noise-variance-rank-plot", style={"height": "320px"}), width=6),
                ]),
            ]),
        ], className="mb-4"),
        dbc.Textarea(id="observation-text", placeholder="Enter your expert observations here...", style={"height": "200px"}),
        dbc.Button("Finalize & Save Report", color="success", className="mt-3"),
    ])


def build_main_layout(assessment_layout: html.Div, decomposition_layout: html.Div, logging_layout: html.Div) -> dbc.Container:
    """Compose the full multi-step app shell from per-step layout factories."""
    return dbc.Container([
        dcc.Store(id="step-tracker", data=1),
        dcc.Store(id="analysis-complete-store", data=False),
        dcc.Store(id="uploaded-file-store", storage_type="memory", data=None),
        dcc.Store(id="apply-grouping-trigger", data=0),
        dcc.Store(id="loess-fraction-store", data=0.05),
        dcc.Store(id="noisy-series-store", data=False),
        html.H1("Time Series Explorer", className="text-center my-4"),
        dbc.Progress([
            dbc.Progress(value=33, label="1. Assessment", id="p1", color="primary", bar=True),
            dbc.Progress(value=0, label="2. Analysis", id="p2", color="secondary", bar=True),
            dbc.Progress(value=0, label="3. Logging", id="p3", color="secondary", bar=True),
        ], className="mb-4", style={"height": "30px"}),
        html.Div(id="step1-container", children=assessment_layout, style={"display": "block"}),
        html.Div(id="step2-container", children=decomposition_layout, style={"display": "none"}),
        html.Div(id="step3-container", children=logging_layout, style={"display": "none"}),
        dbc.Row([
            dbc.Col(dbc.Button("← Previous", id="prev-btn", color="secondary", disabled=True), width="auto"),
            dbc.Col(dbc.Button("Next Step →", id="next-btn", color="primary"), width="auto"),
        ], justify="center", className="mt-5"),
    ], fluid=True)
