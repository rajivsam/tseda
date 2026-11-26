import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd

MODULE_PATH = Path(__file__).parents[1] / "experiments" / "run_simulation_study.py"
SPEC = importlib.util.spec_from_file_location("run_simulation_study", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

build_cases = MODULE.build_cases
run_case = MODULE.run_case
summarize = MODULE.summarize
write_latex_summary = MODULE.write_latex_summary
write_markdown_summary = MODULE.write_markdown_summary
_case_key = MODULE._case_key
_load_checkpoint = MODULE._load_checkpoint
_append_checkpoint = MODULE._append_checkpoint
validate_checkpoint = MODULE.validate_checkpoint


def test_simulation_study_smoke_outputs_are_complete(tmp_path: Path) -> None:
    cases = build_cases(
        replications=1,
        sample_lengths=(60,),
        snr_levels=(5.0,),
    )
    rows = [row for case in cases for row in run_case(case)]
    results = pd.DataFrame(rows)
    summary = summarize(results)

    assert len(cases) == 4
    assert len(results) == len(cases)
    assert set(results["method"]) == {"tseda"}
    assert np.isfinite(results["false_positive_seasonality"]).all()
    assert summary["replications"].eq(1).all()

    markdown_path = tmp_path / "summary.md"
    latex_path = tmp_path / "summary.tex"
    write_markdown_summary(summary, markdown_path, replications=1)
    write_latex_summary(summary, latex_path)

    assert markdown_path.read_text(encoding="utf-8").startswith(
        "# Synthetic Data Study Results"
    )
    assert "\\begin{tabular}" in latex_path.read_text(encoding="utf-8")


def test_simulation_checkpoint_can_be_resumed(tmp_path: Path) -> None:
    case = build_cases(replications=1, sample_lengths=(60,), snr_levels=(5.0,))[0]
    checkpoint_path = tmp_path / "raw.csv"
    rows = run_case(case)
    _append_checkpoint(rows, checkpoint_path)

    checkpoint = _load_checkpoint(checkpoint_path)

    assert len(checkpoint) == 1
    assert {_case_key(row) for _, row in checkpoint.iterrows()} == {
        ("null_control", "ar1", 60, None, 0)
    }
    validate_checkpoint(checkpoint, [case])
