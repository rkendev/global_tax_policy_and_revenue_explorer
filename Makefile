# ---- Portable defaults (can be overridden: `make etl PYTHON=python3`) ----
PYTHON ?= $(or $(PY),$(shell command -v python3),$(shell command -v python))
PIP    ?= $(PYTHON) -m pip
PORT   ?= 8501
API_PORT ?= 8000

.PHONY: help init etl etl_sample test ui api lint fmt clean compare-golden

help:
	@echo "make init        - create local venv, install deps, install pre-commit"
	@echo "make etl         - run OECD ETL (real data): bronze -> silver -> gold"
	@echo "make etl_sample  - run SAMPLE ETL (toy data) to bronze -> silver -> gold"
	@echo "make test        - run pytest"
	@echo "make ui          - run Streamlit app (PORT=$(PORT))"
	@echo "make api         - run FastAPI via uvicorn (API_PORT=$(API_PORT))"
	@echo "make lint        - run pre-commit over repo"
	@echo "make fmt         - run black + isort"
	@echo "make clean       - remove venv and build artifacts"
	@echo "make compare-golden - regenerate 3-country golden CSV fixtures"

# Local bootstrap (venv) — used on developer machines; CI doesn't need this
init:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -r requirements.txt
	.venv/bin/pre-commit install

# --- REAL OECD ETL ---
etl:
	$(PYTHON) etl/raw/download_oecd_rev.py
	$(PYTHON) etl/transform/normalize_oecd_rev.py
	$(PYTHON) etl/gold/build_metrics_oecd.py

# --- SAMPLE ETL (kept for demos; safe to remove if not used) ---
etl_sample:
	$(PYTHON) etl/raw/download_oecd.py
	$(PYTHON) etl/transform/to_silver.py
	$(PYTHON) etl/gold/build_metrics.py

test:
	PYTHONPATH=. $(PYTHON) -m pytest -q

ui:
	$(PYTHON) -m streamlit run ui/app.py --server.port $(PORT)

api:
	$(PYTHON) -m uvicorn api.main:app --reload --port $(API_PORT)

lint:
	pre-commit run --all-files

fmt:
	$(PYTHON) -m isort .
	$(PYTHON) -m black .

clean:
	rm -rf .venv __pycache__ */__pycache__ .pytest_cache htmlcov

compare-golden:
	$(PYTHON) scripts/make_compare_golden.py
