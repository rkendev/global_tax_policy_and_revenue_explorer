import pathlib

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Global Tax Policy & Revenue Explorer", layout="wide")
st.title("Global Tax Policy & Revenue Explorer — MVP")
st.caption(
    "Source: OECD Revenue Statistics (SDMX). Last updated: "
    + __import__("datetime")
    .datetime.fromtimestamp(
        __import__("pathlib").Path("data/gold/tax_to_gdp.parquet").stat().st_mtime
    )
    .strftime("%Y-%m-%d %H:%M:%S")
)

gold_dir = pathlib.Path("data/gold")
t2g_pq = gold_dir / "tax_to_gdp.parquet"
comp_pq = gold_dir / "composition.parquet"

if not (t2g_pq.exists() and comp_pq.exists()):
    st.warning("Gold datasets not found. Run **make etl** first to generate sample data.")
    st.stop()

t2g = pd.read_parquet(t2g_pq)
comp = pd.read_parquet(comp_pq)

countries = sorted(t2g["country"].unique())
years = sorted(t2g["year"].unique())

left, right = st.columns([1, 3])
with left:
    country = st.selectbox("Country", countries, index=0)
    year = st.selectbox("Year", years, index=len(years) - 1)

with right:
    st.subheader(f"Tax-to-GDP — {country} ({year})")
    sel = t2g[(t2g["country"] == country) & (t2g["year"] == year)]
    if sel.empty:
        st.info("No data for selection.")
    else:
        value = float(sel["tax_to_gdp"].iloc[0])
        st.metric(label="Tax-to-GDP (%)", value=f"{value:.1f}")

    st.subheader("Composition (share of total tax, %)")
    csel = comp[(comp["country"] == country) & (comp["year"] == year)]
    if not csel.empty:
        st.bar_chart(csel.set_index("tax_code")["share_pct"])
    else:
        st.info("No composition data for selection.")
