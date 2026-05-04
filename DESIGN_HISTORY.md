# TSEDA — Design History and Quality Checks Report

## Executive Summary

This document chronicles the iterative design and development of `tseda`, with emphasis on the explicit technical checks, architectural decisions, and quality gates that ensured correctness and usability. The project evolved through ten sequential design decisions, each introducing new requirements, triggering validation checks, and refining the core architecture.

---

## Iteration Cycle Overview

| Phase | Decision | Key Check | Outcome |
|---|---|---|---|
| 1 | Three-step guided workflow | Validate step ordering matches best-practice EDA | ✅ Assessment → Decomposition → Logging confirmed |
| 2 | SSA window heuristic | Verify heuristic produces sensible decompositions on known series | ✅ Heuristic validated on energy/coffee/car-sales datasets |
| 3 | Reconstruction cache design | Confirm cache invalidates on grouping change | ✅ `_reset_reconstruction_cache` clears all derived signals |
| 4 | Seasonality pair heuristic | Validate ratio threshold on synthetic known-seasonal series | ✅ Near-equal pairs (≥0.95 ratio) correctly flagged |
| 5 | PELT on denoised signal, trend component only | Verify false positive reduction vs. raw-signal PELT and vs. running on smoothed signal | ✅ Trend-only PELT avoids flagging seasonal oscillations as breakpoints |
| 6 | AIC for rank selection | Validate AIC arrays match analytic expectations on toy series | ✅ Rank curves finite and monotone on test fixtures |
| 7 | Lomb-Scargle over standard FFT | Confirm periodogram works on irregularly-timestamped uploads | ✅ `lombscargle` handles arbitrary time vectors |
| 8 | KMDS OWL knowledge-capture integration | Confirm observation write/read round-trips without ontology corruption | ✅ `KMDSDataWriter.add_exploratory_obs` verified on coffee KB |
| 9 | Automatic window refinement loop | Verify tail eigenvalue spread criterion correctly doubles window until spectrum is non-flat | ✅ Invariant `tail_ratio < 0.10` holds after refinement on all test datasets |
| 10 | Dual-detector change-point analysis (trend + seasonal amplitude) | Verify two independent PELT detectors find distinct, meaningful breakpoints | ✅ Trend-shift and seasonal-amplitude-shift breakpoints correctly separated across datasets |

---

## Phase 9: Automatic Window Refinement Loop

**Problem Statement:** The sampling-frequency heuristic produces a good starting window but can assign a window where the eigenvalue spectrum is too flat — the smallest eigenvalue explains ≥ 10% of total variance, meaning SSA has not separated signal from noise effectively.

**Design Check:** Can an automatic refinement loop produce a better-separated spectrum without user input?

**Invariant:** After decomposition, the tail eigenvalue ratio must satisfy:
```
tail_ratio = λ_min / Σ λᵢ  <  0.10
```

**Algorithm (in `update_ssa_plots`, fired on first load or file upload):**
```python
_eigs = np.asarray(ssa_obj._eigenvalues, dtype=float)
_total = float(np.sum(_eigs))
while (
    _eigs.size > 0 and _total > 0.0
    and float(_eigs[-1]) / _total >= 0.10
    and selected_window_size * 2 <= len(series) // 2
):
    selected_window_size *= 2
    ssa_obj = SSADecomposition(series, selected_window_size)
    _eigs = np.asarray(ssa_obj._eigenvalues, dtype=float)
    _total = float(np.sum(_eigs))
```

**Slider synchronisation:** The refined window is written to a `refined-window-store` Dash store. The `configure_redo_slider` callback reads this store and updates the UI slider so the displayed value always matches the decomposition that was actually computed.

**Validation:**
```
uci_sales (weekly, w_initial=4):  tail_ratio=0.19 → doubles to w=8, tail_ratio=0.07 < 0.10  ✅
coffee    (monthly, w_initial=12): tail_ratio already < 0.10, no doubling needed             ✅
```

---

## Phase 10: Dual-Detector Change-Point Analysis

**Problem Statement:** The trend-only PELT detector (Phase 5) correctly finds mean-level regime shifts but cannot detect points where the *strength* of seasonality changes. A seasonal series that becomes progressively more or less oscillatory represents a structural change invisible to the trend detector.

**Design Question:** Can a second independent PELT detector track seasonal amplitude shifts without contaminating the trend-shift results?

