# Process Classification Reference

## What the classifier is deciding

The process classifier is the first analytical output produced by `tseda`,
before deterministic SSA grouping. It asks a practical question:

> Which interpretation of the observed process is most defensible from the
> available evidence?

The classifier does not claim to discover one uniquely true model, predict the
future, or turn every visible pattern into a deterministic component. It
separates interpretations that need different downstream treatment:

- diffuse noise;
- stochastic persistence;
- deterministic low-frequency movement;
- verified periodic behavior;
- stationary but irregular behavior;
- evidence that cannot yet distinguish those possibilities.

This evidence-first distinction matters because a smooth curve is not
automatically a deterministic trend, and a repeating-looking pattern is not
automatically seasonality. A candidate pattern must survive the applicable
identifiability, persistence, and periodic-verification checks.

The classifier produces an independent result for each available scope:

- `full_series`: behavior across the complete loaded series;
- `active_regime`: behavior in the selected current or final regime.

The classification is the first actionable outcome. It determines whether to
stop, request more evidence, or proceed to SSA window selection, periodic-pair
verification, grouping, and residual diagnostics.

## A conceptual decision path

The labels can be understood as an ordered set of evidence questions:

1. **Is variation broadly distributed without stable leading structure?**
   Classify it as `diffuse_noise`; do not force trend or seasonality.
2. **Does the level series show persistence while its first differences look
   more like diffuse innovations?**
   Classify it as `stochastic_persistence`; use stochastic, differenced, or
   state-space methods rather than treating smooth level motion as a
   deterministic trend.
3. **Is low-frequency movement supported as deterministic after persistence
   alternatives have been considered?**
   Classify it as `deterministic_trend`.
4. **Is a cadence-appropriate period verified by a supported SSA pair and
   enough complete cycles?**
   Classify it as `periodic`, or as `mixed` when independently verified
   periodic behavior coexists with persistent or deterministic level behavior.
5. **Is the series stationary or finite-memory irregular without supported
   deterministic trend or periodicity?**
   Classify it as `stationary_irregular`.
6. **Are the tests contradictory, unavailable, or too weak because the
   selected scope lacks enough evidence?**
   Classify it as `indeterminate`.

These questions are diagnostic rather than a claim that a process has one
universal identity. A label summarizes the interpretation supported for the
reported scope and configuration.

## Requirements, heuristics, and reproducibility

Every classifier tag has explicit operational requirements. `tseda` does not
assign a label because a plot merely "looks" noisy, trending, or periodic. It
evaluates configured, numerical gates and records the result together with
diagnostic evidence.

The decision logic has two different kinds of elements:

- **identifiability requirements**, which prevent unsupported conclusions; for
  example, periodicity requires a valid SSA pair, enough complete cycles, an
  acceptable period error, and sufficient reconstructed spectral strength;
- **heuristic decision thresholds**, which determine when accumulated evidence
  is strong enough for practical use; for example, the minimum top-five SSA
  share, maximum eigenpair difference, or required persistence-score support.

The heuristics are grounded in established time-series and SSA concepts:
variance concentration, paired oscillatory modes, spectral localization,
stationarity and unit-root diagnostics, first-difference behavior, and cycle
support. A threshold is nevertheless a modeling choice, not a universal
physical constant. `tseda` therefore exposes the important choices in
configuration instead of concealing them in code.

This distinction is important for review: the classifier is reproducible and
rule-based, while its defaults are defensible operating choices that can be
questioned and sensitivity-tested. A reviewer should be able to inspect a
reported tag, recover the evidence values, inspect the configured thresholds,
and reproduce why that tag was selected. For publication, users should report
the relevant configuration values and, where material, repeat the analysis
under reasonable alternative thresholds.

## What "stable deterministic structure" means operationally

The phrase refers primarily to **concentration in the Singular Spectrum
Analysis (SSA) eigenspectrum**, not to whether the series looks smooth or to a
Fourier spectrum alone.

SSA forms a trajectory matrix from overlapping lagged windows of the selected
series and decomposes that matrix into ordered eigenmodes. `tseda` normalizes
the eigenvalues by their total:

