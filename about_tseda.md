---
title: "README rewrite brief for tseda"
bibliography: "references.bib"
link-citations: true
---

# What is `tseda` ?


## About tseda
`tseda` is a tool for analyzing operational data from real-world datasets. Its primary goal is to support model development and control (as in operational monitoring and planning) with that data. Forecasting is one example of an application that can benefit from `tseda` analysis. `tseda` can also help teams understand how business processes behave so they can be monitored and managed by technical operations personnel.

For example, an online store may want to understand how customers use the storefront or a specific service, such as the customer address locator. This can be translated into a metric that is sampled, tracked, and analyzed by `tseda`. This helps an operations team understand when particular services are used, when traffic is high and reliable service and a quick response to outages are critical, and when traffic is low enough for maintenance to be scheduled. If the business wants to, it can use this data to build a forecasting model.

In this context, `tseda` can describe the components of a time series that explain the variation in the signal or variable being forecast. This information is important not only to a team that maintains software assets and ensures their reliability, but also to technical teams developing models, such as forecasting models based on time series signals. For example, the same data that a monitoring team uses to understand usage characteristics can be used by a modeling team to predict that signal. A line of business, such as inventory planning, may need to know how a particular resource is consumed so that it can optimize purchasing and storage costs. For such a team, understanding the variance components is important when developing an application and verifying whether the assumptions behind a model remain valid under operating conditions. These examples illustrate the utility of time series analysis for both control and model development purposes. Understanding what happened is usually not developed from a single plot or model. The information needed either for monitoring and control, or to inform model development, is typically built up over time by reviewing a set of statistical plots and developing an intuition for how to decompose the signal.

Several signal decomposition techniques are available. This software uses a method called Singular Spectrum Analysis (SSA). One advantage of this approach is that it requires selecting a single parameter. The interpretation is also intuitive. That parameter is usually chosen iteratively: make a selection, inspect the result, and refine it as needed. Once the selection is reasonably stable, established statistical methods can be used to validate that it gives a near-optimal variance decomposition.

Because this type of analysis is often repeated on a regular schedule, it can be useful to log the observations from each iteration so that historical context is available for future decisions.

`tseda` brings these activities together in a single application interface. In short, it is one tool in your time series toolbox to support your preferred time series analysis, data modeling, and operational monitoring workflows.

The hard part in practice is not any one chart or statistic by itself. It is the fact that getting to a useful decomposition usually requires many steps, many tuning choices, and a careful stitching together of methods: selecting a sampling-aware window, identifying regime boundaries, testing candidate groupings, checking whether the decomposition is structurally meaningful, and then validating the result against the data. These are not isolated decisions; they are part of one analytical workflow. `tseda` is designed to make those choices more explicit, more literature- and practice-grounded, and easier to revisit later. It also makes it possible to log earlier analyses, query them, and repeat or compare them when the same problem reappears with new data.

## How does an analyst use `tseda`?

An analyst starts by launching the `tseda` application and uploading a CSV or similar data file containing two columns: a timestamp and a signal value. At present, `tseda` supports regularly sampled signals only, meaning that the time interval between successive observations is constant. The application infers the sampling period automatically and supports a range of intervals suitable for operational analysis, from short cadence data (for example, 5-minute intervals) to weekly data. The supported range is intended for practical monitoring and forecasting workflows, including use cases spanning roughly 3 months to a year.

The overall workflow is organized into three stages:

### Preliminary Analysis

The goal of this stage is to understand the signal before applying decomposition. The application presents a set of diagnostic views, including:

1. Signal histogram and kernel density estimate: the histogram summarizes where the signal is concentrated, with bin selection defaulting to Scott's rule unless the user explicitly chooses another rule in the notebook interface.
2. Signal box plot: this provides a compact five-number summary of the distribution over the observation window.
3. Raw signal plot: this gives a visual overview of the time series itself and highlights the variation we ultimately want to decompose into a small number of interpretable components.
4. Signal segmentation: the timeline is partitioned into contiguous segments with broadly similar statistical behavior. `tseda` uses change-point detection based on PELT to identify structural changes, such as shifts in level, volatility, or seasonality. Each segment represents a distinct operating regime and helps distinguish stable periods from changes that warrant closer attention.

   The segmentation step is not just descriptive; it shapes the rest of the analysis. For each segment, the system recommends a modeling approach based on the segment’s statistical profile: the linear `l2` model is preferred for trend-dominant or long, stable signals, while the kernelized RBF option is reserved for cases where the seasonal behavior is strongly non-normal, multimodal, or otherwise more complex. This recommendation logic follows the project’s literature review and established modeling guidance, and an advisor feature can explain the rationale in plain language.

   The analyst is not limited to a single segment. `tseda` makes it easy to inspect any regime in the series, and any segment can be selected for follow-up analysis. By default, the most recent segment is highlighted because it usually reflects the current operating conditions, but the interface also allows comparison with earlier segments when the analyst is interested in historical regime changes. This supports both current-state analysis and regime comparison.

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

## Is there an example showing how to do this?

Yes. A more detailed, end-to-end example showing how `tseda` analysis is performed from data upload through preliminary diagnostics, segment decomposition, validation, and interpretation is currently being expanded in the documentation. Detailed installation instructions and notebook-based examples are also coming soon, so readers can follow the same workflow in a reproducible Python environment.

In the meantime, a worked example of time-series analysis in practice is available in this blog post: [Markov analysis of coffee prices](https://rajivsam.github.io/r2ds-blog/posts/markov_analysis_coffee_prices/). It provides a concrete example of how a series is inspected, segmented, and interpreted in context, which is a useful companion to the `tseda` workflow.

Notebook parity is effectively 100 percent: everything that can be done in the UI can also be done in the notebook workflow. The notebook API supports the same decomposition, validation, plotting, and reporting steps, so users can reproduce the UI-driven analysis and extend it with custom code. Stay tuned for updated documentation that brings together installation guidance, notebook walkthroughs, and the full UI-to-notebook parity story.