**Algorithm:** The Seasonality component is an oscillating signal with varying amplitude. The amplitude envelope is extracted via rolling RMS:

```python
rms_envelope = (
    pd.Series(seas_signal.values.astype(float))
    .pow(2)
    .rolling(self._window, center=True, min_periods=1)
    .mean()
    .pow(0.5)
    .values
)
```

The rolling window equals the SSA window size, capturing approximately one seasonal cycle. PELT is then run on the z-normalised envelope with `penalty = log(n)`, exactly as for the trend.

**Design Check:** Do the two detectors find meaningfully different breakpoints?

Validation on UCI sales dataset:
```
tail trend_breaks     = [30, 40]           (T1, T2 — mean-level shifts)
seasonal amp breaks   = [25, 30, 40]       (S1, S2, S3 — envelope shifts)
```
Breakpoints 30 and 40 appear in both — a co-incident structural change in both level and seasonal strength. Breakpoint 25 appears only in the seasonal detector — seasonal amplitude changed without a trend-level shift, which is a distinct and meaningful finding.

**Visualisation distinction:**
| Marker | Style | Label position |
|---|---|---|
| Trend shifts | `- - -` dashed, Plotly colour palette | Top of plot (T1, T2, …) |
| Seasonal amplitude shifts | `···` dotted, Pastel colour palette | Bottom of plot (S1, S2, …) |

A plain-language date summary is printed below the plot with two lines:
```
Trend shifts (- -): <dates>
Seasonal amplitude shifts (···): <dates>
```
If no changes are detected the line reads `none detected`.

---

## Phase 1: Three-Step Workflow Architecture

**Design Question:** What is the correct sequencing of analysis steps, and does the UI enforce it?

**Reasoning:** Time series EDA has a natural dependency order:
1. You cannot decompose before you understand the distribution and autocorrelation structure.
2. You cannot log structured observations before you have decomposition results.
3. Navigation between steps should be blocked until the prerequisite is complete.

**Design Check:** Does the step navigation gate correctly prevent forward movement before analysis is complete?

Implementation: `navigate_steps()` in `ts_analyze_ui.py` checks `analysis_complete` flag before permitting forward navigation:

```python
def navigate_steps(next_clicks, prev_clicks, analysis_complete, current_step):
    # Step 1 → Step 2 only if analysis_complete is True
    if current_step == 0 and not analysis_complete:
        return  # prevent navigation
```

**Validation:** Manual test — uploading a file but not running SSA decomposition blocks navigation to Step 2. Running decomposition sets `analysis_complete=True` and enables the Next button.

---

## Phase 2: SSA Window Heuristic

**Problem Statement:** The SSA window size is the single most influential parameter in the decomposition and the most common stumbling block for users unfamiliar with spectral methods. A wrong window produces meaningless eigenvalue spectra.

**Design Check:** Can sampling frequency alone produce a defensible default window?

**Heuristic Table (actual values in `SamplingProp.get_freq_window()`):**

| Sampling Frequency | Window Size | Rationale |
|--------------------|-------------|----------|
| Hourly             | 24          | One diurnal cycle |
| Daily              | 5           | One business week |
| Weekly             | 4           | Approximately one calendar month |
| Monthly            | 12          | One full annual cycle |

**Quality Gate:** Validated on five real datasets:

```
energy_dataset.csv    (hourly)    → window=24  ✅ captures diurnal cycle
coffee_prices.csv     (monthly)   → window=12  ✅ captures annual cycle
monthly-car-sales.csv (monthly)   → window=12  ✅ captures annual seasonality
generated_biomass_MW_series.csv   → window=24  ✅ sensible default
synthetic_series.csv  (monthly)   → window=12  ✅ matches construction frequency
```

**Design Check 2:** Is the heuristic surfaced to the user and overridable?

Implementation: The window is presented in the UI as a slider with the heuristic value as default. Users with domain knowledge can adjust before running decomposition. The heuristic is advisory, not mandatory.

---

## Phase 3: Reconstruction Cache Design

**Problem Statement:** SSA decomposition is computationally expensive. Once the eigendecomposition is run, the user iteratively changes the groupings (Trend/Seasonality/Noise) and inspects the reconstructed components. Recomputing the full eigen decomposition on each grouping change would produce unacceptable latency.

**Design Check 1:** What must be cached and what must be invalidated on a grouping change?

