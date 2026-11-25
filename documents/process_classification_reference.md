# Process Classification Reference

## First tangible output

Before deterministic SSA grouping, `tseda` assigns one process classification to
each analysis scope:

- `full_series`: behavior across the complete loaded series;
- `active_regime`: behavior in the selected current/final regime.

The classification is the first actionable outcome. It determines whether the
package should stop, request more evidence, or proceed to SSA window selection,
periodic-pair verification, grouping, and residual diagnostics.

## Classification table

| Category | What it means | Typical evidence | Suggested processing | Deterministic SSA status |
|---|---|---|---|---|
| `diffuse_noise` | No stable deterministic structure stands above a broadly distributed noise spectrum. | Low leading-spectrum concentration; jagged EOFs; no supported period. | Use a white-noise, IID, ARMA, distributional, count, anomaly, or domain-specific model. | **Stop.** Do not force Trend or Seasonality. |
| `stochastic_persistence` | The level series behaves like a random walk, persistent AR process, or another stochastic trend. | Smooth concentrated level spectrum, high autocorrelation, diffuse first differences, unit-root/stationarity evidence, compatibility with persistence nulls. | Investigate random-walk, ARIMA/differenced, local-level/state-space, or persistent AR methods. Analyze innovations or residuals separately if later supplied as a new series. | **Stop for the level series.** Visual smoothing can create pareidolia and is not deterministic trend evidence. |
| `deterministic_trend` | A finite low-frequency movement is better supported as deterministic trend than stochastic persistence. | Smooth but finite drift supported after persistence tests; no conflicting unit-root classification. | Model or reconstruct the deterministic trend, then inspect residuals for verified periodic or irregular structure. | **Proceed**, when identifiability and residual-tail requirements pass. |
| `periodic` | One or more cadence-appropriate oscillatory SSA pairs are independently verified. | Sufficient cycles, near-equal eigenpair, phase-quadrature behavior, reconstructed period in its accepted band, independent spectral support. | Proceed with the verified periodic component(s), treating the trend and residual separately. | **Proceed** with complete verified pair(s); singleton seasonality is prohibited. |
| `mixed` | Verified periodic structure coexists with deterministic trend and/or stochastic persistence. | A verified periodic pair plus deterministic or persistent low-frequency evidence. | Treat the stochastic level with stochastic/differenced methods where required and retain independently verified periodic components in the combined interpretation. | **Conditional proceed.** Only verified deterministic/periodic components enter decomposition. |
| `stationary_irregular` | Finite-memory or irregular variation exists, but a stable deterministic trend or cadence period is not supported. | Weak or moderate concentration, limited persistence, finite autocorrelation, no verified periodic pair. | Consider stationary ARMA, regression, intervention, count, or anomaly models; inspect residuals for separately supported structure. | **Usually stop or remain diagnostic.** Do not force a trend or seasonality label. |
| `indeterminate` | Available evidence cannot distinguish valid alternatives, or the scope lacks enough data/cycles. | Short active regime, gaps, contradictory stationarity tests, unstable window/period evidence, or unavailable diagnostics. | Expand history, select another regime, collect more cycles, or provide an explicitly regularized series. Retain any supported full-series result separately. | **Do not proceed automatically.** Resolve the stated evidence gap first. |

## How to interpret the result

The classification does not by itself claim that one model is uniquely true. It
describes which interpretation is most defensible under the configured SSA and
diagnostic evidence.

Read the result together with:

- `confidence`, when calibration is available;
- decomposition suitability status and reason;
- verified periods and cycle counts;
- full-series versus active-regime differences;
- Monte Carlo compatibility, when requested;
- residual and variance-change diagnostics.

## Common follow-up actions

| Result | Typical next step |
|---|---|
| `diffuse_noise` | Stop deterministic SSA; choose a stochastic/noise model. |
| `stochastic_persistence` | Stop level SSA; use differencing or a stochastic-trend model. |
| `deterministic_trend` | Proceed with trend reconstruction and residual validation. |
| `periodic` | Proceed with verified seasonal pair(s) and residual validation. |
| `mixed` | Separate the verified periodic evidence from the persistent/deterministic level model. |
| `stationary_irregular` | Investigate finite-memory/domain behavior before reconstruction. |
| `indeterminate` | Obtain more history, cycles, or explicit preprocessing. |

## Residual handoff

For `stochastic_persistence` or `diffuse_noise`, an external model may produce
residuals or innovations. Such a residual is not recursively analyzed inside the
same run. If the user supplies it as a new series, it starts a separate analysis
with new cadence, scope, suitability, and classification results.

For the complete ordered procedure, see
[`decomposition_process_spec.md`](decomposition_process_spec.md).
