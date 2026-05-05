"""Automatic SSA component grouping heuristics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class AutomaticGroupingHeuristic:
    """Suggest SSA grouping labels from the eigenvalue spectrum.

    The initial trend/seasonality candidate pool is selected from the leading
    eigenvalues up to a detected noise floor (kneedle-style elbow on the
    normalized log-spectrum). Near-equal adjacent pairs are treated as seasonal
    pairs; the remaining eligible components are treated as trend. All other
    components fall into noise.
    """

    eigenvalues: np.ndarray
    pool_selection_method: str = "kneedle"
    variance_threshold: float = 0.10
    pair_similarity_tolerance: float = 0.05
    kneedle_min_distance: float = 0.03
    min_signal_components: int = 1
    min_noise_components: int = 2

    def __post_init__(self) -> None:
        values = np.asarray(self.eigenvalues, dtype=float)
        if values.ndim != 1:
            raise ValueError("eigenvalues must be a one-dimensional array.")
        if np.any(values < 0):
            raise ValueError("eigenvalues must be non-negative.")
        if self.min_signal_components < 1:
            raise ValueError("min_signal_components must be >= 1.")
        if self.min_noise_components < 0:
            raise ValueError("min_noise_components must be >= 0.")

        self.eigenvalues = values

    @property
    def explained_variance_ratios(self) -> np.ndarray:
        """Return per-component explained variance ratios."""
        total_variance = float(np.sum(self.eigenvalues))
        if total_variance <= 0:
            return np.zeros_like(self.eigenvalues, dtype=float)
        return self.eigenvalues / total_variance

    def is_near_equal_pair(self, left_index: int, right_index: int) -> bool:
        """Return True when two eigenvalues differ by at most the configured tolerance."""
        left_value = float(self.eigenvalues[left_index])
        right_value = float(self.eigenvalues[right_index])
        larger = max(left_value, right_value)
        smaller = min(left_value, right_value)
        if larger <= 0:
            return False
        return ((larger - smaller) / larger) <= self.pair_similarity_tolerance

    def has_seasonal_pair(self, max_components: int | None = None) -> bool:
        """Return True when any adjacent eligible pair satisfies the similarity rule."""
        eligible = self.eligible_component_indices()
        if max_components is not None:
            eligible = [index for index in eligible if index < max_components]

        for offset in range(len(eligible) - 1):
            left_index = eligible[offset]
            right_index = eligible[offset + 1]
            if right_index == left_index + 1 and self.is_near_equal_pair(left_index, right_index):
                return True
        return False

    def _resolve_signal_count_bounds(self) -> tuple[int, int]:
        """Return min/max bounds for the initial eligible signal pool size."""
        n = int(len(self.eigenvalues))
        min_signal = min(max(int(self.min_signal_components), 1), n)
        max_signal = n - max(int(self.min_noise_components), 0)
        if max_signal < 1:
            max_signal = 1
        max_signal = min(max_signal, n)
        if min_signal > max_signal:
            min_signal = max_signal
        return min_signal, max_signal

    def _kneedle_noise_floor_index(self) -> int | None:
        """Return the last structural component index from a kneedle-style elbow.

        The spectrum is converted to log scale to stabilize dynamic range,
        normalized to [0, 1], and compared against the straight line between
        endpoints. The elbow is the point of maximum positive distance.
        """
        n = int(len(self.eigenvalues))
        if n < 3:
            return None

        values = np.log1p(np.asarray(self.eigenvalues, dtype=float))
        first = float(values[0])
        last = float(values[-1])
        denom = first - last
        if denom <= 0.0:
            return None

        x = np.linspace(0.0, 1.0, n)
        y = (values - last) / denom
        line = 1.0 - x
        distance = y - line

        knee_index = int(np.argmax(distance))
        if float(distance[knee_index]) < float(self.kneedle_min_distance):
            return None
        return knee_index

    def eligible_component_indices(self) -> list[int]:
        """Return initial signal-pool component indices for grouping.

        Default strategy uses a kneedle-style elbow to estimate the noise floor.
        Legacy ``variance_threshold`` mode is retained as a configurable fallback.
        """
        min_signal, max_signal = self._resolve_signal_count_bounds()
        n = int(len(self.eigenvalues))

        method = str(self.pool_selection_method).strip().lower()
        if method == "variance_threshold":
            ratios = self.explained_variance_ratios
            threshold_indices = [
                index for index, ratio in enumerate(ratios)
                if float(ratio) >= float(self.variance_threshold)
            ]
            if threshold_indices:
                count = len(threshold_indices)
            else:
                count = min_signal
        else:
            knee_index = self._kneedle_noise_floor_index()
            if knee_index is None:
                count = min_signal
            else:
                count = knee_index + 1

        count = max(min_signal, min(count, max_signal))
        return list(range(min(count, n)))

    def suggest_reconstruction(self) -> dict[str, list[int]]:
        """Return a trend/seasonality/noise grouping suggestion."""
        eligible = self.eligible_component_indices()
        trend_indices: list[int] = []
        seasonality_indices: list[int] = []

        cursor = 0
        while cursor < len(eligible):
            left_index = eligible[cursor]
            right_index = eligible[cursor + 1] if cursor + 1 < len(eligible) else None

            if (
                right_index is not None
                and right_index == left_index + 1
                and self.is_near_equal_pair(left_index, right_index)
            ):
                seasonality_indices.extend([left_index, right_index])
                cursor += 2
                continue

            trend_indices.append(left_index)
            cursor += 1

        assigned = set(trend_indices) | set(seasonality_indices)
        noise_indices = [index for index in range(len(self.eigenvalues)) if index not in assigned]

        return {
            "Trend": trend_indices,
            "Seasonality": seasonality_indices,
            "Noise": noise_indices,
        }

    def suggest_next_expansion(
        self, current: dict[str, list[int]]
    ) -> tuple[dict[str, list[int]], bool]:
        """Expand the current assignment by one step from the noise pool.

        Takes the lowest-index (highest-eigenvalue) component in the noise pool.
        If it and its immediate successor form a near-equal adjacent pair, both are
        added to seasonality; otherwise the single component is added to trend.

        Returns:
            A tuple of the updated assignment dict and True when an expansion was
            made, or (current, False) when the noise pool is exhausted.
        """
        noise_pool = sorted(current.get("Noise", []))
        if not noise_pool:
            return current, False

        new_assignment = {k: list(v) for k, v in current.items()}
        candidate = noise_pool[0]
        next_candidate = noise_pool[1] if len(noise_pool) > 1 else None

        if (
            next_candidate is not None
            and next_candidate == candidate + 1
            and self.is_near_equal_pair(candidate, next_candidate)
        ):
            new_assignment["Seasonality"] = sorted(
                new_assignment.get("Seasonality", []) + [candidate, next_candidate]
            )
            new_assignment["Noise"] = [
                i for i in noise_pool if i not in {candidate, next_candidate}
            ]
        else:
            new_assignment["Trend"] = sorted(
                new_assignment.get("Trend", []) + [candidate]
            )
            new_assignment["Noise"] = [i for i in noise_pool if i != candidate]

        return new_assignment, True