# tseda Copilot Initialization

This repository implements `tseda`, a Python package for analyst-guided time series decomposition, diagnostics, and signal validation. It combines a notebook API, a Dash UI, and configuration-driven heuristics for segment-aware analysis.

## Project context

A useful framing for the repo is that `tseda` is an aid for the cold-start problem in time-series analysis: when an analyst is faced with a new or unfamiliar series, the first challenge is deciding where to begin, which regime to inspect, what window to use, and which components are trustworthy enough to build upon. `tseda` helps reduce that startup burden by guiding the analyst through a structured decomposition workflow.

Use these files as the primary sources of project context before making changes:

- [README.md](README.md) — package overview, installation, and quick-start usage
- [documents/PRODUCT.md](documents/PRODUCT.md) — product goals and value proposition
- [documents/ARCHITECTURE.md](documents/ARCHITECTURE.md) — system architecture and design principles
- [documents/CONTRIBUTING.md](documents/CONTRIBUTING.md) — contributor workflow and expectations
- [.github/copilot-instructions.md](.github/copilot-instructions.md) — repo-specific AI guidance

## Working conventions

- Run Python commands with `PYTHONPATH=src` when working from the repo root.
- Keep edits within the repository root unless the user explicitly requests otherwise.
- Follow the existing `src/tseda` package layout instead of creating ad hoc modules.
- Add or update tests under [tests/](tests/) when behavior changes.
- Treat threshold and heuristic settings in [src/tseda/config/tseda_config.yaml](src/tseda/config/tseda_config.yaml) as the configuration source of truth.

## Package map

- Main package: [src/tseda/](src/tseda/)
- Notebook workflow: [src/tseda/notebook_api.py](src/tseda/notebook_api.py)
- UI entrypoint: [src/tseda/user_interface/ts_analyze_ui.py](src/tseda/user_interface/ts_analyze_ui.py)
- Documentation: [docs/](docs/) and [documents/](documents/)
- Tests: [tests/](tests/)

## Typical validation commands

```bash
PYTHONPATH=src pytest -q
```

For narrower validation:

```bash
PYTHONPATH=src pytest tests/test_notebook_api.py -q
PYTHONPATH=src pytest tests/test_ssa_decomposition.py -q
```

## Design principles

- UI and notebook parity: features should be available in both the Dash UI and Python API.
- Configuration-first behavior: heuristic thresholds live in YAML, not hard-coded.
- Segment-aware analysis: the selected regime is the analytical target while the full series remains context.
- Separation of concerns: UI wiring stays separate from decomposition and diagnostics logic.
- Test-backed change requests: prefer small, validated updates aligned with existing architecture.

## Implementation guidance

Use the repository docs as the primary context before editing code. Prefer a minimal, test-backed change that follows the package's existing interface and modular boundaries.

## Ready status

This initialization file is ready for the next session. The repo is prepared to continue work in a focused, repo-aware manner.

Status: standing by.
