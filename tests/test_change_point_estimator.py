import pytest
import pandas as pd
import numpy as np
from change_point.change_point_estimator import ChangePointEstimator

class TestChangePointEstimator:
    
    @pytest.fixture
    def sample_series(self):
        """Create a sample time series with clear change points."""
        dates = pd.date_range('2023-01-01', periods=100)
        values = np.concatenate([
            np.random.normal(5, 1, 30),
            np.random.normal(15, 1, 35),
            np.random.normal(8, 1, 35)
        ])
        return pd.Series(values, index=dates)
    
    def test_init(self, sample_series):
        """Test ChangePointEstimator initialization."""
        estimator = ChangePointEstimator(sample_series)
        assert estimator._df.shape[0] == 100
        assert list(estimator._df.columns) == ["date", "signal"]
        assert estimator._change_pts is None
    
    def test_estimate_change_points(self, sample_series):
        """Test change point estimation."""
        estimator = ChangePointEstimator(sample_series)
        estimator.estimate_change_points()
        assert estimator._change_pts is not None
        assert len(estimator._change_pts) > 0
        assert "segment" in estimator._df.columns
    
    def test_label_segment(self, sample_series):
        """Test segment labeling."""
        estimator = ChangePointEstimator(sample_series)
        estimator.estimate_change_points()
        
        segments = estimator._df["segment"].dropna()
        assert len(segments) > 0
        assert all(seg.startswith("segment-") for seg in segments)
    
    def test_penalty_coefficient(self, sample_series):
        """Test with custom penalty coefficient."""
        estimator = ChangePointEstimator(sample_series)
        estimator.estimate_change_points(penalty_coeff=3.0)
        assert estimator._change_pts is not None