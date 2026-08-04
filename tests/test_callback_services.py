import base64
import io

import pandas as pd
import pytest
from dash import html

from tseda.user_interface import callback_services


def _csv_payload(csv_text: str) -> str:
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("utf-8")
    return f"data:text/csv;base64,{encoded}"


class DummySSA:
    def __init__(self, variation_map, dw_value=None):
        self._variation_by_group = variation_map
        self._durbin_watson = dw_value


def test_compute_window_slider_config_invalid_inputs():
    assert callback_services.compute_window_slider_config(1, 0, 10) == ({}, 0, 0, 0, None)
    assert callback_services.compute_window_slider_config(2, 10, 0) == ({}, 0, 0, 0, None)
    assert callback_services.compute_window_slider_config(1, -1, 5) == ({}, 0, 0, 0, None)


def test_compute_window_slider_config_valid():
    marks, value, min_value, max_value, step = callback_services.compute_window_slider_config(
        current_step=2, series_length=100, default_window_size=24
    )

    assert isinstance(marks, dict)
    assert value == 24
    assert min_value == 24
    assert max_value == 48
    assert step is None
    assert marks[24] == "24"


def test_parse_reconstruction_groups_parse_noise_wildcard_and_overlap():
    result = callback_services.parse_reconstruction_groups(
        rows=[("Trend", "0,1"), ("Noise", "*"), ("Seasonality", "2")],
        window_size=5,
    )
    assert result["Trend"] == [0, 1]
    assert result["Noise"] == [3, 4]
    assert result["Seasonality"] == [2]

    with pytest.raises(ValueError, match="wildcard can only be specified once"):
        callback_services.parse_reconstruction_groups(
            rows=[("Noise", "*"), ("noise", "*")],
            window_size=4,
        )

    with pytest.raises(ValueError, match="component 5 is out of range"):
        callback_services.parse_reconstruction_groups(
            rows=[("Trend", "5")],
            window_size=5,
        )

    with pytest.raises(ValueError, match="Overlapping components detected"):
        callback_services.parse_reconstruction_groups(
            rows=[("Trend", "0,1"), ("Seasonality", "1")],
            window_size=3,
        )


def test_explained_variance_by_group_fallback_case_insensitive():
    ssa = DummySSA({"Trend": 12.345, "seasonality": 34.567})
    assert callback_services.explained_variance_by_group_fallback(ssa, "Trend") == pytest.approx(12.345)
    assert callback_services.explained_variance_by_group_fallback(ssa, "SEASONALITY") == pytest.approx(34.567)
    assert callback_services.explained_variance_by_group_fallback(ssa, "Unknown") == 0.0


def test_build_reconstruction_metadata_formats_output_correctly():
    ssa = DummySSA({"Trend": 25.0, "Noise": 75.0}, dw_value=1.9)
    metadata = callback_services.build_reconstruction_metadata(ssa, {"Trend": [0, 1], "Noise": [2]})

    assert isinstance(metadata, html.Div)
    assert any("Variation Associated with Trend" in str(child) for child in metadata.children[0].children)
    assert any("Durbin-Watson Statistic" in str(child) for child in metadata.children[0].children)


def test_parse_uploaded_series_handles_non_csv_excel_and_validation_errors():
    csv_text = "timestamp,value\n2024-01-01 00:00:00,1\n2024-01-01 01:00:00,2\n"
    payload = _csv_payload(csv_text)
    parsed = callback_services.parse_uploaded_series(payload, "test.csv", 10)
    assert parsed is not None
    assert parsed.index[0].year == 2024
    assert parsed.iloc[0] == 1

    with pytest.raises(ValueError, match="Unsupported file format"):
        callback_services.parse_uploaded_series(payload, "test.txt", 10)

    long_csv = "timestamp,value\n" + "\n".join(f"2024-01-01 {str(i).zfill(2)}:00:00,{i}" for i in range(100))
    long_payload = _csv_payload(long_csv)
    with pytest.raises(ValueError, match="maximum allowed is 10"):
        callback_services.parse_uploaded_series(long_payload, "test.csv", 10)
