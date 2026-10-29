# tseda

<p align="center">
  <img src="assets/images/tseda_logo.png" alt="tseda logo" width="820">
</p>

`tseda` is a Python package for automated time-series decomposition, diagnostics, and signal validation.

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

For bounded random variables, whose values lie within a known range `[a, b]`, concentration inequalities can provide bounds on unusually large observations within a regime. Support for bounding the maximum value of a signal in this way is an upcoming `tseda` feature. Until then, segmentation and variance decomposition still provide practical inputs for monitoring: they make regime changes, changing component behavior, and the level of background noise visible and reviewable.

## How it is used

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
- [White noise example](documents/white_noise_example.md)

## More information

- [about_tseda.md](about_tseda.md) — fuller product overview and narrative explanation
- [documents/coffee_example.md](documents/coffee_example.md) — worked coffee-prices example showing the segment-first workflow, preliminary diagnostics, and final-segment adjustment
- [documents/PRODUCT.md](documents/PRODUCT.md) — product and user-value context
- [documents/ARCHITECTURE.md](documents/ARCHITECTURE.md) — system architecture
- [docs/tutorial.md](docs/tutorial.md) — guided walkthroughs
- [docs/user_guide.md](docs/user_guide.md) — detailed usage guidance
