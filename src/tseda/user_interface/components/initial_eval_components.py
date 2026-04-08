from tseda.series_stats.sampling_prop import SamplingProp
from dash import Dash, html, dcc
from dash_ag_grid import AgGrid
import pandas as pd
import numpy as np
import plotly.figure_factory as ff
import plotly.graph_objects as go
from statsmodels.tsa.stattools import acf, pacf
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from tseda.decomposition.ssa_decomposition import SSADecomposition

def create_summary_table(sampling_prop: SamplingProp) -> AgGrid:
    df = sampling_prop.view_properties()
    
    return AgGrid(
        columnDefs=[
            {
                "field": "property", 
                "headerName": "Property",
                "cellStyle": {"fontWeight": "bold", "backgroundColor": "#e8f4f8"}
            },
            {
                "field": "value", 
                "headerName": "Value",
                "cellStyle": {"backgroundColor": "#f9f9f9"}
            }
        ],
        rowData=df.to_dict('records'),
        defaultColDef={
            "flex": 1,
            "resizable": True,
            "sortable": True,
            "cellStyle": {"border": "1px solid #ddd", "padding": "8px"}
        },
        style={"height": "300px", "width": "100%"},
        className="ag-theme-alpine",
        dashGridOptions={
            "headerHeight": 40,
            "rowHeight": 35
        }
    )

def create_kde_plot(series: pd.Series, show_kde: bool = True, bin_count: int | None = None) -> go.Figure:
    clean_series = series.dropna()
    if clean_series.empty:
        raise ValueError('Series contains no numeric values for KDE/histogram plotting.')

    values = clean_series.values
    if bin_count is None or bin_count <= 0:
        q75, q25 = np.percentile(values, [75, 25])
        iqr = q75 - q25
        if iqr <= 0:
            iqr = np.std(values)
        bin_width = 2 * iqr * np.power(len(values), -1/3)
        if bin_width <= 0:
            bin_width = np.ptp(values) / 10 if np.ptp(values) > 0 else 1.0
        bin_size = float(bin_width)
    else:
        data_range = np.ptp(values)
        bin_size = float(data_range / bin_count) if data_range > 0 else 1.0

    fig = ff.create_distplot(
        [values],
        ['Value'],
        show_hist=True,
        show_rug=False,
        show_curve=show_kde,
        bin_size=bin_size
    )
    fig.update_layout(
        title={"text": "Value Distribution with KDE", "x": 0.5, "xanchor": "center"},
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
        xaxis_title="Value",
        yaxis_title="Density",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def create_box_plot(series: pd.Series) -> go.Figure:
    fig = go.Figure(
        go.Box(
            y=series,
            name="Value",
            boxmean='sd',
            marker=dict(color="#1170d7", opacity=0.8),
            line=dict(color="#0a58ca"),
            hovertemplate="Value: %{y}<extra></extra>"
        )
    )
    fig.update_layout(
        title={"text": "Value Distribution", "x": 0.5, "xanchor": "center"},
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
        yaxis_title="Value",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )

    return fig


def create_scatter_plot(series: pd.Series) -> go.Figure:
    x_values = series.index
    y_values = series.values

    if len(series) >= 2:
        numeric_x = np.arange(len(series))
        coeffs = np.polyfit(numeric_x, y_values, 1)
        trend_values = np.polyval(coeffs, numeric_x)
    else:
        trend_values = y_values

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode='markers+lines',
            name='Series',
            marker=dict(color='#ff7f0e', size=6, opacity=0.8),
            line=dict(color='#ff7f0e', width=1),
            hovertemplate="%{x}<br>Value: %{y}<extra></extra>"
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=trend_values,
            mode='lines',
            name='Trend Line',
            line=dict(color='#636efa', width=2, dash='dash'),
            hovertemplate="%{x}<br>Trend: %{y:.2f}<extra></extra>"
        )
    )

    fig.update_layout(
        title={"text": "Series Scatter Plot", "x": 0.5, "xanchor": "center"},
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
        xaxis_title="Timestamp",
        yaxis_title="Value",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def create_acf_plot(series: pd.Series, lags: int = 40) -> go.Figure:
    """Create an ACF (Autocorrelation Function) plot.
    
    Args:
        series: Time series data
        lags: Number of lags to display (default: 40)
        
    Returns:
        dcc.Graph component containing the ACF plot
    """
    clean_series = series.dropna()
    if clean_series.empty:
        raise ValueError('Series contains no numeric values for ACF plotting.')
    
    # Adjust lags if series is too short
    max_lags = len(clean_series) - 1
    if lags > max_lags:
        lags = max_lags
    
    if lags <= 0:
        # Return empty plot for very short series
        fig = go.Figure()
        fig.add_annotation(
            text="Series too short for ACF analysis.",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14)
        )
        fig.update_layout(
            title={"text": "Autocorrelation Function (ACF)", "x": 0.5, "xanchor": "center"},
            template="plotly_white",
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
            xaxis_title="Lag",
            yaxis_title="ACF"
        )
        return fig
    
    # Calculate ACF values and confidence intervals
    acf_values, conf_int = acf(clean_series, nlags=lags, alpha=0.05)
    
    # Create figure
    fig = go.Figure()
    
    # Add ACF stem plot
    fig.add_trace(
        go.Bar(
            x=np.arange(len(acf_values)),
            y=acf_values,
            name='ACF',
            marker=dict(color='#1170d7'),
            width=0.4,
            hovertemplate="Lag: %{x}<br>ACF: %{y:.4f}<extra></extra>"
        )
    )
    
    # Add confidence interval bounds
    conf_lower = conf_int[:, 0] - acf_values
    conf_upper = conf_int[:, 1] - acf_values
    
    fig.add_trace(
        go.Scatter(
            x=np.arange(len(acf_values)),
            y=conf_upper,
            mode='lines',
            line=dict(color='rgba(0,0,0,0)'),
            showlegend=False,
            hoverinfo='skip'
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=np.arange(len(acf_values)),
            y=conf_lower,
            mode='lines',
            line=dict(color='rgba(0,0,0,0)'),
            fillcolor='rgba(68, 68, 68, 0.2)',
            fill='tonexty',
            name='95% Confidence Interval',
            hovertemplate="Lag: %{x}<extra></extra>"
        )
    )
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title={"text": "Autocorrelation Function (ACF)", "x": 0.5, "xanchor": "center"},
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
        xaxis_title="Lag",
        yaxis_title="ACF",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode='x unified'
    )
    
    return fig


