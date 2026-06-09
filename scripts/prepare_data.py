"""Convert the REAL downloaded files into the clean canonical CSVs the apps expect,
written to data/processed/. Also (re)trains the risk model on the real data.

Run once after placing the real files in data/raw/:
    python scripts/prepare_data.py

Then run the app (webapp/app.py or dashboard/Home.py) — it auto-prefers data/processed/.
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


def prep_cpi():
    f = _find_cpi_file()
    if f is None:
        print("  ! CPI file not found; keeping existing canonical CPI.")
        return None
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


def label_risk(rain_a, cpi_c, fert_c):
    if rain_a < -0.8 and (cpi_c > 15 or fert_c > 30): return "High"
    if rain_a < -0.3 or cpi_c > 10 or fert_c > 20:    return "Medium"
    return "Low"


def train_risk(rain, cpi, fert):
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    if cpi is None or fert is None:
        print("  ! Skipping risk training (missing CPI or fertilizer).")
        return
    cpi = cpi.copy(); fert = fert.copy()
    cpi["cpi_change"] = cpi["food_cpi"].pct_change(12) * 100
    fert["fert_change"] = fert["fert_index"].pct_change(12) * 100
    df = rain[rain.season != "off"].merge(cpi[["date", "cpi_change"]], on="date", how="left")
    df = df.merge(fert[["date", "fert_change"]], on="date", how="left").dropna(
        subset=["rainfall_anomaly", "cpi_change", "fert_change"])
    df["risk_level"] = df.apply(lambda x: label_risk(x.rainfall_anomaly, x.cpi_change, x.fert_change), axis=1)
    feat = ["rainfall_anomaly", "cpi_change", "fert_change"]
    X, y = df[feat], df["risk_level"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    rf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42).fit(Xtr, ytr)
    gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, random_state=42).fit(Xtr, ytr)
    pickle.dump(rf, open(MODELS_STORE / "risk_classifier.pkl", "wb"))

    def acc(model):
        p = model.predict(Xte)
        return {"accuracy": round(accuracy_score(yte, p), 3),
                "precision": round(precision_score(yte, p, average="macro", zero_division=0), 3),
                "recall": round(recall_score(yte, p, average="macro", zero_division=0), 3),
                "f1": round(f1_score(yte, p, average="macro"), 3)}

    # real price-baseline MAPE on a well-covered series
    pr = pd.read_csv(DATA_PROCESSED / "wfp_food_prices_rwanda.csv", parse_dates=["date"])
    s = pr[(pr.crop == "maize") & (pr.market == "Musanze")].sort_values("date").set_index("date")["price_rwf"]
    mape = None
    if len(s) > 40:
        d = pd.DataFrame({"y": s})
        for lag in [1, 2, 3, 6, 12]:
            d[f"lag{lag}"] = d["y"].shift(lag)
        d["target"] = d["y"].shift(-1); d = d.dropna()
        feats = [c for c in d.columns if c.startswith("lag")]
        cc = int(len(d) * 0.8)
        reg = RandomForestRegressor(n_estimators=200, random_state=42).fit(d[feats][:cc], d["target"][:cc])
        pred = reg.predict(d[feats][cc:])
        mape = round(float(np.mean(np.abs((d["target"][cc:].values - pred) / d["target"][cc:].values)) * 100), 2)
        pickle.dump(reg, open(MODELS_STORE / "price_baseline.pkl", "wb"))

    metrics = {"risk_random_forest": acc(rf), "risk_gradient_boosting": acc(gb),
               "price_baseline_mape": mape, "n_risk_rows": len(df)}
    json.dump(metrics, open(MODELS_STORE / "metrics.json", "w"), indent=2)
    print(f"  risk rows={len(df)} classes={dict(df.risk_level.value_counts())} "
          f"RF acc={metrics['risk_random_forest']['accuracy']} price MAPE={mape}%")


def main():
    print("Preparing real data -> data/processed/ ...")
    pr = prep_prices();   print(f"  prices: {len(pr)} rows, {pr.market.nunique()} districts, crops={list(pr.crop.unique())}")
    cpi = prep_cpi();     print(f"  cpi: {0 if cpi is None else len(cpi)} months")
    fert = prep_fertilizer(); print(f"  fertilizer: {'fallback' if fert is None else str(len(fert))+' months'}")
    rain = prep_rainfall(); print(f"  rainfall: {len(rain)} district-months, {rain.district.nunique()} districts")
    inp = prep_inputs();  print(f"  inputs: {0 if inp is None else len(inp)} items")
    train_risk(rain, cpi, fert)
    print("Done. Apps will now prefer data/processed/.")


if __name__ == "__main__":
    main()
