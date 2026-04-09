"""SSA summary generation for diagnostics and observation logging text."""

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from tseda.series_stats.sampling_prop import SamplingProp
from tseda.series_stats.summary_statistics import SummaryStatistics


class SSAResultSummary:
    """Summarize rank-wise SSA explained/noise variance and AIC diagnostics."""

    def __init__(self, ssa_obj: Any, series: pd.Series, window_size: int, eps: float = 1e-12) -> None:
        """Initialize the summary engine and compute rank-wise diagnostics.

        Args:
            ssa_obj: Active SSA decomposition object.
            series: Input series used for baseline variance estimates.
            window_size: SSA window size (max rank cap).
            eps: Minimum positive floor used in log-variance terms.
        """
        self._ssa_obj = ssa_obj
        self._series = series
        self._window_size = int(window_size)
        self._eps = float(eps)

        self._ranks: np.ndarray | None = None
        self._explained_ratio: np.ndarray | None = None
        self._noise_ratio: np.ndarray | None = None
        self._aic_exp_var: np.ndarray | None = None
        self._aic_noise_var: np.ndarray | None = None
        self._n_obs = 0
        self._compute()

    def _compute(self) -> None:
        if self._ssa_obj is None:
            raise ValueError("SSA object is not initialized.")

        eigenvalues = np.asarray(getattr(self._ssa_obj, "_eigenvalues", []), dtype=float)
        if eigenvalues.size == 0:
            raise ValueError("SSA eigenvalues are unavailable.")

        max_rank = min(self._window_size, eigenvalues.size)
        if max_rank <= 0:
            raise ValueError("No valid rank available for SSA summary.")

        self._ranks = np.arange(1, max_rank + 1)

        total_variance = float(np.sum(eigenvalues[:max_rank]))
        if total_variance <= 0:
            raise ValueError("Total SSA variance is non-positive.")

        self._explained_ratio = np.cumsum(eigenvalues[:max_rank]) / total_variance
        self._noise_ratio = 1.0 - self._explained_ratio

        series_values = pd.to_numeric(self._series, errors="coerce").dropna().values.astype(float)
        self._n_obs = len(series_values)
        if self._n_obs == 0:
            raise ValueError("Series values are not numeric.")

        if self._n_obs > 1:
            baseline_variance = float(np.var(series_values, ddof=1))
        else:
            baseline_variance = float(np.var(series_values))
        baseline_variance = max(baseline_variance, self._eps)

        sigma2_exp_var = np.maximum((1.0 - self._explained_ratio) * baseline_variance, self._eps)
        sigma2_noise_var = np.maximum(self._noise_ratio * baseline_variance, self._eps)

        self._aic_exp_var = (self._n_obs * np.log(sigma2_exp_var)) + (2.0 * self._ranks)
        self._aic_noise_var = (self._n_obs * np.log(sigma2_noise_var)) + (2.0 * self._ranks)

    def formulas(self) -> dict[str, str]:
        """Return symbolic formulas used in rank-based diagnostics."""
        return {
            "ev": "EV(r) = sum_{i=1..r}(lambda_i) / sum_{i=1..L}(lambda_i)",
            "noise_var": "sigma2_noise(r) = sigma2_total * (1 - EV(r))",
            "meta": f"n = {self._n_obs}, eps = {self._eps:.0e}",
        }

    def plot_variance_explained(self) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=self._ranks,
                y=self._explained_ratio,
                mode="lines+markers",
                name="Explained Variance Ratio",
                line=dict(color="seagreen"),
            )
        )
        fig.update_layout(
            title="Variance Explained vs Rank",
            xaxis_title="Rank (r)",
            yaxis_title="Explained Variance Ratio",
        )
        return fig

    def plot_noise_variance(self) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=self._ranks,
                y=self._noise_ratio,
                mode="lines+markers",
                name="Noise Variance Ratio",
                line=dict(color="firebrick"),
            )
        )
        fig.update_layout(
            title="Noise Variance vs Rank",
            xaxis_title="Rank (r)",
            yaxis_title="Unexplained Variance Ratio",
        )
        return fig

    # ------------------------------------------------------------------
    # Observation text helpers
    # ------------------------------------------------------------------

    def _sampling_observation(self) -> str:
        """Build a paragraph summarising the sampling properties of the series."""
        try:
            sp = SamplingProp(self._series)
            return (
                f"Sampling properties: The series contains {sp._N} observations spanning "
                f"{sp._start_ts} to {sp._end_ts} (duration: {sp._duration}). "
                f"The inferred sampling frequency is {sp._sampling_freq}."
            )
        except Exception as exc:
            return f"Sampling properties could not be determined ({exc})."

    def _statistics_observation(self) -> str:
        """Build a paragraph summarising the descriptive statistics of the series."""
        try:
            stats_df = SummaryStatistics(self._series).compute_statistics()
            s = dict(zip(stats_df["statistic"], stats_df["value"]))
            return (
                f"Descriptive statistics: mean = {s.get('mean', float('nan')):.4g}, "
                f"median = {s.get('median', float('nan')):.4g}, "
                f"std dev = {s.get('std_dev', float('nan')):.4g}, "
                f"min = {s.get('min', float('nan')):.4g}, "
                f"max = {s.get('max', float('nan')):.4g}, "
                f"skewness = {s.get('skewness', float('nan')):.4g}, "
                f"kurtosis = {s.get('kurtosis', float('nan')):.4g}."
            )
        except Exception as exc:
            return f"Descriptive statistics could not be computed ({exc})."

    def _ssa_decomposition_observation(self) -> str:
        """Build a paragraph summarising the SSA decomposition details."""
        ssa = self._ssa_obj

        n_components = int(getattr(ssa, "_window", self._window_size))

        has_recon = hasattr(ssa, "_recon")
        smoothed_var_pct: float | None = None
        noise_var_pct: float | None = None

        if has_recon:
            try:
                ssa._ensure_reconstruction_cache()
                signal_keys = [k for k in ssa._recon.keys() if k.casefold() != "noise"]
                noise_keys = [k for k in ssa._recon.keys() if k.casefold() == "noise"]

                if signal_keys:
                    smoothed_var_pct = sum(
                        ssa.explained_variance_by_group(k) for k in signal_keys
                    )
                if noise_keys:
                    noise_var_pct = ssa.explained_variance_by_group(noise_keys[0])
            except Exception:
                pass

        seasonality_flag = bool(getattr(ssa, "_seasonality_check_heuristic", False))

        lines = [
            f"SSA decomposition: The analysis used a window size of {self._window_size} "
            f"with {n_components} components available in the decomposition."
        ]

        if smoothed_var_pct is not None:
            lines.append(
                f"The smoothed signal explains {smoothed_var_pct:.2f}% of the total variance."
            )
        if noise_var_pct is not None:
            lines.append(
                f"The noise signal accounts for {noise_var_pct:.2f}% of the total variance; "
                "this percentage is the estimate of noise in the data."
            )

        if seasonality_flag:
            lines.append(
                "The seasonality heuristic indicates that the data appears to have seasonality "
                "(near-equal leading eigenvalues detected)."
            )

        return " ".join(lines)

    def _durbin_watson_observation(self) -> str:
        """Build a paragraph reporting the Durbin-Watson statistic for the noise signal."""
        ssa = self._ssa_obj
        dw = getattr(ssa, "_durbin_watson", None)

        if dw is None:
            return (
                "Durbin-Watson statistic: Not available. Apply component grouping in Step 2 "
                "to compute this diagnostic."
            )

        dw_val = float(dw)
        in_range = 1.5 <= dw_val <= 2.5

        if in_range:
            guidance = (
                "This value falls within the acceptable range of 1.5 to 2.5, "
                "suggesting the noise residuals are approximately uncorrelated."
            )
        else:
            guidance = (
                "This value is outside the acceptable range of 1.5 to 2.5. "
                "Consider adjusting the window size and component grouping in Step 2 "
                "to bring the Durbin-Watson statistic into the desired range."
            )

        return (
            f"Durbin-Watson noise statistic: {dw_val:.4f}. "
            f"A value between 1.5 and 2.5 is generally considered acceptable to treat "
            f"the noise as uncorrelated. {guidance}"
        )

    def _modeling_recommendation(self) -> str:
        """Return a standard recommendation paragraph for the analyst."""
        return (
            "Recommendation: Please correlate the findings above with your modeling, "
            "control, and monitoring objectives. The decomposition provides a basis for "
            "understanding the trend, periodic behaviour, and noise characteristics of "
            "the series, which should inform feature engineering, model selection, and "
            "appropriate monitoring thresholds."
        )

    def build_observation_text(self) -> str:
        """Compose the full auto-generated observation string from all section helpers.

        Returns:
            str: Multi-paragraph observation text suitable for the logging panel textarea.
        """
        sections = [
            self._sampling_observation(),
            self._statistics_observation(),
            self._ssa_decomposition_observation(),
            self._durbin_watson_observation(),
            self._modeling_recommendation(),
        ]
        return "\n\n".join(sections)
