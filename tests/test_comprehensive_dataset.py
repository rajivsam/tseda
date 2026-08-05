import os
from pathlib import Path

import pandas as pd

from tseda.notebook_api import NotebookThreeStepAPI, load_series_from_csv

DATASETS = [
    ("coffee_prices", "data/coffee_prices.csv"),
    ("white_noise_data", "data/white_noise_data.csv"),
    ("trimmed_biomass", "data/trimmed_biomass - generated_biomass_MW_series.csv"),
    ("monthly_car_sales", "data/monthly-car-sales.csv"),
    ("uci_air_quality_hourly_co", "data/uci_air_quality_hourly_co.csv"),
    ("ticket_resolution_hourly_nyc311", "data/ticket_resolution_hourly_nyc311.csv"),
    ("hyndman_arrivals_quarterly_japan", "data/hyndman_arrivals_quarterly_japan.csv"),
    ("hyndman_goog_daily_close", "data/hyndman_goog_daily_close.csv"),
    ("hyndman_hyndsight_daily_pageviews", "data/hyndman_hyndsight_daily_pageviews.csv"),
    ("hyndman_sunspot_monthly_area", "data/hyndman_sunspot_monthly_area.csv"),
    ("hyndman_usconsumption_quarterly_consumption", "data/hyndman_usconsumption_quarterly_consumption.csv"),
]


def _has_component(explained_variance: dict[str, float], component_name: str) -> bool:
    return float(explained_variance.get(component_name, 0.0)) > 0.0


def _change_point_summary(change_points: dict[str, list[int]], has_seasonality: bool = False) -> str:
    labels = []
    if change_points.get("trend"):
        labels.append("trend")
    if change_points.get("seasonal_amplitude"):
        labels.append("amplitude")
    if has_seasonality and change_points.get("seasonal_phase"):
        labels.append("phase")
    return ", ".join(labels) if labels else "none"


