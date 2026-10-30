# Summary of `tseda` - Features and Use


## About tseda
`tseda` is a tool for analyzing operational data from real-world datasets. Its primary goal is to support model development and control (as in operational monitoring and planning) with that data. Forecasting is one example of an application that can benefit from `tseda` analysis. `tseda` can also help teams understand how business processes behave so they can be monitored and managed by technical operations personnel. 

For example, an online store may want to understand how customers use the storefront or a service such as the customer address locator. By sampling and tracking that activity, `tseda` helps operations teams identify when demand is high, when reliability matters most, and when maintenance windows are appropriate. The same data can also inform forecasting and planning: model developers can use it to predict demand, estimate resource consumption, and check whether the assumptions behind a model remain valid in real operating conditions.

In this setting, `tseda` helps decompose a time series into interpretable variance components that support both operational monitoring and model development. The needed insight is rarely captured by a single plot or model; it usually emerges over time through a sequence of diagnostics and a growing intuition for how the signal is structured.

Several signal decomposition techniques are available. This software uses a method called Singular Spectrum Analysis (SSA). One advantage of this approach is that it requires selecting a single structural parameter, the window length, and the interpretation is intuitive. Once the window is chosen, established statistical methods can be used to validate that it gives a near-optimal variance decomposition. The window-selection procedure is described later in the workflow.

Because this type of analysis is often repeated on a regular schedule, it can be useful to log the observations from each iteration so that historical context is available for future decisions.

`tseda` brings these activities together in a single application interface. In short, it is one tool in your time series toolbox to support your preferred time series analysis, data modeling, and operational monitoring workflows.

## Why is `tseda` useful?

The value of identifying variance components is clear for model development: it tells modelers which behaviors need to be represented explicitly and provides extracted signals that can be used to develop a model. The operational value is equally important, although it may be less obvious. Operations teams need to configure alerts and establish guidelines for the range of behavior that should be expected from a particular signal.

Segmentation and variance decomposition provide evidence for those operational decisions. For a given signal, the historical record shows how often the behavior changed and how much variation is attributable to residual noise. Segmentation identifies the current operating regime and makes changes in behavior visible, while decomposition distinguishes systematic behavior such as trend and seasonality from the noise that remains after those effects are accounted for. This helps monitoring teams distinguish expected variation from a meaningful change that warrants investigation.

For bounded random variables, where observations fall within a known range `[a, b]`, concentration inequalities can be used to bound unusually high values within a regime. Maximum-value bounding based on this approach is an upcoming feature for `tseda`; it is not yet part of the current workflow. Even before that feature is available, the segmentation and decomposition outputs give operations teams a practical historical baseline for alert thresholds, expected-range guidance, and detecting changes in the current regime.

The hard part in practice is not any one chart or statistic by itself. It is the fact that getting to a useful decomposition usually requires many steps, many tuning choices, and a careful stitching together of methods: selecting a sampling-aware window, identifying regime boundaries, testing candidate groupings, checking whether the decomposition is structurally meaningful, and then validating the result against the data. These are not isolated decisions; they are part of one analytical workflow. `tseda` is designed to make those choices more explicit, more literature- and practice-grounded, and easier to revisit later. It also makes it possible to log earlier analyses, query them, and repeat or compare them when the same problem reappears with new data.

## How does an analyst use `tseda`?

An analyst starts by launching the `tseda` application and uploading a CSV or similar data file containing two columns: a timestamp and a signal value. At present, `tseda` supports regularly sampled signals only, meaning that the time interval between successive observations is constant. The application infers the sampling period automatically and supports a range of intervals suitable for operational analysis, from short cadence data (for example, 5-minute intervals) to weekly data. The supported range is intended for practical monitoring and forecasting workflows, including use cases spanning roughly 3 months to a year.

The overall workflow is organized into three stages:

### Preliminary Analysis

The goal of this stage is to understand the signal before applying decomposition. The application presents a set of diagnostic views, including:

