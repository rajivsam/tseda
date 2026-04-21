Overview
========

``tseda`` is designed for fast exploratory analysis of regularly sampled time series
(hourly or lower cadence) with Singular Spectrum Analysis (SSA).

Why SSA-first time series analysis
----------------------------------

Before model fitting, it is often useful to separate a series into structural parts:
trend or trend-cycle, seasonality, and noise. This helps you decide what signal
structure is worth keeping for downstream tasks such as forecasting, anomaly
detection, or monitoring.

``tseda`` uses an SSA-first workflow because SSA gives you a high-resolution
decomposition with one primary control parameter (window size). You can then inspect
explained variance, component groupings, and residual behavior before choosing any
downstream model.

For additional conceptual background and worked examples, see:

- `Exploring Time Series Signals <https://rajivsam.github.io/r2ds-blog/posts/markov_analysis_coffee_prices/>`_

Core capabilities
-----------------

- Initial assessment: data profile, spread, distribution, and autocorrelation cues.
- SSA decomposition: component extraction, grouping, reconstruction, and diagnostics.
- Observation logging: AIC-by-rank summaries, editable narrative reporting, and
	validated knowledge-base save locations.

For installation and usage details, see :doc:`installation` and :doc:`workflow`.
