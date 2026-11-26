# Phase 2, Item 4: `tseda` Synthetic Classifier Study

## Purpose

This study evaluates the blind-spot profile of `tseda`'s exploratory
classifier. It does not ask which decomposition library best fits a supplied
component model. That question belongs to Item 3's separate cross-method
validation in
[comparison_validation_similar_methods.md](comparison_validation_similar_methods.md).

The two studies form a combined classifier-validation profile:

- [Synthetic process-identification studies](synthetic_data_studies.md) test
  what `tseda` does against known DGPs, including AR persistence, local
  periodicity, and variance shifts.
- [Cross-method validation](comparison_validation_similar_methods.md) checks
  whether accepted real-data reconstructions are broadly consistent with
  established decomposition methods once the alternatives receive the required
  period information.

Together, they distinguish classifier strengths and blind spots from secondary
differences in reconstruction fit.

The questions here are:

1. What kind of process generated the series?
2. What should `tseda` identify before or during decomposition?
3. What did it actually identify?
4. What blind spot does a mismatch expose, and when should an analyst request
   secondary validation?

The study uses 200 replications per design cell, sample lengths
\(N \in \{60,150,400\}\), and, for signal-bearing DGPs,
\(SNR \in \{2,5,10\}\). It contains 6,000 unique DGP cells.

> [!IMPORTANT]
> **This is a study of `tseda`'s classifier, not a competition between
> smoothers.** Every DGP enters the tool without a supplied trend, period,
> component count, or expected change point. The important result is the
> process diagnosis and its limitations. Component RMSE is supporting evidence
> only.

> [!IMPORTANT]
> **Insufficient, noisy, or irregular local evidence drives many of the
> difficult cases, but “longer is always better” is not verified.** A periodic
> claim needs enough repetitions, and a regime or variance diagnosis needs
> enough observations on both sides of a boundary. These are fundamental
> identifiability constraints for nearly any decomposition or classification
> method, so secondary or domain-informed validation is advisable when the
> relevant evidence is short or unstable.
>
> The simulation also exposes two qualifications. AR(1) `Trend` ambiguity
> becomes **more** frequent as total \(N\) increases because persistence is
> estimated more confidently. The terminal-cycle result becomes worse as a
> longer full-series history increasingly dilutes the local 35% regime.
> Therefore, the important quantity is not total sample length alone; it is the
> amount and stability of evidence supporting the particular process claim.

## What `tseda` is expected to do

For each replication, the evaluation records:

- **Suitability:** whether deterministic decomposition is considered
  defensible.
- **Process evidence:** whether periodicity is verified.
- **Grouping:** whether the reconstruction assigns components to trend and/or
  seasonality.
- **Residual quality:** whether Durbin-Watson is in `[1.5, 2.5]`.
- **Change detection:** whether variance-change evidence is found where one
  exists, and whether it is absent where one does not.

Grouping and process evidence are deliberately reported separately. A
component named `Trend` is not automatically proof of a deterministic trend.
Likewise, rejecting a full-series decomposition can be a useful result when
the interesting behavior is regime-specific.

### How to interpret Durbin-Watson

Durbin-Watson (DW) is a conditional residual diagnostic, not a classifier
accuracy score. It is reported only when `tseda` accepts a series and produces a
reconstruction. A DW outside `[1.5, 2.5]` means that the accepted residual
retains serial dependence; it does not alone prove the process classification
wrong. Conversely, DW near 2 can coexist with a wrong semantic label.

Noise level changes the meaning and sensitivity of the statistic:

- At low SNR, the residual is dominated by comparatively large white-noise
  variation, making DW close to 2 if the decomposition separates the signal.
- At high SNR, the true noise is small. Even modest deterministic leakage can
  dominate that residual and move DW away from 2.
- Rejected series have no accepted reconstruction residual. DW is therefore
  unavailable for them rather than being calculated from the raw series.
- Values near the boundaries are diagnostics, not pass/fail proof of
  decomposition truth.

DW should identify possible under-reconstruction after a process claim is made,
not replace suitability, period verification, or correct process labeling.

## 1. Stationary AR(1) persistence

### Generating process

\[
x_t=0.8x_{t-1}+\epsilon_t,\qquad \epsilon_t\sim N(0,1)
\]