\[
\text{mode share}_i =
\frac{\lambda_i}{\sum_j \lambda_j}
\]

It then computes how much of that total is represented by the first five
modes:

\[
\text{top-k ratio} =
\sum_{i=1}^{5}
\frac{\lambda_i}{\sum_j \lambda_j}
\]

The configured interpretation is:

| SSA eigenspectrum | Interpretation at this gate |
|---|---|
| Top-five share is at least 40% | Enough concentration to investigate a structured interpretation further. |
| Top-five share is below 40% | `diffuse_noise`: spectral mass is spread across too many modes to support a small deterministic SSA reconstruction. |

Concentrated SSA modes are only the first gate. A concentration can also be
caused by stochastic persistence, so `tseda` separately examines:

- the decay of the level-series eigenvalues;
- the smoothness of the leading empirical orthogonal function (EOF);
- whether concentration disappears or falls substantially after first
  differencing;
- ADF and KPSS stationarity evidence;
- candidate periodic behavior.

For periodic behavior, `tseda` additionally uses the Fourier power spectrum.
It detrends the series, identifies a frequency whose period has enough complete
cycles, and measures the fraction of eligible Fourier power near that candidate.
That localized Fourier evidence is not accepted by itself: the candidate must
also produce a supported SSA eigenvalue pair whose reconstructed signal has the
expected period and enough spectral strength.

Thus, the two kinds of spectrum answer different questions:

| Spectrum | What it measures in `tseda` | Current role |
|---|---|---|
| SSA eigenspectrum | Concentration of trajectory-matrix variance into a small number of ordered modes. | Primary broad-structure/noise gate and persistence diagnostics. |
| Fourier power spectrum | Localization of oscillatory power at a frequency or candidate period. | Supporting evidence for periodic candidates; paired with SSA reconstruction checks. |

In this context, “broadly distributed” means that no small set of SSA modes
captures the configured minimum share of trajectory-matrix variance. It does
not mean that the Fourier power must be perfectly flat, nor does
`diffuse_noise` prove statistical independence. A threshold classification is
an operational decision about whether SSA decomposition is informative, not a
complete probabilistic characterization of the series.

## Operational requirements for each tag

The requirements below describe the current classifier at a conceptual level;
the exact configuration keys and values are listed in the following section.

| Tag | Current operational requirement |
|---|---|
| `diffuse_noise` | The normalized share explained by the configured leading SSA modes is below the minimum concentration threshold. This gate is evaluated first. |
| `stochastic_persistence` | The eigenspectrum is sufficiently concentrated, at least five of the six persistence indicators are supported, and no verified periodic component produces a `mixed` result. Indicators cover leading-mode concentration, power-law-like eigenvalue decay, smooth leading EOF behavior, low concentration after differencing, ADF-level/difference behavior, and KPSS evidence. |
| `deterministic_trend` | Persistence does not provide a supported final interpretation; periodic alternatives are absent; and both level/trend ADF checks support stationarity around a deterministic trend at the configured significance level. This rule may replace an initial `indeterminate` or persistence label when the deterministic-trend evidence is decisive. |
| `periodic` | At least one candidate survives the SSA-pair and periodic-reconstruction checks, while persistence is not supported strongly enough to require `mixed`. A periodic candidate needs sufficient complete cycles, a sufficiently similar eigenvalue pair, a reconstructed period within the permitted error band, and configured spectral strength. |
| `mixed` | A verified periodic component and supported stochastic persistence are present in the same scope. |
| `stationary_irregular` | The concentration gate is passed, but no verified periodic component or supported persistence model is selected; the level ADF test supports stationarity at the configured significance level. |
| `indeterminate` | No other rule provides a defensible classification—for example, because evidence is contradictory, diagnostics are unavailable, or periodic/local-regime evidence is insufficient. The suitability status also remains indeterminate rather than presenting a forced decomposition. |

