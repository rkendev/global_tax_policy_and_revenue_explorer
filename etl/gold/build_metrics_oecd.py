from __future__ import annotations

import pathlib
import re

import pandas as pd

SILVER = pathlib.Path("data/silver/oecd_rev_silver.parquet")
GOLD_DIR = pathlib.Path("data/gold")
T2G = GOLD_DIR / "tax_to_gdp.parquet"
COMP = GOLD_DIR / "composition.parquet"

TOTAL_RE = re.compile(r"^(?:TAX|TOT|TOTAL(?:_NET|_GROSS|_FSSB)?|TOTALTAX|TOTAL_TAX)$", re.I)


def _is_total(code: pd.Series) -> pd.Series:
    return code.astype(str).str.upper().str.match(TOTAL_RE)


def _names(silver: pd.DataFrame) -> pd.DataFrame:
    return silver[["iso3", "country"]].dropna().drop_duplicates("iso3")


def _pct_gdp(silver: pd.DataFrame) -> pd.DataFrame:
    return silver[silver["metric"] == "pct_gdp"].copy()


def tax_to_gdp_from_pct_or_total(pct: pd.DataFrame) -> pd.DataFrame:
    if pct.empty:
        raise AssertionError("No pct_gdp rows in silver")
    totals = pct[_is_total(pct["tax_code"])]
    if not totals.empty:
        t2g = (
            totals.sort_values(["iso3", "year"])
            .groupby(["iso3", "year"], as_index=False)["value"]
            .first()
            .rename(columns={"value": "tax_to_gdp"})
        )
    else:
        cats = pct[~_is_total(pct["tax_code"])]
        t2g = (
            cats.groupby(["iso3", "year"], as_index=False)["value"]
            .sum()
            .rename(columns={"value": "tax_to_gdp"})
        )
    # Some SDMX slices emit ratios (0.46) not percents (46)
    if t2g["tax_to_gdp"].median() < 1:
        t2g["tax_to_gdp"] *= 100.0
    return t2g


def composition_from_pct(pct: pd.DataFrame) -> pd.DataFrame:
    """Derive composition from pct_gdp robustly (no share metric required)."""
    cols = ["iso3", "year", "tax_code", "value"]
    miss = [c for c in cols if c not in pct.columns]
    if miss:
        raise AssertionError(f"pct_gdp frame missing {miss}; have={list(pct.columns)}")

    # Keep only category rows (not TOTAL)
    cats = pct.loc[~_is_total(pct["tax_code"]), cols].copy()
    if cats.empty:
        raise AssertionError("No category-level pct_gdp rows to derive composition")

    # 0) Make numeric, clamp, and FILL NaNs with 0 (critical)
    import pandas as pd

    cats["value"] = (
        pd.to_numeric(cats["value"], errors="coerce").fillna(0.0).astype(float).clip(lower=0.0)
    )

    # 1) Drop zero-sum groups (no composition possible)
    totals = cats.groupby(["iso3", "year"])["value"].transform("sum")
    cats = cats.loc[totals > 0].copy()
    if cats.empty:
        return cats.assign(share_pct=pd.Series(dtype="float64"))[
            ["iso3", "year", "tax_code", "share_pct"]
        ]

    # 2) Vectorized composition
    totals = cats.groupby(["iso3", "year"])["value"].transform("sum")
    comp = cats.assign(share_pct=(cats["value"] / totals) * 100.0).drop(columns=["value"])

    # 3) Clamp tiny negatives and FILL any NaNs (defensive)
    comp["share_pct"] = comp["share_pct"].astype(float).clip(lower=0.0).fillna(0.0)

    # 4) Renormalize to exactly 100 per iso3-year (vectorized)
    sums = comp.groupby(["iso3", "year"])["share_pct"].transform("sum")
    mask = sums > 0
    comp.loc[mask, "share_pct"] = comp.loc[mask, "share_pct"] * (100.0 / sums[mask])

    # 5) Residual fix (largest remainder): add tiny delta to the max bar per group
    gsum = comp.groupby(["iso3", "year"])["share_pct"].sum()
    resid = 100.0 - gsum
    idxmax = comp.groupby(["iso3", "year"])["share_pct"].idxmax()
    add = pd.Series(0.0, index=comp.index)
    add.loc[idxmax] = resid.values
    comp["share_pct"] = (comp["share_pct"] + add).clip(lower=0.0).fillna(0.0)

    # Final strict checks
    assert (comp["share_pct"] >= 0).all(), "share_pct has negatives after fix"
    chk = comp.groupby(["iso3", "year"])["share_pct"].sum().round(6)
    assert (
        chk == 100.0
    ).all(), f"composition sums not 100: {chk[chk.ne(100.0)].head(10).to_dict()}"
    return comp[["iso3", "year", "tax_code", "share_pct"]]


def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    silver = pd.read_parquet(SILVER)
    names = _names(silver)
    pct = _pct_gdp(silver)

    t2g = tax_to_gdp_from_pct_or_total(pct).merge(names, on="iso3", how="left")
    comp = composition_from_pct(pct).merge(names, on="iso3", how="left")

    t2g = t2g[["country", "iso3", "year", "tax_to_gdp"]]
    comp = comp[["country", "iso3", "year", "tax_code", "share_pct"]]

    t2g.to_parquet(T2G, index=False)
    comp.to_parquet(COMP, index=False)
    print(f"Wrote gold: {T2G} and {COMP}")


if __name__ == "__main__":
    main()
