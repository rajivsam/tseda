import pandas as pd

from tseda.notebook_api import NotebookThreeStepAPI


def _build_daily_series(n: int = 96) -> pd.Series:
    index = pd.date_range("2023-01-01", periods=n, freq="D")
    values = [
        20.0 + 0.1 * i + 3.0 * ((i % 12) / 12.0)
        for i in range(n)
    ]
    return pd.Series(values, index=index)


def test_notebook_api_window_and_grouping_controls():
    series = _build_daily_series()
    api = NotebookThreeStepAPI(series)

    assert api.get_window() > 0

    new_window = api.set_window(12, apply_window_refinement=False)
    assert new_window == 12

    grouping, _ = api.suggest_grouping()
    assert isinstance(grouping, dict)
    assert api.get_grouping()


def test_notebook_api_kde_bin_algorithm_and_step3_outputs():
    series = _build_daily_series()
    api = NotebookThreeStepAPI(series, window=12)

    kde_fig = api.get_kde_plot(bin_algorithm="scott")
    assert kde_fig is not None

    grouping, _ = api.suggest_grouping()
    api.set_grouping(grouping=grouping)

    var_fig = api.get_variance_explained_plot()
    txt = api.generate_observation_text()

    assert var_fig is not None
    assert isinstance(txt, str)
    assert len(txt) > 20


def test_notebook_api_exposes_grouping_configuration_and_override():
    series = _build_daily_series()
    api = NotebookThreeStepAPI(series, window=12)

    grouping_cfg = api.get_grouping_heuristic_configuration()
    assert isinstance(grouping_cfg, dict)
    assert "pool_selection_method" in grouping_cfg

    grouping, dw_ok = api.suggest_grouping(
        grouping_config={
            "pool_selection_method": "variance_threshold",
            "variance_threshold": 0.10,
        }
    )
    assert isinstance(grouping, dict)
    assert isinstance(dw_ok, bool)


def test_notebook_api_grouping_window_autotune_returns_result_payload():
    series = _build_daily_series(n=180)
    api = NotebookThreeStepAPI(series, window=5, apply_window_refinement=False)

    result = api.suggest_grouping_with_window_autotune()

    assert isinstance(result.grouping, dict)
    assert isinstance(result.dw_in_range, bool)
    assert isinstance(result.windows_tried, list)
    assert len(result.windows_tried) >= 1
    assert result.initial_window == 5
    assert result.final_window == api.get_window()
    assert isinstance(result.reason, str)


def test_notebook_api_grouping_window_autotune_rejects_invalid_doubling_factor():
    series = _build_daily_series(n=120)
    api = NotebookThreeStepAPI(series, window=12, apply_window_refinement=False)

    try:
        api.suggest_grouping_with_window_autotune(doubling_factor=1)
        assert False, "Expected ValueError for invalid doubling_factor"
    except ValueError as exc:
        assert "doubling_factor" in str(exc)
