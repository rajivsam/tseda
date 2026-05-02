"""Automatic SSA component grouping heuristics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class AutomaticGroupingHeuristic:
    """Suggest SSA grouping labels from the eigenvalue spectrum.

    Components explaining at least ``variance_threshold`` of total variance are
    classified as either trend or seasonality. Near-equal adjacent pairs are
    treated as seasonal pairs; the remaining eligible components are treated as
    trend. All other components fall into noise.
    """

    eigenvalues: np.ndarray
    variance_threshold: float = 0.10
    pair_similarity_tolerance: float = 0.05

    def __post_init__(self) -> None:
        values = np.asarray(self.eigenvalues, dtype=float)
        if values.ndim != 1:
            raise ValueError("eigenvalues must be a one-dimensional array.")
        if np.any(values < 0):
            raise ValueError("eigenvalues must be non-negative.")

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

    def eligible_component_indices(self) -> list[int]:
        """Return component indices meeting the minimum explained-variance threshold."""
        ratios = self.explained_variance_ratios
        return [index for index, ratio in enumerate(ratios) if float(ratio) >= self.variance_threshold]

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