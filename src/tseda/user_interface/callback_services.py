"""Pure helper functions for Dash callback business logic."""

import base64
import io
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import html
from scipy import stats


def parse_uploaded_series(contents: str | None, filename: str, max_file_lines: int) -> pd.Series | None:
    """Parse and validate uploaded content.

    Args:
        contents: Dash upload payload as a data URL.
        filename: Original uploaded file name.
        max_file_lines: Maximum accepted number of data rows.

    Returns:
        A numeric time-series extracted from the second file column, or None when
        no content is provided.

    Raises:
        ValueError: If format, schema, frequency, or numeric validation fails.
    """
    if contents is None:
        return None

    _, content_string = contents.split(",", 1)
    decoded = base64.b64decode(content_string)

    if filename.lower().endswith(".csv"):
        df = pd.read_csv(io.StringIO(decoded.decode("utf-8-sig")))
    elif filename.lower().endswith((".xls", ".xlsx")):
        df = pd.read_excel(io.BytesIO(decoded))
    else:
        raise ValueError("Unsupported file format. Please upload a CSV or Excel file.")

    if len(df) > max_file_lines:
        raise ValueError(
            f"File has {len(df)} rows, but maximum allowed is {max_file_lines} rows. Please upload a smaller file."
        )

    if df.shape[1] < 2:
        raise ValueError("Uploaded file must contain at least two columns: timestamp and value.")

    if df.isna().any().any():
        raise ValueError(
            "This application requires data without missing values (NA/NaN). "
            "Please fix missing values and try again."
        )

    _col = df.iloc[:, 0]
    _parsed = None
    _last_exc: Exception | None = None
    for _kwargs in [
        {"format": "mixed", "dayfirst": False},
        {"format": "mixed", "dayfirst": True},
        {"infer_datetime_format": True},
        {},
    ]:
        try:
            _parsed = pd.to_datetime(_col, **_kwargs)
            break
        except Exception as _exc:
            _last_exc = _exc
            continue
    if _parsed is None:
        _sample = str(_col.iloc[0]) if len(_col) > 0 else "(empty)"
        raise ValueError(
            f"Could not parse the first column as datetime "
            f"(first value seen: {_sample!r}). "
            "Ensure the first column contains dates in a recognisable format "
            "(e.g. 2023-01-15, 01/15/2023, Jan 2023, or 2023-01)."
        ) from _last_exc
    timestamp_index = pd.DatetimeIndex(_parsed)
    if len(timestamp_index) < 2:
        raise ValueError("Uploaded file must contain at least two timestamped rows.")

    observed_deltas = timestamp_index.to_series().sort_values().diff().dropna()
    min_delta = observed_deltas.min() if not observed_deltas.empty else pd.Timedelta(0)

    if min_delta < pd.Timedelta(hours=1):
        raise ValueError(
            "This application requires a sampling frequency of one hour or higher. "
            "Please upload data sampled hourly or less frequently."
        )

    series = df.iloc[:, 1].copy()
    series.index = timestamp_index
    series = series.sort_index()
    if not pd.api.types.is_numeric_dtype(series):
        series = pd.to_numeric(series, errors="coerce")

    if series.isna().all():
        raise ValueError("The selected value column does not contain numeric data.")

    return series


def compute_window_slider_config(current_step: int, series_length: int, default_window_size: int) -> tuple[dict[int, str], int, int, int, None]:
    """Compute valid SSA window slider marks and limits.

    Args:
        current_step: Active step index in the workflow.
        series_length: Number of observations in the loaded series.
        default_window_size: Baseline frequency-derived SSA window.

    Returns:
        A tuple containing slider marks, value, min, max, and step.
    """
    if current_step != 2 or series_length <= 0 or default_window_size <= 0:
        return {}, 0, 0, 0, None

    max_k = (series_length + (4 * default_window_size) - 1) // (4 * default_window_size)
    valid_windows = [k * default_window_size for k in range(1, max_k + 1)]

    if not valid_windows:
        return {}, 0, 0, 0, None

    marks = {val: str(val) for val in valid_windows}
    return marks, valid_windows[0], valid_windows[0], valid_windows[-1], None


