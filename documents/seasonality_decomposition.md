# Seasonality Decomposition and Verification

## Scope

`tseda` does not treat a smooth component, a large eigenvalue, or a single Fourier
peak as seasonality. A seasonal component is accepted only when the analysis
scope contains enough repeated cycles and the SSA evidence identifies an
oscillatory pair at a defensible cadence-specific period.

This document describes the seasonal stage after the series has passed the
process-suitability gates in
[`decomposition_process_spec.md`](decomposition_process_spec.md).

## Required inputs

- an identifiable full-series or active-regime scope;
- inferred sampling cadence;
- candidate period or period band;
- enough observations for the configured minimum complete cycles;
- an SSA window that covers the candidate period and retains a residual tail.

If these conditions are not met, the seasonal result is `indeterminate`. It is
not represented by a singleton component or inferred from smoothing.

## Candidate periods

Candidate periods come from cadence-aware configuration and optional
domain-specific overrides:

| Cadence | Typical candidates |
|---|---|
| Hourly | 24 and 168 observations |
| Daily | 7, plus 5 for explicitly business-day data |
| Weekly | 4 or 8 observations |
| Monthly | 12, 24, or a configured long period |
| Quarterly | 4 or 8 observations |

For a candidate period \(P\), the initial SSA window is \(L=P\). Where supported,
\(L=2P\) can be evaluated as a robustness check. Long cycles may be represented as
a period band rather than one exact integer.

## Sequential verification

A periodic SSA component is accepted only after all required gates pass.

### 1. Cycle support

The scope must contain the configured minimum number of complete cycles. A
strong-looking peak in a short final segment is not enough.

### 2. SSA eigenpair

Two adjacent eigenvalues must be sufficiently close. This identifies a potential
oscillatory pair rather than a single monotonic mode.

### 3. Oscillatory behavior

The paired eigenvectors or reconstructed pair must support phase-shifted
oscillation. Singleton modes and two smooth monotonic modes are rejected.

### 4. Reconstructed period

The reconstructed pair is tested for a dominant period inside the accepted band
around the candidate. The fitted period, band, confidence, pair indices, and
cycle count are retained.

### 5. Independent spectral support

The detrended or residual spectrum must concentrate meaningful power at the
candidate period. This check is independent of the adjacent-eigenvalue
similarity test.

### 6. Persistence safeguard

The result is rejected as deterministic seasonality if the level series is better
explained by stochastic persistence. Pure random walks can have smooth,
concentrated spectra, so their level modes are not seasonal evidence.

### 7. Robustness

When feasible, the period is checked at multiple valid windows or across
qualifying contiguous runs. Results are marked indeterminate if the conclusion
changes materially.

## Reconstruction and output

An accepted pair is assigned to `Seasonality` as a complete pair. The output
records:

- fitted period and accepted band;
- candidate period and SSA window;
- eigenvalue pair;
- available cycle count;
- reconstructed spectral strength;
- confidence;
- full-series or active-regime scope.

No singleton component is allowed in `Seasonality`.

## Residual diagnostics

After seasonal reconstruction, `tseda` reports:

- residual variance;
- spectral and observation-scale variance attribution;
- Durbin-Watson as a diagnostic, not a grouping objective;
- ACF/PACF and KDE diagnostics;
- trend, seasonal-amplitude, seasonal-phase, and residual-variance change points.

## Relation to window selection

Window selection is not itself proof of seasonality. It provides valid SSA
embeddings in which periodic pairs can be tested. See
[`../window_selection_algorithm.md`](../window_selection_algorithm.md) for the
window-selection method.
