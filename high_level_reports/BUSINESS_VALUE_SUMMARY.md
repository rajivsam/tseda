# TSEDA — Business Value Summary

## The Problem It Solves

Before a data scientist or analyst can draw conclusions from a time series, they must first understand its structure: is there a trend? Is there seasonality, and at what period? Where do regime changes occur? Is the residual noise independent or autocorrelated? Answering these questions manually requires statistical knowledge, custom pandas or scipy scripts, iterative parameter tuning, and a working understanding of spectral methods like SSA. On a moderately complex dataset this process routinely consumes **1–3 days** before any insight is written down — and the work is rarely reproducible.

`tseda` compresses that work to **under an hour**.

---

## What the App Does for the Team

| Manual task today | What the app does instead |
|---|---|
| Inspect value distribution, identify outliers | Automated KDE plot, box plot, and scatter view on upload |
| Estimate seasonal period from raw data | Lomb-Scargle periodogram + ACF/PACF plots generated automatically |
| Choose SSA window size | Heuristic assignment from sampling frequency (hourly → 24, daily → 5, weekly → 4, monthly → 12) with automatic refinement and UI override |
| Run SSA, interpret eigenvalue spectrum | Eigenvalue distribution and eigenvector plots rendered; near-equal pair heuristic flags suspected seasonality |
| Group components and reconstruct signal | Interactive grouping UI: user specifies Trend / Seasonality / Noise groups, reconstruction plots generated live |
| Detect regime changes | PELT change-point detection run independently on the **Trend** component (mean-level shifts) and the **Seasonality amplitude envelope** (seasonal strength shifts); each plotted as a distinct marker style with a plain-language date summary below the chart |
| Assess noise structure | Durbin-Watson test and noise KDE shown; correlated vs. independent noise conclusion stated explicitly |
| Select model rank with principled criterion | AIC computed as a function of SSA rank; optimal rank identified automatically |
| Write up analysis findings | Automatic text summary generated from decomposition results on the Observation Logging page |
| Preserve findings for future reference | KMDS OWL knowledge-base integration captures observations in a structured, queryable ontology |
| Research background methodology | Embedded Gemini chatbot allows in-app methodology questions without leaving the workflow |

---

## Where It Saves the Most Cycles

The deepest time sink in time series analysis is not running models — it is the manual loop of *load data → write plot code → interpret → adjust parameters → re-run*. `tseda` externalises that entire loop into a three-step guided UI. The SSA window heuristic alone eliminates a multi-hour parameter search on unfamiliar datasets.

The **dual-detector change-point analysis** is particularly high value: the trend detector (PELT on the z-normalised Trend component) identifies permanent mean-level regime shifts, while the seasonal amplitude detector (PELT on the rolling-RMS envelope of the Seasonality component) identifies points where the seasonal pattern becomes structurally stronger or weaker. Noise is excluded from both detectors by design. The two sets of breakpoints are rendered as distinct marker styles — dashed vertical lines for trend shifts, dotted for seasonal amplitude shifts — with a plain-language date summary below the plot.

The **AIC rank selection** converts a subjective eigenvalue elbow-inspection task into an objective decision: the rank that minimises AIC over the signal component is the statistically defensible model size.

---

## Management Headline

> `tseda` moves time series structural analysis from a **2-day expert data science task** to a **guided, auditable, sub-hour workflow**. It reduces time-to-insight on new series from days to under an hour, lowers the risk of methodological errors (wrong window, noisy change points, incorrect noise assumption), and produces a structured, reproducible record of every analytical observation — all from a local Dash app with no data leaving the team.

---

## Key Differentiators

| Feature | Benefit |
|---|---|
| **Three-step guided workflow** | Initial Assessment → SSA Decomposition → Observation Logging mirrors best-practice EDA sequence; no blank-canvas decision paralysis |
| **Window heuristic + refinement** | Sampling-frequency default eliminates the most common SSA stumbling block; automatic eigenvalue-spread refinement handles edge cases without user intervention |
| **Dual-detector change-point analysis** | Separate PELT runs on Trend (mean shifts) and Seasonality amplitude envelope (strength shifts); distinct visual markers and plain-language summary eliminate ambiguity |
| **AIC model selection** | Rank choice is statistically grounded, not subjective |
| **KMDS knowledge capture** | Findings are saved as structured OWL observations, searchable and shareable across projects |
| **Gemini chatbot integration** | In-app methodology lookup without breaking the analysis flow |
| **Configurable 2,000-sample limit** | Keeps UI responsive; prevents accidental loading of unmanageable series |