The requirements are ordered, not independent. In particular, a strong
leading-eigenvalue concentration does not by itself select deterministic trend
or seasonality. The classifier must distinguish that concentration from
stochastic persistence and, for periodicity, verify a real oscillatory pair
rather than accepting a single smooth or concentrated mode.

## Classification table

| Category | What it means | Typical evidence | Suggested processing | Deterministic SSA status |
|---|---|---|---|---|
| `diffuse_noise` | The SSA eigenspectrum does not contain a sufficiently concentrated group of leading modes. | The leading five SSA eigenvalues explain less than 40% of total SSA spectrum mass. This is a broad-spectrum gate; it is not a claim that every observation is statistically independent. | Use a white-noise, IID, ARMA, distributional, count, anomaly, or domain-specific model. | **Stop.** Do not force Trend or Seasonality. |
| `stochastic_persistence` | The level series behaves like a random walk, persistent AR process, or another stochastic trend. | Smooth concentrated level spectrum; high autocorrelation; diffuse first differences; unit-root/stationarity evidence; compatibility with persistence nulls. | Investigate random-walk, ARIMA/differenced, local-level/state-space, or persistent AR methods. Analyze innovations or residuals separately if later supplied as a new series. | **Stop for the level series.** Visual smoothing can create pareidolia and is not deterministic trend evidence. |
| `deterministic_trend` | A finite low-frequency movement is better supported as deterministic trend than stochastic persistence. | Smooth but finite drift supported after persistence tests; no conflicting unit-root classification. | Model or reconstruct the deterministic trend, then inspect residuals for verified periodic or irregular structure. | **Proceed**, when identifiability and residual-tail requirements pass. |
| `periodic` | One or more cadence-appropriate oscillatory SSA pairs are independently verified. | Sufficient cycles; near-equal eigenpair; reconstructed period in its accepted band; independent spectral support. | Proceed with the verified periodic component or components, treating trend and residual separately. | **Proceed** with complete verified pair(s); singleton seasonality is prohibited. |
| `mixed` | Verified periodic structure coexists with deterministic trend and/or stochastic persistence. | A verified periodic pair plus deterministic or persistent low-frequency evidence. | Separate the verified periodic evidence from the appropriate deterministic or stochastic level treatment. | **Conditional proceed.** Only verified deterministic/periodic components enter decomposition. |
| `stationary_irregular` | Finite-memory or irregular variation exists, but a stable deterministic trend or cadence period is not supported. | Weak or moderate concentration; limited persistence; finite autocorrelation; no verified periodic pair. | Consider stationary ARMA, regression, intervention, count, anomaly, or domain-specific behavior; inspect separately supported structure. | **Usually stop or remain diagnostic.** Do not force a trend or seasonality label. |
| `indeterminate` | Available evidence cannot distinguish valid alternatives, or the scope lacks enough data or cycles. | Short active regime; gaps; contradictory stationarity tests; unstable window/period evidence; unavailable diagnostics. | Expand history, select another regime, collect more cycles, or provide an explicitly regularized series. Retain any supported full-series result separately. | **Do not proceed automatically.** Resolve the stated evidence gap first. |

## Where the rules are configured

The authoritative defaults are centralized in
[`src/tseda/config/tseda_config.yaml`](../src/tseda/config/tseda_config.yaml)
and accessed through the package configuration loader. This allows an informed
user to inspect the exact value used by a rule and change the configuration
before running an analysis whose research or domain requirements call for a
different tolerance.

| Configuration area | Examples of controlled choices |
|---|---|
| `suitability_check` | Number of leading SSA modes considered; minimum explained share used by the diffuse-spectrum gate. |
| `process_classification` | Power-law decay target and fit quality; EOF smoothness; differenced concentration; ADF and KPSS significance levels; Monte Carlo budgets. |
| `process_periodicity` | Candidate periods by cadence; minimum complete cycles; eigenpair similarity; allowed period error; minimum reconstructed/candidate spectral strength. |
| `process_compute` | Maximum candidate periods considered and interactive Monte Carlo mode. |
| `segmentation` | Minimum active-regime length, half-life, and lookback weight threshold. |

