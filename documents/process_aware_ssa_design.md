# Process-Aware SSA Design Revision

## Status

Reviewed architecture revision for Item 2, approved as the implementation
specification subject to empirical threshold calibration. This document specifies
the intended behavior and validation gates. It does not change the current runtime
behavior by itself. User-facing help, screenshots, tutorials, and labels should be
updated after the implementation passes the acceptance tests defined below.

## Problem

The current pipeline treats dominant SSA eigenvalues as evidence for a
deterministic decomposition into `Trend`, `Seasonality`, and `Noise`. That model is
insufficient for a stochastic persistent series: a random walk or highly
persistent AR process can have a highly concentrated, smooth eigen spectrum, and
therefore look more “suitable” than a finite deterministic seasonal series.

Observed failures motivate this revision:

- A smooth leading random-walk eigentriple can be promoted to `Seasonality`.
- A single component can become a seasonal group even though periodic structure
  requires an oscillatory pair and enough complete cycles.
- The top-five suitability ratio is degenerate when the SSA window is four or
  five, because it can equal 100% by construction.
- The daily default window of five samples tests a business-week hypothesis, not
  a general seven-day calendar cycle.
- Full-series structure and active-regime structure are currently conflated in
  benchmark reporting.
- Durbin-Watson is used both as a residual diagnostic and as an optimization
  target for component assignment.

## Design goals

1. Classify the generating-process behavior before assigning components.
2. Distinguish deterministic periodicity from stochastic persistence.
3. Preserve full-series and active-regime results as separate scopes.
4. Require evidence that is interpretable at the inferred cadence.
5. Report uncertainty for short or underpowered observations.
6. Keep Monte Carlo and stationarity evidence as diagnostics, not as a claim of
   a single true model.
7. Keep threshold values in configuration rather than in source code.

## Revised result model

The public analysis result must separate process classification, suitability, and
decomposition:

```text
ProcessClassification:
  scope: full_series | active_regime
  label: diffuse_noise | stationary_irregular | deterministic_trend
       | stochastic_persistence | periodic | mixed
  subtype: unit_root_like | high_persistence_ar | persistent_with_regimes | None
  confidence: float | None
  evidence: DiagnosticEvidence

DecompositionSuitability:
  scope: full_series | active_regime
  status: suitable | unsuitable | indeterminate
  reason: explicit machine-readable reason
  evidence: DiagnosticEvidence

DiagnosticSupport:
  scope: full_series | active_regime
  status: supported | unsupported | indeterminate
  reason: explicit machine-readable reason

PeriodicComponent:
  scope: full_series | active_regime
  period: float
  accepted_period_band: tuple[float, float]
  confidence: float
  eigenvalue_pair: tuple[int, int] | None
  seasonal_strength: float
  cycle_count: float

PersistentComponent:
  scope: full_series | active_regime
  component_indices: tuple[int, ...]
  null_compatibility: random_walk | high_persistence_ar | mixed_persistence
  monte_carlo_percentile: float | None

ScopeAnalysisResult:
  schema_version: str
  scope: AnalysisScope
  process_classification: ProcessClassification
  diagnostic_support: DiagnosticSupport
  decomposition_suitability: DecompositionSuitability
  periodic_components: list[PeriodicComponent]
  persistent_components: list[PersistentComponent]
  evidence: DiagnosticEvidence
```

`confidence` is a held-out-calibrated 0–1 classification score, not a posterior
probability and not a p-value. It is `None` when the applicable null or
calibration is unavailable.

Backward compatibility:

- Existing callers may continue to receive legacy `Trend`, `Seasonality`, and
  `Noise` groups.
- A legacy `Seasonality` group must only be populated after periodic verification.
- “Suitable” must no longer imply “deterministic trend or seasonality.”
- A process may support reliable classification while being unsuitable for a
  deterministic SSA reconstruction. These are separate decisions.
- `Persistence` is a process-evidence label for stochastic low-frequency
  behavior. A pure stochastic-persistence scope stops before deterministic SSA
  reconstruction; it is not automatically exposed as a reconstructed group.
- Legacy consumers do not receive a reconstructed `Persistence` group for a pure
  persistence stop. The authoritative result records the process class and stop
  reason instead.
- `process_classification` and `periodic_components` are the authoritative
  semantic outputs for notebook, UI, reports, and KMDS capture.

