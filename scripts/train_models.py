"""Train + evaluate models, serialize winners to models_store/, and write
metrics.json (used by the web app's Home screen). Run: PYTHONPATH=. python scripts/train_models.py
"""
import json, pickle
import numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import (RandomForestClassifier, GradientBoostingClassifier,
                              RandomForestRegressor)
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score)

from config.settings import DATA_RAW, MODELS_STORE
from src.data.preprocessing import label_risk


def build_risk():
    cpi = pd.read_csv(DATA_RAW/"rwanda_food_cpi.csv", parse_dates=["date"]).sort_values("date")
    fert = pd.read_csv(DATA_RAW/"fertilizer_price_index.csv", parse_dates=["date"]).sort_values("date")
    rain = pd.read_csv(DATA_RAW/"district_rainfall_anomalies.csv", parse_dates=["date"]).sort_values("date")
    cpi["cpi_change"] = cpi["food_cpi"].pct_change(12)*100
    fert["fert_change"] = fert["fert_index"].pct_change(12)*100
    df = pd.merge_asof(rain, cpi[["date","cpi_change"]], on="date")
    df = pd.merge_asof(df, fert[["date","fert_change"]], on="date").dropna().reset_index(drop=True)
    df["risk_level"] = df.apply(lambda r: label_risk(r.rainfall_anomaly, r.cpi_change, r.fert_change), axis=1)
    return df


def main():
    df = build_risk()
    rng = np.random.default_rng(0)
    X = df[["rainfall_anomaly","cpi_change","fert_change"]].copy()
    X["rainfall_anomaly"] += rng.normal(0, 0.15, len(X))
    X["cpi_change"]       += rng.normal(0, 1.0,  len(X))
    X["fert_change"]      += rng.normal(0, 2.0,  len(X))
    y = df["risk_level"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    rf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42).fit(Xtr, ytr)
    gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, random_state=42).fit(Xtr, ytr)

    def m(model):
        p = model.predict(Xte)
        return dict(accuracy=accuracy_score(yte,p),
                    precision=precision_score(yte,p,average="macro",zero_division=0),
                    recall=recall_score(yte,p,average="macro",zero_division=0),
                    f1=f1_score(yte,p,average="macro"))
    rf_m, gb_m = m(rf), m(gb)
    best = rf if rf_m["f1"] >= gb_m["f1"] else gb
    pickle.dump(best, open(MODELS_STORE/"risk_classifier.pkl","wb"))

    # price MAPE on maize / Bugesera baseline
    prices = pd.read_csv(DATA_RAW/"wfp_food_prices_rwanda.csv", parse_dates=["date"])
    s = prices[(prices.crop=="maize")&(prices.market=="Bugesera")].sort_values("date").set_index("date")["price_rwf"]
    d = pd.DataFrame({"y": s})
    for lag in [1,2,3,4,8,12,52]: d[f"lag{lag}"] = d["y"].shift(lag)
    d["target"] = d["y"].shift(-4); d = d.dropna()
    feats = [c for c in d.columns if c.startswith("lag")]
    cut = int(len(d)*0.8)
    reg = RandomForestRegressor(n_estimators=200, random_state=42).fit(d[feats][:cut], d["target"][:cut])
    pred = reg.predict(d[feats][cut:])
    mape = float(np.mean(np.abs((d["target"][cut:].values - pred)/d["target"][cut:].values))*100)
    pickle.dump(reg, open(MODELS_STORE/"price_baseline.pkl","wb"))

    metrics = {
        "risk_random_forest": {k: round(v,3) for k,v in rf_m.items()},
        "risk_gradient_boosting": {k: round(v,3) for k,v in gb_m.items()},
        "price_baseline_mape": round(mape,2),
        "n_risk_rows": len(df),
    }
    json.dump(metrics, open(MODELS_STORE/"metrics.json","w"), indent=2)
    print("Saved models + metrics.json")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
