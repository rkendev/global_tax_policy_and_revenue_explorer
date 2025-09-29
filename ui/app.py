from __future__ import annotations

import io
import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# ---- App setup ----
st.set_page_config(page_title="Global Tax Explorer", layout="wide")
alt.data_transformers.disable_max_rows()  # avoid hard 5k-row limit in dev


# ---------- Data loaders ----------
@st.cache_data(show_spinner=False)
def load_gold():
    """Load gold-layer metrics + minimal metadata."""
    t2g = pd.read_parquet("data/gold/tax_to_gdp.parquet")
    comp = pd.read_parquet("data/gold/composition.parquet")

    meta_path = Path("data/silver/_detector_debug.json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    countries = sorted(t2g["country"].dropna().unique().tolist())
    years = sorted(t2g["year"].dropna().unique().tolist())
    return t2g, comp, meta, countries, years


t2g, comp, meta, countries_all, years_all = load_gold()
min_year, max_year = min(years_all), max(years_all)

tabs = st.tabs(["Overview", "Compare"])  # keep existing Overview content as-is

with tabs[1]:
    st.subheader("Compare countries")

    # --- Inputs ---
    sel_countries = st.multiselect(
        "Countries (max 5)",
        options=countries_all,
        default=countries_all[:3],
        max_selections=5,  # enforce ≤5 (Streamlit API)
    )
    if not sel_countries:
        st.info("Pick 1–5 countries to compare.")
        st.stop()

    year_range = st.slider(
        "Year range",
        min_value=min_year,
        max_value=max_year,
        value=(max(min_year, 2010), max_year),
    )
    y0, y1 = year_range

    comp_year = st.select_slider(
        "Composition year",
        options=list(range(y0, y1 + 1)),
        value=y1,
    )

    topN = st.selectbox(
        "Legend size (Top-N tax codes; 0 = All)",
        options=[0, 5, 10, 15],
        index=0,
        help="Keeps stacked legend readable. Non-top codes collapse into 'Other'.",
    )

    # --- Tax-to-GDP series (panelized to expose gaps; no fabricated data) ---
    panel = (
        pd.MultiIndex.from_product(
            [sel_countries, range(y0, y1 + 1)],
            names=["country", "year"],
        )
        .to_frame(index=False)
        .sort_values(["country", "year"])
    )

    series = (
        panel.merge(
            t2g[["country", "year", "tax_to_gdp"]],
            on=["country", "year"],
            how="left",
        )
        .sort_values(["country", "year"])
        .reset_index(drop=True)
    )

    # Warn if the selection yields no data (edge case)
    if series["tax_to_gdp"].notna().sum() == 0:
        st.warning("No Tax-to-GDP values for this selection.")
    line = (
        alt.Chart(series)
        .mark_line(point=True)
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y("tax_to_gdp:Q", title="Tax-to-GDP (%)"),
            color=alt.Color("country:N", legend=alt.Legend(title="Country")),
            tooltip=[
                "country",
                "year",
                alt.Tooltip("tax_to_gdp:Q", format=".1f", title="Tax-to-GDP (%)"),
            ],
        )
        .properties(height=320)
    )

    # --- Composition (selected year) ---
    comp_slice = comp.query("year == @comp_year and country in @sel_countries")[
        ["country", "tax_code", "share_pct"]
    ].copy()

    if topN:
        # Collapse non-top codes into 'Other' to keep legend manageable
        totals = (
            comp_slice.groupby("tax_code", as_index=False)["share_pct"]
            .sum()
            .sort_values("share_pct", ascending=False)
        )
        top_codes = set(totals.head(topN)["tax_code"].tolist())
        comp_slice["tax_code"] = np.where(
            comp_slice["tax_code"].isin(top_codes), comp_slice["tax_code"], "Other"
        )
        comp_slice = comp_slice.groupby(["country", "tax_code"], as_index=False)["share_pct"].sum()

    # Ensure stable stacking order
    comp_slice = comp_slice.sort_values(["country", "tax_code"]).reset_index(drop=True)

    bars = (
        alt.Chart(comp_slice)
        .mark_bar()
        .encode(
            x=alt.X("country:N", title="Country"),
            y=alt.Y(
                "share_pct:Q",
                title="Composition (% of total tax)",
                scale=alt.Scale(domain=[0, 100]),  # lock to 0–100
            ),
            color=alt.Color(
                "tax_code:N",
                legend=alt.Legend(title="Tax code"),
                scale=alt.Scale(scheme="category20b"),  # robust categorical palette
            ),
            order=alt.Order("tax_code:N"),
            tooltip=[
                "country",
                "tax_code",
                alt.Tooltip("share_pct:Q", format=".1f", title="Share (%)"),
            ],
        )
        .properties(height=320)
    )

    # --- Layout ---
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.altair_chart(line, use_container_width=True)
        # Download CSV for the series shown
        buf = io.BytesIO(series[["country", "year", "tax_to_gdp"]].to_csv(index=False).encode())
        st.download_button(
            "Download Tax-to-GDP CSV",
            data=buf,
            file_name="tax_to_gdp_compare.csv",
            mime="text/csv",
        )

    with col2:
        st.altair_chart(bars, use_container_width=True)
        buf2 = io.BytesIO(
            comp_slice[["country", "tax_code", "share_pct"]].to_csv(index=False).encode()
        )
        st.download_button(
            "Download Composition CSV",
            data=buf2,
            file_name=f"composition_{comp_year}.csv",
            mime="text/csv",
        )

    # Attribution (OECD SDMX terms require source citation)
    snap = meta.get("snapshot") or meta.get("fetched_at") or ""
    st.caption(f"Source: OECD (SDMX) • Last updated: {snap}")
