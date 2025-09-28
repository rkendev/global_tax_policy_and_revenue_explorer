from __future__ import annotations

import json
import pathlib

import pandas as pd
import pandera.pandas as pa

BRONZE_FILE = pathlib.Path("data/bronze/oecd_rev_comp.csv")
SILVER_FILE = pathlib.Path("data/silver/oecd_rev_silver.parquet")
SILVER_SAMPLE = pathlib.Path("data/silver/oecd_rev_silver_sample.csv")
LABELS_SAMPLE = pathlib.Path("data/silver/_labels_sample.csv")
DETECT_DEBUG = pathlib.Path("data/silver/_detector_debug.json")


def pick_col(df: pd.DataFrame, *cands: str) -> str | None:
    low = {c.lower(): c for c in df.columns}
    for c in cands:
        if c.lower() in low:
            return low[c.lower()]
    for c in cands:
        cl = c.lower()
        for k, v in low.items():
            if cl in k:
                return v
    return None


def _lower(s: pd.Series | None) -> pd.Series:
    return s.astype(str).str.lower() if s is not None else pd.Series([], dtype="object")


def _sanitize(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Clamp tiny rounding negatives to 0; drop materially negative rows (< -0.005)."""
    if df.empty:
        return df, 0, 0
    tiny_mask = df["value"].between(-0.005, 0, inclusive="left")
    neg_mask = df["value"] < -0.005
    tiny = int(tiny_mask.sum())
    dropped = int(neg_mask.sum())
    if tiny:
        df.loc[tiny_mask, "value"] = 0.0
    if dropped:
        df = df[~neg_mask].copy()
    return df, tiny, dropped


def normalize(
    in_path: pathlib.Path = BRONZE_FILE, out_path: pathlib.Path = SILVER_FILE
) -> pathlib.Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(in_path)

    area_code = pick_col(df, "REF_AREA", "REF_AREA_CODE", "REF_AREA.ID", "Reference area code")
    area_name = pick_col(df, "Reference area", "REF_AREA_LABEL", "Country", "Country name")
    rev_code = pick_col(
        df, "REVENUE_CODE", "Revenue code", "STANDARD_REVENUE", "Revenue category", "REVENUE"
    )
    time_col = pick_col(df, "TIME_PERIOD", "Time period", "time", "year", "Year")
    val_col = pick_col(df, "OBS_VALUE", "Observation value", "value", "Value")
    unit_code = pick_col(df, "UNIT_MEASURE", "UNIT_MEASURE_CODE", "Unit of measure code")
    unit_lab = pick_col(df, "Unit of measure", "UNIT_MEASURE_LABEL", "Unit label", "Unit")
    meas_code = pick_col(df, "MEASURE", "MEASURE_CODE", "Reference measure code")
    meas_lab = pick_col(df, "Measure", "Reference measure", "MEASURE_LABEL")

    need = [
        ("area", area_code or area_name),
        ("revenue_code", rev_code),
        ("time", time_col),
        ("value", val_col),
    ]
    missing = [n for n, c in need if c is None]
    if missing:
        raise KeyError(f"Required columns not found: {missing}; have={list(df.columns)}")

    keep = {
        "iso3": area_code or area_name,
        "country": area_name or area_code,
        "tax_code": rev_code,
        "year": time_col,
        "value": val_col,
    }
    if unit_code:
        keep["unit_code"] = unit_code
    if unit_lab:
        keep["unit"] = unit_lab
    if meas_code:
        keep["measure_code"] = meas_code
    if meas_lab:
        keep["measure"] = meas_lab

    sub = df[list(keep.values())].copy()
    sub.columns = list(keep.keys())

    sub["iso3"] = sub["iso3"].astype("string").str.upper()
    sub["country"] = sub["country"].astype("string")
    sub = sub[sub["year"].astype(str).str.match(r"^\d{4}$")]
    sub["year"] = sub["year"].astype(int)
    sub["value"] = pd.to_numeric(sub["value"], errors="coerce")

    # Metric detection: prefer codes; otherwise use strict labels (require BOTH parts)
    mc = (
        _lower(sub["measure_code"]) if "measure_code" in sub.columns else pd.Series([""] * len(sub))
    )
    uc = _lower(sub["unit_code"]) if "unit_code" in sub.columns else pd.Series([""] * len(sub))
    ml = _lower(sub["measure"]) if "measure" in sub.columns else pd.Series([""] * len(sub))
    ul = _lower(sub["unit"]) if "unit" in sub.columns else pd.Series([""] * len(sub))
    combo = (ml.fillna("") + " " + ul.fillna("")).str.strip()

    # GDP %: code contains pc_gdp (or pctgdp variants) OR (label has percentage/% AND gdp)
    is_gdp = (
        mc.str.contains(r"\bpc[_]?gdp\b|\bpct[_]?gdp\b|\bpcgdp\b", regex=True, na=False)
        | uc.str.contains(r"\bpc[_]?gdp\b|\bpct[_]?gdp\b|\bpcgdp\b", regex=True, na=False)
        | (
            combo.str.contains(r"(?:percent|percentage|%)", regex=True, na=False)
            & combo.str.contains(r"\bgdp\b", regex=True, na=False)
        )
    )

    # Share of total: code contains 'share' OR labels contain BOTH 'share' and 'total'
    is_share = (
        mc.str.contains(r"share", regex=True, na=False)
        | uc.str.contains(r"share", regex=True, na=False)
        | (
            combo.str.contains(r"\bshare\b", regex=True, na=False)
            & combo.str.contains(r"\btotal\b", regex=True, na=False)
        )
    )

    df_gdp = sub[is_gdp].copy()
    df_share = sub[is_share].copy()

    # Persist label samples for quick debugging
    cols = [c for c in ["unit_code", "unit", "measure_code", "measure"] if c in sub.columns]
    sub[cols].drop_duplicates().head(200).to_csv(LABELS_SAMPLE, index=False)

    # Sanitize values (clamp tiny negatives; drop large negatives) BEFORE validation
    gdp_tiny, gdp_drop = 0, 0
    share_tiny, share_drop = 0, 0
    df_gdp, gdp_tiny, gdp_drop = _sanitize(df_gdp)
    df_share, share_tiny, share_drop = _sanitize(df_share)

    SCHEMA = pa.DataFrameSchema(
        {
            "iso3": pa.Column(str, nullable=False),
            "country": pa.Column(object, nullable=True),
            "tax_code": pa.Column(str, nullable=False),
            "year": pa.Column(int, checks=pa.Check.ge(1900), nullable=False),
            "value": pa.Column(float, checks=[pa.Check.ge(0), pa.Check.le(100)], nullable=True),
        },
        coerce=True,
    )

    if not df_gdp.empty:
        SCHEMA.validate(df_gdp, lazy=True)
    if not df_share.empty:
        SCHEMA.validate(df_share, lazy=True)

    silver = (
        pd.concat(
            [df_gdp.assign(metric="pct_gdp"), df_share.assign(metric="share_total")],
            ignore_index=True,
        )
        .sort_values(["iso3", "year", "metric", "tax_code"])
        .reset_index(drop=True)
    )

    DETECT_DEBUG.write_text(
        json.dumps(
            {
                "rows_total": int(len(sub)),
                "rows_gdp": int(len(df_gdp)),
                "rows_share": int(len(df_share)),
                "gdp_tiny_clamped": int(gdp_tiny),
                "gdp_dropped_neg": int(gdp_drop),
                "share_tiny_clamped": int(share_tiny),
                "share_dropped_neg": int(share_drop),
                "has_measure_code": "measure_code" in sub.columns,
                "has_unit_code": "unit_code" in sub.columns,
                "sample_labels_path": str(LABELS_SAMPLE),
            },
            indent=2,
        )
    )

    print("Detector:", json.loads(DETECT_DEBUG.read_text()))

    silver.to_parquet(out_path, index=False)
    silver.head(500).to_csv(SILVER_SAMPLE, index=False)
    print(f"Wrote silver parquet: {out_path}")
    return out_path


def main() -> None:
    normalize()


if __name__ == "__main__":
    main()
