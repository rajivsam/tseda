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
| coffee_prices | ✓ | — | 98.45 | 1.55 | 1.7065303752398788 |
| white_noise_data | rejected | rejected | 0.00 | 0.00 | n/a |
| trimmed_biomass | ✓ | — | 93.79 | 6.21 | 1.7201571160561697 |
| monthly_car_sales | ✓ | ✓ | 90.14 | 9.86 | 2.414672929676177 |
| uci_air_quality_hourly_co | ✓ | ✓ | 83.06 | 16.94 | 1.5677727965182653 |
| ticket_resolution_hourly_nyc311 | ✓ | — | 22.30 | 77.70 | 1.5272124253249215 |
| hyndman_arrivals_quarterly_japan | ✓ | — | 96.29 | 3.71 | 2.062390391408394 |
| hyndman_goog_daily_close | ✓ | — | 99.79 | 0.21 | 2.121087273049771 |
| hyndman_hyndsight_daily_pageviews | ✓ | ✓ | 82.56 | 17.44 | 2.3510354920837018 |
| hyndman_sunspot_monthly_area | ✓ | — | 76.62 | 23.38 | 1.6231811325972851 |
| hyndman_usconsumption_quarterly_consumption | ✓ | — | 34.39 | 65.61 | 2.218193762974913 |
