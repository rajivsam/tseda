# Synthetic Data Study Results

Replications per cell: 200.

## Null false-positive control

| subtype | sample_length | method | false_positive_trend_rate | false_positive_seasonality_rate |
| --- | --- | --- | --- | --- |
| ar1 | 60 | tseda | 50.0% | 14.5% |
| ar1 | 150 | tseda | 93.5% | 24.0% |
| ar1 | 400 | tseda | 99.0% | 28.5% |

## Component recovery and residual diagnostics

| subtype | sample_length | snr | method | trend_rmse_mean | seasonality_rmse_mean | durbin_watson_mean | dw_converged_rate | verified_period_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| short_terminal_regime | 60 | 2.000 | tseda | 0.460 | 0.749 | 2.185 | 84.1% | 20.5% |
| short_terminal_regime | 60 | 5.000 | tseda | 0.499 | 0.836 | 2.101 | 92.3% | 19.5% |
| short_terminal_regime | 60 | 10.000 | tseda | 0.514 | 0.865 | 2.149 | 100.0% | 20.5% |
| short_terminal_regime | 150 | 2.000 | tseda | 0.417 | 0.721 | 2.150 | 90.3% | 12.5% |
| short_terminal_regime | 150 | 5.000 | tseda | 0.439 | 0.800 | 2.273 | 95.5% | 11.0% |
| short_terminal_regime | 150 | 10.000 | tseda | 0.450 | 0.818 | 2.213 | 88.9% | 13.5% |
| short_terminal_regime | 400 | 2.000 | tseda | 0.367 | 0.730 | n/a | n/a | 0.0% |
| short_terminal_regime | 400 | 5.000 | tseda | 0.413 | 0.817 | 2.368 | 100.0% | 0.5% |
| short_terminal_regime | 400 | 10.000 | tseda | 0.432 | 0.855 | 1.829 | 100.0% | 0.5% |
| trend_seasonality | 60 | 2.000 | tseda | 0.260 | 0.271 | 2.001 | 89.0% | 100.0% |
| trend_seasonality | 60 | 5.000 | tseda | 0.256 | 0.188 | 1.805 | 67.5% | 100.0% |
| trend_seasonality | 60 | 10.000 | tseda | 0.195 | 0.134 | 2.146 | 23.5% | 100.0% |
| trend_seasonality | 150 | 2.000 | tseda | 0.236 | 0.265 | 2.063 | 99.0% | 100.0% |
| trend_seasonality | 150 | 5.000 | tseda | 0.260 | 0.184 | 1.651 | 73.5% | 100.0% |
| trend_seasonality | 150 | 10.000 | tseda | 0.213 | 0.137 | 1.906 | 21.0% | 100.0% |
| trend_seasonality | 400 | 2.000 | tseda | 0.234 | 0.259 | 2.053 | 100.0% | 100.0% |
| trend_seasonality | 400 | 5.000 | tseda | 0.261 | 0.185 | 1.610 | 73.0% | 100.0% |
| trend_seasonality | 400 | 10.000 | tseda | 0.234 | 0.134 | 1.670 | 20.5% | 100.0% |
| variance_shift | 60 | 2.000 | tseda | 0.348 | 0.394 | 2.152 | 86.4% | 99.5% |
| variance_shift | 60 | 5.000 | tseda | 0.258 | 0.252 | 1.992 | 89.0% | 100.0% |
| variance_shift | 60 | 10.000 | tseda | 0.247 | 0.194 | 1.862 | 65.0% | 100.0% |
| variance_shift | 150 | 2.000 | tseda | 0.366 | 0.424 | 2.192 | 96.0% | 100.0% |
| variance_shift | 150 | 5.000 | tseda | 0.244 | 0.245 | 1.980 | 96.0% | 100.0% |
| variance_shift | 150 | 10.000 | tseda | 0.259 | 0.191 | 1.658 | 67.0% | 100.0% |
| variance_shift | 400 | 2.000 | tseda | 0.397 | 0.452 | 2.266 | 99.0% | 100.0% |
| variance_shift | 400 | 5.000 | tseda | 0.240 | 0.248 | 1.979 | 100.0% | 100.0% |
| variance_shift | 400 | 10.000 | tseda | 0.260 | 0.190 | 1.634 | 74.5% | 100.0% |

## Variance-shift detection

| sample_length | snr | method | change_point_hit_rate | change_point_location_error_mean | detected_change_point_count_mean |
| --- | --- | --- | --- | --- | --- |
| 60 | 2.000 | tseda | 0.910 | 2.628 | 1.525 |
| 60 | 5.000 | tseda | 0.950 | 1.850 | 1.810 |
| 60 | 10.000 | tseda | 0.965 | 1.500 | 1.980 |
| 150 | 2.000 | tseda | 1.000 | 1.600 | 2.110 |
| 150 | 5.000 | tseda | 1.000 | 1.425 | 2.705 |
| 150 | 10.000 | tseda | 0.990 | 2.000 | 3.275 |
| 400 | 2.000 | tseda | 1.000 | 1.025 | 2.715 |
| 400 | 5.000 | tseda | 1.000 | 1.500 | 3.780 |
| 400 | 10.000 | tseda | 1.000 | 1.425 | 4.500 |
