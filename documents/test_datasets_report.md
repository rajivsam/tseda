# Test dataset report

This report exercises the comprehensive dataset validation workflow implemented in `tests/test_comprehensive_dataset.py`.
Each built-in time series is loaded, evaluated by `NotebookThreeStepAPI`, and summarized for full/active process classification, verified periods, secondary residual-variance changes, reconstruction behavior, and Durbin-Watson diagnostics.

## How to run

```bash
PYTHONPATH=src python -m tseda --generate-test-dataset-report --report-output documents/test_datasets_report.md
# or, when installed as a console script
tseda --generate-test-dataset-report --report-output documents/test_datasets_report.md
```

The command generates a Markdown summary and exits without starting the Dash UI.

## Scope and suitability terminology

**Full Process** classifies behavior over the complete loaded series. **Active Process** classifies only the selected final/current regime, using the shared PELT/chunk boundary rules and the half-life lookback when that final regime is too short. Active Process may therefore be `indeterminate` even when the full series has a confirmed pattern: the local segment may not contain enough complete cycles.

`indeterminate` means the package could not separate valid competing interpretations with the available scope, cadence, cycle count, or diagnostics. It is not evidence of no structure. `unsuitable` means the evidence does not support a deterministic SSA decomposition; diffuse noise is the canonical example. Stochastic persistence can still be classified reliably without being suitable for deterministic Trend/Seasonality extraction.

**Pareidolia guardrail.** Stochastic persistence is consistent with a random walk, persistent AR process, or another stochastic trend. For a pure random walk, visual smoothing can create pareidolia—the tendency to see meaningful patterns in random/stochastic variation. Do not interpret smooth SSA level modes as deterministic trend or seasonality. This tool is not the right exploration choice for the level process. Investigate a random-walk, ARIMA/differenced, local-level, or state-space model. If that analysis produces a separately defined residual, innovation, or differenced series, it may be submitted as a new analysis only after it independently passes cadence and identifiability checks.

## Dataset summary

| Dataset | Full Process | Active Process | Full Periods | Variance Change-Points | Trend | Seasonality | Persistence | Variance Explained (%) | Noise Variance (%) | Durbin-Watson |
|---|---|---|---|---|---|---|---|---:|---:|---:|
| coffee_prices | stochastic_persistence | stochastic_persistence | — | not applicable | rejected | rejected | — | 0.00 | 0.00 | n/a |
| white_noise_data | diffuse_noise | diffuse_noise | — | not applicable | rejected | rejected | — | 0.00 | 0.00 | n/a |
| trimmed_biomass | deterministic_trend | stationary_irregular | — | 29 (2018-04-13 02:00:00+00:00 → 2018-07-03 18:00:00+00:00) | ✓ | — | — | 93.79 | 6.21 | 1.72 |
| monthly_car_sales | periodic | indeterminate | 12.00 | none | ✓ | ✓ | — | 96.41 | 3.59 | 2.62 |
| uci_air_quality_hourly_co | periodic | periodic | 23.58 | 24 (2005-01-16 01:00:00 → 2005-04-03 18:00:00) | ✓ | ✓ | — | 86.65 | 13.35 | 1.76 |
| ticket_resolution_hourly_nyc311 | periodic | periodic | 24.03 | 13 (2026-04-04 19:00:00 → 2026-05-03 18:00:00) | ✓ | ✓ | — | 43.98 | 56.02 | 2.08 |
| hyndman_arrivals_quarterly_japan | periodic | periodic | 4.00 | 1 (2002-04-01 00:00:00) | — | ✓ | — | 96.29 | 3.71 | 2.06 |
| hyndman_goog_daily_close | stochastic_persistence | stochastic_persistence | — | not applicable | rejected | rejected | — | 0.00 | 0.00 | n/a |
| hyndman_hyndsight_daily_pageviews | periodic | periodic | 7.02 | 2 (2014-08-28 00:00:00 → 2014-09-07 00:00:00) | ✓ | ✓ | — | 87.01 | 12.99 | 2.73 |
| hyndman_sunspot_monthly_area | periodic | stochastic_persistence | 131.46 | 34 (1875-08-01 00:00:00 → 2015-03-01 00:00:00) | ✓ | ✓ | — | 77.40 | 22.60 | 1.54 |
| hyndman_usconsumption_quarterly_consumption | stationary_irregular | indeterminate | — | 1 (1992-07-01 00:00:00) | ✓ | — | — | 34.39 | 65.61 | 2.22 |

