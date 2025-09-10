#!/usr/bin/env bash
set -euo pipefail

# Guard: must be run from the repo root (where .git exists)
if [ ! -d ".git" ]; then
  echo "Error: run this script from the git repository root (where .git/ lives)." >&2
  exit 1
fi

mkdir -p .github/workflows
mkdir -p docs/adr
mkdir -p etl/raw etl/transform etl/gold etl/tests/data
mkdir -p data/bronze data/silver data/gold
mkdir -p api ui infra scripts

# -------------------------
# .gitignore
# -------------------------
cat > .gitignore <<'EOF'
# Python
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
*.pytest_cache/
.mypy_cache/
.coverage
htmlcov/

# Data (keep only tiny golden samples in git)
data/bronze/
data/silver/
data/gold/
!etl/tests/data/

# Streamlit cache
.streamlit/

# OS/editor
.DS_Store
*.swp
.idea/
.vscode/
EOF

# -------------------------
# pyproject.toml (tooling config)
# -------------------------
cat > pyproject.toml <<'EOF'
[project]
name = "global-tax-policy-and-revenue-explorer"
version = "0.1.0"
requires-python = ">=3.10"
description = "MVP for global tax policy & revenue explorer"
readme = "README.md"
license = {text = "MIT"}

[tool.ruff]
line-length = 100
select = ["E","F","I","UP","B"]
ignore = ["E203"]  # compatible with black on slices
target-version = "py310"

[tool.black]
line-length = 100

[tool.isort]
profile = "black"
EOF

# -------------------------
# Requirements (dev + runtime)
# -------------------------
cat > requirements.txt <<'EOF'
pandas>=2.2
pyarrow>=15
pandera>=0.18
fastapi>=0.111
uvicorn[standard]>=0.30
streamlit>=1.36
altair>=5.3
pre-commit>=3.7
black>=24.4
ruff>=0.5
isort>=5.13
pytest>=8.2
EOF

# -------------------------
# pre-commit config
# -------------------------
cat > .pre-commit-config.yaml <<'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.6
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-yaml
      - id: check-added-large-files
EOF

# -------------------------
# Makefile
# -------------------------
cat > Makefile <<'EOF'
.PHONY: help init etl test ui api lint fmt clean

PYTHON := .venv/bin/python
PIP := .venv/bin/pip

help:
	@echo "make init   - create venv, install deps, install pre-commit"
	@echo "make etl    - run sample end-to-end ETL (bronze -> silver -> gold)"
	@echo "make test   - run pytest"
	@echo "make ui     - run Streamlit app"
	@echo "make api    - run FastAPI (uvicorn)"
	@echo "make lint   - run pre-commit over repo"
	@echo "make fmt    - run black + isort"
	@echo "make clean  - remove venv and build artifacts"

init:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	.venv/bin/pre-commit install

etl:
	$(PYTHON) etl/raw/download_oecd.py
	$(PYTHON) etl/transform/to_silver.py
	$(PYTHON) etl/gold/build_metrics.py

test:
	$(PYTHON) -m pytest -q

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
EOF

# -------------------------
# CI workflow
# -------------------------
cat > .github/workflows/ci.yml <<'EOF'
name: CI

on:
  push:
  pull_request:

jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Lint (pre-commit)
        run: |
          pre-commit run --all-files
      - name: Tests
        run: |
          pytest -q
EOF

# -------------------------
# README
# -------------------------
cat > README.md <<'EOF'
# Global Tax Policy & Revenue Explorer (MVP)

Solo-dev, production-lean skeleton:
- Reproducible ETL to bronze/silver/gold
- Streamlit MVP UI
- FastAPI stub
- Tests, linting, pre-commit, and CI

## Quickstart
```bash
make init
make etl
make ui         # in another terminal
# or:
make api
```

## Structure
- `etl/` – raw → transform → gold (functions + scripts)
- `data/` – artifacts (ignored in git)
- `ui/` – Streamlit MVP
- `api/` – FastAPI stub (serves metrics later)
- `docs/` – MkDocs + ADRs
EOF

