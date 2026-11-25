# Comprehensive Dataset Results Metadata

Field | Description | Computation / Input
--- | --- | ---
dataset | Identifier for the dataset being tested. | This is an input.
full_samples | Number of rows in the full time series. | Derived from the loaded series.
active_samples | Number of rows in the active regime. | Derived from shared segmentation logic.
full_process_class | Process classification for the full series. | Derived from process-aware SSA diagnostics.
active_process_class | Process classification for the active regime. | Derived from process-aware SSA diagnostics.
full_periods | Verified full-series periods. | Derived from verified SSA pairs and cadence evidence.
active_periods | Verified active-regime periods. | Derived from verified SSA pairs and cadence evidence.
window | Window size suggested or used by the API. | Derived from the API's internal suitability and window selection logic.
suitability_passed | Whether the series passed the suitability gate. | Derived from `api.get_suitability_result().is_suitable`.
top_k_ratio | Ratio used to determine the top-k reconstruction components. | Derived from the suitability result returned by the API.
top_k | Number of top components selected for reconstruction. | Derived from the suitability result returned by the API.
threshold | Suitability threshold value for the dataset. | Derived from the suitability result returned by the API.
trend | Whether a Trend component was identified in the reconstruction. | Derived from the explained variance output; checks if `Trend` variance percent is greater than zero.
seasonality | Whether a Seasonality component was identified. | Derived from the explained variance output; checks if `Seasonality` variance percent is greater than zero.
persistence | Whether a stochastic low-frequency Persistence component was identified. | Derived from the explained variance output.
variance_explained | Total explained variance percent across all identified components. | Derived by summing all values in `reconstructed['explained_variance_percent']`.
durbin_watson | Durbin–Watson statistic for reconstructed residuals. | Derived from `reconstructed.get('durbin_watson')` when reconstruction metadata is available.
change_points | Summary of detected change points in trend and seasonal behavior. | Derived from `api.get_change_points()` and formatted as a summary string.
component_rows | Number of component rows returned by the API when components are exported. | Derived from the length of the component DataFrame or the original series if the grouping was rejected.

For fields labeled as input, the value is directly produced by the dataset or series load process. For derived fields, the value is computed by the API or by aggregating its output.