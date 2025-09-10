from __future__ import annotations

import pathlib

import pandas as pd

BRONZE_DIR = pathlib.Path("data/bronze")
BRONZE_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE = BRONZE_DIR / "oecd_tax_sample.csv"


def generate_sample_bronze(path: pathlib.Path = SAMPLE) -> pathlib.Path:
    """
    Generate a tiny, deterministic sample of tax data:
    columns: country, iso3, year, tax_type, value_pct_gdp
    """
    data = [
        # Netherlands (NLD)
        {
            "country": "Netherlands",
            "iso3": "NLD",
            "year": 2019,
            "tax_type": "PIT",
            "value_pct_gdp": 12.0,
        },
        {
            "country": "Netherlands",
            "iso3": "NLD",
            "year": 2019,
            "tax_type": "VAT",
            "value_pct_gdp": 9.0,
        },
        {
            "country": "Netherlands",
            "iso3": "NLD",
            "year": 2020,
            "tax_type": "PIT",
            "value_pct_gdp": 11.5,
        },
        {
            "country": "Netherlands",
            "iso3": "NLD",
            "year": 2020,
            "tax_type": "VAT",
            "value_pct_gdp": 9.5,
        },
        # Germany (DEU)
        {
            "country": "Germany",
            "iso3": "DEU",
            "year": 2019,
            "tax_type": "PIT",
            "value_pct_gdp": 11.0,
        },
        {
            "country": "Germany",
            "iso3": "DEU",
            "year": 2019,
            "tax_type": "VAT",
            "value_pct_gdp": 8.5,
        },
        {
            "country": "Germany",
            "iso3": "DEU",
            "year": 2020,
            "tax_type": "PIT",
            "value_pct_gdp": 10.8,
        },
        {
            "country": "Germany",
            "iso3": "DEU",
            "year": 2020,
            "tax_type": "VAT",
            "value_pct_gdp": 8.2,
        },
    ]
    df = pd.DataFrame(data)
    df.to_csv(path, index=False)
    return path


def main() -> None:
    p = generate_sample_bronze()
    print(f"Wrote sample bronze CSV: {p}")


if __name__ == "__main__":
    main()