## Ground-truth due diligence

The expected process classes and periods below come from [`test_case_ground_truth.md`](test_case_ground_truth.md), not from the package output. The observed columns are produced independently by the process-aware SSA pipeline. A period matches when the package estimate is within 15% of the expected value.

| Dataset | Expected Process | Produced Process | Expected Period | Produced Period | Comparison |
|---|---|---|---:|---:|---|
| coffee_prices | stochastic_persistence | stochastic_persistence | — | — | Matches |
| white_noise_data | diffuse_noise | diffuse_noise | — | — | Matches |
| trimmed_biomass | deterministic_trend | deterministic_trend | — | — | Matches |
| monthly_car_sales | periodic | periodic | 12.00 | 12.00 | Matches |
| uci_air_quality_hourly_co | periodic | periodic | 24.00 | 23.58 | Matches |
| ticket_resolution_hourly_nyc311 | periodic | periodic | 24.00 | 24.03 | Matches |
| hyndman_arrivals_quarterly_japan | periodic | periodic | 4.00 | 4.00 | Matches |
| hyndman_goog_daily_close | stochastic_persistence | stochastic_persistence | — | — | Matches |
| hyndman_hyndsight_daily_pageviews | periodic | periodic | 7.00 | 7.02 | Matches |
| hyndman_sunspot_monthly_area | periodic | periodic | 132.00 | 131.46 | Matches |
| hyndman_usconsumption_quarterly_consumption | stationary_irregular | stationary_irregular | — | — | Matches |

## Indeterminate and unsuitable cases in this run

| Dataset | Full Process | Active Process | Full Suitability | Interpretation |
|---|---|---|---|---|
| coffee_prices | stochastic_persistence | stochastic_persistence | unsuitable | Stochastic persistence is consistent with a random walk, persistent AR process, or another stochastic trend. For a pure random walk, visual smoothing can create pareidolia—the tendency to see meaningful patterns in random/stochastic variation. Do not interpret smooth SSA level modes as deterministic trend or seasonality. This tool is not the right exploration choice for the level process. Investigate a random-walk, ARIMA/differenced, local-level, or state-space model. If that analysis produces a separately defined residual, innovation, or differenced series, it may be submitted as a new analysis only after it independently passes cadence and identifiability checks. |
| white_noise_data | diffuse_noise | diffuse_noise | unsuitable | diffuse_eigen_spectrum |
| monthly_car_sales | periodic | indeterminate | suitable | The active regime is underpowered or contradictory; retain the full-series result. |
| hyndman_goog_daily_close | stochastic_persistence | stochastic_persistence | unsuitable | Stochastic persistence is consistent with a random walk, persistent AR process, or another stochastic trend. For a pure random walk, visual smoothing can create pareidolia—the tendency to see meaningful patterns in random/stochastic variation. Do not interpret smooth SSA level modes as deterministic trend or seasonality. This tool is not the right exploration choice for the level process. Investigate a random-walk, ARIMA/differenced, local-level, or state-space model. If that analysis produces a separately defined residual, innovation, or differenced series, it may be submitted as a new analysis only after it independently passes cadence and identifiability checks. |
| hyndman_usconsumption_quarterly_consumption | stationary_irregular | indeterminate | suitable | The active regime is underpowered or contradictory; retain the full-series result. |