## Analysis scopes

`tseda` must compute and retain two scopes:

1. **Full-series scope**: used for slowly recurring structure, long-cycle
   assessment, and benchmark ground-truth comparison.
2. **Active-regime scope**: used for the user's current local analysis, model
   monitoring, and regime-specific change-point detection.

Both scopes include:

- the analyzed index range,
- observation count,
- expected and minimum cycle counts,
- SSA window,
- diagnostics,
- classification,
- uncertainty notes.

Active-regime selection must be reproducible:

1. use explicit user-supplied start/end bounds when present;
2. otherwise use PELT boundaries generated by the shared segmentation service;
3. if PELT returns no valid boundary, use the configured deterministic chunk
   fallback;
4. select the final segment by default unless the user selects another segment;
5. apply the existing half-life adjustment only to a short final segment and
   record original bounds, adjusted bounds, cadence minimum, and acceptance flag.

The implementation must extract this logic from UI globals into a pure shared
service. Notebook batch evaluation and UI callbacks must call that same service
so a benchmark result can be reproduced from its stored boundary metadata. Each
scope selects and records its own SSA window; the full-series window is not
silently reused for the active regime.

The full series remains the correct scope for 12-month car-sales seasonality,
seven-day page views, and the approximately 132-month sunspot cycle. The active
regime remains the correct scope for recent operational behavior and local
variance changes.

## Diagnostic pipeline

### 1. Validate identifiability

Before process classification:

- reject constant or non-numeric inputs;
- require a regular cadence;
- require a configurable minimum observation count;
- require enough room for at least a small residual tail in the SSA spectrum;
- mark classification as `indeterminate` when a requested period cannot supply
  the configured minimum number of cycles.

Missingness and cadence are handled as follows:

- Source gaps remain explicit; `tseda` does not silently interpolate to satisfy
  SSA.
- For regularly sampled physical series such as UCI CO, extract qualifying
  contiguous complete runs for SSA. A run must meet the same minimum-cycle and
  minimum-observation requirements for a **run-level** candidate. The normal
  five-cycle floor is applied to the aggregate across qualifying runs; a
  contiguous run requires at least two complete cycles before contributing.
  Aggregate evidence across runs with observation-count weighting and retain
  the gap count/rate. This allows a repeated daily signal to be evaluated across
  many short sensor runs without interpolating missing measurements.
- Use an irregular-timestamp method such as Lomb-Scargle on the complete
  timestamped series as a separate periodicity confirmation; it does not replace
  the contiguous-run SSA pair requirement.
- Count data may retain explicit zeros when those zeros are part of the source
  transformation, as for NYC 311. They must be reported as structural zeros, not
  treated as missing observations.
- A scope with no qualifying contiguous run is `indeterminate`, not imputed.

The former top-k ratio remains one feature, but it is not a standalone suitability
decision. In particular, it must not return `suitable` solely because the
requested `k` is at least the spectrum length.

### 2. Evaluate candidate windows and periods

Cadence defines candidate periods, not a single forced window:

| Cadence | Default candidate periods |
|---|---|
| Hourly | 24, 168 |
| Daily | 5, 7, 14 |
| Weekly | 4, 8 |
| Monthly | 12, 24, configured/domain-specific long periods |
| Quarterly | 4, 8 |

Domain-specific configuration may add a period such as approximately 132 months
for sunspots. Financial series may provide no periodic candidate by default.
Daily calendar series must not be accepted on a five-day business cycle unless
the series is explicitly tagged as business-day data.

For a candidate period `P`, the SSA window begins at `L=P` and may evaluate
`L=2P` when both `L <= N/2` and the configured cycle-count floor is retained.
The accepted period must fall within a configured band around the candidate.
For quasi-periodic structure, such as the solar cycle, the candidate is a period
band rather than an exact integer: its reconstructed-pair peak may vary within
that band, and the output records the fitted period plus acceptance tolerance.
Every evaluated candidate records:

- candidate period,
- SSA window,
- completed cycles,
- period evidence,
- reason accepted or rejected.

Candidate search is bounded by configured maximum windows and candidate counts.
Diagnostics are cached per scope/window, and Monte Carlo nulls are evaluated
lazily for ambiguous or persistent classifications rather than on every plotting
call.

### 3. Characterize the level eigen spectrum

