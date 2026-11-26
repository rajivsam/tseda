# Cross-Method Validation of the Exploratory Classifier

## Purpose

This Item 3 validation examines `tseda` as an exploratory classifier first and
as a reconstruction method second. The central questions are:

1. Does `tseda` identify the process defensibly before decomposition?
2. Does it find the documented period rather than merely fit a requested
   periodic component?
3. After a periodic process is accepted, is its broad signal/noise allocation
   consistent with default STL-family decompositions?
4. Where does a parameterized smoother appear better because the benchmark has
   already supplied information that `tseda` had to discover?

The variance comparison is therefore a conditional confirmation. It is useful
only after suitability, process classification, period discovery, and grouping
have produced an interpretable result.

> [!IMPORTANT]
> **These methods are not solving the same information problem.** `tseda`
> starts from the series alone: it has to decide whether decomposition is
> defensible, identify a candidate period, and verify that period. STL and MSTL
> are supplied the documented period and can therefore be optimized around a
> fact that `tseda` had to discover. Small reconstruction advantages in favor
> of STL or MSTL are consequently not evidence that the blind exploratory
> classifier failed. They show that, once periodic structure is already known,
> a specialized smoother may allocate variance a little differently. The
> relevant `tseda` gaps are the actual classifier blind spots exposed here:
> weak or missing component labels, residual diagnostics outside the target,
> and known corner cases involving persistence or short/local regimes. For
> series resembling those corner cases, secondary classification or
> domain-informed validation is advisable.

It does not claim that SSA, STL, and MSTL are interchangeable. STL or MSTL can
always return fitted trend and seasonal components when a period is supplied;
that output is not itself evidence that a periodic process has been identified.
Variance agreement similarly does not prove component equivalence.

> **Triage is mandatory and method-independent.** Before any decomposition,
> every real-world series must be assessed for suitability for decomposition.
> Irrespective of whether SSA, STL, MSTL, or another method is used later, this
> initial triage is a core `tseda` feature. It checks whether the series contains
> enough concentrated structure to justify a decomposition and must not be
> bypassed when changing algorithms.

The comparator evaluation therefore records and enforces suitability first.
White noise, stochastic persistence, or another unsuitable input is not
rescued by trying a method that always returns fitted components.

## Classification-oriented evaluation

### Dataset selection

Five datasets were selected from the 11-dataset comprehensive suite because
they are fixed local snapshots, have documented periodic structure, contain
enough history for their period, and pass full-series suitability triage:

| Dataset | Samples | Documented period | Suitability | SSA window selected |
|---|---:|---:|---|---:|
| `monthly_car_sales` | 108 | 12 months | pass | 12 |
| `uci_air_quality_hourly_co` | 2,000 | 24 hours | pass | 24 |
| `hyndman_arrivals_quarterly_japan` | 127 | 4 quarters | pass | 4 |
| `hyndman_hyndsight_daily_pageviews` | 365 | 7 days | pass | 7 |
| `hyndman_sunspot_monthly_area` | 1,709 | approximately 132 months | pass | 131 |

`ticket_resolution_hourly_nyc311` was excluded because it is a time-dependent
rolling snapshot, not a fixed benchmark. Series without a documented fixed
period, including coffee prices and GOOG closing prices, are not suitable for
this specific single-period comparator test. The white-noise series is also
excluded because it is the negative control that the suitability gate must
reject.

The exclusions are part of the classifier evaluation. `coffee_prices` and GOOG
closing prices are dominated by stochastic persistence, while white noise has
no reproducible process to decompose. Giving those series to STL with a period
would manufacture a seasonal output rather than reveal one.

### Methods and parameter policy

The comparison uses Statsmodels 0.14.6:

1. **SSA**: use `NotebookThreeStepAPI`, the repository's suitability check,
   existing automatic window autotuning, and automatic grouping. SSA's only
   structural parameter is the window length; the project provides a
   comprehensive tuning guide for that choice.
2. **STL**: call `STL(observed, period=known_period)`. All optional values retain
   the defaults: `seasonal=7`, automatically selected `trend` and `low_pass`
   windows, polynomial degrees of 1, `robust=False`, and jumps of 1.
3. **MSTL**: call `MSTL(observed, periods=(known_period,))`. `windows` and
   `lmbda` remain at their defaults (`None`), `iterate=2`, and no `stl_kwargs`
   are supplied.

   The information available to the methods is not identical. `tseda` must
   classify the series and discover/verify its period from observations. STL and
   MSTL receive the ground-truth period directly. Their reconstruction quality
   therefore represents performance **conditional on known periodicity**, not a
   stronger blind-classification capability.

