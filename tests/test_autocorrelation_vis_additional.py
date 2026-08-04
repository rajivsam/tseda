import pandas as pd

from tseda.visualization.autocorrelation_vis import ACFPlotter


def test_calc_acf_returns_pyplot_module(monkeypatch):
    dates = pd.date_range(start='2023-01-01', periods=10)
    series = pd.Series(range(10), index=dates)
    plotter = ACFPlotter(series)

    def fake_plot_acf(series, lags):
        return None

    monkeypatch.setattr("statsmodels.api.graphics.tsa.plot_acf", fake_plot_acf)

    plt_module = plotter.calc_ACF()
    assert hasattr(plt_module, "plot")


def test_calc_pacf_populates_pacf_dataframe():
    dates = pd.date_range(start='2023-01-01', periods=10)
    series = pd.Series(range(10), index=dates)
    plotter = ACFPlotter(series, lags=5)

    plt_module = plotter.calc_PACF()
    assert hasattr(plt_module, "plot")
    assert plotter._pacf_df.shape[0] > 0
    assert "pacf" in plotter._pacf_df.columns
    assert "CI" in plotter._pacf_df.columns
