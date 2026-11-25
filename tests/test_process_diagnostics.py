import numpy as np
import pandas as pd
import pytest

from tseda.decomposition.process_diagnostics import (
    analyze_process,
    monte_carlo_persistence_percentile,
)
from tseda.decomposition.process_guidance import (
    STOCHASTIC_PERSISTENCE_WARNING,
    stochastic_persistence_stop_message,
)
from tseda.notebook_api import NotebookThreeStepAPI, load_series_from_csv


def test_white_noise_is_classified_as_diffuse_noise():
    rng = np.random.default_rng(42)
    series = pd.Series(
        rng.standard_normal(240),
        index=pd.date_range("2024-01-01", periods=240, freq="h"),
    )

    result = analyze_process(series, window=24, scope="full_series")

    assert result.process_classification.label == "diffuse_noise"
    assert result.decomposition_suitability.status == "unsuitable"
    assert result.periodic_components == []


def test_random_walk_is_persistent_and_never_seasonal():
    rng = np.random.default_rng(7)
    series = pd.Series(
        np.cumsum(rng.standard_normal(240)),
        index=pd.date_range("2024-01-01", periods=240, freq="h"),
    )
    api = NotebookThreeStepAPI(series, window=24, apply_window_refinement=False)

    result = api._ensure_ssa().get_process_analysis()

    assert result.process_classification.label == "stochastic_persistence"
    assert result.persistent_components
    assert result.periodic_components == []
    with pytest.raises(ValueError, match="pareidolia"):
        api.suggest_grouping()


def test_trend_and_periodic_series_has_verified_pair():
    t = np.arange(240)
    series = pd.Series(
        0.05 * t + 3.0 * np.sin(2 * np.pi * t / 12),
        index=pd.date_range("2024-01-01", periods=240, freq="D"),
    )

    result = analyze_process(series, window=12, scope="full_series")

    assert result.process_classification.label == "mixed"
    assert len(result.periodic_components) == 1
    component = result.periodic_components[0]
    assert abs(component.period - 12.0) <= 1.5
    assert component.eigenvalue_pair[1] == component.eigenvalue_pair[0] + 1
    assert component.cycle_count == 20.0


def test_goog_benchmark_is_not_classified_as_deterministic_seasonality():
    series = load_series_from_csv("data/hyndman_goog_daily_close.csv")
    api = NotebookThreeStepAPI(series, window=5, apply_window_refinement=False)

    result = api._ensure_ssa().get_process_analysis(scope="full_series")

    assert result.process_classification.label == "stochastic_persistence"
    assert result.periodic_components == []
    assert api._ensure_ssa().seasonality_check_heuristic() is False
    suitability = api.get_suitability_result()
    assert suitability.is_suitable is False
    assert suitability.status == "unsuitable"
    assert suitability.process_class == "stochastic_persistence"
    with pytest.raises(ValueError, match="pareidolia"):
        api.suggest_grouping()
    with pytest.raises(ValueError, match="pareidolia"):
        api.set_grouping(grouping={"Persistence": [0], "Noise": [1, 2, 3, 4]})

    observation = api.generate_observation_text()
    assert "pareidolia" in observation
    assert STOCHASTIC_PERSISTENCE_WARNING in observation


def test_biomass_trend_override_has_no_persistence_group():
    series = load_series_from_csv(
        "data/trimmed_biomass - generated_biomass_MW_series.csv"
    )
    result = analyze_process(series, window=24, scope="full_series")

    assert result.process_classification.label == "deterministic_trend"
    assert result.persistent_components == []


def test_monte_carlo_null_reports_random_walk_compatibility():
    rng = np.random.default_rng(9)
    values = np.cumsum(rng.standard_normal(120))

    percentile, status = monte_carlo_persistence_percentile(
        values,
        window=24,
        replicates=9,
        seed=11,
    )

    assert status == "completed"
    assert 0.0 <= percentile <= 1.0
    assert "pareidolia" in stochastic_persistence_stop_message()


def test_hyndsight_finds_seven_day_period():
    series = load_series_from_csv("data/hyndman_hyndsight_daily_pageviews.csv")
    api = NotebookThreeStepAPI(series, window=5, apply_window_refinement=False)

    result = analyze_process(series, window=5, scope="full_series")
    grouping_result = api.suggest_grouping_with_window_autotune()

    assert result.process_classification.label == "periodic"
    assert any(abs(component.period - 7.0) <= 0.5 for component in result.periodic_components)
    assert any(component.window >= 7 for component in result.periodic_components)
    assert grouping_result.final_window == 7
    assert grouping_result.grouping["Seasonality"] == [0, 1]
    assert grouping_result.reason == "period_verified_dw_outside_target"


def test_variance_attribution_exposes_all_scales_and_warns_about_separation():
    series = load_series_from_csv("data/monthly-car-sales.csv")
    api = NotebookThreeStepAPI(series, window=12, apply_window_refinement=False)
    grouping, _ = api.suggest_grouping()
    api.set_grouping(grouping)

    attribution = api.get_reconstruction_metadata()["variance_attribution"]

    assert attribution["scale"] == "ssa_preprocessed"
    assert set(attribution["spectral_share"]) == set(grouping)
    assert "Trend" in attribution["reconstruction_variance"]
    assert "Seasonality" in attribution["reconstruction_variance"]
    assert "Noise" in attribution["reconstruction_variance"]
    assert abs(sum(attribution["covariance_adjusted_share"].values()) - 1.0) < 1e-8
    assert isinstance(attribution["separation_warnings"], list)


def test_process_result_is_json_compatible():
    series = load_series_from_csv("data/hyndman_sunspot_monthly_area.csv")

    result = analyze_process(series, window=12, scope="full_series").to_dict()

    assert result["schema_version"] == "1.0"
    assert result["scope"] == "full_series"
    assert isinstance(result["process_classification"]["evidence"]["sample_count"], int)
    assert any(abs(item["period"] - 132.0) <= 4.0 for item in result["periodic_components"])
