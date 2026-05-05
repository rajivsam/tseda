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
- SSA decomposition: component extraction, grouping, reconstruction, and diagnostics,
  including a knee-based (commonly used elbow heuristic) noise-floor estimate for
  initial signal-pool selection.
- Observation logging: AIC-by-rank summaries, editable narrative reporting, and
	validated knowledge-base save locations.

Design philosophy
-----------------

The package follows a few explicit design rules:

- UI and notebook parity: features available in the Dash UI are exposed through
	Python calls for notebook workflows.
- Configuration over hard-coding: algorithm constants and thresholds are loaded
	from ``tseda_config.yaml`` and can be tuned without editing source.
- Explicit decomposition controls: SSA window and component grouping are treated
	as first-class controls rather than hidden internals.
- Composable analysis: each plotting/diagnostic feature is a separate callable,
	allowing custom notebook pipelines and automated reports.

For installation and usage details, see :doc:`installation` and :doc:`workflow`.
