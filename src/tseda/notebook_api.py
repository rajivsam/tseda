"""Notebook-oriented API wrappers for the three-step ``tseda`` workflow.

This module exposes a stable, developer-friendly surface that mirrors the Dash
UI capabilities while remaining fully scriptable in Python notebooks.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import stats

from tseda.config.config_loader import ConfigurationManager
from tseda.decomposition.ssa_decomposition import SSADecomposition
from tseda.decomposition.ssa_result_summary import SSAResultSummary
from tseda.series_stats.sampling_prop import SamplingProp
from tseda.series_stats.summary_statistics import SummaryStatistics
from tseda.user_interface.components.initial_eval_components import (
    create_acf_plot,
    create_box_plot,
    create_kde_plot,
    create_pacf_plot,
    create_scatter_plot,
)


AVAILABLE_BIN_ALGORITHMS = (
    "auto",
    "fd",
    "doane",
    "scott",
    "stone",
    "rice",
    "sturges",
    "sqrt",
)

EXAMPLE_DATASETS: dict[str, str] = {
    "coffee_prices": "data/coffee_prices.csv",
    "monthly_car_sales": "data/monthly-car-sales.csv",
    "trimmed_biomass": "data/trimmed_biomass - generated_biomass_MW_series.csv",
    "white_noise_data": "data/white_noise_data.csv",
    "uci_air_quality_hourly_co": "data/uci_air_quality_hourly_co.csv",
    "ticket_resolution_hourly_nyc311": "data/ticket_resolution_hourly_nyc311.csv",
}


@dataclass(slots=True)
class SuitabilityResult:
    """Result object for the SSA dataset suitability check.

    Attributes:
        top_k_ratio: Fraction of total variance explained by the top-k
            eigenvectors.
        top_k: Effective number of eigenvectors used in the ratio.
        threshold: Minimum required explained-variance threshold.
        is_suitable: ``True`` when ``top_k_ratio >= threshold``.
    """

    top_k_ratio: float
    top_k: int
    threshold: float
    is_suitable: bool


def _as_datetime_numeric_series(
    frame: pd.DataFrame,
    timestamp_col: int | str = 0,
    value_col: int | str = 1,
) -> pd.Series:
    """Convert a two-column frame into a clean timestamp-indexed numeric series.

    Args:
        frame: Input data frame containing at least timestamp and value columns.
        timestamp_col: Timestamp column index or name.
        value_col: Numeric value column index or name.

    Returns:
        Timestamp-indexed numeric series sorted by time.

    Raises:
        ValueError: If conversion fails or no numeric values remain.
    """
    timestamp = pd.to_datetime(frame[timestamp_col], errors="coerce")
    values = pd.to_numeric(frame[value_col], errors="coerce")
    series = pd.Series(values.values, index=timestamp).dropna().sort_index()

    if series.empty:
        raise ValueError("No valid datetime/value rows were found in the provided data.")
    return series


def list_example_datasets() -> list[str]:
    """Return the registry keys for built-in repository example datasets.

    Returns:
        Sorted list of example dataset names that can be passed to
        :func:`load_example_series`.
    """
    return sorted(EXAMPLE_DATASETS.keys())


def load_series_from_csv(
    csv_path: str | Path,
    timestamp_col: int | str = 0,
    value_col: int | str = 1,
    **read_csv_kwargs: Any,
) -> pd.Series:
    """Load a timestamp-indexed numeric series from a CSV file.

    Args:
        csv_path: CSV file path.
        timestamp_col: Timestamp column index or name.
        value_col: Numeric value column index or name.
        **read_csv_kwargs: Extra keyword arguments forwarded to
            :func:`pandas.read_csv`.

    Returns:
        Timestamp-indexed numeric series.

    Raises:
        FileNotFoundError: If the CSV path does not exist.
        ValueError: If no valid datetime/value rows are parsed.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV path does not exist: {path}")

    frame = pd.read_csv(path, **read_csv_kwargs)
    return _as_datetime_numeric_series(frame, timestamp_col=timestamp_col, value_col=value_col)