For each scope/window, compute:

- normalized eigenvalue ratios and top-k concentration;
- log-log decay slope and fit quality;
- tail-spectrum diffusion;
- leading EOF smoothness and zero-crossing count;
- adjacent-pair ratios;
- phase-quadrature evidence for candidate pairs.

These features distinguish:

- a diffuse white-noise floor;
- a concentrated, monotonic persistence spectrum;
- isolated oscillatory pairs;
- weak or indeterminate short-window evidence.

### 4. Apply the stochastic-persistence safeguard

Stochastic persistence is supported when the joint evidence shows:

1. high leading-eigenvalue concentration;
2. a steep, well-fit spectral decay, close to a power-law rather than a sharp
   elbow;
3. smooth, low-frequency leading eigenvectors;
4. no independently verified periodic eigentriple pair;
5. concentration and low-frequency structure collapse after first differencing;
6. unit-root and stationarity diagnostics are consistent with persistence after
   accounting for a deterministic trend alternative;
7. the level spectrum is not exceptional relative to matched Monte Carlo
   random-walk or high-persistence AR surrogates and is materially less compatible
   with the deterministic-trend or diffuse-noise nulls.

The Monte Carlo comparison should include at least:

- a white-noise/diffuse null;
- a deterministic-trend plus noise null;
- a random-walk or random-walk-with-drift null;
- a configurable high-persistence AR(1) null.

The persistence-relevant nulls must match:

- series length,
- SSA window,
- first-difference drift,
- innovation scale,
- optional regime-specific innovation variance.

The preferred comparison is a joint distance based on spectral slope,
concentration, EOF smoothness, and post-difference concentration. The model
should classify `stochastic_persistence` rather than claim an exact unit root
when random-walk and AR(1) nulls overlap.

### Pareidolia guardrail for stochastic persistence

For a pure random walk, visual smoothing can create pareidolia: viewers may see
trends, cycles, or regime boundaries in random/stochastic variation. A smooth
SSA reconstruction is therefore evidence for statistical smoothness, not proof
of deterministic structure.

Every notebook, UI, observation, report, and exported diagnostic must state:

> Do not interpret smooth SSA level modes as deterministic trend or seasonality.
> Stochastic-persistence series should be investigated with random-walk,
> ARIMA/differenced, local-level, or state-space models. This tool is not the
> right exploration choice for the level process.

The scope is then unsuitable for deterministic SSA. Direct API grouping must be
blocked; any independently produced residual, innovation, or differenced series
starts a separate analysis and receives a fresh result.

The ADF and KPSS tests are confirmatory diagnostics, not the sole classifier.
Use both constant-only and trend-adjusted unit-root specifications when a
deterministic trend remains plausible.
Expected random-walk-like evidence is:

- ADF does not reject a unit root in levels;
- KPSS rejects level stationarity;
- ADF rejects a unit root after first differencing.

### 5. Verify deterministic periodicity

A component is periodic only when all applicable conditions are met:

1. the candidate period supplies the configured minimum number of cycles;
2. an adjacent SSA eigenpair exists within the pair tolerance;
3. the pair eigenvectors/reconstructed series support the expected period;
4. phase-quadrature evidence supports an oscillatory pair;
5. residual or detrended spectral evidence supports the period;
6. the process is not better explained by the stochastic-persistence classifier.

A singleton eigentriple may be assigned to `Trend` or remain unclassified. It
must not be assigned to `Seasonality`.

The implementation may use robust STL strength as an independent confirmation,
but SSA eigenpair evidence remains required for an SSA periodic grouping.

For a persistent process, reconstruction order is:

1. reconstruct verified deterministic periodic pairs;
2. reconstruct verified deterministic trend modes;
3. for mixed data, retain verified periodic/deterministic components only under
   their supported semantics;
4. treat the remainder as `Noise`.

Durbin-Watson is calculated for both the final residual and, where applicable,
the first differences of the persistent-mode reconstruction. The latter
prevents a level-signal random walk from producing an apparently autocorrelated
residual by construction.

### 6. Reconstruct and score residuals

After process-aware grouping:

- compute reconstruction and residual series;
- report variance explained with uncertainty/qualification;
- compute Durbin-Watson as a diagnostic with target band and distance;
- do not add components solely to force DW into a target interval;
- preserve the best explainable grouping when DW is borderline;
- run variance change-point detection on:
  - first differences for stochastic-persistence level data;
  - reconstruction residuals for periodic/deterministic data;
  - a count-aware or explicitly documented transform for operational count data.