def create_pacf_plot(series: pd.Series, lags: int = 40, method: str = 'yw') -> go.Figure:
    """Create a PACF (Partial Autocorrelation Function) plot.
    
    Args:
        series: Time series data
        lags: Number of lags to display (default: 40)
        method: Method for PACF calculation ('yw' for Yule-Walker or 'ols' for OLS)
        
    Returns:
        Plotly figure containing the PACF plot
    """
    clean_series = series.dropna()
    if clean_series.empty:
        raise ValueError('Series contains no numeric values for PACF plotting.')
    
    # Adjust lags if series is too short
    max_lags = len(clean_series) // 2 - 1  # PACF can use up to 50% of sample size
    if lags > max_lags:
        lags = max(max_lags, 1)  # At least 1 lag
    
    if lags <= 0:
        # Return empty plot for very short series
        fig = go.Figure()
        fig.add_annotation(
            text="Series too short for PACF analysis.",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14)
        )
        fig.update_layout(
            title={"text": "Partial Autocorrelation Function (PACF)", "x": 0.5, "xanchor": "center"},
            template="plotly_white",
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
            xaxis_title="Lag",
            yaxis_title="PACF"
        )
        return fig
    
    # Calculate PACF values and confidence intervals
    pacf_values, conf_int = pacf(clean_series, nlags=lags, method=method, alpha=0.05)
    
    # Create figure
    fig = go.Figure()
    
    # Add PACF stem plot
    fig.add_trace(
        go.Bar(
            x=np.arange(len(pacf_values)),
            y=pacf_values,
            name='PACF',
            marker=dict(color='#ff7f0e'),
            width=0.4,
            hovertemplate="Lag: %{x}<br>PACF: %{y:.4f}<extra></extra>"
        )
    )
    
    # Add confidence interval bounds
    conf_lower = conf_int[:, 0] - pacf_values
    conf_upper = conf_int[:, 1] - pacf_values
    
    fig.add_trace(
        go.Scatter(
            x=np.arange(len(pacf_values)),
            y=conf_upper,
            mode='lines',
            line=dict(color='rgba(0,0,0,0)'),
            showlegend=False,
            hoverinfo='skip'
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=np.arange(len(pacf_values)),
            y=conf_lower,
            mode='lines',
            line=dict(color='rgba(0,0,0,0)'),
            fillcolor='rgba(68, 68, 68, 0.2)',
            fill='tonexty',
            name='95% Confidence Interval',
            hovertemplate="Lag: %{x}<extra></extra>"
        )
    )
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title={"text": "Partial Autocorrelation Function (PACF)", "x": 0.5, "xanchor": "center"},
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
        xaxis_title="Lag",
        yaxis_title="PACF",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode='x unified'
    )

    return fig


