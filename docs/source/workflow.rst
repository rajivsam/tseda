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

Process-aware interpretation revision
--------------------------------------

SSA concentration alone is not a semantic classification of trend or seasonality.
A random walk or other persistent stochastic process can produce a concentrated,
steep eigen spectrum and smooth leading eigenvectors. The revised workflow first
classifies diffuse noise, deterministic structure, stochastic persistence,
periodic structure, or mixed/indeterminate behavior, then derives decomposition
groups that are compatible with that classification.

For pure random walks, visual smoothing can create pareidolia: apparent trends or
cycles in random/stochastic variation. ``stochastic_persistence`` is therefore
an assessment stop, not a deterministic SSA trend. The UI, notebook, and report
direct the user to random-walk, ARIMA/differenced, local-level, or state-space
models. A separately produced residual or innovation series may be analyzed as a
new input only if it independently passes identifiability checks.

The implementation specification is in
``documents/process_aware_ssa_design.md``. Runtime behavior, UI labels, notebook
outputs, and benchmark reports now use this process-aware classification.

Initial Assessment
------------------

You begin by loading a CSV in long format (timestamp column and value column) and
reviewing baseline diagnostics:

- Sampling properties and dataset profile (size, duration, inferred cadence).
- Distribution and spread (KDE and box plot).
- Raw signal visualization.
- Correlation structure via ACF and PACF plots.

This first pass provides a quick structural read on the data before decomposition.
The expected use case is regularly sampled data at intervals of five minutes or
longer, with missing values handled before upload.

Segment-first analysis and half-life fallback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The app treats the selected segment as the primary local analytic target, while
retaining the full series as a distinct evaluation scope. Slow structure such as
annual seasonality or an approximately eleven-year cycle cannot be inferred
reliably from a short final segment. Results must therefore state whether a
finding belongs to the full series, the active regime, or is indeterminate at one
of those scopes.

When the final segment is too short to support a stable estimate, the UI triggers a
short-tail warning and uses a half-life-weighted lookback from the preceding segment.
This is a stability safeguard, not a model change: it keeps the estimate anchored to
recent regime history without pretending the segment has enough points to stand on its
own.

The half-life mapping is the standard exponential-decay representation used in
recursive smoothing:

.. math::

   \alpha = 1 - (1/2)^{1/h}

and equivalently

.. math::

   (1 - \alpha)^h = 0.5

where :math:`h` is the half-life in observation units and :math:`\alpha` is the
EWMA smoothing factor. This is the same expression used when scaling a decay window to
human-readable time units instead of the more abstract smoothing parameter.

The design choice is consistent with the historical exponential smoothing literature
(Brown, 1956; Holt, 1957), the earlier half-life concept introduced by Rutherford,
and the modern practitioner standard popularized by RiskMetrics and by the explicit
`halflife` parameter in pandas `ewm`.

**References used for the lookback decision**

- Brown, R. G. (1956). *Exponential Smoothing for Predicting Demand*.
- Holt, C. C. (1957). *Forecasting seasonals and trends by exponentially weighted moving averages*.
- J.P. Morgan / Reuters (1996). *RiskMetrics — Technical Document*.
- McKinney, W., & others. (2010). *Data structures for statistical computing in python*.
- Rutherford, E. (1907). Early work on exponential decay and half-life.

Time Series Decomposition
-------------------------

The app applies Singular Spectrum Analysis (SSA) with a heuristic default window
derived from the inferred sampling frequency. You can change this window and compare
decomposition quality directly in the UI.

Initial window assignment and refinement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The revision changes a cadence-derived window from a single forced choice into a
set of candidate periods. The selected window must contain enough observations
for the intended cycle and retain a meaningful residual tail. A daily series may
require a seven-day calendar window even when a five-day business-week model is
also evaluated.

Cadence-to-window mapping:

+----------+----------------+
| Cadence  | Initial Window |
+==========+================+
| 5-minute | 288            |
+----------+----------------+
| 15-minute| 96             |
+----------+----------------+
| 30-minute| 48             |
+----------+----------------+
| Hourly   | 24             |
+----------+----------------+
| Daily    | 5              |
+----------+----------------+
| Weekly   | 4              |
+----------+----------------+
| Monthly  | 12             |
+----------+----------------+

The implementation target is to evaluate cadence-appropriate candidate sets:
hourly ``[24, 168]``, daily ``[5, 7, 14]``, weekly ``[4, 8]``, monthly
``[12, 24]`` plus configured domain periods, and quarterly ``[4, 8]``. The
legacy cadence table remains the current implementation until those tests land.

The pseudocode below describes the full setup procedure:

.. code-block:: text

    Algorithm: Initial SSA Window Setup

    Input:  regular time series x, inferred cadence c
    Params: min_tail_spread = 0.10

    --- Cadence-based initialization ---
    1.  If 5 minutes <= c < 1 hour -> w ← ceil(subhourly_cycle_minutes / c)
    2.  If c = hourly  -> w ← 24
    3.  If c = daily   -> w ← 5
    4.  If c = weekly  -> w ← 4
    5.  If c = monthly -> w ← 12
    6.  If cadence is unknown -> fail with "invalid window"

    --- Spectrum-spread refinement ---
    7.  Build SSA(x, w) and compute eigenvalues λ₁ ≥ ... ≥ λ_w
    8.  tail_ratio ← λ_w / Σᵢ λᵢ
    9.  While tail_ratio ≥ min_tail_spread and 2w ≤ floor(N/2):
          w ← 2w
          Rebuild SSA(x, w)
          tail_ratio ← λ_w / Σᵢ λᵢ

    --- Output ---
    10. Return final w as the decomposition default and slider value

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

Component grouping currently starts with a knee-based noise-floor estimate and
adjacent pair similarity. The design revision retains these as features but no
longer treats them as sufficient semantic evidence. Periodicity must also retain
an actual oscillatory pair, a cadence-appropriate period, enough complete cycles,
and support from the reconstructed or detrended signal. A singleton eigentriple
must not be labeled as seasonality.

The Durbin-Watson (DW) statistic remains a residual independence diagnostic. In
the revised implementation, the target interval is reported with uncertainty and
distance from the boundary; components are not added merely to force DW into
``[1.5, 2.5]``. Process classification and periodic verification are independent
of that optimization.

The pseudocode below documents the **current legacy** group-assignment procedure.
It remains useful for migration and regression comparison, but it is not the
target process-aware algorithm described above:

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

- ``docs/tutorial.md``

References
----------

- Sambasivan, Rajiv. 2026. "An Upcoming Python Package for Time Series Exploration." April 13.
    https://rajivsam.github.io/r2ds-blog/posts/tseda%20announcement/

- Sambasivan, Rajiv. 2026. "Exploring Time Series Signals." March 26.
    https://rajivsam.github.io/r2ds-blog/posts/markov_analysis_coffee_prices/