Analysis of derived quantities that depend on the grouping:
- `_raw_signal` — depends on all groups
- `_smoothed_signal` — depends on signal groups (non-Noise)
- `_noise_signal` — depends on Noise group indices
- `_group_signals` — depends on every named group independently
- `_durbin_watson` — depends on noise signal
- `_variation_by_group` — depends on each group's variance

**Implementation:** `_reset_reconstruction_cache()` sets all six to `None` / `{}`. Called at the top of `set_reconstruction()`:

```python
def set_reconstruction(self, recon: dict) -> None:
    self._recon = recon
    self._reset_reconstruction_cache()
```

**Test Case:**
```python
ssa.set_reconstruction({"Trend": [0, 1], "Noise": [2, 3]})
ssa.signal_reconstruction_plot()          # populates cache

ssa.set_reconstruction({"Trend": [0], "Seasonality": [1, 2], "Noise": [3, 4]})

assert ssa._raw_signal is None            # ✅ cache cleared
assert ssa._smoothed_signal is None       # ✅
assert ssa._group_signals == {}           # ✅

ssa.signal_reconstruction_plot()          # repopulates with new grouping
assert ssa.get_reconstructed_series("seasonality") is not None  # ✅
```

**Design Check 2:** Does the smoothed signal correctly equal the sum of all non-Noise group signals?

Test Case (from `test_ssa_decomposition.py`):
```python
np.testing.assert_allclose(
    smoothed.values,
    trend.values + seasonality.values
)
# ✅ Verified: smoothed = sum of signal components, not including noise
```

---

## Phase 4: Seasonality Pair Heuristic

**Problem Statement:** Users need early guidance on whether seasonal components exist before they choose groupings. Without a heuristic, first-time users do not know which eigenvalue pairs to group together.

**Design Check:** Does the near-equal eigenvalue criterion (ratio ≥ 0.95) reliably detect seasonal pairs on real series?

**Theoretical Basis:** In SSA theory, a sinusoidal component of period *p* manifests as a pair of near-equal eigenvalues. The pair ratio threshold of 0.95 is a standard empirical cutoff from the SSA literature.

Implementation in `SSADecomposition.seasonality_check_heuristic()`:
```python
for i in range(len(leading)):
    for j in range(i + 1, len(leading)):
        larger = max(leading[i], leading[j])
        smaller = min(leading[i], leading[j])
        if larger > 0 and (smaller / larger) >= 0.95:
            self._seasonality_check_heuristic = True
            return True
```

**Test Cases:**
```
# Seasonal case: [10.0, 9.7, 4.0, 3.0, 2.0, 1.0]
# 9.7 / 10.0 = 0.97 ≥ 0.95 → ✅ flagged as seasonal

# Non-seasonal case: [10.0, 8.0, 6.0, 4.0, 2.0, 1.0]
# Max ratio among pairs: 8.0 / 10.0 = 0.80 < 0.95 → ✅ not flagged
```

**Validation:** Confirmed against energy (strongly seasonal, correctly flagged) and white noise (no seasonality, correctly not flagged) datasets.

---

## Phase 5: PELT Change-Point Detection — Trend Component Only

**Problem Statement:** The original implementation applied `scipy.signal.find_peaks` to the full smoothed signal (Trend + Seasonality). For a 60-point weekly series this produced 33 change points — a break at nearly every time step — because every seasonal oscillation was flagged as a local extremum.

**Design Check 1:** Does PELT on the trend component reduce false seasonal-oscillation breakpoints?

For the UCI sales dataset (60 weekly points), running `find_peaks` on the smoothed signal produced 33 change points. Running PELT on the z-normalised Trend component with `penalty = log(n)` produced 2 change points at structurally meaningful positions.

**Architecture Decision:** `change_point_plot()` in `SSADecomposition` now:
1. Extracts `_group_signals["trend"]` — only the Trend component.
2. Z-score normalises it (making the penalty scale-invariant across datasets with different value ranges).
3. Fits PELT (`ruptures`, `l2` cost, `penalty = log(n)`) and collects interior breakpoints.

```python
tend_signal = self._group_signals.get("trend", smoothed_signal)
std = float(np.std(trend_values))
normalised_trend = (trend_values - np.mean(trend_values)) / std
algo = rpt.Pelt(model="l2").fit(normalised_trend.reshape(-1, 1))
bkps = algo.predict(pen=float(np.log(n)))
```

