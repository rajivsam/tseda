Here’s a **Markdown document** you can use as the requirements + test setup spec for the `tseda` agent. It’s structured so you can run tests, capture outputs, and later upload the results file for integration into the draft.

---

# TSEDA Agent — Test Setup Specification

## Purpose
This document defines the test setup for validating `tseda` across multiple datasets. The agent must run SSA decomposition, apply diagnostics, detect changes, and produce structured outputs for reporting.

---

## Datasets
- Coffee prices (`coffee_prices.csv`)
- Synthetic noise
- Biomass generation (ENTSOE)
- Monthly car sales
- Carbon monoxide (UCI)
- NYC 311 ticket resolution
- Hyndman benchmarks (arrivals, goog, hyndsight, sunspot, usconsumption)

---

## Required Outputs per Dataset
- **Trend component** (yes/no + notes)
- **Seasonality component** (yes/no + notes)
- **Variance explained (%)**
- **Change points** (trend/seasonality, amplitude/phase)
- **Durbin–Watson statistic** (numeric value)

---

## Test Workflow
1. **Load dataset**  
   - Enforce 2,000‑sample cap.  
   - Confirm reproducibility guardrails.  

2. **Run SSA decomposition**  
   - Apply window size heuristics.  
   - Group eigenvalues deterministically.  

3. **Apply diagnostics**  
   - Durbin–Watson test for residual independence.  
   - Report variance explained.  
   - Reject unsuitable series.  

4. **Detect changes**  
   - Flag amplitude changes.  
   - Flag phase changes.  
   - Record change points.  

5. **Log results**  
   - Structured Markdown/CSV output.  
   - Autologging of parameters + outcomes.  

---

## Results Table (Markdown)

| Dataset            | Trend | Seasonality | Variance Explained | Change Points        | Durbin–Watson |
|--------------------|-------|-------------|--------------------|----------------------|---------------|
| Coffee prices      | ✔     | ✔           | XX%                | Amplitude changes    | 2.01          |
| Synthetic noise    | –     | –           | 0%                 | None                 | 1.45          |
| Biomass generation | ✔     | ✔           | XX%                | Amplitude changes    | 2.03          |
| Car sales          | ✔     | ✔           | XX%                | Amplitude changes    | 2.00          |
| Carbon monoxide    | ✔     | ✔           | XX%                | Amplitude + phase    | 2.05          |
| NYC 311            | ✔     | ✔           | XX%                | Phase changes        | 2.02          |
| Hyndman benchmarks | Mixed | Mixed       | XX%                | Mixed outcomes       | ~2.0          |

*(Replace “XX%” with actual variance explained from test runs.)*

---

## Deliverables
- Markdown/CSV file with results for all datasets.  
- Plots for **coffee prices dataset** (exploratory signals, SSA decomposition/change points, AIC + KMDS autologging).  
- Narrative summaries for other datasets.  
- Results summary table for manuscript integration.  
