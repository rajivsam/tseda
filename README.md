# Time Series Explorer (`tseda`)

<p align="center">
	<a href="#non-developer-quick-start">
		<img src="assets/images/tseda_logo.png" alt="tseda banner" width="820">
	</a>
</p>

<p align="center">
	<strong>Time series exploration and decomposition for fast, reliable insights.</strong>
</p>

<p align="center">
	<a href="https://pypi.org/project/tseda/"><img src="https://img.shields.io/pypi/v/tseda" alt="PyPI"></a>
	<a href="https://pypi.org/project/tseda/"><img src="https://img.shields.io/pypi/pyversions/tseda" alt="Python"></a>
	<a href="https://tseda.readthedocs.io/en/latest/"><img src="https://readthedocs.org/projects/tseda/badge/?version=latest" alt="Read the Docs"></a>
	<img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="License: Apache 2.0">
</p>

<p align="center">
	<a href="https://tseda.readthedocs.io/en/latest/"><strong>Read the Docs</strong></a>
</p>

An application for time series exploration.

## Overview

`tseda` lets you explore regularly sampled time series with a sampling frequency of one hour or greater. It is currently limited to 2,000 samples (this is configurable).

## Three-Step Exploration Workflow

### (a) Initial Assessment

Explore the distribution and spread of values using a kernel density estimate and box plot. You get to see the raw distribution of the values. The PACF and ACF provide clues about seasonality and autoregressive components.

### (b) Decomposition Using Singular Spectral Analysis

**Window selection and component grouping are the two hardest decisions when applying SSA.** Choosing the wrong window distorts the eigen spectrum and makes meaningful grouping impossible; grouping the wrong components together conflates trend with seasonality or buries signal in noise. `tseda` automates both steps: it selects a window from the sampling frequency and derives a grouping from the eigen spectrum using a variance-and-correlation heuristic. Expert users can override both — the window via a slider and the grouping via direct input — but the defaults are designed to produce a defensible starting point without manual tuning.

The app first computes an initial SSA window from the detected cadence, then validates whether the eigen spectrum has enough spread. If the smallest eigenvalue still explains too much variance, the window is doubled and SSA is recomputed until the criterion is satisfied (or the SSA half-length bound is reached).

Before any component grouping is attempted, the app also performs a **dataset suitability check** — see below.

| Cadence | Initial Window |
|---------|----------------|
| Hourly  | 24             |
| Daily   | 5              |
| Weekly  | 4              |
| Monthly | 12             |
| Quarterly | 4            |

**Algorithm: Initial SSA Window Setup**

```
Input:  regular time series x, inferred cadence c
Params: min_tail_spread = 0.10

--- Cadence-based initialization ---
1.  If c = hourly  -> w ← 24
2.  If c = daily   -> w ← 5
3.  If c = weekly  -> w ← 4
4.  If c = monthly -> w ← 12
5.  If c = quarterly -> w ← 4
6.  If cadence is unknown -> fail with "invalid window"

--- Spectrum-spread refinement ---
7.  Build SSA(x, w) and compute eigenvalues λ₁ ≥ ... ≥ λ_w
8.  tail_ratio ← λ_w / Σᵢ λᵢ
9.  While tail_ratio ≥ min_tail_spread and 2w ≤ floor(N/2):
    w ← 2w
    Rebuild SSA(x, w)
    tail_ratio ← λ_w / Σᵢ λᵢ

--- Output ---
10. Return final w as the decomposition default and slider value
```

This can be changed in the UI. Based on the eigen value distribution, observations from the ACF plot and the eigen vector plot, the seasonal components can be determined if present. Based on these initial plots, the user needs to input a set of groupings and reconstruct the series with these groupings. The reconstruction plots are shown.

#### Dataset Suitability Check

Before the grouping UI is enabled, `tseda` checks whether the series is structurally suited to SSA decomposition. The check is grounded in a fundamental property of SSA: **meaningful decomposition requires that variance be concentrated in a small number of leading eigenvectors**. When a time series contains real structure — a trend, a seasonal pattern, or both — those components manifest as dominant eigenvectors that together account for a large share of total variance. The remaining eigenvectors represent noise and should contribute comparatively little.

A flat eigenspectrum, where variance is spread roughly equally across many eigenvectors, is the signature of white noise. Applying SSA to such a series produces a decomposition that is mathematically valid but practically meaningless: the algorithm will assign components to Trend and Seasonality groups that are indistinguishable from random fluctuations, and the Durbin-Watson test on the residual will rarely produce a clean pass. Since `tseda` is SSA-focused, unsuitable datasets should be analyzed with external stochastic approaches (for example random walk/Brownian-motion-style models or ARIMA/SARIMA), not with SSA decomposition in this app.