## Classification decision table

| Evidence | Classification |
|---|---|
| Diffuse level spectrum, no concentration, no repeatable period | `diffuse_noise` |
| Finite deterministic drift, low stochastic-persistence score | `deterministic_trend` |
| Steep smooth spectrum, diffuse differences, unit-root/null-consistent behavior | `stochastic_persistence` |
| Weak concentration with finite-memory autocorrelation and no verified period | `stationary_irregular` |
| Verified SSA pair plus cadence-appropriate period and sufficient cycles | `periodic` |
| Verified periodic pair plus deterministic or stochastic level behavior | `mixed` |
| Too short, irregular, or contradictory evidence | indeterminate status |

For compatibility, decomposition labels are a derived view:

- `Trend`: deterministic level components that are not oscillatory;
- `Seasonality`: verified periodic components only;
- `Noise`: residual or unassigned finite-memory structure.

Stochastic persistence is not mislabeled as deterministic `Trend` or
`Seasonality`.

## Benchmark acceptance criteria

The comprehensive benchmark must evaluate both full-series and active-regime
scopes. It must assert semantic outcomes rather than only field types.

| Dataset | Required classification evidence |
|---|---|
| White noise | `diffuse_noise`; unsuitable; no trend/seasonality |
| GOOG | `stochastic_persistence`; no deterministic seasonality |
| Coffee | persistent with regime/variance caveat; no forced seasonality |
| Biomass | deterministic/regime trend dominated; no forced short fixed cycle |
| Car sales | full-series 12-month periodicity; active segment marked short |
| UCI CO | 24-hour periodicity; weekly evidence evaluated separately |
| NYC 311 | 24-hour and weekly evidence; high-noise/count caveat |
| Japan arrivals | four-quarter periodicity; DW boundary uncertainty |
| Hyndsight | seven-day periodicity; window must be at least seven |
| Sunspots | approximately 132-month full-series cycle; insufficient active-segment confidence |
| US consumption changes | no four-quarter deterministic seasonality; stationary/irregular classification allowed |

The NYC 311 snapshot is live and must not assert a fixed row range or exact
change-point timestamp. Its tests assert supported period classes and
count/heteroscedasticity caveats, with snapshot provenance recorded in the
artifact.

## Synthetic validation suite

Use two disjoint deterministic-seed sets:

- **Calibration set**: 100 replications per DGP/length/SNR cell, used only to
  select and document thresholds.
- **Held-out evaluation set**: 200 replications per DGP/length/SNR cell. No
  threshold changes are permitted after results are inspected.

The calibration/evaluation grids cover observation counts `100`, `240`, and
`720`, and innovation-to-signal SNRs `0.25`, `0.5`, `1.0`, and `2.0` where a
signal is present. Periodic DGPs use the cadence-appropriate periods and require
at least five cycles. Report a Wilson 95% confidence interval for every rate.

Add deterministic, seeded DGPs for:

1. independent white noise;
2. AR(1) with \(\phi=0.95\);
3. random walk;
4. random walk with drift;
5. deterministic linear trend plus white noise;
6. nonlinear deterministic trend;
7. trend plus one known periodic signal;
8. trend plus multiple known periodic signals;
9. periodic signal with one variance shift;
10. random walk with one innovation-variance shift.

Initial quality targets:

- random-walk/stochastic-persistence recall of at least 85%;
- deterministic trend and periodic false-positive persistence rate below 5%;
- deterministic periodic false-negative rate below 5% when at least five cycles
  are available;
- no singleton seasonal grouping.

The implementation passes only when the lower confidence bound is at least 80%
for random-walk/persistence recall and the upper confidence bound is below 10%
for the false-positive targets. Thresholds are tuned on the calibration set only,
then frozen before held-out synthetic and real-dataset evaluation.

## Configuration

Add configuration sections for:

