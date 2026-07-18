# Architecture Overview

`tseda` is structured as a modular Python package with separate layers for data ingestion, SSA decomposition, diagnostics, notebook/API interfaces, and visualization.

## Core layers

- `src/tseda/dataloader`: Data loading helpers for example datasets, Kaggle-style imports, and local CSV files.
- `src/tseda/decomposition`: SSA decomposition, automatic grouping heuristics, change-point detection, and signal reconstruction.
- `src/tseda/notebook_api.py`: Notebook-friendly API for the three-step analysis workflow, including window selection, grouping, and reporting.
- `src/tseda/user_interface`: Interactive Plotly/Dash components and callback services for exploratory analysis.
- `src/tseda/periodicity` and `src/tseda/series_stats`: Frequency and sampling diagnostics used to guide SSA configuration.

## Design principles

- **Separation of concerns**: Decomposition logic is isolated from UI and notebook orchestration.
- **Configuration-first**: Thresholds and heuristics are centralized in `src/tseda/config/tseda_config.yaml`.
- **Auditability**: Analytical outputs and decisions can be exported and logged using KMDS writer support.
- **Incremental validation**: The core workflow validates input suitability before producing decomposition and change-point diagnostics.

## Data flow

1. Input series is loaded and preprocessed.
2. SSA is performed with a candidate window size.
3. Eigen-spectrum heuristics identify trend, seasonality, and noise components.
4. Reconstructed signals are evaluated for structural suitability and optionally refined.
5. Change-point detectors run on trend, seasonal amplitude, and seasonal phase signals.
6. Results are exposed through plots, a notebook API, and export utilities.

## Deployment model

`tseda` is intended to be used as a library in notebooks or batch pipelines. The package can also support a semi-interactive review workflow through its UI components.
