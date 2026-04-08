from __future__ import annotations

import numpy as np
import pandas as pd
import ruptures as rpt


class PELT_ChangePointEstimator:
	"""Estimate change points with the PELT algorithm and return a predicted segment series."""

	def __init__(self, series: pd.Series, model: str = "rbf") -> None:
		if series is None or len(series) == 0:
			raise ValueError("Input series must be a non-empty pandas Series.")

		self._series = series
		self._model = model
		self._n = len(series)
		self._penalty = float(2 * np.log(self._n))

		values = series.to_numpy().reshape(-1, 1)
		self._algo = rpt.Pelt(model=model).fit(values)
		self._change_pts = self._algo.predict(pen=self._penalty)
		self._predicted_series = self._build_predicted_series(self._change_pts)

	def _build_predicted_series(self, change_points: list[int]) -> pd.Series:
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
		"""Return the predicted segment label series."""
		return self._predicted_series.copy()


class ChangePointEstimator:
	"""Compatibility wrapper used by existing tests and call sites."""

	def __init__(self, series: pd.Series) -> None:
		if series is None or len(series) == 0:
			raise ValueError("Input series must be a non-empty pandas Series.")

		self._series = series
		self._df = pd.DataFrame({"date": series.index, "signal": series.values})
		self._change_pts: list[int] | None = None

	def estimate_change_points(self, penalty_coeff: float = 2.0) -> pd.Series:
		"""Run PELT and assign segment labels for each observation."""
		n = len(self._series)
		penalty = float(penalty_coeff * np.log(n))
		values = self._series.to_numpy().reshape(-1, 1)

		algo = rpt.Pelt(model="rbf").fit(values)
		self._change_pts = algo.predict(pen=penalty)

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

        