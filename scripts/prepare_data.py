"""Convert the REAL downloaded files into the clean canonical CSVs the apps expect,
written to data/processed/. Also (re)trains the risk model on the real data.

Run once after placing the real files in data/raw/:
    python scripts/prepare_data.py

Then run the dashboard (streamlit run dashboard/Home.py). It auto-prefers data/processed/.
"""
from __future__ import annotations

import json
import pickle
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DATA_RAW, DATA_PROCESSED, MODELS_STORE

DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# Standard Rwanda ADM2 P-codes -> district name (verify vs official COD if possible)
PCODE2DISTRICT = {
    "RW11": "Nyarugenge", "RW12": "Gasabo", "RW13": "Kicukiro",
    "RW21": "Nyanza", "RW22": "Gisagara", "RW23": "Nyaruguru", "RW24": "Huye",
    "RW25": "Nyamagabe", "RW26": "Ruhango", "RW27": "Muhanga", "RW28": "Kamonyi",
    "RW31": "Karongi", "RW32": "Rutsiro", "RW33": "Rubavu", "RW34": "Nyabihu",
    "RW35": "Ngororero", "RW36": "Rusizi", "RW37": "Nyamasheke",
    "RW41": "Rulindo", "RW42": "Gakenke", "RW43": "Musanze", "RW44": "Burera", "RW45": "Gicumbi",
    "RW51": "Rwamagana", "RW52": "Nyagatare", "RW53": "Gatsibo", "RW54": "Kayonza",
    "RW55": "Kirehe", "RW56": "Ngoma", "RW57": "Bugesera",
}
CROP_MAP = {"Maize": "maize", "Beans (dry)": "beans", "Potatoes (Irish)": "potatoes"}


def prep_prices():
    w = pd.read_csv(DATA_RAW / "wfp_food_prices_rwa.csv", parse_dates=["date"])
    w = w[(w["pricetype"] == "Retail") & (w["currency"] == "RWF")]
    w = w[w["commodity"].isin(CROP_MAP)].copy()
    w["crop"] = w["commodity"].map(CROP_MAP)
    w = w[w["admin2"] != "Administrative unit not available"]
    w["market"] = w["admin2"]
    w["date"] = w["date"].values.astype("datetime64[M]")
    out = (w.groupby(["crop", "market", "date"])["price"].mean()
             .reset_index().rename(columns={"price": "price_rwf"}))
    out[["date", "market", "crop", "price_rwf"]].to_csv(
        DATA_PROCESSED / "wfp_food_prices_rwanda.csv", index=False)
    return out


def _find_cpi_file():
    for n in ["CPI_time_series_April_2026.xlsx", "CPI_time_series_April_2026.xls"]:
        if (DATA_RAW / n).exists():
            return DATA_RAW / n
    return None


def _prep_cpi_worldbank():
    """Fallback CPI from the World Bank annual CPI file fetched by download_data.py.

    Rwanda has no public *monthly food* CPI API, so we use the World Bank headline
    CPI (2010=100, annual) as the macro-inflation feature, forward-filled to monthly
    so the YoY pct_change(12) used downstream still works. Documented as such.
    """
    f = DATA_RAW / "worldbank_cpi_rwanda.csv"
    if not f.exists():
        return None
    wb = pd.read_csv(f).dropna().sort_values("year")
    # expand annual -> monthly (value stamped at mid-year, then interpolate/ffill)
    wb["date"] = pd.to_datetime(wb["year"].astype(str) + "-07-01")
    monthly = (wb.set_index("date")["cpi"]
                 .resample("MS").interpolate("linear")
                 .reset_index().rename(columns={"cpi": "food_cpi"}))
    monthly["date"] = monthly["date"].values.astype("datetime64[M]")
    monthly[["date", "food_cpi"]].to_csv(DATA_PROCESSED / "rwanda_food_cpi.csv", index=False)
    return monthly


def prep_cpi():
    f = _find_cpi_file()
    if f is None:
        cpi = _prep_cpi_worldbank()
        if cpi is None:
            print("  ! No CPI source (NISR file or World Bank file) found; keeping existing.")
        else:
            print("  cpi: World Bank headline CPI (annual -> monthly), no NISR file present.")
        return cpi
    eng = "openpyxl" if f.suffix == ".xlsx" else "xlrd"
    raw = pd.read_excel(f, sheet_name="All Rwanda", header=None, engine=eng)
    hdr = raw[raw.apply(lambda r: r.astype(str).str.contains("Weights", case=False).any(), axis=1)].index[0]
    wcol = raw.iloc[hdr].astype(str).str.contains("Weights", case=False)
    widx = wcol[wcol].index[0]
    dcols = list(range(widx + 1, raw.shape[1]))
    dates = pd.to_datetime(raw.iloc[hdr, dcols].values, errors="coerce")
    fidx = raw[raw.apply(lambda r: r.astype(str).str.startswith("Food and non").any(), axis=1)].index[0]
    vals = pd.to_numeric(raw.iloc[fidx, dcols], errors="coerce").values
    cpi = pd.DataFrame({"date": dates, "food_cpi": vals}).dropna().sort_values("date")
    cpi["date"] = cpi["date"].values.astype("datetime64[M]")
    cpi.to_csv(DATA_PROCESSED / "rwanda_food_cpi.csv", index=False)
    return cpi


