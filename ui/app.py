# ui/app.py
from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# ----------------------------- Config & utils ------------------------------

ROOT = Path(__file__).resolve().parents[1]
DATA_GOLD = ROOT / "data" / "gold"
BRONZE_META = ROOT / "data" / "bronze" / "oecd_rev_comp.meta.json"

st.set_page_config(
    page_title="Global Tax Policy & Revenue Explorer — MVP",
    layout="wide",
)


def clamp_numeric(s: pd.Series, lo: float, hi: float) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").fillna(0.0)
    return s.clip(lower=lo, upper=hi)


def last_updated_utc() -> str:
    # prefer bronze meta (from the download step); fall back to file mtime
    try:
        if BRONZE_META.exists():
            meta = json.loads(BRONZE_META.read_text())
            # OECD SDMX fetch timestamp if present
            if "fetched_at" in meta:
                return str(meta["fetched_at"])
    except Exception:
        pass
    # fallback: most recent gold file mtime
    try:
        mtimes = [f.stat().st_mtime for f in DATA_GOLD.glob("*.parquet")]
        if mtimes:
            import datetime as dt

            return dt.datetime.utcfromtimestamp(max(mtimes)).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        pass
    return "unknown"


# ----------------------------- Data loading --------------------------------


@st.cache_data(show_spinner=False)
def load_gold() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (tax_to_gdp_df, composition_df) with canonical column names."""
    tax_path = DATA_GOLD / "tax_to_gdp.parquet"
    comp_path = DATA_GOLD / "composition.parquet"

    tax = pd.read_parquet(tax_path)
    comp = pd.read_parquet(comp_path)

    # Canonicalize column names (lowercase + expected names)
    tax.columns = [c.lower() for c in tax.columns]
    comp.columns = [c.lower() for c in comp.columns]

    # tax: accept either 'tax_to_gdp' or a generic 'value'
    if "tax_to_gdp" not in tax.columns and "value" in tax.columns:
        tax = tax.rename(columns={"value": "tax_to_gdp"})

    # comp: accept either 'share_pct' or 'share'
    if "share" not in comp.columns and "share_pct" in comp.columns:
        comp = comp.rename(columns={"share_pct": "share"})
    # Some pipelines export 'pct' or 'share_percent'
    if "share" not in comp.columns and "pct" in comp.columns:
        comp = comp.rename(columns={"pct": "share"})
    if "share" not in comp.columns and "share_percent" in comp.columns:
        comp = comp.rename(columns={"share_percent": "share"})

    # Basic type hygiene
    if "year" in tax.columns:
        tax["year"] = pd.to_numeric(tax["year"], errors="coerce").astype("Int64")
    if "year" in comp.columns:
        comp["year"] = pd.to_numeric(comp["year"], errors="coerce").astype("Int64")

    return tax, comp


# ----------------------------- Slicers (cached) ----------------------------


@st.cache_data(show_spinner=False)
def tax_slice(
    tax_df: pd.DataFrame, countries: tuple[str, ...], year_min: int, year_max: int
) -> pd.DataFrame:
    out = tax_df[
        tax_df["country"].isin(countries)
        & (tax_df["year"] >= year_min)
        & (tax_df["year"] <= year_max)
    ].copy()
    out["tax_to_gdp"] = clamp_numeric(out["tax_to_gdp"], 0, 1000)
    return out


def _rebalance_to_100(df: pd.DataFrame) -> pd.DataFrame:
    """Make each country's composition sum to exactly 100.0 after rounding."""

    def fix(group: pd.DataFrame) -> pd.DataFrame:
        group = group.copy()
        group["share"] = clamp_numeric(group["share"], 0, 1000)
        # Normalize to 100 first to dampen odd inputs
        s = group["share"].sum()
        if s and s > 0:
            group["share"] = group["share"] / s * 100.0
        # Round to 1 decimal (or keep full precision; 1dp is friendly)
        group["share"] = group["share"].round(1)
        # Nudge the largest bucket so sums are exactly 100.0
        diff = 100.0 - group["share"].sum()
        if abs(diff) >= 0.05:  # only if meaningfully off
            idx = group["share"].idxmax()
            group.loc[idx, "share"] = (group.loc[idx, "share"] + diff).round(1)
        else:
            # tiny residuals go to first row to avoid -0.0
            if not group.empty:
                idx = group.index[0]
                group.loc[idx, "share"] = (group.loc[idx, "share"] + diff).round(1)
        return group

    return df.groupby("country", group_keys=False).apply(fix)


@st.cache_data(show_spinner=False)
def composition_slice(comp_df: pd.DataFrame, countries: tuple[str, ...], year: int) -> pd.DataFrame:
    df = comp_df[comp_df["country"].isin(countries) & (comp_df["year"] == year)].copy()

    # Ensure required columns exist
    for need in ("country", "tax_code", "share"):
        if need not in df.columns:
            # Fail fast with a descriptive message in the UI
            raise KeyError(f"composition parquet missing column '{need}'")

    df = _rebalance_to_100(df)
    return df[["country", "tax_code", "share"]]


