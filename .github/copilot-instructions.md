# tseda Agent Instructions

This repository contains Python code for automated time series signal decomposition and diagnostics. Use the documents in the repository as primary context.

- Refer to `PRODUCT.md` for the product purpose and user value.
- Refer to `ARCHITECTURE.md` for the system architecture and module responsibilities.
- Refer to `CONTRIBUTING.md` for developer conventions and test expectations.
- Refer to `README.md` for a high-level overview and usage examples.

## Agent behavior

- Prefer `PYTHONPATH=src` when running local tests or importing `tseda` from within the repository.
- Do not modify files outside the repository root unless explicitly asked.
- Use the existing `src/tseda` package structure and follow the repository's modular design.
- When implementing features, add or update unit tests under `tests/`.
