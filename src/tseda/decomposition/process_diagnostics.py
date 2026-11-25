"""Process-aware diagnostics for SSA spectra and reconstructed periodicity."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
from typing import Any, Sequence
import warnings

import numpy as np
import pandas as pd
from ssalib import SingularSpectrumAnalysis
from statsmodels.tsa.stattools import adfuller, kpss

from tseda.config.config_loader import ConfigurationManager

_PROCESS_CACHE: dict[tuple[str, ...], ProcessAnalysisResult] = {}
_PROCESS_CACHE_LIMIT = 32


def _as_finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


@dataclass(slots=True)
class PeriodicComponent:
    """Verified cadence-appropriate periodic SSA component."""

    scope: str
    period: float
    accepted_period_band: tuple[float, float]
    confidence: float
    eigenvalue_pair: tuple[int, int]
    window: int
    seasonal_strength: float
    cycle_count: float

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return {
            "scope": self.scope,
            "period": self.period,
            "accepted_period_band": list(self.accepted_period_band),
            "confidence": self.confidence,
            "eigenvalue_pair": list(self.eigenvalue_pair),
            "window": self.window,
            "seasonal_strength": self.seasonal_strength,
            "cycle_count": self.cycle_count,
        }


@dataclass(slots=True)
class PersistentComponent:
    """Stochastic low-frequency SSA component."""

    scope: str
    component_indices: tuple[int, ...]
    null_compatibility: str
    monte_carlo_percentile: float | None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return {
            "scope": self.scope,
            "component_indices": list(self.component_indices),
            "null_compatibility": self.null_compatibility,
            "monte_carlo_percentile": self.monte_carlo_percentile,
        }


@dataclass(slots=True)
class DiagnosticEvidence:
    """Observable evidence used for process classification."""

    sample_count: int
    window: int
    top_k_ratio: float
    level_top_one_ratio: float
    level_decay_slope: float | None
    level_decay_r_squared: float | None
    leading_eof_smoothness: float | None
    differenced_top_k_ratio: float | None
    differenced_top_one_ratio: float | None
    differenced_decay_slope: float | None
    adf_level_pvalue: float | None
    adf_trend_pvalue: float | None
    adf_difference_pvalue: float | None
    kpss_level_pvalue: float | None
    dominant_period: float | None
    dominant_period_strength: float | None
    monte_carlo_status: str = "not_run"
    monte_carlo_percentile: float | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return {
            "sample_count": self.sample_count,
            "window": self.window,
            "top_k_ratio": self.top_k_ratio,
            "level_top_one_ratio": self.level_top_one_ratio,
            "level_decay_slope": self.level_decay_slope,
            "level_decay_r_squared": self.level_decay_r_squared,
            "leading_eof_smoothness": self.leading_eof_smoothness,
            "differenced_top_k_ratio": self.differenced_top_k_ratio,
            "differenced_top_one_ratio": self.differenced_top_one_ratio,
            "differenced_decay_slope": self.differenced_decay_slope,
            "adf_level_pvalue": self.adf_level_pvalue,
            "adf_trend_pvalue": self.adf_trend_pvalue,
            "adf_difference_pvalue": self.adf_difference_pvalue,
            "kpss_level_pvalue": self.kpss_level_pvalue,
            "dominant_period": self.dominant_period,
            "dominant_period_strength": self.dominant_period_strength,
            "monte_carlo_status": self.monte_carlo_status,
            "monte_carlo_percentile": self.monte_carlo_percentile,
            "notes": list(self.notes),
        }


@dataclass(slots=True)
class ProcessClassification:
    """Semantic process class independent from decomposition grouping."""

    scope: str
    label: str
    subtype: str | None
    confidence: float | None
    evidence: DiagnosticEvidence

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return {
            "scope": self.scope,
            "label": self.label,
            "subtype": self.subtype,
            "confidence": self.confidence,
            "evidence": self.evidence.to_dict(),
        }


@dataclass(slots=True)
class DecompositionSuitability:
    """Whether deterministic SSA reconstruction is supported."""

    scope: str
    status: str
    reason: str
    evidence: DiagnosticEvidence

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return {
            "scope": self.scope,
            "status": self.status,
            "reason": self.reason,
            "evidence": self.evidence.to_dict(),
        }


@dataclass(slots=True)
class ProcessAnalysisResult:
    """Process-aware result for one full-series or active-regime scope."""

    schema_version: str
    scope: str
    process_classification: ProcessClassification
    decomposition_suitability: DecompositionSuitability
    periodic_components: list[PeriodicComponent] = field(default_factory=list)
    persistent_components: list[PersistentComponent] = field(default_factory=list)
    evidence: DiagnosticEvidence | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        evidence = self.evidence or self.process_classification.evidence
        return {
            "schema_version": self.schema_version,
            "scope": self.scope,
            "process_classification": self.process_classification.to_dict(),
            "decomposition_suitability": self.decomposition_suitability.to_dict(),
            "periodic_components": [item.to_dict() for item in self.periodic_components],
            "persistent_components": [item.to_dict() for item in self.persistent_components],
            "evidence": evidence.to_dict(),
        }


def infer_cadence_name(index: pd.Index) -> str:
    """Infer a coarse cadence name without importing notebook-level services."""
    if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
        return "unknown"
    deltas = pd.Series(index.sort_values()).diff().dropna()
    if deltas.empty:
        return "unknown"
    median = deltas.median()
    if pd.isna(median):
        return "unknown"
    minutes = float(median.total_seconds() / 60.0)
    if minutes < 60:
        return "subhourly"
    if minutes < 24 * 60:
        return "hourly"
    if minutes <= 24 * 60:
        return "business_daily" if index.inferred_freq == "B" else "daily"
    if minutes <= 7 * 24 * 60:
        return "weekly"
    if minutes <= 32 * 24 * 60:
        return "monthly"
    return "quarterly"


def _candidate_periods_for_cadence(cadence: str) -> list[float]:
    configured = ConfigurationManager.get(
        f"process_periodicity.candidate_periods_by_cadence.{cadence}",
        [],
    )
    if cadence == "business_daily":
        configured = ConfigurationManager.get(
            "process_periodicity.candidate_periods_by_cadence.business_daily",
            [5],
        )
    values: list[float] = []
    for raw in configured if isinstance(configured, list) else []:
        try:
            period = float(raw)
        except (TypeError, ValueError):
            continue
        if period >= 2:
            values.append(period)
    return sorted(set(values))


def _fit_spectral_period(values: np.ndarray, min_cycles: float = 3.0) -> tuple[float | None, float]:
    values = np.asarray(values, dtype=float)
    n = int(values.size)
    if n < 8:
        return None, 0.0
    x = np.arange(n, dtype=float)
    detrended = values - np.polyval(np.polyfit(x, values, 1), x)
    power = np.abs(np.fft.rfft(detrended - np.mean(detrended))) ** 2
    frequencies = np.fft.rfftfreq(n)
    periods = np.divide(
        1.0,
        frequencies,
        out=np.full_like(frequencies, np.inf),
        where=frequencies > 0,
    )
    valid = (periods >= 2.0) & (periods <= n / max(min_cycles, 1.0))
    if not np.any(valid) or float(np.sum(power[valid])) <= 0.0:
        return None, 0.0
    indices = np.flatnonzero(valid)
    best = int(indices[int(np.argmax(power[indices]))])
    return float(periods[best]), float(power[best] / np.sum(power[valid]))


def _period_strength_at(values: np.ndarray, period: float) -> float:
    """Return Fourier power share at the frequency nearest a candidate period."""
    values = np.asarray(values, dtype=float)
    n = int(values.size)
    if n < 8 or period < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    detrended = values - np.polyval(np.polyfit(x, values, 1), x)
    power = np.abs(np.fft.rfft(detrended - np.mean(detrended))) ** 2
    frequencies = np.fft.rfftfreq(n)
    valid = frequencies > 0
    if not np.any(valid) or float(np.sum(power[valid])) <= 0.0:
        return 0.0
    periods = 1.0 / frequencies[valid]
    indices = np.flatnonzero(valid)
    best = indices[int(np.argmin(np.abs(periods - period)))]
    return float(power[best] / np.sum(power[valid]))


def _spectrum_features(
    series: pd.Series,
    window: int,
) -> tuple[np.ndarray, np.ndarray | None, float | None, float | None, SingularSpectrumAnalysis]:
    model = SingularSpectrumAnalysis(series, window=window)
    model.decompose()
    eigenvalues = np.asarray(model.eigenvalues, dtype=float)
    u_matrix = np.asarray(model.decomposition_results[0], dtype=float)
    tail_start = min(max(2, int(round(len(eigenvalues) * 0.05))), len(eigenvalues) - 2)
    tail_end = max(tail_start + 2, int(math.floor(len(eigenvalues) * 0.75)))
    tail_end = min(tail_end, len(eigenvalues))
    if tail_end - tail_start < 2:
        return eigenvalues, u_matrix, None, None, model
    ranks = np.arange(tail_start + 1, tail_end + 1, dtype=float)
    target = np.log(np.maximum(eigenvalues[tail_start:tail_end], np.finfo(float).tiny))
    coeff = np.polyfit(np.log(ranks), target, 1)
    fitted = np.polyval(coeff, np.log(ranks))
    residual = float(np.sum((target - fitted) ** 2))
    total = float(np.sum((target - np.mean(target)) ** 2))
    r_squared = 1.0 - residual / total if total > 0.0 else None
    return eigenvalues, u_matrix, float(coeff[0]), r_squared, model


def _periodic_pair_evidence(
    series: pd.Series,
    period: float,
    window: int,
    scope: str,
    min_cycles_override: float | None = None,
) -> PeriodicComponent | None:
    min_period_strength = float(ConfigurationManager.get("process_periodicity.min_period_strength", 0.30))
    pair_tolerance = float(
        ConfigurationManager.get("process_periodicity.pair_similarity_tolerance", 0.20)
    )
    max_period_error = float(ConfigurationManager.get("process_periodicity.max_period_error", 0.15))
    min_cycles = float(
        min_cycles_override
        if min_cycles_override is not None
        else ConfigurationManager.get("process_periodicity.min_complete_cycles", 5.0)
    )
    n = int(len(series))
    cycle_count = n / float(period)
    if cycle_count < min_cycles or window < 2 or window > n // 2:
        return None

    source_values = series.to_numpy(dtype=float)
    if source_values.size >= 3:
        x = np.arange(source_values.size, dtype=float)
        source_values = source_values - np.polyval(np.polyfit(x, source_values, 1), x)
    working_series = pd.Series(source_values, index=series.index)
    eigenvalues, _, _, _, model = _spectrum_features(working_series, window)
    leading = min(max(2, window - 1), 16)
    best: PeriodicComponent | None = None
    for left in range(leading - 1):
        right = left + 1
        larger = max(float(eigenvalues[left]), float(eigenvalues[right]))
        if larger <= 0.0:
            continue
        pair_difference = abs(float(eigenvalues[left]) - float(eigenvalues[right])) / larger
        if pair_difference > pair_tolerance:
            continue

        model.reconstruct({"Candidate": [left, right]})
        reconstructed = pd.to_numeric(
            model.to_frame()["Candidate"], errors="coerce"
        ).dropna()
        fitted_period, fitted_strength = _fit_spectral_period(
            reconstructed.to_numpy(dtype=float),
            min_cycles=min_cycles,
        )
        if fitted_period is None:
            continue
        relative_error = abs(fitted_period - period) / period
        if relative_error > max_period_error or fitted_strength < min_period_strength:
            continue

        confidence = float(
            max(0.0, 1.0 - pair_difference / pair_tolerance)
            * max(0.0, 1.0 - relative_error / max_period_error)
            * min(1.0, fitted_strength / min_period_strength)
        )
        component = PeriodicComponent(
            scope=scope,
            period=fitted_period,
            accepted_period_band=(period * (1.0 - max_period_error), period * (1.0 + max_period_error)),
            confidence=confidence,
            eigenvalue_pair=(left, right),
            window=window,
            seasonal_strength=fitted_strength,
            cycle_count=cycle_count,
        )
        if best is None or component.confidence > best.confidence:
            best = component
    return best


def _safe_adf(values: np.ndarray, *, regression: str = "c") -> float | None:
    if values.size < 8:
        return None
    try:
        return _as_finite_float(adfuller(values, regression=regression, autolag="AIC")[1])
    except (ValueError, np.linalg.LinAlgError):
        return None


def _safe_kpss(values: np.ndarray) -> float | None:
    if values.size < 8:
        return None
    try:
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", category=Warning)
            return _as_finite_float(kpss(values, regression="c", nlags="auto")[1])
    except (ValueError, np.linalg.LinAlgError):
        return None


def _contiguous_runs(series: pd.Series) -> list[pd.Series]:
    """Return contiguous cadence runs without interpolating source gaps."""
    if not isinstance(series.index, pd.DatetimeIndex) or len(series) < 3:
        return [series]
    ordered = series.sort_index()
    deltas = pd.Series(ordered.index).diff().dropna()
    if deltas.empty:
        return [ordered]
    cadence = deltas.median()
    if pd.isna(cadence):
        return [ordered]
    starts = pd.Series(ordered.index).diff().fillna(cadence).gt(cadence * 1.5).cumsum().to_numpy()
    return [
        ordered.iloc[np.flatnonzero(starts == run)]
        for run in sorted(set(starts))
    ]


def _aggregate_periodic_evidence(
    components: list[tuple[PeriodicComponent, int]],
    period: float,
    scope: str,
) -> PeriodicComponent | None:
    if not components:
        return None
    min_cycles = float(ConfigurationManager.get("process_periodicity.min_complete_cycles", 5.0))
    total_observations = sum(observations for _, observations in components)
    aggregate_cycles = total_observations / period
    if aggregate_cycles < min_cycles:
        return None
    weighted_period = sum(item.period * observations for item, observations in components) / total_observations
    weighted_strength = sum(item.seasonal_strength * observations for item, observations in components) / total_observations
    weighted_confidence = sum(item.confidence * observations for item, observations in components) / total_observations
    best, _ = max(components, key=lambda item: item[1])
    return PeriodicComponent(
        scope=scope,
        period=weighted_period,
        accepted_period_band=best.accepted_period_band,
        confidence=weighted_confidence,
        eigenvalue_pair=best.eigenvalue_pair,
        window=best.window,
        seasonal_strength=weighted_strength,
        cycle_count=aggregate_cycles,
    )


def monte_carlo_persistence_percentile(
    values: np.ndarray,
    window: int,
    *,
    replicates: int = 49,
    seed: int = 20261125,
) -> tuple[float, str]:
    """Compare the observed SSA signature with matched Gaussian random walks."""
    values = np.asarray(values, dtype=float)
    if values.size < 8:
        return math.nan, "insufficient_data"
    increments = np.diff(values)
    drift = float(np.mean(increments))
    innovation_scale = float(np.std(increments, ddof=1))
    if not np.isfinite(innovation_scale) or innovation_scale <= np.finfo(float).eps:
        return math.nan, "zero_innovation_scale"

    def _signature(candidate: np.ndarray) -> np.ndarray:
        series = pd.Series(candidate)
        effective_window = max(2, min(int(window), len(series) // 2))
        eigenvalues, u_matrix, slope, r_squared, _ = _spectrum_features(series, effective_window)
        ratios = eigenvalues / float(np.sum(eigenvalues))
        top_k = min(5, len(ratios))
        differences = np.diff(candidate)
        diff_window = max(2, min(effective_window, len(differences) // 2))
        diff_eigenvalues, _, _, _, _ = _spectrum_features(pd.Series(differences), diff_window)
        diff_ratios = diff_eigenvalues / float(np.sum(diff_eigenvalues))
        smoothness = (
            float(np.mean(np.abs(np.diff(u_matrix[:, 0]))))
            if u_matrix is not None and u_matrix.shape[0] > 1
            else 0.0
        )
        return np.array([
            float(ratios[0]),
            float(np.sum(ratios[:top_k])),
            float(slope if slope is not None else 0.0),
            float(r_squared if r_squared is not None else 0.0),
            smoothness,
            float(diff_ratios[0]),
            float(np.sum(diff_ratios[: min(top_k, len(diff_ratios))])),
        ])

    observed = _signature(values)
    rng = np.random.default_rng(seed)
    surrogate_signatures = np.asarray([
        _signature(
            np.cumsum(
                rng.normal(drift, innovation_scale, values.size)
            )
        )
        for _ in range(max(1, int(replicates)))
    ])
    center = np.median(surrogate_signatures, axis=0)
    spread = np.maximum(
        np.median(np.abs(surrogate_signatures - center), axis=0) * 1.4826,
        1e-12,
    )
    distances = np.mean(np.abs((surrogate_signatures - center) / spread), axis=1)
    observed_distance = float(np.mean(np.abs((observed - center) / spread)))
    percentile = float(np.mean(distances <= observed_distance))
    return percentile, "completed"


def analyze_process(
    series: pd.Series,
    window: int,
    *,
    scope: str = "active_regime",
    extra_periods: Sequence[float] | None = None,
    run_monte_carlo: bool = False,
) -> ProcessAnalysisResult:
    """Classify process behavior using level, differenced, and periodic SSA evidence."""
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    n = int(values.size)
    if n < 4:
        raise ValueError("Process analysis requires at least four finite observations.")
    if not np.all(np.isfinite(values)):
        raise ValueError("Process analysis requires finite numeric values.")
    cadence = infer_cadence_name(series.index)
    timestamp_bytes = (
        series.index.asi8.tobytes()
        if isinstance(series.index, pd.DatetimeIndex)
        else repr(series.index).encode()
    )
    cache_digest = hashlib.blake2b(
        values.tobytes() + timestamp_bytes,
        digest_size=16,
    ).hexdigest()
    cache_key = (cache_digest, str(int(window)), scope, cadence, str(run_monte_carlo))
    cached = _PROCESS_CACHE.get(cache_key)
    if cached is not None:
        return cached
    if float(np.var(values)) <= np.finfo(float).eps:
        evidence = DiagnosticEvidence(
            sample_count=n,
            window=int(window),
            top_k_ratio=0.0,
            level_top_one_ratio=0.0,
            level_decay_slope=None,
            level_decay_r_squared=None,
            leading_eof_smoothness=None,
            differenced_top_k_ratio=None,
            differenced_top_one_ratio=None,
            differenced_decay_slope=None,
            adf_level_pvalue=None,
            adf_trend_pvalue=None,
            adf_difference_pvalue=None,
            kpss_level_pvalue=None,
            dominant_period=None,
            dominant_period_strength=0.0,
            notes=["constant_series"],
        )
        classification = ProcessClassification(scope, "indeterminate", None, None, evidence)
        suitability = DecompositionSuitability(scope, "indeterminate", "constant_series", evidence)
        result = ProcessAnalysisResult("1.0", scope, classification, suitability, evidence=evidence)
        _PROCESS_CACHE[cache_key] = result
        return result

    finite_window = max(2, min(int(window), n // 2))
    clean_series = pd.Series(values, index=pd.RangeIndex(n))
    eigenvalues, u_matrix, decay_slope, decay_r2, _ = _spectrum_features(clean_series, finite_window)
    ratios = eigenvalues / float(np.sum(eigenvalues))
    top_k = min(
        int(ConfigurationManager.get("suitability_check.top_k_eigenvectors", 5)),
        len(ratios),
    )
    top_k_ratio = float(np.sum(ratios[:top_k]))
    eof_smoothness = (
        float(np.mean(np.abs(np.diff(u_matrix[:, 0]))))
        if u_matrix is not None and u_matrix.shape[0] > 1
        else None
    )

    differenced = np.diff(values)
    diff_top_k_ratio: float | None = None
    diff_top_one_ratio: float | None = None
    diff_slope: float | None = None
    diff_ratios = np.array([], dtype=float)
    if differenced.size >= 6 and float(np.var(differenced)) > np.finfo(float).eps:
        diff_window = max(2, min(finite_window, differenced.size // 2))
        diff_eigenvalues, _, diff_slope, _, _ = _spectrum_features(
            pd.Series(differenced, index=pd.RangeIndex(differenced.size)),
            diff_window,
        )
        diff_ratios = diff_eigenvalues / float(np.sum(diff_eigenvalues))
        diff_top_k_ratio = float(np.sum(diff_ratios[: min(top_k, len(diff_ratios))]))
        diff_top_one_ratio = float(diff_ratios[0])

    dominant_period, dominant_strength = _fit_spectral_period(values)
    configured_periods = _candidate_periods_for_cadence(cadence)
    candidate_periods = list(configured_periods)
    min_cycles = float(ConfigurationManager.get("process_periodicity.min_complete_cycles", 5.0))
    if dominant_period is not None and dominant_period >= 2 and n / dominant_period >= min_cycles:
        candidate_periods.append(float(dominant_period))
    if extra_periods:
        candidate_periods.extend(float(period) for period in extra_periods if float(period) >= 2)
    candidate_periods = sorted(set(round(period, 8) for period in candidate_periods))

    periodic_components: list[PeriodicComponent] = []
    for candidate in candidate_periods[: int(ConfigurationManager.get("process_compute.max_candidate_periods", 8))]:
        candidate_window = int(round(candidate))
        if candidate_window > n // 2 or candidate_window < 2:
            continue
        component = _periodic_pair_evidence(
            clean_series,
            candidate,
            candidate_window,
            scope,
        )
        candidate_strength = _period_strength_at(values, candidate)
        minimum_candidate_strength = float(
            ConfigurationManager.get(
                "process_periodicity.min_candidate_spectral_strength",
                0.025,
            )
        )
        if component is not None and candidate_strength >= minimum_candidate_strength:
            periodic_components.append(component)
            continue

        runs = _contiguous_runs(series)
        aggregate_components: list[tuple[PeriodicComponent, int]] = []
        attempted_chunks = 0
        if len(runs) > 1:
            for run in runs:
                if len(run) < candidate_window * 2:
                    continue
                attempted_chunks += 1
                run_component = _periodic_pair_evidence(
                    run.reset_index(drop=True),
                    candidate,
                    candidate_window,
                    scope,
                    min_cycles_override=2.0,
                )
                if run_component is not None:
                    aggregate_components.append((run_component, len(run)))
        else:
            run_width = max(candidate_window * 4, candidate_window * 2 + 1)
            for start in range(0, n, max(run_width // 2, 1)):
                chunk = clean_series.iloc[start : min(n, start + run_width)]
                if len(chunk) < run_width:
                    continue
                attempted_chunks += 1
                chunk_component = _periodic_pair_evidence(
                    chunk.reset_index(drop=True),
                    candidate,
                    candidate_window,
                    scope,
                    min_cycles_override=3.0,
                )
                if chunk_component is not None:
                    aggregate_components.append((chunk_component, len(chunk)))

        minimum_support = max(2, int(math.ceil(attempted_chunks * 0.5)))
        aggregate = (
            _aggregate_periodic_evidence(aggregate_components, candidate, scope)
            if len(aggregate_components) >= minimum_support
            else None
        )
        if aggregate is not None:
            periodic_components.append(aggregate)

    deduplicated_components: list[PeriodicComponent] = []
    for component in periodic_components:
        matching = next(
            (
                existing
                for existing in deduplicated_components
                if abs(existing.period - component.period)
                <= max(existing.period, component.period)
                * float(ConfigurationManager.get("process_periodicity.max_period_error", 0.15))
            ),
            None,
        )
        if matching is None:
            deduplicated_components.append(component)
        elif component.confidence > matching.confidence:
            deduplicated_components[deduplicated_components.index(matching)] = component
    periodic_components = deduplicated_components
    max_period_error = float(
        ConfigurationManager.get("process_periodicity.max_period_error", 0.15)
    )
    periodic_components = [
        component
        for component in periodic_components
        if component.confidence >= 0.50
        or any(
            abs(component.period - configured)
            <= max(component.period, configured) * max_period_error
            for configured in configured_periods
        )
    ]

    adf_level = _safe_adf(values)
    adf_trend = _safe_adf(values, regression="ct")
    adf_difference = _safe_adf(differenced)
    kpss_level = _safe_kpss(values)
    evidence = DiagnosticEvidence(
        sample_count=n,
        window=finite_window,
        top_k_ratio=top_k_ratio,
        level_top_one_ratio=float(ratios[0]),
        level_decay_slope=decay_slope,
        level_decay_r_squared=decay_r2,
        leading_eof_smoothness=eof_smoothness,
        differenced_top_k_ratio=diff_top_k_ratio,
        differenced_top_one_ratio=diff_top_one_ratio,
        differenced_decay_slope=diff_slope,
        adf_level_pvalue=adf_level,
        adf_trend_pvalue=adf_trend,
        adf_difference_pvalue=adf_difference,
        kpss_level_pvalue=kpss_level,
        dominant_period=dominant_period,
        dominant_period_strength=dominant_strength,
    )

    min_fit = float(ConfigurationManager.get("process_classification.power_law_fit_min", 0.90))
    slope_target = float(ConfigurationManager.get("process_classification.power_law_slope_target", -2.0))
    smoothness_max = float(ConfigurationManager.get("process_classification.eof_smoothness_max", 0.02))
    diff_concentration_max = float(
        ConfigurationManager.get("process_classification.differenced_concentration_max", 0.55)
    )
    adf_alpha = float(ConfigurationManager.get("process_classification.adf_alpha", 0.05))
    kpss_alpha = float(ConfigurationManager.get("process_classification.kpss_alpha", 0.05))
    persistence_score = 0.0
    if float(ratios[0]) >= 0.50:
        persistence_score += 1.0
    if decay_slope is not None and decay_r2 is not None:
        if decay_slope < -1.5 and abs(decay_slope - slope_target) <= 1.0 and decay_r2 >= min_fit:
            persistence_score += 1.0
    if eof_smoothness is not None and eof_smoothness <= smoothness_max:
        persistence_score += 1.0
    effective_diff_concentration = min(
        value
        for value in (diff_top_one_ratio, diff_top_k_ratio)
        if value is not None
    ) if diff_top_one_ratio is not None or diff_top_k_ratio is not None else None
    if effective_diff_concentration is not None and effective_diff_concentration <= diff_concentration_max:
        persistence_score += 1.0
    if adf_level is not None and adf_difference is not None:
        if adf_level > adf_alpha and adf_difference <= adf_alpha:
            persistence_score += 1.0
    if kpss_level is not None and kpss_level <= kpss_alpha:
        persistence_score += 1.0
    persistence_supported = persistence_score >= 5.0

    persistent_components: list[PersistentComponent] = []
    if top_k_ratio < float(ConfigurationManager.get("suitability_check.min_explained_variance", 0.40)):
        label = "diffuse_noise"
        subtype = None
        confidence = 0.9
    elif periodic_components and persistence_supported:
        label = "mixed"
        subtype = "persistent_with_periodicity"
        confidence = min(
            1.0,
            (persistence_score / 6.0) + max(item.confidence for item in periodic_components),
        ) / 2.0
        persistent_components.append(
            PersistentComponent(
                scope=scope,
                component_indices=(0,),
                null_compatibility="mixed_persistence",
                monte_carlo_percentile=None,
            )
        )
    elif persistence_supported:
        label = "stochastic_persistence"
        subtype = "unit_root_like" if adf_level is not None and adf_level > adf_alpha else "high_persistence_ar"
        confidence = persistence_score / 6.0
        persistent_components.append(
            PersistentComponent(
                scope=scope,
                component_indices=(0,),
                null_compatibility="random_walk" if subtype == "unit_root_like" else "high_persistence_ar",
                monte_carlo_percentile=None,
            )
        )
    elif periodic_components:
        label = "periodic"
        subtype = None
        confidence = max(item.confidence for item in periodic_components)
    elif adf_level is not None and adf_level <= adf_alpha:
        label = "stationary_irregular"
        subtype = None
        confidence = 0.65
    else:
        label = "indeterminate"
        subtype = None
        confidence = 0.35
        evidence.notes.append("persistent_or_deterministic_trend_not_distinguishable")

    evidence.monte_carlo_status = "not_run" if not persistence_supported else "deferred"
    if persistence_supported and run_monte_carlo:
        replicates = int(
            ConfigurationManager.get("process_classification.monte_carlo_replicates", 199)
        )
        fast_budget = int(
            ConfigurationManager.get("process_classification.fast_monte_carlo_replicates", 49)
        )
        mode = str(ConfigurationManager.get("process_compute.interactive_mode", "fast"))
        evidence.monte_carlo_percentile, evidence.monte_carlo_status = (
            monte_carlo_persistence_percentile(
                values,
                finite_window,
                replicates=fast_budget if mode == "fast" else replicates,
            )
        )
    evidence.notes.append("periodic_candidates=" + ",".join(f"{item:g}" for item in candidate_periods))
    if (
        label in {"indeterminate", "stochastic_persistence"}
        and adf_level is not None
        and adf_trend is not None
        and adf_level <= adf_alpha
        and adf_trend <= adf_alpha
        and not periodic_components
    ):
        label = "deterministic_trend"
        subtype = None
        confidence = 0.8
        persistent_components = []

    if label == "diffuse_noise":
        suitability = DecompositionSuitability(
            scope,
            "unsuitable",
            "diffuse_eigen_spectrum",
            evidence,
        )
    elif label == "stochastic_persistence":
        suitability = DecompositionSuitability(
            scope,
            "unsuitable",
            "stochastic_persistence_requires_stochastic_or_differenced_analysis",
            evidence,
        )
    elif label == "indeterminate":
        suitability = DecompositionSuitability(
            scope,
            "indeterminate",
            "insufficient_or_contradictory_evidence",
            evidence,
        )
    else:
        suitability = DecompositionSuitability(
            scope,
            "suitable",
            "process_evidence_supports_decomposition",
            evidence,
        )

    classification = ProcessClassification(
        scope=scope,
        label=label,
        subtype=subtype,
        confidence=confidence,
        evidence=evidence,
    )
    result = ProcessAnalysisResult(
        schema_version="1.0",
        scope=scope,
        process_classification=classification,
        decomposition_suitability=suitability,
        periodic_components=periodic_components,
        persistent_components=persistent_components,
        evidence=evidence,
    )
    _PROCESS_CACHE[cache_key] = result
    if len(_PROCESS_CACHE) > _PROCESS_CACHE_LIMIT:
        _PROCESS_CACHE.pop(next(iter(_PROCESS_CACHE)))
    return result
