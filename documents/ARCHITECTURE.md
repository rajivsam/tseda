# Architecture Overview

`tseda` is structured as a modular Python package with separate layers for data ingestion, SSA decomposition, diagnostics, notebook/API interfaces, and visualization.

The current implementation follows a segment-first analysis design: the full time series remains available as contextual context in the exploratory plots, while the selected segment becomes the active analytical target for decomposition, ACF/PACF diagnostics, and summary reporting. This keeps the workflow aligned with the actual modeling question—understanding the current regime rather than mixing multiple operating states into a single decomposition.

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
2. A candidate segmentation is derived from the full series and compared with the current analysis target.
3. The user selects the active segment for downstream analysis; the full series remains available as context for visualization.
4. SSA is performed on the selected segment with a candidate window size.
5. Eigen-spectrum heuristics identify trend, seasonality, and noise components.
6. Reconstructed signals are evaluated for structural suitability and optionally refined.
7. Change-point detectors run on trend, seasonal amplitude, and seasonal phase signals.
8. Results are exposed through plots, a notebook API, and export utilities.

## Segment-first analysis procedure

The interface now treats the selected segment as the single source of truth for analysis. The full series remains visible in the exploratory scatter plot and baseline diagnostics, but the downstream decomposition and statistical reporting operate on the active segment only.

This is important because a short or final regime in a time series can exaggerate noise and produce unstable estimates if the analyst tries to infer structure from the entire series without isolating the regime of interest. When the final segment has insufficient history, the workflow uses a half-life-weighted lookback from the immediately preceding segment instead of blindly fitting on too little data.

The lookback uses the half-life identity:

$\alpha = 1 - (1/2)^{1/h}$

or equivalently:

$(1 - \alpha)^h = 0.5$

where $h$ is the half-life in observation units and $\alpha$ is the EWMA smoothing parameter. This maps the intuitive idea of "half the weight decays after $h$ points" into the recursive EWMA parameterization used for local smoothing and stability checks.

This is consistent with the historical origins of exponential smoothing in Brown (1956) and Holt (1957), as well as the broader practice of using half-life as a human-readable decay window in risk and signal-processing workflows. For documentation and implementation reference, the design notes use the convention summarized in Brown, Holt, Rutherford, RiskMetrics, and the pandas `ewm(..., halflife=...)` API.

## Design review: rigor, transparency, and cross-domain reuse

The segment-first analysis design is statistically stronger than a whole-series-only workflow because it separates the exploratory context of the full series from the analytical target of the selected segment. This distinction matters when the underlying process is non-stationary, regime-dependent, or affected by a short final segment with insufficient history. The selected segment becomes the modeling unit, while the full series remains a contextual visualization layer. This makes the workflow more transparent to the analyst and reduces the risk of silently mixing regime changes into one decomposition.

This design is also methodologically conservative. The full series is not discarded; it is preserved as a context signal, but the downstream decomposition and diagnostic summaries operate on the chosen segment. That separation preserves interpretability and makes the analysis auditable: the user can see what was modeled, what was excluded from the formal analysis, and why the app is treating the selected region differently from the whole dataset.

The half-life parameterization is mathematically valid because it is a reparameterization of the same exponential decay model. The relationship

$$
\alpha = 1 - (1/2)^{1/h}
$$

and equivalently

$$
(1 - \alpha)^h = 0.5
$$

maps the human-interpretable concept of a half-life into the smoothing coefficient used in recursive EWMA models. This is not a distinct model family; it is the same exponential weighting expressed in a more interpretable time scale. For short or trailing segments, where a direct estimate would be unstable or underpowered, the half-life fallback is therefore a reasonable engineering choice for stability and local continuity, provided it is documented as a default heuristic and not claimed to be universally optimal.

The main principle for long-term reuse is explicitness. The workflow should clearly distinguish between:

- full-series context plots,
- active segment analysis,
- fallback smoothing assumptions,
- segment boundary metadata,
- warnings about short or weakly identified regimes.

This ensures that the design remains domain-independent. The same logic applies in operations, finance, energy, demand forecasting, and sensor monitoring: local structure is often more informative than a global average, and segment-aware exploration is more transparent than a single undifferentiated model over the whole history.

For a rigorous implementation, the system should continue to expose these assumptions in generated summaries and logs, including the selected segment index or boundary, the reason for a fallback, and the effective half-life or decay parameter used. That makes the design both transparent and reproducible, which is essential for cross-domain exploratory modeling and downstream decision-making.

## Deployment model

`tseda` is intended to be used as a library in notebooks or batch pipelines. The package can also support a semi-interactive review workflow through its UI components.