# -------------------------
# MkDocs (optional docs shell)
# -------------------------
cat > mkdocs.yml <<'EOF'
site_name: Global Tax Policy & Revenue Explorer
theme:
  name: material
nav:
  - Home: index.md
  - ADRs:
      - "ADR-001: Initial Scope & DuckDB": docs/adr/ADR-001.md
EOF

cat > docs/index.md <<'EOF'
# Project Docs

This site will host data sources, schema, metric definitions, and runbook.
EOF

cat > docs/adr/ADR-001.md <<'EOF'
# ADR-001: Start with OECD subset + DuckDB/Parquet

- We begin with a narrow, high-quality dataset (OECD Revenue Statistics subset).
- Use local-friendly columnar storage (Parquet) and DuckDB for fast, reproducible dev.
- Avoid premature infra; keep the pipeline deterministic and versioned.
EOF

# -------------------------
# ETL package __init__.py
# -------------------------
touch etl/__init__.py
touch etl/raw/__init__.py
touch etl/transform/__init__.py
touch etl/gold/__init__.py

# -------------------------
# RAW: sample bronze generator
# -------------------------
cat > etl/raw/download_oecd.py <<'EOF'
from __future__ import annotations
import pathlib
import pandas as pd

BRONZE_DIR = pathlib.Path("data/bronze")
BRONZE_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE = BRONZE_DIR / "oecd_tax_sample.csv"

def generate_sample_bronze(path: pathlib.Path = SAMPLE) -> pathlib.Path:
    """
    Generate a tiny, deterministic sample of tax data:
    columns: country, iso3, year, tax_type, value_pct_gdp
    """
    data = [
        # Netherlands (NLD)
        {"country": "Netherlands", "iso3": "NLD", "year": 2019, "tax_type": "PIT", "value_pct_gdp": 12.0},
        {"country": "Netherlands", "iso3": "NLD", "year": 2019, "tax_type": "VAT", "value_pct_gdp": 9.0},
        {"country": "Netherlands", "iso3": "NLD", "year": 2020, "tax_type": "PIT", "value_pct_gdp": 11.5},
        {"country": "Netherlands", "iso3": "NLD", "year": 2020, "tax_type": "VAT", "value_pct_gdp": 9.5},
        # Germany (DEU)
        {"country": "Germany", "iso3": "DEU", "year": 2019, "tax_type": "PIT", "value_pct_gdp": 11.0},
        {"country": "Germany", "iso3": "DEU", "year": 2019, "tax_type": "VAT", "value_pct_gdp": 8.5},
        {"country": "Germany", "iso3": "DEU", "year": 2020, "tax_type": "PIT", "value_pct_gdp": 10.8},
        {"country": "Germany", "iso3": "DEU", "year": 2020, "tax_type": "VAT", "value_pct_gdp": 8.2},
    ]
    df = pd.DataFrame(data)
    df.to_csv(path, index=False)
    return path

def main() -> None:
    p = generate_sample_bronze()
    print(f"Wrote sample bronze CSV: {p}")

if __name__ == "__main__":
    main()
EOF

# -------------------------
# TRANSFORM: to silver with validation
# -------------------------
cat > etl/transform/to_silver.py <<'EOF'
from __future__ import annotations
import pathlib
import pandas as pd
import pandera as pa
from pandera import Column, Check

BRONZE_FILE = pathlib.Path("data/bronze/oecd_tax_sample.csv")
SILVER_DIR = pathlib.Path("data/silver")
SILVER_FILE = SILVER_DIR / "oecd_tax.parquet"

class SilverSchema(pa.SchemaModel):
    country: Column[str] = Column(pa.String, checks=[Check.str_length(2, 64)], nullable=False)
    iso3: Column[str] = Column(pa.String, checks=[Check.str_length(3, 3)], nullable=False)
    year: Column[int] = Column(pa.Int64, checks=[Check.ge(1900), Check.le(2100)], nullable=False)
    tax_type: Column[str] = Column(pa.String, checks=[Check.isin(["PIT", "VAT"])], nullable=False)
    value_pct_gdp: Column[float] = Column(pa.Float, checks=[Check.ge(0), Check.le(100)], nullable=False)

