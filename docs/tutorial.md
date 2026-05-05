# `tseda` Tutorial for Developers

**Audience:** Mid-level Python developer familiar with pandas and Jupyter notebooks, new to `tseda` and SSA-based time series decomposition.

This tutorial walks through three scenarios that cover the full range of behaviour you will encounter when using the app:

| Scenario | Dataset | Outcome |
|---|---|---|
| 1 — Clean run | `coffee_prices` | Everything works; accept suggested grouping and export |
| 2 — Window adjustment needed | `monthly_car_sales` | Initial window too small; must double it (UI: manual slider; notebook: auto-tune helper) |
| 3 — Unsuitable series | `white_noise_data` | Dataset fails the suitability gate; app explains why |

---

## 1. Installation

**Requirement:** Python 3.13 or higher.

```bash
python --version   # must show 3.13+
```

### Option A — conda (recommended)

```bash
conda create -n tseda python=3.13
conda activate tseda
pip install tseda
```

### Option B — pipx (non-developer quick-start)

```bash
pipx install tseda
```

### Option C — virtual environment

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install tseda
```

### Verify

```bash
tseda --version
```

---

## 2. Launching the UI

```bash
tseda
```

Open [http://127.0.0.1:8050](http://127.0.0.1:8050) in a browser. You will see a file upload area and the three-panel navigation on the left: **Initial Assessment → Decomposition → Observation Logging**.

---

## Scenario 1: Coffee Prices — Clean Run

The daily coffee price series has a clear trend and seasonal structure. The auto-suggested window and grouping both satisfy the Durbin-Watson criterion immediately — no manual intervention needed.

### 1a. UI Walkthrough

**Step 1 — Upload the file**

1. Click **Choose File** on the landing page.
2. Select `data/coffee_prices.csv` from the repository, or upload any two-column CSV (column 0: timestamp, column 1: numeric value).
3. The app parses the file, infers daily cadence, and sets an initial window of **5**.

**Step 2 — Initial Assessment**

The app automatically navigates to the **Initial Assessment** panel. Review:

- **KDE / Histogram** — distribution of values.
- **Box Plot** — spread, outliers.
- **ACF / PACF** — inspect for seasonality structure. For coffee prices you will see decay in the ACF consistent with a trend-driven series.

**Step 3 — Decomposition**

Switch to the **Decomposition** panel.

1. The app has already run window refinement; the slider shows the refined window value (typically **5** for this series).
2. Click **Suggest Grouping**. The algorithm runs the kneedle noise-floor heuristic, assigns Trend and Seasonality components, and evaluates Durbin-Watson on the residual.
3. The suggested grouping table is pre-populated. For example:
   - **Trend:** `[0]`
   - **Seasonality:** `[1, 2]`
   - **Noise:** remaining components
4. The DW badge shows **in range** (green, 1.5 – 2.5). The **Export Components** button is now enabled.
5. Click **Apply Grouping** to render the reconstruction plots.
6. Inspect the **Reconstruction Plot** — the trend and seasonality overlays should track the original series cleanly.
7. Click **Export Components** to download a CSV of Trend, Seasonality, and Noise columns.

**Step 4 — Observation Logging**

Switch to the **Observation Logging** panel to review:

- Variance explained per component.
- Change point markers (trend shifts and seasonal amplitude shifts).
- Auto-generated narrative summary.

---

### 1b. Notebook Walkthrough

Run from the repository root (or set `workspace_root` accordingly).

```python
from pathlib import Path
from tseda.notebook_api import NotebookThreeStepAPI, load_example_series

workspace_root = Path.cwd()

# ── Load the series ───────────────────────────────────────────────────────────
series = load_example_series("coffee_prices", workspace_root=workspace_root)
print(series.head())
# 1990-10-01    0.878
# 1990-10-02    0.870
# ...

# ── Create the API session ────────────────────────────────────────────────────
# apply_window_refinement=True mirrors what the UI does on upload.
api = NotebookThreeStepAPI(series, apply_window_refinement=True)

# ── Step 1: Initial Assessment ────────────────────────────────────────────────
print("Sampling properties:\n", api.get_sampling_properties())
print("Summary statistics:\n", api.get_summary_statistics())

kde_fig   = api.get_kde_plot(show_kde=True, bin_algorithm="scott")
acf_fig   = api.get_acf_plot(lags=30)
pacf_fig  = api.get_pacf_plot(lags=30, method="yw")

kde_fig.show()    # displays inline in Jupyter
acf_fig.show()
pacf_fig.show()

# ── Step 2: Decomposition ─────────────────────────────────────────────────────
print("SSA window:", api.get_window())

# Check suitability before grouping
suitability = api.get_suitability_result()
print(f"Suitable: {suitability.is_suitable}  "
      f"(top-{suitability.top_k} ratio = {suitability.top_k_ratio:.3f}, "
      f"threshold = {suitability.threshold:.3f})")
# Suitable: True  (top-5 ratio = 0.897, threshold = 0.400)

if not suitability.is_suitable:
    raise RuntimeError("Dataset not suitable for SSA — see suitability result above.")

