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

| Cadence | Default Window |
|---------|---------------|
| Hourly  | 24            |
| Monthly | 12            |
| Quarterly | 4           |

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

#### Eigenvalue / Variance Profile

A bar chart showing the explained variance for each SSA component (eigenvalue rank). Use this to decide how many components to retain.

#### Eigenvector Patterns

Plots of the leading eigenvectors. **Paired eigenvectors** (similar shape, similar eigenvalues) indicate a periodic/seasonal component.

#### Seasonality Heuristic

The app automatically checks whether any pair among the top 6 eigenvalues has a ratio ≥ 0.95. If so, it flags the presence of a likely sinusoidal seasonal component.

#### Weighted Correlation Matrix

A heatmap of correlations between SSA components. Strongly correlated component pairs should be grouped together in the reconstruction step.

#### Component Grouping

Assign SSA components to interpretable groups by entering index ranges (0-based). Typical groupings:

| Group | Example indices | Meaning |
|-------|----------------|---------|
| Trend | `[0, 1]` | Low-frequency trend |
| Seasonality | `[2, 3]` | Dominant periodic component |
| Noise | `[4:]` | Residual / noise |

The app reconstructs the signal for each group and displays the result overlaid on the original series.

#### Durbin-Watson Test

Applied to the noise component to assess residual independence:
- **Value ≈ 2**: residuals are uncorrelated (good).
- **Value < 1.5**: positive autocorrelation remains (consider adding more components to the structured groups).
- **Value > 2.5**: negative autocorrelation.

#### Change Point Detection

The PELT algorithm (`ruptures` library) is applied to smoothed reconstructed components. Detected change points are marked on the signal plot, indicating structural breaks or regime shifts.

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
