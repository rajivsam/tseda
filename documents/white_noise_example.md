# White-noise example: when SSA is not the right tool

This example exists to illustrate a specific `tseda` feature: when a series has no sharp spectral structure and the variance is diffuse across the entire eigenspectrum, SSA should not be treated as a meaningful decomposition tool. In that situation, the signal is effectively noise-dominated, and the tool warns the user that the decomposition is not reliable.

## Purpose of the example

The purpose of this example is to show how `tseda` handles a dataset that is not suitable for SSA decomposition. The core idea is simple:

- if the eigenvalue spectrum is flat rather than sharply concentrated,
- if no single component or small group of components captures the structure,
- and if the energy is spread across the spectrum,

then the series is not meaningfully separable into trend and seasonality in the way SSA expects. In that case, `tseda` does not pretend that the decomposition is meaningful. Instead, it surfaces a warning and redirects the analyst to an appropriate stochastic/noise-based model such as white-noise, ARMA, anomaly, count, or domain-specific modeling.

This is a critical design feature because a mathematically valid SSA decomposition can still be produced for a noise-dominated process, but the resulting trend and seasonality groups are not interpretable signal components. They are just statistical artifacts.

## What the UI shows

The screenshot below is the canonical example of this behavior. In the decomposition panel, the app reports that the series is not suitable for SSA decomposition and recommends switching to a noise-based approach.

![White-noise example warning screenshot](../assets/images/white_noise_warning.png)

The warning in the interface reads, in essence:

> Stop after initial assessment. The spectrum is diffuse and does not support a
> stable deterministic SSA decomposition. Investigate a white-noise, ARMA, count,
> anomaly, or domain-specific model instead.


## Why this is the expected behavior

The documentation for this workflow explicitly states that when a series is dominated by noise, the eigenspectrum looks flat and variance is spread roughly equally across eigenvectors. In that case:

- there is no single dominant component,
- the trend and seasonality groups are not distinct and interpretable,
- the residual is not a clean noise signal with a meaningful decomposition,
- and the process is better modeled with a stochastic error-driven approach rather than SSA.

This is not a failure of the algorithm. It is a feature of the workflow: the tool is helping the analyst recognize when SSA is simply the wrong modeling lens.

## Example narrative

A white-noise series is a textbook diffuse-spectrum case where SSA is not the
right tool. A random walk is a different case: its spectrum can be highly
concentrated and smooth because of stochastic persistence. In a pure random walk,
visual smoothing can create pareidolia—apparent trends or cycles in stochastic
variation. `tseda` therefore blocks deterministic SSA for both cases, but with
different recommendations:

- diffuse noise: use a noise-oriented, ARMA, count, anomaly, or domain-specific model;
- stochastic persistence: use random-walk, ARIMA/differenced, local-level, or
  state-space methods, then treat any independently defined residual as new input.

This example is therefore intended to demonstrate the guardrail behavior: `tseda` recognizes when the data do not support a meaningful SSA decomposition, warns the user explicitly, and directs them toward a better-suited model class.