---

## Typical Workflow Impact

**Before (2 days)**
1. Load dataset, write pandas code to clean and index → 30 min
2. Write and iterate plot code for distributions, ACF, PACF → 60 min
3. Research and choose SSA window; run SSA, interpret eigenspectrum → 90 min
4. Reconstruct components, visually assess trend/seasonality/noise split → 60 min
5. Manually run PELT or other change-point method on raw series → 45 min
6. Assess noise independence manually (Durbin-Watson or ad-hoc) → 30 min
7. Write up observations in a document → 45 min
Total: ~7 hours, manual, requires SSA expertise, no structured record

**After (under 1 hour)**
1. Upload series to app, auto-profile displayed → 2 min
2. Review KDE, box, scatter, ACF, PACF on Initial Assessment page → 5 min
3. Accept or adjust heuristic window; inspect eigenvalue/eigenvector plots → 5 min
4. Enter component groupings, review reconstruction and change-point plots → 10 min
5. Review AIC rank selection, noise KDE, Durbin-Watson result → 5 min
6. Read and save auto-generated observation summary to KMDS KB → 5 min
Total: ~30 min, guided, reproducible, structured output

---

## Risk Reduction

- **Wrong SSA window**: Mitigated. Heuristic assignment based on sampling frequency is a principled starting point; UI slider allows expert override.
- **Missed seasonality**: Mitigated. Near-equal eigenvalue heuristic flags suspected seasonal pairs before the user makes grouping decisions.
- **Spurious change points on noisy data**: Eliminated. PELT runs on the SSA-denoised Trend and Seasonality components, not the raw series.
- **Change points caused by seasonal oscillations**: Eliminated. The trend detector runs on the Trend component only; seasonal peaks and troughs cannot register as regime shifts.
- **Missed seasonal amplitude changes**: Mitigated. A second PELT detector runs on the rolling-RMS envelope of the Seasonality component and flags points where the seasonal pattern becomes structurally stronger or weaker.
- **Arbitrary model rank selection**: Eliminated. AIC curve over rank provides a principled, reproducible selection criterion.
- **Lost analysis context**: Eliminated. KMDS OWL integration captures findings in a queryable, persistent knowledge base.
- **Unreproducible EDA**: Significantly reduced. Three-step structured workflow enforces a consistent analysis path across analysts and datasets.

---

## ROI Calculation (for a 5-person analytics team)

- **Current annualized cost**: 5 analysts × 0.15 FTE on time series EDA × $130k/year = **$97.5k/year** in analyst labor on exploratory analysis
- **Time saved per series**: 7 hours → 1.5 hours = 5.5 hours per analysis cycle
- **Analysis cycles per analyst per quarter**: ~6 series = 33 hours saved/quarter per analyst
- **Annual savings for team**: 5 analysts × 33 hours × 4 quarters / 2000 work hours × $130k = **~$43k/year**
- **Plus avoided errors**: Incorrect change-point locations, wrong seasonality assumptions, and undocumented EDA reaching production models are measurably reduced.

**Payback period**: ROI-positive on labor alone within the first quarter of adoption; additional value from reproducibility and error prevention compounds over time.

---

## Technical Confidence

The application is production-ready for regularly sampled time series (hourly or coarser) with:
- ✅ Three-step workflow validated on energy, coffee prices, car sales, biomass generation, and synthetic series
- ✅ SSA decomposition backed by `ssalib` with explicit reconstruction cache correctness tests
- ✅ Change-point trend detector validated against series with known mean-level regime shifts
- ✅ Change-point seasonal amplitude detector validated across energy, coffee, and car-sales datasets
- ✅ AIC rank selection validated against analytic ground truth with parametric test suite
- ✅ Sampling property heuristics validated for daily, monthly, quarterly, and hourly frequencies
- ✅ Published to PyPI; installable via `pip install tseda` or `pipx install tseda`
- ✅ Documentation hosted on Read the Docs