def transform_bronze_to_silver(in_path: pathlib.Path = BRONZE_FILE, out_path: pathlib.Path = SILVER_FILE) -> pathlib.Path:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(in_path)
    df["country"] = df["country"].astype("string")
    df["iso3"] = df["iso3"].astype("string")
    df["tax_type"] = df["tax_type"].astype("string")
    df["year"] = df["year"].astype("int64")
    df["value_pct_gdp"] = df["value_pct_gdp"].astype("float64")

    # Validate schema and allowed ranges
    SilverSchema.validate(df, lazy=True)

    # Normalize ordering & write
    df = df.sort_values(["iso3", "year", "tax_type"]).reset_index(drop=True)
    df.to_parquet(out_path, index=False)
    return out_path

def main() -> None:
    p = transform_bronze_to_silver()
    print(f"Wrote silver parquet: {p}")

if __name__ == "__main__":
    main()
EOF

# -------------------------
# GOLD: build metrics (tax_to_gdp + composition)
# -------------------------
cat > etl/gold/build_metrics.py <<'EOF'
from __future__ import annotations
import pathlib
import pandas as pd

SILVER_FILE = pathlib.Path("data/silver/oecd_tax.parquet")
GOLD_DIR = pathlib.Path("data/gold")
GOLD_TAX_TO_GDP = GOLD_DIR / "tax_to_gdp.parquet"
GOLD_COMPOSITION = GOLD_DIR / "composition.parquet"

def build_tax_to_gdp(silver: pd.DataFrame) -> pd.DataFrame:
    out = (
        silver.groupby(["country", "iso3", "year"], as_index=False)["value_pct_gdp"]
        .sum()
        .rename(columns={"value_pct_gdp": "tax_to_gdp"})
    )
    # Sanity: 0..100
    assert (out["tax_to_gdp"].between(0, 100)).all(), "tax_to_gdp out of [0,100]"
    return out

def build_composition(silver: pd.DataFrame) -> pd.DataFrame:
    sums = silver.groupby(["country", "iso3", "year"])["value_pct_gdp"].transform("sum")
    comp = silver.copy()
    comp["share_pct"] = (comp["value_pct_gdp"] / sums) * 100.0
    # group sums should be ~100 (+/- small epsilon)
    check = comp.groupby(["country", "iso3", "year"])["share_pct"].sum().round(3)
    assert ((check - 100.0).abs() <= 0.01).all(), "composition shares do not sum to 100%"
    return comp[["country", "iso3", "year", "tax_type", "share_pct"]]

def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(SILVER_FILE)
    t2g = build_tax_to_gdp(df)
    comp = build_composition(df)
    t2g.to_parquet(GOLD_TAX_TO_GDP, index=False)
    comp.to_parquet(GOLD_COMPOSITION, index=False)
    print(f"Wrote gold: {GOLD_TAX_TO_GDP} and {GOLD_COMPOSITION}")

if __name__ == "__main__":
    main()
EOF

# -------------------------
# Tests (sample)
# -------------------------
cat > etl/tests/test_metrics.py <<'EOF'
from __future__ import annotations
import pandas as pd
from etl.gold.build_metrics import build_tax_to_gdp, build_composition