def parse_reconstruction_groups(rows: list[tuple[str | None, str | None]], window_size: int) -> dict[str, list[int]]:
    """Parse grouped reconstruction rows from UI text inputs.

    Args:
        rows: Pairs of group names and component-list strings.
        window_size: Number of available SSA components.

    Returns:
        Mapping of group name to component indices.

    Raises:
        ValueError: If inputs are malformed, out of range, or overlapping.
    """

    def parse_group_list(comp_str: str | None, label: str, is_noise: bool) -> list[int] | str:
        if not comp_str or comp_str.strip() == "":
            return []

        tokens = [token.strip() for token in comp_str.split(",") if token.strip()]
        if not tokens:
            return []

        if is_noise and len(tokens) == 1 and tokens[0] == "*":
            return "*"

        if "*" in tokens:
            raise ValueError(f'"{label}": wildcard * is allowed only as the entire Noise list.')

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

    recon_dict: dict[str, list[int]] = {}
    used_non_noise_indices: set[int] = set()
    noise_wildcard_label = None

    for name, comp_str in rows:
        if not name or not name.strip():
            continue

        label = name.strip()
        is_noise = label.lower() == "noise"

        parsed_value = parse_group_list(comp_str, label, is_noise)
        if parsed_value == "*":
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
        raise ValueError("Error: Overlapping components detected. Each component can only be assigned once.")

    return recon_dict


def explained_variance_by_group_fallback(ssa_obj: Any, group_name: str) -> float:
    """Return group explained variance with a compatibility fallback.

    Args:
        ssa_obj: Active decomposition instance.
        group_name: Reconstruction group label.

    Returns:
        Explained variance percentage for the provided group.
    """
    if hasattr(ssa_obj, "explained_variance_by_group"):
        return float(ssa_obj.explained_variance_by_group(group_name))

    variation_map = getattr(ssa_obj, "_variation_by_group", {})
    if group_name in variation_map:
        return float(variation_map[group_name])

    lowered = group_name.casefold()
    for name, value in variation_map.items():
        if str(name).casefold() == lowered:
            return float(value)
    return 0.0


def build_reconstruction_metadata(ssa_obj: Any, recon_dict: dict[str, list[int]]) -> html.Div:
    """Build reconstruction metadata shown in the analysis summary card.

    Args:
        ssa_obj: Active decomposition instance.
        recon_dict: Reconstruction groups keyed by group label.

    Returns:
        Dash HTML block containing variance and Durbin-Watson details.
    """
    dw = getattr(ssa_obj, "_durbin_watson", None)
    dw_text = f"{dw:.4f}" if dw is not None else "N/A"

    variation_items = [
        html.Li([
            html.Strong(f"Variation Associated with {group_name} (%): "),
            f"{explained_variance_by_group_fallback(ssa_obj, group_name):.2f}",
        ])
        for group_name in recon_dict.keys()
    ]

    return html.Div([
        html.Ul([
            *variation_items,
            html.Li([html.Strong("Durbin-Watson Statistic: "), dw_text]),
        ]),
        html.Small(
            "A Durbin-Watson value between 1.5 and 2.5 implies that the noise is uncorrelated.",
            className="text-muted",
        ),
    ])


def format_component_indices(indices: list[int]) -> str:
    """Format component indices for display in the UI."""
    return ", ".join(str(index) for index in indices)


