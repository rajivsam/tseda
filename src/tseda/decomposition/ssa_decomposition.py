from ssalib import SingularSpectrumAnalysis
from matplotlib import pyplot as plt
from scipy.signal import find_peaks
from statsmodels.stats.stattools import durbin_watson
from statsmodels.nonparametric.smoothers_lowess import lowess
from typing import List
import pandas as pd
import numpy as np
import plotly.express as px

class SSADecomposition:
    """
    A class to perform Singular Spectrum Analysis (SSA) on a time series.
    """

    SEASONALITY_HEURISTIC_LEADING_EIGENVALUES = 6

    def __init__(self, series: pd.Series, window: int) -> None:
        """
        Initializes the SSADecomposition with a time series DataFrame.

        Args:
            df (pd.DataFrame): The input DataFrame with "date" and "signal" columns.
            window (int): The window size for SSA.
        """
        self._series = series
        self._window = window
        self._ssa = SingularSpectrumAnalysis(series, window=window)
        self._ssa.decompose()
        self._eigenvalues = self._ssa.eigenvalues
        self._total_variance = np.sum(self._eigenvalues)
        self._exp_var = {"var_comp-" + str(i) : (self._eigenvalues[i]/self._total_variance).item() for i in range(self._eigenvalues.shape[0])}
        self._cum_var = {"var_comp-" + str(i) : (np.sum(self._eigenvalues[:i+1])/self._total_variance).item() for i in range(self._eigenvalues.shape[0])}
        self._seasonality_check_heuristic = False
        self._reset_reconstruction_cache()
        return

    def seasonality_check_heuristic(self) -> bool:
        """Heuristic seasonality check based on near-equal leading eigenvalues.

        If any pair among the configured leading eigenvalues has a smaller/larger ratio of
        at least 0.95, mark the internal seasonality flag as True.
        """
        eigenvalues = np.asarray(self._eigenvalues, dtype=float)
        leading = eigenvalues[: min(self.SEASONALITY_HEURISTIC_LEADING_EIGENVALUES, eigenvalues.size)]
        self._seasonality_check_heuristic = False

        for i in range(len(leading)):
            for j in range(i + 1, len(leading)):
                larger = max(leading[i], leading[j])
                smaller = min(leading[i], leading[j])
                if larger > 0 and (smaller / larger) >= 0.95:
                    self._seasonality_check_heuristic = True
                    return True

        return False

    def _reset_reconstruction_cache(self) -> None:
        """Clear cached reconstruction products so they are rebuilt from the latest grouping."""
        self._raw_signal = None
        self._smoothed_signal = None
        self._noise_signal = None
        self._group_signals = {}
        self._durbin_watson = None
        self._variation_by_group = {}

    def _build_reconstruction_cache(self) -> None:
        """Build cached reconstructed series for raw, smoothed, noise, and each named group."""
        if not hasattr(self, "_recon"):
            raise ValueError("Reconstruction map is not set. Call set_reconstruction() first.")

        signal_keys = [key for key in self._recon.keys() if key.casefold() != "noise"]
        noise_keys = [key for key in self._recon.keys() if key.casefold() == "noise"]

        self._variation_by_group = {}
        for group_name, component_indices in self._recon.items():
            variation = 0.0
            for component_index in component_indices:
                component_key = f"var_comp-{component_index}"
                variation += self._exp_var.get(component_key, 0.0)
            self._variation_by_group[group_name] = variation * 100

        ssa_frame = self._ssa.to_frame()

        self._raw_signal = ssa_frame["ssa_preprocessed"].copy()
        self._group_signals = {
            group_name.casefold(): ssa_frame[group_name].copy()
            for group_name in signal_keys
        }
        self._smoothed_signal = ssa_frame[signal_keys].sum(axis=1).copy() if signal_keys else None

        if noise_keys:
            self._noise_signal = ssa_frame[noise_keys[0]].copy()
            self._durbin_watson = durbin_watson(self._noise_signal)
        else:
            self._noise_signal = None
            self._durbin_watson = None

    def _ensure_reconstruction_cache(self) -> None:
        if self._raw_signal is None:
            self._build_reconstruction_cache()

    def get_reconstructed_series(self, group_key: str):
        """Return a cached reconstructed series by case-insensitive group key."""
        self._ensure_reconstruction_cache()

        normalized_key = group_key.strip().casefold()
        if normalized_key in {"raw", "raw_signal", "raw signal"}:
            return self._raw_signal
        if normalized_key in {"smoothed", "smoothed_signal", "smoothed signal"}:
            return self._smoothed_signal
        if normalized_key == "noise":
            return self._noise_signal
        return self._group_signals.get(normalized_key)

    def get_group_series(self, group_key: str):
        """Alias for get_reconstructed_series for external callers."""
        return self.get_reconstructed_series(group_key)

    def eigenplot(self) -> plt.Figure:
        """
        Creates a plot of the SSA decomposition.

        Args:
            comp1 (List[int]): A list of integers representing the components for the trend.
            comp2 (List[int]): A list of integers representing the components for seasonality.

        Returns:
            plt.Figure: A matplotlib Figure object containing the decomposition plot.
        """
        df_eig = pd.DataFrame.from_dict(self._exp_var, orient="index").reset_index()
        df_eig.columns = ["component", "explained_variance"]
        # Create the line plot with markers
        fig = px.line(df_eig, x="component", y="explained_variance", markers=True)
        fig.update_layout(
            title={
            'text': "Eigen Value Variance",
            'y':0.9, # Position (0-1)
            'x':0.5, # Position (0-1)
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=20)
            }
        )
        
        return fig
    
    def eigen_vector_plot(self) -> plt.Figure:

        fig, axes = self._ssa.plot(kind='vectors')

        return fig
    
    def set_reconstruction(self, recon: dict[str, List[int]]) -> None:
        """
        Sets the components for trend and seasonality reconstruction.

        Args:
            comp1 (List[int]): A list of integers representing the components for the trend.
            comp2 (List[int]): A list of integers representing the components for seasonality.
        """
        self._reset_reconstruction_cache()
        self._recon = recon
        self._ssa.reconstruct(recon)
        return
    
    def wcorr_plot(self) -> plt.Figure:
        """
        Creates a plot of the w-correlation matrix.

        Returns:
            plt.Figure: A matplotlib Figure object containing the w-correlation matrix plot.
        """
        
        fig, ax = self._ssa.plot(kind='wcorr', n_components=self._window)
        _ = ax.set_xlabel('Component Index')
        _ = ax.set_ylabel('Component Index')
        cbar = ax.collections[0].colorbar
        cbar.set_label('Weighted Correlation Values')
        return fig
    
    def signal_reconstruction_plot(self):
        """
        Returns a Plotly figure with raw signal and smoothed signal curves over date.
        Also stores per-group variation and the noise signal on the instance.
        """

        if not hasattr(self, "_recon"):
            raise ValueError("Reconstruction map is not set. Call set_reconstruction() first.")

        self.seasonality_check_heuristic()
        self._ensure_reconstruction_cache()

        signal_keys = [key for key in self._recon.keys() if key.casefold() != "noise"]
        raw_signal = self.get_reconstructed_series("raw_signal")
        smoothed_signal = self.get_reconstructed_series("smoothed_signal")
        dates = self._series.index

        import plotly.graph_objects as go
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dates,
            y=raw_signal.values,
            mode="lines",
            name="Raw Signal",
            line=dict(color="#5a5a5a", width=1.5),
            opacity=0.7,
        ))

        fig.add_trace(go.Scatter(
            x=dates,
            y=smoothed_signal.values,
            mode="lines",
            name="Smoothed Signal",
            line=dict(color="#000000", width=2, dash="dash"),
        ))

        colors = ["#1b4f72", "#145a32", "#784212", "#4a235a", "#7b241c"]
        for i, key in enumerate(signal_keys):
            group_signal = self.get_reconstructed_series(key)
            fig.add_trace(go.Scatter(
                x=dates,
                y=group_signal.values,
                mode="lines",
                name=key,
                line=dict(width=1.5, color=colors[i % len(colors)]),
            ))

        fig.update_layout(
            title="Signal Reconstruction by Group",
            xaxis_title="Date",
            yaxis_title="Signal",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        return fig

    def loess_smother(self, fraction: float):
        """
        Fits a LOESS curve to the SSA preprocessed signal and returns a Plotly figure.

        Args:
            fraction (float): Fraction of data used for each local regression in LOESS.

        Returns:
            plotly.graph_objects.Figure: Figure with raw and LOESS-smoothed signals.
        """

        if not 0 < fraction <= 1:
            raise ValueError("fraction must be in the interval (0, 1].")

        ssa_frame = self._ssa.to_frame()
        raw_signal = ssa_frame["ssa_preprocessed"]

        loess_signal = lowess(
            endog=raw_signal.values,
            exog=np.arange(len(raw_signal)),
            frac=fraction,
            return_sorted=False,
        )

        plot_df = pd.DataFrame(
            {
                "date": self._series.index,
                "Raw Signal": raw_signal.values,
                "LOESS Smoothed Signal": loess_signal,
            }
        )

        combined_df = plot_df.melt(
            id_vars="date",
            value_vars=["Raw Signal", "LOESS Smoothed Signal"],
            var_name="Series",
            value_name="Value",
        )

        fig = px.line(
            combined_df,
            x="date",
            y="Value",
            color="Series",
            title="Raw and LOESS Smoothed Signal",
            labels={"date": "Date", "Value": "Signal"},
        )

        return fig

    def change_point_plot(self):
        """
        Returns a Plotly figure for change-point analysis using the reconstructed smoothed signal.
        """

        if not hasattr(self, "_recon"):
            raise ValueError("Reconstruction map is not set. Call set_reconstruction() first.")

        self._ensure_reconstruction_cache()
        smoothed_signal = self.get_reconstructed_series("smoothed_signal")

        max_peaks, _ = find_peaks(smoothed_signal.values)
        min_peaks, _ = find_peaks((-smoothed_signal).values)
        change_points = np.unique(np.concatenate([max_peaks, min_peaks]))
        self._change_points = change_points

        segment_frame = pd.DataFrame(
            {
                "date": self._series.index,
                "Smoothed Signal": smoothed_signal.values,
            }
        )

        segment_ids = np.ones(len(segment_frame), dtype=int)
        if change_points.size > 0:
            for idx, cp in enumerate(change_points, start=1):
                segment_ids[cp:] = idx + 1

        segment_frame["segment"] = [f"segment-{segment_id}" for segment_id in segment_ids]
        self._segment_frame = segment_frame

        fig = px.line(
            segment_frame,
            x="date",
            y="Smoothed Signal",
            color="segment",
            title="Change Point Analysis by Segment",
            labels={"date": "Date", "Smoothed Signal": "Signal", "segment": "Segment"},
        )

        return fig

    def explained_variance_by_group(self, group_name: str) -> float:
        """Return the explained variance (%) for a named reconstruction group.

        The lookup is case-insensitive. Returns 0.0 if the group is not present
        in the reconstruction map.

        Args:
            group_name (str): The group name as used in set_reconstruction().

        Returns:
            float: Explained variance percentage (0–100).
        """
        if not hasattr(self, "_recon"):
            raise ValueError("Reconstruction map is not set. Call set_reconstruction() first.")
        self._ensure_reconstruction_cache()
        key = group_name.strip().casefold()
        for name, value in self._variation_by_group.items():
            if name.casefold() == key:
                return value
        return 0.0

    def explained_variance_trend(self) -> float:
        """Return the explained variance (%) attributed to the trend group.

        Searches for a reconstruction group whose name contains 'trend'
        (case-insensitive).

        Returns:
            float: Explained variance percentage (0–100), or 0.0 if no trend
            group is defined.
        """
        if not hasattr(self, "_recon"):
            raise ValueError("Reconstruction map is not set. Call set_reconstruction() first.")
        self._ensure_reconstruction_cache()
        for name, value in self._variation_by_group.items():
            if "trend" in name.casefold():
                return value
        return 0.0

    def explained_variance_seasonality(self) -> float:
        """Return the explained variance (%) attributed to the seasonality group.

        Searches for a reconstruction group whose name contains 'season'
        (case-insensitive).

        Returns:
            float: Explained variance percentage (0–100), or 0.0 if no
            seasonality group is defined.
        """
        if not hasattr(self, "_recon"):
            raise ValueError("Reconstruction map is not set. Call set_reconstruction() first.")
        self._ensure_reconstruction_cache()
        for name, value in self._variation_by_group.items():
            if "season" in name.casefold():
                return value
        return 0.0

    def explained_variance_noise(self) -> float:
        """Return the explained variance (%) attributed to the noise group.

        Searches for a reconstruction group whose name contains 'noise'
        (case-insensitive).

        Returns:
            float: Explained variance percentage (0–100), or 0.0 if no noise
            group is defined.
        """
        if not hasattr(self, "_recon"):
            raise ValueError("Reconstruction map is not set. Call set_reconstruction() first.")
        self._ensure_reconstruction_cache()
        for name, value in self._variation_by_group.items():
            if "noise" in name.casefold():
                return value
        return 0.0
