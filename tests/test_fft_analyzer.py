import numpy as np
import pytest
from pandas import Series
from periodicity.fft_analyzer import FFT_Analyzer

@pytest.fixture
def sample_series():
    """Create a sample time series with known periodicity."""
    t = np.linspace(0, 10, 100)
    signal = 5 * np.sin(2 * np.pi * 0.5 * t) + np.random.normal(0, 0.1, len(t))
    return Series(signal)


def test_fft_analyzer_init(sample_series):
    """Test FFT_Analyzer initialization."""
    analyzer = FFT_Analyzer(sample_series)
    assert analyzer.fmin == 0.1
    assert analyzer.fmax == 2.0
    assert analyzer.num_freqs == 1000
    assert analyzer.freqs is None
    assert analyzer.power is None
    assert analyzer.periods is None
    assert analyzer.best_period is None


def test_fft_analyzer_custom_params(sample_series):
    """Test FFT_Analyzer with custom parameters."""
    analyzer = FFT_Analyzer(sample_series, fmin=0.2, fmax=3.0, num_freqs=500)
    assert analyzer.fmin == 0.2
    assert analyzer.fmax == 3.0
    assert analyzer.num_freqs == 500


def test_periodogram(sample_series):
    """Test periodogram computation."""
    analyzer = FFT_Analyzer(sample_series)
    periods, power, best_period = analyzer.periodogram()
    
    assert analyzer.freqs is not None
    assert analyzer.power is not None
    assert analyzer.periods is not None
    assert best_period is not None
    assert len(periods) == analyzer.num_freqs
    assert len(power) == analyzer.num_freqs
    assert isinstance(best_period, (float, np.floating))


def test_signal_centering(sample_series):
    """Test that signal is properly centered."""
    analyzer = FFT_Analyzer(sample_series)
    assert np.isclose(analyzer._df["signal_centered"].mean(), 0, atol=1e-10)


def test_best_period_is_max_power(sample_series):
    """Test that best_period corresponds to maximum power."""
    analyzer = FFT_Analyzer(sample_series)
    periods, power, best_period = analyzer.periodogram()
    
    max_power_idx = np.argmax(power)
    assert np.isclose(best_period, periods[max_power_idx])


def test_plot_without_periodogram(sample_series, monkeypatch):
    """Test that plot calls periodogram if not already computed."""
    analyzer = FFT_Analyzer(sample_series)
    monkeypatch.setattr("matplotlib.pyplot.show", lambda: None)
    
    assert analyzer.periods is None
    analyzer.plot()
    assert analyzer.periods is not None