1. Signal histogram and kernel density estimate: the histogram summarizes where the signal is concentrated, with bin selection defaulting to Scott's rule unless the user explicitly chooses another rule in the notebook interface.
2. Signal box plot: this provides a compact five-number summary of the distribution over the observation window.
3. Raw signal plot: this gives a visual overview of the time series itself and highlights the variation we ultimately want to decompose into a small number of interpretable components.
4. Signal segmentation: the timeline is partitioned into contiguous segments with broadly similar statistical behavior. `tseda` uses change-point detection based on the PELT method to identify structural changes, such as shifts in level, volatility, or seasonality ([Killick, Fearnhead, and Eckley, 2012](https://doi.org/10.1080/01621459.2012.737745)). Broader context on offline change-point methods is provided by the review of [Truong, Oudre, and Vayatis (2020)](https://doi.org/10.1016/j.sigpro.2019.107299). Each segment represents a distinct operating regime and helps distinguish stable periods from changes that warrant closer attention.

   The segmentation step is not just descriptive; it shapes the rest of the analysis. For each segment, the system recommends a modeling approach based on the segment’s statistical profile: the linear `l2` model is preferred for trend-dominant or long, stable signals, while the kernelized RBF option is reserved for cases where the seasonal behavior is strongly non-normal, multimodal, or otherwise more complex. This recommendation logic follows the project’s literature review and established modeling guidance, and an advisor feature can explain the rationale in plain language.

   The analyst is not limited to a single segment. `tseda` makes it easy to inspect any regime in the series, and any segment can be selected for follow-up analysis. By default, the most recent segment is highlighted because it usually reflects the current operating conditions, but the interface also allows comparison with earlier segments when the analyst is interested in historical regime changes. This supports both current-state analysis and regime comparison.
   
   As a further refinement, the software first identifies a plausible operating regime through change-point detection on the full series. The analyst then selects that segment as the active analysis target. Once the segment is chosen, the software runs SSA on that specific segment and reconstructs its component structure (for example, trend, seasonality, and residual/noise). It then performs a second layer of change-point analysis on those reconstructed group signals to detect whether the variance structure inside the segment itself has shifted. In practice, this means checking for changes in trend behavior, seasonal amplitude, and seasonal phase. The full series remains available as context, but the decomposition and subsequent diagnostics are focused on the selected segment rather than treating every segment as a separate independent model.

5. ACF and PACF plots: the application generates autocorrelation and partial autocorrelation diagnostics for the selected segment, with the most recent segment as the default focus. This is important because the decomposition step also defaults to the latest regime unless the analyst explicitly selects another segment. The result is a workflow that keeps the analysis anchored to present conditions while still enabling controlled comparisons across historical periods.

   If the final segment is too short to support a stable SSA decomposition, `tseda` uses a dedicated fallback. Instead of discarding the most recent observations, the implementation expands the final analysis window backward using a half-life-weighted look-back from the preceding segment. The current segment remains the anchor, while earlier observations from the previous regime are blended in with exponentially decreasing weights so that recent values retain more influence than older values. This logic is implemented in the segment-adjustment utilities using a half-life parameter and a cumulative weight threshold, and the adjusted segment is then used as the input to the downstream SSA analysis.

   In practical terms, the system checks whether the final segment meets the minimum support needed for the inferred cadence and, if not, it triggers the weighted fallback. This preserves enough context to stabilize the decomposition while still emphasizing the recent behavior that matters most for current analysis. The user is explicitly alerted when this adjustment is applied so the change in the effective analysis window is visible and auditable.

### Segment Decomposition

The preliminary diagnostics establish the operating context for the series. The next step is to decompose the selected segment into interpretable components. A segment is a contiguous period with broadly similar statistical behavior, and the decomposition is performed on that segment rather than on the entire time series in one pass.

Singular spectrum analysis extracts variance components by constructing a trajectory matrix whose rows represent successive windows of the signal. The basis vectors of this matrix capture the dominant structure of the series, and the eigenspectrum helps distinguish between trend-like, seasonal, and noise-like behavior. The software applies these ideas to identify the components that best explain the variance in the selected regime.

In SSA, the window length is the key structural choice. It determines how many consecutive observations are embedded together when the trajectory matrix is formed. A good window is large enough to capture identifiable repeating structure, but not so large that distinct regimes or components become blurred together. This is why the system uses a heuristic procedure that starts from a cadence-based estimate and refines the window until the resulting decomposition is stable and informative.

Interested readers can refer to the [window selection algorithm document](window_selection_algorithm.md) for a more detailed explanation of the heuristic used to choose and refine the window.

At this stage, the analyst can also assess how well the decomposition explains the underlying signal. Two practical questions are especially relevant:

1. How much of the variation in the original series is explained by the extracted components, and can we visualize that contribution?
2. Can we validate the decomposition against another smoothing or trend-estimation method, such as LOESS, to check whether we recover a similar underlying signal?

The answer to both questions is yes. The decomposition panel includes visual diagnostics for explained variance and component structure, making it easier to see whether trend, seasonality, and noise are being separated in a meaningful way. LOESS can be used as a comparison tool, but it is not a direct substitute for SSA: in many implementations it requires additional tuning choices, including the smoothing span and an estimate of seasonal structure. By contrast, `tseda` keeps the SSA workflow interpretable and comparatively lightweight, with the main structural choice being the window length.

This is one of the strengths of the approach: analysts can inspect the variance explained by each component, check whether trend and seasonal structure remain distinct, and review the decomposition in a way that is both transparent and reproducible. The result is a workflow that supports model development, operational monitoring, and disciplined review without requiring a large number of tuning decisions at every step.

### Model Validation and Observation Logging

This stage focuses on checking whether the decomposition is meaningful and recording the analysis in a way that supports reproducibility and future comparison. The decomposition panel allows analysts to inspect how much variation is explained by each extracted component, compare the decomposition against other smoothing or trend-estimation methods such as LOESS when helpful, and review how the chosen window affects the decomposition itself.

A key part of validation is model comparison. `tseda` uses information criteria such as AIC and BIC to assess whether the choices made during decomposition are statistically reasonable. This is especially useful when comparing alternative window sizes, because the selected window should not only produce a visually coherent decomposition, but also a model that is supported by the data. In practice, the analyst can compare the AIC and BIC values across candidate windows and look for a choice that balances explanatory power with model complexity. A window that yields a much poorer criterion value than nearby alternatives is a strong signal that the decomposition is not well supported by the data.

This is also where observation logging becomes essential. Because the decomposition workflow is iterative, it is important to preserve the reasoning behind each decision: the selected segment, the chosen window, the model comparison results, the diagnostic plots, and the component summaries. These observations provide a traceable record of what was tried, what was rejected, and why a particular decomposition was retained. This matters in domain applications where patterns repeat, staff turnover occurs, and the original reasoning can be lost over time.

The project therefore includes a structured observation framework that supports later review and retrieval through natural-language search. KMDS makes this possible by preserving the rationale and supporting evidence in a searchable form, so future analysts can revisit the decision process quickly and understand not only the final decomposition but also the reasoning behind it. This is especially important in operational settings, where long-lived monitoring pipelines and repeated analyses need an auditable trail of decisions.

In short, this stage is not just a final check; it is a record of analytical judgment. It ensures that the decomposition is not only interpretable, but also defensible, comparable across windows, and easy to revisit later when the underlying process or team context changes.

## Testing and evaluation across real-world datasets

`tseda` has been evaluated on a range of real-world and benchmark datasets to confirm that the decomposition workflow remains useful outside of a single synthetic example. The tested series show a broad spread in explained variance and noise: some datasets, such as coffee prices, have a clear signal and a strong decomposition, while others are more weakly structured and are dominated by residual variation. This is exactly the behavior we would expect from a method designed to separate meaningful structure from noise, and it is a useful validation that the analysis is sensitive to the underlying signal rather than forcing a fixed decomposition onto every dataset.

The Durbin-Watson values for the evaluated datasets remain in the healthy range of approximately 1.5 to 2.5, which supports the view that the residuals are not strongly autocorrelated and that the overall model fit remains stable. To see the full test setup, running instructions, and the complete benchmark summary table, refer to [documents/test_datasets_report.md](documents/test_datasets_report.md). This document provides the detailed record of the test suite and the results used to assess the method across the benchmark set.

## Is there an example showing how to do this?

Yes. A worked example of the full workflow is available in [documents/coffee_example.md](documents/coffee_example.md). It walks through the coffee-prices series from data loading and preliminary diagnostics, through segmentation and final-segment adjustment, to SSA decomposition, validation, and operational interpretation.

A complementary example is [documents/car_sales_example.md](documents/car_sales_example.md). It focuses on a monthly car sales series that displays clear cyclical movement without a fixed seasonal rhythm, which makes it a useful case for understanding trend-cycle behavior and how `tseda` validates the decomposition when the signal is not dominated by a regular seasonal component.

A further example is [documents/biomass_power_gen_example.md](documents/biomass_power_gen_example.md). It examines biomass power generation from the European electricity dataset and shows how a signal can be dominated by evolving trend behavior rather than stable seasonality. This is a useful case for analysts working with renewable-generation data, where structural change and regime shifts can be more informative than a recurring seasonal cycle.

The [white-noise example](documents/white_noise_example.md) illustrates the complementary case: when the eigenspectrum is diffuse and the variance is spread broadly across the spectrum, SSA is not the right tool for the signal. In this situation, `tseda` warns the user that the decomposition is not suitable and recommends switching to a stochastic/noise-based model such as a random-walk/Brownian-motion style approach or an ARIMA/SARIMA workflow.


Notebook parity is effectively 100 percent: everything that can be done in the UI can also be done in the notebook workflow. The notebook API supports the same decomposition, validation, plotting, and reporting steps, so users can reproduce the UI-driven analysis and extend it with custom code. Stay tuned for updated documentation that brings together installation guidance, notebook walkthroughs, and the full UI-to-notebook parity story.

## References

- Killick, R., Fearnhead, P., & Eckley, I. A. (2012). Optimal detection of changepoints with a linear computational cost. Journal of the American Statistical Association, 107(500), 1590-1598. https://doi.org/10.1080/01621459.2012.737745
- Truong, C., Oudre, L., & Vayatis, N. (2020). Selective review of offline change point detection methods. Signal Processing, 167, 107299. https://doi.org/10.1016/j.sigpro.2019.107299
