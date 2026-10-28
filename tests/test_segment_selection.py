import numpy as np
import pandas as pd

import tseda.user_interface.ts_analyze_ui as ui
from tseda.segmentation.pelt_segmentation import (
    build_adjusted_analysis_segment,
    get_short_segment_confirmation_message,
    resolve_minimum_segment_points,
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


def test_monthly_and_subhourly_defaults_are_reasonable():
    monthly = pd.date_range("2024-01-01", periods=24, freq="MS")
    monthly_series = pd.Series(np.arange(len(monthly)), index=monthly)
    assert resolve_minimum_segment_points(series=monthly_series) == 12

    subhourly_index = pd.date_range("2024-01-01", periods=200, freq="15min")
    subhourly_series = pd.Series(np.arange(len(subhourly_index)), index=subhourly_index)
    minimum = resolve_minimum_segment_points(series=subhourly_series)
    assert minimum == 96

    five_minute_index = pd.date_range("2024-01-01", periods=200, freq="5min")
    five_minute_series = pd.Series(np.arange(len(five_minute_index)), index=five_minute_index)
    assert resolve_minimum_segment_points(series=five_minute_series) == 288


def test_ui_describes_final_segment_adjustment_in_warning_text():
    series = pd.Series(np.arange(100, dtype=float), index=pd.date_range("2024-01-01", periods=100, freq="D"))
    ui.series = series
    boundaries = [(0, 70), (70, 92), (92, 100)]
    message, adjusted_segment, _ = ui.describe_segment_adjustment(series, boundaries, 2)

    assert "minimum stable window" in message.lower()
    assert "half-life" in message.lower()
    assert adjusted_segment[1] > 92
    assert adjusted_segment[0] < 92
