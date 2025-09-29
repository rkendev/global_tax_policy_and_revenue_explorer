from pathlib import Path

import pandas as pd

OUT = Path("etl/tests/golden")
OUT.mkdir(parents=True, exist_ok=True)

t2g = pd.read_parquet("data/gold/tax_to_gdp.parquet")
comp = pd.read_parquet("data/gold/composition.parquet")

KEEP = ["Netherlands", "Germany", "France"]
YEARS = [2020, 2021]
YEAR_ONE = 2021

t2g_q = (
    t2g[t2g["country"].isin(KEEP) & t2g["year"].isin(YEARS)]
    .sort_values(["country", "year"])[["country", "year", "tax_to_gdp"]]
    .reset_index(drop=True)
)
t2g_q.to_csv(OUT / "t2g_3cty_2yrs.csv", index=False)

comp_q = (
    comp[comp["country"].isin(KEEP) & (comp["year"] == YEAR_ONE)]
    .sort_values(["country", "tax_code"])[["country", "tax_code", "share_pct"]]
    .reset_index(drop=True)
)
comp_q.to_csv(OUT / "comp_3cty_y2021.csv", index=False)

print("Wrote:", [p.name for p in OUT.glob("*.csv")])
