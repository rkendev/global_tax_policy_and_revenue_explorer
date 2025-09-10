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
