from __future__ import annotations

import os
import pathlib
import subprocess

import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLD_T2G = ROOT / "data/gold/tax_to_gdp.parquet"
GOLD_COMP = ROOT / "data/gold/composition.parquet"
SILVER = ROOT / "data/silver/oecd_rev_silver.parquet"


@pytest.mark.network
def test_make_etl_runs_and_produces_gold() -> None:
    # Limit the scope for CI speed: read env or default to 5 EU countries
    env = os.environ.copy()
    env.setdefault("OECD_COUNTRIES", "NLD+DEU+FRA+ITA+ESP")
    env.setdefault("OECD_START_YEAR", "2010")
    # Run the oecd etl chain directly (not the whole make target, to keep logs shorter in CI)
    subprocess.run(
        [env.get("PYTHON", __import__("sys").executable), "etl/raw/download_oecd_rev.py"],
        check=True,
        cwd=ROOT,
        env=env,
    )
    subprocess.run(
        [env.get("PYTHON", __import__("sys").executable), "etl/transform/normalize_oecd_rev.py"],
        check=True,
        cwd=ROOT,
        env=env,
    )
    subprocess.run(
        [env.get("PYTHON", __import__("sys").executable), "etl/gold/build_metrics_oecd.py"],
        check=True,
        cwd=ROOT,
        env=env,
    )

    assert SILVER.exists(), "silver parquet not created"
    assert GOLD_T2G.exists() and GOLD_COMP.exists(), "gold outputs missing"

    t2g = pd.read_parquet(GOLD_T2G)
    comp = pd.read_parquet(GOLD_COMP)

    # DoD: at least 3 countries and 2 years visible in t2g
    assert t2g["iso3"].nunique() >= 3, "need >= 3 countries in t2g"
    counts = t2g.groupby("iso3")["year"].nunique()
    assert (counts >= 2).any(), "at least one country should have >= 2 years"

    # Reconciliation: composition sums ~100 for sampled iso3-year
    sample = comp.groupby(["iso3", "year"])["share_pct"].sum().round(1)
    assert ((sample.between(99.0, 101.0)) | sample.isna()).all(), "composition not ~100%"
