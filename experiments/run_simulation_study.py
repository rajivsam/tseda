"""Run the Phase 2 `tseda` exploratory-classifier simulation study."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import as_completed
from dataclasses import dataclass
import gc
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from statsmodels.stats.stattools import durbin_watson

from tseda.notebook_api import NotebookThreeStepAPI
from tseda.decomposition.process_diagnostics import _PROCESS_CACHE


DEFAULT_SAMPLE_LENGTHS = (60, 150, 400)
DEFAULT_SNR_LEVELS = (2.0, 5.0, 10.0)
SEASONAL_PERIOD = 7
CP_TOLERANCE_FRACTION = 0.10


@dataclass(frozen=True, slots=True)
class SimulationCase:
    scenario: str
    subtype: str
    sample_length: int
    snr: float | None
    replication: int
    seed: int


@dataclass(frozen=True, slots=True)
class SimulatedSeries:
    observed: pd.Series
    true_trend: np.ndarray
    true_seasonality: np.ndarray
    has_trend: bool
    has_seasonality: bool
    variance_change_points: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class MethodEstimate:
    trend: np.ndarray
    seasonality: np.ndarray
    residual: np.ndarray
    suitable: bool | None
    detected_trend: bool
    detected_seasonality: bool
    detected_change_points: tuple[int, ...] = ()
    window: int | None = None
    dw_converged: bool | None = None
    verified_period: bool | None = None


def _standardize_component(values: np.ndarray, scale: float) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return (values - np.mean(values)) / scale


def simulate(case: SimulationCase) -> SimulatedSeries:
    rng = np.random.default_rng(case.seed)
    n = case.sample_length
    time = np.arange(n, dtype=float)
    index = pd.date_range("2020-01-01", periods=n, freq="D")

    if case.subtype == "ar1":
        errors = rng.standard_normal(n)
        observed = np.empty(n, dtype=float)
        observed[0] = errors[0] / math.sqrt(1.0 - 0.8**2)
        for idx in range(1, n):
            observed[idx] = 0.8 * observed[idx - 1] + errors[idx]
        return SimulatedSeries(
            pd.Series(observed, index=index),
            np.zeros(n),
            np.zeros(n),
            False,
            False,
        )

    assert case.snr is not None
    logistic_time = np.linspace(-3.0, 3.0, n)
    trend = 2.0 / (1.0 + np.exp(-logistic_time))
    base_seasonality = 3.0 * np.sin(2.0 * np.pi * time / SEASONAL_PERIOD)

    seasonal_period = (
        4 if case.subtype == "short_terminal_regime" else SEASONAL_PERIOD
    )
    if case.subtype == "trend_seasonality":
        seasonality = base_seasonality
        has_seasonality = True
    elif case.subtype == "short_terminal_regime":
        terminal_start = int(round(0.65 * n))
        seasonality = np.where(
            time >= terminal_start,
            3.0 * np.sin(2.0 * np.pi * time / seasonal_period),
            0.0,
        )
        has_seasonality = True
    elif case.subtype == "variance_shift":
        seasonality = base_seasonality
        has_seasonality = True
    else:
        raise ValueError(f"Unknown simulation subtype: {case.subtype}")

    signal = trend + seasonality
    noise_sd = float(np.std(signal)) / math.sqrt(case.snr)
    if case.subtype == "variance_shift":
        change_point = n // 2
        noise_scale = np.where(time < change_point, 0.5, 2.0)
        noise = rng.standard_normal(n) * noise_sd * noise_scale
        variance_change_points = (change_point,)
    else:
        noise = rng.standard_normal(n) * noise_sd
        variance_change_points = ()

    return SimulatedSeries(
        pd.Series(signal + noise, index=index),
        trend,
        seasonality,
        True,
        has_seasonality,
        variance_change_points,
    )


def _zero_estimate(size: int) -> MethodEstimate:
    zeros = np.zeros(size, dtype=float)
    return MethodEstimate(zeros, zeros, zeros, False, False, False)


def estimate_tseda(simulated: SimulatedSeries) -> MethodEstimate:
    api = NotebookThreeStepAPI(simulated.observed)
    suitability = api.get_suitability_result()
    auto_tune = api.suggest_grouping_with_window_autotune()
    verified_period = bool(api.get_process_analysis()["periodic_components"])
    if not suitability.is_suitable or not auto_tune.grouping:
        estimate = _zero_estimate(len(simulated.observed))
        return MethodEstimate(
            estimate.trend,
            estimate.seasonality,
            np.asarray(simulated.observed, dtype=float),
            False,
            False,
            False,
            window=int(api.get_window()),
            verified_period=verified_period,
        )

    ssa = api._ensure_ssa()
    raw = ssa.get_reconstructed_series("raw_signal")
    trend = ssa.get_reconstructed_series("trend")
    seasonality = ssa.get_reconstructed_series("seasonality")
    residual = ssa.get_reconstructed_series("noise")
    assert raw is not None
    grouping = api.get_grouping()
    return MethodEstimate(
        np.asarray(trend, dtype=float) if trend is not None else np.zeros(len(raw)),
        np.asarray(seasonality, dtype=float) if seasonality is not None else np.zeros(len(raw)),
        np.asarray(residual, dtype=float) if residual is not None else np.asarray(raw, dtype=float),
        True,
        bool(grouping.get("Trend")),
        bool(grouping.get("Seasonality")),
        tuple(api.get_variance_change_points(auto_suggest_if_missing=False)),
        int(api.get_window()),
        bool(auto_tune.dw_in_range),
        verified_period,
    )


def _rmse(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(actual) - np.asarray(expected)) ** 2)))


def _change_point_result(
    detected: tuple[int, ...],
    expected: tuple[int, ...],
    sample_length: int,
) -> tuple[bool, float]:
    if not expected:
        return not detected, math.nan
    if not detected:
        return False, math.nan
    nearest = min(abs(actual - expected[0]) for actual in detected)
    return nearest <= CP_TOLERANCE_FRACTION * sample_length, float(nearest)


def evaluate_method(
    case: SimulationCase,
    simulated: SimulatedSeries,
    method: str,
    estimate: MethodEstimate,
) -> dict[str, Any]:
    scale = float(np.std(simulated.observed))
    expected_trend = _standardize_component(simulated.true_trend, scale)
    expected_seasonality = _standardize_component(simulated.true_seasonality, scale)
    estimated_trend = np.asarray(estimate.trend, dtype=float)
    estimated_seasonality = np.asarray(estimate.seasonality, dtype=float)

    if not np.allclose(np.var(estimated_trend), 0.0):
        estimated_trend = estimated_trend - np.mean(estimated_trend)
    if not np.allclose(np.var(estimated_seasonality), 0.0):
        estimated_seasonality = estimated_seasonality - np.mean(estimated_seasonality)

    cp_hit, cp_error = _change_point_result(
        estimate.detected_change_points,
        simulated.variance_change_points,
        case.sample_length,
    )
    residual_dw = (
        float(durbin_watson(estimate.residual))
        if estimate.suitable
        and np.isfinite(estimate.residual).all()
        and np.var(estimate.residual) > 0.0
        else math.nan
    )
    false_trend = not simulated.has_trend and estimate.detected_trend
    false_seasonality = not simulated.has_seasonality and estimate.detected_seasonality
    return {
        "scenario": case.scenario,
        "subtype": case.subtype,
        "sample_length": case.sample_length,
        "snr": case.snr,
        "replication": case.replication,
        "method": method,
        "suitable": estimate.suitable,
        "window": estimate.window,
        "trend_rmse": _rmse(estimated_trend, expected_trend)
        if simulated.has_trend
        else math.nan,
        "seasonality_rmse": _rmse(estimated_seasonality, expected_seasonality)
        if simulated.has_seasonality
        else math.nan,
        "durbin_watson": residual_dw,
        "dw_converged": (
            1.5 <= residual_dw <= 2.5 if np.isfinite(residual_dw) else None
        ),
        "verified_period": estimate.verified_period,
        "detected_trend": estimate.detected_trend,
        "detected_seasonality": estimate.detected_seasonality,
        "false_positive_trend": false_trend,
        "false_positive_seasonality": false_seasonality,
        "change_point_hit": cp_hit,
        "change_point_location_error": cp_error,
        "detected_change_point_count": len(estimate.detected_change_points),
    }


def run_case(case: SimulationCase) -> list[dict[str, Any]]:
    simulated = simulate(case)
    return [evaluate_method(case, simulated, "tseda", estimate_tseda(simulated))]


def build_cases(
    replications: int,
    sample_lengths: Iterable[int],
    snr_levels: Iterable[float],
) -> list[SimulationCase]:
    cases: list[SimulationCase] = []
    seed = 20261126
    for n in sample_lengths:
        for replication in range(replications):
            cases.append(
                SimulationCase(
                    "null_control",
                    "ar1",
                    int(n),
                    None,
                    replication,
                    seed + len(cases),
                )
            )

    for scenario, subtype in (
        ("structured_signal", "trend_seasonality"),
        ("cold_start", "short_terminal_regime"),
        ("variance_shift", "variance_shift"),
    ):
        for n in sample_lengths:
            for snr in snr_levels:
                for replication in range(replications):
                    cases.append(
                        SimulationCase(
                            scenario,
                            subtype,
                            int(n),
                            float(snr),
                            replication,
                            seed + len(cases),
                        )
                    )
    return cases


def release_analysis_memory() -> None:
    """Release caches retained by repeated SSA and process-analysis runs."""
    _PROCESS_CACHE.clear()
    gc.collect()


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    group_columns = ["scenario", "subtype", "sample_length", "snr", "method"]
    boolean_columns = [
        "suitable",
        "dw_converged",
        "detected_trend",
        "detected_seasonality",
        "false_positive_trend",
        "false_positive_seasonality",
        "change_point_hit",
        "verified_period",
    ]
    aggregations = {
        "replications": pd.NamedAgg(column="replication", aggfunc="count"),
        "trend_rmse_mean": pd.NamedAgg(column="trend_rmse", aggfunc="mean"),
        "seasonality_rmse_mean": pd.NamedAgg(
            column="seasonality_rmse",
            aggfunc="mean",
        ),
        "durbin_watson_mean": pd.NamedAgg(
            column="durbin_watson",
            aggfunc="mean",
        ),
        "change_point_location_error_mean": pd.NamedAgg(
            column="change_point_location_error",
            aggfunc="mean",
        ),
        "detected_change_point_count_mean": pd.NamedAgg(
            column="detected_change_point_count",
            aggfunc="mean",
        ),
        "window_mean": pd.NamedAgg(column="window", aggfunc="mean"),
    }
    for column in boolean_columns:
        aggregations[f"{column}_rate"] = pd.NamedAgg(
            column=column,
            aggfunc="mean",
        )
    grouped = results.groupby(group_columns, dropna=False).agg(**aggregations)
    return grouped.reset_index()


def _format_percent(series: pd.Series) -> pd.Series:
    return (100.0 * series).map(lambda value: "n/a" if pd.isna(value) else f"{value:.1f}%")


def _markdown_table(frame: pd.DataFrame) -> str:
    def render(value: Any) -> str:
        if pd.isna(value):
            return "n/a"
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value)

    columns = [str(column) for column in frame.columns]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows = [
        "| " + " | ".join(render(value) for value in row) + " |"
        for row in frame.itertuples(index=False, name=None)
    ]
    return "\n".join([header, separator, *rows])


def write_markdown_summary(
    summary: pd.DataFrame,
    output_path: Path,
    replications: int,
) -> None:
    null = summary[summary["scenario"] == "null_control"]
    null = null[
        [
            "subtype",
            "sample_length",
            "method",
            "false_positive_trend_rate",
            "false_positive_seasonality_rate",
        ]
    ]
    null["false_positive_trend_rate"] = _format_percent(null["false_positive_trend_rate"])
    null["false_positive_seasonality_rate"] = _format_percent(
        null["false_positive_seasonality_rate"]
    )

    recovery = summary[
        summary["subtype"].isin(
            [
                "trend_seasonality",
                "short_terminal_regime",
                "variance_shift",
            ]
        )
    ][
        [
            "subtype",
            "sample_length",
            "snr",
            "method",
            "trend_rmse_mean",
            "seasonality_rmse_mean",
            "durbin_watson_mean",
            "dw_converged_rate",
            "verified_period_rate",
        ]
    ].copy()
    recovery["dw_converged_rate"] = _format_percent(recovery["dw_converged_rate"])
    recovery["verified_period_rate"] = _format_percent(
        recovery["verified_period_rate"]
    )

    cp = summary[summary["subtype"] == "variance_shift"][
        [
            "sample_length",
            "snr",
            "method",
            "change_point_hit_rate",
            "change_point_location_error_mean",
            "detected_change_point_count_mean",
        ]
    ]

    output_path.write_text(
        "\n".join(
            [
                "# Synthetic Data Study Results",
                "",
                f"Replications per cell: {replications}.",
                "",
                "## Null false-positive control",
                "",
                _markdown_table(null),
                "",
                "## Component recovery and residual diagnostics",
                "",
                _markdown_table(recovery),
                "",
                "## Variance-shift detection",
                "",
                _markdown_table(cp),
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_latex_summary(summary: pd.DataFrame, output_path: Path) -> None:
    output_path.write_text(
        summary.to_latex(
            index=False,
            float_format=lambda value: f"{value:.3f}",
            na_rep="--",
            escape=True,
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replications", type=int, default=200)
    parser.add_argument(
        "--sample-lengths",
        type=int,
        nargs="+",
        default=list(DEFAULT_SAMPLE_LENGTHS),
    )
    parser.add_argument(
        "--snr-levels",
        type=float,
        nargs="+",
        default=list(DEFAULT_SNR_LEVELS),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/simulation_studies"),
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--max-cells",
        type=int,
        default=100,
        help="Limit this invocation to the next N unfinished simulation cells.",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Discard a prior raw checkpoint instead of resuming it.",
    )
    return parser.parse_args()


def _case_key(row: pd.Series) -> tuple[Any, ...]:
    return (
        row["scenario"],
        row["subtype"],
        int(row["sample_length"]),
        None if pd.isna(row["snr"]) else float(row["snr"]),
        int(row["replication"]),
    )


def _simulation_case_key(case: SimulationCase) -> tuple[Any, ...]:
    return (
        case.scenario,
        case.subtype,
        case.sample_length,
        case.snr,
        case.replication,
    )


def _load_checkpoint(checkpoint_path: Path) -> pd.DataFrame:
    if not checkpoint_path.exists():
        return pd.DataFrame()
    checkpoint = pd.read_csv(checkpoint_path)
    expected_columns = {
        "scenario",
        "subtype",
        "sample_length",
        "snr",
        "replication",
        "method",
    }
    if not expected_columns.issubset(checkpoint.columns):
        raise ValueError(
            f"Existing checkpoint {checkpoint_path} does not contain required columns."
        )
    return checkpoint


def validate_checkpoint(
    results: pd.DataFrame,
    expected_cases: list[SimulationCase],
) -> None:
    if results.empty:
        raise ValueError("Simulation checkpoint is empty.")
    expected = {_simulation_case_key(case) for case in expected_cases}
    duplicate_columns = [
        "scenario",
        "subtype",
        "sample_length",
        "snr",
        "replication",
        "method",
    ]
    if results.duplicated(duplicate_columns).any():
        raise ValueError("Simulation checkpoint contains duplicate method rows.")
    if set(results["method"]) != {"tseda"}:
        raise ValueError("Simulation checkpoint must contain only tseda results.")
    observed = {_case_key(row) for _, row in results.iterrows()}
    if observed != expected:
        missing = len(expected - observed)
        unexpected = len(observed - expected)
        raise ValueError(
            f"Simulation checkpoint does not match the requested design; "
            f"missing={missing}, unexpected={unexpected}."
        )
    counts = results.groupby(
        [
            "scenario",
            "subtype",
            "sample_length",
            "snr",
            "replication",
        ],
        dropna=False,
    )["method"].nunique()
    if not counts.eq(1).all():
        raise ValueError("Every simulation cell must contain exactly one tseda row.")


def _append_checkpoint(rows: list[dict[str, Any]], checkpoint_path: Path) -> None:
    frame = pd.DataFrame(rows)
    frame.to_csv(
        checkpoint_path,
        mode="a",
        header=not checkpoint_path.exists(),
        index=False,
    )


def main() -> None:
    args = parse_args()
    if args.replications < 1:
        raise ValueError("--replications must be >= 1.")
    if args.workers < 1:
        raise ValueError("--workers must be >= 1.")
    if args.max_cells is not None and args.max_cells < 1:
        raise ValueError("--max-cells must be >= 1.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "simulation_study_raw.csv"
    if args.restart and checkpoint_path.exists():
        checkpoint_path.unlink()

    checkpoint = _load_checkpoint(checkpoint_path)
    completed_case_keys = (
        {_case_key(row) for _, row in checkpoint.iterrows()}
        if not checkpoint.empty
        else set()
    )
    cases = build_cases(args.replications, args.sample_lengths, args.snr_levels)
    pending_cases = [
        case
        for case in cases
        if _simulation_case_key(case) not in completed_case_keys
    ]
    if args.max_cells is not None:
        pending_cases = pending_cases[: args.max_cells]
    total_cases = len(cases)
    print(
        f"Starting {len(pending_cases)} of {total_cases} simulation cells "
        f"with {args.workers} worker(s)."
    )

    completed = len(completed_case_keys)
    if args.workers == 1:
        for case in pending_cases:
            case_rows = run_case(case)
            _append_checkpoint(case_rows, checkpoint_path)
            release_analysis_memory()
            completed += 1
            print(
                f"Checkpointed {completed}/{total_cases} cells in bounded-memory mode."
            )
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(run_case, case): case
                for case in pending_cases
            }
            for future in as_completed(futures):
                case_rows = future.result()
                _append_checkpoint(case_rows, checkpoint_path)
                release_analysis_memory()
                completed += 1
                if completed % 100 == 0 or completed == total_cases:
                    print(f"Completed {completed}/{total_cases} cells.")

    results = _load_checkpoint(checkpoint_path)
    if completed < total_cases:
        print(
            f"Checkpoint saved with {completed}/{total_cases} cells. "
            "Rerun the same command to continue."
        )
        return
    validate_checkpoint(results, cases)
    summary = summarize(results)
    summary.to_csv(args.output_dir / "simulation_study_summary.csv", index=False)
    write_latex_summary(summary, args.output_dir / "simulation_study_summary.tex")
    write_markdown_summary(
        summary,
        args.output_dir / "simulation_study_summary.md",
        args.replications,
    )


if __name__ == "__main__":
    main()