# Auto-suggest grouping; DW is satisfied immediately for this series
grouping, dw_ok = api.suggest_grouping()
print("Suggested grouping:", grouping)
# {'Trend': [0], 'Seasonality': [1, 2], 'Noise': [3, 4, ...]}
print("DW in range:", dw_ok)
# DW in range: True

api.set_grouping(grouping=grouping)

eigen_fig  = api.get_eigen_plot()
recon_fig  = api.get_reconstruction_plot()
cp_fig     = api.get_change_point_plot()

eigen_fig.show()
recon_fig.show()
cp_fig.show()

# ── Step 3: Observation Logging ───────────────────────────────────────────────
variance_fig = api.get_variance_explained_plot()
variance_fig.show()

observation_text = api.generate_observation_text()
print(observation_text)

# Export all components to a DataFrame
components_df = api.export_components_dataframe()
print(components_df.head())
# columns: timestamp, Trend, Seasonality, Noise
```

---

## Scenario 2: Monthly Car Sales — Window Adjustment Needed

Monthly car sales has a clear 12-month seasonal cycle. The default window of **12** produces an eigen spectrum where the smallest eigenvalue still carries too much variance relative to the noise floor, so the DW criterion on the initial grouping is not satisfied. The fix is to double the window to **24**.

### 2a. UI Walkthrough

**Step 1 — Upload the file**

Upload `data/monthly-car-sales.csv`. The app infers monthly cadence and sets the initial window to **12**.

**Step 2 — Initial Assessment**

Review the ACF plot. You will see a strong repeating pattern every 12 lags, confirming an annual seasonal cycle.

**Step 3 — Decomposition (first attempt)**

1. Switch to **Decomposition**.
2. Click **Suggest Grouping**.
3. The heuristic runs and produces a suggested grouping, but the DW badge shows **out of range** (amber or red). A warning message appears below the grouping table:

   > *DW criterion not met — try a different window size.*

4. The **Export Components** button remains disabled because the DW gate is not satisfied.

**Step 4 — Double the window**

1. Locate the **Window Size** slider at the top of the Decomposition panel. It currently shows **12**.
2. Drag the slider to **24** (double the current value).
3. The app automatically re-runs window refinement and re-runs **Suggest Grouping** with the new window.
4. The DW badge now shows **in range**. The grouping table is refreshed with updated component indices.

**Step 5 — Apply and export**

1. Click **Apply Grouping** to render the reconstruction plots.
2. Verify the Seasonality overlay captures the 12-month cycle.
3. Click **Export Components** to download.

---

### 2b. Notebook Walkthrough

The notebook equivalent uses `suggest_grouping_with_window_autotune()`, which handles the doubling loop automatically.

```python
from pathlib import Path
from tseda.notebook_api import NotebookThreeStepAPI, load_example_series

workspace_root = Path.cwd()

series = load_example_series("monthly_car_sales", workspace_root=workspace_root)
api = NotebookThreeStepAPI(series, apply_window_refinement=True)

print("Initial window:", api.get_window())
# Initial window: 12

# ── Check suitability ─────────────────────────────────────────────────────────
suitability = api.get_suitability_result()
print(f"Suitable: {suitability.is_suitable}")
# Suitable: True

# ── First attempt: manual suggest_grouping ────────────────────────────────────
grouping, dw_ok = api.suggest_grouping()
print("DW in range (window=12):", dw_ok)
# DW in range (window=12): False  ← needs adjustment

# ── Auto-tune: doubles window until DW is satisfied ───────────────────────────
result = api.suggest_grouping_with_window_autotune(doubling_factor=2)

print("Reason:         ", result.reason)
# Reason:          dw_satisfied_after_reassignment
print("Windows tried:  ", result.windows_tried)
# Windows tried:   [12, 24]
print("Initial window: ", result.initial_window)
print("Final window:   ", result.final_window)
# Final window:    24
print("DW in range:    ", result.dw_in_range)
# DW in range:     True
print("Durbin-Watson:  ", round(result.durbin_watson, 3))
print("Grouping:       ", result.grouping)

# The result already applied the grouping internally; render plots directly.
recon_fig = api.get_reconstruction_plot()
recon_fig.show()

# Export
components_df = api.export_components_dataframe()
print(components_df.head())
```

**Interpreting `GroupingAutoTuneResult`**

| Field | Meaning |
|---|---|
| `reason` | Terminal status. `"dw_satisfied"` = no retry needed; `"dw_satisfied_after_reassignment"` = window was increased; `"dw_not_satisfied_max_window"` = gave up; `"suitability_failed"` = series unsuitable |
| `windows_tried` | All windows evaluated in order |
| `initial_window` / `final_window` | Before and after auto-tune |
| `dw_in_range` | Whether the final grouping passed the DW gate |
| `durbin_watson` | Final DW statistic value |

---

## Scenario 3: White Noise — Unsuitable Series

White noise has no trend or seasonality; variance is spread uniformly across all eigenvectors. The app detects this via the suitability gate before allowing any grouping.

### 3a. UI Walkthrough

1. Upload `data/white_noise_data.csv`.
2. Switch to **Decomposition**.
3. Click **Suggest Grouping** (or attempt to apply a grouping manually).
4. The suitability check runs. Because the top-5 eigenvectors explain less than 40% of total variance, the app displays a prominent alert:

   > *Top 5 eigenvectors explain X% — minimum required 40%. Apply Grouping is disabled. Consider external stochastic modelling approaches (e.g. random walk, ARIMA/SARIMA).*

5. The **Apply Grouping** button is disabled. No reconstruction is computed.

This is the correct outcome — SSA decomposition on white noise would produce meaningless components.

---

### 3b. Notebook Walkthrough

```python
from pathlib import Path
from tseda.notebook_api import NotebookThreeStepAPI, load_example_series

