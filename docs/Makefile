# Minimal makefile for Sphinx documentation

SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = _build

.PHONY: help clean html linkcheck verify-api

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

clean:
	rm -rf "$(BUILDDIR)"

html:
	$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

linkcheck:
	$(SPHINXBUILD) -M linkcheck "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

verify-api:
	$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" -W --keep-going $(SPHINXOPTS)
	grep -q "SSADecomposition" "$(BUILDDIR)/html/api/tseda.decomposition.ssa_decomposition.html"
	grep -q "seasonality_check_heuristic" "$(BUILDDIR)/html/api/tseda.decomposition.ssa_decomposition.html"
	grep -q "\\[source\\]" "$(BUILDDIR)/html/api/tseda.decomposition.ssa_decomposition.html"
	@echo "API docs verification passed: class details, method signatures, and source links are present."
