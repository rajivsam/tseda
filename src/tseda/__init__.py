"""tseda package."""

from importlib.resources import files

from tseda.notebook_api import (
	EXAMPLE_DATASETS,
	AVAILABLE_BIN_ALGORITHMS,
	NotebookThreeStepAPI,
	SuitabilityResult,
	list_example_datasets,
	load_example_series,
	load_series_from_csv,
)
from tseda.segmentation.pelt_segmentation import (
    DEFAULT_MIN_SEGMENT_POINTS,
    build_adjusted_analysis_segment,
    get_short_segment_confirmation_message,
    infer_cadence_from_series,
    resolve_minimum_segment_points,
    select_pelt_model,
)


def get_agent_instructions() -> str:
    """Return the packaged AGENTS.md content.

    This helper makes the agent documentation available to installed
    consumers of the package.
    """
    agent_file = files(__package__).joinpath("AGENTS.md")
    return agent_file.read_text(encoding="utf-8")

__all__ = [
	"__version__",
	"AVAILABLE_BIN_ALGORITHMS",
	"EXAMPLE_DATASETS",
	"DEFAULT_MIN_SEGMENT_POINTS",
	"NotebookThreeStepAPI",
	"SuitabilityResult",
	"build_adjusted_analysis_segment",
	"get_short_segment_confirmation_message",
	"infer_cadence_from_series",
	"resolve_minimum_segment_points",
	"select_pelt_model",
	"list_example_datasets",
	"load_example_series",
	"load_series_from_csv",
	"get_agent_instructions",
]
__version__ = "0.1.7"
