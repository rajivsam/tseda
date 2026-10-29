# OKF Documentation for TSEDA

This folder contains an Objective-Key Result-Focus (OKF) documentation structure for the `tseda` project.

It is designed to capture the product objectives, the measurable results we are tracking, and the key functional outcomes that support those objectives.

Files:

- `objectives.md` — top-level product objectives and strategic outcomes.
- `key_results.md` — measurable results mapped back to objectives.
- `outcomes.md` — feature-level outcomes and how they support those objectives.
- `metrics.md` — success criteria and reporting metrics.
- `PRODUCT.md` — product vision and user-facing value proposition.
- `ARCHITECTURE.md` — system architecture and module responsibilities.
- `CONTRIBUTING.md` — developer conventions, testing expectations, and contribution workflow.
- `plan-template.md` — template for implementation planning and feature breakdowns.
- `CONTEXT_ENGINEERING.md` — guide for using the project’s VS Code agent context files.

## Examples

The project includes a small set of focused worked examples that show how the tool behaves in representative scenarios. These examples are kept in a dedicated section so they can grow over time without crowding the core narrative.

### White-noise example

- [White-noise example](./white_noise_example.md) — demonstrates the guardrail behavior when a series is dominated by diffuse, noise-like spectrum and is not suitable for SSA decomposition. The example explains why `tseda` warns the user and recommends a stochastic/noise-based model instead.

Planned additions to this section:

- coffee-prices workflow example
- seasonal/periodic decomposition example
- change-point and validation example
