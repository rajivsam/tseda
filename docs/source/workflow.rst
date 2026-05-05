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

Initial window assignment and refinement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The initial SSA window is selected from inferred cadence, then refined using a
tail-spread check on the SSA eigen spectrum. The objective is to avoid starting
from a window where the smallest eigenvalue still explains too much variance.

Cadence-to-window mapping:

+----------+----------------+
| Cadence  | Initial Window |
+==========+================+
| Hourly   | 24             |
+----------+----------------+
| Daily    | 5              |
+----------+----------------+
| Weekly   | 4              |
+----------+----------------+
| Monthly  | 12             |
+----------+----------------+

The pseudocode below describes the full setup procedure:

.. code-block:: text

    Algorithm: Initial SSA Window Setup

    Input:  regular time series x, inferred cadence c
    Params: min_tail_spread = 0.10

    --- Cadence-based initialization ---
    1.  If c = hourly  -> w ← 24
    2.  If c = daily   -> w ← 5
    3.  If c = weekly  -> w ← 4
    4.  If c = monthly -> w ← 12
    5.  If cadence is unknown -> fail with "invalid window"

    --- Spectrum-spread refinement ---
    6.  Build SSA(x, w) and compute eigenvalues λ₁ ≥ ... ≥ λ_w
    7.  tail_ratio ← λ_w / Σᵢ λᵢ
    8.  While tail_ratio ≥ min_tail_spread and 2w ≤ floor(N/2):
          w ← 2w
          Rebuild SSA(x, w)
          tail_ratio ← λ_w / Σᵢ λᵢ

    --- Output ---
    9.  Return final w as the decomposition default and slider value

In the UI, this final value is surfaced as the Step-2 default and remains
user-overridable via the window slider.

In this step you inspect:

- Eigenvalue and explained-variance profiles.
- Eigenvector patterns.
- Weighted correlation between components.
- A suggested grouping table built from the SSA eigen spectrum.
- Reconstruction quality for user-defined groups (for example trend,
  seasonality, and noise).
- Residual diagnostics, including Durbin-Watson on the noise component.

Component grouping starts with an automatic heuristic that uses a knee-based
noise-floor estimate on the eigen spectrum. This type of knee/elbow detection is a
commonly used heuristic for separating dominant structure from tail components in
ranked spectra. In ``tseda``, components up to the detected knee are treated as the
initial signal pool, then scanned in rank order: adjacent pairs within a 5 percent
eigenvalue difference are suggested as seasonality, remaining eligible components are
suggested as trend, and everything else is assigned to noise.

The Durbin-Watson (DW) statistic is computed on the noise residual to validate the
assignment. If DW falls outside [1.5, 2.5] the algorithm expands the assignment one
component at a time (promoting from the noise pool), tracking the assignment closest
to DW = 2.0, until the criterion is met or only two noise components remain. If the
criterion is never met the user is asked to try a different window size.

The pseudocode below describes the full group-assignment procedure:

.. code-block:: text

    Algorithm: SSA Eigenvalue Group Assignment

    Input:  eigenvalues λ₁ ≥ λ₂ ≥ ... ≥ λₖ (sorted descending),
            noise residual r
    Params: pool_selection_method = "kneedle",
            kneedle_min_distance = 0.03,
            min_signal_components = 1,
            min_noise_components = 2,
            variance_threshold = 0.10,   // legacy fallback mode only
            pair_tolerance = 0.05,
            dw_low = 1.5, dw_high = 2.5

    --- Initial classification ---
    1.  Trend ← ∅;  Seasonality ← ∅
    2.  If pool_selection_method = "kneedle":
          a) yᵢ ← log(1 + λᵢ)
          b) Normalize y between first and last points
          c) Compute distance to endpoint chord line
          d) knee ← argmax(distance) if max(distance) ≥ kneedle_min_distance
          e) Eligible ← {0..knee} with bounds:
                min |Eligible| = min_signal_components
                max |Eligible| = K - min_noise_components
        Else (legacy fallback):
          Eligible ← { i : (λᵢ / Σⱼ λⱼ) ≥ variance_threshold }
    3.  Noise ← all indices not in Eligible

    --- Scan eligible components in rank order ---
    4.  cursor ← 0
    5.  While cursor < |Eligible|:
          j ← Eligible[cursor]
          k ← Eligible[cursor + 1]  (if it exists)
          if k = j + 1  and  |λⱼ − λₖ| / max(λⱼ, λₖ) ≤ pair_tolerance then
              Seasonality ← Seasonality ∪ { j, k }
              cursor ← cursor + 2
          else
              Trend ← Trend ∪ { j }
              cursor ← cursor + 1

    --- Validate with Durbin-Watson ---
    6.  r_noise ← r − Σᵢ∈(Trend∪Seasonality) component(i)
    7.  dw ← DurbinWatson(r_noise)
    8.  best ← current assignment;  best_dist ← |dw − 2.0|

    --- Iterative expansion from noise pool ---
    9.  While dw ∉ [dw_low, dw_high]  and  |Noise| > 0:
          candidate ← Noise[0]          // largest remaining noise eigenvalue
          next      ← Noise[1]  (if it exists)
          if next = candidate + 1  and  |λ_candidate − λ_next| / max(…) ≤ pair_tolerance then
              Seasonality ← Seasonality ∪ { candidate, next }
              Noise ← Noise \ { candidate, next }
          else
              Trend ← Trend ∪ { candidate }
              Noise ← Noise \ { candidate }
          r_noise ← r − Σᵢ∈(Trend∪Seasonality) component(i)
          dw ← DurbinWatson(r_noise)
          if |dw − 2.0| < best_dist then
              best ← current assignment;  best_dist ← |dw − 2.0|

    --- Output ---
        10. If dw ∉ [dw_low, dw_high]:
            Return best  with warning "DW criterion not met — try a different window size"
        11. Else:
            Return (Trend, Seasonality, Noise)

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

Notebook API parity
-------------------

The same three-step workflow is available in notebooks through
``tseda.notebook_api.NotebookThreeStepAPI``.

The API exposes one-call-per-feature methods for:

- Step 1: KDE, box, scatter, ACF, PACF, sampling properties, and summary stats.
- Step 2: eigen plots, change-point plots, LOESS, noise KDE, and reconstruction.
- Step 3: rank-wise variance plots and generated observation text.

Important control points are explicit in the notebook API:

- ``get_window()`` and ``set_window(...)`` for SSA window control.
- ``suggest_grouping()``, ``get_grouping()``, and ``set_grouping(...)`` for
    component assignments.
- ``get_kde_plot(..., bin_algorithm=...)`` for histogram bin-rule selection,
    including ``scott``, ``fd``, ``sturges``, and other NumPy-supported rules.
- ``get_suitability_result(...)`` for the same top-k eigenvalue concentration
    gate used by the UI.

For a complete multi-dataset notebook walkthrough, see:

- ``notebooks/notebook_three_step_api_examples.ipynb``

References
----------

- Sambasivan, Rajiv. 2026. "An Upcoming Python Package for Time Series Exploration." April 13.
    https://rajivsam.github.io/r2ds-blog/posts/tseda%20announcement/

- Sambasivan, Rajiv. 2026. "Exploring Time Series Signals." March 26.
    https://rajivsam.github.io/r2ds-blog/posts/markov_analysis_coffee_prices/
