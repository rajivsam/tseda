# tseda Copilot Initialization

This repository implements `tseda`, a Python package for automated time series decomposition, diagnostics, and signal validation. It combines a notebook-oriented API with an interactive Dash UI and configuration-driven heuristics.

## Project context

- Product overview: `README.md`
- Product value and user outcomes: `documents/PRODUCT.md`
- Architecture and module responsibilities: `documents/ARCHITECTURE.md`
- Contributor workflow and testing expectations: `documents/CONTRIBUTING.md`
- Default repo guidance for AI agents: `.github/copilot-instructions.md`

## Working conventions

- Prefer `PYTHONPATH=src` when running tests or importing `tseda` from the repo.
- Keep changes inside the repository root unless the user explicitly asks otherwise.
- Follow the package layout in `src/tseda` instead of introducing ad hoc module structures.
- Add or update unit tests under `tests/` whenever modifying behavior.
- Treat configuration thresholds in `src/tseda/config/tseda_config.yaml` as the source of tunable algorithm behavior.

## Package shape

- Main package: `src/tseda/`
- Notebook workflow API: `src/tseda/notebook_api.py`
- UI entrypoint: `src/tseda/user_interface/ts_analyze_ui.py`
- Tests: `tests/`
- Documentation: `docs/` and `documents/`

## Typical validation commands

```bash
PYTHONPATH=src pytest -q
```

For more targeted checks:

```bash
PYTHONPATH=src pytest tests/test_notebook_api.py -q
PYTHONPATH=src pytest tests/test_ssa_decomposition.py -q
```

## Design principles

- UI and notebook parity: features in the dashboard should also be available to Python users.
- Configuration-first behavior: heuristics and thresholds live in YAML, not hard-coded.
- Explicit decomposition controls: window size and grouping remain first-class inputs.
- Separation of business logic from UI wiring.
- Test-driven implementation for new functionality.

## Implementation guidance

Use the repository docs as primary context before editing code. For feature work, prefer a small, test-backed change that follows existing module boundaries and architecture.

## Documentation task status

Current status: README rewrite work is in progress, with the model-validation and observation-logging section now drafted.

- A rewrite brief was created at [README_rewrite_points.md](/home/rajiv/programming/tseda/README_rewrite_points.md) and used to shape the documentation direction.
- The project introduction language was refined, including a clearer framing for the "About tseda" narrative.
- The workflow section now includes a dedicated Model Validation and Observation Logging subsection emphasizing:
  - AIC/BIC-based validation of decomposition choices,
  - the effect of window selection on model fit and complexity,
  - the need to preserve analytical decisions for reproducibility,
  - and the value of KMDS for natural-language review and historical retrieval.
- The next iteration should continue from this draft and turn the rewrite brief into a clean README-style narrative, with emphasis on: what tseda does, why it matters, who it is for, quick-start usage, and the three-step workflow.
- This file is ready for the next session to resume from the agreed documentation direction.