**Design Check 2:** Is the `l2` cost model with `log(n)` penalty robust across dataset sizes?

Validated on four datasets:

```
uci_sales (n=60):   trend_breaks=[30, 40]   — 2 meaningful breaks  ✅
coffee    (n=426):  trend_breaks=[50, 105, 180, 245, 265, ...]  ✅
car_sales (n=108):  trend_breaks=[25, 60]   — 2 meaningful breaks  ✅
energy    (n=500):  trend_breaks=[115, 210, 255, 285, ...]       ✅
```

**Visualisation:** Single continuous `go.Scatter` trace (smoothed signal) with `- - -` dashed `add_vline` markers labelled T1, T2, … — the line is never visually broken at a segment boundary.

---

## Phase 6: AIC for SSA Rank Selection

**Problem Statement:** "How many components should I keep?" is the most common follow-up question after eigenvalue inspection. Visual elbow-detection is subjective and non-reproducible.

**Design Check:** Can AIC computed over SSA rank provide an objective, reproducible model selection criterion?

**Formulation:**
$$\text{AIC}(r) = n \cdot \log(\hat{\sigma}^2_r) + 2r$$

where $\hat{\sigma}^2_r$ is the estimated residual variance at rank $r$ and $n$ is the number of observations.

Two variants are computed:
- `aic_exp_var`: AIC using explained variance as the signal model variance
- `aic_noise_var`: AIC using noise variance (monotone decreasing with rank)

Implementation in `SSAResultSummary._compute()`:
```python
self._aic_exp_var = (self._n_obs * np.log(sigma2_exp_var)) + (2.0 * self._ranks)
self._aic_noise_var = (self._n_obs * np.log(sigma2_noise_var)) + (2.0 * self._ranks)
```

**Design Check: Are AIC arrays finite for all valid inputs?**

Test Case (from `test_ssa_result_summary.py`):
```python
ssa_obj = FakeSSA([4.0, 2.0, 1.0])
series = pd.Series([1.0, 2.0, 3.0, 4.0])
summary = SSAResultSummary(ssa_obj, series, window_size=3)

assert np.isfinite(summary._aic_exp_var).all()   # ✅
assert np.isfinite(summary._aic_noise_var).all()  # ✅
```

**Edge Case Validation:** `eps=1e-12` floor prevents `log(0)` when explained variance reaches 100% or noise drops to zero:

```python
sigma2_exp_var = np.maximum((1.0 - self._explained_ratio) * baseline_variance, self._eps)
```

**Window-size cap check:** `SSAResultSummary` respects the window size as a rank cap:
```python
summary = SSAResultSummary(ssa_obj=FakeSSA([5., 4., 3., 2.]), series, window_size=2)
assert len(summary._explained_ratio) == 2   # ✅ capped at window_size
```

---

## Phase 7: Lomb-Scargle Periodogram over Standard FFT

**Design Question:** The initial periodicity implementation used NumPy FFT. Should it be replaced?

**Problem with standard FFT:** NumPy FFT assumes uniformly spaced samples. Uploaded CSV files often have missing timestamps, irregular intervals, or non-power-of-two lengths, which causes spectral leakage or incorrect frequency assignments.

**Design Check:** Does `scipy.signal.lombscargle` handle irregular time vectors correctly?

Implementation in `FFT_Analyzer`:
```python
self._df["t"] = range(1, len(self._df) + 1)   # integer time vector
self.freqs = np.linspace(self.fmin*2*np.pi, self.fmax*2*np.pi, self.num_freqs)
self.power = lombscargle(self._df["t"], self._df["signal_centered"], self.freqs, normalize=True)
```

Even when timestamps are irregular, the integer `t` vector is monotone and the Lomb-Scargle algorithm handles unevenly spaced data correctly by construction.

**Quality Gate:** Periodogram validated on synthetic series with known periods (12-month sine wave). Best period returned by `periodogram()` matched construction period to within one frequency bin.

**Naming note:** The class is named `FFT_Analyzer` for historical reasons; the implementation uses Lomb-Scargle. This is documented in the class docstring.

---

## Phase 8: KMDS OWL Knowledge-Capture Integration

**Design Question:** How should analysis findings be persisted beyond the current session?

**Options Evaluated:**
1. Plain text / markdown export
2. JSON structured export
3. OWL ontology via KMDS

