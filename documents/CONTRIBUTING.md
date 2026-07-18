# Contributing to tseda

Thank you for contributing to `tseda`! This guide describes the expectations and process for contributing code, documentation, and tests.

## Development workflow

1. Fork the repository or work in a branch on the main repository.
2. Create a feature branch with a descriptive name.
3. Make your changes in small, testable increments.
4. Run the targeted tests for any code you modify.
5. Open a pull request with a clear summary and validation notes.

## Coding conventions

- Use Python 3.12+ syntax as the repository is built for modern Python.
- Keep functions and methods short and single-purpose.
- Prefer explicit over implicit behavior in the API.
- Add or update unit tests for any changed or new functionality.
- Keep docstrings clear and consistent with existing style.

## Testing

- Use `pytest` from the repository root.
- Focus on targeted tests when developing a feature.
- Run the full suite before finalizing a contribution.

## Documentation

- Update `README.md`, `docs/`, or `documents/` when behavior changes.
- Create clear examples for new APIs.
- Prefer short, actionable documentation over long prose.

## Context engineering files

- `.github/copilot-instructions.md` should contain high-level guidance for AI agents.
- `.github/agents/plan.agent.md` should describe planning workflows.
- `.github/prompts/plan.prompt.md` should provide a reusable planning prompt.

## Design feedback

If you think a design decision needs discussion, open an issue first or add a design note to `DESIGN_HISTORY.md`.
