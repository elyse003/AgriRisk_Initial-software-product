"""Esoko Rwanda market-price ingestion (esoko.rw/price-trends export).

The Esoko "Market Price Entries" export has farmgate / wholesale / retail prices,
but the **province and district columns are empty** and the product names are in
Kinyarwanda with varieties/grades. This script:

  * maps each `market` (kamembe, butare, kibuye, ...) -> district + province,
  * maps the Kinyarwanda product names to the app's three crops, averaging the
    varieties (Ibishyimbo *, Ibirayi grades) into one price per crop, and keeping
    MAIZE GRAIN only (Ibigori) -- not the "Ifu - Ibigori" flour brands,
  * keeps the FARMGATE price (what the farmer actually receives),
  * aggregates to one monthly price per crop/district, and
  * APPENDS to data/processed/esoko_farmgate_prices.csv, de-duplicating by
    (date, district, crop), so repeated downloads accumulate history over time.

Run:  python scripts/prepare_esoko.py ["path/to/export.csv or .xlsx"]
      (defaults to data/raw/esoko_market_prices.csv)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "esoko_farmgate_prices.csv"

# Esoko leaves province/district blank; map the market name instead.
# '# confirm' rows are best-effort (the same sector name exists in several
# districts) -- correct the district if a market is actually elsewhere.
MARKET_TO_DISTRICT = {
    # --- confident ---
    "kamembe": ("Rusizi", "Western"),
    "bugarama": ("Rusizi", "Western"),
    "nkora": ("Rutsiro", "Western"),
    "kibuye": ("Karongi", "Western"),
    "butare": ("Huye", "Southern"),
    "gasarenda": ("Nyamagabe", "Southern"),
    "kibungo": ("Ngoma", "Eastern"),
    "karenge": ("Rwamagana", "Eastern"),
    "matimba": ("Nyagatare", "Eastern"),
    "musanze": ("Musanze", "Northern"),
    "kicukiro-center": ("Kicukiro", "Kigali City"),
    "gahanga": ("Kicukiro", "Kigali City"),
    "nyabugogo": ("Nyarugenge", "Kigali City"),
    # --- best-effort: CONFIRM these (same sector name can exist in >1 district) ---
    "gahoromani": ("Kirehe", "Eastern"),     # confirm
    "karambi": ("Huye", "Southern"),         # confirm
    "birambo": ("Karongi", "Western"),       # confirm
    "kirambo": ("Burera", "Northern"),       # confirm
    "mulindi": ("Gicumbi", "Northern"),      # confirm
    "nyagahinga": ("Burera", "Northern"),    # confirm
    "mubyangabo": ("Musanze", "Northern"),   # confirm (uncertain)
}


def to_crop(name: str):
    """Map a Kinyarwanda product name to maize / beans / potatoes, or None."""
    n = (name or "").strip().lower()
    if "ifu" in n or "ibiryo" in n or "bran" in n:   # flour / animal feed, not the crop
        return None
    if n == "ibigori":                                # maize GRAIN only
        return "maize"
    if n.startswith("ibishyimbo"):                    # bean varieties
        return "beans"
    if "ibirayi" in n:                                # Irish-potato grades (Amateke excluded)
        return "potatoes"
    return None


def prepare(src):
    df = pd.read_excel(src) if str(src).lower().endswith((".xlsx", ".xls")) else pd.read_csv(src)
    cols = {str(c).lower().strip(): c for c in df.columns}

    def col(*cands):
        for c in cands:
            if c in cols:
                return cols[c]
        raise KeyError(f"none of {cands} in {list(cols)}")

    c_prod = col("product name en", "commodity_name_en", "product name", "commodity_name")
    c_mkt = col("markets", "market_name")
    c_date = col("date")
    c_farm = col("farmgate price", "farmgate_average_price")

    d = pd.DataFrame({
        "product": df[c_prod].astype(str),
        "market": df[c_mkt].astype(str).str.lower().str.strip(),
        # Esoko dates look like "Mon Jun 22 2026 13:28:47 GMT+0200 (...)" -> trim the tz text
        "date": pd.to_datetime(df[c_date].astype(str).str.replace(r"\s*GMT.*$", "", regex=True),
                               errors="coerce"),
        "farmgate": pd.to_numeric(df[c_farm], errors="coerce"),
    })
    d["crop"] = d["product"].map(to_crop)
    d = d.dropna(subset=["crop", "farmgate", "date"])
    d = d[d["farmgate"] > 0]

    unknown = sorted(set(d.loc[~d["market"].isin(MARKET_TO_DISTRICT), "market"]))
    if unknown:
        print("WARNING: unmapped markets (add them to MARKET_TO_DISTRICT):", unknown)
    d = d[d["market"].isin(MARKET_TO_DISTRICT)].copy()
    d["district"] = d["market"].map(lambda m: MARKET_TO_DISTRICT[m][0])
    d["province"] = d["market"].map(lambda m: MARKET_TO_DISTRICT[m][1])
    d["date"] = d["date"].values.astype("datetime64[M]")   # one figure per month

    agg = (d.groupby(["date", "province", "district", "crop"])["farmgate"]
             .mean().round().reset_index().rename(columns={"farmgate": "price_rwf"}))

    if OUT.exists():                                       # accumulate across downloads
        prev = pd.read_csv(OUT, parse_dates=["date"])
        agg = pd.concat([prev, agg], ignore_index=True)
    agg = (agg.sort_values("date")
              .drop_duplicates(["date", "district", "crop"], keep="last")
              .sort_values(["crop", "district", "date"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(OUT, index=False)
    print(f"wrote {OUT}\n  {len(agg)} rows · {agg['crop'].nunique()} crops · "
          f"{agg['district'].nunique()} districts · {agg['date'].min():%Y-%m}..{agg['date'].max():%Y-%m}")
    return agg


if __name__ == "__main__":
    prepare(sys.argv[1] if len(sys.argv) > 1 else RAW / "esoko_market_prices.csv")