from __future__ import annotations

import pathlib

import pandas as pd
import pandera.pandas as pa  # <- new style import (no future warning)

BRONZE_FILE = pathlib.Path("data/bronze/oecd_tax_sample.csv")
SILVER_DIR = pathlib.Path("data/silver")
SILVER_FILE = SILVER_DIR / "oecd_tax.parquet"

SCHEMA = pa.DataFrameSchema(
    {
        "country": pa.Column(
            str, checks=pa.Check.str_length(min_value=2, max_value=64), nullable=False
        ),
        "iso3": pa.Column(
            str, checks=pa.Check.str_length(min_value=3, max_value=3), nullable=False
        ),
        "year": pa.Column(int, checks=[pa.Check.ge(1900), pa.Check.le(2100)], nullable=False),
        "tax_type": pa.Column(str, checks=pa.Check.isin(["PIT", "VAT"]), nullable=False),
        "value_pct_gdp": pa.Column(
            float, checks=[pa.Check.ge(0), pa.Check.le(100)], nullable=False
        ),
    },
    coerce=True,
)


def transform_bronze_to_silver(
    in_path: pathlib.Path = BRONZE_FILE, out_path: pathlib.Path = SILVER_FILE
) -> pathlib.Path:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(in_path)
    df = SCHEMA.validate(df, lazy=True)
    df = df.sort_values(["iso3", "year", "tax_type"]).reset_index(drop=True)
    df.to_parquet(out_path, index=False)
    return out_path


def main() -> None:
    p = transform_bronze_to_silver()
    print(f"Wrote silver parquet: {p}")


if __name__ == "__main__":
    main()
