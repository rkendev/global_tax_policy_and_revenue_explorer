# Changelog

## [0.3.0] - 2025-09-30
### Added
- **Compare view CSV export**: one-click downloads for
  - Tax-to-GDP (time range you selected)
  - Composition snapshot (for the selected year & countries)

### Changed
- **100% stacking** for composition bars with rounding-safe normalization; totals are guaranteed to 100%.
- **Deterministic, high-contrast palette** for long legends; color assignment is stable across re-renders.
- Minor UI copy/labels polish for consistency.

### Performance
- **Cached gold data** and derived slices via `st.cache_data`, cutting repeated reads and recompute time.

---

## [0.2.0] - 2025-09-29
### Added
- Compare tab: multi-select (≤5), year range, Tax-to-GDP lines, stacked composition, CSV downloads.

### Changed
- Composition chart locked to 0–100% and robust categorical palette.

### CI/CD
- Build gold (`make etl`) before tests; cache pip & data.
- Portable Makefile (uses $(PYTHON) instead of hard-coded .venv).

## [0.1.0] - 2025-09-29
### Added
- OECD Revenue Statistics ingest (2010–latest) for 5 countries.
- Normalized dims (`dim_country`, `dim_tax_code`) and facts.
- Gold metrics: `tax_to_gdp`, `composition` (exactly 100%/year).
- Streamlit MVP with source caption + last updated.
- Tests & invariants; CI + pre-commit green.
