"""Singular Spectrum Analysis decomposition and reconstruction utilities."""

from __future__ import annotations

from ssalib import SingularSpectrumAnalysis
from matplotlib import pyplot as plt
import ruptures as rpt
from statsmodels.stats.stattools import durbin_watson
from statsmodels.nonparametric.smoothers_lowess import lowess
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from tseda.decomposition.automatic_grouping_heuristic import AutomaticGroupingHeuristic
from tseda.config.config_loader import ConfigurationManager


class SSADecomposition:
    """
    A class to perform Singular Spectrum Analysis (SSA) on a time series.
    """

    def __init__(self, series: pd.Series, window: int) -> None:
        """
        Initialize SSA decomposition for a timestamp-indexed series.

        Args:
            series: Input numeric series indexed by datetime.
            window: Window size for SSA trajectory matrix construction.
        """
        # Load seasonality heuristic leading eigenvalues from config
        self.SEASONALITY_HEURISTIC_LEADING_EIGENVALUES = ConfigurationManager.get(
            "seasonality_heuristic.leading_eigenvalues_to_check", 6
        )
        
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

    def seasonality_check_heuristic(self) -> bool:
        """Heuristic seasonality check based on near-equal leading eigenvalues.

        If any pair among the configured leading eigenvalues has a smaller/larger ratio of
        at least 0.95, mark the internal seasonality flag as True.
        """
        heuristic = self.get_automatic_grouping_heuristic()
        max_components = min(self.SEASONALITY_HEURISTIC_LEADING_EIGENVALUES, len(heuristic.eigenvalues))
        self._seasonality_check_heuristic = heuristic.has_seasonal_pair(max_components=max_components)
        return self._seasonality_check_heuristic

    def get_automatic_grouping_heuristic(self) -> AutomaticGroupingHeuristic:
        """Return the automatic grouping heuristic for the current eigen spectrum."""
        variance_threshold = ConfigurationManager.get(
            "grouping_heuristic.variance_threshold", 0.10
        )
        pair_similarity_tolerance = ConfigurationManager.get(
            "grouping_heuristic.pair_similarity_tolerance", 0.05
        )
        return AutomaticGroupingHeuristic(
            eigenvalues=np.asarray(self._eigenvalues, dtype=float),
            variance_threshold=variance_threshold,
            pair_similarity_tolerance=pair_similarity_tolerance,
        )

    def suggest_reconstruction_groups(self) -> tuple[dict[str, list[int]], bool]:
        """Return the best auto-inferred grouping and a Durbin-Watson satisfied flag.

        Starting from the threshold-based initial assignment, the method expands the
        assignment one component (or one seasonal pair) at a time until the
        Durbin-Watson statistic of the noise residual falls in [dw_low, dw_high] or the
        candidate pool is exhausted.  The assignment with the DW value closest to
        2.0 is returned.  When no assignment achieves a DW in range the flag is
        False, signalling the caller to prompt the user to try a different window.

        Side effect: leaves SSA reconstruction state set to the returned assignment.
        """
        # Load DW bounds from config
        dw_low = ConfigurationManager.get("noise_validation.dw_low", 1.5)
        dw_high = ConfigurationManager.get("noise_validation.dw_high", 2.5)
        
        heuristic = self.get_automatic_grouping_heuristic()
        assignment = heuristic.suggest_reconstruction()

        dw = self._compute_dw_for_assignment(assignment)
        if dw is not None and dw_low <= dw <= dw_high:
            return assignment, True

        best_assignment = assignment
        best_dw_distance = abs(dw - 2.0) if dw is not None else float("inf")

        while True:
            expanded, did_expand = heuristic.suggest_next_expansion(assignment)
            if not did_expand:
                break
            assignment = expanded
            dw = self._compute_dw_for_assignment(assignment)
            if dw is not None:
                dist = abs(dw - 2.0)
                if dist < best_dw_distance:
                    best_assignment = expanded
                    best_dw_distance = dist
                if dw_low <= dw <= dw_high:
                    return best_assignment, True

        if best_assignment is not assignment:
            self._compute_dw_for_assignment(best_assignment)
        return best_assignment, False

    def _compute_dw_for_assignment(self, assignment: dict[str, list[int]]) -> float | None:
        """Set reconstruction to the given assignment and return the Durbin-Watson statistic.

        Returns None when the noise group is absent or empty (DW cannot be computed).
        """
        if not assignment.get("Noise"):
            return None
        filtered = {k: v for k, v in assignment.items() if v}
        self.set_reconstruction(filtered)
        self._ensure_reconstruction_cache()
        return self._durbin_watson

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
        """Build the reconstruction cache on first access."""
        if self._raw_signal is None:
            self._build_reconstruction_cache()

    def get_reconstructed_series(self, group_key: str) -> pd.Series | None:
        """Return a cached reconstructed series by case-insensitive group key.

        Args:
            group_key: Requested group label.

        Returns:
            Reconstructed series for the key, or None if unavailable.
        """
        self._ensure_reconstruction_cache()

        normalized_key = group_key.strip().casefold()
        if normalized_key in {"raw", "raw_signal", "raw signal"}:
            return self._raw_signal
        if normalized_key in {"smoothed", "smoothed_signal", "smoothed signal"}:
            return self._smoothed_signal
        if normalized_key == "noise":
            return self._noise_signal
        return self._group_signals.get(normalized_key)

    def get_group_series(self, group_key: str) -> pd.Series | None:
        """Alias for get_reconstructed_series for external callers."""
        return self.get_reconstructed_series(group_key)

    def eigenplot(self) -> go.Figure:
        """
        Create the explained-variance-by-component line plot.

        Returns:
            Plotly figure with component explained variance.
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
        """Return the SSA eigenvector matplotlib figure."""

        fig, axes = self._ssa.plot(kind='vectors')

        return fig
    
    def set_reconstruction(self, recon: dict[str, list[int]]) -> None:
        """
        Set decomposition groups used for signal reconstruction.

        Args:
            recon: Mapping of group names to component index lists.
        """
        self._reset_reconstruction_cache()
        self._recon = recon
        self._ssa.reconstruct(recon)
    
    def wcorr_plot(self) -> plt.Figure:
        """Create a plot of the w-correlation matrix."""
        
        fig, ax = self._ssa.plot(kind='wcorr', n_components=self._window)
        _ = ax.set_xlabel('Component Index')
        _ = ax.set_ylabel('Component Index')
        cbar = ax.collections[0].colorbar
        cbar.set_label('Weighted Correlation Values')
        return fig
    
    def signal_reconstruction_plot(self) -> go.Figure:
        """Return a signal reconstruction plot for raw, smoothed, and grouped series.

        This call also refreshes and caches reconstruction products and updates
        the seasonality heuristic flag.
        """

        if not hasattr(self, "_recon"):
            raise ValueError("Reconstruction map is not set. Call set_reconstruction() first.")

        self.seasonality_check_heuristic()
        self._ensure_reconstruction_cache()

        signal_keys = [key for key in self._recon.keys() if key.casefold() != "noise"]
        raw_signal = self.get_reconstructed_series("raw_signal")
        smoothed_signal = self.get_reconstructed_series("smoothed_signal")
        dates = self._series.index

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

    def loess_smother(self, fraction: float) -> go.Figure:
        """Fit a LOESS curve to the SSA preprocessed signal.

        Args:
            fraction: Fraction of data used for each local regression in LOESS.

        Returns:
            Figure with raw and LOESS-smoothed signals.
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

    def change_point_plot(self) -> go.Figure:
        """Return a change-point analysis plot using the smoothed signal.

        Two independent PELT detectors are run:

        * **Trend shifts** — PELT on the z-score-normalised Trend component
          (``l2`` cost, penalty ``log(n)``).  Rendered as vertical *dashed* lines.
        * **Seasonal amplitude shifts** — PELT on the z-score-normalised
          rolling-RMS envelope of the Seasonality component, with a rolling
          window equal to the SSA window size (``l2`` cost, penalty ``log(n)``).
          Rendered as vertical *dotted* lines.

        The smoothed signal (trend + all non-noise components) is plotted as a
        single continuous trace.  A plain-language summary of detected changes
        is appended below the plot.
        """
        if not hasattr(self, "_recon"):
            raise ValueError("Reconstruction map is not set. Call set_reconstruction() first.")

        self._ensure_reconstruction_cache()
        smoothed_signal = self.get_reconstructed_series("smoothed_signal")
        dates = self._series.index
        n = len(smoothed_signal)
        penalty = float(np.log(max(n, 2)))

        def _pelt_on(signal_1d: np.ndarray) -> np.ndarray:
            """Z-normalise then run PELT; return interior breakpoint indices."""
            std = float(np.std(signal_1d))
            normed = ((signal_1d - np.mean(signal_1d)) / std
                      if std > 0.0 else signal_1d.copy())
            bkps = rpt.Pelt(model="l2").fit(normed.reshape(-1, 1)).predict(pen=penalty)
            return np.array([b for b in bkps if b < n], dtype=int)

        # --- Trend shift detection --------------------------------------------
        trend_signal = self._group_signals.get("trend", smoothed_signal)
        trend_change_points = _pelt_on(trend_signal.values.astype(float))
        self._change_points = trend_change_points  # backward-compatible attribute

        # --- Seasonal amplitude shift detection -------------------------------
        seas_signal = self._group_signals.get("seasonality")
        seasonal_change_points: np.ndarray = np.array([], dtype=int)
        if seas_signal is not None:
            rms_envelope = (
                pd.Series(seas_signal.values.astype(float))
                .pow(2)
                .rolling(self._window, center=True, min_periods=1)
                .mean()
                .pow(0.5)
                .values
            )
            seasonal_change_points = _pelt_on(rms_envelope)

        # --- Segment labels (stored for downstream consumers) -----------------
        segment_ids = np.ones(n, dtype=int)
        for seg_idx, bp in enumerate(trend_change_points):
            segment_ids[bp:] = seg_idx + 2
        segment_frame = pd.DataFrame(
            {
                "date": dates,
                "Smoothed Signal": smoothed_signal.values,
                "segment": [f"segment-{s}" for s in segment_ids],
            }
        )
        self._segment_frame = segment_frame

        # --- Figure -----------------------------------------------------------
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=smoothed_signal.values,
                mode="lines",
                name="Smoothed Signal",
                line=dict(color="steelblue", width=2),
            )
        )

        def _ts_to_ms(idx: int) -> float:
            return float(pd.Timestamp(dates[idx]).timestamp() * 1000)

        # Trend change points — dashed lines, blue palette
        trend_colors = px.colors.qualitative.Plotly
        for i, cp_idx in enumerate(trend_change_points):
            fig.add_vline(
                x=_ts_to_ms(cp_idx),
                line_dash="dash",
                line_color=trend_colors[i % len(trend_colors)],
                annotation_text=f"T{i + 1}",
                annotation_position="top left" if i % 2 == 0 else "top right",
            )

        # Seasonal amplitude change points — dotted lines, warm palette
        seasonal_colors = px.colors.qualitative.Pastel
        for i, cp_idx in enumerate(seasonal_change_points):
            fig.add_vline(
                x=_ts_to_ms(cp_idx),
                line_dash="dot",
                line_color=seasonal_colors[i % len(seasonal_colors)],
                annotation_text=f"S{i + 1}",
                annotation_position="bottom left" if i % 2 == 0 else "bottom right",
            )

        # --- Plain-language summary annotations below the plot ----------------
        def _fmt_dates(indices: np.ndarray) -> str:
            if indices.size == 0:
                return "none detected"
            return ", ".join(
                str(dates[idx].date()) if hasattr(dates[idx], "date") else str(dates[idx])
                for idx in indices
            )

        trend_summary = (
            f"Trend shifts (- -): {_fmt_dates(trend_change_points)}"
        )
        seasonal_summary = (
            f"Seasonal amplitude shifts (···): {_fmt_dates(seasonal_change_points)}"
        )

        for row_idx, text in enumerate([trend_summary, seasonal_summary]):
            fig.add_annotation(
                text=text,
                xref="paper", yref="paper",
                x=0.0,
                y=-0.22 - row_idx * 0.09,
                showarrow=False,
                font=dict(size=11),
                align="left",
                xanchor="left",
            )

        fig.update_layout(
            title="Change Point Analysis",
            xaxis_title="Date",
            yaxis_title="Signal",
            margin=dict(b=160),
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
