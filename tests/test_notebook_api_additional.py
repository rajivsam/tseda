import importlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import tseda
from tseda import notebook_api
from tseda.notebook_api import AVAILABLE_BIN_ALGORITHMS, NotebookThreeStepAPI, EXAMPLE_DATASETS


def test_get_agent_instructions_contains_beads_section():
    text = tseda.get_agent_instructions()
    assert isinstance(text, str)
    assert "bd ready" in text


def test_get_column_index_and_label_resolution():
    frame = pd.DataFrame({"timestamp": ["2024-01-01"], "value": [1]})
    assert notebook_api._get_column(frame, 0).tolist() == ["2024-01-01"]
    assert notebook_api._get_column(frame, "value").tolist() == [1]

    with pytest.raises(IndexError):
        notebook_api._get_column(frame, 2)
    with pytest.raises(KeyError):
        notebook_api._get_column(frame, "missing")


def test_as_datetime_numeric_series_parses_valid_frame_and_rejects_invalid():
    frame = pd.DataFrame(
        {"timestamp": ["2024-01-01", "2024-01-02"], "value": ["1", "2"]}
    )
    series = notebook_api._as_datetime_numeric_series(frame, "timestamp", "value")
    assert len(series) == 2
    assert isinstance(series.index, pd.DatetimeIndex)
    assert series.iloc[0] == 1

    bad_frame = pd.DataFrame({"timestamp": ["bad", "also bad"], "value": ["x", "y"]})
    with pytest.raises(ValueError, match="No valid datetime/value rows"):
        notebook_api._as_datetime_numeric_series(bad_frame, "timestamp", "value")


def test_load_series_from_csv_and_example_dataset(tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("timestamp,value\n2024-01-01,1\n2024-01-02,2\n", encoding="utf-8")

    series = notebook_api.load_series_from_csv(csv_path)
    assert series.iloc[0] == 1
    assert series.index[0].year == 2024

    with pytest.raises(FileNotFoundError):
        notebook_api.load_series_from_csv(tmp_path / "missing.csv")

    example_key = next(iter(EXAMPLE_DATASETS))
    example_series = notebook_api.load_example_series(example_key, workspace_root=Path.cwd())
    assert isinstance(example_series, pd.Series)
    assert isinstance(example_series.index, pd.DatetimeIndex)

    with pytest.raises(KeyError):
        notebook_api.load_example_series("not-a-dataset")


def test_resolve_bin_count_explicit_and_algorithm_errors():
    series = pd.Series(range(10), index=pd.date_range("2024-01-01", periods=10, freq="D"))
    api = NotebookThreeStepAPI(series, window=5, apply_window_refinement=False)

    assert api._resolve_bin_count(bin_count=5, bin_algorithm="auto") == 5
    with pytest.raises(ValueError, match="positive integer"):
        api._resolve_bin_count(bin_count=0, bin_algorithm="auto")
    with pytest.raises(ValueError, match="Unsupported bin_algorithm"):
        api._resolve_bin_count(bin_count=None, bin_algorithm="invalid")

    auto_bins = api._resolve_bin_count(bin_count=None, bin_algorithm="scott")
    assert isinstance(auto_bins, int)
    assert auto_bins >= 1


def test_get_configuration_accessor_methods_return_dicts():
    series = pd.Series(range(10), index=pd.date_range("2024-01-01", periods=10, freq="D"))
    api = NotebookThreeStepAPI(series, window=5, apply_window_refinement=False)

    cfg = api.get_configuration()
    assert isinstance(cfg, dict)
    assert "file_upload" in cfg

    heuristic_cfg = api.get_grouping_heuristic_configuration()
    assert isinstance(heuristic_cfg, dict)
    assert "pool_selection_method" in heuristic_cfg


def test_get_suitability_result_with_override_threshold():
    series = pd.Series(range(10), index=pd.date_range("2024-01-01", periods=10, freq="D"))
    api = NotebookThreeStepAPI(series, window=5, apply_window_refinement=False)

    result = api.get_suitability_result(top_k_eigenvectors=1, min_explained_variance=0.0)
    assert result.is_suitable is True
    assert result.top_k == 1
    assert result.threshold == 0.0


def test_set_grouping_rejects_invalid_and_overlapping_indices():
    series = pd.Series(range(15), index=pd.date_range("2024-01-01", periods=15, freq="D"))
    api = NotebookThreeStepAPI(series, window=5, apply_window_refinement=False)

    with pytest.raises(ValueError, match="out of range"):
        api.set_grouping(grouping={"Trend": [0, 1], "Seasonality": [5], "Noise": []})

    with pytest.raises(ValueError, match="overlapping component indices"):
        api.set_grouping(grouping={"Trend": [0], "Seasonality": [0], "Noise": [2]})


def test_reconstruction_metadata_and_export_dataframe_produce_expected_output():
    series = pd.Series(
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        index=pd.date_range("2024-01-01", periods=6, freq="D"),
    )
    api = NotebookThreeStepAPI(series, window=3, apply_window_refinement=False)
    grouping, _ = api.suggest_grouping()
    api.set_grouping(grouping=grouping)

    metadata = api.get_reconstruction_metadata()
    assert "grouping" in metadata
    assert "durbin_watson" in metadata

    df = api.export_components_dataframe()
    assert list(df.columns) == ["timestamp", "Trend", "Seasonality", "Noise"]
    assert len(df) == 6


def test_main_entrypoint_imports_ui_function(monkeypatch):
    import tseda.user_interface.ts_analyze_ui as ui_module
    import tseda.__main__ as main_module

    called = []

    def stub_main():
        called.append(True)

    monkeypatch.setattr(ui_module, "main", stub_main)
    reloaded = importlib.reload(main_module)
    reloaded.main()
    assert called == [True]