The initial value is drawn from the stationary distribution. There is no
deterministic trend and no seasonal term. Because \(|0.8|<1\), the process has
zero mean, constant variance, and autocorrelation \(0.8^k\).

Individual realizations can nevertheless appear locally trend-like because
successive observations are strongly correlated. That is **stochastic
persistence**, not a deterministic trend.

### Desired diagnosis

`tseda` should identify persistent red noise or otherwise refuse a deterministic
decomposition. It should not claim deterministic trend or a recurring seasonal
cycle. A meaningful exploratory result is “persistent/stochastic,”
“indeterminate,” or “not suitable,” rather than a fabricated trend/seasonality
story.

### Observed behavior

| N | Suitable | Group labeled Trend | Group labeled Seasonality | Verified period | DW convergence |
|---:|---:|---:|---:|---:|---:|
| 60 | 55.0% | 50.0% | 14.5% | 14.5% | 90.9% |
| 150 | 96.0% | 93.5% | 24.0% | 24.0% | 97.4% |
| 400 | 99.0% | 99.0% | 28.5% | 29.5% | 93.4% |

Across the complete AR(1) design:

- suitability passed in 83.3% of replications;
- a reconstruction `Trend` group appeared in 80.8%;
- a `Seasonality` group appeared in 22.3%;
- a period was verified in 22.7%.

### Classifier blind spot

The suitability gate often accepts persistent stationary noise, and the
grouping stage then labels its low-frequency autocorrelation as `Trend`.
This rate grows with sample length, not because the DGP acquires a trend, but
because longer realizations provide stronger estimates of persistent
low-frequency structure.

This is the report's clearest semantic blind spot:

> The current `Trend` reconstruction label does not reliably distinguish a
> deterministic trend from stochastic persistence.

The high conditional DW rates do not validate these semantic labels. A
reconstruction can separate persistence well enough to leave a white-noise
residual while still calling the captured stochastic component `Trend`.

Seasonal false positives are lower than trend false positives, but the
approximately 23% rate remains material.

### Analyst response

For a strongly persistent series, inspect:

- differenced-series behavior;
- ADF/KPSS evidence;
- random-walk or stochastic-persistence warnings;
- whether a low-frequency reconstruction component survives differencing.

Treat the `Trend` label as an initial descriptive label, not a claim that a
deterministic trend has been established. Secondary process validation is
recommended.

## 2. Nonlinear trend plus stable seasonality

### Generating process

\[
y_t=T(t)+3\sin(2\pi t/7)+\epsilon_t
\]

where \(T(t)\) is a smooth deterministic logistic curve and noise is scaled to
the requested SNR.

The series therefore has:

- deterministic low-frequency trend;
- a stable seven-observation periodic component;
- additive noise.

### Desired diagnosis

`tseda` should:

- accept the series as suitable;
- verify a period near 7;
- recover a seasonal component;
- retain enough low-frequency structure to represent the nonlinear trend;
- produce residual behavior consistent with the remaining noise.

### Observed behavior

| N | Suitable | Group labeled Trend | Group labeled Seasonality | Verified period | DW convergence |
|---:|---:|---:|---:|---:|---:|
| 60 | 100.0% | 29.5% | 99.8% | 100.0% | 60.0% |
| 150 | 100.0% | 18.8% | 100.0% | 100.0% | 64.5% |
| 400 | 100.0% | 14.0% | 100.0% | 100.0% | 64.5% |

Across all lengths and SNRs:

- suitability: 100.0%;
- verified period near 7: 100.0%;
- seasonal grouping: 99.9%;
- trend grouping: 20.8%;
- conditional DW convergence: 63.0%;
- mean seasonal RMSE: 0.195;
- mean trend RMSE: 0.239.

### Classifier strength

Periodic-process identification is the strongest result in the study.
`tseda` finds the seven-point cycle in every replication without being supplied
the period, and the seasonal reconstruction is consistently supported.

### Classifier blind spot

The weakness is separation of trend from seasonality. Although suitability and
period verification are almost perfect, only 20.8% of reconstructions retain a
group explicitly named `Trend`. The seasonal pair dominates the grouping, and
low-frequency trend structure may be distributed among other components or
insufficiently emphasized.

The low-frequency DGP is therefore recovered numerically more often than its
semantic `Trend` label suggests. This is a labeling/grouping gap, not a failure
to recognize the periodic process.