workspace_root = Path.cwd()

series = load_example_series("white_noise_data", workspace_root=workspace_root)
api = NotebookThreeStepAPI(series, apply_window_refinement=True)

# ── Suitability check ─────────────────────────────────────────────────────────
suitability = api.get_suitability_result()
print(f"Suitable:       {suitability.is_suitable}")
print(f"Top-{suitability.top_k} ratio: {suitability.top_k_ratio:.3f}")
print(f"Threshold:      {suitability.threshold:.3f}")
# Suitable:       False
# Top-5 ratio:    0.217
# Threshold:      0.400

if not suitability.is_suitable:
    print(
        f"\nThis series is not suitable for SSA decomposition.\n"
        f"The top-{suitability.top_k} eigenvectors explain only "
        f"{suitability.top_k_ratio * 100:.1f}% of total variance "
        f"(minimum required: {suitability.threshold * 100:.1f}%).\n"
        f"Recommended: use a stochastic model (e.g. random walk, ARIMA/SARIMA)."
    )

# ── Auto-tune also handles this gracefully ────────────────────────────────────
result = api.suggest_grouping_with_window_autotune()
print("Reason:         ", result.reason)
# Reason:          suitability_failed
print("DW in range:    ", result.dw_in_range)
# DW in range:     False
print("Suitability:    ", result.suitability_passed)
# Suitability:     False
```

When `suggest_grouping_with_window_autotune()` encounters a suitability failure it returns immediately with `reason="suitability_failed"` and an empty grouping — it does not waste time trying window iterations on a fundamentally unsuitable series.

---

## Quick Reference

### Key API methods

```python
from tseda.notebook_api import (
    NotebookThreeStepAPI,
    load_example_series,
    load_series_from_csv,
    list_example_datasets,
)

# List all built-in datasets
print(list_example_datasets())
# ['coffee_prices', 'monthly_car_sales', 'ticket_resolution_hourly_nyc311',
#  'trimmed_biomass', 'uci_air_quality_hourly_co', 'white_noise_data']

# Load your own CSV (column 0 = timestamp, column 1 = value by default)
series = load_series_from_csv("path/to/file.csv", timestamp_col=0, value_col=1)
```

| Method | Returns | Notes |
|---|---|---|
| `NotebookThreeStepAPI(series)` | session object | `apply_window_refinement=True` recommended |
| `get_window()` | `int` | Current SSA window |
| `set_window(w)` | `int` | Rebuilds decomposition |
| `get_suitability_result()` | `SuitabilityResult` | Check before grouping |
| `suggest_grouping()` | `(dict, bool)` | `(grouping, dw_ok)` |
| `suggest_grouping_with_window_autotune()` | `GroupingAutoTuneResult` | Retries with doubled windows |
| `set_grouping(grouping)` | `None` | Apply a custom or suggested grouping |
| `get_reconstruction_plot()` | `go.Figure` | Requires grouping to be set |
| `export_components_dataframe()` | `pd.DataFrame` | DW-gated; raises if DW not in range |
| `generate_observation_text()` | `str` | Auto-generated narrative |
| `get_grouping_heuristic_configuration()` | `dict` | Inspect active config values |

### Grouping override example

If you want to override the kneedle defaults for a specific call (without editing the YAML):

```python
grouping, dw_ok = api.suggest_grouping(
    grouping_config={
        "pool_selection_method": "kneedle",
        "kneedle_min_distance": 0.05,   # stricter knee detection
        "pair_similarity_tolerance": 0.08,
    }
)
```

### All configurable thresholds

All defaults live in `src/tseda/config/tseda_config.yaml`. Key sections:

| Config key | Default | Effect |
|---|---|---|
| `window_refinement.min_tail_spread` | `0.10` | Minimum tail eigenvalue fraction before window doubling |
| `suitability_check.top_k_eigenvectors` | `5` | How many leading eigenvectors are summed |
| `suitability_check.min_explained_variance` | `0.40` | Minimum variance concentration ratio |
| `grouping_heuristic.pool_selection_method` | `"kneedle"` | `"kneedle"` or `"variance_threshold"` |
| `grouping_heuristic.kneedle_min_distance` | `0.03` | Minimum knee distance; smaller = more sensitive |
| `grouping_heuristic.pair_similarity_tolerance` | `0.05` | Eigenvalue proximity for seasonality pairing |
| `grouping_heuristic.dw_low` / `dw_high` | `1.5` / `2.5` | DW valid range |