def test_metrics_from_small_df() -> None:
    df = pd.DataFrame(
        [
            {"country": "X", "iso3": "XXX", "year": 2000, "tax_type": "PIT", "value_pct_gdp": 10.0},
            {"country": "X", "iso3": "XXX", "year": 2000, "tax_type": "VAT", "value_pct_gdp": 5.0},
            {"country": "X", "iso3": "XXX", "year": 2001, "tax_type": "PIT", "value_pct_gdp": 12.0},
            {"country": "X", "iso3": "XXX", "year": 2001, "tax_type": "VAT", "value_pct_gdp": 6.0},
        ]
    )
    t2g = build_tax_to_gdp(df)
    assert set(t2g.columns) == {"country", "iso3", "year", "tax_to_gdp"}
    assert float(t2g.loc[t2g["year"] == 2000, "tax_to_gdp"]) == 15.0

    comp = build_composition(df)
    assert set(comp.columns) == {"country", "iso3", "year", "tax_type", "share_pct"}
    # shares sum ~ 100 each year
    sums = comp.groupby("year")["share_pct"].sum().round(3)
    assert (sums == 100.0).all()
EOF

# -------------------------
# FastAPI stub
# -------------------------
cat > api/main.py <<'EOF'
from __future__ import annotations
import pathlib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Tax Metrics API (MVP)")

GOLD_DIR = pathlib.Path("data/gold")
T2G = GOLD_DIR / "tax_to_gdp.parquet"

class TaxToGdpItem(BaseModel):
    country: str
    iso3: str
    year: int
    tax_to_gdp: float

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/metrics/tax_to_gdp", response_model=list[TaxToGdpItem])
def get_tax_to_gdp(country: str | None = None, iso3: str | None = None, year: int | None = None):
    if not T2G.exists():
        raise HTTPException(status_code=404, detail="Gold dataset not found. Run `make etl` first.")
    df = pd.read_parquet(T2G)
    if country:
        df = df[df["country"].str.lower() == country.lower()]
    if iso3:
        df = df[df["iso3"].str.upper() == iso3.upper()]
    if year:
        df = df[df["year"] == year]
    return df.to_dict(orient="records")
EOF

# -------------------------
# Streamlit MVP shell
# -------------------------
cat > ui/app.py <<'EOF'
import pathlib
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Global Tax Policy & Revenue Explorer", layout="wide")
st.title("Global Tax Policy & Revenue Explorer — MVP")

gold_dir = pathlib.Path("data/gold")
t2g_pq = gold_dir / "tax_to_gdp.parquet"
comp_pq = gold_dir / "composition.parquet"

if not (t2g_pq.exists() and comp_pq.exists()):
    st.warning("Gold datasets not found. Run **make etl** first to generate sample data.")
    st.stop()

t2g = pd.read_parquet(t2g_pq)
comp = pd.read_parquet(comp_pq)

countries = sorted(t2g["country"].unique())
years = sorted(t2g["year"].unique())

left, right = st.columns([1,3])
with left:
    country = st.selectbox("Country", countries, index=0)
    year = st.selectbox("Year", years, index=len(years)-1)

with right:
    st.subheader(f"Tax-to-GDP — {country} ({year})")
    sel = t2g[(t2g["country"] == country) & (t2g["year"] == year)]
    if sel.empty:
        st.info("No data for selection.")
    else:
        value = float(sel["tax_to_gdp"].iloc[0])
        st.metric(label="Tax-to-GDP (%)", value=f"{value:.1f}")

    st.subheader("Composition (share of total tax, %)")
    csel = comp[(comp["country"] == country) & (comp["year"] == year)]
    if not csel.empty:
        st.bar_chart(csel.set_index("tax_type")["share_pct"])
    else:
        st.info("No composition data for selection.")
EOF

# -------------------------
# Simple Dockerfile (optional)
# -------------------------
cat > infra/Dockerfile <<'EOF'
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
EOF

# -------------------------
# Helper script (optional)
# -------------------------
cat > scripts/print_tree.sh <<'EOF'
#!/usr/bin/env bash
set -e
command -v tree >/dev/null 2>&1 && tree -a -I ".git|__pycache__|.venv|.pytest_cache|data" ||   find . -maxdepth 3 -type d -print
EOF
chmod +x scripts/print_tree.sh

echo "✅ Skeleton created. Next steps:"
echo "1) make init"
echo "2) make etl"
echo "3) make ui   # (in a new terminal) or make api"