These are deliberately **default-value results**. Tuning STL/MSTL smoothing
windows, polynomial degrees, robustness, jumps, and other options is difficult
and can materially change the answer. Tuning them to optimize this benchmark
would hide the operational value proposition of SSA: one structural parameter
plus a documented tuning procedure instead of a multi-parameter search. The
period supplied to STL/MSTL is not tuned; it is the known period from the
ground-truth document.

### Common variance definition

All methods are evaluated on the same scale:

- SSA uses its internally standardized `raw_signal`.
- STL and MSTL receive that same standardized signal.
- Explained variance is
  `100 * (1 - residual_sum_of_squares / centered_total_sum_of_squares)`.
- Unexplained variance is `100 - explained_variance`.
- SSA reconstruction uses all signal groups after automatic grouping, excluding
  its residual/noise group.
- STL and MSTL reconstruction uses trend plus seasonal components; each
  method's remainder is residual.

This is a reconstruction-based comparison, not a comparison of eigenvalue
shares. It avoids declaring a different scale or variance formula for each
method.

### Classification checks and variance acceptance criterion

For `tseda`, classification is successful on a selected dataset when:

- full-series suitability passes;
- the process class is `periodic`;
- process-aware diagnostics contain the documented period within the accepted
  tolerance;
- the automatic reconstruction contains a seasonal group;
- the resulting residual is not automatically treated as valid unless its
  Durbin-Watson diagnostic has been inspected.

After those checks, the secondary variance comparison considers methods broadly
similar when each STL-family result is within 15 percentage points of SSA on
explained and unexplained variance. The tolerance identifies a common broad
allocation, not exact equality.

## Process-classification results

| Dataset | Ground-truth process | What `tseda` classified | Verified period | Reconstruction grouping | DW |
|---|---|---|---:|---|---:|
| `monthly_car_sales` | trend + annual seasonality | periodic / suitable | 12.00 | Trend + Seasonality | 2.62 |
| `uci_air_quality_hourly_co` | operational trend + diurnal seasonality | periodic / suitable | 23.58 | Trend + Seasonality | 1.76 |
| `hyndman_arrivals_quarterly_japan` | trend regimes + quarterly seasonality | periodic / suitable | 4.00 | Seasonality only | 2.06 |
| `hyndman_hyndsight_daily_pageviews` | level changes + weekly seasonality | periodic / suitable | 7.02 | Trend + Seasonality | 2.73 |
| `hyndman_sunspot_monthly_area` | long-cycle periodicity with changing amplitude | periodic / suitable | 131.46 | Trend + Seasonality | 1.54 |

This table is the primary result of the exploratory evaluation:

- **All five documented periods were discovered and verified without supplying
  the period to `tseda`.**
- **All five full series passed suitability after process classification.**
- Four datasets retained both trend and seasonal groups. The quarterly-arrivals
  series received only a seasonal group; its trend/regime story should be
  carried by segmentation and process classification rather than by a separate
  deterministic SSA trend label.
- Hyndsight has DW 2.73, above the nominal target; period discovery is supported,
  but residual behavior remains a caveat.

STL and MSTL have no corresponding classifier result in this benchmark. They
were given the period and fitted the requested components. Their 100% ability
to emit trend and seasonal curves must not be compared directly with
`tseda`'s verified period rate.

## Secondary reconstruction-variance results

The test was run with:

```bash
PYTHONPATH=src pytest -q tests/test_comparison_validation_similar_methods.py
```

| Dataset | SSA explained / unexplained | STL default explained / unexplained | MSTL default explained / unexplained | Absolute difference from SSA (STL / MSTL) |
|---|---:|---:|---:|---:|
| `monthly_car_sales` | 97.28% / 2.72% | 96.54% / 3.46% | 95.46% / 4.54% | 0.74 / 1.82 pp |
| `uci_air_quality_hourly_co` | 88.21% / 11.79% | 81.68% / 18.32% | 75.52% / 24.48% | 6.54 / 12.69 pp |
| `hyndman_arrivals_quarterly_japan` | 97.29% / 2.71% | 99.06% / 0.94% | 99.18% / 0.82% | 1.77 / 1.89 pp |
| `hyndman_hyndsight_daily_pageviews` | 88.51% / 11.49% | 90.07% / 9.93% | 88.52% / 11.48% | 1.57 / 0.01 pp |
| `hyndman_sunspot_monthly_area` | 78.37% / 21.63% | 74.65% / 25.35% | 65.80% / 34.20% | 3.73 / 12.57 pp |
| **Mean** | **89.93% / 10.07%** | **88.40% / 11.60%** | **84.90% / 15.10%** | — |

All 10 method comparisons pass the 15-percentage-point criterion; the largest
absolute difference is 12.69 points. The mean STL default allocation is close
to SSA, while the mean default MSTL allocation retains more residual variance.
These results support broad agreement in signal/noise allocation for the
selected datasets, but not exact component equivalence.