Residual DW convergence is also moderate rather than universal. A verified
period should not be interpreted as complete residual adequacy.

It is strongly SNR-dependent: convergence is 89%–100% at SNR 2, 67.5%–73.5%
at SNR 5, and 20.5%–23.5% at SNR 10. Period verification remains 100% at every
SNR. The high-SNR decline therefore does not indicate loss of periodic
classification. It shows that a small residual makes minor deterministic
leakage proportionally more visible. This is a reconstruction-resolution warning
for high-SNR data, not evidence that the identified process vanished.

## 3. Short terminal seasonal regime

### Generating process

The nonlinear trend exists throughout the series. A period-four cycle begins
only at 65% of the sample:

\[
S_t =
\begin{cases}
0, & t < 0.65N,\\
3\sin(2\pi t/4), & t \ge 0.65N.
\end{cases}
\]

This simulates a current operational regime whose behavior differs from older
history.

### Desired diagnosis

`tseda` should recognize that the full history is not one stable periodic
process, identify or isolate the terminal regime, and verify the local
period-four cycle without forcing it onto earlier observations.

A full-series rejection can be cautious and appropriate only if the workflow
continues by directing analysis toward a recent regime. A rejection without
regime-local follow-through is an incomplete exploratory result.

### Observed behavior

| N | Suitable for full series | Group labeled Trend | Group labeled Seasonality | Any verified period | DW convergence |
|---:|---:|---:|---:|---:|---:|
| 60 | 20.7% | 20.7% | 2.3% | 20.2% | 84.1%–100.0% |
| 150 | 13.3% | 13.3% | 11.5% | 12.3% | 88.9%–95.5% |
| 400 | 0.3% | 0.3% | 0.0% | 0.3% | 100.0% in the sole SNR cell with an accepted fit |

Across all cells:

- only 11.4% passed full-series suitability;
- 4.6% received a seasonal reconstruction group;
- 10.9% verified any period;
- mean seasonal RMSE was 0.799.

### Classifier blind spot

This scenario exposes a real limitation. `tseda` is conservative enough to
avoid forcing the terminal cycle onto the entire history, but its full-series
analysis rarely reaches the useful local conclusion. The terminal segment has
more absolute observations at larger \(N\), but it remains only 35% of a much
larger full-series history. The global diagnostics aggregate over increasingly
more pre-regime observations while the evidence remains local, and the
classifier usually stops.

The result should be reported as an open gap:

> Current full-series suitability and periodicity checks do not reliably
> identify a short terminal cycle.

The conditional DW rates are based on very few accepted fits in this scenario
and are not representative of the full DGP. They cannot repair the 11.4%
full-series suitability result or demonstrate that the local cycle was found.

### Analyst response

For suspected recent regime changes:

- segment the series or select a terminal window;
- rerun suitability and periodicity within that regime;
- report periodicity as local, not global;
- compare regime-level residual variance and reconstruction quality.

Until automatic terminal-regime follow-through is improved, this is a mandatory
secondary-analysis case rather than evidence that no cycle exists.

## 4. Within-regime residual-variance shift

### Generating process

The deterministic trend and seven-point seasonality remain stable throughout
the series. At the midpoint, residual-noise scale doubles, making residual
variance approximately four times larger in the second half.

The DGP contains:

- stable deterministic trend;
- stable periodicity;
- one midpoint residual-variance shift;
- no change in the deterministic components themselves.

### Desired diagnosis

`tseda` should:

- continue to classify the series as suitable and periodic;
- preserve the trend/seasonal interpretation across the change;
- detect a variance change near the midpoint;
- avoid describing every residual fluctuation as an additional structural
  regime.

### Observed behavior

| N | Suitable | Group labeled Trend | Group labeled Seasonality | Verified period | DW convergence | CP hit | Mean CP error | Mean points reported |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 60 | 99.8% | 28.0% | 95.5% | 99.8% | 80.2% | 94.2% | 1.99 | 1.77 |
| 150 | 100.0% | 15.7% | 91.2% | 100.0% | 86.3% | 99.7% | 1.68 | 2.70 |
| 400 | 100.0% | 13.8% | 88.2% | 100.0% | 91.2% | 100.0% | 1.32 | 3.67 |

A change-point hit means at least one detected point lies within 10% of sample
length of the true midpoint. Across the complete design:

- period verification: 99.9%;
- suitability: 99.9%;
- change-point hit: 97.9%;
- mean location error among hits: 1.66 samples;
- mean reported change points: 2.71;
- mean seasonal RMSE: 0.288;
- mean trend RMSE: 0.291.

### Classifier strength

The variance-shift result is strong: `tseda` recognizes the stable periodic
process and locates the actual variance transition accurately. It preserves a
supported periodic interpretation rather than treating the change in residual
dispersion as a deterministic seasonal or trend change.

### Classifier blind spot

The detector over-reports. For a DGP with one true variance change, the
procedure reports 2.71 points on average, and the count rises with sample
length. The primary marker is accurate, but the complete marker set needs
specificity calibration.

The table separates the main outcomes:

- **Strong periodic classification:** the period is verified in 99.9% of
  replications and seasonal grouping remains at 91.6%.
- **Strong variance-change localization:** the midpoint is detected in 97.9%
  of replications, with a mean location error of 1.66 samples.
- **Weak trend labeling:** only 19.2% of reconstructions contain a separate
  group labeled `Trend`, despite the DGP's deterministic trend.
- **Weak specificity for additional variance markers:** the detector reports
  2.71 change points on average for a DGP with one true variance transition, so
  markers beyond the accurately localized midpoint require analyst review.

Thus the blind spots are not in period recognition or midpoint localization;
they are semantic trend separation and excess change-point reporting.

## Summary of strengths and blind spots

| DGP | Strength | Blind spot / required secondary validation |
|---|---|---|
| AR(1) persistence | Often converges to a usable residual and limits seasonal false positives more than trend false positives. | Low-frequency persistence is frequently labeled deterministic `Trend`; inspect stationarity/persistence evidence. |
| Stable trend + seasonality | Suitability 100%; period verification 100%; seasonal grouping 99.9%. | Trend grouping appears in only 20.8%; DW is not universally within target. |
| Short terminal regime | Conservatively avoids forcing a recent cycle onto the full history. | Full-series workflow usually stops instead of identifying the local period; segment and re-run. |
| Residual-variance shift | Period remains verified in 99.9%; midpoint detected in 97.9%, mean location error 1.66 samples. | Change-point detector over-reports; trend grouping remains weak. |

## What the study supports

The study supports these claims:

1. `tseda` is strong at blind periodic-process verification for stable cycles.
2. Suitability and periodicity results should remain distinct from component
   labels.
3. `tseda` is conservative about fitting a short cycle globally when only the
   terminal regime contains it.
4. Variance-change localization is accurate, but specificity needs improvement.

The study does not support a claim that:

1. a `Trend` reconstruction group proves deterministic trend;
2. every rejected full-series signal lacks local structure;
3. a verified period guarantees residual independence;
4. every reported variance marker is a distinct real-world transition.

## Practical interpretation

The tool's value is not that it always succeeds at labeling every process. Its
value is that it exposes structure, uncertainty, and diagnostic limits before
an analyst commits to a model.

If the exploratory diagnosis falls near one of the identified blind spots
—stationary persistence, a weak/missing trend label, a short recent regime, or
multiple variance markers—secondary validation should be part of the workflow.
That is not a post-hoc caveat. It is the intended use of an exploratory
classifier: reveal where confidence is warranted and where the next question
must be asked.

## Reproducibility

The executable harness is
[`experiments/run_simulation_study.py`](../experiments/run_simulation_study.py).
The raw checkpoint contains 6,000 `tseda` result rows, one for each DGP cell.
Cross-method reconstruction results are documented separately in
[`comparison_validation_similar_methods.md`](comparison_validation_similar_methods.md).

Generated artifacts:

- `data/simulation_studies/simulation_study_raw.csv`
- `data/simulation_studies/simulation_study_summary.csv`
- `data/simulation_studies/simulation_study_summary.md`
- `data/simulation_studies/simulation_study_summary.tex`

The completed checkpoint is resumable and validated for complete design
coverage, one `tseda` result per cell, and no duplicate rows. Runs default to
one worker and at most 100 new cells to bound memory:

```bash
PYTHONPATH=src python experiments/run_simulation_study.py \
  --replications 200 \
  --workers 1 \
  --max-cells 50 \
  --output-dir data/simulation_studies
```

```bash
PYTHONPATH=src pytest -q tests/test_simulation_study.py
```
