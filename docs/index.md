# Global Tax Policy & Revenue Explorer

A small, production-lean project to explore **tax-to-GDP** and **tax composition** across countries and time using a reproducible ETL and a simple UI.

---

## Live links

- **Streamlit app:** _add your URL here_
- **Changelog:** [/changelog](../changelog/)
- **Repository:** https://github.com/rkendev/global_tax_policy_and_revenue_explorer

---

## Quickstart (local)

```bash
make init        # create venv + install deps + pre-commit
make etl         # build bronze -> silver -> gold from OECD SDMX
make ui          # open Streamlit (port 8501)
# optional:
make api         # start FastAPI stub (port 8000)
pytest -q        # run tests
Artifacts are written to data/bronze, data/silver, and data/gold (git-ignored).

Data source & attribution
Source: OECD Revenue Statistics (SDMX).

Attribution: “Source: OECD Revenue Statistics (SDMX)”.

Last updated: shown in the app header (derived from ETL snapshot metadata).

We ingest a narrow slice (first 5 countries; 2010–latest) to keep the MVP fast and deterministic.

Pipeline overview
Bronze (raw): Single SDMX extract persisted to CSV + a small .meta.json (snapshot timestamp, query).

Silver (normalized):

dim_country (ISO2 → ISO3, canonical names)

dim_tax_code (OECD codes; PIT/VAT highlighted first)

fact_tax (country, year, code, value, unit)

Gold (metrics):

tax_to_gdp.parquet

composition.parquet (share of total tax, per country-year; sums to exactly 100%)

Validations

Pandera schema on silver/gold, ranges 0–100, and composition reconciliation (≈100% with rounding-proof adjustment).

E2E test asserts row counts and golden slices (3 countries × 2 years).

Metrics
Metric	Definition
Tax-to-GDP (%)	(Total tax revenue / GDP) × 100 for a given country-year.
Composition (% of total tax)	Share by OECD tax code (e.g., PIT, VAT, etc.) within a country-year. Bars in the UI are normalized to 0–100%.

UI features (MVP)
Overview: single-country point-in-time view.

Compare: up to 5 countries, year range slider, Tax-to-GDP lines, stacked composition for a selected year, and CSV downloads.

Missing years are handled gracefully; legend remains stable.

Runbook
Nightly refresh: GitHub Actions builds gold artifacts daily (02:00 UTC).

Manual refresh: make etl locally or rerun the Nightly ETL workflow in Actions.

Troubleshooting:

App port occupied? fuser -k 8501/tcp (Linux) then make ui.

CI failures: check the Build gold step and attached artifacts.

Roadmap
Expand ingest to 10–20 additional countries behind existing validations.

Add “download chart data” on Overview.

Optional: versioned docs, broader categories, and API endpoints for gold metrics.

License & notes
OECD data licensing/terms apply for the SDMX source.

This repository’s code is licensed under add your license.
