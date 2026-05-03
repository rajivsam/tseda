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
6. [Gemini Chatbot](#gemini-chatbot)
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

## Gemini Chatbot

A supplementary Streamlit-based chatbot powered by **Google Gemini 2.5 Flash** is available for in-analysis research and Q&A.

### Setup

Create a `.env` file in the project root containing your API key:

```
GEMINI_API_KEY=your_key_here
```

### Usage

The chatbot can be used to ask questions about your findings, look up domain knowledge, or explore interpretations of the decomposition results. It runs as a separate interface from the main Dash app.

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
| Gemini chatbot | Requires a valid `GEMINI_API_KEY` environment variable |