def test_comprehensive_dataset_test(tmp_path: Path):
    results: list[dict[str, object]] = []
    output_dir = Path(os.getenv("COMPREHENSIVE_TEST_OUTPUT", "data/comprehensive_test"))
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, dataset_path in DATASETS:
        series = load_series_from_csv(dataset_path)
        assert not series.empty, f"Dataset {name} produced an empty time series."

        api = NotebookThreeStepAPI(series)
        suitability = api.get_suitability_result()

        result: dict[str, object] = {
            "dataset": name,
            "samples": len(series),
            "window": api.get_window(),
            "suitability_passed": suitability.is_suitable,
            "top_k_ratio": suitability.top_k_ratio,
            "top_k": suitability.top_k,
            "threshold": suitability.threshold,
        }

        if suitability.is_suitable:
            grouping_autotune = api.suggest_grouping_with_window_autotune()
            assert isinstance(grouping_autotune.grouping, dict)
            assert isinstance(grouping_autotune.dw_in_range, bool)
            assert isinstance(grouping_autotune.windows_tried, list)
            assert grouping_autotune.initial_window >= 1
            assert grouping_autotune.final_window >= grouping_autotune.initial_window

            if grouping_autotune.grouping:
                reconstructed = api.get_reconstruction_metadata(auto_suggest_if_missing=False)
                explained_variance = reconstructed["explained_variance_percent"]
                change_points = api.get_change_points(auto_suggest_if_missing=False)
                components = api.export_components_dataframe(auto_suggest_if_missing=False)

                signal_explained = float(
                    sum(
                        value
                        for name, value in explained_variance.items()
                        if str(name).casefold() != "noise"
                    )
                )
                noise_explained = float(explained_variance.get("Noise", 0.0))

                has_seasonality = _has_component(explained_variance, "Seasonality")
                result.update(
                    {
                        "trend": "✔" if _has_component(explained_variance, "Trend") else "–",
                        "seasonality": "✔" if has_seasonality else "–",
                        "signal_explained": signal_explained,
                        "noise_explained": noise_explained,
                        "durbin_watson": float(reconstructed.get("durbin_watson", float("nan")))
                        if reconstructed.get("durbin_watson") is not None
                        else None,
                        "change_points": _change_point_summary(change_points, has_seasonality),
                        "component_rows": len(components),
                    }
                )
            else:
                result.update(
                    {
                        "trend": "n/a",
                        "seasonality": "n/a",
                        "signal_explained": 0.0,
                        "noise_explained": 0.0,
                        "durbin_watson": None,
                        "change_points": "none",
                        "component_rows": len(series),
                    }
                )
        else:
            result.update(
                {
                    "trend": "rejected",
                    "seasonality": "rejected",
                    "signal_explained": 0.0,
                    "noise_explained": 0.0,
                    "durbin_watson": None,
                    "change_points": "rejected",
                    "component_rows": len(series),
                }
            )

        results.append(result)

    assert len(results) == len(DATASETS)
    assert any(not row["suitability_passed"] for row in results), (
        "Expected at least one dataset to fail the suitability gate."
    )
    assert all(row["signal_explained"] >= 0.0 for row in results)
    assert all(row["noise_explained"] >= 0.0 for row in results)
    assert any(row["change_points"] != "none" and row["change_points"] != "rejected" for row in results)

    output_csv = output_dir / "comprehensive_dataset_results.csv"
    output_markdown = output_dir / "comprehensive_dataset_results.md"
    pd.DataFrame(results).to_csv(output_csv, index=False)

    markdown_lines = [
        "| Dataset | Trend | Seasonality | Signal Explained | Noise | Change Points | Durbin–Watson |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in results:
        markdown_lines.append(
            "| {dataset} | {trend} | {seasonality} | {signal_explained:.2f} | {noise_explained:.2f} | {change_points} | {durbin_watson} |".format(
                **{
                    "dataset": row["dataset"],
                    "trend": row["trend"],
                    "seasonality": row["seasonality"],
                    "signal_explained": float(row["signal_explained"]),
                    "noise_explained": float(row.get("noise_explained", 0.0)),
                    "change_points": row["change_points"],
                    "durbin_watson": row["durbin_watson"] if row["durbin_watson"] is not None else "n/a",
                }
            )
        )
    output_markdown.write_text("\n".join(markdown_lines))

    metadata_lines = [
        "# Comprehensive Dataset Results Metadata",
        "",
        "Field | Description | Computation / Input",
        "--- | --- | ---",
        "dataset | Identifier for the dataset being tested. | This is an input.",
        "samples | Number of rows in the loaded time series. | This is an input computed from `len(series)`, the loaded series length.",
        "window | Window size suggested or used by the API. | Derived from the API's internal suitability and window selection logic.",
        "suitability_passed | Whether the series passed the suitability gate. | Derived from `api.get_suitability_result().is_suitable`.",
        "top_k_ratio | Ratio used to determine the top-k reconstruction components. | Derived from the suitability result returned by the API.",
        "top_k | Number of top components selected for reconstruction. | Derived from the suitability result returned by the API.",
        "threshold | Suitability threshold value for the dataset. | Derived from the suitability result returned by the API.",
        "trend | Whether a Trend component was identified in the reconstruction. | Derived from the explained variance output; checks if `Trend` variance percent is greater than zero.",
        "seasonality | Whether a Seasonality component was identified. | Derived from the explained variance output; checks if `Seasonality` variance percent is greater than zero.",
        "variance_explained | Total explained variance percent across all identified components. | Derived by summing all values in `reconstructed['explained_variance_percent']`.",
        "durbin_watson | Durbin–Watson statistic for reconstructed residuals. | Derived from `reconstructed.get('durbin_watson')` when reconstruction metadata is available.",
        "change_points | Summary of detected change points in trend and seasonal behavior. | Derived from `api.get_change_points()` and formatted as a summary string.",
        "component_rows | Number of component rows returned by the API when components are exported. | Derived from the length of the component DataFrame or the original series if the grouping was rejected.",
        "",
        "For fields labeled as input, the value is directly produced by the dataset or series load process. For derived fields, the value is computed by the API or by aggregating its output.",
    ]
    output_metadata = output_dir / "results_meta-data.md"
    output_metadata.write_text("\n".join(metadata_lines))

    assert output_csv.exists()
    assert output_markdown.exists()
    assert output_metadata.exists()
