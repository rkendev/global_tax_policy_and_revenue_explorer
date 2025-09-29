# Changelog

## [0.1.0] - 2025-09-29
### Added
- OECD Revenue Statistics ingest (2010–latest) for 5 countries.
- Normalized dims (`dim_country`, `dim_tax_code`) and facts.
- Gold metrics: `tax_to_gdp`, `composition` (exactly 100%/year).
- Streamlit MVP with source caption + last updated.
- Tests & invariants; CI + pre-commit green.
