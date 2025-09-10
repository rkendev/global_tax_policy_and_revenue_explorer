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
