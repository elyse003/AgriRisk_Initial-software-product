"""System tests for AgriRisk Rwanda.

Testing focuses on the models' predictive accuracy and reliability on real data,
organised around three principles:

  1. Use unseen data   - evaluate on a held-out split the model never trained on.
  2. Evaluate key metrics - accuracy, precision, recall, F1 for risk; MAPE for price.
  3. Test edge cases    - unusual or out-of-range inputs are handled without failing.

Run with:  pytest tests/test_system.py -v
Or as a script:  python tests/test_system.py
"""
import os
import sys
import pickle

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import data_path, MODELS_STORE
from src.data.preprocessing import label_risk
from src.models.input_recommender import recommend
from src.models.disease_alert import assess_crop
from src.channels.whatsapp_bot import parse_message
from src.db.connection import init_db, fetch_catalogue, subscriber_count, log_risk, get_connection
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


# ---------- shared fixtures (plain functions so the file also runs as a script) ----------
def _price_series(crop="maize", district="Musanze"):
    df = pd.read_csv(data_path("wfp_food_prices_rwanda.csv"), parse_dates=["date"])
    return df[(df.crop == crop) & (df.market == district)].sort_values("date")["price_rwf"].reset_index(drop=True)


def _risk_dataset():
    rain = pd.read_csv(data_path("district_rainfall_anomalies.csv"), parse_dates=["date"])
    cpi = pd.read_csv(data_path("rwanda_food_cpi.csv"), parse_dates=["date"]).sort_values("date")
    fert = pd.read_csv(data_path("fertilizer_price_index.csv"), parse_dates=["date"]).sort_values("date")
    cpi["cpi_change"] = cpi["food_cpi"].pct_change(12) * 100
    fert["fert_change"] = fert["fert_index"].pct_change(12) * 100
    df = rain[rain.season != "off"].merge(cpi[["date", "cpi_change"]], on="date", how="left")
    df = df.merge(fert[["date", "fert_change"]], on="date", how="left").dropna(
        subset=["rainfall_anomaly", "cpi_change", "fert_change"])
    df["risk_level"] = df.apply(lambda x: label_risk(x.rainfall_anomaly, x.cpi_change, x.fert_change), axis=1)
    return df


def _mape(y, p):
    y, p = np.array(y), np.array(p)
    return float(np.mean(np.abs((y - p) / y)) * 100)


# ============================== 1. USE UNSEEN DATA ==============================
def test_price_model_on_unseen_data():
    """Train on the first 80% of months, forecast the unseen last 20%."""
    s = _price_series()
    assert len(s) > 40
    d = pd.DataFrame({"y": s})
    for lag in [1, 2, 3, 4, 8, 12]:
        d[f"lag{lag}"] = d["y"].shift(lag)
    d["target"] = d["y"].shift(-1)
    d = d.dropna()
    feats = [c for c in d.columns if c.startswith("lag")]
    cut = int(len(d) * 0.8)
    reg = RandomForestRegressor(n_estimators=200, random_state=42).fit(d[feats][:cut], d["target"][:cut])
    mape = _mape(d["target"][cut:], reg.predict(d[feats][cut:]))
    assert mape < 20, f"price MAPE on unseen data too high: {mape:.1f}%"


def test_risk_model_on_unseen_data():
    """Stratified 80/20 split; the model must generalise to the held-out fold."""
    df = _risk_dataset()
    X, y = df[["rainfall_anomaly", "cpi_change", "fert_change"]], df["risk_level"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    rf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42).fit(Xtr, ytr)
    assert accuracy_score(yte, rf.predict(Xte)) > 0.85


# ============================== 2. EVALUATE KEY METRICS ==============================
def test_risk_key_metrics():
    """Precision, recall and F1 are computed and meet a reasonable bar."""
    df = _risk_dataset()
    X, y = df[["rainfall_anomaly", "cpi_change", "fert_change"]], df["risk_level"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    rf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42).fit(Xtr, ytr)
    p = rf.predict(Xte)
    precision = precision_score(yte, p, average="macro", zero_division=0)
    recall = recall_score(yte, p, average="macro", zero_division=0)
    f1 = f1_score(yte, p, average="macro")
    assert precision > 0.7 and recall > 0.7 and f1 > 0.7


def test_price_meets_mape_target():
    """The price forecast should beat the 15% MAPE target set in the proposal."""
    s = _price_series()
    d = pd.DataFrame({"y": s})
    for lag in [1, 2, 3, 4, 8, 12]:
        d[f"lag{lag}"] = d["y"].shift(lag)
    d["target"] = d["y"].shift(-1)
    d = d.dropna()
    feats = [c for c in d.columns if c.startswith("lag")]
    cut = int(len(d) * 0.8)
    reg = RandomForestRegressor(n_estimators=200, random_state=42).fit(d[feats][:cut], d["target"][:cut])
    assert _mape(d["target"][cut:], reg.predict(d[feats][cut:])) < 15


# ============================== 3. TEST EDGE CASES ==============================
def test_price_handles_district_without_data():
    """A district with no price records returns an empty series, not an error."""
    assert len(_price_series("maize", "Gasabo")) == 0


def test_risk_handles_extreme_inputs():
    """Severe drought with high inflation, and the opposite, both return valid labels."""
    model = pickle.load(open(MODELS_STORE / "risk_classifier.pkl", "rb"))
    cols = ["rainfall_anomaly", "cpi_change", "fert_change"]
    for row in [[-3.0, 80.0, 300.0], [2.5, -5.0, -10.0], [0.0, 0.0, 0.0]]:
        pred = model.predict(pd.DataFrame([row], columns=cols))[0]
        assert pred in {"Low", "Medium", "High"}


def test_recommender_handles_zero_budget():
    """A zero budget returns no recommendations rather than crashing."""
    cat = pd.read_csv(data_path("minagri_input_prices.csv"))
    assert recommend(cat, "maize", "Musanze", 0.0).empty


def test_recommender_handles_unknown_crop():
    """A crop not in the catalogue returns an empty result."""
    cat = pd.read_csv(data_path("minagri_input_prices.csv"))
    assert recommend(cat, "rice", "Musanze", 50000.0).empty


def test_chatbot_handles_gibberish():
    """An unrecognised message still returns a structured reply object."""
    out = parse_message("xkcd qwerty zzz")
    assert isinstance(out, dict) and "intent" in out


def test_disease_alerts_are_well_formed():
    """Disease assessment returns properly structured alerts under a wet, mild forecast."""
    sample = {"temperature_2m_min": [16] * 14, "temperature_2m_max": [24] * 14,
              "relative_humidity_2m_mean": [92] * 14, "precipitation_sum": [7] * 14}
    alerts = assess_crop("potatoes", sample)
    assert isinstance(alerts, list)
    for a in alerts:
        assert {"crop", "disease", "risk", "action"} <= set(a)
        assert a["risk"] in {"Medium", "High"}



# ============================== 4. BACKEND DATABASE ==============================
def _row_count(table):
    conn = get_connection()
    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return n


def test_database_initialises_and_serves_catalogue():
    """The database is created and serves the input catalogue and sample subscribers."""
    init_db()
    cat = fetch_catalogue()
    assert len(cat) >= 1 and "price_rwf" in cat.columns
    assert subscriber_count() >= 1


def test_database_logs_a_risk_assessment():
    """A risk lookup is written to the risk_scores table."""
    init_db()
    before = _row_count("risk_scores")
    log_risk("Musanze", "A", -0.5, 12.0, 25.0, "Medium")
    assert _row_count("risk_scores") == before + 1


# ---------- script runner (so it works without pytest installed) ----------
if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
