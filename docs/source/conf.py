"""Sphinx configuration for tseda documentation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# -- Path setup --------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))

# -- Project information -----------------------------------------------------

project = "tseda"
author = "tseda contributors"
copyright = "2026, tseda contributors"

try:
    from tseda import __version__ as release
except Exception:  # pragma: no cover - docs fallback
    release = "0.1.6"

version = release

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
    "myst_parser",
]
autodoc_member_order = "bysource"
autodoc_typehints = "signature"
autodoc_typehints_format = "short"
autodoc_class_signature = "mixed"
autoclass_content = "both"
autodoc_default_options = {
    "members": True,
    "special-members": "__init__",
    "undoc-members": True,
    "show-inheritance": True,
}
autosummary_generate = True
autosummary_imported_members = False
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True

# Keep API doc generation deterministic for local and RTD builds.
def run_apidoc(app):
    from sphinx.ext.apidoc import main

    output_dir = Path(__file__).parent / "api"
    module_dir = SRC / "tseda"
    excluded_paths = [
        str(module_dir / "user_interface"),
    ]

    main(
        [
            "--force",
            "--remove-old",
            "--implicit-namespaces",
            "--module-first",
            "--separate",
            "--output-dir",
            str(output_dir),
            str(module_dir),
            *excluded_paths,
        ]
    )


def setup(app):
    app.connect("builder-inited", run_apidoc)


templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

# -- Options for HTML output -------------------------------------------------

html_theme = "furo"
html_title = "tseda documentation"
html_static_path = ["_static"]

# Most modules are importable from src/, but UI modules can pull optional deps.
autodoc_mock_imports = [
    "dash",
    "dash_ag_grid",
    "dash_bootstrap_components",
    "KDEpy",
    "google",
    "google.genai",
    "jupyter_dash",
    "kdepy",
    "kmds",
    "matplotlib",
    "matplotlib.pyplot",
    "numpy",
    "pandas",
    "plotly",
    "plotly.express",
    "plotly.graph_objects",
    "ruptures",
    "scipy",
    "scipy.signal",
    "seaborn",
    "skrub",
    "ssalib",
    "statsmodels.nonparametric.smoothers_lowess",
    "statsmodels.stats.stattools",
    "statsmodels",
    "streamlit",
]

myst_enable_extensions = ["colon_fence", "deflist"]

# Respect RTD canonical URL if provided.
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")
