import numpy as np

from tseda.segmentation.pelt_segmentation import (
    build_adjusted_analysis_segment,
    get_short_segment_confirmation_message,
    select_pelt_model,
)


def test_select_pelt_model_defaults_linear_for_trend_component():
    signal = np.linspace(0.0, 10.0, 200)
    assert select_pelt_model(signal, component_type="trend") == "l2"


def test_select_pelt_model_routes_rbf_for_high_kurtosis_seasonality():
    signal = np.concatenate([
        np.full(120, 0.0),
        np.full(120, 10.0),
        np.full(120, -10.0),
    ])
    assert select_pelt_model(signal, component_type="seasonality") == "rbf"


def test_select_pelt_model_falls_back_to_linear_for_long_series():
    signal = np.random.default_rng(0).normal(0.0, 1.0, 40000)
    assert select_pelt_model(signal, component_type="seasonality") == "l2"


def test_build_adjusted_analysis_segment_uses_short_final_segment_fallback():
    series = np.arange(80, dtype=float)
    segments = [
        (0, 60),
        (60, 70),
    ]
    adjusted = build_adjusted_analysis_segment(
        series,
        segments=segments,
        min_points=12,
        half_life=10,
        threshold=0.95,
    )
    assert adjusted["selected_segment"][1] == 70
    assert adjusted["selected_segment"][0] < 60
    assert adjusted["is_adjusted"] is True
    assert adjusted["segment_length"] >= 12


def test_short_segment_message_mentions_user_confirmation():
    message = get_short_segment_confirmation_message(
        cadence="weekly",
        required_points=12,
        final_len=5,
    )
    assert "weekly" in message.lower()
    assert "acknowledge" in message.lower() or "continue" in message.lower()
