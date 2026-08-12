# Build the paper. Regenerates references.bib and values.tex from live
# project data before every compile, so the PDF is never stale relative
# to analysis/ -- run `make` any time after new data lands.
#
# Uses the texlive/2023 module's binaries directly (full path, not
# `module load`) so this works identically whether or not the invoking
# shell has the module system sourced. The bare system pdflatex
# (TeX Live 2018, /usr/bin/pdflatex) lacks IEEEtran.cls.

TEXBIN := /opt/apps/texlive/2023/bin/x86_64-linux
PDFLATEX := $(TEXBIN)/pdflatex -interaction=nonstopmode -halt-on-error
BIBTEX := $(TEXBIN)/bibtex

.PHONY: all clean values bib citations

all: paper.pdf

values:
	cd .. && uv run python scripts/build_paper_values.py

bib:
	cd .. && uv run python scripts/build_paper_bib.py

citations: values bib
	cd .. && uv run python scripts/check_doc_citations.py

paper.pdf: paper.tex values bib $(wildcard sections/*.tex) references.yaml
	$(PDFLATEX) paper.tex
	$(BIBTEX) paper
	$(PDFLATEX) paper.tex
	$(PDFLATEX) paper.tex

clean:
	rm -f paper.aux paper.bbl paper.blg paper.log paper.out paper.toc paper.pdf
