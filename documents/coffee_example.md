# Coffee example: a segment-first workflow in practice

This example follows the `tseda` workflow on the monthly coffee prices series. It is designed to mirror the sequence described in `about_tseda.md`: start with a broad preliminary assessment, then isolate a segment of interest, run SSA decomposition on that segment, and finally validate the result with diagnostics and operational interpretation.

The goal is not to force a single chart or a single answer. The real value of `tseda` is that it makes the analytical sequence explicit: raw data first, then signal diagnostics, then regime selection, then decomposition, then validation. In operational work this matters because a single chart is rarely enough to justify a forecasting model or a monitoring rule.

## 1. Preliminary analysis: understand the signal before decomposing it

The workflow begins by loading the raw coffee series and summarizing its basic structure. The first view shows the data loaded into the system and gives the analyst a high-level view of the time series: the level, the obvious seasonal or cyclical behavior, and the time window being analyzed.

![Coffee series loaded from the example dataset](../assets/images/coffee_series_summary_raw_data_load.png)

Once the series is in place, the next step is to inspect the distribution and basic shape of the observations. The histogram and box plot summarize where the signal spends most of its time and whether there are long tails or irregular concentration in one region.

![Histogram and box plot for the coffee series](../assets/images/coffee_histogram_box_plot.png)

These preliminary diagnostics help answer a simple but important question: does the signal show enough structure to justify decomposition and further modeling? In the coffee example, the raw values are not flat or random. They have a clear central tendency, visible spread, and a recurring pattern that is consistent with a signal that is worth decomposing rather than treating as noise alone.

This stage also includes autocorrelation and partial autocorrelation diagnostics, which tell the analyst whether the raw series still carries serial dependence and whether the likely structure is consistent with a meaningful regime. These plots are used before the final segment is chosen and help frame the analysis before the decomposition is applied.

![ACF and PACF diagnostics for the preliminary signal review](../assets/images/coffee_acf_pacf_final_segment.png)

The preliminary analysis also checks whether the decomposed trend and residual components behave independently. The weighted correlation view is particularly useful here because it shows whether the extracted trend component and the noise component are effectively uncorrelated, which is a desirable sign that the decomposition is separating signal from noise rather than just re-packaging the same variation.

![Weighted correlation matrix for trend and noise components](../assets/images/coffee_wcorrelation_matrix_plot.png)

A strong decomposition should show low or negligible correlation between trend and noise components, and the Durbin-Watson statistic should sit in the acceptable range. When that condition holds, the decomposition is not merely visually plausible; it also satisfies a basic diagnostic check for residual independence and stability. In this example, the low correlation pattern and the acceptable Durbin-Watson value support the view that the extracted components are meaningfully separated and the decomposition is acceptable for operational use.

This is also where the analyst begins to think in operating-regime terms. The series is not just one long sequence; it is a sequence with periods of different behavior. The next step is therefore to identify candidate breaks in the timeline and select a segment that reflects a coherent operating regime.

## 2. Regime selection: identify the segment to analyze

The next stage in the workflow is segmentation. `tseda` applies change-point detection to the raw series and identifies contiguous periods with broadly similar statistical behavior. This step is designed to separate stable phases from transitions or shocks. In the coffee example, the raw series is segmented into operationally meaningful periods rather than treated as a single undifferentiated block.

![Trend change-point summary for the selected final segment](../assets/images/coffee_trend_change_point_final_segment.png)

A key part of the diagnostic flow is that the system does not stop at the raw segmentation. It checks whether the final segment is large enough to be statistically stable for the downstream decomposition. If the most recent segment is unusually short, it is not treated as a valid final working window on its own. Instead, the system applies a half-life look-back that expands the final working segment backward using exponentially decaying weights from the preceding regime.

This is not arbitrary. The intent is to avoid taking a tiny residual tail and pretending it is a robust analysis window. When the final segment is too short, the most recent observations remain the anchor, but earlier values from the previous regime contribute with diminishing weight so the working window remains stable without discarding the current regime entirely.

The alert below is the user-visible evidence that the adjustment was applied.

![Short final-segment adjustment alert](../assets/images/coffee_short_final_segment_alert.png)

The adjustment itself is shown in the segment-level view. Rather than leaving the last segment at a misleadingly small length, the system defines the effective working window as the adjusted final segment. This is the working series used for the decomposition and downstream panels.

![Adjusted final segment used for analysis](../assets/images/coffee_final_segment_adjustment.png)

