<div align="center">

<img src="../assets/images/tseda_logo.png" alt="tseda logo" width="220"/>

# tseda User Guide

**Time Series Explorer & Decomposition App**

Version 0.1.7 &nbsp;|&nbsp; April 2026

---

</div>

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Running the App](#running-the-app)
4. [Data Requirements](#data-requirements)
5. [Workflow](#workflow)
   - [Step 1 — Initial Assessment](#step-1--initial-assessment)
   - [Step 2 — SSA Decomposition](#step-2--ssa-decomposition)
   - [Step 3 — Observation Logging & Export](#step-3--observation-logging--export)
6. [Configuration](#configuration)
7. [Knowledge Base Export](#knowledge-base-export)
8. [Limitations](#limitations)

---

## Overview

`tseda` is an interactive, browser-based tool for exploratory analysis of regularly sampled time series data. It is designed for analysts working with data at **hourly cadence or lower** (daily, monthly, quarterly, etc.) and guides you through a structured three-phase process:

1. **Initial assessment** — upload your data, inspect its statistical properties, and understand its autocorrelation structure.
2. **SSA decomposition** — apply Singular Spectrum Analysis (SSA) to separate the series into trend, seasonal, and noise components.
3. **Observation logging** — review auto-generated narrative summaries, annotate your findings, and export results.

---

## Installation

### Recommended (conda + pip)

```bash
conda create -n tseda python=3.13
conda activate tseda
pip install tseda
```

### pipx (for non-developer use)

```bash
pipx install tseda
```

### From source (developer)

```bash
git clone <repo-url>
cd tseda
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Running the App

After installation, launch `tseda` from the command line:

```bash
tseda
```

Or equivalently:

```bash
python -m tseda
```

The app starts a local Dash web server and opens automatically in your default browser. No arguments are required.

---

## Data Requirements

`tseda` expects a **CSV or Excel file** in long (tidy) format with:

| Column | Description |
|--------|-------------|
| Column 1 | Timestamps — must be parseable as dates/datetimes |
| Column 2 | Numeric values — the time series variable |

Additional requirements:

- **Regular cadence**: the sampling interval must be uniform and inferable (e.g., daily, monthly, quarterly, hourly).
- **No missing values**: gaps in the series are not supported.
- **Maximum 2,000 rows**: longer files will be rejected.
- The file must have at least two columns; only the first two are used.

Example valid formats: daily sales data, monthly energy consumption, quarterly GDP, hourly sensor readings.

---

## Workflow

### Step 1 — Initial Assessment

Upload your CSV or Excel file using the file upload control. The app parses the file and displays:

#### Sampling Metadata Table

A summary table showing:
- **N**: number of observations
- **Start / End**: date range of the series
- **Duration**: total time span
- **Inferred frequency**: e.g., "Monthly", "Daily"
- **Heuristic SSA window**: a suggested window size for decomposition based on the detected cadence

| Cadence | Initial Window |
|---------|----------------|
| Hourly  | 24             |
| Daily   | 5              |
| Weekly  | 4              |
| Monthly | 12             |

#### Distribution Plot (KDE + Box Plot)

A kernel density estimate (KDE) overlaid with a box plot of the raw values. Use this to:
- Assess the central tendency and spread.
- Identify multi-modality (multiple peaks may indicate regime changes or mixed populations).

#### Raw Signal Plot

A scatter/line plot of the full time series, letting you visually inspect trends, seasonality, outliers, and structural breaks.

#### ACF and PACF Plots

Autocorrelation Function (ACF) and Partial ACF plots computed via `statsmodels`. These reveal:
- **Slow decay in ACF**: trend component present.
- **Seasonal spikes**: periodicity at regular lags.
- **PACF cutoff**: guides autoregressive model order if needed.

---

### Step 2 — SSA Decomposition

SSA decomposes the series into a set of components ranked by their contribution to total variance (explained by eigenvalues).

#### Adjusting the Window

The app pre-selects a window size based on the detected cadence. You can adjust it manually. A good rule of thumb:
- The window should be at least as long as the expected seasonal period.
- Larger windows capture longer-range structure but increase computation.

#### Initial Window Setup Heuristic

Before grouping, the app computes a cadence-based initial window and then applies an
eigen-spectrum spread check. The goal is to avoid starting with a window where the
smallest eigenvalue still explains too much variance.

```
Algorithm: Initial SSA Window Setup

Input:  regular time series x, inferred cadence c
Params: min_tail_spread = 0.10

--- Cadence-based initialization ---
1.  If c = hourly  -> w ← 24
2.  If c = daily   -> w ← 5
3.  If c = weekly  -> w ← 4
4.  If c = monthly -> w ← 12
5.  If cadence is unknown -> fail with "invalid window"

--- Spectrum-spread refinement ---
6.  Build SSA(x, w) and compute eigenvalues λ₁ ≥ ... ≥ λ_w
7.  tail_ratio ← λ_w / Σᵢ λᵢ
8.  While tail_ratio ≥ min_tail_spread and 2w ≤ floor(N/2):
   w ← 2w
   Rebuild SSA(x, w)
   tail_ratio ← λ_w / Σᵢ λᵢ

--- Output ---
9.  Return final w as the decomposition default and slider value
```

Operationally, this means the startup window can be larger than the raw cadence mapping
if the first decomposition is too flat in the tail. The UI slider is synchronized to
this final value.

#### Eigenvalue / Variance Profile

A bar chart showing the explained variance for each SSA component (eigenvalue rank). Use this to decide how many components to retain.

#### Eigenvector Patterns

Plots of the leading eigenvectors. **Paired eigenvectors** (similar shape, similar eigenvalues) indicate a periodic/seasonal component.

#### Dataset Suitability Check

Before the grouping controls are activated, the app automatically checks whether this series is structurally suited to SSA decomposition.

**Why this check exists.** SSA decomposes a series by finding a small number of dominant directions (eigenvectors) that capture most of the variance. This works well when the series has real structure — a trend pulling values in a consistent direction, or a seasonal oscillation repeating at a known period. Those structures produce large, concentrated eigenvalues at the top of the spectrum. The remaining eigenvectors, which correspond to noise, are small and comparably sized.

When a series is dominated by noise — white noise, a random walk with no drift, or any process without persistent structure — the eigenspectrum looks completely different: variance is spread roughly equally across all eigenvectors. No single component stands out. Applying SSA to such a series still produces a mathematically valid result, but the Trend and Seasonality groups it generates are statistical artefacts rather than meaningful signal components. The decomposition cannot be trusted, and the Durbin-Watson check on the noise residual will rarely give a clean result because there is no coherent structure left to separate.

The suitability check quantifies this directly: it sums the explained variance of the top `k` eigenvectors and requires that sum to reach a minimum threshold. If it does not, the Apply Grouping button is disabled and a red alert explains what was found:

```
Params: top_k = 5, min_explained_variance = 0.40

1.  total      ← Σᵢ λᵢ
2.  k          ← min(top_k, spectrum_length)
3.  top_k_ratio ← Σᵢ₌₁ᵏ λᵢ / total
4.  If top_k_ratio < min_explained_variance:
        → Block Apply Grouping
        → Show: "Top k eigenvectors explain X.X% — minimum required Y%"
        → Recommend: noise-based modelling (ARIMA / SARIMA)
5.  Else:
        → Allow grouping to proceed
```

The alert reports the **actual ratio** alongside the threshold so you can judge whether the dataset is marginally below the cutoff (and perhaps worth trying with a different window) or deeply unsuitable. Both `top_k` and `min_explained_variance` are configurable — see [Section 10 of the Configuration reference](#10-dataset-suitability-check).

**What to do if the check fails:**
- Try a larger SSA window using the slider. Sometimes a cadence-based default window is too small to reveal seasonal structure.
- Inspect the eigenvalue profile plot — if the bars form a steep drop-off rather than a flat line, the series may still be worth exploring at a different scale.
- If the spectrum remains flat at all window sizes, the series is most likely noise-dominated. Consider ARIMA/SARIMA modelling instead of SSA decomposition.

#### Seasonality Heuristic

The automatic grouping heuristic assigns each SSA component to Trend, Seasonality,
or Noise using the following procedure:

```
Algorithm: SSA Eigenvalue Group Assignment

Input:  eigenvalues λ₁ ≥ λ₂ ≥ ... ≥ λₖ (sorted descending),
      noise residual r
Params: variance_threshold = 0.10, pair_tolerance = 0.05,
      dw_low = 1.5, dw_high = 2.5

--- Initial classification ---
1.  total  ← Σᵢ λᵢ
2.  For each i: vᵢ ← λᵢ / total           // explained variance ratio
3.  Eligible ← { i : vᵢ ≥ variance_threshold }
4.  Noise   ← { i : vᵢ < variance_threshold }
5.  Trend ← ∅;  Seasonality ← ∅

--- Scan eligible components in rank order ---
6.  cursor ← 0
7.  While cursor < |Eligible|:
     j ← Eligible[cursor]
     k ← Eligible[cursor + 1]  (if it exists)
     if k = j + 1  and  |λⱼ − λₖ| / max(λⱼ, λₖ) ≤ pair_tolerance then
        Seasonality ← Seasonality ∪ { j, k }
        cursor ← cursor + 2
     else
        Trend ← Trend ∪ { j }
        cursor ← cursor + 1

--- Validate with Durbin-Watson ---
8.  r_noise ← r − Σᵢ∈(Trend∪Seasonality) component(i)
9.  dw ← DurbinWatson(r_noise)
10. best ← current assignment;  best_dist ← |dw − 2.0|

--- Iterative expansion from noise pool ---
11. While dw ∉ [dw_low, dw_high]  and  |Noise| > 2:
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
12. If dw ∉ [dw_low, dw_high]:
      Return best  with warning "DW criterion not met — try a different window size"
13. Else:
      Return (Trend, Seasonality, Noise)
```

#### Weighted Correlation Matrix

A heatmap of correlations between SSA components. Strongly correlated component pairs should be grouped together in the reconstruction step.

#### Component Grouping

The app first renders a **Suggested Grouping** table in the center of the decomposition panel and prepopulates the input rows for **Trend**, **Seasonality**, and **Noise** using the heuristic above. You can edit those values before reconstruction if the diagnostic plots or domain context suggest a different interpretation.

Assign SSA components to interpretable groups by entering index ranges (0-based). Typical groupings:

| Group | Example indices | Meaning |
|-------|----------------|---------|
| Trend | `[0, 1]` | Low-frequency trend |
| Seasonality | `[2, 3]` | Dominant periodic component |
| Noise | `[4:]` | Residual / noise |

The app reconstructs the signal for each group and displays the result overlaid on the original series.

If you click **Clear Uploaded File** in Step 1, the suggested grouping table and the prepopulated grouping fields are reset with the rest of the session analysis state.

#### Durbin-Watson Test

Applied to the noise component to assess residual independence:
- **Value ≈ 2**: residuals are uncorrelated (good).
- **Value < 1.5**: positive autocorrelation remains (consider adding more components to the structured groups).
- **Value > 2.5**: negative autocorrelation.

---

## Change Point Detection

After applying the reconstruction grouping, the app runs a change-point analysis that independently examines **trend shifts** and **seasonal amplitude shifts**. Noise is excluded from this analysis: by definition, noise has no persistent structure and is not a source of meaningful change points.

### What is analysed and what is not

| Component | Analysed? | Rationale |
|-----------|-----------|----------|
| Trend | ✅ Yes | Persistent mean-level shifts are the primary structural break of interest. |
| Seasonality | ✅ Yes (amplitude envelope) | Changes in how strong the seasonal pattern is (e.g. seasonality growing or shrinking) are detected. Phase/frequency shifts are not — see note below. |
| Noise | ❌ No | Noise is by construction structureless; running a change-point detector on it would produce spurious breaks. |

> **Phase and frequency shifts** are not detected by the current algorithm. Detecting period changes robustly requires either a sliding-window FFT or a Hilbert-transform instantaneous frequency approach; both are noisy on short series (< 200 points) and are not implemented here.

---

### Detector 1 — Trend shifts

Detects points where the long-run mean level of the series changes permanently.

```
Input:  Trend component from the SSA reconstruction

1. Z-score normalise the trend:
       z[t] = (trend[t] − mean(trend)) / std(trend)
   Normalisation makes the penalty scale-invariant across datasets
   with very different value ranges.

2. Fit PELT (ruptures, l2 cost model) with a BIC-style penalty:
       penalty = log(n)
   where n is the series length.

3. Collect interior breakpoints (PELT appends n as a sentinel;
   discard it). These are the trend-shift indices.
```

**Visualisation:** vertical `- - -` dashed lines, labelled **T1, T2, …** at the top of the plot.

---

### Detector 2 — Seasonal amplitude shifts

Detects points where the *strength* of the seasonal pattern changes (the seasonal oscillations become noticeably larger or smaller).

```
Input:  Seasonality component from the SSA reconstruction

1. Compute the rolling RMS envelope over a window w equal to the
   SSA window size (captures one nominal seasonal cycle):
       envelope[t] = sqrt( mean( seasonality[t-w/2 : t+w/2]² ) )
   This converts the oscillating seasonality signal into a smooth
   amplitude envelope.

2. Z-score normalise the envelope (same reason as for the trend).

3. Fit PELT (ruptures, l2 cost model) with penalty = log(n).

4. Collect interior breakpoints. These are the seasonal-amplitude-
   shift indices.
```

**Visualisation:** vertical `···` dotted lines, labelled **S1, S2, …** at the bottom of the plot.

---

### Reading the plot

The smoothed signal (trend + all non-noise components) is drawn as a single continuous line — it is never broken at a segment boundary. The two sets of markers are visually distinct:

| Marker style | Label | Meaning |
|---|---|---|
| Vertical `- - -` dashed line | T1, T2, … | The trend mean shifted here |
| Vertical `···` dotted line | S1, S2, … | The seasonal amplitude changed here |

A plain-language summary is printed below the plot, for example:

```
Trend shifts (- -): 2026-11-29, 2027-02-07
Seasonal amplitude shifts (···): 2026-10-25, 2026-11-29, 2027-02-07
```

If no changes are detected for a component the line reads `none detected`.

When a trend-shift date and a seasonal-amplitude-shift date coincide, both a dashed and a dotted line will appear at the same x position, indicating a simultaneous structural regime change in both the level and the seasonal strength.

---

### Step 3 — Observation Logging & Export

#### AIC-by-Rank Table and Plot

For each candidate model rank $r$ (number of retained SSA components), the app computes:

$$\text{AIC}_r = N \log(\hat{\sigma}^2_r) + 2r$$

where $\hat{\sigma}^2_r$ is the residual variance at rank $r$ and $N$ is the series length. The rank that minimises AIC provides a principled guide to model order selection.

#### Auto-Generated Narrative

The app produces a prose summary combining:
- Sampling metadata and descriptive statistics (mean, median, std, skewness, kurtosis)
- SSA findings (dominant components, seasonality flag)
- Residual diagnostics (Durbin-Watson result)
- Change point locations

#### Editing the Report

The narrative is editable in the app. Add your own observations, domain context, or caveats before exporting.

#### Exporting

The finalised report can be exported as a plain text file for documentation or sharing.

#### Saving Observations to a Knowledge Base

Use **Save to Knowledge Base** in the Observation Logging step to persist observations
to a KMDS OWL/RDF file.

When entering the save location:

- The app validates that the directory exists.
- The app validates that the current user has sufficient write privileges.
- If validation fails, a clear error is shown and the Save button is disabled.
- The app blocks save attempts to invalid or non-writable locations.

The selected directory and file name are stored in app state during the session and
are reset when you click **Clear Uploaded File** in Step 1.

---

## Configuration

`tseda` uses an externalized configuration file to manage thresholds, parameters, and limits across the application. This allows you to customize algorithm behavior without modifying code.

### Configuration File Location

The configuration file is stored at: `src/tseda/config/tseda_config.yaml`

When the application starts, it automatically loads this configuration into memory. You can modify any settings in this file to customize the application behavior.

### Configuration Sections

#### 1. File Upload Limits

```yaml
file_upload:
  max_file_lines: 2000  # Maximum rows allowed in uploaded CSV/Excel files
```

**Default:** `2000` rows
**Suggested range:** 1,000 – 5,000
**Purpose:** Prevents memory exhaustion from very large files and maintains UI responsiveness.

#### 2. Window Selection (Cadence-to-Window Mapping)

```yaml
window_selection:
  hourly: 24    # One diurnal cycle
  daily: 5      # One business week
  weekly: 4     # Approximately one month
  monthly: 12   # One full annual cycle
```

**Default values:** As listed above
**Purpose:** Provides initial SSA window sizes based on detected sampling frequency. Values represent one expected seasonal cycle at each cadence.

#### 3. SSA Eigenvalue Grouping Heuristic

```yaml
grouping_heuristic:
  variance_threshold: 0.10           # Minimum explained variance ratio to classify as "eligible"
  pair_similarity_tolerance: 0.05    # Maximum allowed difference (as fraction) for paired eigenvalues
```

**Variance threshold:**
  - **Default:** `0.10` (10%)
  - **Range:** `0.05` – `0.20`
  - **Purpose:** Components explaining less than this fraction of total variance are classified as noise.

**Pair similarity tolerance:**
  - **Default:** `0.05` (5%)
  - **Range:** `0.02` – `0.10`
  - **Purpose:** When two adjacent eigenvalues differ by ≤ this fraction, they are paired and assigned to seasonality.

#### 4. Durbin-Watson Noise Quality Check

```yaml
noise_validation:
  dw_low: 1.5    # Minimum acceptable Durbin-Watson statistic
  dw_high: 2.5   # Maximum acceptable Durbin-Watson statistic
```

**Default range:** `[1.5, 2.5]`
**Suggested range:** `[1.4, 2.6]`
**Purpose:** The Durbin-Watson (DW) statistic measures autocorrelation in the noise residual. A value near 2.0 indicates uncorrelated noise; values outside this range suggest residual autocorrelation that should be addressed by adjusting component grouping.

#### 5. Window Refinement

```yaml
window_refinement:
  min_tail_spread: 0.10    # Minimum acceptable smallest eigenvalue (as fraction of total variance)
```

**Default:** `0.10` (10%)
**Suggested range:** `0.05` – `0.15`
**Purpose:** After initial window selection, the algorithm checks if the smallest eigenvalue explains too much variance. If it does, the window is doubled and SSA is recomputed until this invariant is satisfied or the half-length bound is reached. This ensures the eigenvalue spectrum has meaningful spread.

#### 6. SSA Seasonality Heuristic

```yaml
seasonality_heuristic:
  leading_eigenvalues_to_check: 6    # Number of top eigenvalues inspected for paired structure
```

**Default:** `6`
**Suggested range:** `4` – `12`
**Purpose:** When deciding whether to flag the series as seasonal, the algorithm examines the top N eigenvalues for paired (near-equal) structure. Higher values inspect more components.

#### 7. FFT / Periodicity Analysis

```yaml
periodicity:
  fmin: 0.1          # Minimum search frequency (cycles per sample)
  fmax: 2.0          # Maximum search frequency (cycles per sample)
  num_frequencies: 1000  # Number of discrete frequency points to evaluate
```

**fmin / fmax:**
  - **Default:** `0.1` – `2.0`
  - **Purpose:** Defines the frequency range for Lomb-Scargle periodogram analysis.

**num_frequencies:**
  - **Default:** `1000`
  - **Suggested range:** `500` – `2000`
  - **Purpose:** Higher values give finer frequency resolution but increase computation cost.

#### 8. LOESS Smoothing

```yaml
loess:
  min_fraction: 0.05     # Minimum smoothing fraction (data points to use per local regression)
  max_fraction: 0.5      # Maximum smoothing fraction
  default_fraction: 0.05 # Default value shown in the UI slider
  step: 0.05             # Slider increment
```

**Default values:** As listed above
**Purpose:** The LOESS smoother uses a sliding-window local regression. The fraction parameter controls the width of each window; lower values produce noisier but more detailed curves, while higher values produce smoother curves that may hide detail.

#### 9. Change Point Detection

```yaml
change_point_detection:
  model: "rbf"   # Cost model for PELT algorithm ("rbf", "l2", "linear")
  penalty_multiplier: 2.0  # Multiplier for BIC-style penalty = penalty_multiplier * log(n)
```

**Model:**
  - **Default:** `"rbf"`
  - **Options:** `"rbf"`, `"l2"`, `"linear"`
  - **Purpose:** Defines the cost function used by the PELT algorithm. "rbf" (radial basis function) is robust and recommended for most time series.

**Penalty multiplier:**
  - **Default:** `2.0` (yields BIC penalty = 2 * log(n))
  - **Suggested range:** `1.5` – `2.5`
  - **Purpose:** Higher values discourage finding many small segments (conservative), while lower values permit more breakpoints (liberal).

#### 10. Dataset Suitability Check

```yaml
suitability_check:
  top_k_eigenvectors: 5       # Number of leading eigenvectors to sum for the concentration test
  min_explained_variance: 0.40  # Minimum fraction of total variance the top-k must explain
```

**top_k_eigenvectors:**
  - **Default:** `5`
  - **Suggested range:** `3` – `8`
  - **Purpose:** Defines how many leading eigenvectors are summed for the suitability check. A value of 5 is a reasonable default for most series — it covers one trend component and up to two seasonal pairs. For series with complex multi-period seasonality (e.g. hourly data with daily and weekly cycles), you may want to raise this to 7 or 8.

**min_explained_variance:**
  - **Default:** `0.40` (40%)
  - **Suggested range:** `0.30` – `0.55`
  - **Purpose:** The minimum fraction of total variance the top-k eigenvectors must collectively explain. If the actual ratio falls below this threshold, the series is deemed unsuitable for SSA and the Apply Grouping button is disabled. Raising this threshold makes the check stricter (only highly structured series pass); lowering it is more permissive and appropriate if your series has moderate but real structure diluted by heavy noise.

**Example: relaxing the check for a noisy-but-structured series:**

```yaml
suitability_check:
  top_k_eigenvectors: 6
  min_explained_variance: 0.30  # Allow series where top-6 explain at least 30%
```

### Modifying Configuration

1. Open `src/tseda/config/tseda_config.yaml` in a text editor.
2. Modify any values in the appropriate section.
3. Save the file.
4. Restart the `tseda` application. Configuration is loaded at startup.

### Example: Adjusting the Durbin-Watson Range

If you find that the automatic component grouping rarely satisfies the DW criterion on your datasets, try relaxing the bounds:

```yaml
noise_validation:
  dw_low: 1.4   # Relaxed from 1.5
  dw_high: 2.6  # Relaxed from 2.5
```

This will allow groupings with slightly more residual autocorrelation to be accepted.

---

## Knowledge Base Export

`tseda` can persist your exploratory observations to an **OWL/RDF knowledge base** using the `kmds` and `owlready2` libraries. This is designed for teams that maintain a structured, machine-readable log of analytical findings.

- Observations are appended to a `.xml` OWL file.
- Existing observations can be deleted from the UI.
- The knowledge base can accumulate findings across multiple analysis sessions.
- Save-location validation prevents writing to non-existent or privilege-restricted
   directories and prompts you to choose a valid location.

---

## Limitations

| Constraint | Detail |
|------------|--------|
| Maximum series length | 2,000 rows |
| Sampling cadence | Must be regular and inferable; gaps not supported |
| Input format | CSV or Excel with timestamp + numeric value columns only |
| Frequency range | Hourly cadence or lower (sub-hourly not supported) |
| Missing values | Not supported |
