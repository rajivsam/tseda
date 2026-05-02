Workflow
========

The application follows three phases that mirror the workflow introduced in the
announcement post:

- `An Upcoming Python Package for Time Series Exploration <https://rajivsam.github.io/r2ds-blog/posts/tseda%20announcement/>`_

The goal is to move from quick signal diagnostics to interpretable decomposition,
then to a documented model-selection and reporting step.

The three phases are:

1. Initial Assessment of Time Series
2. Time Series Decomposition
3. Observation Logging

Initial Assessment
------------------

You begin by loading a CSV in long format (timestamp column and value column) and
reviewing baseline diagnostics:

- Sampling properties and dataset profile (size, duration, inferred cadence).
- Distribution and spread (KDE and box plot).
- Raw signal visualization.
- Correlation structure via ACF and PACF plots.

This first pass provides a quick structural read on the data before decomposition.
At present, the expected use case is regularly sampled data (hourly or lower
frequency) with missing values handled before upload.

Time Series Decomposition
-------------------------

The app applies Singular Spectrum Analysis (SSA) with a heuristic default window
derived from the inferred sampling frequency. You can change this window and compare
decomposition quality directly in the UI.

In this step you inspect:

- Eigenvalue and explained-variance profiles.
- Eigenvector patterns.
- Weighted correlation between components.
- A suggested grouping table built from the SSA eigen spectrum.
- Reconstruction quality for user-defined groups (for example trend,
  seasonality, and noise).
- Residual diagnostics, including Durbin-Watson on the noise component.

Component grouping starts with an automatic heuristic: components explaining at least
10 percent of total variance are scanned in rank order, adjacent pairs within a 5
percent eigenvalue difference are suggested as seasonality, remaining eligible
components are suggested as trend, and everything else is assigned to noise.

The suggested grouping is rendered directly in the UI and prepopulates the editable
Trend, Seasonality, and Noise inputs. You can still regroup components based on
domain context and the diagnostic plots until the decomposition matches the intended
downstream objective.

API quick links
~~~~~~~~~~~~~~~

For implementation-level details, method signatures, and source links:

- :doc:`SSA decomposition module <api/tseda.decomposition.ssa_decomposition>`
- :doc:`SSA result summary module <api/tseda.decomposition.ssa_result_summary>`
- :doc:`Decomposition namespace <api/tseda.decomposition>`

Observation Logging
-------------------

The final step produces a report-ready summary with rank-wise model diagnostics and
editable narrative text.

Knowledge base save validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the Observation Logging phase, you can save observations to a KMDS knowledge base
by providing a directory and file name.

The UI validates the selected save location before writing:

- The directory must exist.
- The process must have write privileges for that directory.
- If validation fails, the UI shows an error and prevents save to that location.

The selected knowledge-base directory and file name are stored in application state
for the active session and are reset when the upload is cleared in the Initial
Assessment phase.

AIC-based model selection
~~~~~~~~~~~~~~~~~~~~~~~~~

SSA yields ordered components from an eigendecomposition of the trajectory matrix.
For each candidate rank $r$, ``tseda`` computes cumulative explained variance and the
remaining (noise) variance, then derives AIC-style scores from these variance terms.
This creates a practical rank-selection table/plot that helps answer:

- How many components are needed before gains flatten out?
- At what rank does unexplained variance become small enough for the use case?
- Does the selected rank align with an interpretable grouping (for example,
  trend + seasonality with a residual treated as noise)?

The generated observation text combines sampling metadata, descriptive statistics,
SSA decomposition notes, and residual diagnostics. You can edit this narrative before
export so the final report reflects both automated diagnostics and expert judgment.

References
----------

- Sambasivan, Rajiv. 2026. "An Upcoming Python Package for Time Series Exploration." April 13.
    https://rajivsam.github.io/r2ds-blog/posts/tseda%20announcement/

- Sambasivan, Rajiv. 2026. "Exploring Time Series Signals." March 26.
    https://rajivsam.github.io/r2ds-blog/posts/markov_analysis_coffee_prices/