This is an important UI and workflow point: the raw segmentation is still useful as context, but the analysis-facing segment is the adjusted one when the final tail is too short. The user sees the adjustment explicitly, and the remainder of the workflow uses the corrected segment instead of the unstable raw tail.

## 3. Segment decomposition: apply SSA to the selected regime

Once a coherent segment is selected, the analysis turns from regime identification to decomposition. In this stage, `tseda` applies Singular Spectrum Analysis (SSA) to the selected segment, where the window length and grouping are chosen to best reflect the dominant structure of that regime.

The selected segment is not the entire history. It is the explicit operating regime the analyst wants to study. Once that segment is chosen, the algorithm reconstructs interpretable variance components such as trend, seasonality, and residual noise, and it examines whether those components are meaningfully separated.

![SSA decomposition of the final adjusted segment](../assets/images/coffee_final_segment_ssa_decomposition.png)

This view makes the decomposition concrete. The trend component captures the broad movement of the signal, the periodic component captures recurrence and seasonal structure, and the residual captures variation that remains after the main components are extracted. The analyst can ask whether the decomposition is logically coherent: do the extracted components line up with expected signal behavior, and does the extracted structure explain the observed regime?

The second decomposition view confirms that the selected segment is not just decomposed once, but also reconstructed and summarized in a way that makes interpretation easier.

![SSA reconstruction and summary for the final segment](../assets/images/coffee_final_seg_ssa_recon_summary.png)

In a serious operational workflow, this is the point where the analyst begins to reason about process behavior. Is there evidence of a long-running trend? Is the seasonal component stable? Are there periods where the residual becomes more variable, suggesting that the operating regime has changed again or that a more detailed model is warranted?

## 4. Validation: check the decomposition against the data and the selected regime

Once the decomposition is available, the next step is validation. `tseda` checks the selected segment using diagnostics that are directly connected to the same regime being analyzed.

This stage now focuses on confirming the decomposition is consistent with the operating regime rather than re-deriving the correlation diagnostics, which were already reviewed in the preliminary analysis. The causal idea is straightforward: preliminary diagnostics establish whether the signal and its components look sensible, and the later validation step checks whether the chosen decomposition remains coherent under the selected segment and the regime-specific decomposition model.

### LOESS comparison and change-point review

The project also supports validation against a smoothing or trend-estimation approach such as LOESS. This helps determine whether the decomposition recovers a broadly similar signal shape compared with a more classic local smoothing method.

![LOESS verification plot for the coffee segment](../assets/images/coffee_loess_verification_plot.png)

This goes hand in hand with the change-point review. The selected segment is judged not only by its internal decomposed structure but also by whether its trend and variability align with the broader regime identification that preceded the SSA step.

### Model validation and observation logging

The final stage of the workflow is about defensibility and reproducibility. It is not enough to have a plausible decomposition; the analyst needs to preserve the evidence behind it. `tseda` therefore supports observation logging and the capture of model-validation metadata so the reasoning is retained and reusable.

![Model validation metadata saved to KMDS](../assets/images/coffee_model_validation_save_to_kmds.png)

This stage records the selected segment, the decomposition settings, the validation diagnostics, and the resulting interpretation. That record is useful for future comparisons, for auditability, and for team handoff. It also makes the workflow repeatable: if the same dataset is revisited later, the analyst can find the earlier assumptions and compare them with the current state.

## 5. Interpreting the result

The coffee price example shows the core `tseda` workflow in action:

1. Raw data is loaded and summarized.
2. A histogram, box plot, and preliminary ACF/PACF diagnostics highlight the signal’s shape, concentration, and serial dependence.
3. The weighted correlation view checks whether the trend and noise components are not strongly correlated and whether the decomposition passes the Durbin-Watson acceptability check.
4. The series is segmented into operating regimes.
5. The final segment is checked for minimum stability and adjusted when needed.
6. A selected segment is decomposed by SSA into interpretable components.
7. LOESS and change-point diagnostics validate the decomposition.
8. The final state is logged and preserved for later review.

This is the real value proposition of `tseda`: it does not require analysts to guess at the right decomposition in isolation. It provides a structured, documented workflow that makes the transition from raw time series to interpretable variance components explicit, auditable, and repeatable.

For coffee prices, that means the analyst is not just looking at a graph of prices. They are looking at a regime-centered decomposition that distinguishes recurring structure from transient variation, identifies where the signal is conceptually stable, and records the reasoning that supports the model decisions.
