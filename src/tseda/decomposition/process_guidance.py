"""Canonical user guidance for process-aware stop conditions."""

from __future__ import annotations


STOCHASTIC_PERSISTENCE_WARNING = (
    "Stochastic persistence is consistent with a random walk, persistent AR "
    "process, or another stochastic trend. For a pure random walk, visual "
    "smoothing can create pareidolia—the tendency to see meaningful patterns "
    "in random/stochastic variation. Do not interpret smooth SSA level modes as "
    "deterministic trend or seasonality. This tool is not the right exploration "
    "choice for the level process."
)

STOCHASTIC_PERSISTENCE_ACTION = (
    "Investigate a random-walk, ARIMA/differenced, local-level, or state-space "
    "model. If that analysis produces a separately defined residual, innovation, "
    "or differenced series, it may be submitted as a new analysis only after it "
    "independently passes cadence and identifiability checks."
)


def stochastic_persistence_stop_message() -> str:
    """Return the canonical warning and recommended action."""
    return f"{STOCHASTIC_PERSISTENCE_WARNING} {STOCHASTIC_PERSISTENCE_ACTION}"
