.PHONY: help init etl etl_sample test ui api lint fmt clean

PYTHON := .venv/bin/python
PIP := .venv/bin/pip

help:
	@echo "make init        - create venv, install deps, install pre-commit"
	@echo "make etl         - run OECD ETL (real data): bronze -> silver -> gold"
	@echo "make etl_sample  - run SAMPLE ETL (toy data) to bronze -> silver -> gold"
	@echo "make test        - run pytest"
	@echo "make ui          - run Streamlit app"
	@echo "make api         - run FastAPI (uvicorn)"
	@echo "make lint        - run pre-commit over repo"
	@echo "make fmt         - run black + isort"
	@echo "make clean       - remove venv and build artifacts"

init:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	.venv/bin/pre-commit install

# --- REAL OECD ETL ---
etl:
	$(PYTHON) etl/raw/download_oecd_rev.py
	$(PYTHON) etl/transform/normalize_oecd_rev.py
	$(PYTHON) etl/gold/build_metrics_oecd.py

# --- SAMPLE ETL (kept for demos) ---
etl_sample:
	$(PYTHON) etl/raw/download_oecd.py
	$(PYTHON) etl/transform/to_silver.py
	$(PYTHON) etl/gold/build_metrics.py

test:
	PYTHONPATH=. $(PYTHON) -m pytest -q

ui:
	.venv/bin/streamlit run ui/app.py

api:
	.venv/bin/uvicorn api.main:app --reload

lint:
	.venv/bin/pre-commit run --all-files

fmt:
	.venv/bin/isort .
	.venv/bin/black .

clean:
	rm -rf .venv __pycache__ */__pycache__ .pytest_cache htmlcov
