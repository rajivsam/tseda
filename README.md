# tseda

<p align="center">
  <img src="assets/images/tseda_logo.png" alt="tseda logo" width="820">
</p>

`tseda` is a Python package for analyst-guided time-series decomposition, diagnostics, and signal validation.

It helps analysts work with regularly sampled operational data by turning raw measurement streams into interpretable components such as trend, seasonality, and noise, while making the underlying analysis steps explicit, repeatable, and reviewable.

For the fuller product story, design rationale, and detailed explanation of the workflow, see [about_tseda.md](about_tseda.md).

## What it helps with

- understanding whether a signal has meaningful structure,
- separating trend and recurring seasonal behavior from residual noise,
- identifying regime changes and shifts in operating behavior,
- deciding whether a series is suitable for decomposition and modeling,
- preserving earlier analytical decisions so they can be revisited and repeated.

## Why it exists

The hard part in practice is not a single plot or statistic. It is the sequence of choices needed (and this is not a few; see [about_tseda.md](about_tseda.md) for the details) to get from raw data to a defensible decomposition: selecting a sensible window, identifying regime boundaries, choosing groups of components, checking whether the result is structurally meaningful, and documenting the reasoning for later reuse.

`tseda` brings those steps together in one workflow.

## Why it is useful?

Variance decomposition is useful not only to modelers, but also to the teams responsible for monitoring and operating systems. Modelers use the extracted behaviors to decide which patterns a forecasting or anomaly-detection model must represent explicitly. Operations teams can use the same information to define alerts and establish guidelines for what behavior is expected from a signal.

Segmentation shows how often a signal changes behavior and identifies the current operating regime. Decomposition then describes that regime in terms of components such as trend, seasonality, and residual noise. Together, these results give an operations team historical evidence about how frequently changes occur, how much variation is normal, and when a signal has moved into a behavior that deserves investigation.

`tseda` has also been evaluated across a range of real-world and benchmark datasets, and the results are encouraging. The proportion of explained variance differs substantially between signals, which is expected given the diversity of operational data being tested. In clearly structured examples such as coffee prices, the decomposition captures a large share of the signal with a strong trend and/or seasonal component. In noisier or more weakly structured cases, the residual noise makes up a much larger share of the series, and the decomposition correctly reflects that difference. This demonstrates that the method is not blindly forcing structure onto every dataset; instead, it identifies the degree to which a signal is informative and interpretable.

The purpose of this evaluation is to show that the approach works across a range of real datasets and produces useful, stable diagnostics rather than a single tuned result. Across the tested benchmark set, the Durbin-Watson statistic remains within the acceptable 1.5 to 2.5 range, indicating that the residuals do not show strong autocorrelation and that the decomposition remains statistically reasonable. Taken together, these checks suggest that `tseda` performs satisfactorily in real-world operational settings and is well suited to structured exploratory analysis, model development, and monitoring workflows.

For bounded random variables, whose values lie within a known range `[a, b]`, concentration inequalities can provide bounds on unusually large observations within a regime. Support for bounding the maximum value of a signal in this way is an upcoming `tseda` feature. Until then, segmentation and variance decomposition still provide practical inputs for monitoring: they make regime changes, changing component behavior, and the level of background noise visible and reviewable.

## How is it used?

`tseda` supports a three-step workflow:

1. initial assessment of the signal,
2. decomposition and grouping of the signal components,
3. validation and observation logging.

The package is designed to work both in a browser-based UI and in Python notebooks, with the same core workflow exposed in both environments.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install tseda
```

Then run:

```bash
tseda
```

## Quick start

```python
from tseda.notebook_api import NotebookThreeStepAPI, load_example_series

series = load_example_series("coffee_prices")
api = NotebookThreeStepAPI(series)

kde_fig = api.get_kde_plot(show_kde=True, bin_algorithm="scott")
acf_fig = api.get_acf_plot(lags=30)

api.set_window(api.get_window(), apply_window_refinement=True)
grouping, dw_ok = api.suggest_grouping()
api.set_grouping(grouping)
recon_fig = api.get_reconstruction_plot()

summary = api.generate_observation_text()
print(summary[:500])
```

## UI Example Illustrations

For examples of using tseda with the UI, please see the following links:

- [Coffee prices example](documents/coffee_example.md)
- [Car sales example](documents/car_sales_example.md)
- [Biomass power generation example](documents/biomass_power_gen_example.md)
- [White noise example](documents/white_noise_example.md)

## Testing

`tseda` has been evaluated across a range of real-world and benchmark datasets, and the results indicate that the workflow performs satisfactorily across heterogeneous time-series conditions. The proportion of explained variance varies considerably between datasets, which is expected when signals differ in their clarity and structure: clearly patterned data such as coffee prices show a strong decomposition, while more irregular or noisy series retain a larger residual component. The objective of this testing is to show that the method works across a range of realistic operating cases and provides actionable diagnostics rather than a single narrowly tuned result.

The Durbin-Watson statistic remains within the healthy 1.5 to 2.5 range across the evaluated datasets, indicating that the residuals do not show strong autocorrelation and that the decomposition remains statistically stable. For the detailed test setup, the generated report, and the full results table, see [documents/test_datasets_report.md](documents/test_datasets_report.md). Interested readers can refer to that document for the exact running instructions and the complete results from the test suite.

## More information

- [about_tseda.md](about_tseda.md) — fuller product overview and narrative explanation
- [documents/coffee_example.md](documents/coffee_example.md) — worked coffee-prices example showing the segment-first workflow, preliminary diagnostics, and final-segment adjustment
- [documents/car_sales_example.md](documents/car_sales_example.md) — trend-cycle example with evolving operating behavior and no fixed seasonal rhythm
- [documents/biomass_power_gen_example.md](documents/biomass_power_gen_example.md) — renewable generation example highlighting non-seasonal trend-driven change
- [documents/PRODUCT.md](documents/PRODUCT.md) — product and user-value context
- [documents/ARCHITECTURE.md](documents/ARCHITECTURE.md) — system architecture
- [docs/tutorial.md](docs/tutorial.md) — guided walkthroughs
- [docs/user_guide.md](docs/user_guide.md) — detailed usage guidance