## Strengths and weaknesses exposed by the comparison

### Where the exploratory classifier does well

- **Blind period discovery:** `tseda` recovers 12, approximately 24, 4, 7, and
  approximately 132 samples from the observations. STL/MSTL cannot establish
  these periods here because the benchmark supplies them.
- **Separation of identification from fitting:** periodicity is verified before
  a seasonal reconstruction is interpreted. This is stronger evidence than a
  smoother's nonzero seasonal output.
- **Consistent broad reconstruction:** once classification succeeds, SSA's
  explained/residual allocation stays within 12.69 percentage points of both
  default STL-family methods in every case.
- **One structural parameter:** SSA requires the analyst to tune window length,
  while STL/MSTL require period knowledge plus consequential default or tuned
  choices for smoothing windows, robustness, polynomial degrees, jumps, and
  iteration.

### Where the alternatives appear stronger

- **Conditional fitting when the period is known:** STL/MSTL can explain
  slightly more or less variance than SSA without first passing a suitability
  or periodicity decision. That is useful reconstruction performance, but it is
  conditional on information supplied to them.
- **Quarterly-arrivals reconstruction:** STL and MSTL attribute 99.06% and
  99.18% to trend plus seasonality versus 97.29% for SSA. The difference is
  small, but the defaults are effective for this short, regular benchmark.
- **Hyndsight reconstruction:** default STL and MSTL explain 90.07% and 88.52%
  versus SSA's 88.51%. STL is marginally better on this allocation even though
  `tseda` is the method that independently discovers the weekly cycle.
- **Default MSTL's lower explained share on complex operational/long-cycle
  data:** this is not uniformly “better.” It retains more residual for the
  air-quality and sunspot series, exposing sensitivity to unoptimized windows
  and evolving structure.

These small advantages should be read in the context of the information callout
above. They concern conditional reconstruction after known-period input. They
do not imply that STL/MSTL independently found the process, rejected unsuitable
inputs, or performed cold-start triage.

### Classifier weaknesses that reconstruction variance does not fix

- A correct period does not guarantee a separate, semantically correct `Trend`
  group. The quarterly-arrivals series is periodic and suitable, but its
  reconstruction labels no trend group.
- A within-tolerance variance share does not validate residual independence:
  Hyndsight's DW of 2.73 remains a diagnostic caveat.
- Similar variance allocation can occur for differently shaped components.
- Because these five datasets were selected to have periodic structure, this
  benchmark does not test the harder classifier cases: stochastic persistence,
  diffuse noise, abrupt regime changes, or short terminal cycles. The separate
  synthetic and comprehensive studies cover those limitations.

## Practical interpretation

- **Strong agreement:** monthly car sales, quarterly Japan arrivals, and daily
  Hyndsight page views produce nearly identical broad signal/residual shares.
- **Reasonable agreement with higher variation:** the air-quality and sunspot
  series show larger default-MSTL residuals. Their irregularity and evolving
  cycle structure make optional smoothing and robustness choices consequential.
- **Default values matter:** STL and MSTL require the known seasonal period plus
  several controls with consequential defaults. These results intentionally do
  not claim that a tuned comparator would be worse or that one default is
  universally appropriate.
- **SSA's practical distinction:** only window length is structurally tuned for
  SSA, and the existing guide constrains that decision. This reduces the
  analyst's parameter-search burden in cold-start exploration.
- **Classifier first, decomposition second:** the main `tseda` value in this
  benchmark is deciding that a periodic decomposition is supported and finding
  the period without prior specification. Variance agreement is supporting
  evidence that its subsequent reconstruction is not wildly inconsistent with
  established decomposers.
- **Suitability remains decisive:** a method can always produce numerical trend
  and seasonal components; the central exploratory question is whether the
  input supports a meaningful deterministic decomposition.

## Scope and limitations

1. The variance results are secondary. This is not a blind method-comparison
   benchmark because STL/MSTL receive the period, whereas `tseda` must discover
   it.
2. This is a variance-allocation comparison, not a test of component shape,
   forecasts, change points, or causal interpretation.
3. The selected series are periodic cases. Results should not be generalized to
   stochastic persistence, diffuse noise, or irregular stationary processes.
4. STL and MSTL are evaluated at library defaults. Parameter-tuned results may
   differ substantially.
5. The benchmark uses known ground-truth periods. In a blind exploration, period
   estimation is another required decision for the alternatives.
6. A future comparator study should include blinded period selection, outlier
   robustness, nonstationary regimes, and holdout reconstruction error.

The executable Item 3 check is maintained in
`tests/test_comparison_validation_similar_methods.py`.