# Test dataset report

This report exercises the comprehensive dataset validation workflow implemented in `tests/test_comprehensive_dataset.py`.
Each built-in time series is loaded, evaluated by `NotebookThreeStepAPI`, and summarized for trend/seasonality presence, variance explained, noise variance, and Durbin-Watson behavior.

## How to run

```bash
PYTHONPATH=src python -m tseda --generate-test-dataset-report --report-output documents/test_datasets_report.md
# or, when installed as a console script
tseda --generate-test-dataset-report --report-output documents/test_datasets_report.md
```

The command generates a Markdown summary and exits without starting the Dash UI.

## Dataset summary

| Dataset | Trend | Seasonality | Variance Explained (%) | Noise Variance (%) | Durbin-Watson |
|---|---|---|---:|---:|---:|
| coffee_prices | ✓ | — | 98.20 | 1.80 | 1.94 |
| white_noise_data | rejected | rejected | 0.00 | 0.00 | n/a |
| trimmed_biomass | ✓ | — | 91.50 | 8.50 | 1.52 |
| monthly_car_sales | ✓ | — | 95.86 | 4.14 | 1.89 |
| uci_air_quality_hourly_co | ✓ | ✓ | 84.85 | 15.15 | 1.67 |
| ticket_resolution_hourly_nyc311 | ✓ | — | 22.30 | 77.70 | 1.53 |
| hyndman_arrivals_quarterly_japan | ✓ | — | 97.40 | 2.60 | 1.44 |
| hyndman_goog_daily_close | ✓ | — | 98.16 | 1.84 | 1.97 |
| hyndman_hyndsight_daily_pageviews | ✓ | — | 80.99 | 19.01 | 2.20 |
| hyndman_sunspot_monthly_area | ✓ | — | 77.87 | 22.13 | 1.73 |
| hyndman_usconsumption_quarterly_consumption | ✓ | — | 46.63 | 53.37 | 1.84 |