def build_suggested_grouping_table(
    ssa_obj: Any,
    recon_dict: dict[str, list[int]],
    dw_satisfied: bool = True,
) -> html.Div:
    """Build a centered table describing the automatic grouping suggestion.

    When ``dw_satisfied`` is False, a warning is appended advising the user to
    try a different SSA window size.
    """
    exp_var = getattr(ssa_obj, "_exp_var", {})
    rows = []
    for group_name in ("Trend", "Seasonality", "Noise"):
        indices = recon_dict.get(group_name, [])
        variance_pct = sum(float(exp_var.get(f"var_comp-{index}", 0.0)) for index in indices) * 100
        rows.append(
            html.Tr([
                html.Td(group_name),
                html.Td(format_component_indices(indices) if indices else "None"),
                html.Td(f"{variance_pct:.2f}"),
            ])
        )

    body_children: list = [
        html.H6("Suggested Grouping", className="text-center mb-3"),
        html.Div(
            html.Small(
                "These values are prepopulated below. You can change them if you want to.",
                className="text-muted",
            ),
            className="text-center mb-3",
        ),
        html.Div(
            dbc.Table(
                [
                    html.Thead(html.Tr([
                        html.Th("Group"),
                        html.Th("Components"),
                        html.Th("Explained Variance (%)"),
                    ])),
                    html.Tbody(rows),
                ],
                bordered=True,
                hover=True,
                responsive=True,
                style={"width": "auto", "margin": "0 auto"},
            ),
            className="d-flex justify-content-center",
        ),
    ]

    if not dw_satisfied:
        body_children.append(
            dbc.Alert(
                "The noise residual for this grouping does not pass the Durbin-Watson "
                "test (target range 1.5\u20132.5). Consider trying a different SSA "
                "window size.",
                color="warning",
                className="mt-3",
            )
        )

    return html.Div(html.Div(body_children), className="mb-4")


def build_noise_kde_figure(ssa_obj: Any, fallback_fig: go.Figure) -> go.Figure:
    """Build a KDE plot for reconstructed noise.

    Args:
        ssa_obj: Active decomposition instance.
        fallback_fig: Figure returned when noise is unavailable.

    Returns:
        KDE figure for noise residuals or fallback figure.
    """
    noise_signal = ssa_obj.get_reconstructed_series("noise")
    if noise_signal is None:
        return fallback_fig

    noise_data = noise_signal.dropna().values.astype(float)
    if noise_data.size < 2:
        return fallback_fig

    try:
        kde_estimator = stats.gaussian_kde(noise_data)
    except Exception as err:
        # Some datasets produce near-singular covariance (lower-dimensional support).
        # Retry once with a tiny, deterministic jitter to stabilize KDE estimation.
        err_text = str(err).lower()
        is_singular_covariance = (
            isinstance(err, np.linalg.LinAlgError)
            or "singular" in err_text
            or "lower-dimensional subspace" in err_text
        )
        if not is_singular_covariance:
            raise

        scale = float(np.std(noise_data))
        if not np.isfinite(scale) or scale <= 0.0:
            scale = max(float(np.max(np.abs(noise_data))), 1.0)
        jitter_sigma = max(scale * 1e-8, 1e-12)
        rng = np.random.default_rng(42)
        jittered = noise_data + rng.normal(0.0, jitter_sigma, size=noise_data.shape)
        kde_estimator = stats.gaussian_kde(jittered)
        noise_data = jittered

    data_min = float(np.min(noise_data))
    data_max = float(np.max(noise_data))
    if data_min == data_max:
        eps = max(abs(data_min) * 1e-6, 1e-6)
        data_min -= eps
        data_max += eps

    xs = np.linspace(data_min, data_max, 300)
    ys = kde_estimator(xs)

    noise_kde_fig = go.Figure()
    noise_kde_fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            name="Noise KDE",
            line=dict(color="steelblue"),
        )
    )
    noise_kde_fig.update_layout(
        title="Noise Kernel Density Estimate",
        xaxis_title="Value",
        yaxis_title="Density",
    )
    return noise_kde_fig


def matplotlib_figure_to_data_url(mpl_fig: Any) -> str:
    """Serialize a matplotlib figure to a base64 data URL.

    Args:
        mpl_fig: Matplotlib figure instance.

    Returns:
        PNG data URL string suitable for Dash image sources.
    """
    buf = io.BytesIO()
    mpl_fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    return f"data:image/png;base64,{img_b64}"
