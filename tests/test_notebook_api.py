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
