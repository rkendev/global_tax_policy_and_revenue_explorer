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
