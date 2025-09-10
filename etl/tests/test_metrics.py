from __future__ import annotations

import pandas as pd

from etl.gold.build_metrics import build_composition, build_tax_to_gdp


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