def load_example_series(
    dataset_name: str,
    workspace_root: str | Path | None = None,
    timestamp_col: int | str = 0,
    value_col: int | str = 1,
) -> pd.Series:
    """Load one of the repository example datasets as a pandas Series.

    Args:
        dataset_name: Key from :data:`EXAMPLE_DATASETS`.
        workspace_root: Optional workspace root. If omitted, uses current
            working directory.
        timestamp_col: Timestamp column index or name for the source CSV.
        value_col: Value column index or name for the source CSV.

    Returns:
        Timestamp-indexed numeric series for the requested dataset.

    Raises:
        KeyError: If the dataset name is unknown.
        FileNotFoundError: If the resolved CSV path does not exist.
        ValueError: If datetime/value parsing fails.
    """
    if dataset_name not in EXAMPLE_DATASETS:
        valid = ", ".join(list_example_datasets())
        raise KeyError(f"Unknown dataset '{dataset_name}'. Valid names: {valid}")

    root = Path(workspace_root) if workspace_root is not None else Path.cwd()
    csv_path = root / EXAMPLE_DATASETS[dataset_name]
    return load_series_from_csv(csv_path, timestamp_col=timestamp_col, value_col=value_col)


class NotebookThreeStepAPI:
    """Notebook-first wrapper exposing the same three-step workflow as the UI.

    The class keeps decomposition state (window, SSA model, grouping) so each
    feature can be called independently in notebooks while preserving continuity
    across steps.
    """

    def __init__(
        self,
        series: pd.Series,
        window: int | None = None,
        apply_window_refinement: bool = True,
    ) -> None:
        """Create a notebook workflow session for one time series.

        Args:
            series: Timestamp-indexed numeric input series.
            window: Optional initial SSA window. If omitted, the cadence-based
                heuristic from :class:`tseda.series_stats.sampling_prop.SamplingProp`
                is used.
            apply_window_refinement: Whether to apply the same eigen-tail
                refinement loop used by the UI.

        Raises:
            ValueError: If a valid default window cannot be inferred.
        """
        ConfigurationManager.load_config()
        self._series = self._validate_series(series)
        self._sampling = SamplingProp(self._series)

        inferred_window = self._sampling._freq_window
        if window is None:
            if inferred_window is None or int(inferred_window) <= 0:
                raise ValueError(
                    "Could not infer a valid window from sampling frequency; pass an explicit window."
                )
            window = int(inferred_window)

        self._window = int(window)
        self._ssa: SSADecomposition | None = None
        self._grouping: dict[str, list[int]] | None = None
        self._summary: SSAResultSummary | None = None
        self._build_decomposition(self._window, apply_window_refinement=apply_window_refinement)

    @staticmethod
    def _validate_series(series: pd.Series) -> pd.Series:
        """Return a cleaned datetime-indexed numeric series.

        Args:
            series: Input series.

        Returns:
            Sorted numeric series with datetime index and dropped missing rows.

        Raises:
            ValueError: If the result is empty after validation.
        """
        values = pd.to_numeric(series, errors="coerce")
        index = pd.to_datetime(series.index, errors="coerce")
        cleaned = pd.Series(values.values, index=index).dropna().sort_index()
        if cleaned.empty:
            raise ValueError("Series must contain at least one valid datetime/value observation.")
        return cleaned

    @property
    def series(self) -> pd.Series:
        """Return the validated input series."""
        return self._series.copy()

    def get_configuration(self) -> dict[str, Any]:
        """Return the effective full configuration dictionary.

        Returns:
            Deep copy of the currently loaded ``tseda_config.yaml`` content.
        """
        return deepcopy(ConfigurationManager.load_config())

    def get_sampling_properties(self) -> pd.DataFrame:
        """Return sampling properties used in Step 1.

        Returns:
            DataFrame with property/value rows.
        """
        return self._sampling.view_properties()

    def get_summary_statistics(self) -> pd.DataFrame:
        """Return descriptive summary statistics for the current series.

        Returns:
            DataFrame containing mean, variance, percentiles, skewness, and kurtosis.
        """
        return SummaryStatistics(self._series).compute_statistics()

    def _resolve_bin_count(
        self,
        bin_count: int | None,
        bin_algorithm: str,
    ) -> int | None:
        """Resolve histogram bin count from explicit value or named algorithm.

        Args:
            bin_count: Explicit number of bins. If provided and positive, it is
                used as-is.
            bin_algorithm: Algorithm name accepted by
                :func:`numpy.histogram_bin_edges` (for example ``"scott"``,
                ``"fd"``, ``"sturges"``, ``"auto"``).

        Returns:
            Positive integer bin count or ``None`` when auto sizing should be used.

        Raises:
            ValueError: If bin_count is non-positive or algorithm is invalid.
        """
        if bin_count is not None:
            if int(bin_count) <= 0:
                raise ValueError("bin_count must be a positive integer when provided.")
            return int(bin_count)

        values = self._series.dropna().values.astype(float)
        if values.size < 2:
            return 1

        algo = str(bin_algorithm).strip().lower()
        if algo not in AVAILABLE_BIN_ALGORITHMS:
            raise ValueError(
                f"Unsupported bin_algorithm '{bin_algorithm}'. "
                f"Choose one of: {', '.join(AVAILABLE_BIN_ALGORITHMS)}"
            )

        edges = np.histogram_bin_edges(values, bins=algo)
        return max(len(edges) - 1, 1)

    def get_kde_plot(
        self,
        show_kde: bool = True,
        bin_count: int | None = None,
        bin_algorithm: str = "fd",
    ) -> go.Figure:
        """Get the Step-1 distribution plot (histogram and optional KDE).

        Args:
            show_kde: Whether to overlay the KDE curve.
            bin_count: Explicit histogram bin count.
            bin_algorithm: Bin selection rule used when ``bin_count`` is omitted;
                supports numpy rules such as ``"scott"``, ``"fd"``, and
                ``"sturges"``.

        Returns:
            Plotly figure with histogram and optional KDE curve.
        """
        resolved_bin_count = self._resolve_bin_count(bin_count=bin_count, bin_algorithm=bin_algorithm)
        return create_kde_plot(self._series, show_kde=show_kde, bin_count=resolved_bin_count)

    def get_box_plot(self) -> go.Figure:
        """Get the Step-1 box plot for value spread diagnostics.

        Returns:
            Plotly box plot figure.
        """
        return create_box_plot(self._series)

    def get_scatter_plot(self) -> go.Figure:
        """Get the Step-1 scatter/line plot with trend overlay.

        Returns:
            Plotly time-series scatter figure.
        """
        return create_scatter_plot(self._series)

    def get_acf_plot(self, lags: int = 40) -> go.Figure:
        """Get the Step-1 autocorrelation plot.

        Args:
            lags: Maximum lag count.

        Returns:
            Plotly ACF figure.
        """
        return create_acf_plot(self._series, lags=lags)

    def get_pacf_plot(self, lags: int = 40, method: str = "yw") -> go.Figure:
        """Get the Step-1 partial autocorrelation plot.

        Args:
            lags: Maximum lag count.
            method: PACF estimator method forwarded to statsmodels.

        Returns:
            Plotly PACF figure.
        """
        return create_pacf_plot(self._series, lags=lags, method=method)

    def _build_decomposition(self, window: int, apply_window_refinement: bool) -> None:
        """Build or rebuild the SSA decomposition state.

        Args:
            window: Requested SSA window.
            apply_window_refinement: Whether to run the same tail-spread
                refinement loop as the UI.
        """
        selected_window = int(window)
        ssa = SSADecomposition(self._series, selected_window)

        if apply_window_refinement:
            min_tail_spread = float(ConfigurationManager.get("window_refinement.min_tail_spread", 0.10))
            eigenvalues = np.asarray(getattr(ssa, "_eigenvalues", []), dtype=float)
            total = float(np.sum(eigenvalues))
            while (
                eigenvalues.size > 0
                and total > 0.0
                and float(eigenvalues[-1]) / total >= min_tail_spread
                and selected_window * 2 <= len(self._series) // 2
            ):
                selected_window *= 2
                ssa = SSADecomposition(self._series, selected_window)
                eigenvalues = np.asarray(getattr(ssa, "_eigenvalues", []), dtype=float)
                total = float(np.sum(eigenvalues))

        self._window = selected_window
        self._ssa = ssa
        self._grouping = None
        self._summary = None

    def get_window(self) -> int:
        """Get the current SSA window size used by the decomposition.

        Returns:
            Current window size.
        """
        return int(self._window)

    def set_window(self, window: int, apply_window_refinement: bool = False) -> int:
        """Set and rebuild the SSA window.

        Args:
            window: New SSA window size.
            apply_window_refinement: Whether to apply refinement loop after setting.

        Returns:
            Effective window after optional refinement.

        Raises:
            ValueError: If window is not positive.
        """
        if int(window) <= 0:
            raise ValueError("window must be a positive integer.")
        self._build_decomposition(int(window), apply_window_refinement=apply_window_refinement)
        return self.get_window()

    def _ensure_ssa(self) -> SSADecomposition:
        """Return active SSA decomposition object.

        Returns:
            Current SSA decomposition.
        """
        if self._ssa is None:
            self._build_decomposition(self._window, apply_window_refinement=False)
        return self._ssa

    def get_suitability_result(
        self,
        top_k_eigenvectors: int | None = None,
        min_explained_variance: float | None = None,
    ) -> SuitabilityResult:
        """Evaluate the same top-k eigenvalue suitability gate used by the UI.

        Args:
            top_k_eigenvectors: Number of leading eigenvalues to sum. If omitted,
                uses ``suitability_check.top_k_eigenvectors`` from config.
            min_explained_variance: Minimum required variance concentration ratio.
                If omitted, uses ``suitability_check.min_explained_variance``.

        Returns:
            SuitabilityResult with pass/fail and computed ratios.
        """
        ssa = self._ensure_ssa()
        eigenvalues = np.asarray(getattr(ssa, "_eigenvalues", []), dtype=float)

        top_k = int(
            top_k_eigenvectors
            if top_k_eigenvectors is not None
            else ConfigurationManager.get("suitability_check.top_k_eigenvectors", 5)
        )
        threshold = float(
            min_explained_variance
            if min_explained_variance is not None
            else ConfigurationManager.get("suitability_check.min_explained_variance", 0.40)
        )

        total = float(np.sum(eigenvalues)) if eigenvalues.size > 0 else 0.0
        k = min(max(top_k, 1), eigenvalues.size if eigenvalues.size > 0 else 1)
        ratio = (float(np.sum(eigenvalues[:k])) / total) if total > 0.0 else 0.0

        return SuitabilityResult(
            is_suitable=ratio >= threshold,
            top_k=k,
            top_k_ratio=ratio,
            threshold=threshold,
        )

    def get_eigen_plot(self) -> go.Figure:
        """Get Step-2 eigenvalue explained-variance plot.

        Returns:
            Plotly eigenvalue variance figure.
        """
        return self._ensure_ssa().eigenplot()

    def get_eigen_vector_plot(self) -> Any:
        """Get Step-2 SSA eigenvector plot.

        Returns:
            Matplotlib figure generated by ``ssalib``.
        """
        return self._ensure_ssa().eigen_vector_plot()

    def get_wcorr_plot(self) -> Any:
        """Get Step-2 weighted-correlation matrix plot.

        Returns:
            Matplotlib figure with the SSA w-correlation matrix.
        """
        return self._ensure_ssa().wcorr_plot()

    def suggest_grouping(self) -> tuple[dict[str, list[int]], bool]:
        """Run automatic grouping heuristic and apply the suggested grouping.

        Returns:
            A tuple of ``(grouping, durbin_watson_in_range)`` where grouping has
            ``Trend``, ``Seasonality``, and ``Noise`` keys.
        """
        ssa = self._ensure_ssa()
        grouping, dw_satisfied = ssa.suggest_reconstruction_groups()
        self._grouping = {k: list(v) for k, v in grouping.items()}
        self._summary = None
        return self.get_grouping(), bool(dw_satisfied)

    def get_grouping(self) -> dict[str, list[int]]:
        """Get the active component grouping.

        Returns:
            Grouping dictionary. Empty dict if not set yet.
        """
        if self._grouping is None:
            return {}
        return {k: list(v) for k, v in self._grouping.items()}

    def set_grouping(
        self,
        grouping: Mapping[str, Sequence[int]] | None = None,
        trend: Sequence[int] | None = None,
        seasonality: Sequence[int] | None = None,
        noise: Sequence[int] | None = None,
    ) -> dict[str, list[int]]:
        """Set and apply reconstruction grouping for Step 2.

        You can either pass ``grouping`` directly or use explicit ``trend``,
        ``seasonality``, and ``noise`` sequences.

        Args:
            grouping: Mapping from group name to component indices.
            trend: Component indices for trend.
            seasonality: Component indices for seasonality.
            noise: Component indices for noise.

        Returns:
            Normalized grouping that was applied.

        Raises:
            ValueError: If indices overlap or are out of range.
        """
        ssa = self._ensure_ssa()

        if grouping is None:
            grouping = {
                "Trend": list(trend or []),
                "Seasonality": list(seasonality or []),
                "Noise": list(noise or []),
            }

        normalized: dict[str, list[int]] = {}
        used: set[int] = set()
        max_component = self.get_window() - 1

        for name, indices in grouping.items():
            key = str(name).strip()
            if not key:
                continue
            int_indices = [int(i) for i in indices]
            for idx in int_indices:
                if idx < 0 or idx > max_component:
                    raise ValueError(
                        f"Component index {idx} is out of range [0, {max_component}] for window {self.get_window()}."
                    )
                if idx in used:
                    raise ValueError("Grouping contains overlapping component indices.")
                used.add(idx)
            normalized[key] = int_indices

        if not normalized:
            raise ValueError("At least one non-empty grouping entry is required.")

        ssa.set_reconstruction(normalized)
        self._grouping = normalized
        self._summary = None
        return self.get_grouping()

    def _ensure_grouping(self) -> dict[str, list[int]]:
        """Ensure a reconstruction grouping is available and applied."""
        if self._grouping is None:
            grouping, _ = self.suggest_grouping()
            self.set_grouping(grouping=grouping)
        return self._grouping

    def get_reconstruction_plot(self, auto_suggest_if_missing: bool = True) -> go.Figure:
        """Get Step-2 reconstruction plot for currently grouped components.

        Args:
            auto_suggest_if_missing: If True and no grouping exists yet, auto-suggest
                and apply a grouping first.

        Returns:
            Plotly reconstruction figure.

        Raises:
            ValueError: If no grouping is set and auto suggestion is disabled.
        """
        if self._grouping is None:
            if auto_suggest_if_missing:
                self._ensure_grouping()
            else:
                raise ValueError("Grouping is not set. Call suggest_grouping() or set_grouping() first.")
        return self._ensure_ssa().signal_reconstruction_plot()

    def get_change_point_plot(self, auto_suggest_if_missing: bool = True) -> go.Figure:
        """Get Step-2 change-point plot from grouped reconstruction.

        Args:
            auto_suggest_if_missing: Whether to auto-suggest grouping if absent.

        Returns:
            Plotly change-point figure.
        """
        if self._grouping is None and auto_suggest_if_missing:
            self._ensure_grouping()
        return self._ensure_ssa().change_point_plot()

    def get_loess_plot(self, fraction: float | None = None) -> go.Figure:
        """Get LOESS verification plot for the reconstructed signal.

        Args:
            fraction: LOESS fraction in ``(0, 1]``. When omitted, uses config
                ``loess.default_fraction``.

        Returns:
            Plotly figure with raw and LOESS-smoothed signals.
        """
        if fraction is None:
            fraction = float(ConfigurationManager.get("loess.default_fraction", 0.05))
        return self._ensure_ssa().loess_smother(float(fraction))

    def get_noise_kde_plot(
        self,
        bandwidth: str | float = "scott",
        auto_suggest_if_missing: bool = True,
    ) -> go.Figure:
        """Get a KDE plot for the reconstructed Noise component.

        Args:
            bandwidth: ``scipy.stats.gaussian_kde`` bandwidth specification
                (for example ``"scott"``, ``"silverman"``, or a scalar).
            auto_suggest_if_missing: Whether to auto-suggest grouping if absent.

        Returns:
            Plotly figure with KDE of noise values.

        Raises:
            ValueError: If noise series is unavailable.
        """
        if self._grouping is None:
            if auto_suggest_if_missing:
                self._ensure_grouping()
            else:
                raise ValueError("Grouping is not set. Call suggest_grouping() or set_grouping() first.")

        noise = self._ensure_ssa().get_reconstructed_series("noise")
        if noise is None:
            raise ValueError("Noise series is unavailable. Ensure your grouping includes a Noise group.")

        values = noise.dropna().values.astype(float)
        if values.size < 2:
            raise ValueError("Noise series needs at least two values for KDE plotting.")

        kde = stats.gaussian_kde(values, bw_method=bandwidth)
        x_grid = np.linspace(values.min(), values.max(), 300)
        y_density = kde(x_grid)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x_grid,
                y=y_density,
                mode="lines",
                name="Noise KDE",
                line=dict(color="#d62728", width=2),
            )
        )
        fig.update_layout(
            title="Noise Component KDE",
            xaxis_title="Noise value",
            yaxis_title="Density",
            template="plotly_white",
        )
        return fig

    def get_reconstruction_metadata(self, auto_suggest_if_missing: bool = True) -> dict[str, Any]:
        """Return key reconstruction diagnostics (explained variance and DW).

        Args:
            auto_suggest_if_missing: Whether to auto-suggest grouping if absent.

        Returns:
            Dictionary containing per-group explained variance and Durbin-Watson.
        """
        if self._grouping is None and auto_suggest_if_missing:
            self._ensure_grouping()

        ssa = self._ensure_ssa()
        grouping = self.get_grouping()

        if grouping:
            _ = ssa.signal_reconstruction_plot()

        explained_variance = {
            name: float(ssa.explained_variance_by_group(name))
            for name in grouping.keys()
        }

        return {
            "grouping": grouping,
            "explained_variance_percent": explained_variance,
            "durbin_watson": getattr(ssa, "_durbin_watson", None),
        }

    def export_components_dataframe(self, auto_suggest_if_missing: bool = True) -> pd.DataFrame:
        """Export timestamp, trend, seasonality, and noise components as a DataFrame.

        Args:
            auto_suggest_if_missing: Whether to auto-suggest grouping if absent.

        Returns:
            DataFrame with ``timestamp``, ``Trend``, ``Seasonality``, and ``Noise``
            columns where available.
        """
        if self._grouping is None and auto_suggest_if_missing:
            self._ensure_grouping()

        ssa = self._ensure_ssa()
        frame = pd.DataFrame({"timestamp": self._series.index})

        trend = ssa.get_reconstructed_series("trend")
        seasonality = ssa.get_reconstructed_series("seasonality")
        noise = ssa.get_reconstructed_series("noise")

        frame["Trend"] = trend.values if trend is not None else np.nan
        frame["Seasonality"] = seasonality.values if seasonality is not None else np.nan
        frame["Noise"] = noise.values if noise is not None else np.nan
        return frame

    def _build_step3_summary(self, eps: float = 1e-12) -> SSAResultSummary:
        """Create a Step-3 summary object for rank diagnostics.

        Args:
            eps: Numerical floor used in AIC-related log computations.

        Returns:
            Prepared :class:`SSAResultSummary` instance.
        """
        self._ensure_grouping()
        return SSAResultSummary(self._ensure_ssa(), self._series, self.get_window(), eps=eps)

    def get_variance_explained_plot(self) -> go.Figure:
        """Get Step-3 cumulative explained-variance-by-rank plot.

        Returns:
            Plotly figure from :class:`SSAResultSummary`.
        """
        return self._build_step3_summary().plot_variance_explained()

    def get_noise_variance_plot(self) -> go.Figure:
        """Get Step-3 remaining-noise-variance-by-rank plot.

        Returns:
            Plotly figure from :class:`SSAResultSummary`.
        """
        return self._build_step3_summary().plot_noise_variance()

    def generate_observation_text(self) -> str:
        """Get the auto-generated observation narrative for Step 3.

        Returns:
            Multi-paragraph text combining sampling, statistics, decomposition,
            and residual-diagnostic interpretation.
        """
        return self._build_step3_summary().build_observation_text()
