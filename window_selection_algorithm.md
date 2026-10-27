# Window Selection in Singular Spectrum Analysis

This note is written for GitHub Markdown, so the equations use GitHub-friendly math syntax rather than LaTeX preamble commands or BibTeX metadata.

The window length $L$ is the central tuning parameter in SSA. It defines how many consecutive observations are embedded into the trajectory matrix and therefore controls how much local history is available to identify trend, seasonal structure, and noise. The choice is not arbitrary: too short a window captures only local variation, while too long a window can blur distinct regimes and make the decomposition less interpretable.

The implementation in `tseda` follows a concrete, code-verified heuristic rather than a generic kneedle search. The key distinction is this: the window-selection step is a cadence-driven initialization followed by a tail-share refinement loop; the kneedle-style elbow logic is used later in the grouping heuristic to estimate the signal/noise boundary from the eigen-spectrum. The two are related but not the same algorithm.

## Verified implementation logic

The code path is:

- `SamplingProp.get_freq_window()` computes the initial candidate window from the inferred sampling cadence.
- `NotebookThreeStepAPI._build_decomposition()` applies a refinement loop.
- The refinement loop checks whether the smallest eigenvalue still accounts for too much of the total variance.

This is exactly the implemented behavior: the code sets `min_tail_spread` from configuration (`window_refinement.min_tail_spread`, default `0.10`), then while

$$
\frac{\lambda_{\text{last}}}{\sum_i \lambda_i} \ge \text{min\_tail\_spread}
$$

it doubles the window and rebuilds the SSA decomposition. Once the tail share falls below the threshold, or the window would exceed half the series length, the refinement stops. That is the current algorithm in the code, and it is consistent with the general SSA principle that a window should be large enough to capture the dominant cycle but not so large that the eigenspectrum loses separation between structured signal and noise; see Golyandina, Nekrutkin, and Zhigljavsky (2001), and Golyandina et al. (2010).

## Algorithmic description

### 1. Input data set

Given a regular time series

$$
\mathbf{x} = (x_1, \ldots, x_n),
$$

with a timestamp index and inferred cadence $\Delta t$, the procedure begins by estimating the dominant cycle length. The initial window is chosen from the cadence-to-window mapping in `SamplingProp.get_freq_window()`:

- sub-hourly data: one day of samples is used as a nominal cycle,
- hourly: $L_0 = 24$,
- daily: $L_0 = 5$,
- weekly: $L_0 = 4$,
- monthly: $L_0 = 12$,
- quarterly: $L_0 = 4$.

This is a heuristic rather than a theorem: it chooses a starting window that is plausibly large enough to cover one seasonal cycle while still being numerically stable.

### 2. Pseudocode (verified against implementation)

```text
Input: regular series x_1, ..., x_n, cadence Δt
Input: threshold τ = 0.10 from window_refinement.min_tail_spread
Output: SSA window L

L ← InitialWindowFromCadence(Δt)
Build SSA decomposition with window L
Compute eigenvalues λ_1, ..., λ_L
T ← sum_i λ_i

while T > 0 and λ_last / T ≥ τ and 2L ≤ n/2:
    L ← 2L
    rebuild SSA decomposition with new window
    recompute eigenvalues and T

return L
```

This is the code path actually used in `NotebookThreeStepAPI._build_decomposition()`. In the implementation, the condition is:

$$
\frac{\lambda_{\text{last}}}{\sum_i \lambda_i} < \tau,
\quad \tau = 0.10,
$$

and the window is doubled while the trailing eigenvalue remains too large. The stop condition is therefore not “the knee is reached” in the kneedle sense; it is “the tail of the spectrum is no longer too dominant.”

### 3. How the initial estimate is done

The initial estimate is created by `SamplingProp.get_freq_window()`. It first infers the sampling frequency from the timestamp index, and then maps that cadence to a nominal seasonal cycle. The rationale is straightforward:

- the SSA window should cover a full seasonal cycle,
- a window that spans the dominant periodic structure is more likely to produce clean eigenpairs,
- a short window may only capture local fluctuations and fails to isolate trend/seasonality.

This is standard SSA practice and is consistent with the conceptual guidance in Golyandina et al. (2001) and the parameter-selection discussion in Golyandina et al. (2010).

### 4. How we increment

The implementation does not do a dense search over all candidate windows. It performs a coarse-to-fine doubling strategy:

$$
L \leftarrow 2L.
$$

The code checks whether the final eigenvalue still explains too much of the total variance. This is the operational version of the idea that the spectrum should have some spread; if the tail is still too heavy, then the window is too short relative to the series structure and should be expanded.

### 5. What we check

At each candidate window, the code computes the eigen-spectrum and evaluates the normalized tail share:

$$
\rho = \frac{\lambda_{\text{last}}}{\sum_i \lambda_i}.
$$

If

$$
\rho \ge \tau,
$$

then the last eigenvalue is still too prominent, meaning the decomposition is not sufficiently separated and the window is enlarged. The threshold is configured through `window_refinement.min_tail_spread` and defaults to `0.10`.

### 6. When we stop

The loop stops when one of the following holds:

1. the tail share drops below the threshold,
2. the window would exceed half the series length,
3. the decomposition is no longer increasing enough to justify further expansion.

This prevents degenerate matrices and avoids building an SSA window that is too large for the available sample size.

## References

- Golyandina, N., Nekrutkin, V., and Zhigljavsky, A. A. (2001). *Analysis of Time Series Structure: SSA and Related Techniques*. Chapman and Hall/CRC.
- Golyandina, N., Korobeynikov, A., and Zhigljavsky, A. (2010). "On the choice of parameters in Singular Spectrum Analysis." arXiv:1005.4374.

These references provide the practical and theoretical context for why SSA window choice should be based on the dominant cycle and the spectral separation of signal from noise, even though the exact threshold used here is a pragmatic implementation choice rather than a universal theorem.
