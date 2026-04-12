Workflow
========

The application follows three phases:

1. Initial Assessment of Time Series
2. Time Series Decomposition
3. Observation Logging

Initial Assessment
------------------

You inspect spread and distribution (KDE and box plot), plus ACF/PACF cues.

Time Series Decomposition
-------------------------

The app applies Singular Spectrum Analysis (SSA), using a heuristic default window from detected frequency. The user can alter window size and grouping in the UI.

Observation Logging
-------------------

The app presents AIC-by-rank and generated observations, and allows users to refine report text before export.
