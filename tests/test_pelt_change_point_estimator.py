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
