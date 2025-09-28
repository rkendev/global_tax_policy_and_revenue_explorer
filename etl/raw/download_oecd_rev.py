from __future__ import annotations

import io
import json
import os
import pathlib
import re
import time
from urllib.parse import urlencode

import pandas as pd
import requests

BRONZE_DIR = pathlib.Path("data/bronze")
BRONZE_DIR.mkdir(parents=True, exist_ok=True)

# OECD SDMX Dataflow: Revenue Statistics comparative tables (OECD members)
# Docs: https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html
# Dataflow id seen in Data Explorer and DB.NOMICS mirrors:
#   Agency: OECD.CTP.TPS
#   Id    : DSD_REV_COMP_OECD@DF_RSOECD
DATAFLOW = "OECD.CTP.TPS,DSD_REV_COMP_OECD@DF_RSOECD"
BASE = "https://sdmx.oecd.org/public/rest/data"

START_YEAR = int(os.getenv("OECD_START_YEAR", "2010"))
COUNTRY_FILTER = os.getenv("OECD_COUNTRIES", "")  # e.g., "NLD+DEU+FRA"

OUT_CSV = BRONZE_DIR / "oecd_rev_comp.csv"
META_JSON = BRONZE_DIR / "oecd_rev_comp.meta.json"


def _parse_country_filter(raw):
    """Return list[str] of country tokens or None."""
    if not raw:
        return None
    if isinstance(raw, str):
        tokens = [t for t in re.split(r"[+,;|\s]+", raw) if t.strip()]
    else:
        try:
            tokens = list(raw)
        except TypeError:
            return None
    return [t.strip().upper() for t in tokens if t.strip()] or None


def fetch_csv() -> pd.DataFrame:
    """Download OECD CSV with labels; constrain by start year and optional countries."""
    params = {
        "startPeriod": START_YEAR,
        "dimensionAtObservation": "AllDimensions",
        "format": "csvfilewithlabels",
    }
    url = f"{BASE}/{DATAFLOW}/all?{urlencode(params)}"

    # Reasonable timeouts for CI: (connect, read)
    resp = requests.get(url, timeout=(10, 90))
    resp.raise_for_status()

    data = resp.content
    df = pd.read_csv(io.BytesIO(data))

    if COUNTRY_FILTER:
        values = _parse_country_filter(COUNTRY_FILTER)
        if values:
            candidates = ["REF_AREA", "Country", "Country code", "REF_AREA.code", "REF_AREA.label"]
            have = [c for c in candidates if c in df.columns]
            if have:
                sub = df[have].apply(lambda s: s.astype(str).str.upper())
                mask = sub.isin(values).any(axis=1)
                df = df.loc[mask].copy()

    return df


def main() -> None:
    df = fetch_csv()
    df.to_csv(OUT_CSV, index=False)
    META_JSON.write_text(
        json.dumps(
            {
                "source": "OECD SDMX CSV with labels",
                "endpoint": f"{BASE}/{DATAFLOW}",
                "start_year": START_YEAR,
                "countries": COUNTRY_FILTER or "ALL",
                "fetched_at_epoch": int(time.time()),
                "fetched_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            indent=2,
        )
    )
    print(f"Wrote bronze CSV: {OUT_CSV}")
    print(f"Wrote metadata   : {META_JSON}")


if __name__ == "__main__":
    main()