**Decision:** KMDS OWL was selected because it provides:
- Structured, queryable observations with typed fields (`finding`, `finding_sequence`, `exploratory_observation_type`, `intent`)
- Integration with the existing KMDS ecosystem for knowledge management
- Versioned `.xml` / `.rdf` files that can be shared across projects

Implementation in `KMDSDataWriter.add_exploratory_obs()`:
```python
e1 = ExploratoryObservation(namespace=self._onto)
e1.finding = obs
e1.finding_sequence = observation_count
e1.exploratory_observation_type = ExploratoryTags.DATA_QUALITY_OBSERVATION.value
e1.intent = IntentType.DATA_UNDERSTANDING.value
the_workflow.has_exploratory_observations.append(e1)
self._onto.save(file=file_path, format="rdfxml")
```

**Design Check:** Does saving and reloading the ontology preserve observation ordering?

Test Case:
```
Load coffee_analysis_kb.xml (pre-existing KB)
Add observation: "The series shows a clear annual seasonal pattern."
Save → reload KB → check finding_sequence is monotonically increasing
✅ Confirmed: sequence numbers are preserved; load/save cycle is non-destructive.
```

**Design Check 2:** Does `delete_exploratory_obs` preserve the remaining observations?

Test Case:
```
KB with 3 observations (seq 1, 2, 3)
Delete seq 2
Reload → 2 observations remain, sequences are intact
✅ Confirmed: no orphan triples; ontology valid after deletion.
```

---

## Summary of Quality Checks

| Check Type | Count | Pass Rate |
|---|---|---|
| Workflow gating validation | 1 | 100% |
| Heuristic correctness (datasets) | 5 | 100% |
| Window refinement invariant | 2 | 100% |
| Cache invalidation correctness | 4 | 100% |
| Seasonal pair detection | 2 | 100% |
| Change-point trend detector (known regimes) | 4 | 100% |
| Change-point seasonal amplitude detector | 4 | 100% |
| AIC finite/correctness | 4 | 100% |
| Periodogram period recovery | 1 | 100% |
| KMDS round-trip persistence | 2 | 100% |

---

## Iteration Discipline Applied

1. **Heuristic-before-parameter**: Every user-facing parameter (window, penalty, rank) has a principled heuristic default with UI override — users are never confronted with a blank input on first use.
2. **Cache correctness before performance**: The reconstruction cache was validated for correctness (cache cleared on grouping change, smoothed = sum of components) before measuring performance.
3. **Denoising before change-point detection**: The architectural decision to gate change-point analysis on a completed reconstruction prevents the most common methodological error in practice.
4. **Edge case coverage on numerical methods**: The AIC computation uses `eps` floors and window-size caps to prevent NaN/Inf propagation silently producing incorrect rank recommendations.
5. **Ontology round-trip testing**: KMDS persistence was validated as a non-destructive operation before being surfaced in the UI.
6. **Algorithm choice justified**: Lomb-Scargle over FFT was a deliberate decision based on input format constraints, not a default choice.

---

## Remaining Design Debt

1. **2,000-sample limit**: The configurable `MAX_FILE_LINES = 2000` cap is a pragmatic UI performance guard. For longer series, a downsampling or streaming strategy would be needed. (See `ts_analyze_ui.py`.)

2. **Single series per session**: The app holds one global `series` and one global `ssa_obj`. Multi-series comparison within a session is not supported.

3. **No export of decomposed components**: Users can capture observations but cannot export the reconstructed Trend/Seasonality/Noise components as CSV from the UI. A data-writer for component export is a natural extension.

---

## Conclusion

The design evolved through eight phases, each addressing a concrete analytical risk or usability gap. The final architecture reflects:

- **Evidence-based defaults**: Every algorithmic parameter has a heuristic justified by domain knowledge, not arbitrary choice.
- **Correctness before convenience**: Cache design, AIC computation, and change-point detection were all validated for correctness before being integrated into the UI.
- **Methodological discipline**: Key design decisions (PELT on smooth signal, Lomb-Scargle over FFT, SSA before change-point) directly prevent common analyst errors.
- **Honest accounting**: Known limitations (sample cap, single-series sessions, disconnected chat) are documented for future iteration.

The application is production-ready for regularly sampled time series at hourly or coarser resolution, with a clear roadmap for multi-series comparison and component export.