These entries identify active rules rather than every key present in the YAML
file. For example, a key reserved for a future phase-quadrature or compute-time
guard should not be represented as an enforced current check until the
classifier consumes it. Before changing a setting, verify that the corresponding
rule reads that key; the active mappings are visible in
[`process_diagnostics.py`](../src/tseda/decomposition/process_diagnostics.py) and
[`pelt_segmentation.py`](../src/tseda/segmentation/pelt_segmentation.py).

Configuration changes should be deliberate and documented. Relaxing one
threshold may increase classification coverage while decreasing specificity;
tightening it may protect against false structure while increasing
`indeterminate` results. Suitable review practice is to:

1. record the configuration used for the analysis;
2. state any departures from package defaults and their domain rationale;
3. rerun the same input after changing the YAML setting;
4. compare classification, suitability, verified periods, and component
   results;
5. report threshold sensitivity for conclusions that materially affect the
   study.

The benchmark report and acceptance tests provide reproducibility checks for
the bundled defaults, but they do not make a default universally optimal for
every domain. Configuration is the intended mechanism for adapting
defensibility criteria without changing the classifier's rule structure.

## Scope comes first

Always read a process label together with its scope. A full-series result and
an active-regime result can legitimately differ:

- the full series may contain enough repetitions to verify long-period
  behavior;
- the current regime may be too short to confirm that behavior independently;
- recent behavior may differ structurally from earlier history;
- a transition between regimes can mix characteristics when a short tail is
  expanded backward.

An `indeterminate` active-regime result does not invalidate a supported
full-series result. Likewise, a supported full-series period does not prove that
the same period remains active in the current regime.

## What the half-life lookback does—and does not do

When a final regime is below the configured minimum analysis length, the
half-life lookback expands the working window backward into the preceding
regime. This prevents a tiny terminal segment from producing an obviously
unstable SSA computation.

It can help:

- stabilize the numerical window;
- provide enough observations for a low-frequency estimate;
- retain the most recent observations as the analytical anchor.

It cannot:

- create new observations;
- create additional complete repetitions of a seasonal cycle;
- guarantee that earlier and recent regimes represent the same process;
- resolve contradictory persistence diagnostics;
- turn a visually suggestive curve into a verified periodic component.

The current implementation uses the exponential weights to choose the lookback
boundary. It then analyzes the selected observations as a normal series rather
than applying those weights as per-observation SSA weights.

The distinction can be summarized as:

| Question | Mechanism |
|---|---|
| Is the final working window too small for stable computation? | Half-life lookback |
| Is a candidate period supported by enough complete cycles? | Periodic evidence and cycle-count checks |
| Can valid process alternatives be separated? | Process diagnostics and classification |

A lookback window can therefore be computationally adequate while periodic
classification remains `indeterminate`.

## Understanding `indeterminate`

`indeterminate` means:

> The available evidence for this scope cannot distinguish the valid
> alternatives with sufficient confidence.

It does **not** mean:

- no structure exists;
- the series is white noise;
- the full-series classification is wrong;
- every component must be discarded.

Possible reasons include:

| Cause | What remains unresolved | Typical next action |
|---|---|---|
| Insufficient complete cycles | A period may be plausible, but the scope does not contain enough repetitions to verify it independently. | Expand the history or wait for more cycles. |
| Regime uncertainty | Lookback crosses a boundary and mixes behavior from different regimes. | Inspect neighboring scopes or select a different regime. |
| Contradictory diagnostics | Persistence, stationarity, and deterministic-trend evidence disagree. | Compare differenced behavior and use a stochastic/persistence analysis where appropriate. |
| Insufficient usable span | Gaps or a short preceding regime leave no qualifying contiguous run. | Supply a documented preprocessing choice or collect more data. |
| Unstable period evidence | A spectral peak does not yield a valid SSA pair or reconstruct the candidate period consistently. | Do not name seasonality; seek an independently supported period or more history. |
| Unavailable diagnostics | A required diagnostic cannot be computed or is not defensible. | Resolve the stated data or diagnostic problem. |

The evidence note and suitability reason should be read together with the
label. They identify which condition prevented a more specific conclusion.

