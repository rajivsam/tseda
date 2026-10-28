import pandas as pd
import numpy as np
import pytest

from tseda.change_point.change_point_estimator import PELT_ChangePointEstimator, ChangePointEstimator


def test_pelt_estimator_rejects_empty_series():
    with pytest.raises(ValueError, match="non-empty pandas Series"):
        PELT_ChangePointEstimator(pd.Series(dtype=float))


def test_pelt_predict_series_has_expected_labels():
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    values = np.concatenate([np.ones(5) * 1.0, np.ones(5) * 4.0])
    series = pd.Series(values, index=dates)

    estimator = PELT_ChangePointEstimator(series)
    predicted = estimator.predict_series()

    assert list(predicted.index) == list(series.index)
    assert all(label.startswith("segment-") for label in predicted)
    assert len(predicted.unique()) == 1


def test_pelt_tail_breaks_are_merged_when_final_segment_is_too_short():
    estimator = PELT_ChangePointEstimator.__new__(PELT_ChangePointEstimator)
    estimator._n = 100
    estimator._min_segment_points = 12
    adjusted = estimator._apply_minimum_segment_rule([20, 50, 92])

    assert adjusted[-1] < 92
    assert 100 - adjusted[-1] >= 12
    assert all(a < b for a, b in zip(adjusted, adjusted[1:]))


def test_legacy_change_point_estimator_rejects_invalid_series():
    with pytest.raises(ValueError, match="non-empty pandas Series"):
        ChangePointEstimator(pd.Series(dtype=float)).estimate_change_points()


def test_change_point_estimator_segment_labels_are_consistent():
    dates = pd.date_range("2024-01-01", periods=8, freq="D")
    values = [1.0, 1.0, 10.0, 10.0, 1.0, 1.0, 10.0, 10.0]
    series = pd.Series(values, index=dates)

    estimator = ChangePointEstimator(series)
    labels = estimator.estimate_change_points(penalty_coeff=2.0)

    assert list(labels.index) == list(range(len(series)))
    assert all(lbl.startswith("segment-") for lbl in labels)
    assert len(labels.unique()) == 1
