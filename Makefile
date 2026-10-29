# ER or Urgent Care? One command from public data to site, charts and PDF.
PY := .venv/bin/python
export MPLCONFIGDIR := $(CURDIR)/.venv/.mpl

.PHONY: all venv data trim build site charts pdf test clean-raw

all: venv data trim build test

venv: .venv/bin/python
.venv/bin/python:
	python3 -m venv .venv
	$(PY) -m pip install -q --no-cache-dir -r requirements.txt

# Download raw CMS, Census and OpenStreetMap data into data/raw/ (gitignored).
# Cached files are kept; use `make data REFRESH=1` to re-download everything.
data:
	$(PY) -m eruc fetch $(if $(REFRESH),--refresh,)

# Trim the raw files into the small committed caches in data/.
trim:
	$(PY) -m eruc trim

# Build site/data.js, docs/*.png and docs/ER-or-Urgent-Care.pdf from data/.
build:
	$(PY) -m eruc build

site:
	$(PY) -m eruc site
charts:
	$(PY) -m eruc charts
pdf:
	$(PY) -m eruc pdf

test:
	$(PY) -m pytest

clean-raw:
	rm -rf data/raw