The suitability check is:

```
Params: top_k = 5, min_explained_variance = 0.40

1.  total ← Σᵢ λᵢ
2.  top_k_ratio ← Σᵢ₌₁ᵏ λᵢ / total    (k = min(top_k, spectrum_length))
3.  If top_k_ratio < min_explained_variance:
        Block Apply Grouping
        Display: "Top k eigenvectors explain X% — minimum required Y%"
    Suggest: try external stochastic modelling approaches
4.  Else:
        Proceed with grouping
```

Both `top_k` and `min_explained_variance` are configurable in `tseda_config.yaml` under `suitability_check`. When this check fails, the Apply Grouping button is disabled and a prominent alert explains the actual ratio alongside the threshold, so the user can judge whether to try a different window or accept that a different modelling approach is needed.

**Change point detection** is run automatically after grouping, covering two independent analyses:

- **Trend shifts** — detects permanent changes in the long-run mean level (PELT on the normalised Trend component).
- **Seasonal amplitude shifts** — detects points where the seasonal pattern becomes noticeably stronger or weaker (PELT on the rolling-RMS envelope of the Seasonality component).
- **Noise** — excluded from change-point analysis by design; noise has no persistent structure.

The plot overlays both sets of markers on a single continuous signal line, with a plain-language date summary below. See the [User Guide — Change Point Detection](docs/user_guide.md#change-point-detection) section for the full algorithm and visualisation reference.

The explained variance from signal and noise components and the assessment of the noise structure (independent or correlated) is provided.

The decomposition step now also includes an automatic grouping heuristic. Instead of a fixed explained-variance cutoff, the initial signal pool is selected up to a kneedle-style noise floor detected from the eigen spectrum. Near-equal adjacent pairs within a 5% difference are suggested as seasonality, other components in that pool are suggested as trend, and all remaining components are left to noise. The Durbin-Watson (DW) statistic is then computed on the noise residual; if DW falls outside [1.5, 2.5] the algorithm expands the assignment one component at a time, tracking the assignment closest to DW = 2.0, until the criterion is met or all components are consumed. If the criterion is never met the user is prompted to try a different window size. The UI renders the result as a suggested grouping table, prepopulates the Trend, Seasonality, and Noise inputs, and still lets you override before applying reconstruction. Changing the window size slider re-runs the heuristic automatically.

The **Export Components** action in the decomposition panel is DW-gated: it is enabled only when the current reconstruction has DW in the configured valid range. When enabled, export downloads a CSV with timestamp, Trend, Seasonality, and Noise.

> **Configuration callout:** all constants and heuristics shown here (window mapping, suitability thresholds, grouping tolerances, DW bounds, change-point penalty, etc.) are configurable via [src/tseda/config/tseda_config.yaml](src/tseda/config/tseda_config.yaml).

**Algorithm: SSA Eigenvalue Group Assignment**

```
Input:  eigenvalues λ₁ ≥ λ₂ ≥ ... ≥ λₖ (sorted descending),
        noise residual r
Params: variance_threshold = 0.10, pair_tolerance = 0.05,
        pool_selection_method = "kneedle",
        kneedle_min_distance = 0.03,
        min_signal_components = 1,
        min_noise_components = 2,
        dw_low = 1.5, dw_high = 2.5

--- Initial classification ---
1.  Trend ← ∅;  Seasonality ← ∅
2.  If pool_selection_method = "kneedle":
      a) yᵢ ← log(1 + λᵢ)
      b) Normalize y between first and last points
      c) Compute distance to endpoint chord line
      d) knee ← argmax(distance) if max(distance) ≥ kneedle_min_distance
      e) Eligible ← {0..knee} with bounds:
            min |Eligible| = min_signal_components
            max |Eligible| = K - min_noise_components
    Else (legacy fallback):
      Eligible ← { i : (λᵢ / Σⱼ λⱼ) ≥ variance_threshold }
3.  Noise ← all indices not in Eligible

--- Scan eligible components in rank order ---
4.  cursor ← 0
5.  While cursor < |Eligible|:
      j ← Eligible[cursor]
      k ← Eligible[cursor + 1]  (if it exists)
      if k = j + 1  and  |λⱼ − λₖ| / max(λⱼ, λₖ) ≤ pair_tolerance then
          Seasonality ← Seasonality ∪ { j, k }
          cursor ← cursor + 2
      else
          Trend ← Trend ∪ { j }
          cursor ← cursor + 1

--- Validate with Durbin-Watson ---
6.  r_noise ← r − Σᵢ∈(Trend∪Seasonality) component(i)
7.  dw ← DurbinWatson(r_noise)
8.  best ← current assignment;  best_dist ← |dw − 2.0|

--- Iterative expansion from noise pool ---
9.  While dw ∉ [dw_low, dw_high]  and  |Noise| > 0:
      candidate ← Noise[0]          // largest remaining noise eigenvalue
      next      ← Noise[1]  (if it exists)
      if next = candidate + 1  and  |λ_candidate − λ_next| / max(…) ≤ pair_tolerance then
          Seasonality ← Seasonality ∪ { candidate, next }
          Noise ← Noise \ { candidate, next }
      else
          Trend ← Trend ∪ { candidate }
          Noise ← Noise \ { candidate }
      r_noise ← r − Σᵢ∈(Trend∪Seasonality) component(i)
      dw ← DurbinWatson(r_noise)
      if |dw − 2.0| < best_dist then
          best ← current assignment;  best_dist ← |dw − 2.0|

--- Output ---
10. If dw ∉ [dw_low, dw_high]:
        Return best  with warning "DW criterion not met — try a different window size"
11. Else:
        Return (Trend, Seasonality, Noise)
```

### (c) Observation Logging

The SSA is based on the eigen decomposition of the trajectory matrix. Though the raw signal is correlated, the eigenvectors are uncorrelated. If we assume that the signal is Gaussian, this also implies independence. We can use the Akaike Information Criterion for model selection and determine the AIC as a function of the rank of the model. This is shown in the observation page. An automatic summary of all the observations is provided.

## Notebook Interface

The package also provides a notebook interface to these features. If you have a new dataset that you want to analyze, look at the data loader directory for examples. Download your dataset, clean it, produce your time series, and analyze it with `tseda`.

### Design Philosophy

- **UI and notebook parity**: Anything you can do in the UI should be scriptable in notebooks.
- **Configuration-first behavior**: Runtime thresholds and heuristics are externalized in `src/tseda/config/tseda_config.yaml`.
- **Explicit controls for decomposition**: Window size and component grouping are treated as first-class controls in both UI and Python API.
- **Composable feature calls**: Plotting, decomposition, diagnostics, and reporting are exposed as separate methods so users can build custom analysis flows.

### Developer Notebook API

Use `NotebookThreeStepAPI` for the same three-step workflow directly in Python:

```python
from tseda.notebook_api import NotebookThreeStepAPI, load_series_from_csv

series = load_series_from_csv("data/coffee_prices.csv")
api = NotebookThreeStepAPI(series)

# Step 1: initial assessment
fig_kde = api.get_kde_plot(show_kde=True, bin_algorithm="scott")
fig_acf = api.get_acf_plot(lags=40)

# Step 2: decomposition with explicit window and grouping control
current_window = api.get_window()
api.set_window(current_window, apply_window_refinement=True)
grouping, dw_ok = api.suggest_grouping()
api.set_grouping(grouping=grouping)
fig_recon = api.get_reconstruction_plot()

# Step 3: observation logging outputs
fig_var = api.get_variance_explained_plot()
report_text = api.generate_observation_text()
```

Key notebook API capabilities:

- `get_kde_plot(..., bin_algorithm="scott")` with configurable histogram bin algorithms (`auto`, `fd`, `doane`, `scott`, `stone`, `rice`, `sturges`, `sqrt`).
- `get_window()` / `set_window(...)` for explicit SSA window control.
- `suggest_grouping(grouping_config=...)` / `set_grouping(...)` / `get_grouping()` for explicit component assignment control, including kneedle/noise-floor overrides.
- `suggest_grouping_with_window_autotune(...)` to retry grouping with automatic window reassignment until DW is in range or the window limit is reached.
- `get_grouping_heuristic_configuration()` to inspect active grouping-heuristic config values.
- `get_suitability_result(...)` for the same top-k eigenvalue suitability gate used by the UI.

#### End-to-End Script Example (Copy/Paste)

```python
from pathlib import Path

from tseda.notebook_api import NotebookThreeStepAPI, load_example_series

# Assumes this script runs from the repository root.
workspace_root = Path.cwd()

# Load an example dataset.
series = load_example_series("coffee_prices", workspace_root=workspace_root)
api = NotebookThreeStepAPI(series)

# -------------------------
# Step 1: Initial Assessment
# -------------------------
sampling_df = api.get_sampling_properties()
stats_df = api.get_summary_statistics()
kde_fig = api.get_kde_plot(show_kde=True, bin_algorithm="scott")
acf_fig = api.get_acf_plot(lags=30)
pacf_fig = api.get_pacf_plot(lags=30, method="yw")

# -------------------------
# Step 2: Decomposition
# -------------------------
window_before = api.get_window()
window_after = api.set_window(window_before, apply_window_refinement=True)

suitability = api.get_suitability_result()
if not suitability.is_suitable:
    raise RuntimeError(
        f"Dataset not suitable for SSA: top-{suitability.top_k} ratio "
        f"{suitability.top_k_ratio:.3f} < threshold {suitability.threshold:.3f}"
    )

grouping, dw_ok = api.suggest_grouping()
api.set_grouping(grouping=grouping)

eigen_fig = api.get_eigen_plot()
reconstruction_fig = api.get_reconstruction_plot()
change_point_fig = api.get_change_point_plot()
loess_fig = api.get_loess_plot(fraction=0.10)
noise_kde_fig = api.get_noise_kde_plot(bandwidth="silverman")
recon_meta = api.get_reconstruction_metadata()

# -------------------------
# Step 3: Observation Logging
# -------------------------
variance_fig = api.get_variance_explained_plot()
noise_variance_fig = api.get_noise_variance_plot()
observation_text = api.generate_observation_text()
components_df = api.export_components_dataframe()

print("Window:", window_before, "->", window_after)
print("DW in suggested grouping:", dw_ok)
print("Reconstruction metadata:", recon_meta)
print("Observation preview:\n", observation_text[:500])
print("Components head:\n", components_df.head())
```

#### End-to-End Script Example (Your Own CSV)

```python
from pathlib import Path

from tseda.notebook_api import NotebookThreeStepAPI, load_series_from_csv

# Replace with your own CSV path.
csv_path = Path("/absolute/path/to/your_time_series.csv")

# Default expects: column 0 = timestamp, column 1 = numeric value.
# If your schema is different, pass timestamp_col/value_col as names or indices.
series = load_series_from_csv(csv_path, timestamp_col=0, value_col=1)

api = NotebookThreeStepAPI(series)

# Optional: inspect and adjust decomposition control points.
print("Initial window:", api.get_window())
api.set_window(api.get_window(), apply_window_refinement=True)

grouping, dw_ok = api.suggest_grouping()
api.set_grouping(grouping=grouping)

# Generate core artifacts.
kde_fig = api.get_kde_plot(show_kde=True, bin_algorithm="scott")
reconstruction_fig = api.get_reconstruction_plot()
variance_fig = api.get_variance_explained_plot()
observation_text = api.generate_observation_text()
components_df = api.export_components_dataframe()

print("DW status:", dw_ok)
print(observation_text[:400])
print(components_df.head())
```

## Requirements

**Python 3.13 or higher** is required to run this package.

Before starting the installation, verify your Python version:

```bash
python --version
```

Ensure the output shows Python 3.13 or higher. If not, please upgrade Python before proceeding.

## Install And Run From PyPI

### Recommended: Using Conda

Conda is the recommended package manager for development and installation (development was done with conda):

```bash
conda create -n tseda python=3.13
conda activate tseda
pip install tseda
```

Then run the app:

```bash
tseda
```

## Non-Developer Quick Start

If you just want to run the app with minimal setup:

1. Install with `pipx`:

```bash
pipx install tseda
```

2. Launch the app:

```bash
tseda
```

3. Open your browser at `http://127.0.0.1:8050`.

If `pipx` is not available, use the standard Python install instructions below.

### 1. Install

Verify you have Python 3.13 or higher installed:

```bash
python --version
```

Create and activate a virtual environment, then install from PyPI:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install tseda
```

### 2. Run The Dash App

```bash
tseda
```

You can also launch with Python module execution:

```bash
python -m tseda
```

Note: `python tseda` is not a valid way to run an installed package because Python treats `tseda` as a local script path.

By default, the app starts at `http://127.0.0.1:8050`.

Optional runtime overrides:

```bash
TSEDA_HOST=0.0.0.0 TSEDA_PORT=8050 TSEDA_DEBUG=false tseda
```

### 3. Upload Your Data

- Click **"Drag and Drop or Select Files"** in the Initial Assessment panel.
- Your file must be a **CSV or Excel** file with at least two columns: a **timestamp** column (first) and a **numeric value** column (second).
- The data must be **regularly sampled at hourly or lower frequency** (e.g., hourly, daily, monthly).
- The dataset must contain **no missing values** (NA / NaN). Clean your data before uploading.
- Files are limited to **2,000 rows** (configurable via `file_upload.max_file_lines` in `src/tseda/config/tseda_config.yaml`).

#### Example Datasets (Repository)

Example datasets are available directly in the repository under [data](data). They are intentionally **not bundled** inside wheel/sdist package builds to keep distribution artifacts lean.

Hyndman-based example files:
- [data/hyndman_arrivals_quarterly_japan.csv](data/hyndman_arrivals_quarterly_japan.csv)
- [data/hyndman_goog_daily_close.csv](data/hyndman_goog_daily_close.csv)
- [data/hyndman_hyndsight_daily_pageviews.csv](data/hyndman_hyndsight_daily_pageviews.csv)
- [data/hyndman_sunspot_monthly_area.csv](data/hyndman_sunspot_monthly_area.csv)
- [data/hyndman_usconsumption_quarterly_consumption.csv](data/hyndman_usconsumption_quarterly_consumption.csv)

Additional example files:
- [data/coffee_prices.csv](data/coffee_prices.csv)
- [data/monthly-car-sales.csv](data/monthly-car-sales.csv)
- [data/trimmed_biomass - generated_biomass_MW_series.csv](data/trimmed_biomass%20-%20generated_biomass_MW_series.csv)
- [data/uci_air_quality_hourly_co.csv](data/uci_air_quality_hourly_co.csv)
- [data/ticket_resolution_hourly_nyc311.csv](data/ticket_resolution_hourly_nyc311.csv)
- [data/white_noise_data.csv](data/white_noise_data.csv) — negative example; expected to fail the dataset suitability check

If you install from source (clone the repo), these files are available immediately. If you install from PyPI/package artifacts, download the examples from the repository paths above.

### 4. Explore In Three Steps

| Step | Panel | What to do |
|------|-------|------------|
| 1 | **Initial Assessment of Time Series** | Review distribution plots (KDE, box plot) and the ACF / PACF for autocorrelation patterns. |
| 2 | **Time Series Decomposition** | Review the suggested grouping table, adjust the prepopulated Trend, Seasonality, and Noise inputs if needed, then click **Apply Grouping**. When Durbin-Watson is in range [1.5, 2.5], the **Export Components** button is enabled to download Trend/Seasonality/Noise as CSV. |
| 3 | **Observation Logging** | Review the AIC rank diagnostics, read the auto-generated summary, and add your own observations before saving the report. |

## Development Install (From Source)

If you are developing locally from source:

```bash
pip install -e .
tseda
```

## Build With uv

1. Build source and wheel distributions:

```bash
uv build
```

2. Validate distributions before upload:

```bash
uvx twine check dist/*
```

## Documentation (Sphinx)

### Build locally

```bash
pip install -r docs/requirements.txt
sphinx-build -b html docs/source docs/_build/html
```

You can also use the Makefile:

```bash
make -C docs html
```

The generated site will be available in `docs/_build/html`.

### Publish on Read the Docs

This repository includes `.readthedocs.yaml` configured to build docs from `docs/source/conf.py`.

1. Push the repository to GitHub (or another supported provider).
2. Sign in to Read the Docs and import the project.
3. In Read the Docs project settings:
	- Set the default branch.
	- Confirm the config file path is `.readthedocs.yaml`.
4. Trigger a build from the Read the Docs dashboard.
5. Optionally enable a custom domain and versioned docs.

If the build fails, inspect the Read the Docs build logs and replicate locally using:

```bash
make -C docs html
```

## User Guide

A detailed user guide is available at [`docs/user_guide.md`](docs/user_guide.md). A video version of the user guide is also available on [YouTube](https://youtu.be/baoJrIpSTE8). The written guide covers:

- Data requirements and input format
- Step-by-step walkthrough of all three workflow phases
- Interpreting SSA decomposition outputs (eigenvalue profile, component groupings, Durbin-Watson test)
- Change point detection (trend shifts and seasonal amplitude shifts — see [Change Point Detection](docs/user_guide.md#change-point-detection))
- AIC-based model order selection
- Exporting reports and knowledge base entries
- Configuration guide

## Contributing & Feature Requests

If you'd like to request a feature or report an issue, please [open an issue](https://github.com/rajivsam/tseda/issues) on GitHub. You're also welcome to reach out to me directly.
