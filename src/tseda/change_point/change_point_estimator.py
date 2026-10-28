"""Change-point detection utilities based on the PELT algorithm."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import ruptures as rpt


def _resolve_minimum_segment_points(series: pd.Series) -> int:
	"""Return the minimum admissible segment length for the series cadence."""
	if hasattr(series, "index") and hasattr(series.index, "inferred_freq"):
		freq = str(series.index.inferred_freq or "").lower()
		if "min" in freq or freq in {"s", "sec", "second", "seconds"} or ("t" in freq and "min" not in freq):
			deltas = pd.Series(series.index).diff().dropna()
			if not deltas.empty:
				median_delta = deltas.median()
				if pd.notna(median_delta):
					delta_minutes = float(median_delta.total_seconds() / 60.0)
					if delta_minutes > 0:
						points_per_day = max(1, int(round(24 * 60 / delta_minutes)))
						return max(24, points_per_day)
			return 24
		if "h" in freq:
			return 24 * 7 * 3
		if "w" in freq:
			return 12
		if "m" in freq:
			return 12
		if "d" in freq or "b" in freq:
			return 90
	return 90


def _adjust_change_points_for_min_segment_length(change_points: list[int], n: int, min_points: int) -> list[int]:
	"""Collapse a trivial final change point into the previous regime when it is too short.

	This mirrors the exponential half-life enforcement used elsewhere in tseda: if the
	last regime is shorter than the minimum admissible window, move the final break
	backward using a half-life-weighted look-back from the preceding segment.
	"""
	if n <= 0:
		return []
	if not change_points:
		return []

	final_break = int(change_points[-1])
	final_segment_length = max(0, n - final_break)
	if final_segment_length >= min_points:
		return list(change_points)

	if len(change_points) == 1:
		return []

	prev_start = int(change_points[-2])
	prev_end = int(change_points[-1])
	prev_length = max(0, prev_end - prev_start)
	if prev_length <= min_points:
		return list(change_points[:-1])

	half_life = max(float(min_points), 30.0)
	alpha = 1.0 - math.exp(-math.log(2.0) / half_life)
	weights = np.array(
		[alpha * (1.0 - alpha) ** idx for idx in range(prev_length)],
		dtype=float,
	)
	if weights.size == 0:
		return list(change_points[:-1])

	total_weight = float(weights.sum())
	if total_weight <= 0.0:
		total_weight = 1.0
	cumulative = np.cumsum(weights) / total_weight
	lookback = int(np.searchsorted(cumulative, 0.95, side="left") + 1)
	lookback = max(min_points, min(prev_length, lookback))
	adjusted_break = max(prev_start, prev_end - lookback)
	adjusted = [int(point) for point in change_points[:-1]]
	adjusted.append(int(adjusted_break))
	adjusted = sorted(set(adjusted))
	return adjusted


class PELT_ChangePointEstimator:
	"""Estimate change points with the PELT algorithm and return a predicted segment series."""

	def __init__(self, series: pd.Series, model: str = "rbf") -> None:
		"""Initialize PELT estimator and fit the algorithm on the input series.

		Args:
			series: Non-empty numeric series indexed by datetimes.
			model: Cost model used by PELT (default ``"rbf"``).
		"""
		if series is None or len(series) == 0:
			raise ValueError("Input series must be a non-empty pandas Series.")

		self._series = series
		self._model = model
		self._n = len(series)
		self._penalty = float(2 * np.log(self._n))
		self._min_segment_points = _resolve_minimum_segment_points(series)

		values = series.to_numpy().reshape(-1, 1)
		self._algo = rpt.Pelt(model=model).fit(values)
		self._change_pts = self._apply_minimum_segment_rule(self._algo.predict(pen=self._penalty))
		self._predicted_series = self._build_predicted_series(self._change_pts)

	def _apply_minimum_segment_rule(self, change_points: list[int]) -> list[int]:
		"""Trim a trivial tail break so the final regime is not artificially short."""
		return _adjust_change_points_for_min_segment_length(change_points, self._n, self._min_segment_points)

	def _build_predicted_series(self, change_points: list[int]) -> pd.Series:
		"""Build a segment-label series aligned to the input index.

		Args:
			change_points: Predicted break-point indices returned by PELT.

		Returns:
			Series of segment labels (e.g. ``"segment-1"``) with the same index as the input.
		"""
		segment_labels: list[str] = []
		start_idx = 0

		for segment_no, end_idx in enumerate(change_points, start=1):
			segment_length = max(0, end_idx - start_idx)
			segment_labels.extend([f"segment-{segment_no}"] * segment_length)
			start_idx = end_idx

		if len(segment_labels) < self._n:
			segment_labels.extend([f"segment-{len(change_points) + 1}"] * (self._n - len(segment_labels)))

		return pd.Series(segment_labels[: self._n], index=self._series.index, name="segment")

	def predict_series(self) -> pd.Series:
		"""Return the predicted segment label series.

		Returns:
			Series with the same index as the input series and values such as
			``"segment-1"``, ``"segment-2"``, etc.
		"""
		return self._predicted_series.copy()


class ChangePointEstimator:
	"""Compatibility wrapper used by existing tests and call sites."""

	def __init__(self, series: pd.Series) -> None:
		"""Initialize the estimator with the input series.

		Args:
			series: Non-empty numeric series indexed by datetimes.
		"""
		if series is None or len(series) == 0:
			raise ValueError("Input series must be a non-empty pandas Series.")

		self._series = series
		self._df = pd.DataFrame({"date": series.index, "signal": series.values})
		self._change_pts: list[int] | None = None
		self._min_segment_points = _resolve_minimum_segment_points(series)

	def estimate_change_points(self, penalty_coeff: float = 2.0) -> pd.Series:
		"""Run PELT and assign segment labels for each observation.

		Args:
			penalty_coeff: Multiplier applied to ``log(n)`` when building the PELT
				penalty term.

		Returns:
			Series of segment labels aligned to the original input index.
		"""
		n = len(self._series)
		penalty = float(penalty_coeff * np.log(n))
		values = self._series.to_numpy().reshape(-1, 1)

		algo = rpt.Pelt(model="rbf").fit(values)
		self._change_pts = _adjust_change_points_for_min_segment_length(
			algo.predict(pen=penalty),
			n,
			self._min_segment_points,
		)

		segment_labels: list[str] = []
		start_idx = 0
		for segment_no, end_idx in enumerate(self._change_pts, start=1):
			segment_length = max(0, end_idx - start_idx)
			segment_labels.extend([f"segment-{segment_no}"] * segment_length)
			start_idx = end_idx

		if len(segment_labels) < n:
			segment_labels.extend([f"segment-{len(self._change_pts) + 1}"] * (n - len(segment_labels)))

		self._df["segment"] = segment_labels[:n]
		return self._df["segment"]

        