import pandas as pd
from pandas.testing import assert_frame_equal

KEEP = ["Netherlands", "Germany", "France"]
YEARS = [2020, 2021]
YEAR_ONE = 2021


def test_t2g_golden_matches():
    got = pd.read_parquet("data/gold/tax_to_gdp.parquet")
    got = got[got["country"].isin(KEEP) & got["year"].isin(YEARS)]
    got = got.sort_values(["country", "year"])[["country", "year", "tax_to_gdp"]].reset_index(
        drop=True
    )
    exp = pd.read_csv("etl/tests/golden/t2g_3cty_2yrs.csv")
    assert_frame_equal(got, exp.reset_index(drop=True), check_dtype=False)


def test_comp_reconciles_and_golden_subset():
    comp = pd.read_parquet("data/gold/composition.parquet")
    sub = comp[comp["country"].isin(KEEP) & (comp["year"] == YEAR_ONE)].copy()
    sums = sub.groupby(["country", "year"])["share_pct"].sum().round(6)
    assert (sums == 100.0).all()

    got = sub.sort_values(["country", "tax_code"])[
        ["country", "tax_code", "share_pct"]
    ].reset_index(drop=True)
    exp = pd.read_csv("etl/tests/golden/comp_3cty_y2021.csv")
    assert_frame_equal(got, exp, check_dtype=False, check_exact=False, rtol=1e-6, atol=1e-6)
