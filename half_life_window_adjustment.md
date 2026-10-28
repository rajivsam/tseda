# Half-life final-segment window adjustment

## Purpose

The decomposition workflow first applies PELT segmentation to identify candidate regime boundaries in the raw series. After that, tseda validates the final regime before using it as the working analysis segment. If the last regime is too short to support a statistically stable SSA analysis window, the system expands that final working segment backward using a half-life-weighted look-back from the preceding segment.

This is a UI-level safety rule: the segmented selection shown to the user and used for downstream plots and analysis must use the adjusted final segment when the raw PELT result would otherwise create an unstable tail segment.

## Stage 1: PELT segmentation

1. PELT is run on the input series to estimate a small number of regime changes.
2. The raw segment boundaries are produced as contiguous intervals.
3. The last interval is then checked for stability.

If the last interval is long enough, no adjustment is necessary and the final segment remains unchanged.

## Stage 2: minimum stable final window check

The final selected segment is considered too short when it is below the configured minimum admissible window size.

Configuration parameter:

- `segmentation.minimum_final_segment_points`
- Default behavior: `null` (use cadence-aware defaults)
- Default cadence defaults:
  - sub-hourly: one day of observations at the observed cadence (for example: 5 min => 288 points, 15 min => 96 points, 30 min => 48 points)
  - hourly: 24 * 7 * 3 = 504 points
  - weekly: 12 points
  - daily: 90 points
  - monthly: 12 points

These values are resolved by `resolve_minimum_segment_points()` in `src/tseda/segmentation/pelt_segmentation.py`.

The practical sub-hourly rule is therefore:

- required_points = max(24, points_per_day)
- where `points_per_day = round(24 * 60 / sampling_interval_minutes)`
- so a 5-minute series requires about 288 points for the final working segment, while a 15-minute series requires about 96 points

The effective safety rule is:

- if final segment length >= required minimum points: keep it as-is
- if final segment length < required minimum points: apply the half-life adjustment

The rule is implemented in the segmentation helper `build_adjusted_analysis_segment()` and is also surfaced in the UI via `sync_segment_dropdown()` and `describe_segment_adjustment()`.

## Stage 3: half-life weighted look-back

When the final segment is too short, tseda does not silently keep the tiny tail. Instead, it expands the final working segment backward into the preceding regime using a half-life-weighted look-back.

The adjustment uses two configuration values:

- `segmentation.final_segment_half_life: 30.0`
- `segmentation.final_segment_weight_threshold: 0.95`

### Algorithm

Let the previous segment length be `L` and let the weight for the `k`-th observation in that preceding regime be:

- `w_k = alpha * (1 - alpha)^k`
- `alpha = 1 - exp(-ln(2) / half_life)`

This is the standard exponential-decay formulation associated with a half-life. The cumulative weight is normalized and the adjustment chooses the minimum look-back so that the cumulative prior weight reaches the configured threshold.

Equivalently, the implementation does this:

1. Compute the previous segment's half-life weights.
2. Form the cumulative normalized weights.
3. Find the smallest look-back size such that the cumulative weight is at least `final_segment_weight_threshold` (default 0.95).
4. Expand the final working segment backward from the previous regime by that amount.
5. Use the adjusted segment as the active analysis segment.

This is intentionally conservative: it prevents trivial terminal segments from producing a misleadingly tiny working window for SSA-based trend/seasonality analysis.

Pseudo-code:

```python
half_life = max(float(half_life), 1.0)
alpha = 1.0 - math.exp(-math.log(2.0) / half_life)
weights = [alpha * (1.0 - alpha) ** idx for idx in range(prev_length)]
cumulative = np.cumsum(weights) / np.sum(weights)
lookback = int(np.searchsorted(cumulative, threshold, side="left") + 1)
lookback = max(required_points, min(prev_length, lookback))
adjusted_start = max(prev_start, prev_end - lookback)
selected_segment = (adjusted_start, last_end)
```

## Why this is the right guardrail

The raw PELT output can produce a final change point close to the end of the series. If the remaining tail is extremely short, it may not carry enough observations to support a stable decomposition or change-point review. A tiny tail segment is therefore treated as an artifact of the detection step, not as a valid final operating regime.

The adjusted segment keeps the final regime but expands backward to include a stable share of the previous regime using a mathematically principled decay model.

## Citation grounding for the half-life model

The algorithm is grounded in the standard exponential-decay / half-life formulation used in decay modeling and time-weighted averaging, and in the standard exponential smoothing literature used for time series forecasting.

Key references:

- Hyndman, Rob J., and George Athanasopoulos. Forecasting: Principles and Practice, 3rd ed., OTexts, 2021. Chapter 8, “Exponential smoothing.” The chapter gives the standard weighted-average form for simple exponential smoothing:
  - `ŷ_{T+1|T} = α y_T + α(1 - α) y_{T-1} + α(1 - α)^2 y_{T-2} + ...`
  - This is the canonical exponential decay weighting used in time series forecasting.
  - URL: https://otexts.com/fpp3/exponential-smoothing.html

- pandas Development Team. pandas.DataFrame.ewm documentation. The official pandas EWM documentation defines the half-life parameter relationship as:
  - `alpha = 1 - exp(-ln(2) / halflife)`
  - This is the standard equivalence used in exponential-weighted moving averages.
  - URL: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.ewm.html

- Half-life and exponential decay: https://en.wikipedia.org/wiki/Half-life
- Exponential decay: https://en.wikipedia.org/wiki/Exponential_decay

The implementation uses the standard relationship between the decay constant and half-life:

- `lambda = ln(2) / half_life`
- `alpha = 1 - exp(-lambda)`

This is equivalent to the established formulation used for exponential weighting and half-life smoothing, and it is the same family of decay used in the EWMA/ES literature cited above.

## UI behavior

If the final segment is short and is adjusted, the UI uses the adjusted final segment in the analysis workflow.

This includes:

- the segment dropdown summary label for the last segment
- the selected working segment used in the segment preview panel
- any ACF / PACF or segment-specific diagnostics based on the effective final segment
- the final working series used for downstream analysis after the adjustment

The raw PELT segmentation is still available for context in the raw scatter plot, but the analysis-facing UI selection is the adjusted final segment when the minimum stable window rule is triggered.

## Summary

The complete sequence is:

1. Run PELT segmentation.
2. Check the final segment length against the minimum stable analysis window.
3. If it is too short, apply a half-life-weighted backward expansion from the preceding regime.
4. Use the adjusted segment as the working analysis segment in the UI.
5. Keep the raw PELT segmentation visible only as context where appropriate.
