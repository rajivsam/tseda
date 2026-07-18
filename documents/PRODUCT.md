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
