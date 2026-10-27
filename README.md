# tseda

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

The hard part in practice is not a single plot or statistic. It is the sequence of choices needed to get from raw data to a defensible decomposition: selecting a sensible window, identifying regime boundaries, choosing groups of components, checking whether the result is structurally meaningful, and documenting the reasoning for later reuse.

`tseda` brings those steps together in one workflow.

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

## More information

- [about_tseda.md](about_tseda.md) — fuller product overview and narrative explanation
- [documents/PRODUCT.md](documents/PRODUCT.md) — product and user-value context
- [documents/ARCHITECTURE.md](documents/ARCHITECTURE.md) — system architecture
- [docs/tutorial.md](docs/tutorial.md) — guided walkthroughs
- [docs/user_guide.md](docs/user_guide.md) — detailed usage guidance
