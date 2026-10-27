"""PELT segmentation helpers and automated model-routing heuristics."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.stats import kurtosis

DEFAULT_MIN_SEGMENT_POINTS: dict[str, int] = {
    "weekly": 12,
    "daily": 90,
    "hourly": 24 * 7 * 3,
}


def infer_cadence_from_series(series: pd.Series) -> str:
    """Infer a coarse cadence label from a datetime-indexed series."""
    if not isinstance(series, pd.Series):
        return "daily"

    index = series.index
    if not isinstance(index, pd.DatetimeIndex):
        return "daily"

    if hasattr(index, "inferred_freq") and index.inferred_freq is not None:
        freq = str(index.inferred_freq).lower()
        if "h" in freq:
            return "hourly"
        if "w" in freq:
            return "weekly"
        if "d" in freq or "b" in freq:
            return "daily"

    if len(index) >= 2:
        deltas = pd.Series(index).diff().dropna()
        if not deltas.empty:
            median_delta = deltas.median()
            if pd.notna(median_delta):
                hours = median_delta.total_seconds() / 3600.0
                if hours <= 24:
                    return "hourly" if hours < 24 else "daily"
                if hours <= 168:
                    return "weekly"

    return "daily"


def resolve_minimum_segment_points(cadence: str | None = None, series: pd.Series | None = None) -> int:
    """Resolve the minimum number of observations required for a stable final analysis segment."""
    if cadence is None and series is not None:
        cadence = infer_cadence_from_series(series)

    key = str(cadence or "daily").lower()
    if key.startswith("hour"):
        return DEFAULT_MIN_SEGMENT_POINTS["hourly"]
    if key.startswith("week"):
        return DEFAULT_MIN_SEGMENT_POINTS["weekly"]
    if key.startswith("day"):
        return DEFAULT_MIN_SEGMENT_POINTS["daily"]
    return DEFAULT_MIN_SEGMENT_POINTS["daily"]


def select_pelt_model(signal: Sequence[float] | np.ndarray, component_type: str = "trend") -> str:
    """Route PELT to the safer linear model or the more flexible RBF kernel.

    The rules follow the product requirement:
    - always prefer linear for trend signals
    - force linear for very long inputs to avoid quadratic slowdowns
    - use RBF only when seasonal data shows heavy-tail or bimodal behavior
    """
    arr = np.asarray(signal, dtype=float).ravel()
    if arr.size == 0:
        raise ValueError("Signal must contain at least one value.")

    if arr.size > 35000:
        return "l2"

    component = str(component_type).lower()
    if component in {"trend", "trend_component", "trend-signal"}:
        return "l2"

    if component in {"seasonality", "seasonal", "amplitude", "seasonal_amplitude"}:
        if arr.size >= 4:
            kurt = float(abs(kurtosis(arr, fisher=True, bias=False)))
            if np.isfinite(kurt) and kurt > 1.5:
                return "rbf"
        return "l2"

    return "l2"


def get_short_segment_confirmation_message(cadence: str = "weekly", required_points: int = 12, final_len: int = 0) -> str:
    """Return the user-facing explanation for a short final segment fallback."""
    cadence_label = str(cadence or "weekly").lower()
    return (
        f"The final segment is shorter than the minimum analysis window for {cadence_label} data "
        f"({required_points} points; current length: {final_len}). To keep the analysis statistically stable, "
        "tseda will blend in a half-life-weighted look-back from the preceding segment. "
        "Please acknowledge this adjustment to continue with the adjusted segment for analysis."
    )


def _coerce_segments(segments: Sequence[tuple[int, int]] | Sequence[list[int]]) -> list[tuple[int, int]]:
    """Normalize segment tuples into a list of start/end pairs."""
    parsed: list[tuple[int, int]] = []
    for segment in segments:
        if isinstance(segment, dict):
            start = int(segment.get("start", segment.get("start_idx", 0)))
            end = int(segment.get("end", segment.get("end_idx", start)))
        else:
            start, end = tuple(segment)
        if end <= start:
            continue
        parsed.append((int(start), int(end)))
    return parsed


def build_adjusted_analysis_segment(
    series: Sequence[float] | np.ndarray | pd.Series,
    segments: Sequence[tuple[int, int]] | Sequence[list[int]] | None = None,
    min_points: int | None = None,
    half_life: float = 30.0,
    threshold: float = 0.95,
    cadence: str | None = None,
) -> dict[str, object]:
    """Adjust a short final segment using a half-life look-back from the preceding segment.

    The method keeps the current regime but expands the selection backward until the
    cumulative half-life weight in the prior segment reaches the configured threshold.
    """
    values = np.asarray(series, dtype=float).ravel()
    if values.size == 0:
        raise ValueError("Series must contain at least one observation.")

    if segments is None:
        segments = [(0, int(values.size))]

    normalized = _coerce_segments(segments)
    if not normalized:
        raise ValueError("At least one valid segment boundary must be supplied.")

    last_start, last_end = normalized[-1]
    last_length = max(0, last_end - last_start)

    required = int(min_points) if min_points is not None else resolve_minimum_segment_points(cadence=cadence, series=pd.Series(values))
    required = max(1, required)

    if last_length >= required:
        return {
            "selected_segment": (int(last_start), int(last_end)),
            "segment_length": last_length,
            "required_points": required,
            "is_adjusted": False,
            "reason": "Final segment already meets the minimum analysis length.",
            "cadence": cadence or infer_cadence_from_series(pd.Series(values)),
        }

    if len(normalized) < 2:
        return {
            "selected_segment": (int(last_start), int(last_end)),
            "segment_length": last_length,
            "required_points": required,
            "is_adjusted": False,
            "reason": "Only one segment is available; no preceding regime exists for fallback.",
            "cadence": cadence or infer_cadence_from_series(pd.Series(values)),
        }

    prev_start, prev_end = normalized[-2]
    prev_length = max(0, prev_end - prev_start)
    if prev_length <= 0:
        return {
            "selected_segment": (int(last_start), int(last_end)),
            "segment_length": last_length,
            "required_points": required,
            "is_adjusted": False,
            "reason": "Previous segment is empty; no short-tail adjustment is possible.",
            "cadence": cadence or infer_cadence_from_series(pd.Series(values)),
        }

    half_life_value = max(float(half_life), 1.0)
    alpha = 1.0 - math.exp(-math.log(2.0) / half_life_value)
    weights = np.array(
        [alpha * (1.0 - alpha) ** idx for idx in range(prev_length)],
        dtype=float,
    )
    total_weight = float(weights.sum())
    if total_weight <= 0.0:
        total_weight = 1.0
    cumulative = np.cumsum(weights) / total_weight
    lookback = int(np.searchsorted(cumulative, float(threshold), side="left") + 1)
    lookback = max(required, min(prev_length, lookback))

    adjusted_start = max(prev_start, prev_end - lookback)
    selected_end = last_end
    selected_start = int(adjusted_start)

    adjusted_segment = (selected_start, int(selected_end))
    adjusted_length = max(0, selected_end - selected_start)

    return {
        "selected_segment": adjusted_segment,
        "segment_length": adjusted_length,
        "required_points": required,
        "is_adjusted": True,
        "reason": "Short final segment was expanded using a half-life-weighted look-back from the previous regime.",
        "preceding_segment": (int(prev_start), int(prev_end)),
        "final_segment": (int(last_start), int(last_end)),
        "cadence": cadence or infer_cadence_from_series(pd.Series(values)),
        "half_life": half_life_value,
        "threshold": float(threshold),
        "lookback_points": lookback,
    }