def create_ssa_decomposition_plot(series: pd.Series, window_size: int, trend_components: list = None, seasonal_components: list = None) -> go.Figure:
    """Create an SSA (Singular Spectrum Analysis) decomposition plot.
    
    Args:
        series: Time series data
        window_size: Window size for SSA decomposition
        trend_components: List of component indices for trend (default: [0, 1])
        seasonal_components: List of component indices for seasonality (default: [2, 3])
        
    Returns:
        dcc.Graph component containing the SSA decomposition plot
    """
    if window_size <= 0:
        # Return empty plot with message when window_size is invalid
        fig = go.Figure()
        fig.add_annotation(
            text="SSA decomposition requires a valid window size (> 0).<br>Please upload time series data first.",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14)
        )
        fig.update_layout(
            title={"text": "SSA Decomposition (Window Size: Invalid)", "x": 0.5, "xanchor": "center"},
            template="plotly_white",
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
            xaxis_title="Time",
            yaxis_title="Value"
        )
        return fig
    
    if trend_components is None:
        trend_components = [0, 1]
    if seasonal_components is None:
        seasonal_components = [2, 3]
    
    try:
        # Prepare data for SSA (needs date and signal columns)
        df = series.reset_index()
        df.columns = ['date', 'signal']
        
        # Create SSA decomposition
        ssa = SSADecomposition(df, window=window_size)
        
        # Reconstruct trend and seasonal components
        ssa._ssa.reconstruct(groups={'Trend': trend_components, 'Seasonal': seasonal_components})
        
        # Create plotly figure
        fig = go.Figure()
        
        # Add original series
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                mode='lines',
                name='Original',
                line=dict(color='#1f77b4', width=2),
                hovertemplate="%{x}<br>Original: %{y:.4f}<extra></extra>"
            )
        )
        
        # Add trend component
        if 'Trend' in ssa._ssa.groups and len(ssa._ssa['Trend']) > 0:
            trend_series = ssa._ssa['Trend']
            # Use the same index as the original series
            fig.add_trace(
                go.Scatter(
                    x=series.index[:len(trend_series)],  # Match length with trend series
                    y=trend_series.values,
                    mode='lines',
                    name='Trend',
                    line=dict(color='#ff7f0e', width=2, dash='dash'),
                    hovertemplate="%{x}<br>Trend: %{y:.4f}<extra></extra>"
                )
            )
        
        # Add seasonal component
        if 'Seasonal' in ssa._ssa.groups and len(ssa._ssa['Seasonal']) > 0:
            seasonal_series = ssa._ssa['Seasonal']
            # Use the same index as the original series
            fig.add_trace(
                go.Scatter(
                    x=series.index[:len(seasonal_series)],  # Match length with seasonal series
                    y=seasonal_series.values,
                    mode='lines',
                    name='Seasonal',
                    line=dict(color='#2ca02c', width=2, dash='dot'),
                    hovertemplate="%{x}<br>Seasonal: %{y:.4f}<extra></extra>"
                )
            )
        
        fig.update_layout(
            title={"text": f"SSA Decomposition (Window Size: {window_size})", "x": 0.5, "xanchor": "center"},
            template="plotly_white",
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
            xaxis_title="Time",
            yaxis_title="Value",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        return fig
    
    except Exception as e:
        # Return error plot if SSA decomposition fails
        fig = go.Figure()
        fig.add_annotation(
            text=f"SSA decomposition failed: {str(e)}<br>Please check your data and window size.",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=12)
        )
        fig.update_layout(
            title={"text": f"SSA Decomposition Error (Window Size: {window_size})", "x": 0.5, "xanchor": "center"},
            template="plotly_white",
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
            xaxis_title="Time",
            yaxis_title="Value"
        )
        return fig