# ----------------------------- Charts --------------------------------------


def tax_lines_chart(df: pd.DataFrame) -> alt.Chart:
    base = alt.Chart(df)
    line = base.mark_line(point=True).encode(
        x=alt.X("year:O", title="Year"),
        y=alt.Y("tax_to_gdp:Q", title="Tax-to-GDP (%)"),
        color=alt.Color("country:N", title="Country"),
        tooltip=[
            alt.Tooltip("country:N"),
            alt.Tooltip("year:O"),
            alt.Tooltip("tax_to_gdp:Q", title="Tax-to-GDP (%)"),
        ],
    )
    return line.properties(height=320)


def stacked_comp_chart(df: pd.DataFrame, x: str) -> alt.Chart:
    # x is either "country" (Compare tab) or "tax_code" (Overview)
    base = alt.Chart(df)
    bar = base.mark_bar().encode(
        x=alt.X(f"{x}:N", title=x.replace("_", " ").title()),
        y=alt.Y("share:Q", title="Composition (% of total tax)", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("tax_code:N", title="tax_code"),
        tooltip=[
            alt.Tooltip("country:N"),
            alt.Tooltip("tax_code:N", title="Tax code"),
            alt.Tooltip("share:Q", title="Share (%)"),
        ],
    )
    return bar.properties(height=360)


# ----------------------------- UI blocks -----------------------------------


def render_overview(tax_df: pd.DataFrame, comp_df: pd.DataFrame) -> None:
    countries = tuple(sorted(tax_df["country"].unique()))
    years = tuple(sorted(tax_df["year"].dropna().unique()))

    c = st.selectbox("Country", countries, index=0)
    y = st.selectbox("Year", years, index=len(years) - 1)

    # KPI
    tax_one = tax_df[(tax_df["country"] == c) & (tax_df["year"] == y)]
    val = float(tax_one["tax_to_gdp"].iloc[0]) if not tax_one.empty else float("nan")
    st.subheader(f"Tax-to-GDP — {c} ({y})")
    st.write(f"**{val:.1f}**")

    # Composition for the selected country/year
    comp_one = composition_slice(comp_df, (c,), int(y))
    st.subheader("Composition (share of total tax, %)")
    st.altair_chart(stacked_comp_chart(comp_one, x="tax_code"), use_container_width=True)


def render_compare(tax_df: pd.DataFrame, comp_df: pd.DataFrame) -> None:
    st.header("Compare countries")
    countries = tuple(sorted(tax_df["country"].unique()))
    years = tuple(sorted(tax_df["year"].dropna().unique()))
    y_min, y_max = int(min(years)), int(max(years))

    sel = st.multiselect("Countries (max 5)", countries, default=list(countries)[:5])
    if len(sel) > 5:
        sel = sel[:5]
    rng = st.slider(
        "Year range", min_value=y_min, max_value=y_max, value=(max(y_min, y_max - 7), y_max)
    )
    comp_year = st.slider("Composition year", min_value=y_min, max_value=y_max, value=y_max)

    if not sel:
        st.info("Select at least one country.")
        return

    # Tax-to-GDP lines
    lines_df = tax_slice(tax_df, tuple(sel), rng[0], rng[1])
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.subheader("Tax-to-GDP (%, by year)")
        st.altair_chart(tax_lines_chart(lines_df), use_container_width=True)
        # CSV download for lines
        csv_lines = (
            lines_df[["country", "year", "tax_to_gdp"]]
            .sort_values(["country", "year"])
            .to_csv(index=False)
        )
        st.download_button(
            "Download Tax-to-GDP CSV",
            data=csv_lines,
            file_name=f"tax_to_gdp_{rng[0]}_{rng[1]}_{len(sel)}c.csv",
            mime="text/csv",
        )

    # Composition stacks by country
    comp_df_s = composition_slice(comp_df, tuple(sel), int(comp_year))
    with right:
        st.subheader("Composition (share of total tax, %)")
        # group by country so each column sums to 100
        st.altair_chart(stacked_comp_chart(comp_df_s, x="country"), use_container_width=True)
        # CSV download for composition
        csv_comp = (
            comp_df_s[["country", "tax_code", "share"]]
            .sort_values(["country", "tax_code"])
            .to_csv(index=False)
        )
        st.download_button(
            "Download Composition CSV",
            data=csv_comp,
            file_name=f"composition_{comp_year}_{len(sel)}c.csv",
            mime="text/csv",
        )


# ----------------------------- Main ----------------------------------------


def main() -> None:
    st.caption(f"Source: OECD Revenue Statistics (SDMX) • Last updated: {last_updated_utc()}")

    tax_df, comp_df = load_gold()

    tab1, tab2 = st.tabs(["Overview", "Compare"])
    with tab1:
        render_overview(tax_df, comp_df)
    with tab2:
        render_compare(tax_df, comp_df)


if __name__ == "__main__":
    main()
