import numpy as np
import pytest

from tseda.decomposition.automatic_grouping_heuristic import AutomaticGroupingHeuristic


def test_automatic_grouping_heuristic_validates_input_dimensions():
    with pytest.raises(ValueError, match="one-dimensional array"):
        AutomaticGroupingHeuristic(eigenvalues=np.array([[1.0, 2.0]]))


def test_automatic_grouping_heuristic_rejects_negative_eigenvalues():
    with pytest.raises(ValueError, match="non-negative"):
        AutomaticGroupingHeuristic(eigenvalues=np.array([1.0, -2.0, 3.0]))


def test_automatic_grouping_heuristic_rejects_invalid_component_bounds():
    with pytest.raises(ValueError, match="min_signal_components must be >= 1"):
        AutomaticGroupingHeuristic(eigenvalues=np.array([1.0, 2.0]), min_signal_components=0)

    with pytest.raises(ValueError, match="min_noise_components must be >= 0"):
        AutomaticGroupingHeuristic(eigenvalues=np.array([1.0, 2.0]), min_noise_components=-1)


def test_has_seasonal_pair_false_when_no_adjacent_pair():
    heuristic = AutomaticGroupingHeuristic(
        eigenvalues=np.array([5.0, 4.0, 2.0, 1.0]),
        pair_similarity_tolerance=0.01,
    )
    assert heuristic.has_seasonal_pair() is False


def test_has_seasonal_pair_true_with_adjacent_near_equal_values():
    heuristic = AutomaticGroupingHeuristic(
        eigenvalues=np.array([5.0, 4.95, 1.0, 0.5]),
        pair_similarity_tolerance=0.02,
    )
    assert heuristic.has_seasonal_pair() is True


def test_eligible_component_indices_respects_min_and_max_bounds():
    heuristic = AutomaticGroupingHeuristic(
        eigenvalues=np.array([10.0, 1.0, 0.5]),
        min_signal_components=2,
        min_noise_components=1,
        pool_selection_method="variance_threshold",
        variance_threshold=0.9,
    )
    assert heuristic.eligible_component_indices() == [0, 1]


def test_suggest_reconstruction_handles_single_component_signal_pool():
    heuristic = AutomaticGroupingHeuristic(
        eigenvalues=np.array([10.0, 2.0, 1.0]),
        pool_selection_method="variance_threshold",
        variance_threshold=0.5,
    )
    result = heuristic.suggest_reconstruction()
    assert result["Trend"] == [0]
    assert result["Seasonality"] == []
    assert result["Noise"] == [1, 2]


def test_suggest_next_expansion_consumes_next_noise_component():
    heuristic = AutomaticGroupingHeuristic(
        eigenvalues=np.array([10.0, 7.0, 5.0, 1.0]),
        pair_similarity_tolerance=0.1,
    )
    current = {"Trend": [0], "Seasonality": [], "Noise": [1, 2, 3]}
    expanded, did_expand = heuristic.suggest_next_expansion(current)

    assert did_expand is True
    assert expanded["Trend"] == [0, 1]
    assert 1 not in expanded["Noise"]