def prep_fertilizer():
    f = DATA_RAW / "CMO-Historical-Data-Monthly.xlsx"
    if not f.exists():
        print("  ! World Bank CMO file not found; using existing canonical fertilizer as fallback.")
        for src in [DATA_PROCESSED / "fertilizer_price_index.csv", DATA_RAW / "fertilizer_price_index.csv"]:
            if src.exists():
                fb = pd.read_csv(src, parse_dates=["date"])
                fb["date"] = fb["date"].values.astype("datetime64[M]")
                fb[["date", "fert_index"]].to_csv(DATA_PROCESSED / "fertilizer_price_index.csv", index=False)
                return fb
        return None
    raw = pd.read_excel(f, sheet_name="Monthly Indices", header=None)
    mask = raw[0].astype(str).str.match(r"^\d{4}M\d{2}$")
    fert = raw.loc[mask, [0, 13]].copy()
    fert.columns = ["period", "fert_index"]
    fert["date"] = pd.to_datetime(fert["period"].str.replace("M", "-") + "-01", errors="coerce")
    fert["fert_index"] = pd.to_numeric(fert["fert_index"], errors="coerce")
    fert = fert.dropna().sort_values("date")
    fert["date"] = fert["date"].values.astype("datetime64[M]")
    fert[["date", "fert_index"]].to_csv(DATA_PROCESSED / "fertilizer_price_index.csv", index=False)
    return fert


def prep_rainfall():
    raw = pd.read_csv(DATA_RAW / "rwa-rainfall-subnat-full.csv", parse_dates=["date"])
    r = raw[raw["adm_level"] == 2].copy()
    r["district"] = r["PCODE"].map(PCODE2DISTRICT)
    r = r.dropna(subset=["district", "rfq"])
    r["date"] = r["date"].values.astype("datetime64[M]")
    rain = r.groupby(["district", "date"])["rfq"].mean().reset_index()
    rain["dev"] = rain["rfq"] / 100 - 1
    rain["rainfall_anomaly"] = rain.groupby("district")["dev"].transform(
        lambda s: (s - s.mean()) / s.std())
    rain["season"] = rain["date"].dt.month.map(
        lambda m: "A" if m in (3, 4, 5) else ("B" if m in (10, 11, 12) else "off"))
    rain[["date", "district", "season", "rainfall_anomaly"]].to_csv(
        DATA_PROCESSED / "district_rainfall_anomalies.csv", index=False)
    return rain


def prep_inputs():
    for n in ["minagri_input_prices_real.csv", "minagri_input_prices.csv"]:
        f = DATA_RAW / n
        if f.exists():
            df = pd.read_csv(f)
            if "supplier" not in df.columns:  # real subsidy file -> canonical
                df["supplier"] = df.get("availability", "Smart Nkunganire System")
                df["district"] = "Nationwide"
            cols = ["input_id", "input_name", "input_type", "crop_suitability",
                    "supplier", "district", "price_rwf"]
            df = df[[c for c in cols if c in df.columns]]
            df.to_csv(DATA_PROCESSED / "minagri_input_prices.csv", index=False)
            return df
    print("  ! No input price file found.")
    return None


def _write_last_updated(pr, cpi, fert, rain):
    """Record how current each series is, for the dashboard's freshness caption."""
    def through(df, col="date"):
        return pd.to_datetime(df[col]).max().strftime("%Y-%m") if df is not None and len(df) else None
    status = {
        "wfp_prices": {"data_through": through(pr)},
        "cpi": {"data_through": through(cpi)},
        "fertilizer": {"data_through": through(fert)},
        "rainfall": {"data_through": through(rain)},
    }
    json.dump(status, open(DATA_PROCESSED / "last_updated.json", "w"), indent=2)


def main():
    print("Preparing real data -> data/processed/ ...")
    pr = prep_prices();   print(f"  prices: {len(pr)} rows, {pr.market.nunique()} districts, crops={list(pr.crop.unique())}")
    cpi = prep_cpi();     print(f"  cpi: {0 if cpi is None else len(cpi)} months")
    fert = prep_fertilizer(); print(f"  fertilizer: {'fallback' if fert is None else str(len(fert))+' months'}")
    rain = prep_rainfall(); print(f"  rainfall: {len(rain)} district-months, {rain.district.nunique()} districts")
    inp = prep_inputs();  print(f"  inputs: {0 if inp is None else len(inp)} items")
    _write_last_updated(pr, cpi, fert, rain)
    print("Done. Next: python scripts/train_models.py  (trains + serializes the models)")


if __name__ == "__main__":
    main()