```text
process_classification:
  min_spectrum_tail: 3
  power_law_slope_target: -2.0
  power_law_fit_min: 0.90
  eof_smoothness_max: 0.02
  differenced_concentration_max: 0.55
  monte_carlo_replicates: 199
  adf_alpha: 0.05
  kpss_alpha: 0.05

periodicity:
  candidate_periods_by_cadence:
    hourly: [24, 168]
    daily: [5, 7, 14]
    weekly: [4, 8]
    monthly: [12, 24]
    quarterly: [4, 8]
  max_period_error: 0.15
  min_complete_cycles: 5
  pair_similarity_tolerance: 0.20
  phase_quadrature_tolerance: 0.20
  min_period_strength: 0.30

process_compute:
  max_candidate_periods: 8
  max_windows_per_scope: 6
  max_monte_carlo_seconds: 30
  interactive_mode: fast

benchmark:
  evaluate_full_scope: true
  evaluate_active_scope: true
  max_period_error_fraction: 0.15
  expected_process_mismatch_is_failure: true
```

These values are proposed starting defaults for implementation review, not final
production thresholds. They must be supplied from YAML, range-validated at load
time, and finalized only by the held-out simulation protocol above.

Initial validation ranges:

| Setting | Accepted range |
|---|---|
| `min_spectrum_tail` | 2–8 |
| `power_law_slope_target` | −3.0 to −1.0 |
| `power_law_fit_min` | 0–1 |
| `eof_smoothness_max` | 0 to 1 |
| `differenced_concentration_max` | 0 to 1 |
| `monte_carlo_replicates` | 49–999, odd |
| `adf_alpha`, `kpss_alpha` | 0 to 0.2 |
| `max_period_error` | 0 to 0.5 |
| `min_complete_cycles` | 2–10 |
| tolerances/strengths | 0 to 1 |
| `max_candidate_periods` | 1–20 |
| `max_windows_per_scope` | 1–20 |
| `max_monte_carlo_seconds` | 1–300 |

If Monte Carlo exceeds the time budget, the classifier returns the fast
evidence-based status with `monte_carlo_percentile: null` and an explicit
`timeout` evidence flag. It must not silently fabricate confidence.

## Implementation sequence

1. Introduce diagnostic and result dataclasses without changing existing outputs.
2. Add level/difference eigen-spectrum and EOF diagnostics.
3. Add unit-root/stationarity evidence and stochastic-persistence classification.
4. Add Monte Carlo null calibration.
5. Replace one-window seasonality promotion with candidate-period verification.
6. Add multi-scope benchmark evaluation and explicit ground-truth assertions.
7. Stop DW-driven component promotion; retain DW as a diagnostic.
8. Update notebook/UI/KMDS schemas to expose the new authoritative outputs.
9. Only after tests pass, revise README, tutorials, example narratives, UI labels,
   plots, alerts, screenshots, and generated reports.

Compatibility details for the transition:

- `get_suitability_result()` gains `status`, `diagnostic_supported`, and reason
  metadata. Legacy `is_suitable` remains a boolean projection: true only for
  `status == suitable`.
- `suggest_grouping()` and `set_grouping()` raise the canonical stop message for
  pure stochastic persistence. They cannot be used to bypass Step 1.
- `generate_test_dataset_report()` and comprehensive tests evaluate the
  authoritative semantic result, then render legacy columns for compatibility.
- A versioned schema field is required for exported diagnostics and KMDS records
  so older records remain interpretable.
- The legacy methods are deprecated only after one release with both old and new
  fields available.

## Review checklist

- No stochastic-persistence series is shown as deterministic seasonality.
- No seasonal group contains one component.
- Short windows produce `indeterminate`, not false confidence.
- Full-series and active-regime conclusions are visible and cannot be confused.
- Every accepted period includes period, cycle count, pair, and confidence.
- Durbin-Watson cannot alter semantic process classification.
- Residual variance testing uses the process-appropriate residual series.
- Every threshold is configured and every result records the evidence that drove it.
- Active-regime boundaries can be reproduced without UI global state.
- Missing-value and regularization policy is explicit for every benchmark.
- Long/quasi-periodic candidates record fitted period and accepted band.
- Monte Carlo thresholds are evaluated on held-out synthetic data.

## Review disposition

Review completed on 25 November 2026. The initial review identified ambiguous
active-regime selection, missing-data handling, persistence reconstruction,
quasi-periodic period/window rules, and simulation acceptance criteria. The
specification now defines each explicitly. Proceed to implementation in the
sequence above; no runtime or user-visible behavior is authorized by this
document alone.
