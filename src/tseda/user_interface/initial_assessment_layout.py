"""Initial Assessment Layout for Time Series Analysis Dashboard."""

from dash import html, dcc
from components.initial_eval_components import (
    create_summary_table,
    create_kde_plot,
    create_box_plot,
    create_scatter_plot,
    create_acf_plot,
    create_pacf_plot
)
from tseda.series_stats.sampling_prop import SamplingProp
import pandas as pd


def create_initial_assessment_layout(
    series: pd.Series,
    sampling_prop: SamplingProp | None = None,
    acf_lags: int = 40,
    pacf_lags: int = 40,
    pacf_method: str = 'yw'
) -> html.Div:
    """
    Create the initial assessment layout with comprehensive time series analysis.
    
    Args:
        series: The time series data to analyze
        sampling_prop: SamplingProp object containing series properties (optional)
        acf_lags: Number of lags for ACF plot (default: 40)
        pacf_lags: Number of lags for PACF plot (default: 40)
        pacf_method: Method for PACF calculation - 'yw' (Yule-Walker) or 'ols' (default: 'yw')
    
    Returns:
        html.Div: The complete assessment layout
    """
    
    components = []
    
    # Summary Table Section
    if sampling_prop:
        components.append(
            html.Div([
                html.H3("Series Properties", className="section-title"),
                create_summary_table(sampling_prop)
            ], className="section-container")
        )
    
    # Row 1: Series Scatter Plot
    components.append(
        html.Div([
            html.H3("Series Overview", className="section-title"),
            create_scatter_plot(series)
        ], className="plot-container", style={"width": "100%", "marginBottom": "20px"})
    )
    
    # Row 2: ACF and PACF
    components.append(
        html.Div([
            html.Div([
                html.H3("Autocorrelation (ACF)", className="section-title"),
                create_acf_plot(series, lags=acf_lags)
            ], className="plot-container", style={"width": "48%", "display": "inline-block"}),
            
            html.Div([
                html.H3("Partial Autocorrelation (PACF)", className="section-title"),
                create_pacf_plot(series, lags=pacf_lags, method=pacf_method)
            ], className="plot-container", style={"width": "48%", "display": "inline-block", "marginLeft": "4%"})
        ], style={"width": "100%", "marginBottom": "20px"})
    )
    
    # Row 3: Distribution Analysis
    components.append(
        html.Div([
            html.Div([
                html.H3("Value Distribution", className="section-title"),
                create_kde_plot(series)
            ], className="plot-container", style={"width": "48%", "display": "inline-block"}),
            
            html.Div([
                html.H3("Box Plot Analysis", className="section-title"),
                create_box_plot(series)
            ], className="plot-container", style={"width": "48%", "display": "inline-block", "marginLeft": "4%"})
        ], style={"width": "100%"})
    )
    
    return html.Div(
        components,
        className="initial-assessment-container",
        style={
            "padding": "20px",
            "fontFamily": "Arial, sans-serif",
            "backgroundColor": "#f5f5f5",
            "borderRadius": "5px"
        }
    )
