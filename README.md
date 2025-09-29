Quickstart
# 0) Create & activate a venv (recommended)
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# 1) Install deps & git hooks
pip install -r requirements.txt
pre-commit install

# 2) Initialize local env (ruff/black config, etc.) and fetch sample data
make init
make etl           # builds gold from real OECD data (2010–latest, 5-country sample)

# 3A) Run the UI
make ui            # Streamlit will print a local URL

# 3B) Or run the API stub
make api

Project structure
etl/        # raw → transform → gold
  raw/      # download_oecd_rev.py (SDMX CSV)
  transform/# normalize_oecd_rev.py (dim_country, dim_tax_code, fact_tax)
  gold/     # build_metrics_oecd.py (tax_to_gdp, composition)
ui/         # Streamlit app (MVP)
api/        # FastAPI stub (to serve metrics)
data/       # generated artifacts (git-ignored)
docs/       # MkDocs site + ADRs


Implementation favors vectorized Pandas (split–apply–combine) instead of groupby.apply to keep performance predictable and avoid deprecation traps.
pandas.pydata.org
+1

Make targets
make init        # one-time repo bootstrap (hooks, basic checks)
make etl         # full pipeline → data/gold/*.parquet
make ui          # run Streamlit app
make api         # run FastAPI app
make test        # pytest (scoped to etl/tests)
make lint        # ruff + black + isort
make doctor      # project_doctor.sh (ETL invariants + tests + lint)

Data source & attribution

OECD Revenue Statistics via the SDMX REST API. The APIs are free of charge and subject to the OECD Terms and Conditions—attribute the OECD as the source and comply with their usage terms.
OECD

If you consume SDMX programmatically beyond this project, see the SDMX tools ecosystem.
sdmx.org

Gold metrics produced

tax_to_gdp (auto ratio→percent guard, country–year)

composition (category shares, non-negative, sums to 100% per country–year)

Running tests & quality gates
pytest -q                    # fast unit/e2e checks (no network)
ruff check . --fix           # lint (autofix imports, py-upgrades, etc.)
black .                      # formatting
pre-commit run --all-files   # same set as CI


pre-commit manages the hooks and ensures consistent formatting/linting locally and in CI.
pre-commit.com
+1

Docs

Built with MkDocs Material; the site includes ADRs and a live Changelog (the docs/changelog.md page includes the repo-root CHANGELOG.md via snippets).
squidfunk.github.io
+1

Local preview:

mkdocs serve


Publish to GitHub Pages:

mkdocs gh-deploy --force

Tech notes

Streamlit: lightweight data app framework; ideal for MVP dashboards.
docs.streamlit.io
+1

FastAPI: type-hinted, high-performance API framework; great for exposing metrics.
FastAPI

Versioning & releases

Use SemVer: tag releases (e.g., v0.1.0) and maintain CHANGELOG.md. Pre-1.0 means the interface can change without bumping MAJOR.
Semantic Versioning
+1

Draft a GitHub Release for each tag with concise human-oriented notes (link to the relevant changelog section).

Example:

git tag -a v0.1.0 -m "MVP: OECD RevStats ingest + gold + UI + tests"
git push origin v0.1.0

License & terms

Code: MIT (or your chosen license).

Data: OECD Terms and Conditions apply to the data/API usage. Cite the OECD as the source.
OECD

Roadmap (short)

Compare tab (≤5 countries): time series for tax-to-GDP + stacked composition per selected year.

Expand ingest coverage (more countries / tax codes).

API endpoints for gold metrics (with caching + ETags).

Data dictionary & per-metric provenance.
