# Metrics

## Usage metrics

- Time to complete analysis: median minutes from dataset load to final export.
- Default window acceptance rate: percentage of sessions where the user keeps the suggested SSA window.
- Export rate: percentage of completed analyses that generate at least one exported artifact.

## Quality metrics

- AIC rank application rate: percentage of decompositions that record AIC-based rank selection.
- Change-point validation accuracy: percentage of correct detections on benchmark datasets.
- Noise diagnostic coverage: percentage of runs that report both Durbin-Watson and KDE assessment.

## Documentation metrics

- OKF documentation coverage: number of completed OKF docs in `documents/`.
- User guide update frequency: number of updates to `docs/user_guide.md` per release.
- ReadTheDocs build success rate: percentage of successful builds on the main branch.
