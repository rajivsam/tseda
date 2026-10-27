# Product Overview

`tseda` is an enterprise-grade Python framework for automated time series signal decomposition and diagnostics. It is designed to help analysts and data engineers detect structural features in regularly sampled time series, such as trend, seasonality, and noise, and to make those diagnostics reproducible and auditable.

## What it does

- Loads regularly sampled time series data from CSV or built-in examples.
- Automatically selects SSA parameters such as window size and grouping.
- Decomposes the signal into trend, seasonality, and noise components.
- Detects structural changes such as trend shifts, seasonal amplitude shifts, and seasonal phase shifts.
- Exports results in tabular form and integrates with a KMDS ontology-backed knowledge graph for lineage and observation logging.

## Primary users

- Data scientists who need reliable pre-processing for forecasting, anomaly detection, and signal modeling.
- Analytics engineers who need a reproducible decomposition workflow for operational pipelines.
- Decision intelligence teams that require audit-ready insights from time series diagnostics.

## Value proposition

- Reduces manual SSA tuning by automating window selection and component grouping.
- Helps identify whether data is structurally suitable for SSA before wasting effort on noisy series.
- Produces export-ready artifacts and structured observations for downstream review and compliance.

## Analysis procedure

`tseda` now follows a segment-first analysis workflow. The full series remains visible as context in the exploratory plots, but the selected segment is the analytical target for decomposition, ACF/PACF diagnostics, and summary text. This makes the workflow consistent with the decomposition question the analyst is actually trying to answer: the behaviour of the current regime, not the full history in aggregate.

When the final segment has too little history, `tseda` does not force an unstable estimate. Instead, it triggers a short-tail warning and applies a half-life-weighted lookback from the immediately preceding segment. The lookback uses the standard exponential-decay identity:

$$
\alpha = 1 - (1/2)^{1/h} \quad \text{and} \quad (1 - \alpha)^h = 0.5
$$

where $h$ is the effective half-life in observations. This makes the smoothing window interpretable in time units while preserving the recursive EWMA structure used in modern time-series software.

The design is consistent with Brown (1956), Holt (1957), the physical half-life concept introduced by Rutherford (1907), and the modern practitioner usage reflected in RiskMetrics and pandas `ewm(..., halflife=...)`.
