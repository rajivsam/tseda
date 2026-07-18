# Context Engineering for tseda

This document explains how the repo-level context files are organized and how to use them for VS Code agent workflows.

## Purpose

These files provide concise project and process context for AI-assisted development. They are intended to:

- Ground the agent in the product vision and architecture.
- Provide developer conventions and testing expectations.
- Offer a reusable implementation planning template.
- Enable a simple planning and implementation workflow via custom agent files.

## Files and roles

- `PRODUCT.md` — Describes the product vision, target users, and the value proposition of `tseda`.
- `ARCHITECTURE.md` — Describes the repository architecture, module responsibilities, and design principles.
- `CONTRIBUTING.md` — Describes development workflow, coding conventions, and testing expectations.
- `plan-template.md` — Provides a structured template for implementation plans.
- `.github/copilot-instructions.md` — Defines the default agent context and repository-specific guidance.
- `.github/agents/plan.agent.md` — Defines a planning agent persona for creating implementation plans.
- `.github/agents/implement.agent.md` — Defines a test-driven implementation agent persona.
- `.github/prompts/plan.prompt.md` — Provides a reusable planning prompt for the `plan` agent.

## How to use these files

1. Open the project in VS Code.
2. Use the `.github/copilot-instructions.md` file to ensure the agent has the right repository-level guidance.
3. Use the `plan` agent to generate implementation plans from requirements or feature requests.
4. Use `plan-template.md` as the structure for documenting those plans.
5. Use the `implement` agent to execute the plan in a test-first way, validating changes against the repository's conventions.

## Recommended workflow

- Start with a short feature request or bug description.
- Run the `plan` agent with `plan.prompt.md` to generate a structured plan.
- Review the plan and add any missing acceptance criteria.
- Use the `implement` agent to add tests and code incrementally.
- Update `CONTRIBUTING.md`, `ARCHITECTURE.md`, or `PRODUCT.md` if the feature changes the repository design or product direction.