## Worked example: periodicity in monthly car sales

The [car-sales example](car_sales_example.md) illustrates a common
`indeterminate` result:

- the full 108-observation monthly series is classified as `periodic`;
- the verified full-series period is 12 months;
- the final active regime contains 24 observations;
- it therefore contains only \(24 / 12 = 2\) complete annual cycles.

With a default requirement of five complete cycles for normal periodic
confirmation, two repetitions are not enough to verify annual seasonality
independently in the active regime. The active result is therefore
`indeterminate`.

This does not say that the annual pattern disappeared. It says:

> The full history supports a 12-month period, but the current regime does not
> contain enough independent repetitions to reconfirm it.

For monthly data, the cadence minimum is 12 observations, so this 24-point
active regime does not need half-life lookback. If a shorter tail did trigger
lookback, a longer computational window could help estimate trend, but it would
not create five clean annual repetitions within one homogeneous active regime.

## Contrasting example: quarterly US consumption

The quarterly US consumption benchmark illustrates a different kind of
indeterminate result:

- the full series is classified as `stationary_irregular`;
- the active regime is classified as `indeterminate`;
- no periodic component is verified.

Here, `indeterminate` should not automatically be summarized as “missing
periodic cycles.” The active scope does not provide enough decisive evidence to
reproduce the full-series classification or select a different stable process
class. The classification is therefore incomplete for the local scope even
though periodicity has not been established.

This example shows why the overall evidence reason matters: insufficient cycle
count is a common explanation for active-regime `indeterminate`, but it is not
the only one.

## How to interpret a result

Read the result together with:

- the analysis scope;
- `confidence`, when calibration is available;
- decomposition suitability status and reason;
- verified periods and complete-cycle counts;
- full-series versus active-regime differences;
- whether half-life lookback crossed a regime boundary;
- Monte Carlo compatibility, when requested;
- residual and variance-change diagnostics.

Process classification and decomposition suitability answer different
questions:

- **Process classification:** What behavior is best supported by the available
  evidence?
- **Decomposition suitability:** May `tseda` defensibly proceed with a
  deterministic SSA reconstruction?

For example:

- `periodic` can be suitable for verified SSA reconstruction;
- `stochastic_persistence` can be classified reliably but unsuitable for a
  deterministic level-series decomposition;
- `indeterminate` active-regime evidence can coexist with a supported
  full-series result.

## Common follow-up actions

| Result | Typical next step |
|---|---|
| `diffuse_noise` | Stop deterministic SSA; choose a stochastic/noise model. |
| `stochastic_persistence` | Stop level SSA; use differencing or a stochastic-trend model. |
| `deterministic_trend` | Proceed with trend reconstruction and residual validation. |
| `periodic` | Proceed with verified seasonal pair(s) and residual validation. |
| `mixed` | Separate verified periodic evidence from the appropriate persistent/deterministic level model. |
| `stationary_irregular` | Investigate finite-memory/domain behavior before reconstruction. |
| `indeterminate` | Obtain more history or cycles, resolve regime/gap questions, or inspect the unavailable or contradictory diagnostic. |

## New-user interpretation checklist

When explaining a process classification:

1. State whether the label applies to the full series or the active regime.
2. Check whether a short final segment used half-life lookback.
3. Distinguish a stable computational window from sufficient identification
   evidence.
4. For a proposed period, calculate the available complete-cycle count.
5. Read `indeterminate` as “evidence is insufficient or contradictory,” not
   “no structure exists.”
6. Retain supported full-series findings when the active-regime result is
   indeterminate.
7. Read process classification separately from decomposition suitability.
8. Use the stated next action rather than forcing a Trend or Seasonality label.

## Residual handoff

For `stochastic_persistence` or `diffuse_noise`, an external model may produce
residuals or innovations. Such a residual is not recursively analyzed inside
the same run. If a user supplies it as a new series, it starts a separate
analysis with new cadence, scope, suitability, and classification results.

For the complete ordered procedure, see
[`decomposition_process_spec.md`](decomposition_process_spec.md).
