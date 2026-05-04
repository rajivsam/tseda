"""tseda package."""

from tseda.notebook_api import (
	EXAMPLE_DATASETS,
	AVAILABLE_BIN_ALGORITHMS,
	NotebookThreeStepAPI,
	SuitabilityResult,
	list_example_datasets,
	load_example_series,
	load_series_from_csv,
)

__all__ = [
	"__version__",
	"AVAILABLE_BIN_ALGORITHMS",
	"EXAMPLE_DATASETS",
	"NotebookThreeStepAPI",
	"SuitabilityResult",
	"list_example_datasets",
	"load_example_series",
	"load_series_from_csv",
]
__version__ = "0.1.7"
